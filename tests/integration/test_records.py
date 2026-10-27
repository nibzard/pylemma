"""Exercise SQLite boundaries using private local files and no network access."""

import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from threading import Barrier
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pylemma.game.models import Decision, MatchSettings
from pylemma.game.opponents import decide
from pylemma.game.rules import Choice
from pylemma.records import sqlite as storage
from pylemma.records.models import AttemptRecord, Observation, Replay, RoundRecord
from pylemma.records.sqlite import MatchStore, RecordConsistencyError, migrate

NOW = datetime(2026, 10, 27, tzinfo=UTC)


def settings(**changes: Any) -> MatchSettings:
    values: dict[str, Any] = dict(
        match_id=uuid4(),
        strategy="Cooperate.",
        strategy_hash=sha256(b"Cooperate.").hexdigest(),
        opponent_id="optimist",
        opponent_version="optimist-v1",
        provider="fake",
        model_id="fake-v1",
        model_settings_json='{"temperature":0}',
        system_prompt_version="system-v1",
        notice_version="notice-v1",
        application_version="test-revision",
        created_at=NOW,
    )
    values.update(changes)
    return MatchSettings(**values)


@pytest.fixture
def database(tmp_path: Path) -> Path:
    # pytest owns and removes these local files. No external resource is created.
    return tmp_path / f"{os.environ.get('LOOPER_RESOURCE_PREFIX', 'local')}.sqlite3"


@pytest.fixture
def store(database: Path) -> MatchStore:
    migrate(database)
    return MatchStore(database)


def start(store: MatchStore, **changes: Any) -> Replay:
    replay = store.create(settings(**changes))
    return store.transition(
        replay.match.settings.match_id, "running", at=NOW, trace_id="match-trace"
    )


def attempt(replay: Replay, **changes: Any) -> AttemptRecord:
    values: dict[str, Any] = dict(
        match_id=replay.match.settings.match_id,
        round_number=len(replay.rounds) + 1,
        attempt_number=1,
        status="succeeded",
        model_settings_json='{"temperature":0}',
        started_at=replay.updated_at,
        completed_at=replay.updated_at + timedelta(seconds=1),
        trace_id="match-trace",
        span_id="request-span",
    )
    values.update(changes)
    return AttemptRecord(**values)


def prepare_round(
    store: MatchStore, replay: Replay, player: Choice = "cooperate"
) -> RoundRecord:
    request = attempt(replay)
    store.record_attempt(request)
    outcome = replay.match.resolve(
        len(replay.rounds) + 1,
        Decision(choice=player, stated_reason="A fixed test decision."),
        decide(replay.match.settings.opponent_version, replay.match.history),
    ).outcomes[-1]
    return RoundRecord(
        match_id=replay.match.settings.match_id,
        observation=Observation.from_match(replay.match),
        outcome=outcome,
        player_points=outcome.player_points,
        opponent_points=outcome.opponent_points,
        player_total=replay.match.player_total + outcome.player_points,
        opponent_total=replay.match.opponent_total + outcome.opponent_points,
        started_at=request.started_at,
        completed_at=request.completed_at,
        trace_id="match-trace",
        span_id="round-span",
        attempt_count=1,
    )


def test_migrations_repeat_and_upgrade(database: Path) -> None:
    directory = files("pylemma.records").joinpath("migrations")
    first = directory.joinpath("001_matches.sql")
    with sqlite3.connect(database) as connection:
        connection.executescript(first.read_text())
        connection.execute(
            "CREATE TABLE schema_migrations "
            "(version INTEGER PRIMARY KEY, name TEXT, digest TEXT)"
        )
        connection.execute(
            "INSERT INTO schema_migrations VALUES (1, ?, ?)",
            (first.name, sha256(first.read_bytes()).hexdigest()),
        )
    store = MatchStore(database)
    # Version one already has match records. The upgrade must preserve them.
    initial = settings()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO matches (match_id, settings_json, status, created_at, "
            "updated_at) VALUES (?, ?, 'pending', ?, ?)",
            (
                str(initial.match_id),
                initial.model_dump_json(),
                NOW.isoformat(),
                NOW.isoformat(),
            ),
        )
    migrate(database)
    migrate(database)
    assert store.read(initial.match_id).match.settings == initial
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("wal",)
        assert connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall() == [(1,), (2,)]
        connection.execute(
            "UPDATE schema_migrations SET digest='changed' WHERE version=1"
        )
    with pytest.raises(RecordConsistencyError, match="Migration history"):
        migrate(database)


