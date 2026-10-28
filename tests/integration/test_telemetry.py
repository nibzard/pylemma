"""Inspect actual SDK exports without credentials, paid requests, or network access."""

import asyncio
import json
import os
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import httpx
import logfire
import pytest
from opentelemetry import baggage, context
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExportResult
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from test_model import Transport, completion, settings

from pylemma.application.runner import run_match
from pylemma.cli import main
from pylemma.player.model import ModelPlayer
from pylemma.records.links import validate_public_url
from pylemma.records.models import Replay
from pylemma.records.sqlite import MatchStore, migrate
from pylemma.telemetry import configure, match_context, span


@pytest.fixture
def store(tmp_path: Path) -> MatchStore:
    path = tmp_path / f"{os.environ.get('LOOPER_RESOURCE_PREFIX', 'local')}.sqlite3"
    migrate(path)
    return MatchStore(path)


@pytest.fixture
def telemetry() -> Iterator[tuple[logfire.Logfire, InMemorySpanExporter]]:
    exporter = InMemorySpanExporter()
    client = configure(
        send_to_logfire=False,
        processors=[SimpleSpanProcessor(exporter)],
    )
    yield client, exporter
    client.force_flush()


def execute(
    store: MatchStore,
    client: logfire.Logfire | None,
    transport: Transport,
) -> Replay:
    match_id = store.create(settings()).match.settings.match_id

    async def run() -> Replay:
        player = ModelPlayer(
            "CREDENTIAL-SENTINEL", transport=httpx.MockTransport(transport)
        )
        try:
            return await run_match(store, match_id, player, telemetry=client)
        finally:
            await player.close()

    return asyncio.run(run())


def finished(exporter: InMemorySpanExporter) -> list[ReadableSpan]:
    return [
        s
        for s in exporter.get_finished_spans()
        if (s.attributes or {}).get("logfire.span_type") == "span"
    ]


def test_trace_hierarchy_references_and_safe_attributes(
    store: MatchStore,
    telemetry: tuple[logfire.Logfire, InMemorySpanExporter],
) -> None:
    client, exporter = telemetry
    transport = Transport(
        [completion("invalid-private-provider-body"), *[completion()] * 10]
    )
    token = context.attach(baggage.set_baggage("visitor_ip", "ACCESS-SENTINEL"))
    try:
        with client.span("unrelated request", authorization="HEADER-SENTINEL"):
            replay = execute(store, client, transport)
    finally:
        context.detach(token)
    spans = [s for s in finished(exporter) if s.name != "unrelated request"]
    roots = [s for s in spans if s.name == "match.run"]
    assert len(roots) == 1
    root = roots[0]
    assert root.parent is None and root.context is not None
    assert replay.trace_id == f"{root.context.trace_id:032x}"
    assert replay.public_trace_url is None
    assert len(spans) == 63  # root, summary, ten groups of five, eleven requests
    by_id = {f"{s.context.span_id:016x}": s for s in spans if s.context}
    rounds = [s for s in spans if s.name == "round.run"]
    assert len(rounds) == 10
    for record in replay.rounds:
        assert record.trace_id == replay.trace_id
        round_span = by_id[str(record.span_id)]
        assert round_span.parent == root.context
        assert (round_span.attributes or {})[
            "round_number"
        ] == record.outcome.round_number
        assert (round_span.attributes or {})["player_total"] == record.player_total
        children = [s for s in spans if s.parent == round_span.context]
        assert {s.name for s in children} == {
            "player.decide",
            "opponent.decide",
            "round.resolve",
            "round.commit",
        }
    for attempt in replay.attempts:
        request = by_id[str(attempt.span_id)]
        assert attempt.trace_id == replay.trace_id
        assert request.name == "model request" and request.parent is not None
        assert by_id[f"{request.parent.span_id:016x}"].name == "player.decide"
        assert request.end_time and request.start_time
        assert request.end_time >= request.start_time
        attrs = dict(request.attributes or {})
        assert attrs["attempt"] == attempt.attempt_number
        assert attrs["input_tokens"] == attempt.input_tokens
        assert attrs["output_tokens"] == attempt.output_tokens
        observation = json.loads(str(attrs["observation"]))
        assert len(observation["history"]) == attempt.round_number - 1
        assert "stated_reason" not in json.dumps(observation)
    requests = [s for s in spans if s.name == "model request"]
    assert (requests[0].attributes or {})["error_category"] == "invalid_decision"
    assert (requests[0].attributes or {})["retry"] is True
    assert (requests[1].attributes or {})["repair_instruction"]
    exported = json.dumps([dict(s.attributes or {}) for s in spans])
    for secret in (
        "CREDENTIAL-SENTINEL",
        "HEADER-SENTINEL",
        "ACCESS-SENTINEL",
        "invalid-private-provider-body",
        "authorization",
        "visitor_ip",
    ):
        assert secret not in exported
    assert all(not s.events for s in spans)
    for item in spans:
        assert item.resource.attributes["host.name"] == "redacted"
        assert item.resource.attributes["service.instance.id"] == "redacted"
        assert not (item.attributes or {}).get("code.filepath")
    assert store.read(replay.match.settings.match_id) == replay


