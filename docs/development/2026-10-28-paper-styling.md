# Restyle the existing interface

## Objective

Replace the green palette and rounded borders with paper colors, dark ink, cobalt accents, and square borders.
Limit the implementation to colors, borders, spacing, and related styling.

## Relevant specification sections

The first-visit experience contract and sections 3 and 16 apply.
The current task changes presentation only.

## Files and contracts changed

`src/pylemma/web/static/style.css` changes the presentation of existing elements.
No public data contract changes.

## Decisions and reasons

Use a warm background and light surfaces. Use dark text for reading and cobalt for primary actions.
Use a red accent for betrayal choices. Retain text labels for both choices.
Remove rounded corners from controls, panels, choice boxes, code blocks, and score meters.
Reduce excess spacing slightly within the existing layout.

## Simplicity review

No abstraction or dependency is required. Existing selectors cover the styling changes.
The main failure modes are poor contrast, clipped text, and incorrect colors in native controls.
Visual checks cover desktop, mobile, rules, and stored results.

## Checks run and results

- Desktop visual review passed at 1280 by 900 pixels.
- Mobile visual review passed at 390 by 844 pixels.
- Browser measurements showed no horizontal overflow at either width.
- Computed styles confirmed the paper background and zero panel corner radius.
- A stored result rendered readable scores and cobalt reference meters on mobile.
- Six foreground and background checks produced contrast ratios from 5.14:1 to 14.00:1.
- The primary button contrast is 7.46:1. The betrayal text contrast is 5.18:1.
- Browser error checks returned no errors.
- `uv run --offline --locked ruff check .`: passed.
- `uv run --offline --locked ruff format --check .`: passed.
- `git diff --check`: passed.
- A content snapshot confirmed that locked offline setup and lint checks leave project files unchanged.
- Wrangler uploaded only the changed stylesheet and reported deployment version `836fb3a7-bb2a-4fec-a87e-ae59b86b5535`.
- The deployed stylesheet matches the local file byte for byte.
- Browser review confirmed the published mobile appearance.

No behavior tests were added or repeated for this stylesheet-only implementation.
No model request was made.

## Failures and verified corrections

Wrangler reported a successful deployment, then exited with status 143.
A direct comparison verified the live stylesheet instead of repeating the deployment.
No application error was observed.

## Known limits

Visual review cannot establish user preference or measured usability improvements.

## Next implementation step

Review visitor feedback on the new appearance.
