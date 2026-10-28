"""Short SQLite transactions for immutable machines and completed replay records."""

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pylemma.machines import Machine
from pylemma.public_games import entry, page, timestamp
from pylemma.records.links import validate_public_url


class MachineStore:
    """Store only completed results; a failed execution never becomes a replay."""

    def __init__(self, path: Path):
        self.path = path
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS machines (
                    id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS machine_replays (
                    id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS arena_entries (
                    machine_id TEXT PRIMARY KEY, replay_id TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS challenge_slots (
                    id INTEGER PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS generation_slots (
                    id INTEGER PRIMARY KEY, created TEXT DEFAULT CURRENT_TIMESTAMP);
            """)

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=5)

    def reserve(self, daily_limit: int) -> bool:
        """Reserve before generation; failed requests retain their reservation."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute(
                "SELECT count(*) FROM generation_slots WHERE date(created)=date('now')"
            ).fetchone()[0]
            if count >= daily_limit:
                return False
            db.execute("INSERT INTO generation_slots DEFAULT VALUES")
            return True

    def reserve_challenge(self, daily_limit: int) -> bool:
        """Bound challenge execution separately from paid generation."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute(
                "SELECT count(*) FROM challenge_slots WHERE date(created)=date('now')"
            ).fetchone()[0]
            if count >= daily_limit:
                return False
            db.execute("INSERT INTO challenge_slots DEFAULT VALUES")
            return True

    def put(self, machine: Machine) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO machines VALUES (?, ?)",
                (str(machine.id), machine.model_dump_json()),
            )

    def get(self, identifier: UUID) -> Machine:
        with self.connect() as db:
            row = db.execute(
                "SELECT data FROM machines WHERE id=?", (str(identifier),)
            ).fetchone()
        if row is None:
            raise KeyError(identifier)
        return Machine.model_validate_json(row[0])

    def replay(self, data: dict[str, Any]) -> UUID:
        identifier = uuid4()
        data = {"created_at": timestamp(), **data}
        with self.connect() as db:
            if data.get("kind") == "arena":
                db.execute(
                    "INSERT INTO arena_entries VALUES (?, ?)",
                    (data["machine"]["id"], str(identifier)),
                )
            db.execute(
                "INSERT INTO machine_replays VALUES (?, ?)",
                (str(identifier), json.dumps(data)),
            )
        return identifier

    def read(self, identifier: UUID) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute(
                "SELECT data FROM machine_replays WHERE id=?", (str(identifier),)
            ).fetchone()
        if row is None:
            raise KeyError(identifier)
        result: dict[str, Any] = json.loads(row[0])
        return result

    def review(self, identifier: UUID, url: str | None) -> None:
        """Record a reviewed link; this operation never publishes remote data."""
        if url is not None:
            url = validate_public_url(url)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT data FROM machine_replays WHERE id=?", (str(identifier),)
            ).fetchone()
            if row is None:
                raise KeyError(identifier)
            data = json.loads(row[0])
            data["public_trace_url"] = url
            db.execute(
                "UPDATE machine_replays SET data=? WHERE id=?",
                (json.dumps(data), str(identifier)),
            )

    def public_games(
        self, *, ranked: bool, offset: int = 0, limit: int = 20
    ) -> dict[str, Any]:
        """Read public summaries without running a game or requesting a model."""
        with self.connect() as db:
            records = db.execute("SELECT id, data FROM machine_replays").fetchall()
        entries = []
        for identifier, raw in records:
            summary = entry(identifier, json.loads(raw))
            if summary is not None:
                entries.append(summary)
        return page(entries, ranked, offset, limit)

    def arena_entry(self, identifier: UUID) -> dict[str, Any] | None:
        """Return the completed entry without reserving or executing again."""
        with self.connect() as db:
            row = db.execute(
                "SELECT replay_id FROM arena_entries WHERE machine_id=?",
                (str(identifier),),
            ).fetchone()
        if row is None:
            return None
        return {"replay_id": row[0], **self.read(UUID(row[0]))}

    def arena_opponents(self, identifier: UUID) -> list[Machine]:
        """Use latest completed public games, deduplicated by strategy version."""
        with self.connect() as db:
            records = db.execute("SELECT id, data FROM machine_replays").fetchall()
        summaries = [
            summary
            for key, raw in records
            if (summary := entry(key, json.loads(raw))) is not None
        ]
        ordered = page(summaries, False, 0, len(summaries))["entries"]
        selected: dict[str, Machine] = {}
        for summary in ordered:
            for player in summary["players"]:
                key = player["id"]
                if key == str(identifier) or key in selected:
                    continue
                candidate = self.get(UUID(key))
                if candidate.public_listing:
                    selected[key] = candidate
                if len(selected) == 10:
                    return list(selected.values())
        return list(selected.values())

    def arena_games(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        ranked: bool = False,
        player: str | None = None,
    ) -> dict[str, Any]:
        with self.connect() as db:
            records = db.execute("SELECT id, data FROM machine_replays").fetchall()
        summaries = [
            summary
            for key, raw in records
            if (summary := entry(key, json.loads(raw))) is not None
            and summary["kind"] == "arena"
        ]
        return page(summaries, "arena" if ranked else False, offset, limit, player)
