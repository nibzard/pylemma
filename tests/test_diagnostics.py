"""Correlate failures without recording private request or exception data."""

from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic_monty import MontyRuntimeError
from test_machines import FakeBuilder

from pylemma.machine_store import MachineStore
from pylemma.machines import Blueprint, Sandbox
from pylemma.telemetry import configure, match_context, request_reference
from pylemma.web.app import create_app


def test_requests_and_game_spans_share_reference_without_private_headers(
    tmp_path: Path,
) -> None:
    exporter = InMemorySpanExporter()
    telemetry = configure(
        send_to_logfire=False, processors=[SimpleSpanProcessor(exporter)]
    )
    reference = "00000000-0000-0000-0000-000000000001"
    with TestClient(
        create_app(MachineStore(tmp_path / "db.sqlite3"), FakeBuilder(), telemetry, 1)
    ) as client:
        created = client.post(
            "/api/machines?secret=PRIVATE",
            headers={"X-Request-ID": reference, "Authorization": "PRIVATE"},
            json={
                "name": "Trust",
                "strategy": "Cooperate",
                "preview": True,
                "public_acknowledged": True,
            },
        )
        assert created.status_code == 201
        assert created.headers["X-Request-ID"] == reference
        rejected = client.post(
            "/api/diagnostics",
            json={
                "request_id": reference,
                "operation": "create",
                "failure": "network",
                "status": 0,
                "message": "PRIVATE",
            },
        )
        assert rejected.status_code == 422
        report = client.post(
            "/api/diagnostics",
            json={
                "request_id": reference,
                "operation": "create",
                "failure": "network",
                "status": 0,
            },
        )
        assert report.status_code == 204
        assert UUID(report.headers["X-Request-ID"]) != UUID(reference)
    spans = exporter.get_finished_spans()
    creation = next(s for s in spans if s.name == "machine.create")
    decision = next(s for s in spans if s.name == "machine.decision")
    assert (creation.attributes or {})["request_id"] == reference
    assert (decision.attributes or {})["request_id"] == reference
    assert (creation.attributes or {})["stage"] == "complete"
    request = next(
        s
        for s in spans
        if s.name == "application.request"
        and (s.attributes or {}).get("request_id") == reference
    )
    assert (request.attributes or {})["status"] == 201
    assert (request.attributes or {})["route"] == "/api/machines"
    assert any(
        s.name == "browser.failure"
        and (s.attributes or {}).get("failed_request_id") == reference
        for s in spans
    )
    assert "PRIVATE" not in str([s.attributes for s in spans])
    assert request_reference.get() is None


@pytest.mark.parametrize(
    "code, subtype",
    [
        ('def decide(o):\n    return o["PRIVATE"]', "KeyError"),
        ("def decide(o):\n    while True:\n        pass", "TimeoutError"),
    ],
)
def test_sandbox_failure_records_stage_limits_and_safe_subtype(
    code: str, subtype: str
) -> None:
    exporter = InMemorySpanExporter()
    telemetry = configure(
        send_to_logfire=False, processors=[SimpleSpanProcessor(exporter)]
    )
    sandbox = Sandbox()
    try:
        with match_context(telemetry), pytest.raises(MontyRuntimeError):
            sandbox.decide(
                Blueprint(summary="Error", code=code),
                {},
            )
    finally:
        sandbox.close()
    telemetry.force_flush()
    record = next(
        s for s in exporter.get_finished_spans() if s.name == "machine.decision"
    )
    attributes = record.attributes or {}
    assert attributes["stage"] == "execute"
    assert attributes["runtime_error_type"] == subtype
    assert attributes["error_type"] == "MontyRuntimeError"
    assert attributes["request_timeout_seconds"] == 2.0
    assert "PRIVATE" not in str(attributes)
    assert not record.events
