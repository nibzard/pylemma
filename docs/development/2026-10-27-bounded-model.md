# Bounded model adapter

## Objective and scope

T005 implements the model adapter for development round 2.
Relevant specification sections are 7.2, 8, 9.3, 10, 15.2, 15.5, and 16.
The adapter must return real model decisions within two requests per round.
It must retain request metadata after success and failure.
Live execution, trace review, and publication remain separate tasks.

## Files and contracts changed

- `player/model.py` implements the fixed model, separate prompts, native structured output, bounded retries, and cost estimation.
- `player/service.py` adds attempt metadata to results and safe failures.
- `records/models.py` separates request metadata from storage identifiers without changing stored field names.
- `application/runner.py` stores all attempts and aggregates known usage before committing outcomes.
- `evaluate.py` provides explicit live evaluations with a spending allowance and JSON reports.
- `tests/integration/test_model.py` exercises the real provider adapter and SDK through an offline HTTP transport.
- `pyproject.toml` and `uv.lock` pin compatible model dependencies.
- `.gitignore` excludes `.evaluations/` reports.
- The README, architecture document, and model decision describe the implemented contracts.

## Decisions and simplicity review

The [model decision](../decisions/002-model-and-retry-limits.md) records the provider, identifier, prices, and retry policy.
The existing fake player cannot issue model requests or preserve multiple attempts.
One adapter module satisfies the current provider requirement.
An explicit loop avoids coordinating retries across an agent loop and the SDK.
The shared metadata contract avoids copying storage validation into the Player context.
No migration, second provider, agent tools, or dependency framework is added.

The response override preserves missing usage before library normalization.
Its failure risk is dependence on a protected library method.
The locked dependencies and HTTP boundary tests verify that method and the actual request parameters.
The additional dependencies supply the required Pydantic AI provider integration.
The evaluation command uses Game contracts directly and writes one report to standard output.
No evaluation platform is necessary.

## Checks and results

The focused adapter suite passed all 34 tests with internet sockets disabled.
Tests exercise actual SDK request construction through an HTTP mock transport.
They cover invalid choices, missing reasons, blank reasons, excessive lengths, unknown fields, truncation, and refusal.
They verify trimmed output, separate system and visitor input, native schema, absent tools, and exact generation parameters.
Mixed validation and transport failures share the two-request ceiling.
Ten repaired rounds issue exactly twenty HTTP requests.
Authentication and quota errors issue one request and stop.
Connection failures, timeouts, and server failures retain safe categories and unknown charges.

Storage tests retain repair attempts, usage, estimated costs, and partial scores.
Replay reads issue no model requests.
Evaluation tests check positive finite allowances, repetition limits, explicit opt-in, credentials, reports, and unknown costs.
No paid model request or telemetry export ran.

Final checks ran on Python 3.14.3:

| Command | Actual result |
| --- | --- |
| `uv sync --locked` | Passed; 46 packages resolved and 44 audited. |
| `uv run --offline --locked python3 -c 'import pylemma; print(pylemma.__version__)'` | Printed `0.1.0`. |
| `uv run --offline --locked pytest` | All 161 tests passed with internet sockets disabled. |
| `uv run --offline --locked ruff check .` | Passed. |
| `uv run --offline --locked ruff format --check .` | All 19 files passed. |
| `uv run --offline --locked mypy` | All 19 source files passed. |
| `uv build --offline --no-build-isolation` | Built the wheel and source archive in ignored `dist/`. |
| `git diff --check` | Passed. |

A Python script compared file names and SHA-256 hashes before and after setup, checks, and builds.
All 40 tracked and unignored files remained unchanged, including supplied task context files.
No generated artifact is tracked.
Tests use private temporary databases named with `LOOPER_RESOURCE_PREFIX`.
Existing ignore rules cover environments, caches, builds, databases, and editorial reference output.

## Failures and verified corrections

