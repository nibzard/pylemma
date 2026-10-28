# Replace the rating scale with a measured reference

## Objective

Remove the misleading out-of-five presentation from results and sharing.

## Relevant specification sections

Arena-v2 comparisons, public discovery, and section 16.1 apply.

## Files and contracts changed

Show average points per round without a denominator.
Use the tested always-cooperate score as the current arena reference.
Game rules, points, and stored records remain unchanged.

## Decisions and reasons

Five is an individual-round maximum, not an attainable average across the fixed opponents.
The always-cooperate policy scores 501 over 200 rounds, displayed as 2.51.
Use that measured reference without suggesting a universal threshold or percentile.

## Simplicity review

Change existing presentation strings and reuse one reference sentence.
No new score system or abstraction is required.

## Checks run and results

All 17 browser tests passed, including sharing text and the baseline rounding check.
JavaScript syntax and git diff checks passed. File fingerprints were unchanged by checks.

## Failures and verified corrections

A browser assertion had an escaped regular-expression syntax error.
Literal text checks corrected the verification script and passed.

## Known limits

The reference applies only to the current fixed arena.
It is not a promise about games against other opponents.

## Next implementation step

No further work is required for this presentation change.


## Live verification

Worker version: 65f3a9e6-eabf-494c-a7f1-43ed4baf8a21.
Both deployed JavaScript assets match the checked local files.
The live results page shows points per round and the 2.51 always-cooperate reference.
The rendered page contains no out-of-five score labels.
The container image and stored results are unchanged.
No model or game execution requests were made.
