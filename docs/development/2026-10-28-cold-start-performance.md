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

Monitor real requests for latency variation and remaining cold-start failures.


## Hosted verification

Worker version: 00a97618-234a-4e22-bbab-e51f366a9e93.
Image digest: 1b24ccda7d43540a91bef56685ed63ca219b595281e0f05733290ab0e00642d0.
Container information confirmed the new image, 0.25 CPU, and healthy status before testing.
All requests below returned HTTP 201.

| Request | External seconds | Application seconds |
| --- | ---: | ---: |
| First challenge after rollout | 9.765489 | 0.848402 |
| Warm challenge | 1.747942 | 0.893969 |
| Warm player preview build | 4.016603 | 3.370257 |
| Arena for that player | 5.382388 | Not queried |

The baseline challenge took 83.157316 seconds.
The first request after rollout took 88 percent less time.
This comparison includes startup, proxying, transport, and execution; it is not a pure startup measurement.
Each number is one observation, not a percentile or guarantee.

The generation span took 2.984048 seconds, with dispatch after 24.162 milliseconds.
Its first content arrived after 1.539 seconds.
Logfire confirmed the deployed version for the challenge and generation requests.
One unlisted generation used the existing USD 0.01 reservation.
The challenge and arena checks made no model requests.

References:
- First challenge: c9d75429-a705-461e-b4b1-35ad371e23ec.
- Warm challenge: 97b69d25-04bb-4f34-b279-89e72e842b22.
- Player build: 6d366f16-0d83-49b5-aaba-a5fc6a27a622.
- Arena: 5e9d37a9-7fd7-4fb2-9f9b-5f70bc7a09eb.
