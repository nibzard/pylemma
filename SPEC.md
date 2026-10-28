# pylemma specification

Status: proposed implementation contract.  
Version: 0.2.0.
Date: 2026-10-28.
Product name: **pylemma**.  
Public subtitle: **Prisoner's Pylemma**.

This file defines the first release. It does not describe an existing implementation.

The [simple arena contract](#simple-arena-contract) defines the current browser entry and supersedes the fixed tournament default.

## Machine release contract

This contract supersedes conflicting behavior in sections 1, 2, 4 through 15, and 17 through 19.
Those sections describe the original model-per-round implementation and its stored records.
Documentation requirements in sections 3 and 16 remain active.

### Purpose and current phase

The current phase implements reusable machines, a fixed tournament, challenges, and the browser experience.
The public promise is: Describe your rules for trust. Build a machine. Challenge someone else's.
Logfire is required for hosted operation. Monty executes every machine decision.

### Machine creation

A visitor supplies a name and a strategy of at most 1,000 characters.
The visitor acknowledges that names, strategies, code, and results are available through unlisted links.
The generator makes one bounded request using the existing fixed provider and model.
A blueprint contains Python source and a brief description of the implemented rules.
Source defines `decide(observation)` and returns the existing validated Decision contract.
The application validates sample histories before running the tournament.
Sample checks cannot prove that generated code represents visitor intent.
A stored machine has a new identifier and source hash. Revisions create new machines.

### Execution and scoring

Each decision executes in a fresh Monty session without mounts or host callbacks.
Observations contain the round, ten scheduled rounds, and completed choices from the participant's perspective.
Both observations exist before either current choice is computed.
Host scoring uses the existing pd-v1 matrix. Generated code cannot change scores.
Memory, execution time, recursion, and host request deadlines bound execution.
Failures never produce a fabricated choice or completed replay.
The fixed trust-v1 tournament plays Optimist, Grudge Holder, and Opportunist for ten rounds each.
Its score adds the machine's points across all three matches. Show combined points and individual match records.
A challenge runs two immutable machines for ten rounds and stores the completed replay.
A challenge link invites its recipient to build a machine and challenge the linked version.
Global rankings, accounts, and automatic optimization remain outside this phase.

### Hosted boundaries

FastAPI serves the browser, creation, machine reads, challenges, and replay reads.
SQLite stores immutable machines, completed replays, and daily generation reservations.
Hosted startup requires a model credential, a Logfire token, and a positive daily generation quota.
One process serializes generation and game execution. Busy requests receive an explicit retry response.
Challenges have a separate daily quota of twenty times the generation quota.
Reserve generation allowance before making a provider request. Failed requests consume their reservation.
The provider client disables retries and bounds request duration and output tokens.
The quota limits request count; it does not claim to enforce a monetary billing ceiling.
The operator must select the quota within their authorized spending allowance before deployment.
No live verification runs without an explicit spending allowance.

### Observability and publication

Trace generation, validation, decisions, rounds, matches, and challenges through Logfire.
Include source hashes, permitted observations, validated decisions, and completed scores.
Trace identifiers do not prove successful delivery or public access.
Export failure does not change game results.
Public trace publication requires review under the existing trace review procedure.
The browser must not invent public trace addresses from trace identifiers.

### Acceptance

Offline tests cover scoring, simultaneous observations, fresh sessions, resource failures, validation, storage, and transport behavior.
Existing checks remain required. Public machine and replay reads must not make provider requests.
Live generation, export delivery, and reviewed public access need separate configured verification.

## 1. Purpose

pylemma is a small game about trust between players.
The visitor gives an AI player a strategy prompt.
The player faces a known opponent for ten rounds.
Each player chooses **Cooperate** or **Betray**.

The visitor watches the choices, reads the stated reasons, and checks the results.
Logfire shows the actual model requests and the game execution.
The visitor can then change the strategy and start another match.

The product has two objectives:

1. Make a short game that developers want to try again.
2. Give those developers a useful first experience with Logfire.

The demonstration supports a Head of Growth application to Pydantic.
Its value comes from developer participation and measured product use.
It must not depend on an association with Pydantic that does not exist.

### 1.1 Product promise

> Give your player a strategy. See when it cooperates. Inspect what happened.

The first screen must explain the game without technical documentation.
The technical explanation follows the game.

### 1.2 Product principles

- Use two choices and one fixed scoring system.
- Make the first match available without an account.
- Use real model responses during live play.
- Identify recorded examples as recorded examples.
- Make Logfire access visible near an interesting result.
- Keep facts separate from interpretations.
- Keep the game small enough for one maintainer.
- Document decisions and evidence during development.

## 2. Scope

### 2.1 First release

The first release contains:

- One strategy field.
- Three opponent choices.
- Three example strategy prompts.
- Ten rounds per match.
- One configured model provider and one pinned model identifier.
- One model-controlled player and one deterministic opponent.
- A round timeline with both choices and scores.
- A detail view for each completed round.
- A permanent identifier for each stored match.
- An unlisted replay URL for each match.
- Public Logfire links for reviewed example matches.
- A local example that sends traces to the developer's Logfire project.
- Basic use and cost measurements.

An unlisted URL does not appear in a public directory.
Anyone who has that URL can open it.
An unlisted URL is not private storage.

### 2.2 Excluded from the first release

- User accounts and profiles.
- Live human opponents.
- A second model-controlled player.
- Ranked matches or a global score table.
- Prizes, payments, or financial stakes.
- Multiple games or configurable scoring systems.
- Model selection by visitors.
- Generated code execution.
- Agent tools, web access, or external actions.
- Automatic strategy optimization.
- Automatic explanations written by another model.
- A custom trace explorer that replaces Logfire.
- Distributed workers, a message broker, or separate services.
- Automatic match recovery after a process restart.

Monty is not required for this game.
Add Monty only if a later feature requires bounded execution of generated Python.
Do not add a dependency only to display its logo.

## 3. Language and documentation rules

Use ASD-STE100 Simplified Technical English as the writing standard.
Use Issue 9 as the initial reference.
Use the official dictionary and rules during editorial review.

This specification uses short technical English.
It does not claim independently verified ASD-STE100 compliance.

Apply these rules to documentation, comments, interface text, errors, and development reports:

1. Use a maximum of 20 words in an instruction sentence.
2. Use a maximum of 25 words in a description sentence.
3. Give one instruction in each sentence.
4. Keep each sentence about one subject.
5. Use active voice.
6. Put a necessary condition before its instruction.
7. Use the same term for the same concept.
8. Define technical terms before use.
9. Use complete sentences where sentences are required.
10. Keep error messages specific.
11. State the next useful action after an error.
12. Preserve exact identifiers and external quotations.

Technical names can include Pydantic, Logfire, FastAPI, SQLite, HTTP, JSON, and Python.
Maintain a project term list when implementation starts.
A sentence-length check is an aid. It is not an ASD-STE100 compliance test.

### 3.1 Extensive documentation without duplication

Documentation is part of each implementation change.
Record the reason for a decision while that reason is known.
Record failed experiments when they affect later work.

Keep one authoritative location for each fact:

| Information | Authoritative location |
| --- | --- |
| Product behavior and scope | `SPEC.md` |
| Current installation and quick start | `README.md` |
| Agent development instructions | `AGENTS.md` |
| Domain terms and boundaries | `docs/architecture.md` |
| Consequential decisions | `docs/decisions/` |
| Interface contracts | Generated OpenAPI and domain model definitions |
| Development evidence | `docs/development/` |
| Operational procedures | `docs/runbooks/` |
| Released behavior changes | `CHANGELOG.md` |

Create these documents when their implementation phase starts.
Do not create empty documents for planned features.
Link to authoritative content instead of copying it.

## 4. Domain language

Domain-driven design organizes code around product responsibilities.
A bounded context owns one consistent set of terms and rules.
The first release uses three small contexts within one application.

| Term | Definition |
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
| Replay | A display of stored outcomes. It does not call a model. |
| Rematch | A new match created from an earlier match's settings. |
| Trace | The Logfire record for one match execution. |
| Span | A timed operation within a trace. |
| Public trace link | A Logfire URL that permits access without project membership. |
| Featured match | A reviewed match with a public Logfire link. |

Use **Betray** in the interface.
Use `betray` in stored contracts.
Explain once that game theory often calls this choice **defect**.
Do not alternate these terms in application text.

The stated reason is model output.
It is not hidden reasoning or proof of the cause of a choice.

## 5. Game rules

Rules version: `pd-v1`.

### 5.1 Score matrix

| Player choice | Opponent choice | Player points | Opponent points |
| --- | --- | ---: | ---: |
| Cooperate | Cooperate | 3 | 3 |
| Cooperate | Betray | 0 | 5 |
| Betray | Cooperate | 5 | 0 |
| Betray | Betray | 1 | 1 |

Each participant starts with zero points.
The match has exactly ten scheduled rounds.
The participant with more points after ten completed rounds wins.
Equal totals produce a draw.

Show both individual totals and the combined total.
The combined total helps visitors see the effect of mutual cooperation.
It does not change the winner rule.

### 5.2 Information available before a round

Both participants receive the same completed history.
Neither participant receives the other participant's current choice.

The player observation contains:

- Current round number.
- Total scheduled rounds.
- Score matrix and rules version.
- Current scores.
- Previous choices and score changes.
- Opponent name, policy version, and exact public policy description.

The player also receives the visitor's strategy.
The opponent does not receive the visitor's strategy.
Neither participant receives the other participant's stated reasons.

Create both observations before either current decision is revealed.
Sequential computation is permitted because both observations are fixed first.
The model request must not contain the opponent's computed current choice.

### 5.3 Opponent policies

Opponent policies are deterministic Python functions.
They do not call a model.
Their policy versions are stored with each match.

**The Optimist — `optimist-v1`**

- Cooperate in every round.

**The Grudge Holder — `grudge-v1`**

- Cooperate until the player betrays in a completed round.
- Betray in every later round after that first betrayal.

**The Opportunist — `opportunist-v1`**

- Betray if the player betrayed in the previous round.
- Otherwise, betray in rounds 3, 6, and 9.
- Otherwise, cooperate.

Apply the conditions in their listed order.
In round 1, there is no previous player choice.
Store a fixed explanation for each policy branch.

Show these policies in the opponent selector.
Do not imply that a deterministic opponent has independent model reasoning.

### 5.4 Interpretation limits

This is a finite game with a known final round.
Players can exploit known policies and the final round.
Such behavior is part of the demonstration.

A high score does not measure model intelligence, moral behavior, or real-world trustworthiness.
A single match does not prove that one prompt is better.
Different model responses can occur with identical inputs.

Do not describe a rematch as a controlled benchmark.
Store model settings so a later evaluation can compare repeated trials.

### 5.5 Invariants

The game must preserve these conditions:

- A resolved round has exactly two valid choices.
- A round resolves once.
- Round numbers start at 1 and have no gaps.
- A completed match has exactly ten resolved rounds.
- Scores equal the sum of stored round scores.
- Score changes come only from the score matrix.
- A participant cannot see the other participant's current choice before resolution.
- Match settings do not change after creation.
- A replay never changes a match.
- A rematch has a new identifier.
- A failed round has no outcome and adds no points.
- A partial match has no winner.
- Model text cannot change the score matrix or opponent policy.

## 6. Visitor experience

### 6.1 Initial screen

Show the product name and one sentence about the game.
Show a compact score matrix beside the strategy field.

Suggested introductory text:

> Give your player a strategy. Play ten rounds of cooperation and betrayal.

Use these controls:

- Strategy text area.
- Opponent selector.
- Example strategy buttons.
- Public-record acknowledgement.
- **Play ten rounds** button.

Example strategies:

- “Cooperate first. Copy the opponent's previous choice after that.”
- “Cooperate unless the opponent betrays twice. Then always betray.”
- “Get the most points for yourself. Use the opponent's known policy.”

The examples fill the field. They do not start a match.

### 6.2 Public-record notice

Hosted matches produce unlisted public replay pages.
Those pages include the strategy, choices, and stated reasons.

Before the first submission, show this notice:

> Your strategy and match results are available to anyone with the replay link. Do not enter private information.

Require an acknowledgement before starting a hosted match.
Store the notice version with the match.
This acknowledgement permits the stated game record.
It does not automatically authorize publishing all request metadata in Logfire.

Reviewed public traces must contain only data covered by the notice.
Do not publish a trace with additional private data.

### 6.3 During a match

Show round progress and current scores.
Display both choices together after the round commits.
Show the player's stated reason under the revealed choice.

Use text labels as well as colors.
Do not use animation to delay results artificially.
Show an explicit waiting state during a model request.

The visitor can leave the page without stopping the match.
Reopening the replay URL shows its latest stored state.
The first release has no pause, cancellation, or resume controls.

### 6.4 Completed match

Show:

- Winner or draw.
- Both scores and combined score.
- Cooperation count for each participant.
- A ten-round timeline.
- Deterministic observations about the match.
- **Change strategy and play again**.
- **Copy replay link**.
- **Inspect match in Logfire**, when a public link exists.
- **Run locally with Logfire**.

Examples of deterministic observations:

- “Your player cooperated in 7 of 10 rounds.”
- “The first betrayal occurred in round 3.”
- “Both players betrayed in the last 4 rounds.”

Each observation must follow directly from stored outcomes.
Do not add unsupported psychological explanations.

### 6.5 Round details

Selecting a round shows its permitted observation, both decisions, and score changes.
Label model explanations **Player's stated reason**.
Label opponent explanations **Opponent policy**.

For a featured match, provide its public trace link.
Highlight a round only if Logfire supports a verified link for that span.
Otherwise, open the complete trace and identify the round by name.
Do not invent a span-link format.

### 6.6 Errors and partial matches

Keep completed rounds visible after failure.
Show the failed round and a useful error category.
Do not expose raw provider responses or credentials in error text.

Suggested message:

> The model did not return a valid choice for round 4. The match stopped. You can start a new match.

The interface must not invent a choice to finish the game.
It must not show a partial result as a completed result.

## 7. Domain boundaries and modules

Use a modular monolith.
All modules run in one application process.
Boundaries describe ownership. They do not require separate services.

### 7.1 Game context

The Game context owns:

- Choice and outcome types.
- Score matrix.
- Round resolution.
- Match settings and state transitions.
- Opponent policies.
- Result summaries and game invariants.

The match is the aggregate root.
An aggregate is the set of data that must remain consistent during one change.
The match controls round order, score totals, and final status.

Use pure functions for scoring and opponent policies.
Game code must not import FastAPI, a provider SDK, SQLite, or Logfire.
Pydantic can define domain contracts.

### 7.2 Player context

The Player context owns:

- Construction of the model observation.
- Separation of system rules and visitor strategy.
- Model decision generation.
- Decision validation.
- Model-attempt records and bounded retries.

Expose one narrow operation:

```python
async def decide(observation: Observation, strategy: str) -> DecisionResult:
    ...
```

`DecisionResult` contains the validated decision and execution metadata.
Provider failures use explicit error types.
Do not return a fabricated decision after failure.

### 7.3 Match record context

The Match Record context owns:

- Storage of match settings and committed rounds.
- Replay read models.
- Trace and span references.
- Reviewed public trace references.
- Stored use events and retention procedures.

Storage adapters implement these responsibilities.
They do not decide scores or opponent choices.

### 7.4 Application coordination

The match runner coordinates the three contexts.
It creates observations, requests decisions, resolves rounds, and commits results.
It also establishes tracing scopes and applies resource limits.

The HTTP layer validates transport input and calls application operations.
It must not contain game rules.
The browser renders read models. It must not recalculate authoritative scores.

### 7.5 Proposed source layout

```text
pylemma/
  SPEC.md
  AGENTS.md
  README.md
  CHANGELOG.md
  pyproject.toml
  uv.lock
  src/pylemma/
    game/
      models.py
      rules.py
      opponents.py
    player/
      models.py
      prompts.py
      service.py
    records/
      models.py
      sqlite.py
    application/
      runner.py
      admission.py
    web/
      app.py
      routes.py
      static/
        index.html
        app.js
        styles.css
    telemetry.py
    settings.py
    cli.py
  tests/
    unit/
    integration/
    fixtures/
  docs/
    architecture.md
    decisions/
    development/
    runbooks/
```

This layout is a starting point, not a requirement for empty files.
Create a file only when it owns a clear responsibility.
Keep one module instead of several empty abstraction layers.

Do not create generic `utils`, `managers`, or `services` collections.
Introduce an interface only at a real external boundary or a useful test seam.
Do not create repositories for every data type.
Do not add a dependency injection framework.

## 8. Data contracts

Use explicit Pydantic models at external boundaries.
Reject unknown fields where they can hide a contract error.
Use bounded strings and strict choice values.

### 8.1 Match settings

Store these immutable values:

- Match identifier.
- Optional parent match identifier.
- Strategy text and its hash.
- Opponent identifier and version.
- Rules version.
- Scheduled round count.
- Provider and pinned model identifier.
- Model settings supported by the selected provider.
- System prompt version.
- Public-record notice version.
- Application version or source revision.
- Creation time in UTC.

Record provider parameters actually sent.
Do not claim deterministic model behavior from a seed or temperature setting.

### 8.2 Decision

```json
{
  "choice": "cooperate",
  "stated_reason": "The opponent cooperated last round. I will cooperate again."
}
```

Allowed choices are `cooperate` and `betray`.
The stated reason contains 1 to 240 characters.
Trim surrounding whitespace before validation.
Reject an empty reason after trimming.
Do not require hidden reasoning or detailed internal deliberation.

### 8.3 Round record

Store:

- Match identifier and round number.
- Exact permitted observation.
- Both choices and stated reasons.
- Both score changes and cumulative totals.
- Start and completion times.
- Trace identifier and optional span identifier.
- Decision attempt count.
- Token usage, where supplied by the provider.
- Estimated model cost, where available.

Use `null` for unknown usage or cost.
Unknown cost is not zero cost.
Label estimated cost as an estimate.

### 8.4 Storage design

Use SQLite for the first hosted instance.
Use a persistent volume and one application worker process.
Use short transactions and enable appropriate SQLite concurrency settings.
Do not hold a transaction during a model request.

Start with these tables:

- `matches`: settings, status, timestamps, error category, and public trace reference.
- `rounds`: committed outcomes and permitted observations.
- `attempts`: execution status and bounded usage metadata.
- `admissions`: idempotency and temporary cost reservations.
- `events`: the small set of defined product events.

Give `rounds` a unique constraint on `(match_id, round_number)`.
Commit each outcome and match progress in one transaction.
Use stored round records to reconstruct totals and verify consistency.

Store replay data separately from Logfire.
Logfire retention must not determine whether a game replay can render.
Use versioned, ordered SQL migrations.
Do not add an object-relational mapping layer without a demonstrated need.

## 9. Match execution

### 9.1 State model

Allowed states:

```text
pending -> running -> completed
pending -> interrupted
running -> failed
running -> interrupted
```

`completed`, `failed`, and `interrupted` are terminal states.
A new attempt creates a new match.

`pending` exists between accepted storage and task start.
Do not accept an unlimited waiting list.
Reject new requests when execution capacity is full.

### 9.2 Execution procedure

1. Validate the strategy and opponent identifier.
2. Check the public-record acknowledgement.
3. Check rate, concurrency, and cost limits.
4. Reserve execution capacity and a bounded cost allowance.
5. Store the match with status `pending`.
6. Start one application task for the match.
7. Change the status to `running`.
8. Open the match trace.
9. Build both observations from completed rounds.
10. Get the model player's decision.
11. Get the opponent's decision from the fixed observation.
12. Validate both decisions.
13. Resolve the outcome with the score matrix.
14. Commit the round and updated match state.
15. Emit the committed outcome to telemetry.
16. Repeat until ten rounds complete or an error stops the match.
17. Store the terminal status.
18. Release capacity and settle the cost reservation.

A failed storage write must not expose a resolved round to the browser.
A telemetry export failure must not change game results.
Mark missing trace access honestly when telemetry is unavailable.

### 9.3 Retries

Allow at most two provider requests per round.
This limit includes validation repair and transport retries.
Disable hidden provider retries that exceed this limit.

Allow one repair request after an invalid structured decision.
Allow one retry for an eligible transient provider failure instead.
Both cases share the same remaining-attempt allowance.

Do not retry authentication errors or exhausted budgets.
Do not replace the strategy after failure.
Record every attempt and its outcome.

The maximum is twenty provider requests for a ten-round match.
A model timeout can still incur provider charges.
Keep a conservative reservation when final usage is unknown.

### 9.4 Restart behavior

On startup, mark stored `pending` and `running` matches as `interrupted`.
Preserve their completed rounds.
Release their execution slots.
Reconcile cost reservations conservatively.

Do not repeat an uncertain provider request automatically.
Do not claim durable execution or exactly-once model requests.
Run one application process until a different execution design is justified.

## 10. Model behavior

Use Pydantic AI for the model-controlled player.
Pin a supported model identifier during the initial integration phase.
Record the selected identifier and selection evidence in a decision record.

The system prompt defines the score rules and output contract.
The visitor strategy is separate, clearly labelled input.
The application supplies only the permitted observation.

The model has no tools.
It cannot read files, browse the web, or change application settings.
The output schema limits its action to the two legal choices.

Request a short stated reason.
Do not claim that the reason identifies the model's internal decision process.

Use a fake player adapter for ordinary automated tests.
Live model tests require explicit configuration and a bounded spend limit.

## 11. Logfire integration

Logfire is a required product integration.
It must be useful before visual polish starts.

### 11.1 Trace structure

Use one root trace per executed match.
Use readable, stable span names.

```text
match.run
  round.run [round_number=1]
    player.decide
      model request [attempt=1]
    opponent.decide
    round.resolve
    round.commit
  round.run [round_number=2]
    ...
  match.complete
```

Attach the match identifier and rules version to the root span.
Attach the round number to each round span.
Store trace references in the match record.

Record:

- Strategy and system prompt versions.
- Permitted model input and structured model output.
- Opponent policy branch.
- Validation errors and retries.
- Score changes and match summary.
- Model duration and available token usage.
- Estimated cost and its estimation basis.
- Application errors with safe messages.

Do not place every request header or environment variable into trace attributes.
Do not export provider credentials, network identifiers, or visitor access metadata in public match traces.

### 11.2 Public sharing: verified facts

The official Logfire documentation describes public trace links.
The UI can create links with expiration settings.
People with a link can inspect the complete trace and its attributes.
Project settings can list and revoke these links.

Selecting an inner span does not limit exposure to that span.
Review the full trace before sharing it.

The official Terraform project schema includes public/private visibility.
Anonymous project access and applicable plan limits remain unverified for this implementation.

No supported automatic trace-sharing endpoint has been verified for this project.
Do not infer an endpoint from a browser request or another vendor's API.

### 11.3 Release sharing strategy

Use reviewed featured matches as the initial public Logfire experience.
Create their public trace links through the supported Logfire UI.
Store each verified URL in the matching record.

Provide a small operator CLI for recording or removing that URL.
Validate HTTPS and an explicit Logfire host allowlist.
The CLI must not accept executable URLs or arbitrary redirect destinations.
Do not add a public administration endpoint.

A visitor match without a public trace link must not show a working trace button.
Show a clear alternative:

> This match has no public trace. Inspect an example match in Logfire.

The alternative must identify the example match.
It must not imply that the example contains the visitor's execution.

### 11.4 Public-project experiment

Test a dedicated project with synthetic match data.
Check signed-out access to the project and individual traces.
Check plan requirements, retention, and revocation behavior.
Record the evidence in a decision record.

If public access works, consider direct links for every eligible match.
The visitor notice and telemetry review must cover that exposure first.
Public-project access is an enhancement, not a launch dependency.

### 11.5 Retention and unavailable links

Public links can expire or be revoked.
Underlying telemetry also has a retention period.
Do not describe a public trace as permanent.

Keep an operator procedure for checking featured links.
Remove or replace expired references.
An unavailable Logfire link must not prevent replay access.

### 11.6 Local activation path

Provide a local example that uses normal Logfire authentication.
The developer creates or selects their own Logfire project.
The developer then runs a match and finds its trace.

Hosted play must never request a visitor's Logfire token.
Do not send a local developer's telemetry to the hosted demonstration project by default.

## 12. HTTP interface

Use FastAPI and serve the browser assets from the same origin.
Use ordinary HTTP polling for progress.
WebSockets and server-sent events are not required.

### 12.1 Endpoints

| Method | Path | Responsibility |
| --- | --- | --- |
| `GET` | `/api/config` | Return rules, opponent policies, examples, and notice version. |
| `POST` | `/api/matches` | Validate and accept one match within available limits. |
| `GET` | `/api/matches/{id}` | Return stored match state and committed rounds. |
| `POST` | `/api/events` | Accept only the defined bounded product events. |
| `GET` | `/health/live` | Report process liveness without secrets. |
| `GET` | `/health/ready` | Report local readiness and admission availability. |
| `GET` | `/m/{id}` | Serve the replay page. |

Readiness must not call a paid model endpoint.
Public health responses must not reveal provider credentials or detailed infrastructure settings.

### 12.2 Match creation

Request fields:

- `strategy`: 1 to 1000 characters after trimming.
- `opponent_id`: one published identifier.
- `notice_version`: current version.
- `public_record_acknowledged`: `true`.
- `parent_match_id`: optional existing match identifier.

Require an `Idempotency-Key` header generated for each intended submission.
Use a random key with at least 128 bits of entropy.
Reuse it when retrying the same HTTP submission.

The same key and body return the same match identifier for 24 hours.
The same key with a different body returns HTTP `409`.
Keep a unique storage constraint on the key.

Return HTTP `202` with the match identifier and replay URL after acceptance.
Return HTTP `422` for invalid input.
Return HTTP `429` for rate or concurrency limits.
Return HTTP `503` when the model service or daily budget is unavailable.

Persist the accepted match before returning success.
Do not charge a second model run for an HTTP retry.

### 12.3 Progress reads

Poll once per second while the match is active.
Stop polling after a terminal state.
Reduce polling while the page is hidden.
Return only committed rounds and safe error categories.

Use random match identifiers with at least 128 bits of entropy.
Do not provide an endpoint that lists visitor matches.

## 13. Cost, abuse, and operational limits

Initial configurable limits:

| Limit | Initial value |
| --- | ---: |
| Strategy length | 1000 characters |
| Stated reason length | 240 characters |
| Rounds | 10 |
| Requests per round | 2 |
| Model output allowance | 256 tokens per request |
| Provider request timeout | 15 seconds |
| Match wall-clock deadline | 180 seconds |
| Concurrent matches per process | 4 |
| New matches per source per 10 minutes | 3 |
| Match request body | 8 KiB |

These are starting settings, not verified performance results.
Measure provider behavior before release.
Document any adjustment and its reason.

Require an explicit daily model-spend cap before hosted launch.
Choose a per-match reservation from worst-case bounded requests and current model prices.
Reserve enough allowance before accepting a match.
Reject a request when the remaining budget cannot cover it.

Define the daily reset at 00:00 UTC.
Keep admitted reservations across a process restart.
Treat unknown charges conservatively until reconciled.
Keep telemetry volume within a separately configured operating budget.

Rate limiting must use trusted proxy configuration.
Do not trust arbitrary forwarded-address headers.
Use short-lived source hashes for rate limits.
Keep source identifiers out of shared traces and replay records.
Document that rate limits reduce abuse but do not prevent all abuse.

Render strategy text and model output as plain text.
Do not render arbitrary HTML or model-generated links.
The model output must never execute as code.

Serve the hosted application over HTTPS.
Keep provider and Logfire credentials in server configuration.
Define a database backup and restore procedure before public release.

## 14. Measurement

Measure participation before interpreting growth.
Use a small fixed event vocabulary.

Events:

- `match_accepted`: emitted by the server.
- `match_completed`: emitted by the server.
- `match_failed`: emitted by the server.
- `match_interrupted`: emitted by the server.
- `rematch_accepted`: emitted when a parent identifier is present.
- `replay_opened`: bounded browser event.
- `logfire_link_clicked`: bounded browser event.
- `example_trace_clicked`: bounded browser event.
- `replay_link_copied`: bounded browser event.
- `local_setup_clicked`: bounded browser event.

Do not accept arbitrary event names or arbitrary attributes.
Do not store strategy text in product-event payloads.
Treat browser events as untrusted, approximate measurements.

Report these measures:

- Completed matches divided by accepted matches.
- Matches with a rematch divided by completed parent matches.
- Public-trace clicks divided by eligible replay opens.
- Example-trace clicks separately from own-match trace clicks.
- Local-setup clicks.
- Provider cost per completed match, with failed-match costs included separately.
- Median and upper-percentile match duration.

A click does not prove a Logfire view, signup, or activation.
Measure Logfire activation only with consented confirmation or Pydantic collaboration.
Do not report replay links as unique people.
Do not claim that a small initial sample establishes a conversion rate for a wider audience.

## 15. Validation and tests

### 15.1 Domain tests

Verify every score-matrix entry.
Verify all opponent branches and their boundary rounds.
Verify cumulative scores and draw behavior.
Verify round order and terminal-state rules.
Verify that partial matches have no winner.

Use these reference outcomes:

- Ten mutual cooperations produce scores of 30 and 30.
- Ten mutual betrayals produce scores of 10 and 10.
- Ten player betrayals against Optimist produce scores of 50 and 0.
- Ten player cooperations against Opportunist produce scores of 21 and 36.
- Ten player betrayals against Grudge Holder produce scores of 14 and 9.

### 15.2 Boundary tests

Verify:

- Invalid choices, missing reasons, and excessive lengths are rejected.
- Current opponent choices never enter player observations.
- Opponent policies receive only completed history.
- Two attempts is the maximum, including SDK retries.
- A failed attempt does not commit an outcome.
- Concurrent duplicate submissions create one match.
- Cost reservations prevent admission above the budget.
- Restart handling preserves completed rounds and marks interruption.
- A failed telemetry export does not change stored scores.
- Replays perform no model requests.
- Public responses contain no credentials or source identifiers.
- HTML-like strategy text renders as text.

### 15.3 Logfire acceptance checks

Use one real, low-cost integration match.
Verify that its trace contains the model request and resolved rounds.
Verify that its trace identifier matches the stored record.
Review every attribute before creating its public link.
Open the link in a signed-out browser.
Verify complete access to the intended match.
Verify that revocation removes public access.
Create a fresh reviewed link for the featured example afterward.

Record actual results and applicable plan settings.
Do not treat documentation alone as proof of deployed behavior.

### 15.4 Interface acceptance checks

Verify keyboard operation and visible focus.
Verify readable contrast and text labels for both choices.
Verify the layout at 375-pixel and desktop widths.
Verify a slow model request and a failed request.
Verify reload during a match and after completion.
Verify that the Logfire control distinguishes own-match and example links.
Verify that reduced-motion settings are respected.

### 15.5 Live evaluation policy

Ordinary tests use fixed player responses.
Live evaluations are separate, opt-in commands.
Each evaluation records its model, settings, prompts, repetitions, failures, and total estimated cost.

Use Pydantic Evals later if repeated prompt comparisons require a structured evaluation suite.
The first release does not need a separate evaluation platform.

## 16. Development workflow and required evidence

Use small implementation steps.
Complete the relevant documentation before closing each step.

For each step:

1. Identify the relevant specification sections.
2. Record the intended behavior and scope.
3. Add meaningful tests for new game or boundary behavior.
4. Make the smallest implementation change.
5. Run the relevant checks.
6. Record the actual command results.
7. Update affected documentation.
8. Record remaining limitations.

### 16.1 Development record template

Store records under `docs/development/YYYY-MM-DD-short-topic.md`.

Each record contains:

- Objective.
- Relevant specification sections.
- Files and contracts changed.
- Decisions and their reasons.
- Checks run and their results.
- Failures and verified corrections.
- Known limits.
- Next implementation step.

Keep records factual.
Do not copy private prompts, credentials, or full tool transcripts.
Do not describe a planned check as a passed check.

### 16.2 Decision record template

Use numbered files under `docs/decisions/`.

Each decision record contains:

- Status and date.
- Problem.
- Constraints.
- Options considered.
- Decision.
- Reason.
- Consequences.
- Evidence links.
- Conditions that would justify a new decision.

Create decision records for model choice, public trace access, retry limits, storage, and material scope changes.
Do not create a decision record for every variable name.
Mark replaced decisions as superseded.
Link each superseded decision to its replacement.

### 16.3 Code documentation

Document domain invariants near the code that enforces them.
Document public module functions and external contracts.
Explain non-obvious decisions and limits.
Use comments for reasons, not line-by-line restatements.

Update the specification when accepted product behavior changes.
Update the architecture document when a module boundary changes.
Update a runbook when an operational command changes.
Keep generated API documentation synchronized with request and response models.

### 16.4 Simplicity review

Before adding an abstraction, answer:

- Which current requirement needs it?
- Which existing implementation cannot satisfy that requirement?
- Can one function or module solve the problem?
- What new failure modes does the abstraction add?
- What documentation and tests will it require?

Prefer explicit functions and data contracts.
Avoid speculative extension points.
Keep dependencies few and justified.

## 17. Implementation phases

### Phase 0: Establish the project contract

Deliver:

- Development instructions in `AGENTS.md`.
- Minimal Python package and locked dependencies.
- Architecture document and term list.
- Test, formatting, and type-check commands.

Exit condition: contributors can install the project and run offline checks.

### Phase 1: Prove the game

Deliver:

- Domain contracts and score matrix.
- Three opponent policies.
- Fake player and ten-round execution.
- SQLite match records.
- Replay data without a browser interface.

Exit condition: all reference scores and domain invariants pass.

### Phase 2: Prove the model and Logfire path

Deliver:

- One configured model adapter.
- Bounded attempts and cost measurement.
- One complete Logfire trace.
- One reviewed public trace link.
- A decision record about public-project access.

Exit condition: a signed-out visitor can inspect the featured match in Logfire.
Do not postpone this check until launch.

### Phase 3: Make the game playable

Deliver:

- Strategy field, presets, and opponent selector.
- Match admission and polling.
- Round timeline, details, and scores.
- Replay and rematch controls.
- Public-record notice and safe text rendering.

Exit condition: a visitor can complete and understand a match without setup instructions.

### Phase 4: Make hosted operation bounded

Deliver:

- Idempotency, concurrency, and rate limits.
- Daily budget and conservative reservations.
- Restart behavior and safe errors.
- Persistent storage backup procedure.
- Featured-link review procedure.
- Product events and measurement definitions.

Exit condition: failure and abuse checks pass within the configured resource limits.

### Phase 5: Prepare the demonstration

Deliver:

- Three reviewed example matches.
- A local Logfire quick start.
- A short demonstration recording.
- A technical explanation with real trace links.
- A small playtest report and one documented improvement.

Exit condition: the complete play, inspect, and rematch flow works for external testers.

## 18. Release criteria

The first release is ready when all conditions are met:

- A new visitor can start a match without an account.
- A completed match contains ten correctly scored rounds.
- Choices are revealed together.
- The player never receives the opponent's current choice.
- Every live player decision comes from the configured model.
- Deterministic opponent behavior is clearly identified.
- The result page distinguishes facts from stated reasons.
- A reviewed example opens in Logfire without project membership.
- Missing public links are represented honestly.
- A developer can run the local example in their own Logfire project.
- Failed and interrupted matches preserve committed rounds.
- Hosted use has explicit rate, concurrency, and spending limits.
- Core tests and relevant interface checks pass.
- Installation, operations, decisions, and development evidence are documented.
- No required documentation describes unimplemented behavior as available.

## 19. Open decisions

Resolve these during implementation:

1. Which pinned model gives acceptable structured decisions at the required cost?
2. Does the selected Logfire plan permit useful anonymous public-project access?
3. Is there a supported API for automatic public trace links?
4. What daily hosted budget does the owner choose?
5. What replay retention period should hosted operation use?
6. Which persistent host meets the single-process design?

These questions do not justify additional product features.
Record verified answers and update the relevant specification sections.

## 20. References and verification status

References checked on 2026-10-26:

- [ASD-STE100 Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf): official writing standard.
- [Logfire public traces](https://pydantic.dev/docs/logfire/observe/public-traces/): public links, full trace exposure, expiration, and revocation.
- [Official Logfire project schema](https://raw.githubusercontent.com/pydantic/terraform-provider-logfire/main/docs/resources/project.md): public/private project visibility.
- [Logfire first trace](https://pydantic.dev/docs/logfire/get-started/first-trace/): local authentication and first-trace workflow.
- [Logfire API keys](https://pydantic.dev/docs/logfire/manage/use-api-keys/): documented API permissions.
- [Logfire pricing](https://pydantic.dev/pricing): plan limits and retention.

The API and pricing pages give different broad statements about Public API availability.
Verify actual account permissions before depending on an API capability.

This specification has no verified deployed Logfire integration yet.
The implementation phases require that verification.

## Cloudflare deployment contract

This section refines the machine release contract for the Cloudflare deployment.
The public domain is pylemma.aor.fyi. The current phase includes deployment and authorized live verification.
Python and Monty run in one Linux container. Cloudflare Worker assets serve the browser.
A SQLite-backed Durable Object owns machine records, replay records, quotas, and lifetime spending reservations.
The container accesses this boundary through authenticated private requests.
Local SQLite remains supported for local installations.

Generation has a daily limit of twenty and a lifetime limit of eighty.
Each attempt reserves USD 0.05 against a USD 4 allowance before the provider call.
Failed and uncertain attempts retain their reservation. The lifetime allowance does not reset at midnight or deployment.
Challenges have daily and lifetime limits of four hundred and sixteen hundred.
The initial authorization is at most USD 5, including verification and an infrastructure buffer.
Cloudflare still meters infrastructure use. Application reservations cannot cap unrelated account charges.
The operator must authorize any increase before changing these limits.

Static pages and stored reads do not start the container.
The idle container is destroyed after thirty seconds. Records survive that destruction.
The application flushes completed traces before responding. Export failures do not change completed results.
Validate generation, challenges, stored replays after replacement, browser rendering, and remote trace delivery before announcing the deployment.

## First-visit experience contract

The current phase teaches the game and explains completed results.
Use player in visitor-facing text. Machine remains the immutable implementation contract.
Explain simultaneous choices, all four scores, and the ten-round objective before asking for a strategy.
Provide a three-step local demonstration without storage, credentials, or model requests.
The demonstration illustrates single-round outcomes. It does not claim to be a completed match.
Supply a default name and complete example strategies.

The browser creates a validated machine with `preview: true` on `POST /api/machines`.
This optional field defaults to false to preserve existing clients.
Preview creation stores the machine but creates no tournament or replay.
The visitor checks its generated summary before starting play.
`POST /api/tournaments` accepts `machine_id` and runs that stored version without generating code again.
Tournament execution shares the challenge execution quota. It does not consume a generation reservation.
A challenge invitation retains its target through preview, reload, and confirmation.
Preview links use the player identifier. Replay links continue to use the replay identifier.

Show shared results and challenge invitations before any creation form.
Label both participants, choices, and points in round details.
Derive explanations from completed outcomes. Do not infer motives or describe code reasons as verified causes.
Show first betrayal, delayed response, and a final mutual betrayal streak when the stored choices support those statements.
For completed trust-v1 tournaments under pd-v1, compare against fixed reference scores.
Always cooperate earns 81 points. Always betray earns 78 points against the same opponent suite.
The score comparison does not measure general intelligence or establish performance against other opponents.
A revision link can preserve the earlier replay for a comparison under the same suite and rules version.

Keep generated code and infrastructure explanations in optional details.
Show a public Logfire link and its purpose when a reviewed reference exists.
Do not show operator publication procedures as visitor instructions.
Verify the demonstration, confirmation, revision, invitation, result, and mobile flows.
Automated and browser checks do not replace comprehension testing with new visitors.

## Public leaderboard contract

The current phase adds public rankings and public game history.
This section supersedes the original exclusion of a global score table.
A new immutable machine field, `public_listing`, defaults to false.
The creation request accepts the same optional field. The browser requires a separate listing choice, unchecked by default.
The existing public-record acknowledgement remains required for creation.
Missing listing fields preserve existing unlisted behavior. Do not publish old records through the public directory.
A completed challenge enters public history only when both players permit listing.
A stored preview does not enter either list until a game completes.

`GET /api/leaderboard` ranks every completed public trust-v1 tournament under pd-v1 by total points, highest first.
Keep repeated games by the same player as separate entries. Equal scores share a rank; subsequent ranks have a gap.
Use replay identifiers to order equal scores consistently.
`GET /api/games` lists the same public tournaments and completed public challenges by completion time, newest first.
Challenge scores do not affect tournament ranks because their opponents can differ.
Both endpoints accept `offset` and `limit`. Offset ranges from zero to 100,000. Limit ranges from one to fifty.
The default page contains twenty entries. Responses include entries, total, and the next offset when another page exists.
Entries contain replay identifiers, game kind, player identifiers and names, scores, and completion time.
Each listed game links to its existing replay. Tournament rows also link to a challenge invitation.
Names do not establish a verified human identity.

Save the compact public summary atomically with each qualifying replay in Cloudflare durable storage.
Local SQLite derives the equivalent read model from stored replays.
Public reads do not call a model, execute a strategy, or start the container.
Retain the current palette, borders, and existing game flow while adding the leaderboard navigation and table.

## Inspect in Logfire contract

The current phase adds a prominent Inspect in Logfire action near each completed result summary.
Replay read models include `logfire_url` and `logfire_access`.
Access is public only when a reviewed public trace reference exists for that exact trace identifier.
Prefer the stored public reference or the operator's reviewed reference map.
Otherwise, generate an account-required trace link from the configured Logfire project URL and validated trace identifier.
Use the supported `q` filter. Add an hour on either side of the completion time when that time exists.
Missing trace identifiers or project configuration produce an unavailable action rather than an invented link.
The interface states whether a Logfire account is required. Links open in another tab without opener access.
Newly completed games load their saved replay before rendering the inspection action.

Accept the verified public-trace highlight parameter `spanId` only as sixteen hexadecimal characters.
That parameter is permitted only on a public-trace path with a universally unique identifier.
Reject unrelated parameters, duplicate parameters, fragments, credentials, and ports.
Public sharing exposes the complete trace. A selected span does not restrict disclosure to that span.
Creating account-free public links remains an operator action through Logfire's documented sharing controls.
Do not describe ordinary project links, project visibility, or connected-app handoffs as account-free public sharing.

## Simple arena contract

This accepted contract supersedes the fixed tournament as the default browser experience.
Existing tournament endpoints and historical replays remain supported.

A visitor enters a strategy through one form. Code inspection is optional.
The public-record acknowledgement remains required. Public discovery consent remains optional.
Each immutable strategy receives at most one completed arena result.
Repeated entry returns that saved result without execution or another allowance reservation.

An arena contains ten matches of ten rounds each, using pd-v1 scoring.
Select the ten most recent distinct strategies with completed public games, excluding the entrant.
Use completion time, then replay identifier, to order candidates.
Only strategies with explicit public discovery consent are eligible.
Fill missing slots by cycling Optimist, Grudge Holder, and Opportunist in that order.
Store the selected identities, source hashes, preset labels, and all completed matches.
A failed match produces no completed arena result. A retry can select a new opponent set.

Arena points sum the entrant's points across the ten matches.
Recent arena results use completion order without ranks. Entrants can face different opponents.
Public arena results require the entrant's consent and public eligibility for every visitor opponent.

Results show a factual event, an explicitly labelled Logfire action, and revision and sharing controls.
Sharing opens an X composer or copies a challenge link. The visitor publishes the post.
Share cards contain the strategy name, short rule, score, and opponent count.
Shared invitations show the strategy first and offer a direct challenge.
Funnel events count completed entries, inspection clicks, share clicks, and referral completions.
Clicks do not prove publication or successful trace access.
Public trace publication retains the full review procedure. No public address is invented.
Daily tournaments, accounts, accumulated points, and ranked matchmaking remain outside this phase.

If a game's trace is restricted or unavailable, offer the existing reviewed public example with an explicit separate-example label.
Count example inspection clicks separately from inspection of the visitor's own game.

## Runtime feedback

Show an indeterminate activity indicator while a visitor request is pending.
Show the request stage and elapsed time without invented round counts or percentages.
Generation and validation share one stage because they share one server request.
Show game execution and result retrieval as subsequent stages.
Stop the indicator on success and failure. Preserve the strategy description and any stored player after failure.
Translate browser connection failures into specific recovery instructions.
Generation has a 45-second total deadline in addition to the provider transport timeout.
Trace failures include only a permitted exception class, never raw exception text.
