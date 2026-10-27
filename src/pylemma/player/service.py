"""One asynchronous decision boundary; strategy stays separate from observation."""

from typing import Protocol

from pydantic import Field, field_validator

from pylemma.game.models import Contract, Decision, MatchSettings
from pylemma.records.models import AttemptMetadata, ErrorCategory, Observation


class DecisionResult(Contract):
    """Validated decision and metadata for every provider request."""

    attempts: tuple[AttemptMetadata, ...] = Field(default=(), max_length=2)
    decision: Decision
    model_settings_json: str = "{}"

    @field_validator("model_settings_json")
    @classmethod
    def parameters(cls, value: str) -> str:
        return MatchSettings.require_parameters(value)


class PlayerError(Exception):
    """Explicit decision failure carrying only a safe error category."""

    def __init__(
        self, category: ErrorCategory, attempts: tuple[AttemptMetadata, ...] = ()
    ):
        self.attempts = attempts
        self.category = category
        super().__init__(category)


class Player(Protocol):
    """Request a decision without access to current opponent choices."""

    def validate_settings(self, settings: MatchSettings) -> None:
        """Reject incompatible execution settings with ValueError before execution."""
        ...

    async def decide(self, observation: Observation, strategy: str) -> DecisionResult:
        """Return a validated decision or raise PlayerError."""
        ...


class FakePlayer:
    """Return fixed decisions by round number without network operations.

    An exhausted script fails explicitly; it never invents another decision.
    """

    def __init__(self, decisions: tuple[Decision, ...]):
        self.decisions = tuple(Decision.model_validate(d) for d in decisions)

    def validate_settings(self, settings: MatchSettings) -> None:
        """Require settings that describe this fixed fake player."""
        if (
            settings.provider != "fake"
            or settings.model_id != "fake-v1"
            or settings.model_parameters() != {}
            or settings.system_prompt_version != "fake-v1"
        ):
            raise ValueError(
                "Incompatible fake settings. Create a match with fake-v1 settings."
            )

    async def decide(self, observation: Observation, strategy: str) -> DecisionResult:
        """Select the scripted decision for the observed round."""
        if observation.round_number > len(self.decisions):
            raise PlayerError("invalid_decision")
        return DecisionResult(decision=self.decisions[observation.round_number - 1])
