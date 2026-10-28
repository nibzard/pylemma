# Architecture and terms

## Current implementation

The `pylemma` package contains the Game context, Match Record context, Player boundary, and application runner.
Pydantic validates domain contracts. Game code has no external operations.
The packaging tests check the installed distribution.
`pyproject.toml` defines checks and dependencies; `uv.lock` fixes their resolved versions.
Hatchling builds distributions. Pytest runs tests, and pytest-socket blocks test network access.
Ruff checks formatting and code quality. Mypy checks types.

## Context boundaries

A bounded context owns a consistent set of terms and rules.
The planned application is a modular monolith: its modules run in one process.
The following boundaries implement the contract in `SPEC.md` section 7.
The Game context, match storage, fake player, model adapter, and runner are implemented.

| Context | Owns | Boundary |
| --- | --- | --- |
| Game | Choices, outcomes, scoring, round order, match state, policies, summaries, and invariants. | Pure scoring and policy functions. No FastAPI, provider libraries, SQLite, or Logfire imports. Pydantic contracts are permitted. |
| Player | Observations, prompt separation, model decisions, validation, attempts, and bounded retries. | Exposes `async decide(observation, strategy) -> DecisionResult`. Failures use explicit error types; they never produce invented decisions. |
| Match Record | Stored settings, committed rounds, replay data, trace references, reviewed links, events, and retention. | Storage adapters preserve records. They do not choose scores or opponent actions. |

The match is the aggregate root.
An aggregate contains data that must remain consistent during one change.
The match controls round order, score totals, and final status.
`DecisionResult` contains a validated decision and execution metadata.

The application runner coordinates the three contexts.
It fixes observations before decisions, resolves rounds, and commits outcomes.
The runner establishes explicit tracing scopes. Later tasks add hosted resource limits.
The Hypertext Transfer Protocol (HTTP) layer validates transport input and calls application operations.
It contains no game rules.
The browser displays stored read models and does not calculate authoritative scores.
A read model contains data prepared for display.

Create modules when behavior requires them.
Use one module before adding empty layers.
Add interfaces only at external boundaries or where tests need substitution.

## Game contracts

- `game/rules.py` owns the immutable `pd-v1` score matrix and pure scoring function.
- `game/models.py` owns decisions, settings, outcomes, completed history, and match state transitions.
- `game/opponents.py` owns public policy descriptions and fixed explanations for each policy branch.

The models reject unknown fields and prevent field assignment.
Nested contracts are frozen, and histories and outcomes use tuples.
Settings store provider parameters as an immutable JavaScript Object Notation (JSON) object string.
`model_parameters()` returns a fresh dictionary for an adapter to use.
The provider adapter must validate supported parameters and record the values actually sent.
A universally unique identifier (UUID) identifies each match.
Identifiers and creation times use UUID and timezone-aware datetime types in Python constructors.
JSON deserialization uses `model_validate_json` to validate string representations of these types.
Creation times are normalized to Coordinated Universal Time (UTC).
The strategy hash is the SHA-256 digest of the trimmed strategy encoded as UTF-8.
SHA-256 is the 256-bit Secure Hash Algorithm. UTF-8 is Unicode Transformation Format with 8-bit units.

`Match.start`, `resolve`, `fail`, and `interrupt` return new validated match values.
`resolve` accepts only the next round number and completes the match at round ten.
Terminal matches reject all transitions. A new attempt needs a new match identifier.
Scores and cooperation counts are derived properties, not independently supplied fields.
The winner is absent until the match is complete.
`Match.history` excludes settings and stated reasons.
The opponent receives only this completed history; its next round number follows from the history length.

Use validated constructors or `model_validate_json` at boundaries.
Pydantic's `model_construct` and `model_copy(update=...)` do not validate their inputs.
Nested contracts undergo validation again when passed to a validated constructor.
Storage persists derived score changes and totals with each committed round record.
The application runner fixes both observations before decisions and exposes only committed outcomes.

The technical verbs `validate`, `deserialize`, `trim`, and `return` describe software operations here.
Validation checks a value against a contract. Deserialization converts stored text into typed values.
Trimming removes surrounding whitespace. Returning supplies a function result to its caller.

## Match Record contracts

