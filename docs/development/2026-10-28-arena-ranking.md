# Lead with points and rank

## Objective

Show total points and rank so visitors can immediately see the score to beat.

## Relevant specification sections

Arena-v2 comparisons, public discovery, and section 16.1 apply.

## Files and contracts changed

Add a ranked view of public arena-v2 results.
Keep chronological and historical APIs available.
Rank the entire comparable set before pagination.
Expose the requested public player's current standing independently of the page.

## Decisions and reasons

Higher total scores rank first because every ranked entrant faces the same schedule.
Ties share a competition rank: 1, 1, 3.
Only public arena-v2 entries participate.
Ranks are current read data, not mutations to immutable replays.
Points per round move into expandable details.
Remove the always-cooperate reference from the primary experience.

## Simplicity review

Reuse the existing public ranking and pagination functions.
No stored ranking table, background jobs, or additional service is required.
Existing ranking functions satisfy the requirement with an arena filter and an optional player lookup.
No additional abstraction is needed.
The new failure boundary is the standing request; its failure leaves the score visible.
Tests cover ties, pagination, exclusions, and a player outside the selected page.
Architecture documentation records the read contract.

## Checks run and results

- `uv run --offline --locked pytest -q`: 251 passed.
- `node --test tests/web/*.test.mjs`: 18 passed.
- `npm test --prefix deploy/cloudflare`: 27 passed.
- Ruff checks and formatting passed. Mypy passed for 42 source files.
- JavaScript syntax and `git diff --check` passed.
- Local browser: scores descend from 564 to 425, with ranks 1 through 5.
- Mobile browser: document width equals the 390-pixel viewport.
- Additional API validation checks passed in the three public game tests.
- Docker image built and pushed successfully.

## Failures and verified corrections

The new Worker test initially wrote summaries under the arena lookup prefix.
Corrected the fixture to use the public summary prefix; all Worker tests passed.
Formatted the additional API assertions after the formatter identified their layout.

## Known limits

Rank changes when new strategies enter.
It measures performance against this fixed opponent set, not general ability.

## Next implementation step

Verify the ranked view, result page, and sharing text, then deploy.
