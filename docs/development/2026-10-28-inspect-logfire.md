# Inspect a game in Logfire

## Objective

Show a prominent Inspect in Logfire action for completed games and distinguish public access from account access.

## Relevant specification sections

The machine release, first-visit, and public leaderboard contracts apply.
The reviewed public trace decision and runbook govern anonymous sharing.

## Files and contracts changed

Add a configured project URL and reviewed public trace references to replay read models.
Prefer reviewed public links. Otherwise, link to the exact trace with an explicit sign-in message.

## Decisions and reasons

The supported Logfire link tool verifies the trace filter and time parameters.
Project visibility alone does not establish anonymous access. The current project redirects signed-out visitors to login.
A connected-app browser handoff is supported, but its granted access cannot open the project's sharing controls.
The user supplies a public URL from the normal account's sharing interface.
A fresh signed-out browser verifies read-only trace access. The root identifies the expected game and trace.
Official access documentation confirms that public projects are public within the organization.
A normal Logfire account does not by itself give an outsider project access.
Public references can be configured without changing immutable replay records or exposing a credential.

## Simplicity review

The requirement needs trace navigation on every completed result.
The existing conditional footer link disappears when no reviewed public reference exists.
One pure link function per deployed runtime provides the replay read model.
The added failure modes are invalid links, missing configuration, and incorrect access labels.
Tests cover URL validation, trace filtering, time hints, public precedence, and unavailable traces.
No new dependency is needed.

## Checks run and results

- `uv run --offline --locked pytest -q`: 231 tests passed.
- `uv run --offline --locked pytest -q tests/test_trace_links.py`: thirteen initial link and API checks passed before the highlight case was added.
- `uv run --offline --locked ruff check .`: passed after correcting a long error string.
- `uv run --offline --locked ruff format --check .`: passed.
- `uv run --offline --locked mypy`: passed for 36 source files.
- `npm test --prefix deploy/cloudflare`: seven tests passed.
- `node --test tests/web/story.test.mjs`: three tests passed.
- JavaScript syntax checks passed for the browser, Worker, and link helper.
- `uv build --offline --no-build-isolation`: wheel and source archive built.
- `git diff --check`: passed.
- A content snapshot confirmed that locked offline setup and lint checks leave project files unchanged.
- Local browser checks show the action near the result and the correct public or account-required access label.
- The supported Logfire link tool returns the exact trace filter and time parameters used by this implementation.
- The supplied public URL opens in a fresh browser context without a Logfire account.
- Its raw root record identifies replay `bb4976a0-f335-4fec-b795-ac279ce7feb4` and trace `01a18279f80e04757e90f2b753321bc4`.
- All 94 exported records match the expected structure: one tournament, three matches, thirty rounds, and sixty decisions.
- Every exported decision and its observation match the stored replay.
- Resource identifiers are redacted. The reviewed records contain no HTTP metadata or exceptions.
- The configured provider credential and bearer credential patterns do not occur in the reviewed export.
- The Worker and updated container deploy successfully.
- Hosted replay responses return the expected public URL for the reviewed game and account-required links for other games.
- Clicking the live button from a fresh browser session opens the expected read-only public trace without sign-in.

Deployment version: `52f006ae-2834-43d5-9c99-1aa93f4e4304`.
Image digest: `sha256:4a47c04a5acf4277a7b6fdc92cef32b0e74269c01bef49fc4d5363c0814bebad`.
Public URL: https://logfire-eu.pydantic.dev/public-trace/44e57f30-c25a-47fe-b85f-5db1d0604010?spanId=4ed36f7dff63d8fe
The inspection work makes no provider request and does not change the spending allowance.

## Failures and verified corrections

The Logfire CLI has no `api spec` command. Its documented project commands require explicit beta configuration.
The first handoff parser expected a JSON object, while the tool returned a URL string.
Handling the documented string result opened the supported handoff without exposing its temporary URL.
The handoff is intentionally limited and cannot open the full sharing interface.
The user-created public link resolves that limitation for the verified example.
The existing validator rejected its valid `spanId` parameter. A narrow verified-path exception now preserves it.
A review script used the system interpreter, which could not import the editable package.
Running it through the locked project environment completed all comparisons.
Lint found a long error string. Splitting it corrected the check.

## Known limits

A normal signed-in Logfire session is required to create each public trace link through the documented interface.
Automatic public sharing remains unavailable through the verified supported contracts.
Account-required links still require project access. Project visibility does not grant outsiders access.
The supplied public link was not revoked or replaced during verification.
Public URLs remain subject to Logfire expiration, revocation, and telemetry retention.
Do not expose a connected-app handoff URL as a public link.

## Next implementation step

Use the documented operator process for additional public references. Reconsider automation only after a supported sharing contract is verified.
