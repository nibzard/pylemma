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

Monitor completion, request latency, and inspection clicks using the documented events.


## Hosted verification

Worker version: fa5f0ee4-60bd-472b-9105-3a55f3cb0c90.
Image digest: e2d948e96e6538a98642ed4f873e2a54937e067186222a3a07699ffb13898626.
Container information confirmed the new image and healthy state before testing.
The public build module matched the checked local asset.

One unlisted preview generation used the existing USD 0.01 reservation.
The client intentionally disconnected after 3.008 seconds.
Polling observed starting, generating, saving, and complete stages.
Completion became visible 12.125 seconds after submission.
The short checking and finishing stages were not sampled by this one-second poll.
A browser fixture separately verified checking-stage display.

Repeating the same reference and input returned the same machine in 0.125 seconds.
Changed input under that reference returned HTTP 409.
The arena completed ten matches of twenty rounds in 5.872 seconds.
Repeating the arena request returned the same replay in 0.135 seconds.

Logfire recorded exactly one generation span for the build reference.
It took 5.117 seconds and used 284 input tokens and 435 output tokens.
The arena span recorded completed=true and took 4.570 seconds.
Both application requests reported the deployed Worker version.

The live browser displayed 509 points, points per round, a recorded cooperation recovery, and the adjacent Logfire action.
It showed ten expandable groups of twenty rounds.
The legacy replay retained arena-v1, 297 points, and ten matches of ten rounds.
No existing player or replay was rewritten.

References:
- Build: b49e57c3-061f-4a90-9bc2-00f89325fe44.
- Arena request: 776369cf-e35f-4fea-9332-f8ca827d5eaf.
- New replay: eab8b4f1-e8fc-4565-a4f2-2b80ad933897.
- Legacy replay: 390e52e3-2ed2-461f-82f3-9402af76545d.

These timings are individual observations, not latency percentiles.
