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

None.

## Known limits

The reference applies only to the current fixed arena.
It is not a promise about games against other opponents.

## Next implementation step

Deploy and verify the public presentation.
