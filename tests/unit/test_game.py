"""Exercise contracts and game invariants without external services."""

import json
from datetime import UTC, datetime, timedelta, timezone
from hashlib import sha256
from itertools import product
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from pylemma.game.models import Decision, HistoryEntry, Match, MatchSettings, Outcome
from pylemma.game.opponents import POLICIES, decide
from pylemma.game.rules import Choice, score


def settings(**changes: Any) -> MatchSettings:
    values: dict[str, Any] = {
        "match_id": uuid4(),
        "strategy": "Cooperate.",
        "strategy_hash": sha256(b"Cooperate.").hexdigest(),
        "opponent_id": "optimist",
        "opponent_version": "optimist-v1",
        "provider": "fake",
        "model_id": "fake-v1",
        "model_settings_json": '{"temperature":0,"nested":{"values":[1,true,null]}}',
        "system_prompt_version": "system-v1",
        "notice_version": "notice-v1",
        "application_version": "0.1.0",
        "created_at": datetime.now(UTC),
    }
    values.update(changes)
    return MatchSettings(**values)


def decision(choice: Choice = "cooperate") -> Decision:
    return Decision(choice=choice, stated_reason="A fixed test choice.")


def play(player: Choice, opponent: str) -> Match:
    match = Match(
        settings=settings(opponent_id=opponent, opponent_version=f"{opponent}-v1")
    ).start()
    for number in range(1, 11):
        match = match.resolve(
            number,
            decision(player),
            decide(match.settings.opponent_version, match.history),
        )
    return match


@pytest.mark.parametrize(
    "player,opponent,expected",
    [
        ("cooperate", "cooperate", (3, 3)),
        ("cooperate", "betray", (0, 5)),
        ("betray", "cooperate", (5, 0)),
        ("betray", "betray", (1, 1)),
    ],
)
def test_score_matrix(
    player: Choice, opponent: Choice, expected: tuple[int, int]
) -> None:
    assert score(player, opponent) == expected
    outcome = Outcome(
        round_number=1, player=decision(player), opponent=decision(opponent)
    )
    assert (outcome.player_points, outcome.opponent_points) == expected


@pytest.mark.parametrize(
    "value", ["defect", "Cooperate", " cooperate", "", 1, True, None, b"betray"]
)
def test_choices_are_strict(value: Any) -> None:
    with pytest.raises(ValidationError):
        Decision(choice=value, stated_reason="A reason.")
    with pytest.raises(ValueError):
        score(value, "cooperate")


@pytest.mark.parametrize("reason", ["", " \n\t ", "a" * 241, None, 42])
def test_invalid_reasons(reason: Any) -> None:
    with pytest.raises(ValidationError):
        Decision(choice="cooperate", stated_reason=reason)


@pytest.mark.parametrize("length", [1, 240])
def test_reason_trims_before_length_check(length: int) -> None:
    assert (
        Decision(
            choice="betray", stated_reason=" \n" + "a" * length + " "
        ).stated_reason
        == "a" * length
    )


def test_decision_rejects_missing_and_extra_fields() -> None:
    for data in [
        {"choice": "cooperate"},
        {"choice": "betray", "stated_reason": "Hi", "score": 50},
    ]:
        with pytest.raises(ValidationError):
            Decision.model_validate(data)


