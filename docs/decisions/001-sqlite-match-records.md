# Store match records in SQLite

## Status and date

Accepted for development round 1 on 2026-10-27.

## Problem

A replay must preserve match results independently of model availability and Logfire retention.
Outcome storage and match progress must succeed or fail together.

## Constraints

`SPEC.md` sections 8.4 and 9 require SQLite, ordered migrations, short transactions, and one application process.
The Game context owns scores and legal state transitions.
Unknown usage and cost must remain unknown.

## Options considered

- Standard-library SQLite with explicit SQL and validated record contracts.
- An object-relational mapping library over SQLite.
- An external database service.

## Decision

Use the standard-library `sqlite3` adapter with packaged, numbered SQL migrations.
Store immutable settings and validated record payloads as JavaScript Object Notation (JSON).
Use relational keys for match identity, round uniqueness, attempt order, and parent references.
Keep status, progress, timestamps, and trace references in the match row.

Enable write-ahead logging, foreign keys, a five-second lock timeout, and full synchronous writes.
Each write operation uses `BEGIN IMMEDIATE` and closes its connection after commit or rollback.
Each replay read uses a read transaction with `query_only` enabled.
The adapter has no provider callback and cannot hold a transaction around a model request.

Apply all pending migrations in one transaction.
Store each applied migration's number, filename, and SHA-256 digest.
Reject changed migration history instead of silently accepting a different schema.
SHA-256 is the 256-bit Secure Hash Algorithm.

## Reason

SQLite satisfies the specified deployment model without another service or runtime dependency.
Explicit SQL keeps transaction ownership visible.
Validated JSON preserves nested settings and observations without separate tables for every value.
Relational keys enforce duplicate rejection and parent existence.

## Consequences

The hosted database requires a persistent local volume and one application worker.
A second writer can wait briefly for the first transaction.
Database errors propagate to the caller; the adapter returns no uncommitted result.

Replay reads reconstruct the Game aggregate and verify stored scores, totals, observations, attempts, and progress.
They do not fetch traces or call a model.
Unavailable trace references do not prevent replay reads.
Estimated cost uses decimal values. A missing attempt value makes the corresponding round aggregate unknown.

Attempts commit separately before outcomes, preserving failed requests without adding points.
The caller supplies actual request parameters and completed request metadata.
The provider adapter must enforce request limits across its own retries.

Admission and event tables start with T013 and T015, when their contracts are implemented.
Startup interruption and reservation reconciliation remain in T014.
Reviewed trace-link editing remains in T006.
Future migrations must preserve existing records.

## Evidence

- [Specification](../../SPEC.md), sections 8, 9, and 15.2.
- [Development record](../development/2026-10-27-match-records.md).
- [Storage boundary tests](../../tests/integration/test_records.py).

## Conditions for a new decision

Reconsider storage if multiple application processes or remote database access become required.
Reconsider JSON payloads if measured reporting needs cannot use the current relational fields.
Do not add a storage framework without a demonstrated requirement.
