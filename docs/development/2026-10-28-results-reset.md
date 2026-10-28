# Clear previous results

## Objective

Remove all previous game results at the user's explicit request.

## Relevant specification sections

Hosted storage, public discovery, and section 16.1 apply.
The operator-requested reset is an explicit exception to retaining immutable replays.

## Files and contracts changed

Delete replay records, public summaries, and arena completion references.
Keep machines, build recovery records, daily reservations, and lifetime reservations.
Run the reset once when the Durable Object initializes.

## Decisions and reasons

Use one transaction and a dated completion marker.
The marker prevents a restart or later deployment from deleting new results.
Block incoming operations until the transaction finishes.
Remove arena references so they cannot point at deleted replays.
Do not change quota reservations or infer authorization to reset spending allowances.

## Simplicity review

Use the existing storage boundary and its transaction support.
No permanent public deletion endpoint, credential rotation, or new service is needed.
A regression test checks preservation, bounded batches, and one-time execution.

## Checks run and results

Before cleanup, the public games endpoint reported 25 results.
All 25 Worker tests passed.
The cleanup test deletes more than one batch and preserves players, recovery records, and counters.
A second invocation preserves a result created after the reset.
Git diff checks passed, and file fingerprints matched before and after checks.

## Failures and verified corrections

The first read after deployment still reached the previous Durable Object version and reported 25 results.
After deployment propagation, the same endpoint reported zero.

## Known limits

Previous replay links will no longer open.
Saved players remain available, including legacy players.
Logfire traces are outside this database cleanup.

## Next implementation step

No further cleanup is required.


## Live verification

Worker version: 449db312-2663-4629-b54d-6fe3aeb7bd08.
The games, arena, and leaderboard endpoints each returned zero entries.
All 25 previously listed replay identifiers returned HTTP 404.
One additional unlisted replay also returned HTTP 404.
A saved player and its completed build recovery record remained readable.
No generation or challenge requests were made during verification.
The container image is unchanged.
