# Daily generation limit

## Objective

Raise the hosted daily generation limit to 100, as requested by the operator.

## Relevant specification sections

The hosted deployment contract, spending controls, and section 16.1 apply.

## Files and contracts changed

Update Worker admission, storage reservations, container configuration, boundary tests, and the deployment runbook.

## Decisions and reasons

Keep the USD 4 lifetime reservation budget. Reduce the per-attempt reservation to USD 0.01.
This permits 400 lifetime attempts and 100 daily attempts without increasing the monetary allowance.
Today's 20 recorded requests cost an estimated USD 0.002104 at current standard model rates.
The 2,400-token output cap and bounded input keep an ordinary request below the new reservation.
Retain existing counters and the separate challenge limits of 400 daily and 1,600 lifetime runs.
The status endpoint values all generation counts at the current reservation rate.

## Simplicity review

Use constants in the existing storage module for shared hosted limits.
Duplicated admission values could reject requests that storage permits.
No new module or configuration layer is needed. Boundary tests cover daily and lifetime rejection.

## Checks run and results

- `npm test --prefix deploy/cloudflare`: 19 tests passed.
- `uv run --offline --locked pytest tests/test_remote_store.py tests/test_machines.py -q`: 20 tests passed.
- `git diff --check`: passed.
- File fingerprints before and after checks matched for tracked and unignored files.
- The hosted container was inactive before deployment, so its next start receives the new environment value.

## Failures and verified corrections

None.

## Known limits

Reservations are conservative accounting, not provider-enforced billing limits.
The lifetime limit remains finite and does not reset at midnight.

## Next implementation step

Run boundary checks, deploy, and verify admission without a model request.