@pytest.mark.parametrize(
    "changes",
    [
        {"strategy": " "},
        {"strategy": "a" * 1001},
        {"strategy_hash": "0" * 64},
        {"scheduled_rounds": 9},
        {"scheduled_rounds": True},
        {"rules_version": "pd-v2"},
        {"opponent_version": "grudge-v1"},
        {"opponent_id": "unknown"},
        {"provider": ""},
        {"model_id": ""},
        {"unexpected": True},
        {"created_at": datetime(2026, 1, 1)},
        {"model_settings_json": "[]"},
        {"model_settings_json": '{"x":NaN}'},
        {"model_settings_json": '{"x":1e999}'},
        {"model_settings_json": "{"},
    ],
)
def test_invalid_settings(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        settings(**changes)


def test_immutable_settings_and_round_trip() -> None:
    original = settings(strategy=" Cooperate. ")
    assert original.strategy == "Cooperate."
    assert MatchSettings.model_validate_json(original.model_dump_json()) == original
    with pytest.raises(ValidationError):
        original.strategy = "Betray."
    params = original.model_parameters()
    params["temperature"] = 1
    assert original.model_parameters()["temperature"] == 0
    identifier = uuid4()
    with pytest.raises(ValidationError):
        settings(match_id=identifier, parent_match_id=identifier)
    later = settings(parent_match_id=original.match_id)
    assert later.match_id != original.match_id
    utc = settings(
        created_at=datetime.now(UTC).astimezone(tz=timezone(timedelta(hours=2)))
    )
    assert utc.created_at.utcoffset() == timedelta(0)


def test_policies_for_every_possible_player_history() -> None:
    choices_available: tuple[Choice, ...] = ("cooperate", "betray")
    for size in range(10):
        for choices in product(choices_available, repeat=size):
            history = tuple(
                HistoryEntry(
                    round_number=i, player_choice=c, opponent_choice="cooperate"
                )
                for i, c in enumerate(choices, 1)
            )
            number = size + 1
            assert decide("optimist-v1", history) == decision_for(
                "cooperate", "I cooperate in every round."
            )
            expected = (
                decision_for(
                    "betray",
                    "The player betrayed in an earlier round. "
                    "I betray in every later round.",
                )
                if "betray" in choices
                else decision_for(
                    "cooperate",
                    "The player has not betrayed in a completed round. I cooperate.",
                )
            )
            assert decide("grudge-v1", history) == expected
            if choices and choices[-1] == "betray":
                expected = decision_for(
                    "betray", "The player betrayed in the previous round. I betray."
                )
            elif number in (3, 6, 9):
                expected = decision_for("betray", "This is round 3, 6, or 9. I betray.")
            else:
                expected = decision_for(
                    "cooperate",
                    "The player did not betray in the previous round, "
                    "and this is not round 3, 6, or 9. I cooperate.",
                )
            assert decide("opportunist-v1", history) == expected


def decision_for(choice: Choice, reason: str) -> Decision:
    return Decision(choice=choice, stated_reason=reason)


def test_policy_contracts_and_invalid_history() -> None:
    assert [p.version for p in POLICIES] == [
        "optimist-v1",
        "grudge-v1",
        "opportunist-v1",
    ]
    assert all(p.name and p.description for p in POLICIES)
    with pytest.raises(ValueError):
        decide("unknown", ())
    for numbers in [(2,), (1, 1), (1, 3), tuple(range(1, 11))]:
        history = tuple(
            HistoryEntry(
                round_number=n, player_choice="cooperate", opponent_choice="cooperate"
            )
            for n in numbers
        )
        with pytest.raises(ValueError):
            decide("optimist-v1", history)
    with pytest.raises(ValidationError):
        HistoryEntry(
            round_number=1,
            player_choice="cooperate",
            opponent_choice="cooperate",
            stated_reason="Private",
            strategy="Private",
        )  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "player,opponent,totals,winner",
    [
        ("cooperate", "optimist", (30, 30), "draw"),
        ("betray", "optimist", (50, 0), "player"),
        ("cooperate", "opportunist", (21, 36), "opponent"),
        ("betray", "grudge", (14, 9), "player"),
    ],
)
def test_reference_matches(
    player: Choice, opponent: str, totals: tuple[int, int], winner: str
) -> None:
    match = play(player, opponent)
    assert match.status == "completed"
    assert (match.player_total, match.opponent_total) == totals
    assert match.combined_total == sum(totals)
    assert match.winner == winner
    assert match.player_cooperations == (10 if player == "cooperate" else 0)
    assert match.opponent_cooperations == sum(
        r.opponent.choice == "cooperate" for r in match.outcomes
    )
    assert Match.model_validate_json(match.model_dump_json()) == match


def test_mutual_betrayal_and_cumulative_totals() -> None:
    match = Match(settings=settings()).start()
    for number in range(1, 11):
        old = match
        match = match.resolve(number, decision("betray"), decision("betray"))
        assert match.player_total == match.opponent_total == number
        assert len(old.outcomes) == number - 1
        assert match.winner == ("draw" if number == 10 else None)
    assert match.player_cooperations == match.opponent_cooperations == 0


@pytest.mark.parametrize("number", [0, 2, 10, 11, True])
def test_round_order(number: int) -> None:
    match = Match(settings=settings()).start()
    with pytest.raises(ValueError):
        match.resolve(number, decision(), decision())
    resolved = match.resolve(1, decision(), decision())
    with pytest.raises(ValueError):
        resolved.resolve(1, decision(), decision())
    assert not match.outcomes