`records/models.py` defines observations, attempts, committed rounds, and replay values.
The observation contains the permitted history, score matrix, current totals, and exact public opponent policy.
`Observation.from_match` builds that value from completed outcomes and immutable settings.
`opponent_history()` returns completed choices without strategy text or stated reasons.
The runner must create observations before computing either current decision.

`records/sqlite.py` owns migrations and the `MatchStore` boundary.
`create`, `transition`, `record_attempt`, `commit_round`, and `read` each own one short transaction.
Call `migrate` explicitly during setup, before using the store.
Match settings have no update operation.
A parent identifier must reference an existing match.
The caller supplies a new identifier when it creates a rematch.

A round commit checks the supplied observation against the stored history.
It uses Game transitions to verify score changes, cumulative totals, and round order.
It checks attempt counts and aggregates known usage and estimated cost.
One unknown attempt value makes that aggregate unknown.
The database enforces unique round numbers and unique attempt numbers within each match round.

Replay reads use one database snapshot and reconstruct the Game aggregate from stored outcomes.
The returned `Replay.match` provides totals, cooperation counts, and the winner as derived properties.
`Replay.rounds` provides stored observations, decisions, points, cumulative totals, timestamps, and trace references.
`Replay.attempts` includes unsuccessful requests, including requests for an unresolved round.
Replay reads verify stored progress and reject inconsistent records.
Trace references are optional metadata; replay reads never access Logfire.

The [storage decision](decisions/001-sqlite-match-records.md) owns concurrency and migration choices.
Admission, event storage, and startup coordination remain in their assigned tasks.
The adapter does not implement request scheduling or automatic recovery.

A transaction groups database operations that must commit or roll back together.
A migration changes the database schema in a defined order.
To commit means to save a transaction's changes permanently.
To roll back means to discard that transaction's changes.

## Player and runner contracts

`player/service.py` defines `Player.decide(observation, strategy)` and the validated `DecisionResult`.
`Player.validate_settings(settings)` checks compatibility before the runner changes stored state.
Each adapter owns this check and raises `ValueError` for incompatible settings.
The strategy is a separate argument. The opponent never receives it.
`FakePlayer` selects a fixed decision by round number and fails when its script ends.
`PlayerError` carries a safe error category. Invalid results fail validation at the runner boundary.
Fake attempts record empty execution parameters and unknown usage and cost.
Real requests include metadata for retries and failed request usage.
The model adapter accepts positive token counts and treats zero counts as unavailable for nonempty requests and decisions.
Each usable counter remains available independently; an unavailable counter keeps the estimated cost unknown.

`application/runner.py` starts an existing pending match and coordinates ten rounds.
It fixes the player observation and opponent history before calling either participant.
The existing `records.models.Observation` remains the shared contract to preserve storage compatibility.
History excludes both stated reasons and all current decisions.
The runner records attempts separately, then resolves and commits each outcome.
It returns only stored replay data. Progress readers use the same storage boundary.
No storage transaction remains open during player execution.

Explicit player failures preserve attempts and completed rounds, then store a failed status.
SQLite failures store `storage_error` when storage remains available.
A persistent storage failure propagates without exposing the uncommitted outcome.
Unexpected application errors and process cancellation require the later interruption handling in T014.
The runner provides no automatic resume, scheduling, or retries.

## Term list

This list applies the domain vocabulary from `SPEC.md` section 4 to implementation.
Product behavior remains authoritative in `SPEC.md`.

| Term | Meaning |
| --- | --- |
| Visitor | A person who opens the application. |
| Player | The participant controlled by the visitor's strategy prompt. |
| Opponent | The participant controlled by a preset policy. |
| Strategy | The visitor's instructions for the player. |
| Match | One attempt to complete ten rounds with fixed settings. |
| Round | One pair of choices and its resulting score changes. |
| Choice | Either `cooperate` or `betray`. |
| Observation | The permitted information supplied before a choice. |
| Decision | A validated choice and its stated reason. |
| Stated reason | The explanation returned with a decision. |
| Outcome | Both revealed choices and their score changes. |
| History | Completed outcomes from earlier rounds in the same match. |
| Replay | A display of stored outcomes that makes no model calls. |
| Rematch | A new match created from an earlier match's settings. |
| Trace | The Logfire record for one match execution. |
| Span | A timed operation within a trace. |
| Public trace link | A Logfire address that permits access without project membership. |
| Featured match | A reviewed match with a public Logfire link. |

