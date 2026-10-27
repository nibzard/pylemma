# Reviewed public trace access

## Status and date

Accepted for local preparation on 2026-10-27.
Account settings, live trace contents, and signed-out access remain unverified.
T007 through T009 own those development round 2 checks.

## Problem

Visitors need access to real execution traces without project membership.
A public link exposes the complete trace, including nested spans and attributes.

## Constraints

Follow `SPEC.md` sections 6.2, 11, and 15.3.
Replay storage must remain independent of telemetry retention.
No supported automatic sharing endpoint has been verified for this project.
A trace identifier proves neither export delivery nor public access.

## Options considered

- Review selected matches and create their links through the supported interface.
- Make an entire project public after a separate access experiment.
- Automate sharing through an endpoint, if a supported contract becomes available.

## Decision and reason

Use reviewed featured matches and operator-created links for the first release.
This limits publication to complete traces reviewed against the public-record notice.
The CLI records or removes references. It never publishes data or revokes remote access.
The [runbook](../runbooks/trace-review.md) defines review, replacement, and removal.

## Documented capabilities and plan limits

The [public trace documentation](https://pydantic.dev/docs/logfire/observe/public-traces/) describes link creation with expiration settings.
It describes listing and deleting links under project settings.
An inner-span selection does not restrict access to that span.
These are documented capabilities, not evidence from our account.

The [pricing page](https://pydantic.dev/pricing) lists these limits on the review date:

| Plan | Published telemetry allowance | Published retention |
| --- | --- | --- |
| Personal | 10 million records monthly; USD 0 hard cap | 30 days |
| Team | 10 million included; USD 2 per additional million | 30 days |
| Growth | 10 million included; USD 2 per additional million | Up to 90 days |

Personal lists three projects. Team lists five projects. Growth lists unlimited projects.
Team starts at USD 49 monthly; Growth starts at USD 249 monthly.
These figures require confirmation before selecting a plan or authorizing exports.
They do not establish public-sharing entitlement or our project's actual retention.

## Unverified questions and required evidence

T007 must identify the project, region, plan, credentials, and authorized spending allowance.
T008 must record actual ingestion, trace identifiers, usage, costs, retention settings, and every exported attribute.
T009 must verify sharing permission, expiration options, complete signed-out access, revocation, and a replacement link.
Record the selected plan's applicable sharing limits and telemetry budget during those checks.
No live provider request, remote telemetry export, or public link was created for T006.

Anonymous project access remains an optional post-release experiment in T024.
A public-project schema option alone does not prove anonymous access or an automatic sharing endpoint.

## Consequences

Matches without reviewed links have no public trace reference.
Exports can fail without changing stored scores or completed rounds.
Operators must review SDK resource metadata as well as application attributes.
Expired links need removal or replacement. Replays remain readable after either operation.
The explicit host allowlist can reject new regional hosts until reviewed and added.
Links with parameters are rejected; verify a complete-trace link without parameters through the supported interface.
Do not rewrite an unfamiliar link or guess its path.

## Conditions for reconsideration

Reconsider this decision after verified account capabilities or a supported sharing contract changes.
Keep optional project-wide access separate from the reviewed-link release gate.
