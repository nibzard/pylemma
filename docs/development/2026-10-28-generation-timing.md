# Measure generation latency

## Objective

Separate client preparation, connection, first content, and response completion for the reported 25-second generation.

## Relevant specification sections

The generation contract, diagnostic correlation contract, and section 16.1 apply.

## Files and contracts changed

Use provider streaming internally, retain complete blueprint validation, and record safe elapsed timings on the existing generation span.
The browser continues to receive one completed response.

## Decisions and reasons

Record monotonic elapsed times and process CPU time without raw network metadata.
HTTPX hooks expose connection events; the first nonempty content chunk measures when generated text reaches the application.
Streaming changes response delivery, so measurements describe new calls and cannot reconstruct the earlier request.
One hosted generation is authorized for this measurement, within the existing quota and USD 0.01 reservation.

## Simplicity review

One local timing record and context-local hooks preserve the existing HTTP connection pool.
No automatic instrumentation, tracing service, or browser streaming protocol is required.
Tests must cover fragmented content, usage, timeouts, cleanup, and metadata exclusion.

## Checks run and results

- `uv run --offline --locked pytest -q`: 246 tests passed.
- `uv run --offline --locked ruff check .`: passed.
- `uv run --offline --locked ruff format --check .`: 39 files unchanged.
- `uv run --offline --locked mypy`: passed for 39 source files.
- `git diff --check`: passed.
- File fingerprints before and after checks matched for tracked and unignored files.
- Docker build and registry push passed.

## Failures and verified corrections

The first type check required narrowing a numeric telemetry attribute in the test. The corrected check passed.

## Known limits

The provider does not expose queue time or internal computation time here.
Process CPU time includes other threads in the application process.
Connection timings include local scheduling. DNS is not measured separately from TCP connection setup.

## Next implementation step

Use these measurements to target local client preparation and cold startup before changing models.

## Hosted measurement

Deployed Worker version `66a55870-c5b5-4a48-9f4d-39c0b4abb553`.
The container information endpoint confirmed image `94037f95d430ddd1fd6625fb1a37d6b1cadd9d90ce6b4f41e289b14616e4719c` before the call.
One unlisted preview generation returned HTTP 201 in 29.350618 seconds.
Request reference: `a18fc3c9-36c4-4ed6-a5ac-cfad69e3bce3`.
The initial Logfire query preceded ingestion. A later query returned the completed spans with the expected deployment version.

| Interval | Seconds |
| --- | ---: |
| Generation start to HTTP dispatch | 13.054270 |
| Dispatch to request body sent | 0.300710 |
| TCP connection setup | 0.099225 |
| TLS handshake | 0.103046 |
| Request body sent to first nonempty content | 2.104505 |
| First content to stream completion | 1.699518 |
| Stream completion to blueprint validation | 0.000333 |
| Complete generation span | 17.254449 |
| Complete application request span | 18.621225 |
| External request elapsed | 29.350618 |

Connection rows are subdivisions of dispatch-to-send time, not additional intervals.
The application boundary excludes approximately 10.73 seconds of external latency, including startup, proxying, and transport.
Process CPU time was 1.456997 seconds overall and 1.314678 seconds before dispatch.
The 13.05-second pre-dispatch interval proves that local preparation dominates this generation sample.
CPU throttling on the 1/16-CPU instance is a plausible contributor; these measurements do not isolate its exact share.

Usage was 240 input tokens and 174 output tokens, with zero reasoning or cache tokens.
At standard model prices, estimated provider cost was USD 0.000111 against the USD 0.01 reservation.
No further model calls were made for this measurement.
This streamed sample does not prove the timing breakdown of the earlier non-streamed request.