Use **Betray** in the interface and `betray` in stored contracts.
Game theory often calls this choice **defect**.
Use **Betray** consistently in application text.
A stated reason is model output, not hidden reasoning or proof of a choice's cause.

## Model adapter

`player/model.py` owns the fixed provider configuration, separate prompts, and two-request allowance.
It validates the stored provider, model identifier, parameters, and system prompt version against its fixed configuration.
Parameter comparison ignores JSON formatting and key order, but preserves value types.
It uses Pydantic AI direct model requests with native structured output and no tools.
`AttemptMetadata` contains request details before the runner assigns storage identifiers.
`DecisionResult` and `PlayerError` carry every completed attempt.
The runner stores these attempts before committing an outcome or a failed state.
Unknown usage in any attempt keeps the corresponding round total unknown.
The fake player retains its existing unknown-usage behavior.

`evaluate.py` provides explicit live evaluation with a conservative spending ceiling.
It resolves matches through the Game context and writes a report to standard output.
It does not create external resources or publish results.
See the [model decision](decisions/002-model-and-retry-limits.md) for supported settings and retry rules.
Tracing remains in T006. Persistent hosted admission remains in T013.

## Telemetry and reviewed links

`telemetry.py` owns explicit Logfire scopes and a task-local client reference.
The runner starts an independent root without inherited request parents or baggage.
The model adapter creates one child span around each actual request and validation attempt.
No automatic provider or HTTP instrumentation is enabled.
Only explicit permitted inputs, validated decisions, safe error categories, and execution metadata enter application attributes.
The wrapper never passes raw exceptions to the SDK.
Scores enter round attributes only after storage commits.
SDK durations supply match, round, and request timing.
A failed export does not change the Game aggregate or stored results.
Trace identifiers indicate local span creation, not delivery or public availability.

`MatchStore.set_public_trace_url` changes only the reviewed reference.
`records/links.py` owns exact host and URL validation.
`cli.py` requires an explicit review acknowledgement when recording a link.
The operator verifies remote content and revocation through the supported Logfire interface.
Replay reads never follow the stored reference.
See the [runbook](runbooks/trace-review.md) and [access decision](decisions/003-public-trace-access.md).

## Generated machine application

The machine release contract in `SPEC.md` supersedes the original hosted experience.
The historical model adapter and match storage remain available.

`machines.py` owns immutable machine contracts, fresh Monty sessions, tournaments, and two-machine execution.
The host owns observations and scoring. Sandboxed code returns only validated decisions.
`generator.py` owns the single bounded provider request for a blueprint.
`machine_store.py` owns short SQLite transactions for machine versions, completed replays, and generation reservations.
`web/app.py` owns transport validation, admission, hosted startup, and lifecycle cleanup.
The browser displays server results and creates challenge invitations.

A machine is a named immutable strategy version with generated Python and its source hash.
A blueprint is the generated source and its short description.
A tournament runs the fixed trust-v1 opponent set and adds the machine's points.
A challenge runs two stored machines against each other.
The machine observation uses `self` and `opponent` for completed choices.
It excludes the opponent's current decision, source, and strategy.

## Cloudflare deployment boundary

`deploy/cloudflare/worker.js` routes public requests and serves static assets.
Its single `Pylemma` Durable Object owns immutable records and atomic spending reservations through `storage.mjs`.
Stored reads do not start the container. The Worker validates paid requests before forwarding them.
`remote_store.py` authenticates private storage operations from Python.
Local installations retain `MachineStore`; Cloudflare selects the remote adapter through environment configuration.
The container owns model generation and Monty execution, with one instance and one application worker.
The application flushes traces after completed requests without changing game results on exporter failure.
Idle destruction avoids keeping a stopped Python server inside a running container.
See [the deployment decision](decisions/005-cloudflare-container-storage.md) and [operations](runbooks/cloudflare.md).

## First-visit interface

