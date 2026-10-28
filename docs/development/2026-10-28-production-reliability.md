# Recover builds and introduce a comparable arena

## Objective

Recover interrupted builds, report actual stages, explain results, and introduce a consistent twenty-round arena.

## Relevant specification sections

Machine creation, hosted boundaries, simple arena, observability, and sections 16.1 and 16.2 apply.

## Files and contracts changed

Add durable build references, a read-only progress endpoint, browser recovery, and versioned arena rules.
Preserve stored players and replay results.
New players use arena-v2 with ten fixed opponents and twenty rounds.

## Decisions and reasons

See decision 010.
A reference identifies one build attempt; retrying it cannot reserve another generation.
Actual stages come from the Worker and application, not timers.
Legacy players retain arena-v1. Historical tournaments and direct challenges retain ten rounds.
Compare only matching arena versions. Display points per round.

## Simplicity review

Use the existing Durable Object and request identifier.
A small durable build record replaces a separate queue or job service.
Polling reads do not start the container or consume generation quota.
No automatic provider retries or new dependencies are needed.
Tests must cover duplicate requests, interrupted responses, immutable records, rule versions, and browser recovery.

## Checks run and results

- Full offline Python suite: 250 tests passed.
- Worker suite: 24 tests passed.
- Browser unit suite: 15 tests passed.
- Ruff lint and format checks: passed for 43 files.
- Mypy: passed for 42 source files.
- JavaScript module syntax and git diff checks: passed.
- File fingerprints before and after checks: unchanged.
- Docker build and registry push: passed.
- CPU-limited Docker benchmark with local tracing: twenty-round arena medians of 0.909–0.923 seconds.
- Ten-round benchmark medians: 0.406–0.478 seconds.
- Browser direct entry with a fake builder completed a 501-point, twenty-round-per-opponent arena.
- Browser recovery with a simulated status endpoint made zero POST requests and displayed the actual checking stage.
- Recovery opened the saved preview and cleared its pending reference.
- Confirmed that the browser restores its draft without restoring the consent checkbox.

## Failures and verified corrections

The initial type check found a reused variable with different blueprint and machine types.
Distinct names corrected the type error.
One API test expected the old arena score for a newly created player.
The new fixed suite scores an always-cooperating player at 501; legacy tests retain 273.
A browser fixture required an async wrapper for its evaluation script.
Review found a save-versus-execution race: progress could complete before the build released its execution slot.
The finishing stage and a regression test now cover that boundary.
Initial formatting checks found long lines and import ordering; corrected checks passed.

## Known limits

A recorded attempt cannot safely restart automatically after an uncertain provider outcome.
New rules do not retroactively change stored code.
A local benchmark cannot establish hosted latency.
Direct challenges and historical tournaments intentionally remain at ten rounds.
Session storage is scoped to the current browser tab; another browser needs the saved reference.
Cloudflare runtime replacement can still interrupt unfinished work.

## Next implementation step

Complete offline checks and one bounded hosted generation and arena verification.
