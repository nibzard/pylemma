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

Run offline checks, deploy, and measure one hosted generation.
