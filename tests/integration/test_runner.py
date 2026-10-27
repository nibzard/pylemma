"""Exercise real storage and application execution with offline players."""

import asyncio
import os
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest

from pylemma.application.runner import run_match
from pylemma.game import opponents
from pylemma.game.models import Decision, HistoryEntry, MatchSettings
from pylemma.game.rules import Choice
from pylemma.player.service import DecisionResult, FakePlayer, PlayerError
from pylemma.records.models import Observation, Replay, RoundRecord
from pylemma.records.sqlite import MatchStore, migrate


@pytest.fixture
def store(tmp_path: Path) -> MatchStore:
    path = tmp_path / f"{os.environ.get('LOOPER_RESOURCE_PREFIX', 'local')}.sqlite3"
    migrate(path)
    return MatchStore(path)


def create(store: MatchStore, opponent: str = "optimist") -> Replay:
    return store.create(
        MatchSettings.model_validate(
            dict(
                match_id=uuid4(),
                strategy="Private strategy sentinel.",
                strategy_hash=sha256(b"Private strategy sentinel.").hexdigest(),
                opponent_id=opponent,
                opponent_version=f"{opponent}-v1",
                provider="fake",
                model_id="fake-v1",
                model_settings_json="{}",
                system_prompt_version="fake-v1",
                notice_version="notice-v1",
                application_version="test",
                created_at=datetime.now(UTC),
            )
        )
    )


def fake(choice: Choice, count: int = 10) -> FakePlayer:
    return FakePlayer(
        (Decision(choice=choice, stated_reason="Reason sentinel."),) * count
    )


@pytest.mark.parametrize(
    ("choice", "opponent", "totals", "winner"),
    [
        ("cooperate", "optimist", (30, 30), "draw"),
        ("betray", "optimist", (50, 0), "player"),
        ("cooperate", "opportunist", (21, 36), "opponent"),
        ("betray", "grudge", (14, 9), "player"),
    ],
)
def test_reference_matches(
    store: MatchStore,
    choice: Choice,
    opponent: str,
    totals: tuple[int, int],
    winner: str,
) -> None:
    match_id = create(store, opponent).match.settings.match_id
    replay = asyncio.run(run_match(store, match_id, fake(choice)))
    assert replay == MatchStore(store.path).read(match_id)
    assert replay.match.status == "completed"
    assert (replay.match.player_total, replay.match.opponent_total) == totals
    assert replay.match.winner == winner
    assert len(replay.rounds) == len(replay.attempts) == 10
    assert all(a.model_settings_json == "{}" for a in replay.attempts)
    assert all(
        r.input_tokens is None and r.estimated_cost_usd is None for r in replay.rounds
    )
    with pytest.raises(ValueError, match="Cannot change completed"):
        asyncio.run(run_match(store, match_id, fake(choice)))


