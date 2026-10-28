# Explain results for new visitors

## Objective

Make public results and sharing text understandable without prior game knowledge.

## Relevant specification sections

Public discovery, arena-v2 comparisons, and section 16.1 apply.

## Files and contracts changed

Public player summaries include their submitted strategy.
Existing summaries receive strategy text from their public saved player during reads.
The recent results table shows the strategy and explains the score scale.
Homogeneous current results omit internal version labels.
Mixed formats retain visible labels.

## Decisions and reasons

Use the submitted rules rather than inventing a strategy title.
Show a short excerpt with access to the full text.
Explain the common opponent set, match length, and points per round.
Describe individual scores in sharing text; do not claim an unmeasured comparison.

## Simplicity review

Extend the existing read model and rendering functions.
No generation request, new database, or new service is needed.
Read enrichment preserves existing results and visibility decisions.

## Checks run and results

- Four Python tests covering public records and arena-v2 passed.
- All 26 Worker tests passed, including enrichment of existing public summaries.
- All 17 browser tests passed, including sharing text, truncation, and decimal rounding.
- Ruff lint and format checks passed; mypy passed for 42 source files.
- JavaScript module syntax and git diff checks passed.
- File fingerprints matched before and after checks.
- Browser checks used the two current public entries as read-only fixtures.
- Desktop columns show Player, Strategy, Score, Replay, and Challenge.
- A mixed-format fixture retained Current arena and Earlier arena labels.
- Long strategies offered their full text in an expandable control.
- At a 390-pixel viewport, the page width remained 390 pixels and the result list fit its 354-pixel container.
- Docker build and registry push passed.

## Failures and verified corrections

The first mobile layout clipped the score and wrapped the handle.
Stacking the fields at narrow widths corrected both issues.
Existing floating-point formatting displayed 517 / 200 as 2.58.
Rounding the scaled integer score first correctly displays 2.59 without changing stored points.

## Known limits

Submitted strategy text can differ from generated behavior.
A score is an average of game points, not a percentile or quality rating.

## Next implementation step

No further work is required for this presentation change.


## Live verification

Worker version: f31e2841-0f6f-49d1-84d1-21ac3bc9b2da.
Image digest: bd6b000e39561ac489a3c60ee25c4fdc8c395c21dbeaf239264e94722744a101.
Container information confirmed the new image and healthy state.

Both existing public replay identifiers and their stored scores were preserved.
The public read endpoint supplied their original strategy text.
The browser showed Player, Strategy, Score, Replay, and Challenge columns.
The two scores displayed as 2.59 / 5 and 2.13 / 5.
The current-only page did not show internal arena version labels.
At a 390-pixel viewport, the list fit its 354-pixel container without page overflow.
No model generation or game execution requests were made.
