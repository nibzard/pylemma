# Live model and Logfire verification

## Objective

Verify one real match and fresh telemetry in the EU project `nibzard/starter-project`.
Relevant specification sections: 9, 10, 11, 15.3, 15.5, and 16.
The operator authorizes one match with a USD 0.20 model spending limit.
Public sharing is outside this authorization.

## Files and contracts changed

This record contains live verification evidence. No application contract changes are planned.
SDK credentials remain in the ignored `.logfire/` directory.
Local match records and trace review output remain ignored.

## Decisions and reasons

Reuse the existing runner, model adapter, and explicit tracing scopes.
Use synthetic cooperation instructions and the Optimist opponent.
The existing USD 0.16640 request reservation fits the authorized allowance.
Published model rates were checked before execution.
The existing estimate uses the published cache-write upper rate without discounts.

## Checks run and results

The Logfire CLI confirms EU organization `nibzard` and project `starter-project`.
A scoped MCP identity query succeeds after browser authorization.
`init use --name starter-project --permission send` creates the local SDK credential.
`project current` confirms the exact EU project and no ambient token override.
A query for existing `pylemma` spans returns no rows before execution.
The command `uv run --offline --locked python3 /tmp/pylemma-live-match.py` executes one real match.
The temporary harness uses the existing application runner and model adapter without automatic instrumentation.
It checks the allowance, creates a stored match, exports explicit spans, and flushes the exporter.
Its synthetic strategy is `Cooperate in every round.`

- Match: `7cdf8654-9404-40a3-b403-1152e74ba624`.
- Trace: `01a17c64d53c79359a7cfdc60ea0b12e`.
- Result: completed; ten rounds; ten requests; player 34, opponent 24.
- The model betrays twice despite the cooperation strategy. Model compliance is not guaranteed.
- Storage: ignored `live-review.sqlite3`; review snapshots: ignored `.trace-reviews/`.
- The adapter reports zero input and output tokens for every request.
  No raw response was retained, so the source of those zeros is unverified.
- The adapter therefore records USD 0.000 as its estimate. This does not establish the actual charge.
- Retain the USD 0.16640 conservative reservation until billing is reconciled.

The scoped CLI query selects completed spans for this exact service and trace.
The remote query returns all 62 spans with fresh execution timestamps.
The trace has one root, ten rounds, ten player spans, ten requests, ten opponent spans, and one completion span.
Each round also has a resolution span and a commit span.
All stored round and request references match remote span identifiers.
Every non-root span has a parent in this trace.
All remote attributes and resource attributes match local exported values after SDK JSON normalization.
No local events or span links exist.
The first comparison failed because the SDK serializes structured attributes as JSON strings locally.
Decoding attributes according to the SDK schema makes every comparison pass.
No application correction was needed.
Host and service-instance identifiers are redacted. Resources include runtime versions, architecture, and a process identifier.
A subsequent full comparison checks every observation, decision, opponent branch, score, summary, model parameter, and request reference.
The command `uv run --offline --locked python3 /tmp/pylemma-review-trace.py` passes all comparisons.
The reviewer is the coding agent on 2026-10-27; the notice version is `synthetic-live-review-v1`.
The complete exported content contains synthetic strategy text, game history, stated reasons, and runtime metadata.
No credentials, source addresses, access metadata, unrelated headers, or raw exceptions appear in the reviewed attributes.
The process identifier is runtime metadata; the host and service-instance identifiers remain redacted.
The model's round-nine stated reason incorrectly calls that round the final round.
The stored observation and outcome correctly identify round nine.
This illustrates why stated reasons must remain separate from factual round data.
Publication still requires operator acceptance of this synthetic notice and complete trace content.

`mcp link project` and `mcp link trace` return project and exact-trace URLs successfully.
These links require project access; they are not verified public links.
No application code changes occur, so the earlier passing 189 tests remain the offline evidence.
`git diff --check` passes for these documentation changes.

## Failures and verified corrections

Browser authorization initially failed because Linux Secret Service was unavailable.
Installing GNOME Keyring and starting it on the existing user bus fixes availability.
This headless session uses its memory-only collection as the default keyring.
`doctor credentials` then reports `available`, and browser authorization succeeds.
OAuth credentials disappear when this keyring service stops.

## Known limits

No public link or signed-out access has been verified.
Actual billing remains unresolved because all recorded usage values are zero.
Plan limits, project retention, and sharing permissions remain unverified.
No hosted admission or persistent budget reservation is implemented.

## Simplicity review

No abstraction or dependency is added. Existing execution and telemetry boundaries satisfy this check.

## Next implementation step

The complete exported trace comparison is finished.
Complete authorized sharing and revocation checks separately.

## Phase 2 completion audit

| Requirement | Evidence | State |
| --- | --- | --- |
| Configured model adapter | The live match completes ten model requests through the pinned adapter. | Verified |
| Bounded attempts | Offline boundary tests enforce two requests per round, including repair and transport retries. | Verified offline |
| Cost measurement | Positive counts produce estimates; zero counts now produce unknown costs. Historical charges need reconciliation. | Partly verified |
| Complete trace | All 62 exported spans match the stored match and the local export. | Verified |
| Full-trace review | Every model input, decision, policy branch, score, reference, and resource attribute is compared or inspected. | Reviewed |
| Reviewed public link | No public link exists in the stored match. | Incomplete |
| Signed-out access and revocation | The browser reaches the login page; no sharing check has run. | Incomplete |
| Account evidence | Region and project are verified. Plan, retention, and sharing permissions remain unverified. | Incomplete |

The continuation audit confirms the agent browser remains signed out after page initialization.
The official public-trace documentation still directs link creation and deletion through the project interface.
Generating a project trace URL does not create a public link or satisfy this gate.
No additional model request is needed for sharing checks while the existing trace remains available.

### Operator handoff for the existing match

Use project `nibzard/starter-project` in the EU region.
The trace identifier is `01a17c64d53c79359a7cfdc60ea0b12e`.
The stored match identifier is `7cdf8654-9404-40a3-b403-1152e74ba624`.
The database is the ignored local file `live-review.sqlite3`.

1. Open the trace and review the synthetic content and runtime metadata described in this record.
2. Record the project plan, retention, sharing permissions, chosen expiration, reviewer, and date.
3. Create a public link through **Private** in the trace details panel.
4. Open that link in a signed-out browser and verify all ten rounds and the intended trace identifier.
5. Delete the link under **Project Settings**, **Shared Traces**, and verify that signed-out access stops.
6. Create a replacement link and verify the complete trace again in a signed-out browser.
7. Supply the replacement URL and the observed results for recording with the reviewed-link CLI.

Use the [runbook](../runbooks/trace-review.md) to record the replacement URL after these checks pass.
Do not provide account passwords, session cookies, access tokens, or provider keys in the handoff.
Keep phase 3 closed until these public-access results are recorded.
