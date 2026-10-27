"""Immutable game contracts and match transitions.

Use validated constructors or model_validate_json when restoring records.
Pydantic model_construct and model_copy(update=...) skip validation; do not use
these trusted-data APIs at external boundaries. Scores derive from outcomes.
"""

import json
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from pylemma.game.rules import Choice, score

Text = Annotated[str, Field(min_length=1, max_length=240)]
RoundNumber = Annotated[int, Field(ge=1, le=10)]
OpponentId = Literal["optimist", "grudge", "opportunist"]
PolicyVersion = Literal["optimist-v1", "grudge-v1", "opportunist-v1"]
Status = Literal["pending", "running", "completed", "failed", "interrupted"]


class Contract(BaseModel):
    """Reject unknown fields and coercion; prevent field assignment."""

    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, revalidate_instances="always"
    )


class Decision(Contract):
    """One choice with a trimmed stated reason of 1 to 240 characters."""

    choice: Choice
    stated_reason: Text

    @field_validator("stated_reason", mode="before")
    @classmethod
    def trim_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class MatchSettings(Contract):
    """Settings fixed at creation; model parameters are an immutable JSON object.

    Model and version identifiers are opaque. The provider adapter owns supported
    parameter validation and selection of a pinned model identifier.
    """

    match_id: UUID
    parent_match_id: UUID | None = None
    strategy: Annotated[str, Field(min_length=1, max_length=1000)]
    strategy_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    opponent_id: OpponentId
    opponent_version: PolicyVersion
    rules_version: Literal["pd-v1"] = "pd-v1"
    scheduled_rounds: Annotated[int, Field(ge=10, le=10)] = 10
    provider: Text
    model_id: Text
    model_settings_json: Annotated[str, Field(min_length=2, max_length=8192)]
    system_prompt_version: Text
    notice_version: Text
    application_version: Text
    created_at: datetime

    @field_validator("strategy", mode="before")
    @classmethod
    def trim_strategy(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("created_at")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError(
                "Creation time needs a timezone. Supply an aware datetime."
            )
        return value.astimezone(UTC)

    @field_validator("model_settings_json")
    @classmethod
    def require_parameters(cls, value: str) -> str:
        def invalid_constant(constant: str) -> None:
            raise ValueError("Model parameters must contain finite JSON values.")

        parsed = json.loads(value, parse_constant=invalid_constant)
        if not isinstance(parsed, dict):
            raise ValueError("Model parameters must be a JSON object.")
        json.dumps(parsed, allow_nan=False)
        return value

    @model_validator(mode="after")
    def check_settings(self) -> Self:
        if self.parent_match_id == self.match_id:
            raise ValueError("A rematch needs a new match identifier.")
        if self.opponent_version != f"{self.opponent_id}-v1":
            raise ValueError("Opponent identifier and policy version must match.")
        if self.strategy_hash != sha256(self.strategy.encode("utf-8")).hexdigest():
            raise ValueError(
                "Strategy hash must match the trimmed strategy encoded as UTF-8."
            )
        return self

    def model_parameters(self) -> dict[str, JsonValue]:
        """Return a fresh parameter dictionary without exposing mutable settings."""
        parameters: dict[str, JsonValue] = json.loads(self.model_settings_json)
        return parameters


class HistoryEntry(Contract):
    """Completed choices only; no strategy or stated reasons enter policy input."""

    round_number: RoundNumber
    player_choice: Choice
    opponent_choice: Choice

    @property
    def player_points(self) -> int:
        return score(self.player_choice, self.opponent_choice)[0]

    @property
    def opponent_points(self) -> int:
        return score(self.player_choice, self.opponent_choice)[1]


class Outcome(Contract):
    """Two revealed decisions with score changes derived only from pd-v1."""

    round_number: RoundNumber
    player: Decision
    opponent: Decision

    @property
    def player_points(self) -> int:
        return score(self.player.choice, self.opponent.choice)[0]

    @property
    def opponent_points(self) -> int:
        return score(self.player.choice, self.opponent.choice)[1]


def validate_history(history: tuple[HistoryEntry, ...]) -> None:
    """Require consecutive completed rounds before an unresolved scheduled round."""
    if len(history) >= 10:
        raise ValueError("All scheduled rounds are complete. Start a new match.")
    if any(entry.round_number != number for number, entry in enumerate(history, 1)):
        raise ValueError("History must start at round 1 without gaps or duplicates.")


class Match(Contract):
    """Aggregate that derives totals and returns validated immutable transitions.

    Completion occurs with the tenth outcome. Failed and interrupted matches
    retain completed outcomes and have no winner. Persistence commits the new
    aggregate before exposing outcomes to visitors.
    """

    settings: MatchSettings
    status: Status = "pending"
    outcomes: tuple[Outcome, ...] = ()

    @model_validator(mode="after")
    def check_state(self) -> Self:
        count = len(self.outcomes)
        if count > 10 or any(
            o.round_number != n for n, o in enumerate(self.outcomes, 1)
        ):
            raise ValueError(
                "Outcomes must contain rounds 1 through 10 without gaps or duplicates."
            )
        if self.status == "pending" and count:
            raise ValueError("A pending match cannot contain outcomes.")
        if (self.status == "completed") != (count == 10):
            raise ValueError("Only a completed match can contain exactly ten outcomes.")
        return self

    @property
    def history(self) -> tuple[HistoryEntry, ...]:
        return tuple(
            HistoryEntry(
                round_number=o.round_number,
                player_choice=o.player.choice,
                opponent_choice=o.opponent.choice,
            )
            for o in self.outcomes
        )

    @property
    def player_total(self) -> int:
        return sum(o.player_points for o in self.outcomes)

    @property
    def opponent_total(self) -> int:
        return sum(o.opponent_points for o in self.outcomes)

    @property
    def combined_total(self) -> int:
        return self.player_total + self.opponent_total

    @property
    def player_cooperations(self) -> int:
        return sum(o.player.choice == "cooperate" for o in self.outcomes)

    @property
    def opponent_cooperations(self) -> int:
        return sum(o.opponent.choice == "cooperate" for o in self.outcomes)

    @property
    def winner(self) -> Literal["player", "opponent", "draw"] | None:
        if self.status != "completed":
            return None
        if self.player_total == self.opponent_total:
            return "draw"
        return "player" if self.player_total > self.opponent_total else "opponent"

    def start(self) -> Self:
        """Start a pending match."""
        return self._transition("running", ("pending",))

    def fail(self) -> Self:
        """Stop a running match without adding an outcome."""
        return self._transition("failed", ("running",))

    def interrupt(self) -> Self:
        """Stop a pending or running match without adding an outcome."""
        return self._transition("interrupted", ("pending", "running"))

    def _transition(self, status: Status, allowed: tuple[Status, ...]) -> Self:
        if self.status not in allowed:
            raise ValueError(
                f"Cannot change {self.status} to {status}. Start a new match if needed."
            )
        return type(self)(settings=self.settings, status=status, outcomes=self.outcomes)

    def resolve(self, round_number: int, player: Decision, opponent: Decision) -> Self:
        """Resolve the next round once; automatically complete round 10."""
        if self.status != "running":
            raise ValueError("Only a running match can resolve a round.")
        outcome = Outcome(round_number=round_number, player=player, opponent=opponent)
        if round_number != len(self.outcomes) + 1:
            raise ValueError(
                "Resolve the next round number without gaps or duplicates."
            )
        outcomes = (*self.outcomes, outcome)
        status: Status = "completed" if len(outcomes) == 10 else "running"
        return type(self)(settings=self.settings, status=status, outcomes=outcomes)
