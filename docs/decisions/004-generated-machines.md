# Generate reusable machines

Status: accepted. Date: 2026-10-28.

## Problem

The original game provides limited reasons to create, revisit, or share a strategy.
Per-round model requests also make a strategy less stable across challenges.

## Constraints

Logfire must be required for hosted operation. Ordinary tests remain offline.
The game must remain understandable without code knowledge.

## Options considered

- Keep per-round model decisions against presets.
- Generate code once and run reusable machines against presets and visitor machines.

## Decision

Use generated machines, fresh Monty sessions, a fixed tournament, and challenge links.
Keep pd-v1 scoring and ten-round matches.
Require explicit Logfire configuration at hosted startup.
Keep pure scoring and historical replay reads independent of telemetry export.

## Reason

A stable machine gives visitors something to name, revise, and share.
Challenges give recipients an action. The tournament rewards points across varied opponents.

## Consequences

Generated code adds execution failures and translation errors.
Sample validation cannot establish correct interpretation of visitor instructions.
Machine versions and completed replays use a separate SQLite contract.
Historical match records retain their existing contracts.

## Evidence links

- [Monty](https://github.com/pydantic/monty)
- [Public traces](https://pydantic.dev/docs/logfire/observe/public-traces/)
- [Development evidence](../development/2026-10-28-machines.md)

## Conditions for reconsideration

Reconsider the game if visitors do not revise machines or respond to challenges.
Reconsider storage and scheduling if measured load exceeds one-process capacity.
