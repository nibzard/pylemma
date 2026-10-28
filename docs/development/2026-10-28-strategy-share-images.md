# Strategy share images

## Objective

Give each completed run a distinctive image for sharing on X.
Keep visible text to the handle, score, brand, and invitation.

## Relevant specification sections

The current machine release, publication, immutable replay, and section 16.1 contracts apply.

## Files and contracts changed

The Worker serves versioned PNG images from recorded choices.
Replay URLs include server-rendered Open Graph and X metadata.
The browser shares replay URLs and provides a direct challenge action.

## Decisions and reasons

Use a small pixel renderer with a fixed bitmap alphabet and native compression.
Each recorded round supplies one colored square.
No model, container, font download, or new dependency is needed.
Keep changing ranks and long strategy descriptions off the image.
Unlisted results remain accessible through their existing unlisted identifiers.

## Simplicity review

The requirement needs crawler-readable PNG images and HTML metadata.
Static assets cannot represent a particular saved run.
One Worker module provides rendering and share metadata.
The new failure modes are invalid records, image rendering, and crawler caching.
Validate completed records and test PNG decoding, metadata escaping, and stored-only reads.
Document the image route, palette, caching, and sharing contract.

## Checks run and results

- Python tests: 251 passed.
- Wrangler deployment dry run passed.
- Worker tests: 33 passed, including pixel mapping, PNG decompression, metadata escaping, cache reuse, and stored-only requests.
- Browser logic tests: 18 passed.
- Ruff checks and formatting passed; mypy passed for 42 source files.
- JavaScript syntax and `git diff --check` passed.
- Tracked and unignored file fingerprints remained unchanged across checks.
- Rendered and inspected the real 564-point result: PNG size 10,375 bytes, dimensions 1200 by 630.
- Local render measured about 65 milliseconds, including writing the preview file.
- Browser verified initial metadata, loaded image, replay share URL, and direct challenge link.
- Mobile document width equals its 390-pixel viewport; the image fits within its card.

## Failures and verified corrections

The cache test initially tried to mock a global absent from Node.
Added an explicit fake cache with cleanup; all Worker tests then passed.

## Known limits

X controls when it fetches and displays link previews.
The fixed image alphabet supports ASCII; other characters use a replacement glyph.
Images use recorded outcomes and do not claim to measure general ability.

## Next implementation step

Implement, test, inspect the actual image, and deploy.

## References

Cloudflare documents native deflate compression in its
[Web standards reference](https://developers.cloudflare.com/workers/runtime-apis/web-standards/).
The former X large-image card documentation redirects to its general documentation overview.
Validation therefore checks actual metadata and image responses without claiming X preview approval.
