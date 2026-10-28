"""Offline acceptance checks for generated machines and the public boundary."""

from pathlib import Path
from typing import Any

import logfire
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pydantic_monty import MontyRuntimeError

from pylemma.machine_store import MachineStore
from pylemma.machines import Blueprint, Machine, Sandbox, play, presets, tournament
from pylemma.web.app import create_app, hosted


@pytest.fixture
def sandbox() -> Any:
    instance = Sandbox()
    yield instance
    instance.close()


def test_tournament_and_simultaneous_choices(sandbox: Sandbox) -> None:
    machine = Machine.create("Trust", "Always cooperate", presets()[0])
    result = tournament(sandbox, machine)
    assert result["total"] == 81
    assert result["matches"][0]["totals"] == [30, 30]
    assert result["matches"][2]["totals"] == [21, 36]
    copy = Blueprint(
        summary="Copy",
        code="""
def decide(observation):
    h = observation['history']
    choice = h[-1]['opponent'] if h else 'cooperate'
    return {'choice': choice, 'stated_reason': 'Copy the last completed choice.'}
""",
    )
    result = play(sandbox, copy, presets()[2])
    assert result["rounds"][2]["choices"] == ["cooperate", "betray"]
    assert result["rounds"][3]["choices"][0] == "betray"


def test_fresh_sessions(sandbox: Sandbox) -> None:
    blueprint = Blueprint(
        summary="Fresh state",
        code="""
counter = 0
def decide(observation):
    global counter
    counter += 1
    return {'choice': 'cooperate' if counter == 1 else 'betray',
            'stated_reason': 'The counter starts fresh.'}
""",
    )
    result = play(sandbox, blueprint, blueprint)
    assert result["totals"] == [30, 30]


@pytest.mark.parametrize(
    "code",
    [
        "while True:\n    pass",
        "open('/etc/passwd').read()",
        "import os\nos.environ['OPENAI_API_KEY']",
        "x = 'a' * 100000000",
    ],
)
def test_sandbox_rejects_unbounded_or_host_access(sandbox: Sandbox, code: str) -> None:
    with pytest.raises(MontyRuntimeError):
        sandbox.decide(Blueprint(summary="Invalid", code=code), {})
    sandbox.validate(presets()[0])


def test_invalid_decision(sandbox: Sandbox) -> None:
    blueprint = Blueprint(
        summary="Invalid", code="def decide(o):\n    return {'choice': 'win'}"
    )
    with pytest.raises(ValidationError):
        sandbox.decide(blueprint, {})


class FakeBuilder:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, strategy: str) -> Blueprint:
        self.calls += 1
        return presets()[0]

    async def close(self) -> None:
        pass


def test_public_flow_and_daily_reservation(tmp_path: Path) -> None:
    store = MachineStore(tmp_path / "machines.sqlite3")
    builder = FakeBuilder()
    telemetry = logfire.configure(send_to_logfire=False, console=False, local=True)
    with TestClient(create_app(store, builder, telemetry, 2)) as client:
        assert client.get("/").status_code == 200
        body = {
            "name": "Trust",
            "strategy": "Always cooperate",
            "public_acknowledged": False,
        }
        assert client.post("/api/machines", json=body).status_code == 422
        assert builder.calls == 0
        body["public_acknowledged"] = True
        a = client.post("/api/machines", json=body)
        assert a.status_code == 201
        first = a.json()
        assert first["result"]["total"] == 81
        b = client.post("/api/machines", json=body).json()
        assert first["machine"]["id"] != b["machine"]["id"]
        assert (
            client.get("/api/machines/" + first["machine"]["id"]).json()
            == first["machine"]
        )
        assert (
            client.get("/api/replays/" + first["replay_id"]).json()["result"]["total"]
            == 81
        )
        result = client.post(
            "/api/challenges",
            json={"left": first["machine"]["id"], "right": b["machine"]["id"]},
        )
        assert result.status_code == 201
        assert result.json()["result"]["totals"] == [30, 30]
        assert client.post("/api/machines", json=body).status_code == 429
        assert builder.calls == 2
        assert client.get("/api/machines/not-a-uuid").status_code == 422
        assert (
            client.get("/api/replays/00000000-0000-0000-0000-000000000000").status_code
            == 404
        )
    assert MachineStore(store.path).get(first["machine"]["id"]).name == "Trust"


def test_hosted_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="LOGFIRE_TOKEN"):
        hosted()


def test_reviewed_trace_link(tmp_path: Path) -> None:
    store = MachineStore(tmp_path / "records.sqlite3")
    identifier = store.replay({"kind": "challenge", "result": {}})
    url = "https://logfire-us.pydantic.dev/public-trace/example"
    store.review(identifier, url)
    assert store.read(identifier)["public_trace_url"] == url
    with pytest.raises(ValueError):
        store.review(identifier, "https://example.com/private")
    assert store.read(identifier)["public_trace_url"] == url
    store.review(identifier, None)
    assert store.read(identifier)["public_trace_url"] is None


def test_failed_generation_consumes_quota(tmp_path: Path) -> None:
    class BrokenBuilder(FakeBuilder):
        async def generate(self, strategy: str) -> Blueprint:
            raise RuntimeError("private provider error")

    store = MachineStore(tmp_path / "failed.sqlite3")
    telemetry = logfire.configure(send_to_logfire=False, console=False, local=True)
    with TestClient(create_app(store, BrokenBuilder(), telemetry, 1)) as client:
        body = {"name": "Test", "strategy": "Trust", "public_acknowledged": True}
        response = client.post("/api/machines", json=body)
        assert response.status_code == 502
        assert "private provider error" not in response.text
        assert client.post("/api/machines", json=body).status_code == 429
        with store.connect() as db:
            assert db.execute("SELECT count(*) FROM machines").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM machine_replays").fetchone()[0] == 0


