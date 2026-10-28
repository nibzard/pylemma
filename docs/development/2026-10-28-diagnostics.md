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
- `npm test --prefix deploy/cloudflare`: 16 tests passed.
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

Monitor real failures using request references and the documented queries.

## Deployment investigation

The first live challenge succeeded on the previous container during image rollover.
Subsequent cold starts returned 503 after approximately thirty seconds.
Each failure followed a `container.idle_shutdown` event and produced no application span.
Restoring the previous image reproduced the failure.
The SDK increments its active request count only after container startup completes.
The existing thirty-second idle callback can therefore destroy a container during startup.

The Worker now defers idle shutdown while its existing busy flag is set.
The flag covers startup and execution and resets in the existing `finally` block.
A regression test checks that active work defers shutdown and completed work permits shutdown.
Lifecycle records include start, stop, exit code, safe stop reason, and deployment version.
Raw lifecycle errors are excluded from these records.

A local container started under the hosted memory and CPU limits with synthetic credentials.
Cloudflare denied the stored-log query with the available Wrangler credential.
Worker tail records provided the shutdown evidence instead.
No model generation was used for these checks.

After idle protection, the SDK still returned 503 while waiting for the application port.
The default port deadline is twenty seconds. Full local startup exceeded that interval at the hosted CPU limit.
The Worker now requests a bounded sixty-second port deadline and propagates request cancellation.
The regression test holds startup pending while invoking idle expiry through the actual request path.
The `container.wait` event records the request reference and configured deadline.

Container error records classify known startup exits and port deadlines without exposing raw SDK errors.

## Live verification

The new image completed a cold-start challenge with HTTP 201 in 75.93 seconds.
Replay: `9ac7f50b-63a5-4325-8c27-ce655fc325d0`.
Request reference: `7c54d435-e3e6-4b70-b1c1-dea6aecc6474`.
Worker version: `a13044a5-dd27-4e29-9283-ee7555d7ba78`.
The Logfire query returned 37 spans with this reference and deployment version.
They included the application request, storage requests, challenge, match, rounds, and decisions.
The application span recorded HTTP 201; the challenge stage was `complete`.

The configured port deadline is an SDK polling budget, not a strict wall-clock limit.
Connection attempts and execution add time. Cold startup remains slow on the lite instance.
The earlier 422 sandbox failure ran on the old image and had no runtime subtype.
Do not infer its cause from the successful check.
