# Deploy and operate the Cloudflare application

The public application runs at https://pylemma.aor.fyi.
The Worker serves assets and stored reads. One small container runs Python and Monty.
A SQLite-backed Durable Object preserves records and reservations when the container stops.
The container disk contains no authoritative machine records.

## Spending controls

The deployment permits twenty generations per day and eighty generations for its lifetime.
Each generation reserves USD 0.05 against a USD 4 allowance before the provider request.
Failed requests retain their reservations. Restarting or deploying does not reset these counters.
Challenges permit four hundred daily runs and sixteen hundred lifetime runs.

The generator uses the existing model with standard processing and no reasoning allocation.
It makes one request, disables retries, and limits output to 2,400 tokens.
The strategy contains at most 1,000 characters. The fixed prompt and output schema bound the remaining input.
At the verified rates, the reservation exceeds the maximum ordinary request cost by a substantial margin.
Recheck rates before changing model configuration or increasing the allowance.

Cloudflare billing remains metered. The existing paid plan includes container usage allowances.
No new subscription was created. Unrelated account use can consume shared allowances.
The container uses 256 MiB and sleeps after thirty idle seconds.
Static pages and stored reads do not start it.
The USD 1 remainder is a verification and infrastructure buffer, not a provider-enforced account ceiling.

## Deploy a code change

1. Run the checks in `README.md` and `npm test --prefix deploy/cloudflare`.
2. Run `npm ci --prefix deploy/cloudflare` to install the locked deployment tools.
3. Build with `docker build --network host -t pylemma:deploy .`.
4. Push with `deploy/cloudflare/node_modules/.bin/wrangler containers push pylemma:deploy --config deploy/cloudflare/wrangler.jsonc`.
5. Set the returned image digest in `deploy/cloudflare/wrangler.jsonc`.
6. Deploy with `deploy/cloudflare/node_modules/.bin/wrangler deploy --config deploy/cloudflare/wrangler.jsonc`.
7. Verify the home page, a stored replay, and an authorized challenge after an idle restart.

The Docker build context excludes local credentials, databases, and development records.
Default Docker networking failed on the development host. Host networking completed the build.
The image runs as an unprivileged user and starts one Uvicorn worker.

## Runtime secrets

The Worker requires `OPENAI_API_KEY`, `LOGFIRE_TOKEN`, and `STORE_TOKEN`.
Use Wrangler secret commands to set these values. Never put them in configuration files or build arguments.
`STORE_TOKEN` authenticates private container storage calls. Generate an independent random value.
The configured Logfire endpoint belongs to the EU project used by this repository.
Restart the container after changing secrets so its process receives the updated values.

## Inspect health and traces

`GET /health` checks Worker availability. It does not start or validate the container.
`GET /api/replays/{identifier}` reads durable storage without a provider request.
A successful challenge validates the container, sandbox, and record boundary.
Search Logfire by the replay's stored `trace_id` to inspect execution.
Public trace sharing still requires the existing full review procedure.

The authenticated `/_store` operation `status` returns lifetime counts and reserved microdollars.
It does not return credentials. Send the internal secret only through an authorization header.
Read-only Logfire queries can verify delivery without creating public trace links.

## Stop new generation

Delete the Worker's OpenAI secret and stop the active container to disable new provider requests.
Stored replays and static pages remain available through the Worker.
To pause all game execution, remove the container binding route or deploy a maintenance response.
Do not delete the Durable Object or change its `public-v1` name to reset spending limits.
A budget increase requires a new explicit allowance and a reviewed configuration change.

## Historical tournament execution

Clients can create a preview with `POST /api/machines` and `preview: true`.
The historical `POST /api/tournaments` endpoint accepts the stored `machine_id`.
This operation shares the challenge execution allowance and makes no model request.
Existing creation requests without preview retain their previous behavior.
Verify old replay links after an interface deployment. They should show the result before the creation form.

## Public game discovery

The Worker serves `GET /api/leaderboard` and `GET /api/games` from durable summaries.
These reads do not start the container. Each response contains at most fifty entries.
A completed replay and its eligible public summary commit in one transaction.
The immutable `public_listing` field controls discovery. Missing fields mean false.
Do not backfill old unlisted records into the public index.
Public summaries contain names, scores, and replay links. Full strategies and generated code remain available through the replay.
Verify an unlisted replay remains readable but absent from both public endpoints after deployments.

## Inspect in Logfire links

`LOGFIRE_PROJECT_URL` configures ordinary account-required trace navigation.
`LOGFIRE_PUBLIC_TRACES` contains a JSON object mapping trace identifiers to reviewed public URLs.
Both settings live in Worker variables. Never place a runtime token or browser handoff in either setting.
The public reference map does not publish a trace by itself.

To attach a public sharing link:

1. Create the trace-specific public link through Logfire's signed-in sharing controls.
2. Open it in a fresh browser session and verify the intended replay identifier and complete trace.
3. Complete the content review in [the trace review procedure](trace-review.md).
4. Add the exact trace identifier and public URL to `LOGFIRE_PUBLIC_TRACES` in the Wrangler configuration.
5. Deploy the Worker and verify the replay's `logfire_access` is `public`.
6. Click Inspect in Logfire while signed out and confirm the intended trace opens.