def test_zero_usage_stays_unknown_in_storage_and_trace(
    store: MatchStore,
    telemetry: tuple[logfire.Logfire, InMemorySpanExporter],
) -> None:
    client, exporter = telemetry
    body = completion().json()
    body["usage"] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    replay = execute(store, client, Transport([httpx.Response(200, json=body)] * 10))
    assert replay.match.status == "completed"
    for attempt in replay.attempts:
        assert attempt.input_tokens is None
        assert attempt.output_tokens is None
        assert attempt.estimated_cost_usd is None
    for record in replay.rounds:
        assert record.input_tokens is None
        assert record.output_tokens is None
        assert record.estimated_cost_usd is None
    assert store.read(replay.match.settings.match_id) == replay
    requests = [s for s in finished(exporter) if s.name == "model request"]
    assert len(requests) == 10
    for request in requests:
        attributes = dict(request.attributes or {})
        # The SDK serializes null structured attributes as JSON strings.
        assert json.loads(str(attributes["input_tokens"])) is None
        assert json.loads(str(attributes["output_tokens"])) is None
        assert json.loads(str(attributes["estimated_cost_usd"])) is None


class FailingExporter(InMemorySpanExporter):
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        raise RuntimeError("Exporter is unavailable.")


def test_export_failure_preserves_results(store: MatchStore) -> None:
    client = logfire.configure(
        local=True,
        send_to_logfire=False,
        console=False,
        metrics=False,
        inspect_arguments=False,
        additional_span_processors=[SimpleSpanProcessor(FailingExporter())],
    )
    replay = execute(store, client, Transport([completion()] * 10))
    assert replay.match.status == "completed"
    assert replay.match.player_total == replay.match.opponent_total == 30
    assert len(replay.rounds) == 10
    assert replay.public_trace_url is None
    assert store.read(replay.match.settings.match_id) == replay


def test_safe_failed_match(
    store: MatchStore,
    telemetry: tuple[logfire.Logfire, InMemorySpanExporter],
) -> None:
    client, exporter = telemetry
    replay = execute(
        store,
        client,
        Transport(
            [
                completion(),
                httpx.Response(401, json={"error": {"message": "SECRET-BODY"}}),
            ]
        ),
    )
    assert replay.match.status == "failed" and len(replay.rounds) == 1
    spans = finished(exporter)
    assert "match.complete" not in [s.name for s in spans]
    assert "SECRET-BODY" not in json.dumps([dict(s.attributes or {}) for s in spans])
    assert all(not s.events for s in spans)
    assert replay.attempts[-1].span_id
    assert replay.attempts[-1].input_tokens is None


def test_disabled_telemetry(store: MatchStore) -> None:
    replay = execute(store, None, Transport([completion()] * 10))
    assert replay.trace_id is None
    assert all(r.span_id is None for r in replay.rounds)
    assert all(a.span_id is None for a in replay.attempts)


