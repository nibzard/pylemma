"""Immutable machine versions and isolated, bounded game execution."""

from hashlib import sha256
from typing import Annotated, Any
from uuid import UUID, uuid4

from pydantic import Field
from pydantic_monty import Monty

from pylemma.game.models import Contract, Decision
from pylemma.game.rules import score
from pylemma.telemetry import span

Source = Annotated[str, Field(min_length=1, max_length=8000)]


class Blueprint(Contract):
    """Generated source defines decide(observation), without host capabilities."""

    summary: Annotated[str, Field(min_length=1, max_length=240)]
    code: Source


class Machine(Contract):
    """A stored version never changes; revisions receive new identifiers."""

    id: UUID
    name: Annotated[str, Field(min_length=1, max_length=60)]
    strategy: Annotated[str, Field(min_length=1, max_length=1000)]
    blueprint: Blueprint
    source_hash: str
    public_listing: bool = False

    @classmethod
    def create(
        cls,
        name: str,
        strategy: str,
        blueprint: Blueprint,
        *,
        public_listing: bool = False,
    ) -> "Machine":
        return cls(
            id=uuid4(),
            name=name,
            strategy=strategy,
            blueprint=blueprint,
            public_listing=public_listing,
            source_hash=sha256(blueprint.code.encode()).hexdigest(),
        )


class Sandbox:
    """Use one worker pool and a fresh session for every call.

    No filesystem mounts, callbacks, network, or environment access are provided.
    The host deadline also bounds parsing and stalled worker requests.
    """

    def __init__(self) -> None:
        self.pool = Monty(max_processes=1, request_timeout=2.0)
        self.pool.__enter__()

    def close(self) -> None:
        self.pool.__exit__(None, None, None)

    def decide(self, blueprint: Blueprint, observation: dict[str, Any]) -> Decision:
        with span(
            "machine.decision",
            observation=observation,
            source_hash=sha256(blueprint.code.encode()).hexdigest(),
        ) as operation:
            with self.pool.checkout(
                limits={
                    "max_memory": 8_000_000,
                    "max_feed_duration_secs": 0.05,
                    "max_recursion_depth": 80,
                }
            ) as session:
                result = session.feed_run(
                    blueprint.code + "\ndecide(observation)",
                    inputs={"observation": observation},
                )
            decision = Decision.model_validate(result)
            operation.set(decision=decision.model_dump())
            return decision

    def validate(self, blueprint: Blueprint) -> None:
        """Probe output shape; probes cannot establish fidelity to visitor intent."""
        for history in (
            [],
            [{"self": "cooperate", "opponent": "betray"}],
            [{"self": "betray", "opponent": "cooperate"}] * 9,
        ):
            self.decide(
                blueprint, {"round": len(history) + 1, "rounds": 10, "history": history}
            )


PRESETS = (
    ("The Optimist", '"cooperate"'),
    (
        "The Grudge Holder",
        '"betray" if any(r["opponent"] == "betray" for r in h) else "cooperate"',
    ),
    (
        "The Opportunist",
        '"betray" if (h and h[-1]["opponent"] == "betray") '
        'or observation["round"] in (3, 6, 9) else "cooperate"',
    ),
)


def presets() -> tuple[Blueprint, ...]:
    return tuple(
        Blueprint(
            summary=name,
            code=(
                'def decide(observation):\n    h = observation["history"]\n'
                f"    choice = {expression}\n"
                '    return {"choice": choice, "stated_reason": "Preset policy."}'
            ),
        )
        for name, expression in PRESETS
    )


def play(sandbox: Sandbox, left: Blueprint, right: Blueprint) -> dict[str, Any]:
    """Resolve simultaneous choices from separate, completed histories only."""
    rounds: list[dict[str, Any]] = []
    totals = [0, 0]
    with span(
        "machine.match",
        left_hash=sha256(left.code.encode()).hexdigest(),
        right_hash=sha256(right.code.encode()).hexdigest(),
        left_source=left.code,
        right_source=right.code,
    ) as operation:
        for number in range(1, 11):
            with span("machine.round", round_number=number) as round_span:
                observations = [
                    {
                        "round": number,
                        "rounds": 10,
                        "history": [
                            {
                                "self": r["choices"][side],
                                "opponent": r["choices"][1 - side],
                            }
                            for r in rounds
                        ],
                    }
                    for side in (0, 1)
                ]
                a = sandbox.decide(left, observations[0])
                b = sandbox.decide(right, observations[1])
                points = score(a.choice, b.choice)
                totals = [totals[i] + points[i] for i in (0, 1)]
                rounds.append(
                    {
                        "round": number,
                        "span_id": round_span.span_id,
                        "choices": [a.choice, b.choice],
                        "reasons": [a.stated_reason, b.stated_reason],
                        "points": list(points),
                        "totals": totals.copy(),
                    }
                )
        operation.set(totals=totals)
        return {
            "rounds": rounds,
            "totals": totals,
            "cooperation": [
                sum(r["choices"][i] == "cooperate" for r in rounds) for i in (0, 1)
            ],
            "combined": sum(totals),
            "trace_id": operation.trace_id,
        }


def tournament(sandbox: Sandbox, machine: Machine) -> dict[str, Any]:
    """Compare one fixed version against the same three opponents."""
    matches = [
        dict(opponent=name, **play(sandbox, machine.blueprint, opponent))
        for (name, _), opponent in zip(PRESETS, presets(), strict=True)
    ]
    return {
        "rules_version": "pd-v1",
        "suite_version": "trust-v1",
        "matches": matches,
        "total": sum(m["totals"][0] for m in matches),
        "combined": sum(m["combined"] for m in matches),
    }


def arena(
    sandbox: Sandbox, machine: Machine, opponents: list[Machine]
) -> dict[str, Any]:
    """Execute a fixed selection. Failed matches never become completed results."""
    selected = opponents[:10]
    if any(not m.public_listing or m.id == machine.id for m in selected):
        raise ValueError("Arena opponents must be other public strategies.")
    if len({m.id for m in selected}) != len(selected):
        raise ValueError("Arena visitor opponents must be distinct.")
    matches = []
    for opponent in selected:
        with span(
            "arena.opponent", opponent=opponent.name, opponent_id=str(opponent.id)
        ):
            result = play(sandbox, machine.blueprint, opponent.blueprint)
        matches.append(
            dict(
                opponent=opponent.name,
                opponent_id=str(opponent.id),
                source_hash=opponent.source_hash,
                preset=False,
                **result,
            )
        )
    fixed = presets()
    for index in range(10 - len(selected)):
        slot = index % len(fixed)
        with span("arena.opponent", opponent=PRESETS[slot][0], preset=True):
            result = play(sandbox, machine.blueprint, fixed[slot])
        matches.append(
            dict(
                opponent=PRESETS[slot][0],
                opponent_id=None,
                preset=True,
                source_hash=sha256(fixed[slot].code.encode()).hexdigest(),
                **result,
            )
        )
    return {
        "rules_version": "pd-v1",
        "suite_version": "arena-v1",
        "matches": matches,
        "total": sum(m["totals"][0] for m in matches),
        "combined": sum(m["combined"] for m in matches),
    }