The interface calls each machine a player. Stored `Machine` contracts and API identifiers retain their existing names.
Creation validates and stores code before execution. The optional preview delays execution until confirmation.
It shares the execution quota with challenges and makes no provider request.
`web/static/story.mjs` derives factual explanations from completed choices and contains version-specific reference scores.
It never changes authoritative scores or requests another explanation from a model.
The browser demonstration uses three fixed single-round examples and makes no external request.
Shared pages render their result or invitation first. Revision links retain an earlier replay for comparison.

## Public discovery

`Machine.public_listing` records immutable discovery consent. Its default is false for existing records and older clients.
`public_games.py` defines the public summary and ranking contract for local storage.
The Cloudflare equivalent lives in `deploy/cloudflare/public-games.mjs`.
The Durable Object saves summaries in `public:` keys within the replay transaction.
Public leaderboard and game-history reads access those compact entries without starting the container.
Tournaments share one score comparison. Challenges appear only in chronological history.
A preview has no public game entry. Both challenge participants must permit discovery before their game is listed.

## Trace inspection links

`trace_links.py` decorates local replay reads with a validated URL and explicit access mode.
`deploy/cloudflare/trace-links.mjs` applies the equivalent contract to hosted replay reads.
The Worker uses a configured project URL and a reviewed public reference map keyed by exact trace identifier.
These are navigation settings, not credentials. They do not change stored game outcomes or public listing consent.
The browser reloads a saved replay after completion so new games receive the same inspection metadata as shared replays.
Public sharing links take precedence over ordinary project trace filters.
Only the verified public-trace path accepts the narrow `spanId` highlight parameter.

## Arena entry and inspection

An arena is one completed set of ten matches for an immutable machine.
`machines.arena` executes a selected opponent list and fills empty slots with labelled presets.
The host selects recent distinct public machines with completed games. Preview-only machines are not eligible.
`MachineStore` uses a unique machine-to-replay table. The Durable Object uses an equivalent transactional key.
Saved entries return before execution allowance checks. Reads and retries make no provider request.
Public arena summaries use completion order without ranks. Historical fixed-suite ranks remain separate.

Each match trace includes source code and hashes. Each round stores its span reference.
The browser selects a factual event and highlights its recorded span only on the verified public-trace URL format.
Account-required and unavailable states remain explicit.
Share controls open a composer or copy an invitation. They never publish a post automatically.

A result without public trace access also offers the existing reviewed example, explicitly labelled as a separate tournament.
Its click event is separate from inspection of the visitor's own game.

## Pending requests and safe failures

`web/static/progress.mjs` maps actual requests to stages and provides recovery messages.
The browser renders an indeterminate indicator and elapsed time while submission is pending.
Generation and validation remain one stage. No streaming protocol or estimated completion percentage is used.
`generator.py` enforces a 45-second total deadline around the single provider request.
`telemetry.py` records permitted failure classes and replaces other class names with `UnexpectedError`.
It does not record raw exceptions or their messages.

## Request diagnostics

The browser creates a UUID request reference and sends it through `X-Request-ID`.
`POST /api/diagnostics` accepts a small, validated failure report without a replay requirement.
The Worker records reports without starting the container. Local FastAPI records equivalent `browser.failure` spans.
Reports are explicitly untrusted. Failed delivery does not retry the operation.

Worker request logs include normalized routes and deployment versions from `VERSION_METADATA`.
The Worker supplies that version to the container through `PYLEMMA_RELEASE`.
Application middleware sets a context-local request reference. Separate game traces retain this reference without inheriting request baggage.
The remote store forwards the reference to internal storage calls.
`telemetry.py` attaches the reference and deployment version to explicit spans.
Sandbox and generation stages identify which boundary failed. Limits and permitted error subtypes provide further evidence.

Container lifecycle records distinguish startup, stop, and idle shutdown.
The Worker defers idle shutdown while a request waits for startup or execution.
The existing busy flag protects this interval before the SDK starts counting active requests.

The generator consumes provider streaming internally to measure first content and complete response timing.
A context-local timing record connects HTTPX hooks to the existing generation span while retaining the HTTP connection pool.
Only approved event names become numeric timing marks. Transport payloads are ignored.
The browser receives one completed blueprint after normal stream completion and schema validation.