def test_challenge_reservation_is_separate(tmp_path: Path) -> None:
    store = MachineStore(tmp_path / "limits.sqlite3")
    assert store.reserve_challenge(1)
    assert not store.reserve_challenge(1)
    assert store.reserve(1)
    assert not store.reserve(1)


def test_generation_http_contract_and_trace(sandbox: Sandbox) -> None:
    import asyncio
    import json

    import httpx
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from pylemma.generator import Generator
    from pylemma.telemetry import configure, match_context

    requests: list[dict[str, Any]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        chunk = {
            "id": "example",
            "created": 1,
            "object": "chat.completion.chunk",
            "model": "test",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "delta": {"content": presets()[0].model_dump_json()},
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream"},
            content=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n",
        )

    exporter = InMemorySpanExporter()
    telemetry = configure(
        send_to_logfire=False, processors=[SimpleSpanProcessor(exporter)]
    )

    async def execute() -> None:
        generator = Generator("synthetic-key", transport=httpx.MockTransport(respond))
        assert not requests  # Preparing client resources must not call the provider.
        try:
            with match_context(telemetry):
                blueprint = await generator.generate("Always cooperate")
                sandbox.validate(blueprint)
        finally:
            await generator.close()

    asyncio.run(execute())
    assert len(requests) == 1
    assert requests[0]["max_completion_tokens"] == 2400
    assert requests[0]["stream"] is True
    assert requests[0]["stream_options"] == {"include_usage": True}
    assert requests[0]["messages"][1]["content"] == "Always cooperate"
    telemetry.force_flush()
    spans = exporter.get_finished_spans()
    assert any(s.name == "machine.generate" for s in spans)
    assert any(s.name == "machine.decision" for s in spans)


def test_export_flush_failure_preserves_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MachineStore(tmp_path / "flush.sqlite3")
    telemetry = logfire.configure(send_to_logfire=False, console=False, local=True)

    def broken_flush(*args: Any, **kwargs: Any) -> bool:
        raise RuntimeError("Exporter unavailable")

    monkeypatch.setattr(telemetry, "force_flush", broken_flush)
    with TestClient(create_app(store, FakeBuilder(), telemetry, 1)) as client:
        response = client.post(
            "/api/machines",
            json={
                "name": "Trust",
                "strategy": "Cooperate",
                "public_acknowledged": True,
            },
        )
        assert response.status_code == 201
        assert response.json()["result"]["total"] == 81


def test_preview_then_confirm_without_another_generation(tmp_path: Path) -> None:
    store = MachineStore(tmp_path / "preview.sqlite3")
    builder = FakeBuilder()
    telemetry = logfire.configure(send_to_logfire=False, console=False, local=True)
    with TestClient(create_app(store, builder, telemetry, 1)) as client:
        preview = client.post(
            "/api/machines",
            json={
                "name": "Trust",
                "strategy": "Cooperate",
                "public_acknowledged": True,
                "preview": True,
            },
        )
        assert preview.status_code == 201
        assert "result" not in preview.json()
        assert builder.calls == 1
        with store.connect() as db:
            assert db.execute("SELECT count(*) FROM machine_replays").fetchone()[0] == 0
        machine_id = preview.json()["machine"]["id"]
        result = client.post("/api/tournaments", json={"machine_id": machine_id})
        assert result.status_code == 201
        assert result.json()["result"]["total"] == 81
        assert builder.calls == 1
        replay = client.get("/api/replays/" + result.json()["replay_id"]).json()
        assert replay["machine"]["id"] == machine_id
        assert replay["result"]["total"] == 81
        assert (
            client.post(
                "/api/tournaments",
                json={"machine_id": "00000000-0000-0000-0000-000000000000"},
            ).status_code
            == 404
        )


def test_published_reference_scores(sandbox: Sandbox) -> None:
    cooperate = Machine.create("Cooperate", "Always cooperate", presets()[0])
    betray = Machine.create(
        "Betray",
        "Always betray",
        Blueprint(
            summary="Always betray",
            code=(
                "def decide(o):\n"
                "    return {'choice': 'betray', 'stated_reason': 'Always betray.'}"
            ),
        ),
    )
    assert tournament(sandbox, cooperate)["total"] == 81
    assert tournament(sandbox, betray)["total"] == 78


def test_generation_has_a_total_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    import httpx

    from pylemma import generator as module

    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(500)

    monkeypatch.setattr(module, "GENERATION_TIMEOUT", 0.01)

    async def execute() -> None:
        builder = module.Generator("synthetic", transport=httpx.MockTransport(slow))
        try:
            with pytest.raises(TimeoutError):
                await builder.generate("Cooperate")
        finally:
            await builder.close()

    asyncio.run(execute())


def test_creation_timeout_has_a_useful_response(tmp_path: Path) -> None:
    class SlowBuilder(FakeBuilder):
        async def generate(self, strategy: str) -> Blueprint:
            raise TimeoutError()

    store = MachineStore(tmp_path / "deadline.sqlite3")
    telemetry = logfire.configure(send_to_logfire=False, console=False, local=True)
    with TestClient(create_app(store, SlowBuilder(), telemetry, 1)) as client:
        response = client.post(
            "/api/machines",
            json={
                "name": "Trust",
                "strategy": "Cooperate",
                "public_acknowledged": True,
            },
        )
        assert response.status_code == 504
        assert "took too long" in response.json()["detail"]
        assert not store.reserve(1)
