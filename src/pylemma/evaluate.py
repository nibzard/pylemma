"""Explicit, bounded live evaluation. Ordinary tests never invoke the provider."""

import argparse
import asyncio
import json
import os
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any
from uuid import uuid4

from pylemma.game.models import Match, MatchSettings
from pylemma.game.opponents import decide
from pylemma.player.model import (
    COST_BASIS,
    MAX_INPUT_TOKENS,
    MODEL_ID,
    PARAMETERS,
    SYSTEM_PROMPT,
    SYSTEM_VERSION,
    ModelPlayer,
    estimate,
)
from pylemma.player.service import Player, PlayerError
from pylemma.records.models import Observation

MATCH_RESERVATION = 20 * estimate(MAX_INPUT_TOKENS, 256)


def check_allowance(repetitions: int, allowance: Decimal) -> Decimal:
    """Reserve the full request ceiling, including requests with unknown charges."""
    if not 1 <= repetitions <= 10 or not allowance.is_finite() or allowance <= 0:
        raise ValueError("Use 1 to 10 repetitions and a finite positive allowance.")
    reservation = repetitions * MATCH_RESERVATION
    if reservation > allowance:
        raise ValueError(
            f"The request ceiling needs USD {reservation}. Increase the allowance."
        )
    return reservation


async def evaluate(
    player: Player, strategy: str, repetitions: int, allowance: Decimal
) -> dict[str, Any]:
    """Evaluate complete matches against Optimist and retain failures and costs."""
    reserved = check_allowance(repetitions, allowance)
    strategy = strategy.strip()
    matches: list[dict[str, Any]] = []
    costs: list[Decimal | None] = []
    for _ in range(repetitions):
        match = Match(
            settings=MatchSettings(
                match_id=uuid4(),
                strategy=strategy,
                strategy_hash=sha256(strategy.encode()).hexdigest(),
                opponent_id="optimist",
                opponent_version="optimist-v1",
                provider="openai",
                model_id=MODEL_ID,
                model_settings_json=PARAMETERS,
                system_prompt_version=SYSTEM_VERSION,
                notice_version="local-evaluation-v1",
                application_version="0.1.0",
                created_at=datetime.now(UTC),
            )
        ).start()
        player.validate_settings(match.settings)
        rounds: list[dict[str, Any]] = []
        failure = None
        while match.status == "running":
            observation = Observation.from_match(match)
            try:
                result = await player.decide(observation, strategy)
                attempts = result.attempts
                decision = result.decision
            except PlayerError as error:
                attempts = error.attempts
                decision = None
                failure = error.category
            costs.extend(a.estimated_cost_usd for a in attempts)
            rounds.append(
                {
                    "observation": observation.model_dump(mode="json"),
                    "decision": decision.model_dump(mode="json") if decision else None,
                    "attempts": [a.model_dump(mode="json") for a in attempts],
                }
            )
            if decision is None:
                match = match.fail()
                break
            match = match.resolve(
                observation.round_number,
                decision,
                decide("optimist-v1", observation.opponent_history()),
            )
        matches.append(
            {
                "match": match.model_dump(mode="json"),
                "rounds": rounds,
                "failure": failure,
            }
        )
        if failure in ("authentication", "budget_exhausted"):
            break
    known_cost = sum((cost for cost in costs if cost is not None), Decimal(0))
    return {
        "model": MODEL_ID,
        "settings": json.loads(PARAMETERS),
        "system_prompt_version": SYSTEM_VERSION,
        "system_prompt": SYSTEM_PROMPT,
        "visitor_strategy": strategy,
        "requested_repetitions": repetitions,
        "executed_repetitions": len(matches),
        "matches": matches,
        "failures": sum(m["failure"] is not None for m in matches),
        "known_estimated_cost_usd": str(known_cost),
        "total_estimated_cost_usd": None if None in costs else str(known_cost),
        "unknown_cost_attempts": costs.count(None),
        "cost_basis": COST_BASIS,
        "reserved_ceiling_usd": str(reserved),
    }


def main() -> None:
    """Require explicit consent and an allowance before creating a provider client."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true", required=True)
    parser.add_argument("--max-cost-usd", type=Decimal, required=True)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--strategy", default="Cooperate in every round.")
    args = parser.parse_args()
    try:
        check_allowance(args.repetitions, args.max_cost_usd)
        if not args.strategy.strip() or len(args.strategy) > 1000:
            raise ValueError("Supply a strategy of 1 to 1000 characters.")
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError(
                "Set OPENAI_API_KEY outside the repository before a live evaluation."
            )
    except ValueError as error:
        parser.error(str(error))

    async def run() -> None:
        player = ModelPlayer(key)
        try:
            report = await evaluate(
                player, args.strategy, args.repetitions, args.max_cost_usd
            )
            print(json.dumps(report, indent=2))
        finally:
            await player.close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
