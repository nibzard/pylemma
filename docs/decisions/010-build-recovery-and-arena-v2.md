# Recover builds and version the arena

## Status

Accepted.

## Context

A browser lost a build response although its player was saved.
Recent opponent selection makes arena scores difficult to compare.
An offline experiment found that twenty rounds can reveal recovery missed at ten rounds.

## Decision

Persist build status by request identifier in the existing Durable Object.
Bind each identifier to a hash of the input.
Return saved work for repeated identifiers, and reject changed input.
Keep uncertain attempts visible without generating again.
Commit the machine and its recovery reference in one storage transaction.
Expose only stage, safe failure text, and completed public machine data through the status endpoint.
The browser retains the reference and draft in session storage until completion.

New players declare arena-v2.
They face the same ten deterministic presets for twenty rounds each.
Missing versions retain arena-v1 and its historical behavior.
Direct challenges and historical tournaments retain ten rounds.
Render all replays from their stored rounds and suite version.

## Consequences

Disconnected clients can find saved work without another provider request.
A stuck attempt requires a new explicit attempt, not an automatic retry.
Progress polling adds inexpensive stored reads.
Twenty-round replays create more trace data.
Old and new scores must be labeled and compared only within matching versions.
