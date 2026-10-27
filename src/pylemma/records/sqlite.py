"""SQLite storage with short transactions and independent replay reads.

Each operation owns and closes its connection. Never pass a model callback into
storage. Commit attempts before outcomes so failed rounds retain usage records.
Use one application process and a persistent local volume for hosted operation.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from typing import Literal
from uuid import UUID

from pylemma.game.models import Match, MatchSettings
from pylemma.records.links import validate_public_url
from pylemma.records.models import (
    AttemptRecord,
    ErrorCategory,
    Observation,
    Replay,
    RoundRecord,
)


class RecordConsistencyError(ValueError):
    """Stored records disagree. Restore a verified backup before continuing."""


def _apply_sql(connection: sqlite3.Connection, script: str) -> None:
    # executescript commits an existing transaction before executing its input.
    statement = ""
    for line in script.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            connection.execute(statement)
            statement = ""
    if statement.strip():
        raise ValueError("Incomplete migration statement. Check the SQL file.")


def migrate(path: Path) -> None:
    """Apply ordered packaged SQL migrations atomically; reject changed history."""
    migrations = sorted(
        files("pylemma.records").joinpath("migrations").iterdir(),
        key=lambda entry: entry.name,
    )
    connection = sqlite3.connect(path, timeout=5, isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, name TEXT NOT NULL, digest TEXT NOT NULL)"
        )
        applied = connection.execute(
            "SELECT version, name, digest FROM schema_migrations ORDER BY version"
        ).fetchall()
        scripts = [entry for entry in migrations if entry.name.endswith(".sql")]
        expected = [
            (n, entry.name, sha256(entry.read_bytes()).hexdigest())
            for n, entry in enumerate(scripts, 1)
        ]
        if applied != expected[: len(applied)]:
            raise RecordConsistencyError("Migration history differs. Check the schema.")
        for (version, name, digest), entry in zip(expected, scripts, strict=True):
            if not name.startswith(f"{version:03d}_"):
                raise RecordConsistencyError(
                    "Migration order differs. Check filenames."
                )
            if version > len(applied):
                _apply_sql(connection, entry.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations VALUES (?, ?, ?)",
                    (version, name, digest),
                )
        connection.commit()
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.close()


class MatchStore:
    """Store validated changes and read consistent snapshots by match identifier.

    Call migrate explicitly before use. No method lists visitor matches.
    Read methods do not migrate, write, fetch traces, or call a model.
    """

    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def _connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self.path.resolve().as_uri() + "?mode=rw",
            uri=True,
            timeout=5,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA synchronous = FULL")
            if not write:
                connection.execute("PRAGMA query_only = ON")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            connection.commit()
        finally:
            if connection.in_transaction:
                connection.rollback()
            connection.close()

    def create(self, settings: MatchSettings) -> Replay:
        """Persist acceptance as pending. A rematch must reference an existing match."""
        settings = MatchSettings.model_validate(settings)
        with self._connection(write=True) as connection:
            connection.execute(
                "INSERT INTO matches "
                "(match_id, parent_match_id, settings_json, status, created_at, "
                "updated_at) VALUES (?, ?, ?, 'pending', ?, ?)",
                (
                    str(settings.match_id),
                    str(settings.parent_match_id) if settings.parent_match_id else None,
                    settings.model_dump_json(),
                    settings.created_at.isoformat(),
                    settings.created_at.isoformat(),
                ),
            )
            return self._read(connection, settings.match_id)

    def read(self, match_id: UUID) -> Replay:
        """Reconstruct totals and check stored progress in one read transaction."""
        with self._connection() as connection:
            return self._read(connection, match_id)

    def set_public_trace_url(self, match_id: UUID, url: str | None) -> Replay:
        """Record an operator-reviewed link, or remove the local reference.

        This operation does not create, verify, or revoke a remote public link.
        A new link requires a completed match with an execution trace reference.
        """
        if url is not None:
            url = validate_public_url(url)
        with self._connection(write=True) as connection:
            replay = self._read(connection, match_id)
            if url is not None and (
                replay.match.status != "completed" or replay.trace_id is None
            ):
                raise ValueError(
                    "A reviewed link needs a completed traced match. Check the record."
                )
            connection.execute(
                "UPDATE matches SET public_trace_url=? WHERE match_id=?",
                (url, str(match_id)),
            )
            return self._read(connection, match_id)

    def transition(
        self,
        match_id: UUID,
        status: Literal["running", "failed", "interrupted"],
        *,
        at: datetime,
        error_category: ErrorCategory | None = None,
        trace_id: str | None = None,
    ) -> Replay:
        """Persist a legal transition. Completion requires ten committed rounds."""
        with self._connection(write=True) as connection:
            replay = self._read(connection, match_id)
            timestamp = self._timestamp(at, replay.updated_at)
            if status == "running":
                match = replay.match.start()
            elif status == "failed":
                match = replay.match.fail()
            elif status == "interrupted":
                match = replay.match.interrupt()
            else:
                raise ValueError(
                    "Invalid transition. Use running, failed, or interrupted."
                )
            if (status != "running") != (error_category is not None):
                raise ValueError(
                    "Stopped matches need an error category. Check status."
                )
            connection.execute(
                "UPDATE matches SET status=?, updated_at=?, error_category=?, "
                "started_at=?, completed_at=?, trace_id=? WHERE match_id=?",
                (
                    match.status,
                    timestamp,
                    error_category,
                    timestamp
                    if status == "running"
                    else (replay.started_at.isoformat() if replay.started_at else None),
                    None if status == "running" else timestamp,
                    trace_id if trace_id is not None else replay.trace_id,
                    str(match_id),
                ),
            )
            return self._read(connection, match_id)

    def record_attempt(self, attempt: AttemptRecord) -> Replay:
        """Store one finished request without creating an outcome or adding points."""
        attempt = AttemptRecord.model_validate(attempt)
        with self._connection(write=True) as connection:
            replay = self._read(connection, attempt.match_id)
            if (
                replay.match.status != "running"
                or attempt.round_number != len(replay.rounds) + 1
            ):
                raise ValueError(
                    "Attempt needs the next running round. Check progress."
                )
            earlier = [
                a for a in replay.attempts if a.round_number == attempt.round_number
            ]
            if attempt.attempt_number != len(earlier) + 1 or (
                earlier and earlier[-1].status == "succeeded"
            ):
                raise ValueError("Attempt order is invalid. Check previous requests.")
            self._timestamp(attempt.started_at, replay.updated_at)
            connection.execute(
                "INSERT INTO attempts VALUES (?, ?, ?, ?)",
                (
                    str(attempt.match_id),
                    attempt.round_number,
                    attempt.attempt_number,
                    attempt.model_dump_json(),
                ),
            )
            connection.execute(
                "UPDATE matches SET updated_at=? WHERE match_id=?",
                (attempt.completed_at.isoformat(), str(attempt.match_id)),
            )
            return self._read(connection, attempt.match_id)

    def commit_round(self, record: RoundRecord) -> Replay:
        """Commit outcome and progress together; return only after successful commit."""
        record = RoundRecord.model_validate(record)
        with self._connection(write=True) as connection:
            replay = self._read(connection, record.match_id)
            match = replay.match.resolve(
                record.outcome.round_number,
                record.outcome.player,
                record.outcome.opponent,
            )
            self._check_round(replay.match, record, replay.attempts)
            timestamp = self._timestamp(record.completed_at, replay.updated_at)
            connection.execute(
                "INSERT INTO rounds VALUES (?, ?, ?)",
                (
                    str(record.match_id),
                    record.outcome.round_number,
                    record.model_dump_json(),
                ),
            )
            connection.execute(
                "UPDATE matches SET status=?, completed_rounds=?, updated_at=?, "
                "completed_at=? WHERE match_id=?",
                (
                    match.status,
                    len(match.outcomes),
                    timestamp,
                    timestamp if match.status == "completed" else None,
                    str(record.match_id),
                ),
            )
            return self._read(connection, record.match_id)

    @staticmethod
    def _timestamp(at: datetime, previous: datetime) -> str:
        if at.utcoffset() is None or at < previous:
            raise ValueError("Timestamp is invalid. Use an aware time after progress.")
        return at.astimezone(UTC).isoformat()

    @staticmethod
    def _check_round(
        before: Match,
        record: RoundRecord,
        attempts: tuple[AttemptRecord, ...],
    ) -> None:
        after = before.resolve(
            record.outcome.round_number, record.outcome.player, record.outcome.opponent
        )
        relevant = [
            a for a in attempts if a.round_number == record.outcome.round_number
        ]
        if (
            record.match_id != before.settings.match_id
            or record.observation != Observation.from_match(before)
            or (record.player_points, record.opponent_points)
            != (record.outcome.player_points, record.outcome.opponent_points)
            or (record.player_total, record.opponent_total)
            != (after.player_total, after.opponent_total)
        ):
            raise RecordConsistencyError(
                "Round differs from history. Check the record."
            )
        if (
            len(relevant) != record.attempt_count
            or not relevant
            or relevant[-1].status != "succeeded"
            or record.started_at < before.settings.created_at
            or any(
                a.started_at < record.started_at or a.completed_at > record.completed_at
                for a in relevant
            )
        ):
            raise RecordConsistencyError(
                "Round attempts differ. Check request records."
            )
        for field in ("input_tokens", "output_tokens", "estimated_cost_usd"):
            values = [getattr(a, field) for a in relevant]
            expected = None if any(v is None for v in values) else sum(values)
            if getattr(record, field) != expected:
                raise RecordConsistencyError(
                    "Round usage differs. Check request records."
                )

    @classmethod
    def _read(cls, connection: sqlite3.Connection, match_id: UUID) -> Replay:
        row = connection.execute(
            "SELECT * FROM matches WHERE match_id=?", (str(match_id),)
        ).fetchone()
        if row is None:
            raise KeyError(match_id)
        settings = MatchSettings.model_validate_json(row["settings_json"])
        if (
            settings.match_id != match_id
            or row["parent_match_id"]
            != (str(settings.parent_match_id) if settings.parent_match_id else None)
            or row["created_at"] != settings.created_at.isoformat()
        ):
            raise RecordConsistencyError("Match settings differ. Check the record.")
        attempt_rows = connection.execute(
            "SELECT * FROM attempts WHERE match_id=? "
            "ORDER BY round_number, attempt_number",
            (str(match_id),),
        ).fetchall()
        attempts = tuple(
            AttemptRecord.model_validate_json(r["record_json"]) for r in attempt_rows
        )
        for index, (attempt, stored) in enumerate(
            zip(attempts, attempt_rows, strict=True)
        ):
            previous = attempts[index - 1] if index else None
            same_round = previous and previous.round_number == attempt.round_number
            expected_number = (
                previous.attempt_number + 1 if same_round and previous else 1
            )
            if (
                attempt.match_id != match_id
                or attempt.round_number != stored["round_number"]
                or attempt.attempt_number != stored["attempt_number"]
                or attempt.attempt_number != expected_number
                or (same_round and previous and previous.status == "succeeded")
                or attempt.round_number > row["completed_rounds"] + 1
                or row["status"] == "pending"
            ):
                raise RecordConsistencyError(
                    "Attempt order differs. Check the records."
                )
        round_rows = connection.execute(
            "SELECT * FROM rounds WHERE match_id=? ORDER BY round_number",
            (str(match_id),),
        ).fetchall()
        rounds = tuple(
            RoundRecord.model_validate_json(r["record_json"]) for r in round_rows
        )
        for record, stored in zip(rounds, round_rows, strict=True):
            if record.outcome.round_number != stored["round_number"]:
                raise RecordConsistencyError("Round number differs. Check the record.")
        before = Match(settings=settings).start()
        for record in rounds:
            cls._check_round(before, record, attempts)
            before = before.resolve(
                record.outcome.round_number,
                record.outcome.player,
                record.outcome.opponent,
            )
        match = Match(settings=settings, status=row["status"], outcomes=before.outcomes)
        if len(rounds) != row["completed_rounds"]:
            raise RecordConsistencyError("Stored progress differs. Check the outcomes.")
        return Replay(
            match=match,
            rounds=rounds,
            attempts=attempts,
            updated_at=datetime.fromisoformat(row["updated_at"]),
            started_at=datetime.fromisoformat(row["started_at"])
            if row["started_at"]
            else None,
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None,
            error_category=row["error_category"],
            trace_id=row["trace_id"],
            public_trace_url=row["public_trace_url"],
        )
