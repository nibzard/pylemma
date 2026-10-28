# Confirm generated rules before execution

Status: accepted. Date: 2026-10-28.

## Problem

The original creation request runs a tournament before the visitor can check the generated interpretation.
New visitors also receive scores without reference points or explanations of turning points.

## Constraints

Keep existing clients and stored replays compatible. Keep generation within the existing spending allowance.
Separate generated reasons from factual explanations. Do not require coding knowledge.

## Options considered

- Show the summary after the existing complete tournament.
- Split generation and execution for all existing API clients.
- Add an optional preview mode and an explicit tournament operation.

## Decision

Add preview mode and a tournament endpoint. The browser confirms the generated summary before running a stored version.
Preserve existing creation behavior when preview is false.
Teach choices through a local demonstration. Derive result explanations from completed choices.
Show shared games first and preserve earlier replays when revising rules.

## Reason

Visitors can correct the interpretation before play. Confirmation does not require another model request.
Existing API clients and unlisted links continue to work.

## Consequences

A preview can exist without a completed tournament. It remains an immutable stored version.
Tournament execution shares the existing challenge allowance.
The browser must preserve invitation targets and comparison references across reloads.
Reference scores apply only to the matching versioned opponent suite.

## Evidence links

- [First-visit contract](../../SPEC.md#first-visit-experience-contract)
- [Development evidence](../development/2026-10-28-first-visit.md)

## Conditions for reconsideration

Reconsider the instructions after observing comprehension tests with visitors unfamiliar with the game.
