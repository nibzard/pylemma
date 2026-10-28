# Correlated runtime diagnostics

## Objective

Make browser, Worker, application, provider, and sandbox failures diagnosable from safe records.

## Relevant specification sections

Sections 3, 16, the machine contract, and runtime feedback apply.
Preserve explicit telemetry and full review before public trace publication.

## Files and contracts changed

Changed correlation headers, bounded browser failure reports, request spans, and execution-stage attributes.
Updated the specification, architecture, and diagnostic runbook.

## Decisions and reasons

Use one UUID request reference across the browser, Worker, and application.
Treat browser reports as untrusted observations, not authoritative failures.
Record safe routes, statuses, stages, limits, and exception categories.
Do not record raw URLs, headers, request bodies, exception messages, or stack traces in diagnostic events.
Existing permitted game trace data remains subject to its existing publication review.

## Simplicity review

The previous failure lacked a sandbox error subtype and a browser-to-server reference.
Extend existing spans and request boundaries. A streaming protocol or new service is not needed.
Diagnostic failure must not change game results. Tests cover failure isolation and data minimization.

## Checks run and results

- `uv run --offline --locked pytest`: 243 tests passed.
- `npm test --prefix deploy/cloudflare`: 14 tests passed.
- `node --test tests/web/*.test.mjs`: eight tests passed.
- `uv run --offline --locked ruff check .`: passed.
- `uv run --offline --locked ruff format --check .`: 38 files unchanged.
- `uv run --offline --locked mypy`: passed for 38 files.
- `uv build --offline --no-build-isolation`: wheel and source archive built successfully.
- `node --input-type=module --check < src/pylemma/web/static/app.js`: passed.
- `git diff --check`: passed.

File hashes before and after checks and builds were identical for tracked and unignored files.
A local browser simulated a connection failure without calling a model.
Its displayed reference matched the accepted diagnostic report. The report contained only four permitted fields.
Sandbox tests verified both a missing-key error and an execution timeout through actual SDK spans.
Worker tests verified correlation, redaction, quota outcomes, report validation, and logging failure isolation.
The Docker build and registry push succeeded.

## Failures and verified corrections

The extracted limit dictionary needed the existing Monty ResourceLimits type for strict type checking.
A new parameterized test initially reused its fixed missing-key fixture for both cases.
Using the supplied case verified the execution-timeout subtype. The full suite then passed.

## Known limits

A browser report can be lost if the connection remains unavailable.
Request references correlate events but do not authenticate visitors.

## Next implementation step

Implement, test, document query examples, and deploy the instrumentation.
