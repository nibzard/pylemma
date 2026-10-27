"""Versioned deterministic policies and fixed branch explanations."""

from pylemma.game.models import (
    Contract,
    Decision,
    HistoryEntry,
    OpponentId,
    PolicyVersion,
    Text,
    validate_history,
)


class Policy(Contract):
    """Public policy metadata used by selectors and observations."""

    identifier: OpponentId
    version: PolicyVersion
    name: Text
    description: Text


POLICIES = (
    Policy(
        identifier="optimist",
        version="optimist-v1",
        name="The Optimist",
        description="Cooperate in every round.",
    ),
    Policy(
        identifier="grudge",
        version="grudge-v1",
        name="The Grudge Holder",
        description="Cooperate until the player betrays in a completed round. "
        "Betray in every later round after that first betrayal.",
    ),
    Policy(
        identifier="opportunist",
        version="opportunist-v1",
        name="The Opportunist",
        description="Betray if the player betrayed in the previous round. "
        "Otherwise, betray in rounds 3, 6, and 9. Otherwise, cooperate.",
    ),
)


def decide(version: str, history: tuple[HistoryEntry, ...]) -> Decision:
    """Apply the versioned policy to completed history, in specified branch order."""
    validate_history(history)
    match version:
        case "optimist-v1":
            return Decision(
                choice="cooperate", stated_reason="I cooperate in every round."
            )
        case "grudge-v1":
            if any(entry.player_choice == "betray" for entry in history):
                return Decision(
                    choice="betray",
                    stated_reason=(
                        "The player betrayed in an earlier round. "
                        "I betray in every later round."
                    ),
                )
            return Decision(
                choice="cooperate",
                stated_reason=(
                    "The player has not betrayed in a completed round. I cooperate."
                ),
            )
        case "opportunist-v1":
            if history and history[-1].player_choice == "betray":
                return Decision(
                    choice="betray",
                    stated_reason=(
                        "The player betrayed in the previous round. I betray."
                    ),
                )
            if len(history) + 1 in (3, 6, 9):
                return Decision(
                    choice="betray", stated_reason="This is round 3, 6, or 9. I betray."
                )
            return Decision(
                choice="cooperate",
                stated_reason="The player did not betray in the previous round, "
                "and this is not round 3, 6, or 9. I cooperate.",
            )
        case _:
            raise ValueError(
                "Unknown opponent policy version. Select a published policy."
            )
