# Normalize the handle prefix

## Objective

Add @ when a visitor enters a handle without it.

## Relevant specification sections

Machine creation, simple arena entry, and section 16.1 apply.

## Files and contracts changed

The browser normalizes the handle when focus leaves the field and before submission.
Stored players and the general name API remain unchanged.

## Decisions and reasons

Trim surrounding whitespace and preserve an existing @ prefix.
Leave empty input empty so normalization cannot supply a name.
Use one function for both browser events.

## Simplicity review

One small browser module makes the formatting rule testable without the page.
No dependency, account lookup, or additional validation policy is needed.
Tests cover both formats, repeated normalization, whitespace, and empty input.

## Checks run and results

All ten browser tests passed. The two handle tests also passed after matching the existing .mjs convention.
JavaScript syntax and git diff checks passed.
File fingerprints matched before and after checks.

## Failures and verified corrections

None.

## Known limits

This formatting rule does not verify account ownership or existence.

## Next implementation step

Deploy and verify the static assets.
