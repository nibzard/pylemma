"""Measure streaming boundaries without exporting transport metadata."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from pylemma import generator as module
from pylemma.machines import presets
from pylemma.telemetry import configure, match_context


class Chunks(httpx.AsyncByteStream):
    def __init__(self, *, finish: bool = True, stall: bool = False) -> None:
        self.finish = finish
        self.stall = stall
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        blueprint = presets()[0].model_dump_json()
        parts = ["", blueprint[:30], blueprint[30:]]
        for part in parts:
            await asyncio.sleep(10 if self.stall and part else 0.01)
            yield self.encode([{"index": 0, "delta": {"content": part}}])
        if self.finish:
            yield self.encode([{"index": 0, "delta": {}, "finish_reason": "stop"}])
            yield self.encode(
                [], {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
            )
        yield b"data: [DONE]\n\n"

    @staticmethod
    def encode(
        choices: list[dict[str, Any]], usage: dict[str, int] | None = None
    ) -> bytes:
        return (
            "data: "
            + json.dumps(
                {
                    "id": "test",
                    "object": "chat.completion.chunk",
                    "created": 1,
                    "model": "test",
                    "choices": choices,
                    "usage": usage,
                }
            )
            + "\n\n"
        ).encode()

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.parametrize("mode", ["complete", "incomplete", "timeout"])
def test_generation_timing_and_stream_cleanup(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    exporter = InMemorySpanExporter()
    telemetry = configure(
        send_to_logfire=False, processors=[SimpleSpanProcessor(exporter)]
    )
    chunks = Chunks(finish=mode != "incomplete", stall=mode == "timeout")
    calls = 0
    if mode == "timeout":
        monkeypatch.setattr(module, "GENERATION_TIMEOUT", 0.08)

    async def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        trace = request.extensions["trace"]
        for event in (
            "connection.connect_tcp.started",
            "connection.connect_tcp.complete",
            "connection.start_tls.started",
            "connection.start_tls.complete",
            "http11.send_request_body.complete",
        ):
            await trace(
                event, {"secret": "PRIVATE", "exception": RuntimeError("PRIVATE")}
            )
        await trace("unrecognized.PRIVATE", {"secret": "PRIVATE"})
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream", "x-private": "PRIVATE"},
            stream=chunks,
        )

    async def execute() -> None:
        builder = module.Generator("PRIVATE", transport=httpx.MockTransport(respond))
        try:
            with match_context(telemetry):
                if mode == "complete":
                    assert await builder.generate("Cooperate") == presets()[0]
                else:
                    with pytest.raises(
                        TimeoutError if mode == "timeout" else ValueError
                    ):
                        await builder.generate("Cooperate")
            assert module._current_timing.get() is None
        finally:
            await builder.close()

    asyncio.run(execute())
    assert calls == 1
    assert chunks.closed
    record = next(
        s for s in exporter.get_finished_spans() if s.name == "machine.generate"
    )
    attrs = record.attributes or {}
    marks = json.loads(str(attrs["timing_ms"]))
    assert marks["request_dispatched"] <= marks["tcp_start"] <= marks["tcp_complete"]
    assert marks["tls_start"] <= marks["tls_complete"] <= marks["request_sent"]
    assert marks["request_sent"] <= marks["response_headers"] <= marks["first_chunk"]
    cpu_ms = attrs["process_cpu_ms"]
    assert isinstance(cpu_ms, (float, int))
    assert cpu_ms >= 0
    if mode == "complete":
        assert marks["first_chunk"] < marks["first_content"] < marks["stream_complete"]
        assert marks["stream_complete"] <= marks["validated"] <= marks["total"]
        assert json.loads(str(attrs["usage"]))["total_tokens"] == 150
    else:
        assert "validated" not in marks
        assert attrs["stage"] != "complete"
    assert "PRIVATE" not in str(attrs)
    assert not record.events
