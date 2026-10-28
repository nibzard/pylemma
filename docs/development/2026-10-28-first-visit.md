# Explain the game to first-time visitors

## Objective

Teach the choices before creation. Explain stored outcomes and make shared games the first content on their pages.

## Relevant specification sections

The machine release contract, Cloudflare deployment contract, and sections 3 and 16 apply.

## Files and contracts changed

`web/static/index.html`, `style.css`, and `app.js` provide the revised visitor flow.
`web/static/story.mjs` derives factual explanations and version-specific score comparisons.
`web/app.py` adds preview creation and confirmed tournaments.
The Cloudflare Worker validates and forwards the new operation. Its image reference identifies the deployed build.
`tests/test_machines.py` and `tests/web/story.test.mjs` cover the new contracts and explanations.
An optional preview creation mode stores a validated machine without running its tournament.
A tournament endpoint runs that stored version without a new model request.
Existing creation requests retain their current behavior.

## Decisions and reasons

Put the demonstration before the form on small screens. Use complete example strategies and a default name.
Show a generated summary before execution so visitors can check the translated rules.
Use stored choices for factual explanations. Keep explanations separate from generated reasons.
Show fixed reference scores only for the matching opponent suite.
Keep technical information in optional details. Show Logfire links only when reviewed references exist.

## Simplicity review

The current requirement needs instruction, confirmation, and interpretation.
The current form and raw round records do not provide these steps.
One browser module handles rendering. One pure module derives factual explanations from stored records.
An optional request field preserves existing clients. One endpoint handles the new confirmation step.
Failures include lost invitation context, duplicate submission, and incorrect interpretation of a result.
Tests cover preview boundaries, no additional generation, factual explanations, and browser navigation.

## Checks run and results

- `uv run --offline --locked pytest -q`: 215 tests passed.
- `uv run --offline --locked ruff check .`: passed after correcting a long test string.
- `uv run --offline --locked ruff format --check .`: passed.
- `uv run --offline --locked mypy`: passed for 32 source files.
- `node --test tests/web/story.test.mjs`: three tests passed.
- `npm test --prefix deploy/cloudflare`: two tests passed.
- `node --check src/pylemma/web/static/app.js`: passed.
- `node --check deploy/cloudflare/worker.js`: passed.
- `uv build --offline --no-build-isolation`: wheel and source archive built.
- A ZipFile inspection confirmed that the wheel contains all four browser assets.
- `git diff --check`: passed.
- A content snapshot confirmed that locked offline setup and lint checks leave project files unchanged.
- The deployment image built with host networking, uploaded, and deployed through Wrangler.
- Browser checks covered the local demonstration, preview, confirmation, reload, revision comparison, and challenge invitation.
- Local browser generation used a fake builder and a private database. It required no credentials.
- Desktop and mobile screenshots received visual review. Mobile width was 390 pixels.
- Existing public replay and challenge links opened on their result or invitation before the form.
- A live confirmed tournament completed with 80 points using a previously stored machine.
- Its remote Logfire trace contains one tournament, three matches, thirty rounds, and sixty decisions.
- That trace contains no generation span.
- One authorized live preview generated a new challenger. Confirmation completed its ten-round challenge with a draw.
- The challenge target survived a browser reload before confirmation. Browser error checks returned no errors.

Deployment version: `1fca8047-de6d-43ed-8579-7f1954fe214f`.
Image digest: `sha256:b50f682a6814c643c6688a1c12b8e28b1df9c6dbb870102bc41951ee5b0f8379`.

Verified tournament replay: `2ad1e486-d401-409d-a422-951ec590b233`.
Verified tournament trace: `01a1820d3e2c51346f7e9740e4d3a26e`.
Verified challenge replay: `89ed2c03-c706-40b6-b581-73e32093f56b`.
The live preview retains its existing USD 0.05 generation reservation. No allowance was increased or reset.

## Failures and verified corrections

Lint found a long string in the reference-score test. Splitting the string corrected the check without changing its behavior.
Local review found that confirmation could leave the introductory content above the rule summary.
The preview now uses its own view. Reload and confirmation checks passed.
Native score meters had inconsistent rendering. Explicit meter styles corrected the presentation.
The share button now reports successful copying directly in its label.
A revision check initially stopped at the required public-record acknowledgement. Checking it allowed the intended flow to continue.

## Known limits

User testing with people unfamiliar with the game remains necessary.
The interface changes do not establish measured improvement in understanding.

## Next implementation step

Run comprehension tests with visitors unfamiliar with the game. Measure whether they can explain their choices and results.