The first dependency resolution selected OpenAI SDK 3.39.0, which requires an HTTPX2 client.
Pydantic AI 1.107.0 uses the HTTPX client contract at this boundary.
An attempted SDK 2.26.0 pin failed because Pydantic AI requires at least 2.29.0.
Pinning SDK 2.29.0 resolved the type mismatch and passed the HTTP tests.
The initial papercut report named 2.26.0 before verification; the verified correction is 2.29.0.

Two initial tests exposed Pydantic AI's wrapping of SDK connection errors as `ModelAPIError`.
The adapter now classifies that wrapper and distinguishes its timeout cause.
Both tests passed after this correction.
Mypy also identified a mutable-list type mismatch in test setup.
An explicit union annotation corrected it without changing the assertions.
Ruff formatting corrected source layout before the final formatting check.

## Editorial review

Review consulted the official [Issue 9 rules and dictionary](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf).
The site homepage returned HTTP 403 through the browser tool.
The direct official PDF downloaded successfully into ignored `.verification/` output.
`pdftotext` supplied the word rules, procedure limits, descriptive rules, and dictionary entries, including `RECORD`.
The review used these rules and the architecture terms. It does not claim independent certification.

## Known limits and next implementation step

Provider account access and live quality remain unverified.
T007 supplies credentials, model access, a Logfire project, and an authorized spending allowance.
T006 adds instrumentation. T008 verifies a complete real match and reviews its trace.
T009 remains the public-access exit gate for development round 2.
These external checks do not block T005's local implementation.

The provider currently lists no dated snapshot for `gpt-6-luna`.
Its fixed identifier does not guarantee unchanged provider behavior.
Prices require review before live authorization.
Hosted budget persistence, reservation settlement, and restart handling remain in T013 and T014.
No external resource was created, and no cleanup registration was changed.

## Review repair: execution settings

The round 2 repair covers specification sections 5.5, 8.1, 10, and 16.1.
Stored provider, model, parameters, and system prompt version must match the selected player before execution.
Incompatible settings must raise a specific error before a request or storage transition.
The existing Player protocol can own this check; no additional abstraction is required.
Each adapter validates its own settings, so the runner does not import provider constants.
The new protocol method requires explicit support from custom players.
Boundary tests must cover each mismatch and compare completed records with actual HTTP requests.

The repair adds `validate_settings` to the existing Player protocol and both adapters.
The runner calls it before the running transition. The evaluation command also validates its generated settings.
Fake settings require `fake-v1` for both the model and system prompt version.
The README, architecture document, and model decision describe the compatibility requirement.
Existing test players inherit the fake validation method.

Seven rejection cases cover provider, model, system version, missing parameters, changed limits, extra parameters, and incorrect value types.
Each case leaves the stored replay unchanged and sends zero requests.
A positive test accepts different JSON formatting and key order.
It completes ten rounds with scores of 30/30 and compares every request with stored settings and attempt parameters.

Repair verification results:

| Command | Actual result |
| --- | --- |
| `uv run --offline --locked pytest tests/integration/test_model.py tests/integration/test_runner.py` | All 54 tests passed. |
| `uv sync --locked` | Passed; 46 packages resolved and 44 audited. |
| `uv run --offline --locked python3 -c 'import pylemma; print(pylemma.__version__)'` | Printed `0.1.0`. |
| `uv run --offline --locked pytest` | All 169 tests passed with internet sockets disabled. |
| `uv run --offline --locked ruff check .` | Passed after correcting one long line and import order. |
| `uv run --offline --locked ruff format --check .` | All 19 files passed. |
| `uv run --offline --locked mypy` | All 19 source files passed. |
| `uv build --offline --no-build-isolation` | Built both archives in ignored `dist/`. |
| `git diff --check` | Passed. |

The final verification script compared file names and SHA-256 hashes around setup, checks, and builds.
All 40 tracked and unignored files remained unchanged.
Existing ignore rules cover all generated output; no build artifact was added to tracked files.
Editorial review consulted the official Issue 9 PDF, including rules 5.1 and 6.1 and dictionary entries.
The browser returned HTTP 403; `curl` downloaded the official PDF into ignored `.verification/` output.
No paid requests, external resources, or telemetry exports were used.
The existing live verification limits and next tasks remain unchanged.
