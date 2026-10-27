"""Validated storage contracts. Unknown usage and estimated cost remain null."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from pylemma.game.models import (
    Contract,
    HistoryEntry,
    Match,
    MatchSettings,
    Outcome,
    RoundNumber,
    Text,
)
from pylemma.game.opponents import POLICIES, Policy
from pylemma.game.rules import Choice, score

Count = Annotated[int, Field(ge=0)]
ErrorCategory = Literal[
    "invalid_decision",
    "provider_error",
    "authentication",
    "budget_exhausted",
    "timeout",
    "storage_error",
    "interrupted",
]


class ScoreEntry(Contract):
    """One score-matrix entry, with stored points checked against game rules."""

    player_choice: Choice
    opponent_choice: Choice
    player_points: Count
    opponent_points: Count

    @model_validator(mode="after")
    def check_points(self) -> Self:
        if (self.player_points, self.opponent_points) != score(
            self.player_choice, self.opponent_choice
        ):
            raise ValueError("Stored points differ from the rules. Check the record.")
        return self


class ObservedRound(ScoreEntry):
    """Completed choices and points without either stated reason."""

    round_number: RoundNumber


class Observation(Contract):
    """Exact permitted model input, excluding strategy and current decisions.

    The runner creates this value before requesting either current decision.
    Storage checks it against the previously committed match.
    """

    round_number: RoundNumber
    scheduled_rounds: Literal[10] = 10
    rules_version: Literal["pd-v1"] = "pd-v1"
    score_matrix: tuple[ScoreEntry, ...]
    player_total: Count
    opponent_total: Count
    history: tuple[ObservedRound, ...]
    opponent: Policy

    @classmethod
    def from_match(cls, match: Match) -> Self:
        """Build permitted input from completed outcomes and fixed settings."""
        choices: tuple[Choice, ...] = ("cooperate", "betray")
        return cls(
            round_number=len(match.outcomes) + 1,
            score_matrix=tuple(
                ScoreEntry(
                    player_choice=p,
                    opponent_choice=o,
                    player_points=points[0],
                    opponent_points=points[1],
                )
                for p in choices
                for o in choices
                for points in (score(p, o),)
            ),
            player_total=match.player_total,
            opponent_total=match.opponent_total,
            history=tuple(
                ObservedRound(
                    round_number=h.round_number,
                    player_choice=h.player_choice,
                    opponent_choice=h.opponent_choice,
                    player_points=h.player_points,
                    opponent_points=h.opponent_points,
                )
                for h in match.history
            ),
            opponent=next(
                p for p in POLICIES if p.version == match.settings.opponent_version
            ),
        )

    def opponent_history(self) -> tuple[HistoryEntry, ...]:
        """Return completed choices for the deterministic opponent."""
        return tuple(
            HistoryEntry(
                round_number=h.round_number,
                player_choice=h.player_choice,
                opponent_choice=h.opponent_choice,
            )
            for h in self.history
        )


class TimedRecord(Contract):
    """Normalize aware timestamps to UTC and reject reversed intervals."""

    started_at: datetime
    completed_at: datetime

    @field_validator("started_at", "completed_at")
    @classmethod
    def utc(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("Timestamp needs a timezone. Supply an aware datetime.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def check_times(self) -> Self:
        if self.completed_at < self.started_at:
            raise ValueError("Completion precedes start. Check the timestamps.")
        return self


class AttemptMetadata(TimedRecord):
    """One completed provider request, including failed requests.

    Record actual parameters, not provider defaults inferred after execution.
    Unknown usage on any attempt keeps the round aggregate unknown.
    """

    status: Literal["succeeded", "failed"]
    error_category: ErrorCategory | None = None
    model_settings_json: Annotated[str, Field(min_length=2, max_length=8192)]
    input_tokens: Count | None = None
    output_tokens: Count | None = None
    estimated_cost_usd: Annotated[Decimal, Field(ge=0, allow_inf_nan=False)] | None = (
        None
    )
    cost_basis: Text | None = None
    trace_id: Text | None = None
    span_id: Text | None = None

    @field_validator("model_settings_json")
    @classmethod
    def parameters(cls, value: str) -> str:
        return MatchSettings.require_parameters(value)

    @model_validator(mode="after")
    def check_result(self) -> Self:
        if (self.status == "failed") != (self.error_category is not None):
            raise ValueError(
                "Failed attempts need an error category. Check the result."
            )
        if self.estimated_cost_usd is not None and self.cost_basis is None:
            raise ValueError("Estimated cost needs a basis. Record the pricing source.")
        return self


class AttemptRecord(AttemptMetadata):
    """Request metadata assigned to one match, round, and attempt."""

    match_id: UUID
    round_number: RoundNumber
    attempt_number: Annotated[int, Field(ge=1, le=2)]


class RoundRecord(TimedRecord):
    """Committed observation, outcome, totals, and execution metadata."""

    match_id: UUID
    observation: Observation
    outcome: Outcome
    player_total: Count
    opponent_total: Count
    trace_id: Text | None = None
    span_id: Text | None = None
    attempt_count: Annotated[int, Field(ge=1, le=2)]
    input_tokens: Count | None = None
    output_tokens: Count | None = None
    estimated_cost_usd: Annotated[Decimal, Field(ge=0, allow_inf_nan=False)] | None = (
        None
    )
    player_points: Count
    opponent_points: Count


class Replay(Contract):
    """Stored replay data. Scores and winner are available through match properties."""

    match: Match
    rounds: tuple[RoundRecord, ...]
    attempts: tuple[AttemptRecord, ...]
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_category: ErrorCategory | None
    trace_id: Text | None
    public_trace_url: Text | None
