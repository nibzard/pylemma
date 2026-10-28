# Reduce cold-start time

## Objective

Reduce the delay before player creation starts.

## Relevant specification sections

Machine creation, hosted boundaries, observability, and section 16.1 apply.

## Files and contracts changed

Change the shared model identifier, build bytecode, container size, idle policy, and readiness diagnostics.
Request, storage, model, quota, and sandbox contracts remain unchanged.

## Decisions and reasons

The previous cold generation took 102.16 seconds overall but only 8.37 seconds inside the application.
Importing the model identifier currently loads the historical AI player and its dependencies.
Move that identifier into a small shared configuration module.
Compile Python bytecode during the image build, where the files are writable.
Measure cold startup and warm execution separately.
Use basic instead of lite for four times the CPU capacity.
Keep the single container warm for five idle minutes instead of thirty seconds.
This limits repeated startup during a play session.
Provisioned memory and disk cost USD 0.000834 per five idle minutes before allowances; CPU is additional.
No quota or spending allowance is increased.

## Simplicity review

A constant module removes an unnecessary dependency between two implementations.
No new service, queue, retry, or provider request is needed.
A subprocess regression test can check the import boundary.
Existing tests cover both model consumers.

## Checks run and results

The live baseline challenge returned HTTP 201 in 83.157316 seconds without a model request.
Reference: cc4fc422-3ae7-42f2-baad-6aa2432da9c1.
Offline Docker imports and generator construction with network disabled:
- Previous image at 0.0625 CPU: 40.499 seconds.
- Revised image at 0.0625 CPU: 15.595 seconds.
- Revised image at 0.25 CPU: 3.912 seconds.

These are single observations, not latency distributions.

- Full offline pytest suite: 247 passed.
- Ruff lint and format checks: passed.
- Mypy: passed for 41 files.
- Worker tests: 19 passed.
- Browser unit tests: eight passed.
- Git diff check: passed.
- File fingerprints before and after checks: unchanged.
- Docker build and registry push: passed.

## Failures and verified corrections

The first type check required an explicit re-export of MODEL_ID for existing consumers.
The corrected check passed.

## Known limits

Local CPU limits approximate available compute but do not reproduce Cloudflare scheduling or image startup.

## Next implementation step

Measure the revised image and verify a hosted challenge without a model request.
