"""Arena selection, idempotency, consent, and complete scoring."""

import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID

import logfire
import pytest
from fastapi.testclient import TestClient
from test_machines import FakeBuilder

from pylemma.machine_store import MachineStore
from pylemma.machines import Machine, Sandbox, arena, presets
from pylemma.web.app import create_app


def test_arena_fallback_and_selection(tmp_path: Path) -> None:
    store = MachineStore(tmp_path / "arena.sqlite3")
    player = Machine.create("Entry", "Cooperate", presets()[0], public_listing=True)
    store.put(player)
    sandbox = Sandbox()
    try:
        result = arena(sandbox, player, [])
        assert result["total"] == 273
        assert len(result["matches"]) == 10
        assert all(m["preset"] for m in result["matches"])
        for index in range(12):
            candidate = Machine.create(
                str(index), "Cooperate", presets()[0], public_listing=True
            )
            store.put(candidate)
            store.replay(
                {
                    "kind": "arena",
                    "machine": candidate.model_dump(mode="json"),
                    "result": result,
                    "created_at": f"2026-10-28T12:00:{index:02}+00:00",
                }
            )
        chosen = store.arena_opponents(player.id)
        assert [m.name for m in chosen] == [str(i) for i in range(11, 1, -1)]
        mixed = arena(sandbox, player, chosen[:1])
        assert mixed["matches"][0]["opponent_id"] == str(chosen[0].id)
        assert mixed["matches"][0]["source_hash"] == chosen[0].source_hash
        assert mixed["total"] == 273
        assert len(store.arena_opponents(chosen[0].id)) == 10
        assert chosen[0].id not in {m.id for m in store.arena_opponents(chosen[0].id)}
        with pytest.raises(ValueError):
            arena(sandbox, player, [player])
    finally:
        sandbox.close()


def test_entry_retry_is_saved_and_unlisted_stays_private(tmp_path: Path) -> None:
    store = MachineStore(tmp_path / "entry.sqlite3")
    telemetry = logfire.configure(send_to_logfire=False, console=False, local=True)
    builder = FakeBuilder()
    with TestClient(create_app(store, builder, telemetry, 2)) as client:

        def enter(listed: bool) -> dict[str, Any]:
            machine = client.post(
                "/api/machines",
                json={
                    "name": "Trust",
                    "strategy": "Cooperate",
                    "public_acknowledged": True,
                    "public_listing": listed,
                    "preview": True,
                },
            ).json()["machine"]
            body = {"machine_id": machine["id"]}
            first = client.post("/api/arena", json=body)
            assert first.status_code == 201
            with store.connect() as db:
                count = db.execute("SELECT count(*) FROM challenge_slots").fetchone()[0]
            second = client.post("/api/arena", json=body)
            assert second.json()["replay_id"] == first.json()["replay_id"]
            assert second.json()["result"] == first.json()["result"]
            with store.connect() as db:
                assert (
                    db.execute("SELECT count(*) FROM challenge_slots").fetchone()[0]
                    == count
                )
            result: dict[str, Any] = first.json()
            return result

        private = enter(False)
        assert client.get("/api/arena").json()["total"] == 0
        public = enter(True)
        recent = client.get("/api/arena").json()
        assert recent["total"] == 1
        assert "rank" not in recent["entries"][0]
        assert recent["entries"][0]["scores"] == [273]
        assert client.get("/api/leaderboard").json()["total"] == 0
        assert builder.calls == 2
        assert [
            m.id for m in store.arena_opponents(UUID(private["machine"]["id"]))
        ] == [UUID(public["machine"]["id"])]
        assert (
            client.post(
                "/api/events",
                json={"event": "inspection_click", "replay_id": public["replay_id"]},
            ).status_code
            == 204
        )
        assert (
            client.post(
                "/api/events",
                json={"event": "unknown", "replay_id": public["replay_id"]},
            ).status_code
            == 422
        )
        with pytest.raises(sqlite3.IntegrityError):
            store.replay({k: v for k, v in public.items() if k != "replay_id"})


def test_failed_arena_does_not_save_a_completed_entry(tmp_path: Path) -> None:
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from pylemma.machines import Blueprint
    from pylemma.telemetry import configure

    store = MachineStore(tmp_path / "failed-arena.sqlite3")
    broken = Machine.create(
        "Stops",
        "Stop in round two",
        Blueprint(
            summary="Stops",
            code="""
def decide(observation):
    if observation['round'] == 2:
        return {'choice':'invalid', 'stated_reason':'Stop.'}
    return {'choice':'cooperate', 'stated_reason':'Start.'}
""",
        ),
    )
    store.put(broken)
    exporter = InMemorySpanExporter()
    telemetry = configure(
        send_to_logfire=False, processors=[SimpleSpanProcessor(exporter)]
    )
    with TestClient(create_app(store, FakeBuilder(), telemetry, 1)) as client:
        response = client.post("/api/arena", json={"machine_id": str(broken.id)})
        assert response.status_code == 422
        assert store.arena_entry(broken.id) is None
        assert store.arena_games()["total"] == 0
        with store.connect() as db:
            assert db.execute("SELECT count(*) FROM machine_replays").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM challenge_slots").fetchone()[0] == 1

    root = next(s for s in exporter.get_finished_spans() if s.name == "machine.arena")
    assert root.attributes is not None
    assert root.attributes["machine_id"] == str(broken.id)
    assert root.attributes["stage"] == "execution"


def test_arena_trace_records_round_references_and_funnel(tmp_path: Path) -> None:
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from pylemma.telemetry import configure

    exporter = InMemorySpanExporter()
    telemetry = configure(
        send_to_logfire=False, processors=[SimpleSpanProcessor(exporter)]
    )
    store = MachineStore(tmp_path / "traces.sqlite3")
    player = Machine.create("Trust", "Cooperate", presets()[0])
    store.put(player)
    with TestClient(create_app(store, FakeBuilder(), telemetry, 1)) as client:
        response = client.post(
            "/api/arena",
            json={"machine_id": str(player.id), "referral": str(player.id)},
        )
        assert response.status_code == 201
        data = response.json()
        client.post(
            "/api/events",
            json={"event": "inspection_click", "replay_id": data["replay_id"]},
        )
        client.post("/api/arena", json={"machine_id": str(player.id)})
    spans = exporter.get_finished_spans()
    roots = [s for s in spans if s.name == "machine.arena"]
    assert len(roots) == 1
    assert roots[0].attributes is not None
    assert roots[0].attributes["completed"] is True
    assert roots[0].attributes["referred"] is True
    rounds = [s for s in spans if s.name == "machine.round"]
    assert len(rounds) == 100
    references = {f"{s.context.span_id:016x}" for s in rounds if s.context}
    assert {
        r["span_id"] for m in data["result"]["matches"] for r in m["rounds"]
    } == references
    assert len([s for s in spans if s.name == "arena.opponent"]) == 10
    assert any(s.name == "game.funnel" for s in spans)
