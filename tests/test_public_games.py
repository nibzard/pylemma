"""Public rankings preserve consent, comparable scores, and stored-only reads."""

from pathlib import Path
from typing import Any

import logfire
from fastapi.testclient import TestClient

from pylemma.machine_store import MachineStore
from pylemma.machines import Blueprint, Machine, Sandbox, presets, tournament
from pylemma.web.app import create_app


def test_old_records_and_partial_or_other_suites_stay_unlisted(tmp_path: Path) -> None:
    store = MachineStore(tmp_path / "games.sqlite3")
    sandbox = Sandbox()
    try:
        player = Machine.create("Trust", "Cooperate", presets()[0], public_listing=True)
        result = tournament(sandbox, player)
    finally:
        sandbox.close()
    public = {
        "kind": "tournament",
        "machine": player.model_dump(mode="json"),
        "result": result,
    }
    a = store.replay(public)
    b = store.replay(public)
    old = player.model_dump(mode="json")
    del old["public_listing"]
    unlisted = store.replay({**public, "machine": old})
    store.replay({**public, "result": {**result, "suite_version": "future-v1"}})
    store.replay({**public, "result": {**result, "matches": []}})
    page = store.public_games(ranked=True, limit=1)
    assert page["total"] == 2
    assert page["entries"][0]["rank"] == 1
    assert page["next_offset"] == 1
    second = store.public_games(ranked=True, offset=1, limit=1)
    assert second["entries"][0]["rank"] == 1
    assert second["next_offset"] is None
    assert {row["replay_id"] for row in page["entries"] + second["entries"]} == {
        str(a),
        str(b),
    }
    assert store.read(unlisted)["machine"]["name"] == "Trust"
    assert "created_at" not in public


class Builder:
    calls = 0

    async def generate(self, strategy: str) -> Blueprint:
        self.calls += 1
        return presets()[0]

    async def close(self) -> None:
        pass


def test_public_api_indexes_only_completed_consented_games(tmp_path: Path) -> None:
    store = MachineStore(tmp_path / "public.sqlite3")
    builder = Builder()
    telemetry = logfire.configure(send_to_logfire=False, console=False, local=True)
    with TestClient(create_app(store, builder, telemetry, 5)) as client:

        def create(listed: bool) -> dict[str, Any]:
            response = client.post(
                "/api/machines",
                json={
                    "name": "Trust",
                    "strategy": "Cooperate",
                    "preview": True,
                    "public_acknowledged": True,
                    "public_listing": listed,
                },
            )
            assert response.status_code == 201
            machine: dict[str, Any] = response.json()["machine"]
            return machine

        private = create(False)
        public = create(True)
        assert public["public_listing"] is True
        assert client.get("/api/leaderboard").json()["total"] == 0
        result = client.post("/api/tournaments", json={"machine_id": public["id"]})
        assert result.status_code == 201
        page = client.get("/api/leaderboard").json()
        assert page["total"] == 1
        assert page["entries"][0]["scores"] == [81]
        assert page["entries"][0]["replay_id"] == result.json()["replay_id"]
        assert "strategy" not in page["entries"][0]
        client.post(
            "/api/challenges", json={"left": public["id"], "right": private["id"]}
        )
        assert client.get("/api/games").json()["total"] == 1
        challenge = client.post(
            "/api/challenges", json={"left": public["id"], "right": public["id"]}
        )
        assert challenge.status_code == 201
        assert client.get("/api/games").json()["total"] == 2
        assert client.get("/api/leaderboard").json()["total"] == 1
        assert client.get("/api/leaderboard?limit=1000").status_code == 422
        assert client.get("/api/games?offset=-1").status_code == 422
        assert client.get("/api/games?offset=100").json()["entries"] == []
        assert builder.calls == 2
