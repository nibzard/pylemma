# Review and maintain public trace links

## Prerequisites

T007 supplies provider access, a Logfire project, and an explicit spending allowance.
Use synthetic strategy text for review matches.
Do not enter credentials or personal data in strategy text.
Use a dedicated process without automatic HTTP, provider, or framework instrumentation.

`pylemma.telemetry.configure()` uses normal Logfire authentication and returns a local SDK instance.
Pass that instance as `telemetry=` to `run_match` after configuring the operator's project.
Importing the module does not configure Logfire or export data.
The existing evaluation command does not export match traces.
The developer example remains in T019.

The configuration masks host identifiers and source paths.
It rejects custom resource metadata from environment settings.
Do not add custom detectors, resource metadata, or automatic instrumentation to reviewed match execution.
Logfire scrubbing remains enabled, but it cannot replace a full review.
A saved identifier does not confirm delivery. Confirm the actual trace in Logfire.

## Offline trace checks

Run these checks before a live review:

```sh
uv run --offline --locked pytest tests/integration/test_telemetry.py
```

The tests inspect actual SDK spans through an in-memory exporter.
They use mock provider responses, private temporary databases, and disabled internet sockets.
They verify hierarchy, references, retries, permitted inputs, structured outputs, usage, and safe failures.
They also exercise reviewed-link validation and replay reads after reference removal.
Offline success does not satisfy the live acceptance gate in `SPEC.md` section 15.3.

## Full-trace review

1. Run one authorized match within the allowance and record its match identifier.
2. Find its root trace through the stored trace identifier.
3. Compare all ten round references and request references with stored records.
4. Inspect every span, event, attribute, resource attribute, and link in the complete trace.
5. Compare model inputs, decisions, policy branches, scores, retries, durations, usage, and cost estimates with the stored match.
6. Reject publication if credentials, network identifiers, access metadata, unrelated headers, private text, or raw errors appear.
7. Record the reviewer, date, notice version, match identifier, trace identifier, findings, and applicable account settings.

Include retry spans and failed requests in the review.
Only validated structured decisions are exported; invalid response bodies are omitted.
Safe error categories identify validation and provider failures.
Unknown usage and costs remain unknown. They must not be interpreted as zero.
SDK resource attributes include runtime information, service version, and process metadata.
Review those attributes too. No automatic field filter establishes publication approval.
Keep local review output in ignored `.trace-reviews/` and exclude private data from development records.

## Authorized publication and access verification

This procedure belongs to T009 and requires operator publication authorization.
The [official instructions](https://pydantic.dev/docs/logfire/observe/public-traces/) describe the supported interface.

1. Open the reviewed complete trace and select **Private** in the details panel.
2. Choose the approved expiration and create the public link.
3. Open the link in a signed-out browser and verify the complete intended trace.
4. Delete the link under **Project Settings**, **Shared Traces**.
5. Reload the signed-out link and verify that public access is removed.
6. Create a fresh link and repeat the signed-out content check.
7. Record the fresh link with the CLI after completing the review record.

Interface labels can change. Record actual labels and results during T009.
Do not infer an endpoint from browser traffic.
If sharing permission or controls are missing, record the exact prerequisite and stop publication.

## Record a reviewed reference

Use the actual match identifier and verified complete-trace URL:

```sh
uv run --offline --locked python3 -m pylemma.cli --database "$DATABASE" \
  record-link "$MATCH_ID" "$PUBLIC_TRACE_URL" --reviewed
```

`--reviewed` confirms the full-trace and signed-out review.
The command requires a completed match with a trace identifier.
Allowed hosts are exactly `logfire.pydantic.dev` and `logfire-us.pydantic.dev`.
Only HTTPS links without credentials, ports, parameters, fragments, escapes, or whitespace are accepted.
The command does not fetch the URL or prove that it identifies the stored trace.
The operator must compare the identifiers and complete contents before recording the link.
There is no visitor administration endpoint.

## Check, replace, or remove links

Check featured links before each demonstration and before their recorded expiration.
Compare remaining telemetry retention with the planned demonstration date.
If a link fails, remove its stored reference promptly:

```sh
uv run --offline --locked python3 -m pylemma.cli --database "$DATABASE" \
  remove-link "$MATCH_ID"
```

Removal is repeatable and preserves all replay data.
It does not revoke remote access. Revoke access through the supported Logfire interface separately.
To replace a link, repeat the review and use `record-link` with the verified replacement.
If telemetry has expired, create another authorized example and review its complete trace.
Do not assign another match's trace to the original match.
