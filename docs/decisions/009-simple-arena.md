# Use recent strategies for a simple arena

Status: accepted. Date: 2026-10-28.

## Problem

The fixed opponents provide limited reasons to share a strategy or return to play.
The desired funnel leads from a surprising game result to Logfire inspection.

## Constraints

Keep one process, bounded execution, public consent, immutable machines, and reviewed trace publication.
Keep old endpoints and replays readable. Avoid accounts and scheduled tournaments.

## Options considered

- Continue the fixed tournament as the main entry.
- Select the highest ranked strategies and accumulate points.
- Select recent public strategies and save one result per strategy.

## Decision

Use ten recent distinct public strategies with completed games. Fill empty slots with existing presets.
Save one completed entry per strategy. Show recent results without ranks.
Make code preview optional. Offer a factual inspection highlight and share controls after execution.

## Reason

Recent strategies supply changing opponents. One saved result prevents repeated play from accumulating points.
Chronological results avoid implying equal opponents across entries.

## Consequences

Each arena executes 200 bounded decisions. Existing execution allowances still apply.
A failed participant stops the entry without a completed result.
A strategy revision has a new identifier and can enter again.
Public trace creation remains manual. Automatic public inspection is not established by this change.

## Evidence links

- [Development record](../development/2026-10-28-arena.md)
- [Arena contract](../../SPEC.md#simple-arena-contract)
- [Trace access decision](008-inspect-game-trace.md)

## Conditions for reconsideration

Reconsider scheduling if visitors need comparable rankings across changing opponents.
Reconsider publication only when a supported automatic sharing contract is verified.
