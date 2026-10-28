# Simplify inspection links

## Objective

Make the decision inspection action primary and the reviewed public example a smaller fallback.

## Relevant specification sections

The Inspect in Logfire contract, public-example contract, and section 16.1 apply.

## Files and contracts changed

Change inspection copy and layout in the browser application.
Preserve destinations, access labels, and separate click events.

## Decisions and reasons

Remove the generic explanation beneath the decision action.
Use one small paragraph: “No project access? Explore a public example”.
Keep round-finding guidance for account-required links because they do not highlight the selected span.
Omit that guidance when a public link already highlights the selected round.

## Simplicity review

Use the existing inspection component and small-text style. No new abstraction or dependency is needed.

## Checks run and results

- JavaScript module syntax check: passed.
- `node --test tests/web/*.test.mjs`: eight tests passed.
- `git diff --check`: passed.
- Browser checks confirmed one primary action and a small fallback for an account-required replay.
- A public replay showed no fallback. Its older round lacked a span reference, so round-finding guidance remained.
- Existing URL tests verified span selection for reviewed public links.
- Browser checks used stored local replays and made no model requests.

## Failures and verified corrections

None.

## Known limits

Account-required links still require visitors to find the selected round in the trace.

## Next implementation step

No further implementation is required for this copy change.

## Deployment verification

Worker version `6ca42416-c4e5-42b1-bc47-cd47511c997a` serves the updated asset.
The live JavaScript matched the local file byte for byte.
A browser opened the completed arena replay and confirmed one primary inspection action and the small public-example fallback.
The account access statement appeared once. Round-finding guidance remained for the account-required link.
Checks left tracked and unignored file fingerprints unchanged.
