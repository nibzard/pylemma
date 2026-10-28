"""Offline tests for durable records across the container boundary."""

import json
from uuid import uuid4

import httpx
import pytest

from pylemma.machines import Machine, presets
from pylemma.remote_store import RemoteMachineStore


def test_remote_contracts_and_authentication() -> None:
    records: dict[str, object] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer synthetic-token"
        body = json.loads(request.content)
        if body["operation"] == "public_games":
            return httpx.Response(
                200, json={"entries": [], "total": 0, "next_offset": None}
            )
        if body["operation"] == "reserve":
            return httpx.Response(200, json=True)
        key = body["kind"] + ":" + body["id"]
        if body["operation"] == "put":
            records[key] = body["data"]
            return httpx.Response(200, json=True)
        if key not in records:
            return httpx.Response(404, json=None)
        return httpx.Response(200, json=records[key])

    store = RemoteMachineStore(
        "https://example.test",
        "synthetic-token",
        transport=httpx.MockTransport(respond),
    )
    try:
        assert store.public_games(ranked=True)["total"] == 0
        assert store.reserve(20)
        assert store.reserve_challenge(400)
        machine = Machine.create("Trust", "Always cooperate", presets()[0])
        store.put(machine)
        assert store.get(machine.id) == machine
        identifier = store.replay({"trace_id": "example", "result": {"total": 81}})
        assert store.read(identifier)["result"]["total"] == 81
        with pytest.raises(KeyError):
            store.get(uuid4())
    finally:
        store.close()


def test_remote_arena_operations() -> None:
    machine = Machine.create("Public", "Cooperate", presets()[0], public_listing=True)
    calls = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body)
        if body["operation"] == "arena_entry":
            return httpx.Response(404, json=None)
        if body["operation"] == "arena_opponents":
            return httpx.Response(200, json=[machine.model_dump(mode="json")])
        return httpx.Response(
            200, json={"entries": [], "total": 0, "next_offset": None}
        )

    store = RemoteMachineStore(
        "https://example.test", "synthetic", transport=httpx.MockTransport(respond)
    )
    try:
        assert store.arena_entry(machine.id) is None
        assert store.arena_opponents(machine.id) == [machine]
        assert store.arena_games()["total"] == 0
        assert [body["operation"] for body in calls] == [
            "arena_entry",
            "arena_opponents",
            "arena_games",
        ]
    finally:
        store.close()
