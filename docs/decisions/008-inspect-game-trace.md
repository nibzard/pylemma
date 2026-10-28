# Show trace inspection with explicit access

Status: accepted. Date: 2026-10-28.

## Problem

The trace action disappears when a completed game has no reviewed public link.
Visitors cannot discover the recorded execution, and account-required links differ from public sharing links.

## Constraints

Preserve explicit access labels and reviewed publication. Use verified Logfire link formats.
Do not expose runtime credentials or browser handoffs. Do not publish a project to obtain trace-specific access.
Keep stored game outcomes immutable and reads independent of model requests.

## Options considered

- Continue hiding the action without a public reference.
- Describe ordinary trace links as public, which incorrectly implies anonymous access.
- Always show inspection and distinguish public, account-required, and unavailable states.

## Decision

Show the action near the completed result summary. Prefer reviewed public references.
Generate ordinary trace links from configured project URLs and validated identifiers for other completed games.
Label account requirements explicitly. Disable the action when no valid link can be constructed.
Configure verified public references by trace identifier in the Cloudflare Worker.

## Reason

Every completed result can explain its trace access without claiming unsupported anonymous sharing.
The user supplies one public link. Signed-out access and replay identity are verified before attaching it.
The selected span parameter is preserved through a narrow validation exception.

## Consequences

An ordinary link remains useful to project members. Other visitors need a public sharing link for account-free access.
The documented sharing workflow currently creates one public link per trace.
No supported automatic public-link endpoint has been verified.
The supplied link is verified in a fresh browser context and against all 94 exported records.
The verification does not revoke or replace the user's existing public link.

## Evidence links

- [Development evidence](../development/2026-10-28-inspect-logfire.md)
- [Logfire public traces](https://pydantic.dev/docs/logfire/observe/public-traces/)
- [Original publication decision](003-public-trace-access.md)

## Conditions for reconsideration

Reconsider automatic publication when Logfire provides a verified supported contract for it.
Recheck public links after expiration, revocation, or telemetry retention changes.

## Verified project access semantics

The [official access documentation](https://pydantic.dev/docs/logfire/manage/organizations-and-projects/) defines public projects as public within the organization.
An outside account needs an invitation. A public trace link permits access without membership or sign-in.
