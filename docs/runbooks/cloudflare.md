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

## Confirmed tournament execution

The browser creates a preview with `POST /api/machines` and `preview: true`.
Confirmation calls `POST /api/tournaments` with the stored `machine_id`.
This operation shares the challenge execution allowance and makes no model request.
Existing creation requests without preview retain their previous behavior.
Verify old replay links after an interface deployment. They should show the result before the creation form.
