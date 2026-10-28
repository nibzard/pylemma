"""Explicit match telemetry. Never pass exceptions or transport objects to Logfire."""

import os
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

import logfire
from opentelemetry import context, trace
from opentelemetry.sdk.trace import SpanProcessor

from pylemma import __version__

_active: ContextVar[logfire.Logfire | None] = ContextVar(
    "match_telemetry", default=None
)


@dataclass
class Span:
    """Best-effort attributes and references; identifiers do not prove delivery."""

    handle: logfire.LogfireSpan | None = None
    trace_id: str | None = None
    span_id: str | None = None

    def set(self, **attributes: Any) -> None:
        if self.handle is not None:
            try:
                self.handle.set_attributes(attributes)
            except Exception:
                pass


@contextmanager
def match_context(client: logfire.Logfire | None) -> Iterator[None]:
    """Start an independent trace without inherited request baggage or parents."""
    token = _active.set(client)
    parent = context.attach(context.Context())
    try:
        yield
    finally:
        context.detach(parent)
        _active.reset(token)


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[Span]:
    """Keep exporter failures separate from application failures and private text."""
    result = Span()
    client = _active.get()
    parent = context.attach(context.get_current())
    try:
        if client is not None:
            try:
                attributes.update(
                    {"code.filepath": "", "code.function": "", "code.lineno": 0}
                )
                result.handle = client.span(name, **attributes)
                result.handle.__enter__()
                reference = trace.get_current_span().get_span_context()
                if reference.is_valid:
                    result.trace_id = f"{reference.trace_id:032x}"
                    result.span_id = f"{reference.span_id:016x}"
            except Exception:
                result = Span()
        try:
            yield result
        except BaseException as error:
            name = type(error).__name__
            permitted = {
                "TimeoutError",
                "ValidationError",
                "MontyCrashedError",
                "MontyDisconnectError",
                "MontyRuntimeError",
                "MontySyntaxError",
                "MontyConversionError",
                "MontyTypingError",
                "APIConnectionError",
                "APITimeoutError",
                "RateLimitError",
            }
            result.set(
                error_category="application_error",
                error_type=name if name in permitted else "UnexpectedError",
            )
            raise
    finally:
        if result.handle is not None:
            try:
                # Never let the SDK capture raw exceptions, stack locals, or bodies.
                result.handle.__exit__(None, None, None)
            except Exception:
                pass
        # Restore context even when an exporter fails during span exit.
        context.detach(parent)


def configure(
    *,
    send_to_logfire: bool = True,
    processors: Sequence[SpanProcessor] = (),
) -> logfire.Logfire:
    """Opt in using normal Logfire authentication for the operator's project.

    Do not enable automatic HTTP, provider, or framework instrumentation.
    Call only after explicit configuration; importing this module exports nothing.
    """
    # Resource environment overrides can add arbitrary metadata outside span scrubbing.
    if any(
        os.environ.get(key)
        for key in (
            "OTEL_RESOURCE_ATTRIBUTES",
            "OTEL_EXPERIMENTAL_RESOURCE_DETECTORS",
            "LOGFIRE_RESOURCE_ATTRIBUTES",
            "LOGFIRE_RESOURCE_DETECTORS",
        )
    ):
        raise ValueError(
            "Remove custom resource metadata before configuring match traces."
        )
    return logfire.configure(
        send_to_logfire=send_to_logfire,
        additional_span_processors=processors,
        resource_attributes={
            "host.name": "redacted",
            "service.instance.id": "redacted",
        },
        service_version=__version__,
        advanced=logfire.AdvancedOptions(resource_detectors=[]),
        local=True,
        service_name="pylemma",
        console=False,
        metrics=False,
        inspect_arguments=False,
        add_baggage_to_attributes=False,
        distributed_tracing=False,
    )