def test_migration_failure_rolls_back_all_sql(
    database: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "package"
    directory = root / "migrations"
    directory.mkdir(parents=True)
    (directory / "001_first.sql").write_text("CREATE TABLE first (value TEXT);\n")
    (directory / "002_broken.sql").write_text(
        "CREATE TABLE second (value TEXT);\nINVALID SQL;\n"
    )
    monkeypatch.setattr(storage, "files", lambda _: root)
    with pytest.raises(sqlite3.OperationalError):
        migrate(database)
    with sqlite3.connect(database) as connection:
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            == []
        )
    (directory / "002_broken.sql").write_text("CREATE TABLE second (value TEXT);\n")
    migrate(database)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT count(*) FROM schema_migrations"
        ).fetchone() == (2,)


@pytest.mark.parametrize(
    "player,opponent,totals",
    [
        ("cooperate", "optimist", (30, 30)),
        ("betray", "optimist", (50, 0)),
        ("cooperate", "opportunist", (21, 36)),
        ("betray", "grudge", (14, 9)),
    ],
)
def test_replay_round_trip(
    store: MatchStore,
    player: Choice,
    opponent: str,
    totals: tuple[int, int],
) -> None:
    replay = start(store, opponent_id=opponent, opponent_version=f"{opponent}-v1")
    initial = replay.match.settings
    for _ in range(10):
        record = prepare_round(store, replay, player)
        replay = store.commit_round(record)
        assert replay.rounds[-1] == record
    reopened = MatchStore(store.path).read(initial.match_id)
    assert reopened == replay
    assert reopened.match.settings == initial
    assert (reopened.match.player_total, reopened.match.opponent_total) == totals
    assert reopened.match.combined_total == sum(totals)
    assert reopened.match.status == "completed"
    assert reopened.match.winner is not None
    assert reopened.completed_at == NOW + timedelta(seconds=10)
    assert len(reopened.attempts) == 10
    assert reopened.rounds[0].input_tokens is None
    assert reopened.rounds[0].estimated_cost_usd is None
    assert (
        json.loads(reopened.rounds[0].model_dump_json())["estimated_cost_usd"] is None
    )
    assert reopened.public_trace_url is None
    assert reopened.trace_id == "match-trace"
    observation = reopened.rounds[1].observation.model_dump_json()
    assert "stated_reason" not in observation
    assert "strategy" not in observation
    assert reopened.rounds[1].observation.opponent_history() == replay.match.history[:1]
    with pytest.raises(ValueError):
        store.transition(initial.match_id, "running", at=reopened.updated_at)


def test_duplicate_round_and_atomic_rollback(store: MatchStore) -> None:
    replay = start(store)
    record = prepare_round(store, replay)
    before = store.read(record.match_id)
    with sqlite3.connect(store.path) as connection:
        connection.executescript("""
            CREATE TRIGGER fail_progress BEFORE UPDATE ON matches
            WHEN NEW.completed_rounds > OLD.completed_rounds
            BEGIN SELECT RAISE(ABORT, 'injected failure'); END;
        """)
    with pytest.raises(sqlite3.IntegrityError, match="injected failure"):
        store.commit_round(record)
    assert store.read(record.match_id) == before
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT count(*) FROM rounds").fetchone() == (0,)
        connection.execute("DROP TRIGGER fail_progress")
    committed = store.commit_round(record)
    with pytest.raises(ValueError, match="next round"):
        store.commit_round(record)
    with sqlite3.connect(store.path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO rounds VALUES (?, 1, ?)",
                (str(record.match_id), record.model_dump_json()),
            )
    assert store.read(record.match_id) == committed


