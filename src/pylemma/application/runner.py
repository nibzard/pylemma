"""Execute a pending match once and expose only committed replay data."""

import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal, overload
from uuid import UUID

import logfire
from pydantic import ValidationError

from pylemma.game import opponents
from pylemma.player.service import DecisionResult, Player, PlayerError
from pylemma.records.models import (
    AttemptMetadata,
    AttemptRecord,
    Observation,
    Replay,
    RoundRecord,
)
from pylemma.records.sqlite import MatchStore
from pylemma.telemetry import match_context, span


async def run_match(
    store: MatchStore,
    match_id: UUID,
    player: Player,
    *,
    telemetry: logfire.Logfire | None = None,
) -> Replay:
    """Execute once with optional tracing; trace references do not prove delivery."""
    settings = store.read(match_id).match.settings
    player.validate_settings(settings)
    with (
        match_context(telemetry),
        span(
            "match.run",
            match_id=str(match_id),
            rules_version=settings.rules_version,
            strategy_hash=settings.strategy_hash,
            system_prompt_version=settings.system_prompt_version,
            opponent_version=settings.opponent_version,
            provider=settings.provider,
            model_id=settings.model_id,
        ) as root,
    ):
        replay = await _execute(store, match_id, player, root.trace_id)
        root.set(status=replay.match.status, error_category=replay.error_category)
        if replay.match.status == "completed":
            with span(
                "match.complete",
                player_total=replay.match.player_total,
                opponent_total=replay.match.opponent_total,
                combined_total=replay.match.player_total + replay.match.opponent_total,
                winner=replay.match.winner,
                player_cooperations=replay.match.player_cooperations,
                opponent_cooperations=replay.match.opponent_cooperations,
            ):
                pass
        return replay


async def _execute(
    store: MatchStore,
    match_id: UUID,
    player: Player,
    trace_id: str | None,
) -> Replay:
    replay = store.transition(
        match_id, "running", at=datetime.now(UTC), trace_id=trace_id
    )
    try:
        while replay.match.status == "running":
            with span("round.run", round_number=len(replay.rounds) + 1) as round_span:
                observation = Observation.from_match(replay.match)
                opponent_history = observation.opponent_history()
                started_at = datetime.now(UTC)
                # Both immutable observations exist before either decision is computed.
                try:
                    with span("player.decide") as player_span:
                        result = DecisionResult.model_validate(
                            await player.decide(
                                observation, replay.match.settings.strategy
                            )
                        )
                        player_span.set(
                            decision=result.decision.model_dump(mode="json")
                        )
                except (PlayerError, ValidationError) as error:
                    category = (
                        error.category
                        if isinstance(error, PlayerError)
                        else "invalid_decision"
                    )
                    round_span.set(error_category=category)
                    completed_at = datetime.now(UTC)
                    attempts = error.attempts if isinstance(error, PlayerError) else ()
                    save_attempts(
                        store,
                        match_id,
                        observation.round_number,
                        attempts
                        or (
                            AttemptMetadata(
                                status="failed",
                                error_category=category,
                                model_settings_json="{}",
                                started_at=started_at,
                                completed_at=completed_at,
                            ),
                        ),
                    )
                    return store.transition(
                        match_id, "failed", at=completed_at, error_category=category
                    )
                completed_at = datetime.now(UTC)
                attempts = result.attempts or (
                    AttemptMetadata(
                        status="succeeded",
                        model_settings_json=result.model_settings_json,
                        started_at=started_at,
                        completed_at=completed_at,
                    ),
                )
                save_attempts(store, match_id, observation.round_number, attempts)
                with span("opponent.decide") as opponent_span:
                    opponent = opponents.decide(
                        replay.match.settings.opponent_version, opponent_history
                    )
                    opponent_span.set(
                        choice=opponent.choice,
                        policy_branch=opponent.stated_reason,
                    )
                with span("round.resolve"):
                    resolved = replay.match.resolve(
                        observation.round_number, result.decision, opponent
                    )
                    outcome = resolved.outcomes[-1]
                with span("round.commit"):
                    replay = store.commit_round(
                        RoundRecord(
                            match_id=match_id,
                            trace_id=round_span.trace_id,
                            span_id=round_span.span_id,
                            observation=observation,
                            outcome=outcome,
                            player_points=outcome.player_points,
                            opponent_points=outcome.opponent_points,
                            player_total=resolved.player_total,
                            opponent_total=resolved.opponent_total,
                            started_at=started_at,
                            completed_at=completed_at,
                            attempt_count=len(attempts),
                            input_tokens=total(attempts, "input_tokens"),
                            output_tokens=total(attempts, "output_tokens"),
                            estimated_cost_usd=total(attempts, "estimated_cost_usd"),
                        )
                    )
                round_span.set(
                    player_points=outcome.player_points,
                    opponent_points=outcome.opponent_points,
                    player_total=replay.match.player_total,
                    opponent_total=replay.match.opponent_total,
                )
    except sqlite3.Error:
        return store.transition(
            match_id, "failed", at=datetime.now(UTC), error_category="storage_error"
        )
    return replay


def save_attempts(
    store: MatchStore,
    match_id: UUID,
    round_number: int,
    attempts: tuple[AttemptMetadata, ...],
) -> None:
    """Persist all requests before committing a resolved round."""
    for number, attempt in enumerate(attempts, 1):
        store.record_attempt(
            AttemptRecord(
                **attempt.model_dump(),
                match_id=match_id,
                round_number=round_number,
                attempt_number=number,
            )
        )


@overload
def total(
    attempts: tuple[AttemptMetadata, ...],
    field: Literal["input_tokens", "output_tokens"],
) -> int | None: ...


@overload
def total(
    attempts: tuple[AttemptMetadata, ...], field: Literal["estimated_cost_usd"]
) -> Decimal | None: ...


def total(attempts: tuple[AttemptMetadata, ...], field: str) -> int | Decimal | None:
    """Keep an aggregate unknown if any request has unknown usage."""
    values = [getattr(attempt, field) for attempt in attempts]
    return None if any(value is None for value in values) else sum(values)
