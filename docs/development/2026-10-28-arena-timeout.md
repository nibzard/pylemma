# Arena execution timeout

## Objective

Fix the arena timeout reported with request reference `a2b212f8-2139-43b0-8e74-900f85eb4250`.

## Relevant specification sections

The machine execution contract, simple arena contract, diagnostics contract, and section 16.1 apply.

## Files and contracts changed

Raise the existing sandbox feed budget from 0.05 to 0.5 seconds.
Retain the two-second host deadline, memory limit, recursion limit, and fresh sessions.
Record the entrant identifier when an arena span starts, including failed runs.
Update the specification, operational guidance, and failed-arena trace test.

## Decisions and reasons

Logfire identifies a Monty RuntimeError with TimeoutError subtype during decision execution.
The configured feed duration was 0.05 seconds. The failing decision span lasted 0.198 seconds.
The source hash matches a bounded policy using history and a final-round condition.
The failure occurred in round seven against the second selected opponent.
There is no evidence of a provider failure or an invalid decision.

## Simplicity review

Prefer adjusting the existing duration limit over retries or changes to scoring.
Memory, recursion, process isolation, and the host request deadline must remain enforced.

## Checks run and results

An offline Docker run used the recorded source and observation at 256 MiB and 1/16 CPU.
All 200 repeated decisions passed without competing host work. The production failure is intermittent.
With a competing CPU thread, 200 decisions passed at each duration limit.
The original limit took 29.0 seconds; the new limit took 33.4 seconds.
These runs did not reproduce the intermittent timeout and do not prove its scheduling cause.
The production trace remains the evidence for the failing limit.
- `uv run --offline --locked pytest -q`: 243 tests passed.
- `uv run --offline --locked mypy`: passed for 38 source files.
- `uv run --offline --locked ruff format --check .`: 38 files unchanged.
- `uv run --offline --locked ruff check .`: passed after correcting test import order.
- `git diff --check`: passed.
- The tracked and unignored file fingerprints matched before and after the checks.
- Docker build and registry push passed.
- The updated image completed ten matches and 100 rounds using the entrant and the recorded opposing policy.
  This offline run used the hosted CPU and memory limits, scored 270, and completed execution in 0.6 seconds.
- The stored entrant matched the source hash in the failing trace.

## Failures and verified corrections

The first diagnostic query used incorrect source attribute names. The corrected query retrieved source by its verified hash.
The first lint check found unsorted imports in the extended test. Sorting the imports corrected the failure.

## Known limits

A timing failure depends on scheduling and may not reproduce in an isolated run.

## Next implementation step

Test execution under contention, apply the smallest bounded correction, and verify deployment.
