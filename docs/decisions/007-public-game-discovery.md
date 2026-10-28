# Rank public tournaments and list completed games

Status: accepted. Date: 2026-10-28.

## Problem

Visitors cannot compare their games with other completed games or discover players to challenge.
Existing records were created under an unlisted-link notice.

## Constraints

Keep older records unlisted. Preserve explicit consent for public discovery.
Compare the same opponent suite and rules. Keep public reads independent of model requests and container startup.
Do not increase the spending allowance.

## Options considered

- Rank every result together, which compares different challenge opponents.
- Publish all existing records, which changes their promised visibility.
- Rank consented tournaments and list consented games in a separate chronological view.

## Decision

Use a false-by-default immutable listing flag for new machines.
Rank complete public tournaments against trust-v1 under pd-v1. Equal scores share a rank.
Keep every completed tournament entry. List public tournaments and challenges in a paginated history.
Require listing consent from both challenge participants.
Write a compact public index alongside each qualifying replay in the existing Durable Object transaction.

## Reason

The tournament provides a common comparison. The separate history includes other public games without changing that comparison.
Compact summaries keep public reads small and avoid loading complete replay histories.
The existing storage and application boundaries are sufficient.

## Consequences

Existing unlisted games remain accessible through their links and do not appear in the public directory.
Listing consent applies to an immutable player version. A new version can use a different listing choice.
Repeated games can occupy multiple rows. Names are visitor supplied and do not verify identity.
Offset pages can change as new public games complete.

## Evidence links

- [Leaderboard contract](../../SPEC.md#public-leaderboard-contract)
- [Development evidence](../development/2026-10-28-leaderboard.md)
- [Durable Object transactions](https://developers.cloudflare.com/durable-objects/api/legacy-kv-storage-api/)

## Conditions for reconsideration

Reconsider ranking per player if repeated submissions reduce the usefulness of the board.
Reconsider pagination after measured growth beyond the current bounded game volume.
