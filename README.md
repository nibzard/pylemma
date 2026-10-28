# pylemma

Describe your rules for trust. Build a machine. Challenge someone else's.

The browser application requires Logfire and executes AI-generated Python in Monty.
See [Build a machine and challenge a friend](#build-a-machine-and-challenge-a-friend) for startup.

Prisoner's Pylemma is a small trust game under development.
The Game context supports ten rounds against three deterministic opponents.
It includes validated decisions, immutable settings, scoring, and match state transitions.
SQLite storage preserves match settings, completed rounds, attempts, and replay data.
The application runner executes ten rounds with a fake player and preserves partial results after failure.
A bounded OpenAI adapter is available through Pydantic AI.
Optional Logfire tracing and an operator CLI for reviewed links are available.
The browser provides arena entry, shared challenges, and saved replays.
See [SPEC.md](SPEC.md) for the product contract.

## Install

Use Python 3.12 or later and `uv`.
The verified versions appear in the [development record](docs/development/2026-10-27-project-foundation.md).
Run these commands from the repository root:

```sh
uv sync --locked
uv run --offline --locked python3 -c 'import pylemma; print(pylemma.__version__)'
```

The first command downloads locked dependencies and creates `.venv`.
Installation needs network access unless the required packages already exist in the `uv` cache.
Pydantic validates the game contracts.
The game checks need no provider credentials or Logfire account.

## Offline checks

After installation, run:

```sh
uv run --offline --locked pytest
uv run --offline --locked ruff check .
uv run --offline --locked ruff format --check .
uv run --offline --locked mypy
```

Tests disable internet sockets through `pytest-socket`.
Local Unix sockets support the asynchronous event loop.
These commands do not call a model or export telemetry.
The formatting check does not change source files.
To apply formatting during development, run `uv run --offline --locked ruff format .`.

## Offline match execution

Create a pending match with `MatchStore.create(settings)` before running it.
Use `provider="fake"`, `model_id="fake-v1"`, and `model_settings_json="{}"` for fake execution.
Use `system_prompt_version="fake-v1"` for the fake player.
The fake player uses fixed decisions and sends no provider parameters.

```python
import asyncio

from pylemma.application.runner import run_match
from pylemma.game.models import Decision
from pylemma.player.service import FakePlayer

player = FakePlayer((Decision(choice="cooperate", stated_reason="I cooperate."),) * 10)
# Use your initialized store and pending match identifier.
replay = asyncio.run(run_match(store, match_id, player))
print(replay.match.player_total, replay.match.opponent_total)
```

`run_match` accepts only a pending match and returns stored replay data.
Read progress with `store.read(match_id)` during execution.
Both observations contain only completed history and exist before either decision.
An exhausted fake script stops the match with `invalid_decision`.
A failed round adds no outcome or points. A partial match has no winner.
The runner does not resume stopped matches or retry requests.

## Model execution and live evaluation

`ModelPlayer` in `pylemma.player.model` implements the same player boundary.
It uses the fixed `MODEL_ID`, `PARAMETERS`, and `SYSTEM_VERSION` constants for real match settings.
Store `provider="openai"` with these constants before execution.
The runner validates these settings before starting the match or sending requests.
Incompatible settings raise `ValueError` and leave the pending match unchanged.
Custom players must implement `validate_settings(settings)` as well as `decide`.
Close the player with `await player.close()` after use.
Each round permits two provider requests, including repair and transport retries.
The runner stores every returned attempt before the outcome.
See the [model decision](docs/decisions/002-model-and-retry-limits.md) for model selection and cost evidence.

Live evaluations require provider credentials and an authorized spending allowance.
Set `OPENAI_API_KEY` in your shell or secret manager. The command does not load `.env` files.
After authorization, run this explicit evaluation:

```sh
mkdir -p .evaluations
uv run --offline --locked python3 -m pylemma.evaluate \
  --allow-live --max-cost-usd 0.20 --repetitions 1 \
  > .evaluations/evaluation.json
```

Here, `--offline` prevents package downloads. The explicit evaluation still calls the model provider.
The command runs one ten-round match against Optimist with a fixed cooperation strategy.
Use `--strategy` to supply another synthetic strategy.
The report includes the system prompt, visitor strategy, observations, decisions, attempts, failures, and estimated costs.
Do not put private information in evaluation strategies.
Reports are local, ignored output. The command does not publish or export telemetry.

The command reserves USD 0.16640 per match at the recorded rates.
It rejects insufficient allowances before any model request.
Repetitions range from one to ten and share the explicit allowance.
Unknown costs remain null; the report retains the conservative reservation.
Zero token counts for nonempty model requests are unavailable usage, so their estimated cost remains unknown.
Recheck published prices before authorizing live execution.
Hosted daily budgets and persistent reservations remain in T013.
One real match and remote trace are verified in the [live verification record](docs/development/2026-10-27-live-logfire.md).
Actual billing and publication review remain open.

## Match tracing and reviewed links

Pass an explicitly configured Logfire instance to `run_match(..., telemetry=client)`.
Use `pylemma.telemetry.configure()` after selecting the operator's Logfire project through normal authentication.
The default `telemetry=None` sends no traces and stores no trace identifiers.
Tracing covers match execution, rounds, player requests, retries, opponent policies, resolution, and commits.
Stored identifiers do not prove export delivery or public access.
Exporter failures do not change game results.

Read the [trace review runbook](docs/runbooks/trace-review.md) before live execution or link management.
It includes executable offline checks and the full-trace review procedure.
The [public-access decision](docs/decisions/003-public-trace-access.md) records documented capabilities and unverified account questions.
The operator CLI records or removes reviewed references; it does not publish or revoke remote links.
Live trace verification and authorized publication remain in T007 through T009.

## Stored replay data

The `pylemma.records` package reads replays without a browser, model, or Logfire connection.
Use `migrate(Path(...))` from `pylemma.records.sqlite` before creating a `MatchStore`.
The migration function creates the database and applies packaged Structured Query Language (SQL) files in order.
The parent directory must already exist.
Use a private database path for tests and local experiments.

`MatchStore.create(settings)` stores a pending match.
`transition(...)` stores a legal start, failure, or interruption.
`record_attempt(...)` stores each completed request, including failed requests.
`commit_round(...)` stores an outcome and match progress in one transaction.
Call these methods between model requests.

Read an existing match by its identifier:

```python
from pathlib import Path
from uuid import UUID

from pylemma.records.sqlite import MatchStore

store = MatchStore(Path("matches.sqlite3"))
replay = store.read(UUID("01234567-89ab-4cde-8fab-0123456789ab"))
print(replay.match.status, replay.match.player_total, replay.match.opponent_total)
print(replay.match.winner)
```

Replace the example identifier with a stored match identifier.
A missing match raises `KeyError`. Inconsistent records raise a validation error.
Reads do not create or migrate a database.
Unknown token usage and estimated cost remain `None` in Python and `null` in JSON.
A partial match has no winner.
See the [storage decision](docs/decisions/001-sqlite-match-records.md) for transaction and deployment constraints.

## Build

Build a wheel and a source archive with the installed, locked backend:

```sh
uv build --offline --no-build-isolation
```

Artifacts go into ignored `dist/`.
Environments, caches, and build output are ignored by Git.
Setup and checks must leave tracked and unignored project files unchanged.
Keep local secrets in ignored `.env` files.

## Contribute

Read [AGENTS.md](AGENTS.md) before implementation.
See [architecture and terms](docs/architecture.md) for context ownership.
Record actual checks and limitations under `docs/development/`.
Create operational and release documents when their implementation phase starts.

## Build a machine and challenge a friend

The new browser experience generates Python once and runs each decision in a fresh Monty sandbox.
Your machine faces ten recent public strategies. Presets fill empty slots. Share its challenge link to invite another machine.
Stored machine versions and replay links remain available after restart.

Set `OPENAI_API_KEY`, `LOGFIRE_TOKEN`, and `PYLEMMA_DAILY_GENERATIONS` in your shell.
Choose the daily quota within your authorized spending allowance.
Each generation makes at most one provider request with 2,400 output tokens.
The quota bounds request count, not the provider's bill.
The application does not load `.env` files.
Set `PYLEMMA_DATABASE` to a persistent SQLite path when hosting.
Its parent directory must exist.

Start one worker:

```sh
uv run --offline --locked uvicorn pylemma.web.app:hosted --factory --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.
Creation calls the configured provider and sends permitted execution records to Logfire.
Machine and replay reads use stored data without provider calls.
Names, strategies, generated code, and results are available to anyone with their unlisted links.
Public Logfire links require the existing operator review procedure.
Trace identifiers alone do not provide public access.

The original model-per-round sections remain supported as developer examples.
See the machine release contract in [SPEC.md](SPEC.md) for current product behavior.

After reviewing a public trace, attach its link to a machine replay:

```sh
uv run --offline --locked python3 -m pylemma.review_machine \
  --database machines.sqlite3 --replay REPLAY_UUID \
  --url REVIEWED_LOGFIRE_URL --reviewed
```

Replace the uppercase values with the replay identifier and reviewed public URL.
Omit `--url` to clear the stored reference.
This command neither publishes nor revokes the remote public link.
See [trace review](docs/runbooks/trace-review.md) for the required content review.

Challenges have a separate daily quota of twenty times the generation quota.
Run one application worker to preserve the execution admission limit.

## Public deployment

Open https://pylemma.aor.fyi to build a machine or challenge a shared machine.
The Cloudflare deployment stores records outside its temporary container disk.
It has twenty daily generations and eighty lifetime generations under the initial spending allowance.
See [Cloudflare operations](docs/runbooks/cloudflare.md) for deployment, secrets, spending controls, and shutdown.
Run its offline storage checks with `npm test --prefix deploy/cloudflare`.

## Learn the game

The home page includes a short example that makes no model requests.
Describe a strategy and enter the arena. Select the optional preview to inspect generated rules before playing.
Revisions can compare against the previous replay. Shared links open directly on the result or invitation.

Run the factual explanation checks offline:

```sh
node --test tests/web/story.test.mjs
```

## Recent arena results

Open **Recent results** to see completed public arena entries in completion order.
Each strategy receives one arena result. Repeated entry returns that result without execution or another allowance reservation.
Entrants can face different opponents. The page does not assign global ranks.
Each entry links to its replay and challenge invitation.

Select **List my strategy and completed games publicly** to permit discovery and selection as an arena opponent.
The choice is optional and unchecked by default. Existing unlisted games remain unlisted.
Challenges appear publicly only when both players permit listing.
The historical fixed-suite leaderboard remains available through `GET /api/leaderboard`.

`POST /api/arena` accepts `machine_id` and an optional referral identifier.
`GET /api/arena` returns recent public results with the existing pagination parameters.
The browser creates a stored preview first, then starts execution automatically unless preview was requested.
A failed execution keeps the stored player available for another attempt.

Results include a short share card, an X composer link, and a challenge link to copy.
Opening the composer does not publish a post. The visitor controls publication.

## Inspect game execution

Completed results show **Inspect in Logfire** near the score.
A reviewed public trace link opens without an account. Other trace links state that Logfire access is required.
The public example is [The open hand's tournament](https://pylemma.aor.fyi/?replay=bb4976a0-f335-4fec-b795-ac279ce7feb4).
Public links currently require manual creation through Logfire's sharing controls for each trace.
See [the inspection runbook](docs/runbooks/cloudflare.md#inspect-in-logfire-links) to attach another reviewed link.