def test_synthetic_mutual_betrayal_reference(
    store: MatchStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # All published opponents cooperate in round one. This synthetic policy
    # exercises the remaining score reference without adding a public opponent.
    def betray(version: str, history: tuple[HistoryEntry, ...]) -> Decision:
        return Decision(choice="betray", stated_reason="Synthetic test policy.")

    monkeypatch.setattr(opponents, "decide", betray)
    match_id = create(store).match.settings.match_id
    replay = asyncio.run(run_match(store, match_id, fake("betray")))
    assert (replay.match.player_total, replay.match.opponent_total) == (10, 10)
    assert replay.match.winner == "draw"


def test_fixed_observations_and_committed_visibility(
    store: MatchStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    match_id = create(store, "opportunist").match.settings.match_id
    events: list[tuple[str, int]] = []
    original_from_match = Observation.from_match
    original_history = Observation.opponent_history
    original_decide = opponents.decide
    original_commit = store.commit_round

    def observation(cls: type[Observation], match: object) -> Observation:
        from pylemma.game.models import Match

        assert isinstance(match, Match)
        result = original_from_match(match)
        events.append(("observation", result.round_number))
        return result

    def history(self: Observation) -> tuple[HistoryEntry, ...]:
        events.append(("history", self.round_number))
        return original_history(self)

    def opponent(version: str, history: tuple[HistoryEntry, ...]) -> Decision:
        number = len(history) + 1
        assert ("observation", number) in events
        assert ("history", number) in events
        for entry in history:
            assert set(entry.model_dump()) == {
                "round_number",
                "player_choice",
                "opponent_choice",
            }
        events.append(("opponent", number))
        return original_decide(version, history)

    class InspectingPlayer(FakePlayer):
        async def decide(
            self, observation: Observation, strategy: str
        ) -> DecisionResult:
            number = observation.round_number
            assert ("history", number) in events
            assert strategy == "Private strategy sentinel."
            data = observation.model_dump_json()
            assert "sentinel" not in data and "stated_reason" not in data
            assert len(observation.history) == number - 1
            assert all(h.round_number < number for h in observation.history)
            stored = store.read(match_id)
            assert len(stored.rounds) == number - 1
            assert observation.player_total == stored.match.player_total
            assert observation.opponent == next(
                p for p in opponents.POLICIES if p.version == "opportunist-v1"
            )
            # A write lock is available while the player executes.
            with sqlite3.connect(store.path, timeout=0) as connection:
                connection.execute("BEGIN IMMEDIATE")
            return await fake("cooperate").decide(observation, strategy)

    def commit(record: RoundRecord) -> Replay:
        before = store.read(match_id)
        assert len(before.rounds) == record.outcome.round_number - 1
        assert before.match.winner is None
        result = original_commit(record)
        assert store.read(match_id) == result
        return result

    monkeypatch.setattr(Observation, "from_match", classmethod(observation))
    monkeypatch.setattr(Observation, "opponent_history", history)
    monkeypatch.setattr(opponents, "decide", opponent)
    monkeypatch.setattr(store, "commit_round", commit)
    replay = asyncio.run(run_match(store, match_id, InspectingPlayer(())))
    assert len(replay.rounds) == 10


@pytest.mark.parametrize("completed", [0, 3, 9])
def test_exhausted_fake_preserves_partial_match(
    store: MatchStore, completed: int
) -> None:
    match_id = create(store).match.settings.match_id
    replay = asyncio.run(run_match(store, match_id, fake("cooperate", completed)))
    assert replay.match.status == "failed"
    assert replay.error_category == "invalid_decision"
    assert len(replay.rounds) == completed
    assert replay.match.player_total == replay.match.opponent_total == 3 * completed
    assert replay.match.winner is None
    assert len(replay.attempts) == completed + 1
    assert replay.attempts[-1].status == "failed"
    assert store.read(match_id) == replay


@pytest.mark.parametrize("invalid", [False, True])
def test_failure_has_safe_category(store: MatchStore, invalid: bool) -> None:
    class BrokenPlayer(FakePlayer):
        async def decide(
            self, observation: Observation, strategy: str
        ) -> DecisionResult:
            if invalid:
                return DecisionResult.model_construct(decision={"choice": "invented"})
            raise PlayerError("provider_error")

    match_id = create(store).match.settings.match_id
    replay = asyncio.run(run_match(store, match_id, BrokenPlayer(())))
    assert replay.error_category == (
        "invalid_decision" if invalid else "provider_error"
    )
    assert replay.rounds == ()
    assert replay.match.player_total == replay.match.opponent_total == 0
    assert replay.match.winner is None


def test_commit_failure_does_not_reveal_outcome(store: MatchStore) -> None:
    match_id = create(store).match.settings.match_id
    with sqlite3.connect(store.path) as connection:
        connection.execute("""
            CREATE TRIGGER reject_round BEFORE INSERT ON rounds
            WHEN NEW.round_number = 4
            BEGIN SELECT RAISE(ABORT, 'injected commit failure'); END
        """)
    replay = asyncio.run(run_match(store, match_id, fake("cooperate")))
    assert replay.match.status == "failed"
    assert replay.error_category == "storage_error"
    assert len(replay.rounds) == 3
    assert len(replay.attempts) == 4
    assert replay.match.player_total == replay.match.opponent_total == 9
    assert replay.match.winner is None
    assert store.read(match_id) == replay