The reviewed URL can include one `spanId` parameter on the verified public-trace path.
This highlights a span while still sharing the complete trace.
Other games retain account-required links until their own public links are created and attached.
No automatic per-game public-link API has been verified.

A public project is public within its organization. Ordinary inspection links still require project access.
A public trace link grants access to that trace without an invitation or sign-in.

## Arena operations and funnel checks

The browser calls `POST /api/arena` after storing its generated player.
The optional preview delays this call until confirmation. Arena execution shares the challenge allowance.
A saved entry returns before quota checks, without starting the container.
`GET /api/arena` serves chronological public arena summaries from durable storage.
The `arena:` keys prevent duplicate entries. Preserve these keys during maintenance.
Internal storage requests permit 420,000 bytes. Stored records permit 400,000 JSON characters.
These limits accommodate ten matches while retaining a bounded request body.

The application records `machine.arena` and `machine.challenge` spans with `completed` and `referred` attributes.
The browser sends `inspection_click`, `example_inspection_click`, and `share_click` events with an existing replay identifier.
The Worker records these events in its logs without starting a container.
Local FastAPI operation records equivalent `game.funnel` spans in Logfire.
Count completed entries separately from clicks. Clicks do not prove publication or successful public access.
These unauthenticated counts can contain repeated or automated events. They do not identify unique people.

Before promoting the public inspection funnel, review a new arena trace and verify signed-out access.
Include all ten matches, source attributes, and round spans in the review.
Do not reuse another game's public trace URL or describe account-required access as public.

When a result lacks public access, the browser also links to the existing reviewed public tournament.
This example is labelled separately. Its inspection clicks have a separate event name.
Recheck its link before promotion. Remove or replace it if public access expires.

A new Worker can become available before the previous container stops.
During the arena deployment, the first arena request returned 404 from the container.
The same request succeeded after the instance became inactive and restarted.
Check the new execution endpoint after the idle restart before declaring deployment verified.

## Diagnose a visitor error

1. Obtain the request reference from the displayed error and its approximate time.
2. Find `game.request` and `browser.failure` records with that reference in Worker logs.
3. Compare the response status, outcome, duration, and deployment version.
4. Query Logfire for the same reference and inspect the failed stage.
5. Compare Worker and application deployment versions if a new endpoint returns 404 during rollout.
6. Reproduce with the stored rules offline before making another provider request.

Use `wrangler tail --config deploy/cloudflare/wrangler.jsonc --format json` for a current Worker stream.
A tail starts with current activity. It does not retrieve historical requests.
Worker diagnostics distinguish `busy`, `daily_quota`, `lifetime_quota`, `saved_entry`, `invalid_container_response`, and `container_connection`.
A browser failure report can exist without a server request record when the connection failed before admission.
Browser reports are untrusted observations. Their absence does not prove that a request succeeded.

Use this Logfire query with the visitor's UUID and an appropriate time range:

```sql
SELECT start_timestamp, span_name, trace_id,
       attributes->>'stage' AS stage,
       attributes->>'status' AS status,
       attributes->>'outcome' AS outcome,
       attributes->>'error_type' AS error_type,
       attributes->>'runtime_error_type' AS runtime_error_type,
       attributes->>'deployment_version' AS deployment_version
FROM records
WHERE service_name = 'pylemma'
  AND start_timestamp >= now() - interval '1 hour'
  AND attributes->>'request_id' = 'REQUEST_UUID'
ORDER BY start_timestamp
LIMIT 100
```

The request span uses `application.request`. Separate game traces share the request reference.
`machine.decision` records `checkout`, `execute`, or `validate_decision` when a failure occurs.
Inspect its `limits`, `request_timeout_seconds`, `worker_timed_out`, and `worker_exit_status` attributes when present.
`machine.generate` separates provider waiting from blueprint validation and records configured deadlines.
`storage.request` distinguishes a storage failure from a game failure.
A missing `error_type` on an older trace cannot establish the historical failure's cause.
Diagnostic records deliberately omit raw exception text, request bodies, and credentials.

Container lifecycle events include `container.started`, `container.stopped`, and `container.error`.
The stop event records the exit code and a restricted reason.
`container.idle_shutdown` identifies an idle stop; `container.idle_deferred` identifies active work that prevents shutdown.
A waiting request protects startup because the SDK counts active requests only after startup completes.
Compare lifecycle timestamps with request duration before attributing a startup failure to the application image.
[Stored Cloudflare log queries](https://developers.cloudflare.com/api/resources/workers/subresources/observability/subresources/telemetry/methods/query/) require `Workers Observability Write` permission.
Use Worker tail when stored-log access is unavailable. Never print authentication tokens.

Wrangler success can precede container rollout completion.
Check `wrangler containers info` for the expected image before testing a cold restart.
Do not start another deployment while the previous container rollout remains pending.

`container.wait` records the request reference and sixty-second port deadline.
A cold start can exceed the SDK default of twenty seconds at the hosted CPU limit.

Container error categories distinguish `startup_exit`, `port_deadline`, and `other` without recording the SDK error text.

The port deadline is an SDK polling budget. Connection attempts can extend the elapsed wait.
A verified cold-start challenge took about seventy-six seconds on the lite instance.
