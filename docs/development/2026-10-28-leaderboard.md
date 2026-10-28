# Public leaderboard and game history

## Objective

Rank completed public tournaments and provide a paginated history of completed public games.

## Relevant specification sections

The machine release, first-visit, and Cloudflare deployment contracts apply.
The leaderboard contract supersedes the original exclusion of global rankings for this phase.

## Files and contracts changed

Add an immutable public-listing flag to new machines. Missing flags preserve unlisted behavior.
Add bounded read endpoints for rankings and public game history.
Index small public summaries with each completed replay in durable storage.
Local SQLite derives the same summaries from stored replay records.

## Decisions and reasons

Tournament scores share a fixed opponent suite. Rank these scores together and give equal scores equal ranks.
Keep every qualifying tournament entry, including repeated games by the same player.
Challenges appear in chronological history because opponents can differ.
Require explicit listing consent. Existing unlisted games remain unlisted.
A challenge appears publicly only when both players permit listing.
Public reads do not execute code, call a model, or start the Cloudflare container.

## Simplicity review

Public discovery needs a read model that the current replay lookup does not provide.
One pure summary module per runtime and small storage methods provide this boundary.
Compact index entries avoid loading full replay histories on each public request.
The added failure modes are incorrect ranking, pagination errors, and unintended listing.
Tests cover consent, ties, completion, suite versions, pagination, and index persistence.
No new dependency is required.

## Checks run and results

- `uv run --offline --locked pytest -q`: 217 tests passed.
- `uv run --offline --locked ruff check .`: passed.
- `uv run --offline --locked ruff format --check .`: passed.
- `uv run --offline --locked mypy`: passed for 34 source files.
- `node --test tests/web/story.test.mjs`: three tests passed.
- `npm test --prefix deploy/cloudflare`: three tests passed.
- `node --check src/pylemma/web/static/app.js`: passed.
- `node --check deploy/cloudflare/worker.js`: passed.
- `uv build --offline --no-build-isolation`: wheel and source archive built.
- `git diff --check`: passed.
- A content snapshot confirmed that locked offline setup and lint checks leave project files unchanged.
- The deployment image built and uploaded. Wrangler completed deployment after one retry.
- Local browser checks used fake generation and 25 public fixture games with one unlisted game.
- The first page displayed twenty rows. The second displayed five rows and a previous-page link.
- A new listed player completed a local tournament and increased the visible total to 26.
- Mobile review at 390 pixels showed no document overflow. The table scrolls within its own region.
- Browser error checks returned no errors.
- The live leaderboard and public history returned empty pages before new consented games completed.
- One authorized live generation created a listed player, The open hand.
- Its completed tournament earned 81 points and appeared in both public endpoints.
- Another public game completed during verification. Presence checks therefore use the expected replay identifier.
- An old unlisted replay remained readable through its URL and absent from public results.

Deployment version: `3a89b819-1a1e-4d79-8e69-3592f4051211`.
Image digest: `sha256:23a3aeca12638d8ff5b99065d595bd6983f42ebf3a69293ea178a2e7ffd2784f`.
Verified public replay: `bb4976a0-f335-4fec-b795-ac279ce7feb4`.
The verification used the existing generation allowance. No allowance was increased or reset.

## Failures and verified corrections

Wrangler uploaded the Worker and assets, then returned an internal error during the container rollout.
A retry completed the rollout and the new live generation flow succeeded.
A live verification initially assumed exactly one public entry. Another public game completed during the check.
The corrected check verifies the expected replay and score without assuming a fixed live total.

## Known limits

Names are visitor supplied. Rankings compare games against the fixed suite and do not verify human identity.
Older unlisted games do not enter the public directory.

## Next implementation step

Observe use of the public board. Review repeated submissions before changing ranking rules.
