# Persist container records in a Durable Object

Status: accepted. Date: 2026-10-28.

## Problem

Cloudflare container disks are temporary. Local SQLite cannot preserve public machine links after replacement.
Monty needs a Linux runtime with native binaries.

## Constraints

Deploy through the existing Cloudflare account. Use pylemma.aor.fyi.
The user authorizes a spending allowance of USD 5 or less.
Keep model and Logfire credentials in runtime secrets.

## Options considered

- Use Python Workers, which cannot run the installed native Monty runtime.
- Keep records on container disk, which loses records during replacement.
- Run Python in one container and persist records in a Durable Object.

## Decision

Use one small Linux container for Python and Monty.
Serve assets and stored reads directly from the Worker.
Use a SQLite-backed Durable Object for immutable records and atomic reservations.
Authenticate the container's storage requests with a separate runtime secret.
Destroy the idle container after thirty seconds. Flush completed request traces before responding.
Keep exporter failures separate from completed game results.

## Reason

This preserves the existing application behavior and supports temporary container disks.
Reads and static pages avoid starting the container.
Atomic lifetime reservations survive deployments and daily quota changes.

## Consequences

Storage calls now have network and authentication failure modes.
The application rejects generation after eighty lifetime reservations or twenty daily reservations.
Each reservation accounts for USD 0.05 against a USD 4 generation allowance.
The allowance retains failed and uncertain requests. It does not reset automatically.
Infrastructure billing remains metered and shares the account's existing plan allowances.
The application cannot cap unrelated account spending.

## Evidence links

- [Cloudflare container disk lifecycle](https://developers.cloudflare.com/containers/faq/)
- [Container pricing](https://developers.cloudflare.com/containers/platform/pricing/)
- [Model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [Deployment evidence](../development/2026-10-28-cloudflare.md)

## Conditions for reconsideration

Reconsider the quotas after measured visitor use and an explicit new spending allowance.
Reconsider the network boundary if storage latency becomes a measured problem.
