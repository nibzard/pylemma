"""Required hosted configuration and bounded machine operations."""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Protocol
from uuid import UUID

import logfire
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from pylemma.generator import Generator
from pylemma.machine_store import MachineStore
from pylemma.machines import Blueprint, Machine, Sandbox, play, tournament
from pylemma.telemetry import configure, match_context, span


class Builder(Protocol):
    async def generate(self, strategy: str) -> Blueprint: ...
    async def close(self) -> None: ...


class Create(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: Annotated[str, Field(min_length=1, max_length=60)]
    strategy: Annotated[str, Field(min_length=1, max_length=1000)]
    public_acknowledged: bool


class Challenge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    left: UUID
    right: UUID


def create_app(
    store: MachineStore, builder: Builder, telemetry: logfire.Logfire, daily_limit: int
) -> FastAPI:
    """Explicit dependencies allow offline tests without weakening hosted startup."""
    if telemetry is None or daily_limit < 1:
        raise ValueError("Configure Logfire and a positive generation quota.")
    sandbox = Sandbox()
    gate = asyncio.Lock()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            sandbox.close()
            await builder.close()

    app = FastAPI(lifespan=lifespan)
    assets = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=assets), name="static")

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
            raise HTTPException(429, "Another operation is running. Try again shortly.")
        async with gate:
            if not store.reserve(daily_limit):
                raise HTTPException(429, "The daily generation quota is exhausted.")
            with match_context(telemetry), span("machine.create") as operation:
                try:
                    blueprint = await builder.generate(body.strategy)
                    await asyncio.to_thread(sandbox.validate, blueprint)
                    result = Machine.create(body.name, body.strategy, blueprint)
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
                except Exception:
                    raise HTTPException(
                        502,
                        "Machine creation failed. Revise your rules "
                        "or try again later.",
                    ) from None

    @app.post("/api/challenges", status_code=201)
    async def challenge(body: Challenge) -> dict[str, Any]:
        left, right = machine(body.left), machine(body.right)
        if gate.locked():
            raise HTTPException(429, "Another operation is running. Try again shortly.")
        async with gate:
            if not store.reserve_challenge(daily_limit * 20):
                raise HTTPException(429, "The daily challenge quota is exhausted.")
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
                    return {"replay_id": replay, "result": result}
                except Exception:
                    raise HTTPException(
                        422,
                        "A machine failed during this challenge. "
                        "No completed result was recorded.",
                    ) from None

    @app.get("/api/replays/{identifier}")
    def replay(identifier: UUID) -> dict[str, Any]:
        try:
            return store.read(identifier)
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
    return create_app(
        MachineStore(Path(os.environ.get("PYLEMMA_DATABASE", "machines.sqlite3"))),
        Generator(os.environ["OPENAI_API_KEY"]),
        configure(),
        quota,
    )