def test_concurrent_duplicate_round(store: MatchStore) -> None:
    record = prepare_round(store, start(store))
    barrier = Barrier(2)

    def commit() -> bool:
        barrier.wait(timeout=5)
        try:
            MatchStore(store.path).commit_round(record)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(commit) for _ in range(2)]
        assert sorted(f.result() for f in futures) == [False, True]
    assert len(store.read(record.match_id).rounds) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("player_total", 99),
        ("player_points", 99),
        ("attempt_count", 2),
        ("input_tokens", 0),
    ],
)
def test_inconsistent_round_rejected(store: MatchStore, field: str, value: int) -> None:
    record = prepare_round(store, start(store))
    before = store.read(record.match_id)
    data = record.model_dump(mode="json")
    data[field] = value
    invalid = RoundRecord.model_validate_json(json.dumps(data))
    with pytest.raises(RecordConsistencyError):
        store.commit_round(invalid)
    assert store.read(record.match_id) == before


def test_corrupted_observation_and_totals_rejected(store: MatchStore) -> None:
    record = prepare_round(store, start(store))
    data = record.model_dump(mode="json")
    data["observation"]["opponent"]["description"] = "Altered policy."
    with pytest.raises(RecordConsistencyError):
        store.commit_round(RoundRecord.model_validate_json(json.dumps(data)))
    store.commit_round(record)
    data = record.model_dump(mode="json")
    data["opponent_total"] = 99
    with sqlite3.connect(store.path) as connection:
        connection.execute("UPDATE rounds SET record_json=?", (json.dumps(data),))
    with pytest.raises(RecordConsistencyError):
        store.read(record.match_id)


def test_failed_match_keeps_attempts_and_completed_rounds(store: MatchStore) -> None:
    replay = store.commit_round(prepare_round(store, start(store)))
    failed = attempt(replay, status="failed", error_category="timeout")
    replay = store.record_attempt(failed)
    assert len(replay.rounds) == 1
    assert replay.match.player_total == 3
    replay = store.transition(
        failed.match_id, "failed", at=failed.completed_at, error_category="timeout"
    )
    assert replay.match.winner is None
    assert replay.error_category == "timeout"
    assert replay.attempts[-1] == failed
    with pytest.raises(ValueError):
        store.record_attempt(attempt(replay, attempt_number=2))
    assert store.read(failed.match_id) == replay


@pytest.mark.parametrize("unknown", [False, True])
def test_retry_usage_aggregates(store: MatchStore, unknown: bool) -> None:
    replay = start(store)
    failed = attempt(
        replay,
        status="failed",
        error_category="invalid_decision",
        input_tokens=None if unknown else 4,
        output_tokens=2,
        estimated_cost_usd=None if unknown else Decimal("0.001"),
        cost_basis="Fixture price per token.",
    )
    retried = store.record_attempt(failed)
    success = attempt(
        retried,
        attempt_number=2,
        input_tokens=5,
        output_tokens=3,
        estimated_cost_usd=Decimal("0.002"),
        cost_basis="Fixture price per token.",
    )
    store.record_attempt(success)
    outcome = replay.match.resolve(
        1,
        Decision(choice="cooperate", stated_reason="Test."),
        decide("optimist-v1", ()),
    ).outcomes[0]
    record = RoundRecord(
        match_id=success.match_id,
        observation=Observation.from_match(replay.match),
        outcome=outcome,
        player_points=3,
        opponent_points=3,
        player_total=3,
        opponent_total=3,
        started_at=failed.started_at,
        completed_at=success.completed_at,
        attempt_count=2,
        input_tokens=None if unknown else 9,
        output_tokens=5,
        estimated_cost_usd=None if unknown else Decimal("0.003"),
    )
    assert store.commit_round(record).rounds == (record,)
    with pytest.raises(ValueError):
        store.record_attempt(success)


