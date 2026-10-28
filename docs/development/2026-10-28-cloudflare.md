# Cloudflare deployment

## Objective

Deploy the machine game at pylemma.aor.fyi within the authorized spending allowance of USD 5.

## Relevant specification sections

The machine release contract and sections 3 and 16 apply.

## Files and contracts changed

Deployment adds a Worker, one container, and durable records outside the temporary container disk.

## Decisions and reasons

Keep Python and Monty in a Linux container. Serve static assets directly from the Worker.
Store machines, replays, quotas, and lifetime spending reservations in a SQLite-backed Durable Object.
Reserve USD 0.05 before each generation against a lifetime USD 4 allowance.
Keep failed reservations. Bound output to 2,400 tokens and use standard model processing.
The remaining USD 1 provides a buffer for verification and infrastructure usage.
This application limit does not cap unrelated account spending or provider price changes.

## Simplicity review

Current requirements need Linux binaries and records that survive container replacement.
The local SQLite implementation cannot preserve records on a temporary disk.
One remote store adapter and one Worker storage module provide the required boundary.
Added failures include network errors, authentication errors, and container startup errors.
Tests must cover remote contracts, atomic reservations, restart persistence, and public browser behavior.

## Checks run and results

- `uv run --offline --locked pytest -q`: 213 tests passed.
- `uv run --offline --locked ruff check .`: passed.
- `uv run --offline --locked ruff format --check .`: passed.
- `uv run --offline --locked mypy`: passed for 32 source files.
- `npm test --prefix deploy/cloudflare`: two storage tests passed.
- `node --check deploy/cloudflare/worker.js`: passed.
- `docker build --network host -t pylemma:deploy .`: passed.
- A deployment-image probe validated a preset through the real Monty runtime.
- Wrangler dry run, image push, and deployment completed successfully.
- Browser checks created two named strategies and displayed their tournaments.
- Desktop and mobile screenshots received visual review. The mobile viewport was 390 by 844 pixels.
- The browser opened a challenge invitation and its permanent replay without errors.
- Live challenge requests returned status 201 with scores of 30 and 30.
- Existing machine and replay records survived the container image replacement.
- The instance list reported an inactive container before a later successful challenge request.
- A remote Logfire query returned all 98 spans for the first verified tournament.
- Those spans include one creation, one generation, three matches, thirty rounds, and sixty-three decisions.
- A subsequent remote query confirmed the completed challenge span.
- The authenticated budget status reported three generation reservations, totaling USD 0.15 against USD 4.
- Cloudflare DNS-over-HTTPS returned public addresses for pylemma.aor.fyi. HTTPS returned status 200.
- `uv build --offline --no-build-isolation`: wheel and source archive built.
- `node --check src/pylemma/web/static/app.js`: passed.
- `git diff --check`: passed.
- A content snapshot confirmed that locked offline setup and lint checks leave project files unchanged.

Deployment version: `19edcfe7-46f3-46b3-854c-5e05c10c2514`.
Image digest: `sha256:1351e5cabfbda5c56131083328e719ff701e9bbb0b7e484b21ff2aa5a29321fc`.
Verified tournament replay: `c6b2d7d0-02e6-41a8-acc7-ac5d1555144c`.
Verified trace: `01a181edfe79e187ccb551a56fe80d7f`.
Verified challenge replay: `dd468b88-e118-4945-869a-379247151878`.

## Failures and verified corrections

The default Docker build network could not resolve the package registry. Host networking completed the build.
The local DNS resolver retained a negative domain response. Public DNS returned the configured records.
Curl address overrides and Chromium resolver rules verified the actual domain and certificate.
The browser's function-based wait conflicted with the page security policy. Text-based waits worked.
The screenshot command interpreted an explicit output path as a selector. Its JSON mode returned a valid temporary image.
The first challenge reached a Python process during graceful shutdown and returned a proxy error.
Idle destruction and a JSON startup response corrected this path. Two later challenge requests completed successfully.
The application now flushes completed traces before responding, with a bounded wait and independent exporter failure handling.
A new regression test verifies that exporter flush failure preserves the completed result.
An initial Logfire query referenced an unavailable column. The corrected schema-based query returned the expected spans.

## Known limits

Infrastructure billing remains metered by Cloudflare. No new subscription was created.
The generation allowance covers this application, not unrelated account use or later price changes.
The reservation total is not a claim about actual billing. Failed or uncertain requests retain their reservation.
Public trace publication remains unverified and uses the existing review procedure.
The local DNS resolver can lag behind public authoritative records.
No independently verified ASD-STE100 compliance is claimed.

## Next implementation step

Observe visitor use within the fixed allowance. Obtain a new allowance before increasing quotas.
