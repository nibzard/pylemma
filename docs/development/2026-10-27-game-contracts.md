# Game contracts and deterministic rules

## Objective and scope

T002 implements the Game context in development round 1.
Relevant requirements are `SPEC.md` sections 4, 5, 7.1, 8.1, 8.2, 9.1, and 15.1.
Section 8.3 storage records and execution metadata belong to T003.
The game provides strict decisions, immutable settings, outcomes, policies, summaries, and legal state transitions.

## Decisions and simplicity review

The specification requires validated contracts and a match aggregate.
The existing package contains only version metadata.
Three modules separate contracts, scoring, and opponent policies without introducing service interfaces.
Pydantic validates external data and rejects unknown fields.
Frozen models and tuples prevent normal mutation of nested game state.
Provider parameters use an immutable JSON string to preserve nested values without mutable dictionaries.
The selected provider must later validate these parameters and record only parameters actually sent.
Scores and summaries derive from outcomes; callers cannot supply authoritative totals.
Transitions return a new match, so a failed operation cannot partially change the previous match.
Invalid restored state is a new failure mode; constructor validation and round-trip tests cover it.
Public contracts need module documentation, boundary tests, and architecture updates.

## Files and contracts changed

- `game/rules.py` defines strict choices, the immutable score matrix, and pure scoring.
- `game/models.py` defines validated decisions, settings, outcomes, history, and match transitions.
- `game/opponents.py` defines all three policy versions and their fixed branch explanations.
- `tests/unit/test_game.py` covers game behavior and invalid boundary input.
- `pyproject.toml` and `uv.lock` add and lock Pydantic for contract validation.
- `README.md` describes the implemented scope and runtime dependency.
- `docs/architecture.md` documents contracts, derived scores, serialization, and context boundaries.

Existing `.gitignore` rules cover environments, verification files, caches, and build output.
No tracked build artifacts were introduced.

## Checks and results

Verification used Python 3.14.3 and a fresh Python 3.12.3 environment.
The fresh environment used `.verification/$LOOPER_RESOURCE_PREFIX/check-env` through `UV_PROJECT_ENVIRONMENT`.
No external resource, service, or container was created.
The existing cleanup registration was unchanged.

| Command | Actual result |
| --- | --- |
| `uv add 'pydantic>=2.12,<3'` | Resolved 20 packages and locked Pydantic 2.14.1. |
| `uv sync --locked --python /usr/bin/python3` | Installed 19 packages in the fresh Python 3.12.3 environment. |
| `uv run --offline --locked pytest` | All 79 tests passed on Python 3.12.3 and 3.14.3 with sockets disabled. |
| `uv run --offline --locked ruff check .` | Passed. |
| `uv run --offline --locked ruff format --check .` | All seven Python files passed. |
| `uv run --offline --locked mypy` | No issues in seven source files. |
| `uv build --offline --no-build-isolation` | Built the source archive and wheel. |
| `git diff --check` | Passed. |

Policy tests cover all 1,023 possible player histories before rounds 1 through 10 for each policy.
They check exact branch explanations and precedence when the previous betrayal coincides with a scheduled betrayal.
Game tests verify all matrix entries and reference totals: 30/30, 10/10, 50/0, 21/36, and 14/9.
They cover draws, both winners, cumulative totals, cooperation counts, and round-order rejection.
The transition table covers every status against every public transition operation.
Boundary tests cover reason lengths, trimmed strategies, unknown fields, immutable settings, invalid restoration, and failed-round preservation.
A dependency test rejects imports outside the Game context and its permitted contract dependencies.

File snapshots compared names and SHA-256 hashes before setup and after all verification commands.
Tracked and unignored files were identical, including pre-existing task context files.
All generated files remained ignored.

Editorial review used the official [ASD-STE100 Issue 9 rules and dictionary](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf).
The review consulted rules 1.5, 1.12, 5.1, and 6.1 and dictionary entries for the new wording.
The architecture document defines technical verbs used in software descriptions.
This review does not claim independently certified compliance.

## Failures and verified corrections

The initial Ruff check found import ordering and long lines.
Formatting and explicit string splits corrected these issues; the final checks passed.
Mypy found an inferred string type in the exhaustive policy test.
An explicit tuple of valid choices corrected the test annotation.
Restoration tests now deserialize JSON so unrelated Python input types cannot cause false passing results.
Review also added rejection of non-finite values represented by large JSON exponents.
Nested contracts undergo validation again to reject invalid values from unvalidated Pydantic copies.

Web browsing returned HTTP 403 for the official editorial reference.
Python `urllib.request` downloaded the same official file, and `pdftotext` extracted the rules and dictionary.
Papercut `pc_01M5X960C171ZAW5GBWZ65N6H2` records this verified workaround.

## Known limits and next step

T003 implements storage records, execution metadata, migrations, and replay reads.
T004 constructs both observations before decisions and coordinates fake-player execution.
The Game context does not perform storage, provider calls, or telemetry operations.

Provider selection and supported parameter validation remain in T005.
Round-one integration acceptance remains in T004; domain checks alone do not satisfy that gate.
