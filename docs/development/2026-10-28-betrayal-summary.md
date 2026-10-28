# Correct the betrayal summary

## Objective

Remove contradictory first-betrayal statements from match summaries.

## Relevant specification sections

The observability, completed result, and section 16.1 contracts apply.

## Files and contracts changed

The browser distinguishes a first betrayal from a repeated betrayal.
Stored scores, choices, and replays remain unchanged.

## Decisions and reasons

Check earlier recorded choices before calling a response the player's first betrayal.
Use "betrayed again" when the player already betrayed.
Do not infer intent from a recorded choice.

## Simplicity review

One condition in the existing summary function resolves the error.
No abstraction or dependency is needed.

## Checks run and results

All sixteen browser tests passed, including the new regression case.
Git diff checks passed. File fingerprints were unchanged by checks.

## Failures and verified corrections

The supplied result described round one and round three as the player's first betrayal.
The regression case reproduces that opening sequence.

## Known limits

The summary describes choices, not the player's motives.

## Next implementation step

Deploy the static correction and verify the public asset.
