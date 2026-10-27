"""The immutable pd-v1 score matrix."""

from types import MappingProxyType
from typing import Literal

Choice = Literal["cooperate", "betray"]
RULES_VERSION = "pd-v1"
SCHEDULED_ROUNDS = 10
SCORE_MATRIX = MappingProxyType(
    {
        ("cooperate", "cooperate"): (3, 3),
        ("cooperate", "betray"): (0, 5),
        ("betray", "cooperate"): (5, 0),
        ("betray", "betray"): (1, 1),
    }
)


def score(player: Choice, opponent: Choice) -> tuple[int, int]:
    """Return player and opponent points for two exact choice values."""
    for choice in (player, opponent):
        if type(choice) is not str or choice not in ("cooperate", "betray"):
            raise ValueError("Invalid choice. Use cooperate or betray.")
    return SCORE_MATRIX[player, opponent]