@pytest.mark.parametrize(
    "status", ["pending", "running", "completed", "failed", "interrupted"]
)
@pytest.mark.parametrize("operation", ["start", "fail", "interrupt", "resolve"])
def test_transition_table(status: str, operation: str) -> None:
    match = Match(settings=settings())
    if status == "completed":
        match = play("cooperate", "optimist")
    elif status != "pending":
        match = match.start().resolve(1, decision(), decision())
        if status == "failed":
            match = match.fail()
        elif status == "interrupted":
            match = match.interrupt()
    allowed = {
        "start": {"pending"},
        "fail": {"running"},
        "interrupt": {"pending", "running"},
        "resolve": {"running"},
    }

    def apply() -> Match:
        if operation == "resolve":
            return match.resolve(len(match.outcomes) + 1, decision(), decision())
        result: Match = getattr(match, operation)()
        return result

    if status in allowed[operation]:
        result = apply()
        if operation in ("fail", "interrupt"):
            assert result.outcomes == match.outcomes
            assert result.player_total == match.player_total
            assert result.winner is None
    else:
        with pytest.raises(ValueError):
            apply()


def test_restored_state_cannot_bypass_invariants() -> None:
    complete = play("cooperate", "optimist")
    data = complete.model_dump(mode="json")
    for status in ("pending", "running", "failed", "interrupted"):
        with pytest.raises(ValidationError):
            Match.model_validate_json(json.dumps({**data, "status": status}))
    for outcomes in [
        data["outcomes"][:-1],
        data["outcomes"] + data["outcomes"][:1],
        list(reversed(data["outcomes"])),
    ]:
        with pytest.raises(ValidationError):
            Match.model_validate_json(json.dumps({**data, "outcomes": outcomes}))
    outcome = complete.outcomes[0]
    with pytest.raises(ValidationError):
        Outcome.model_validate({**outcome.model_dump(), "player_points": 99})
    with pytest.raises(ValidationError):
        outcome.round_number = 2
    for number in (0, 11, True):
        with pytest.raises(ValidationError):
            Outcome(round_number=number, player=decision(), opponent=decision())


def test_pending_state_and_incomplete_completion_are_rejected() -> None:
    outcome = Outcome(round_number=1, player=decision(), opponent=decision())
    for status in ("pending", "completed"):
        with pytest.raises(ValidationError):
            Match.model_validate(
                {"settings": settings(), "status": status, "outcomes": (outcome,)}
            )
    with pytest.raises(ValidationError):
        Match(settings=settings(), status="completed")


def test_failed_round_preserves_partial_results() -> None:
    match = Match(settings=settings()).start()
    for number in range(1, 10):
        match = match.resolve(number, decision("betray"), decision())
    failed = match.fail()
    assert len(failed.outcomes) == 9
    assert failed.player_total == 45
    assert failed.opponent_total == 0
    assert failed.winner is None
    assert match.status == "running"
    assert Match.model_validate_json(failed.model_dump_json()) == failed


def test_history_excludes_reasons_and_settings() -> None:
    match = (
        Match(settings=settings()).start().resolve(1, decision("betray"), decision())
    )
    assert match.history[0].model_dump() == {
        "round_number": 1,
        "player_choice": "betray",
        "opponent_choice": "cooperate",
    }
    assert (match.history[0].player_points, match.history[0].opponent_points) == (5, 0)
    with pytest.raises(ValidationError):
        match.settings = settings()
    with pytest.raises(ValidationError):
        match.outcomes[0].player.choice = "cooperate"


def test_nested_unvalidated_copies_are_rejected_at_construction() -> None:
    invalid = decision().model_copy(update={"choice": "defect"})
    with pytest.raises(ValidationError):
        Match(settings=settings()).start().resolve(1, invalid, decision())


@pytest.mark.parametrize("length", [1, 1000])
def test_strategy_bounds(length: int) -> None:
    strategy = "a" * length
    result = settings(
        strategy=" " + strategy + " ",
        strategy_hash=sha256(strategy.encode()).hexdigest(),
    )
    assert result.strategy == strategy


def test_game_imports_only_domain_and_contract_dependencies() -> None:
    import ast
    from pathlib import Path

    import pylemma.game

    root = Path(pylemma.game.__file__).parent
    allowed = {
        "__future__",
        "datetime",
        "hashlib",
        "json",
        "pydantic",
        "pylemma",
        "types",
        "typing",
        "uuid",
    }
    for path in root.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] in allowed for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert node.module and node.module.split(".")[0] in allowed
                if node.module.startswith("pylemma"):
                    assert node.module.startswith("pylemma.game")
