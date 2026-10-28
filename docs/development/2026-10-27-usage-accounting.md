# Conservative model usage accounting

## Objective

Fix misleading zero cost after the real match reports zero tokens for nonempty requests and decisions.
Relevant specification sections: 8, 9.3, 10, 13, 15.2, 15.5, and 16.
Unknown usage must remain unknown through attempts, round aggregates, evaluations, and telemetry.
No additional paid model request is authorized by this task.

## Files and contracts changed

The model adapter must validate reported counters before treating usage as known.
The reviewed-link allowlist must accept the verified EU project host.
Its existing rejection rules for unknown hosts and redirect parameters remain in force.
Offline boundary tests cover zero counters and evaluation aggregates.
The README, architecture, model decision, and trace evidence must explain the limits.

## Decisions and reasons

A nonempty prompt and a nonempty decision require positive input and output token counts.
Treat a nonpositive reported counter as unavailable, while preserving a valid counter from the same response.
Do not estimate usage from text length or describe an unknown charge as free.
Do not rewrite the historical live replay or its exported trace.

## Simplicity review

The existing usage-object presence check cannot distinguish zero placeholders from usable counters.
The existing decision function can preserve counter availability without a new module or dependency.
The added failure mode is conservative unknown accounting for anomalous provider reports.
Boundary tests and cost documentation cover that behavior.

## Checks run and results

Before implementation, four new usage checks fail because zero counters produce known zero cost.
After implementation, `uv run --offline --locked pytest tests/integration/test_model.py -q -k zero_usage` passes all four checks.
The trace and CLI checks initially expose rejection of the verified EU host.
Adding that exact host makes the boundary checks pass without relaxing other URL restrictions.
`uv run --offline --locked pytest tests/integration/test_model.py tests/integration/test_telemetry.py -q` passes all 71 checks.

Final checks use Python 3.14.3:

| Command | Actual result |
| --- | --- |
| `uv sync --offline --locked` | Passed; 60 packages resolved and 58 audited. |
| `uv run --offline --locked python3 -c 'import pylemma; print(pylemma.__version__)'` | Printed `0.1.0`. |
| `uv run --offline --locked pytest -q` | All 198 tests passed. |
| `uv run --offline --locked ruff check .` | Passed. |
| `uv run --offline --locked ruff format --check .` | All 23 files passed. |
| `uv run --offline --locked mypy` | All 23 files passed. |
| `git diff --check` | Passed. |

A SHA-256 comparison confirms all 46 tracked and unignored files remain unchanged during final setup and checks.
The count includes this record and the earlier live verification record.
No credentials, databases, build artifacts, or trace snapshots enter Git.
No new paid request or telemetry export runs during this correction.

The full live trace review checks all ten observations, decisions, opponent branches, requests, scores, and stored references.
The [live record](2026-10-27-live-logfire.md) contains its results and limitations.

Editorial review uses the official ASD-STE100 Issue 9 PDF, rule 5.1, descriptive-writing rules, and dictionary entries.
The PDF and extracted text remain outside the repository.
This review does not claim certified compliance.

## Failures and verified corrections

The live record has zero usage for all ten requests.
The fix preserves each positive counter independently and makes cost unknown when either counter is unavailable.
Tests verify unchanged valid decisions, no extra requests, unknown round aggregates, evaluation reservations, and null trace values.
The EU CLI tests verify link replacement, removal, and unchanged replay data for all three allowed hosts.
No raw provider response was retained, so its precise origin cannot be established retroactively.
The dependency maps missing usage to zero; offline tests must distinguish these cases.

## Known limits

Actual charges for the historical live match remain unverified.
Keep the conservative reservation until billing is reconciled.
The agent browser reaches the Logfire login page despite valid CLI authorization.
The supported MCP tools expose project and trace links but no public-sharing operation.
No private endpoint or CLI credential is used to bypass browser login.
The operator must supply browser access or perform sharing, revocation, and replacement through the supported interface.
Project plan settings and retention also remain unverified.
Phase 3 remains gated on verified public trace access.

## Next implementation step

Complete browser authentication, record account settings, and verify public sharing, revocation, and a replacement link.