def test_rematch_and_invalid_state_boundaries(store: MatchStore) -> None:
    original = store.create(settings())
    with pytest.raises(ValueError):
        store.record_attempt(attempt(original))
    child = store.create(settings(parent_match_id=original.match.settings.match_id))
    assert child.match.settings.match_id != original.match.settings.match_id
    with pytest.raises(sqlite3.IntegrityError):
        store.create(settings(parent_match_id=uuid4()))
    with pytest.raises(sqlite3.IntegrityError):
        store.create(original.match.settings)
    stopped = store.transition(
        original.match.settings.match_id,
        "interrupted",
        at=NOW,
        error_category="interrupted",
    )
    assert stopped.started_at is None
    assert stopped.match.player_total == 0
    assert stopped.match.winner is None
    with pytest.raises(ValueError):
        store.transition(stopped.match.settings.match_id, "running", at=NOW)
    with pytest.raises(KeyError):
        store.read(uuid4())


def test_read_does_not_write_or_require_trace_access(store: MatchStore) -> None:
    replay = store.commit_round(prepare_round(store, start(store)))
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE matches SET trace_id=NULL, "
            "public_trace_url='https://unavailable.invalid/trace'"
        )
        before = tuple(connection.iterdump())
    for _ in range(3):
        read = store.read(replay.match.settings.match_id)
        assert read.rounds == replay.rounds
        assert read.trace_id is None
    with sqlite3.connect(store.path) as connection:
        assert tuple(connection.iterdump()) == before


@pytest.mark.parametrize(
    "changes",
    [
        {"input_tokens": -1},
        {"output_tokens": True},
        {"estimated_cost_usd": Decimal("NaN")},
        {"estimated_cost_usd": Decimal("0")},
        {"attempt_number": 3},
        {"started_at": datetime(2026, 10, 27)},
        {"completed_at": NOW - timedelta(seconds=1)},
        {"model_settings_json": '{"temperature":NaN}'},
        {"model_settings_json": "[]"},
        {"error_category": "raw secret"},
        {"status": "failed"},
        {"unknown": "field"},
    ],
)
def test_attempt_boundary_rejects_invalid_values(
    store: MatchStore,
    changes: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        attempt(start(store), **changes)


def test_attempt_order_and_round_order(store: MatchStore) -> None:
    replay = start(store)
    with pytest.raises(ValueError, match="Attempt order"):
        store.record_attempt(attempt(replay, attempt_number=2))
    with pytest.raises(ValueError, match="next running round"):
        store.record_attempt(attempt(replay, round_number=2))
    success = attempt(replay)
    stored = store.record_attempt(success)
    with pytest.raises(ValueError, match="Attempt order"):
        store.record_attempt(attempt(stored, attempt_number=2))
    assert store.read(success.match_id) == stored


@pytest.mark.parametrize(
    "table,column,value",
    [
        ("rounds", "round_number", 2),
        ("attempts", "attempt_number", 2),
        ("matches", "completed_rounds", 2),
    ],
)
def test_replay_rejects_corrupted_progress(
    store: MatchStore,
    table: str,
    column: str,
    value: int,
) -> None:
    replay = store.commit_round(prepare_round(store, start(store)))
    with sqlite3.connect(store.path) as connection:
        # The identifiers come only from the fixed test parameter list.
        connection.execute(f"UPDATE {table} SET {column}=?", (value,))
    with pytest.raises(RecordConsistencyError):
        store.read(replay.match.settings.match_id)


def test_storage_releases_locks_between_requests(store: MatchStore) -> None:
    replay = start(store)
    # This independent writer stands for unrelated work during a model request.
    with sqlite3.connect(store.path, timeout=0) as connection:
        connection.execute("BEGIN IMMEDIATE")
        assert connection.execute("SELECT status FROM matches").fetchone() == (
            "running",
        )
    request = attempt(replay)
    store.record_attempt(request)
    with sqlite3.connect(store.path, timeout=0) as connection:
        connection.execute("BEGIN IMMEDIATE")
        assert connection.execute("SELECT count(*) FROM attempts").fetchone() == (1,)


def test_read_missing_database_does_not_create_file(database: Path) -> None:
    with pytest.raises(sqlite3.OperationalError):
        MatchStore(database).read(uuid4())
    assert not database.exists()
