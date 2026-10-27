# Match tracing and reviewed links

## Objective

T006 implements local preparation for development round 2.
Relevant specification sections: 7.4, 9.2, 11, 15.3, and 16.
Execution needs nested spans, stored references, safe failures, and reviewed-link management.
Live verification and publication remain in T007 through T009.

## Intended contracts and simplicity review

One telemetry module owns the Logfire boundary and task-local tracing context.
The existing runner cannot export spans or attach execution references.
One wrapper isolates telemetry failures without changing Game contracts or the Player protocol.
Its failure modes include missing exports and unavailable trace references.
Offline exporter tests and a full-trace review runbook must cover that boundary.
The existing database fields support trace references and reviewed links without a migration.

## Files and contracts changed

- `telemetry.py` adds optional Logfire configuration, isolated match context, safe span attributes, and execution references.
- `application/runner.py` adds the specified hierarchy and emits scores only after a successful commit.
- `player/model.py` records permitted request inputs, validated decisions, repair instructions, safe errors, usage, and cost estimates.
- `records/sqlite.py` stores or removes reviewed public references without changing replay outcomes.
- `records/links.py` validates HTTPS and exact allowed hosts.
- `cli.py` requires a review acknowledgement before recording a link.
- `tests/integration/test_telemetry.py` adds executable offline export and CLI checks.
- `pyproject.toml` and `uv.lock` add Logfire 4.41.0 and its resolved dependencies.
- `.gitignore` excludes local Logfire authentication and trace-review output.
- The README, architecture, public-access decision, and review runbook describe the current behavior.

## Decisions and reasons

The [public-access decision](../decisions/003-public-trace-access.md) records sharing capabilities, published plan limits, and unverified questions.
Logfire supplies the required trace exporter and span timing.
The wrapper catches telemetry failures but preserves application exceptions.
It never supplies raw exceptions to Logfire, which would otherwise record exception details.
Explicit spans avoid exporting provider headers, HTTP bodies, and unrelated access metadata.
The runner separates the root from inherited request context and baggage.
Task-local context prevents concurrent matches from sharing a root.

Inspection found default SDK host identifiers in resource attributes.
The project configuration masks host and service-instance identifiers and source paths.
It rejects custom resource metadata and detectors from environment settings.
Full-trace review remains necessary before publication, including SDK resource attributes.
The wrapper does not claim that a locally generated identifier proves delivery.
Only an explicitly reviewed public reference represents public access.

## Checks and results

The focused trace suite passed all 20 tests with network sockets disabled.
It inspects actual SDK exports using an in-memory exporter and mock provider transport.
The retry case verifies 63 spans, ten committed rounds, eleven requests, and all stored parent references.
It compares permitted history, structured output, usage, retry flags, and repair instructions.
Credential, access, header, and raw-response sentinels are absent from match attributes.
Tests also cover failed requests, failed commits, exporter exceptions, disabled tracing, concurrent matches, and SDK entry failures.
Link checks cover unsafe URLs, explicit review acknowledgement, replacement, repeatable removal, and unchanged replay data.

Final verification used Python 3.14.3:

| Command | Actual result |
| --- | --- |
| `uv sync --locked` | Passed; 60 packages resolved and 58 audited. |
| `uv run --offline --locked python3 -c 'import pylemma; print(pylemma.__version__)'` | Printed `0.1.0`. |
| `uv run --offline --locked pytest -q` | All 189 tests passed. |
| `uv run --offline --locked ruff check .` | Passed. |
| `uv run --offline --locked ruff format --check .` | All 23 files passed. |
| `uv run --offline --locked mypy` | All 23 source files passed. |
| `uv build --offline --no-build-isolation` | Built both archives in ignored `dist/`. |
| `git diff --check` | Passed. |

A script compared file names and SHA-256 hashes around setup, checks, and builds.
All 47 tracked and unignored files remained unchanged during verification.
No generated build artifact is tracked.
Test databases use private temporary directories and `LOOPER_RESOURCE_PREFIX` names.
No external resource was created. Existing cleanup registrations were not changed.

## Failures and verified corrections

Initial formatting and import checks found layout issues; Ruff corrected them.
Mypy rejected an untyped keyword expansion for source metadata and a concurrent-result return annotation.
Using the existing typed attribute mapping and a tuple return annotation corrected both errors.
The final type check and full suite passed after these corrections.
An SDK inspection exposed default host metadata before the final privacy checks.
Masking those identifiers passed exported-resource assertions.

## Editorial review

Review consulted the official [Issue 9 rules and dictionary](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf).
The PDF and extracted text remain in ignored `.verification/` output.
The review used rules 5.1 and 6.1, dictionary entries, and the architecture term list.
This review does not claim independently certified compliance.

## Known limits and next implementation step

No paid model request, remote telemetry export, or public publication ran.
T007 supplies account access and an authorized allowance.
T008 verifies a real complete match, actual exports, cost, and every trace attribute.
T009 verifies signed-out access, revocation, and a fresh reviewed link.
These external round 2 gates remain open; offline checks do not replace them.
No automatic sharing endpoint or anonymous project access is assumed.
The optional public-project experiment remains in T024 after release.

The CLI does not fetch links or verify their contents.
Operators must compare each complete trace with the intended match before storing its reference.
The conservative allowlist rejects unknown regional hosts and URL parameters until reviewed.
Trace retention, account sharing entitlements, and actual project limits remain unverified.
The local developer example remains in T019; hosted budgeting remains in T013.
