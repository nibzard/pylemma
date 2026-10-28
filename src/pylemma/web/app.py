"""Required hosted configuration and bounded machine operations."""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Literal, Protocol
from uuid import UUID, uuid4

import logfire
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import RequestResponseEndpoint

from pylemma.generator import Generator
from pylemma.machine_store import MachineStore
from pylemma.machines import Blueprint, Machine, Sandbox, arena, play, tournament
from pylemma.remote_store import RemoteMachineStore
from pylemma.telemetry import configure, match_context, request_reference, span
from pylemma.trace_links import inspect_link


class Builder(Protocol):
    async def generate(self, strategy: str) -> Blueprint: ...
    async def close(self) -> None: ...


class Create(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: Annotated[str, Field(min_length=1, max_length=60)]
    strategy: Annotated[str, Field(min_length=1, max_length=1000)]
    public_acknowledged: bool
    preview: bool = False
    public_listing: bool = False


class TournamentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    machine_id: UUID


class Challenge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    left: UUID
    right: UUID
    referral: UUID | None = None


class FunnelEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event: Literal["inspection_click", "example_inspection_click", "share_click"]
    replay_id: UUID


class BrowserFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    request_id: Annotated[
        str, Field(pattern=r"^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$")
    ]
    operation: Literal["create", "arena", "challenge", "tournament", "replay", "read"]
    failure: Literal["network", "http", "invalid_response"]
    status: Annotated[int, Field(ge=0, le=599)]


class ArenaRequest(TournamentRequest):
    referral: UUID | None = None


def create_app(
    store: MachineStore | RemoteMachineStore,
    builder: Builder,
    telemetry: logfire.Logfire,
    daily_limit: int,
    *,
    logfire_project_url: str | None = None,
    public_trace_urls: dict[str, str] | None = None,
) -> FastAPI:
    """Explicit dependencies allow offline tests without weakening hosted startup."""
    if telemetry is None or daily_limit < 1:
        raise ValueError("Configure Logfire and a positive generation quota.")
    sandbox = Sandbox()
    gate = asyncio.Lock()

    def flush() -> None:
        try:
            telemetry.force_flush(timeout_millis=3000)
        except Exception:
            pass

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            sandbox.close()
            await builder.close()
            if isinstance(store, RemoteMachineStore):
                store.close()
            flush()

    app = FastAPI(lifespan=lifespan)

    @app.middleware("http")
    async def flush_trace(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        try:
            identifier = str(UUID(request.headers.get("X-Request-ID", "")))
        except ValueError:
            identifier = str(uuid4())
        token = request_reference.set(identifier)
        try:
            with (
                match_context(telemetry),
                span(
                    "application.request",
                    method=request.method
                    if request.method in {"GET", "POST"}
                    else "OTHER",
                    route="unmatched",
                ) as operation,
            ):
                try:
                    response = await call_next(request)
                    operation.set(
                        status=response.status_code,
                        outcome=response.headers.get(
                            "X-Game-Outcome",
                            "rejected" if response.status_code >= 400 else "completed",
                        ),
                        route=getattr(request.scope.get("route"), "path", "unmatched"),
                    )
                    response.headers["X-Request-ID"] = identifier
                except asyncio.CancelledError:
                    operation.set(status=499)
                    raise
                except Exception:
                    operation.set(status=500)
                    raise
            if request.method == "POST":
                await asyncio.to_thread(flush)
            return response
        finally:
            request_reference.reset(token)

    @app.post("/api/diagnostics", status_code=204)
    async def browser_failure(body: BrowserFailure) -> Response:
        with span(
            "browser.failure",
            failed_request_id=body.request_id,
            operation=body.operation,
            failure=body.failure,
            status=body.status,
            untrusted=True,
        ):
            pass
        return Response(status_code=204)

    assets = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=assets), name="static")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(assets / "index.html")

    def machine(identifier: UUID) -> Machine:
        try:
            return store.get(identifier)
        except KeyError:
            raise HTTPException(404, "Machine not found.") from None

    @app.get("/api/machines/{identifier}")
    def get_machine(identifier: UUID) -> Machine:
        return machine(identifier)

    @app.post("/api/machines", status_code=201)
    async def create(body: Create) -> dict[str, Any]:
        if not body.public_acknowledged:
            raise HTTPException(422, "Acknowledge the public record before creating.")
        if gate.locked():
            raise HTTPException(
                429,
                "Another operation is running. Try again shortly.",
                headers={"X-Game-Outcome": "busy"},
            )
        async with gate:
            if not store.reserve(daily_limit):
                raise HTTPException(
                    429,
                    "The daily generation quota is exhausted.",
                    headers={"X-Game-Outcome": "daily_quota"},
                )
            with match_context(telemetry), span("machine.create") as operation:
                try:
                    operation.set(stage="generation")
                    blueprint = await builder.generate(body.strategy)
                    operation.set(stage="sample_validation")
                    await asyncio.to_thread(sandbox.validate, blueprint)
                    result = Machine.create(
                        body.name,
                        body.strategy,
                        blueprint,
                        public_listing=body.public_listing,
                    )
                    if body.preview:
                        operation.set(stage="store_machine")
                        store.put(result)
                        operation.set(stage="complete", machine_id=str(result.id))
                        return {"machine": result}
                    trial = await asyncio.to_thread(tournament, sandbox, result)
                    store.put(result)
                    replay = store.replay(
                        {
                            "kind": "tournament",
                            "machine": result.model_dump(mode="json"),
                            "result": trial,
                            "trace_id": operation.trace_id,
                        }
                    )
                    operation.set(machine_id=str(result.id), replay_id=str(replay))
                    return {"machine": result, "replay_id": replay, "result": trial}
                except TimeoutError:
                    raise HTTPException(
                        504,
                        "Building your player took too long. "
                        "Your description is still here. Try again shortly.",
                    ) from None
                except Exception:
                    raise HTTPException(
                        502,
                        "Machine creation failed. Revise your rules "
                        "or try again later.",
                    ) from None

    @app.post("/api/tournaments", status_code=201)
    async def run_tournament(body: TournamentRequest) -> dict[str, Any]:
        player = machine(body.machine_id)
        if gate.locked():
            raise HTTPException(
                429,
                "Another game is running. Try again shortly.",
                headers={"X-Game-Outcome": "busy"},
            )
        async with gate:
            if not store.reserve_challenge(daily_limit * 20):
                raise HTTPException(
                    429,
                    "The daily game allowance is exhausted.",
                    headers={"X-Game-Outcome": "daily_quota"},
                )
            with match_context(telemetry), span("machine.tournament") as operation:
                try:
                    result = await asyncio.to_thread(tournament, sandbox, player)
                    replay = store.replay(
                        {
                            "kind": "tournament",
                            "machine": player.model_dump(mode="json"),
                            "result": result,
                            "trace_id": operation.trace_id,
                        }
                    )
                    operation.set(machine_id=str(player.id), replay_id=str(replay))
                    return {"machine": player, "replay_id": replay, "result": result}
                except Exception:
                    raise HTTPException(
                        422,
                        "Your player stopped during the tournament. "
                        "No completed result was recorded.",
                    ) from None

    @app.get("/api/arena")
    def recent_arena(
        offset: Annotated[int, Query(ge=0, le=100000)] = 0,
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
    ) -> dict[str, Any]:
        return store.arena_games(offset=offset, limit=limit)

    @app.post("/api/arena", status_code=201)
    async def enter_arena(body: ArenaRequest) -> dict[str, Any]:
        player = machine(body.machine_id)
        saved = store.arena_entry(player.id)
        if saved is not None:
            return saved
        if gate.locked():
            raise HTTPException(
                429,
                "Another game is running. Try again shortly.",
                headers={"X-Game-Outcome": "busy"},
            )
        async with gate:
            if not store.reserve_challenge(daily_limit * 20):
                raise HTTPException(
                    429,
                    "The daily game allowance is exhausted.",
                    headers={"X-Game-Outcome": "daily_quota"},
                )
            with (
                match_context(telemetry),
                span("machine.arena", machine_id=str(player.id)) as operation,
            ):
                try:
                    operation.set(stage="select_opponents")
                    opponents = store.arena_opponents(player.id)
                    operation.set(stage="execution", opponent_count=len(opponents))
                    result = await asyncio.to_thread(arena, sandbox, player, opponents)
                    data = {
                        "kind": "arena",
                        "machine": player.model_dump(mode="json"),
                        "result": result,
                        "trace_id": operation.trace_id,
                    }
                    operation.set(stage="store_replay")
                    replay_id = store.replay(data)
                    operation.set(
                        machine_id=str(player.id),
                        replay_id=str(replay_id),
                        stage="complete",
                        completed=True,
                        referred=body.referral is not None,
                    )
                    return {"replay_id": replay_id, **data}
                except Exception:
                    raise HTTPException(
                        422,
                        "A player stopped during the arena. "
                        "No completed result was recorded. Try again later.",
                    ) from None

    @app.post("/api/events", status_code=204)
    async def funnel_event(body: FunnelEvent) -> Response:
        # Collect only a bounded event name and an existing replay reference.
        try:
            store.read(body.replay_id)
        except KeyError:
            raise HTTPException(404, "Replay not found.") from None
        with (
            match_context(telemetry),
            span("game.funnel", event=body.event, replay_id=str(body.replay_id)),
        ):
            pass
        return Response(status_code=204)

    @app.post("/api/challenges", status_code=201)
    async def challenge(body: Challenge) -> dict[str, Any]:
        left, right = machine(body.left), machine(body.right)
        if gate.locked():
            raise HTTPException(
                429,
                "Another operation is running. Try again shortly.",
                headers={"X-Game-Outcome": "busy"},
            )
        async with gate:
            if not store.reserve_challenge(daily_limit * 20):
                raise HTTPException(
                    429,
                    "The daily challenge quota is exhausted.",
                    headers={"X-Game-Outcome": "daily_quota"},
                )
            with match_context(telemetry), span("machine.challenge") as operation:
                try:
                    result = await asyncio.to_thread(
                        play, sandbox, left.blueprint, right.blueprint
                    )
                    replay = store.replay(
                        {
                            "kind": "challenge",
                            "machines": [
                                left.model_dump(mode="json"),
                                right.model_dump(mode="json"),
                            ],
                            "result": result,
                            "trace_id": operation.trace_id,
                        }
                    )
                    operation.set(
                        stage="complete",
                        completed=True,
                        referred=body.referral is not None,
                        replay_id=str(replay),
                    )
                    return {"replay_id": replay, "result": result}
                except Exception:
                    raise HTTPException(
                        422,
                        "A machine failed during this challenge. "
                        "No completed result was recorded.",
                    ) from None

    @app.get("/api/leaderboard")
    def leaderboard(
        offset: Annotated[int, Query(ge=0, le=100000)] = 0,
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
    ) -> dict[str, Any]:
        return store.public_games(ranked=True, offset=offset, limit=limit)

    @app.get("/api/games")
    def games(
        offset: Annotated[int, Query(ge=0, le=100000)] = 0,
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
    ) -> dict[str, Any]:
        return store.public_games(ranked=False, offset=offset, limit=limit)

    @app.get("/api/replays/{identifier}")
    def replay(identifier: UUID) -> dict[str, Any]:
        try:
            return inspect_link(
                store.read(identifier), logfire_project_url, public_trace_urls
            )
        except KeyError:
            raise HTTPException(404, "Replay not found.") from None

    return app


def hosted() -> FastAPI:
    """Fail before serving when required operator configuration is missing."""
    required = ("LOGFIRE_TOKEN", "OPENAI_API_KEY", "PYLEMMA_DAILY_GENERATIONS")
    if any(not os.environ.get(key) for key in required):
        raise RuntimeError(
            "Set LOGFIRE_TOKEN, OPENAI_API_KEY, "
            "and PYLEMMA_DAILY_GENERATIONS before serving."
        )
    quota = int(os.environ["PYLEMMA_DAILY_GENERATIONS"])
    if quota < 1:
        raise ValueError("The generation quota must be positive.")
    store_url = os.environ.get("PYLEMMA_STORE_URL")
    store: MachineStore | RemoteMachineStore
    if store_url:
        store = RemoteMachineStore(store_url, os.environ["PYLEMMA_STORE_TOKEN"])
    else:
        store = MachineStore(
            Path(os.environ.get("PYLEMMA_DATABASE", "machines.sqlite3"))
        )
    return create_app(
        store,
        Generator(os.environ["OPENAI_API_KEY"]),
        configure(),
        quota,
        logfire_project_url=os.environ.get("PYLEMMA_LOGFIRE_PROJECT_URL"),
    )