def test_span_api_failure_does_not_swallow_application_errors(
    telemetry: tuple[logfire.Logfire, InMemorySpanExporter],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = telemetry

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("SDK failed")

    monkeypatch.setattr(client, "span", fail)
    with match_context(client), span("test") as reference:
        assert reference.trace_id is None
    with pytest.raises(ValueError, match="application"):
        with match_context(client), span("test"):
            raise ValueError("application")


@pytest.mark.parametrize(
    "url",
    [
        "http://logfire.pydantic.dev/public/example",
        "javascript:alert(1)",
        "https://logfire.pydantic.dev.evil.test/public/example",
        "https://evil.test@logfire.pydantic.dev/public/example",
        "https://logfire.pydantic.dev:443/public/example",
        "https://logfire.pydantic.dev/redirect?url=https://evil.test",
        "https://logfire.pydantic.dev/%2f%2fevil.test",
        "https://logfire.pydantic.dev/",
        "https://logfire.pydantic.dev/public/example\n",
        "https://logfire.pydantic.dev\\@evil.test/x",
        "https://logfire.pydantic.dev/public/example#javascript:alert(1)",
        "https://logfire-eu.pydantic.dev.evil.test/public/example",
        "https://logfire-eu.pydantic.dev/redirect?url=https://evil.test",
    ],
)
def test_reject_unsafe_links(url: str) -> None:
    with pytest.raises(ValueError):
        validate_public_url(url)


@pytest.mark.parametrize(
    "host",
    ["logfire.pydantic.dev", "logfire-us.pydantic.dev", "logfire-eu.pydantic.dev"],
)
def test_reviewed_cli_and_replay_independence(
    host: str,
    store: MatchStore,
    telemetry: tuple[logfire.Logfire, InMemorySpanExporter],
) -> None:
    client, _ = telemetry
    replay = execute(store, client, Transport([completion()] * 10))
    match_id = str(replay.match.settings.match_id)
    base = ["--database", str(store.path)]
    url = f"https://{host}/public/example"
    with pytest.raises(SystemExit):
        main([*base, "record-link", match_id, url])
    main([*base, "record-link", match_id, url, "--reviewed"])
    assert store.read(replay.match.settings.match_id).public_trace_url == url
    replacement = "https://logfire-us.pydantic.dev/public/replacement"
    main([*base, "record-link", match_id, replacement, "--reviewed"])
    assert store.read(replay.match.settings.match_id).public_trace_url == replacement
    main([*base, "remove-link", match_id])
    main([*base, "remove-link", match_id])
    assert store.read(replay.match.settings.match_id) == replay
    pending = store.create(settings())
    with pytest.raises(ValueError, match="completed traced"):
        store.set_public_trace_url(pending.match.settings.match_id, url)
    with pytest.raises(SystemExit):
        main([*base, "record-link", match_id, "https://evil.test/x", "--reviewed"])
    assert store.read(replay.match.settings.match_id) == replay


def test_failed_commit_has_no_score_attributes(
    store: MatchStore,
    telemetry: tuple[logfire.Logfire, InMemorySpanExporter],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sqlite3

    client, exporter = telemetry

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise sqlite3.OperationalError("PRIVATE-STORAGE-DETAIL")

    monkeypatch.setattr(store, "commit_round", fail)
    replay = execute(store, client, Transport([completion()]))
    assert replay.error_category == "storage_error"
    assert not replay.rounds and replay.match.player_total == 0
    exported = json.dumps([dict(s.attributes or {}) for s in finished(exporter)])
    assert "PRIVATE-STORAGE-DETAIL" not in exported
    for item in finished(exporter):
        assert "player_points" not in (item.attributes or {})
        assert not item.events


def test_configuration_rejects_custom_resource_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "visitor_ip=PRIVATE")
    with pytest.raises(ValueError, match="custom resource metadata"):
        configure(send_to_logfire=False)


def test_concurrent_matches_have_independent_roots(
    store: MatchStore,
    telemetry: tuple[logfire.Logfire, InMemorySpanExporter],
) -> None:
    client, exporter = telemetry
    first = store.create(settings()).match.settings.match_id
    second = store.create(settings()).match.settings.match_id

    async def run() -> tuple[Replay, Replay]:
        players = [
            ModelPlayer(
                "unused", transport=httpx.MockTransport(Transport([completion()] * 10))
            )
            for _ in range(2)
        ]
        try:
            return await asyncio.gather(
                run_match(store, first, players[0], telemetry=client),
                run_match(store, second, players[1], telemetry=client),
            )
        finally:
            for player in players:
                await player.close()

    replays = asyncio.run(run())
    assert replays[0].trace_id != replays[1].trace_id
    roots = [s for s in finished(exporter) if s.name == "match.run"]
    assert len(roots) == 2 and all(s.parent is None for s in roots)
    for replay in replays:
        assert all(a.trace_id == replay.trace_id for a in replay.attempts)
        assert all(r.trace_id == replay.trace_id for r in replay.rounds)
