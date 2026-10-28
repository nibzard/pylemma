# Runtime failures and progress feedback

## Objective

Diagnose reported hosted errors and give visitors clear progress and recovery messages.

## Relevant specification sections

The simple arena contract and sections 3, 5, 16 apply.
Preserve bounded execution, public trace review, and immutable results.

## Files and contracts changed

Changed browser progress, request errors, generation deadline, and safe failure diagnostics.

## Decisions and reasons

Use real request stages and an indeterminate indicator. Do not invent round counts or percentages.
Generation and validation share one request, so display them as one stage.
The installed container library already protects requests from idle shutdown. No additional lifecycle change is needed.
Record safe exception classes without raw errors, credentials, or visitor text.

## Simplicity review

Existing request boundaries provide useful progress without a streaming protocol.
One browser module can render stages and elapsed time.
Timers must stop on success and failure. Tests cover error mapping and stage selection.
No runtime dependency is added.

## Checks run and results

Live health and stored reads succeeded. The Worker tail showed successful reads and later creation requests.
Logfire showed one failed initial sandbox decision at 15:07 UTC after successful generation.
The generated blueprint passed the existing local sandbox checks unchanged.
Five fresh sandboxes also passed in Docker with 256 MiB and 0.0625 CPUs.
The historical error did not include its exception class. Its exact cause remains unconfirmed.

## Failures and verified corrections

The Logfire CLI was not on PATH. The existing project wrapper provided read-only queries.

## Known limits

No new provider request is needed for ordinary verification.
A visible indicator cannot report server internals that the request does not expose.

## Next implementation step

Check safe failure classes if the sandbox error recurs.

## Implementation checks

The full offline Python suite passed 238 tests before the final diagnostic assertions were added.
JavaScript checks passed seven browser tests and eleven Worker tests.
Lint, formatting, and strict type checks passed.
A delayed fake builder showed the pending indicator and actual stages in a local browser.
The indicator stopped after the result opened.
A simulated browser Load failed error produced a recovery message, retained the description, and enabled another submission.
No browser script errors were reported.
The 45-second total generation deadline allows the observed 32-second response while bounding the whole provider request.
The original sandbox failure remains unconfirmed. Safe exception classes improve diagnosis of any recurrence.

Final targeted checks passed 45 Python tests, including the new failure-class assertions.
Commands: `uv run --offline --locked pytest tests/test_machines.py tests/integration/test_telemetry.py` and `node --test tests/web/*.test.mjs`.
`docker build --network host -t pylemma:deploy .` and the Cloudflare registry push succeeded.
Image digest: `sha256:0f9ca7f145cc919ef7af83ff1e2c78a0d5e32ca6e654bf1e7b8271578976cf52`.

## Deployment

Commit `5da05bd` and its notes were pushed to `main`.
Cloudflare deployed version `80a81ace-ba8d-475b-a748-12d5cad0f390` with the pinned image.
The live progress module matched the local file byte for byte.
A hosted browser opened an existing player, requested its saved arena entry, and loaded the result successfully.
The completed request showed the expected stages and stopped the activity indicator. No script errors occurred.
No model generation request was made during this verification.
