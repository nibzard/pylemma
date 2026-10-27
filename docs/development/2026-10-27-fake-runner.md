# Ten-round execution with a fake player

## Objective and scope

T004 completes development round 1 under specification sections 5, 7.2–7.4, 8, 15.1–15.2, 16, and 17.
Fix both observations before decisions. Store outcomes before revealing them.
Preserve completed scores after failure and leave partial matches without a winner.

## Decisions and simplicity review

The current Game and Match Record contexts cannot request player decisions or coordinate execution.
One runner function and one narrow player protocol satisfy this requirement.
The protocol permits offline fake players now and a model adapter in T005.
The fake player returns an explicit result with its decision and execution parameters.
No new dependency is needed.
Boundary failures can leave attempts without outcomes; storage failures can prevent terminal status updates.
Integration tests and architecture documentation must explain these behaviors.
Reuse the existing observation contract to avoid changing the stored format.

## Files and contracts changed

- `player/service.py` defines the player protocol, validated result, explicit failure, and scripted fake player.
- `application/runner.py` starts pending matches and commits ten rounds or a safe failure.
- `tests/integration/test_runner.py` covers reference scores, observation isolation, failures, and committed visibility.
- Package initializers identify the new context and coordination modules.
- `pyproject.toml` permits local Unix sockets for asynchronous event loops. Internet sockets remain disabled.
- `README.md` documents fake execution and the test configuration.
- `docs/architecture.md` describes the implemented boundaries and failure behavior.

Existing `.gitignore` rules cover environments, caches, SQLite files, journals, builds, and `.verification/` output.
No generated artifact is tracked. Tests use private temporary databases with `LOOPER_RESOURCE_PREFIX` names.
No external resource was created.

## Checks and results

All commands ran on Python 3.14.3.

| Command | Actual result |
| --- | --- |
| `uv sync --locked` | Passed; 20 packages resolved and 19 audited. |
| `uv run --offline --locked python3 -c 'import pylemma; print(pylemma.__version__)'` | Printed `0.1.0`. |
| `uv run --offline --locked pytest tests/integration/test_runner.py` | 12 tests passed. |
| `uv run --offline --locked pytest` | All 127 tests passed with internet sockets disabled. |
| `uv run --offline --locked ruff check .` | Passed. |
| `uv run --offline --locked ruff format --check .` | All 16 files passed. |
| `uv run --offline --locked mypy` | All 16 source files passed. |
| `uv build --offline --no-build-isolation` | Built the wheel and source archive in ignored `dist/`. |
| `git diff --check` | Passed. |

A Python script compared SHA-256 file hashes before and after setup, tests, checks, and builds.
The tracked and unignored file sets and contents remained identical, including supplied task context files.

### Round 1 exit evidence

The complete suite includes 77 domain tests, 36 persistence tests, 12 runner tests, and two package tests.
Published opponent matches produce totals of 30/30, 50/0, 21/36, and 14/9.
A synthetic mutual-betrayal opponent produces 10/10 through the runner and storage.
All published policies cooperate in round one, so this synthetic policy exists only in the test.
The existing domain suite independently verifies all five reference totals.

Runner checks inspect observations before both participants compute decisions.
They verify completed history, exact public policy, score totals, and separate strategy delivery.
Neither stated reasons nor the current opponent choice enter player history.
Opponent history contains only completed choices and round numbers.
A database write lock remains available during player execution.
Reads before each commit contain only earlier rounds. Reads after commits match the returned replay.

Failures after zero, three, and nine completed rounds preserve scores and have no winner.
Invalid results and explicit provider failures store safe categories without fabricated outcomes.
A database trigger rejects round four. Only three outcomes and nine points per participant remain visible.
Reopening storage produces the same replay without another player request.
Completed matches reject a second execution.
The domain and persistence suites also verify migrations, rollback, duplicate rounds, immutable settings, and terminal transitions.
These results satisfy the development round 1 exit condition.

### Editorial review

Review consulted the official [Issue 9 rules and dictionary](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf).
Python downloaded the reference into ignored local verification output. `pdftotext` extracted the text.
Review used the word rules, instruction limits, description rules, and dictionary entries, including `RECORD`.
Technical terms follow the architecture document. This review does not claim independent certification.

## Failures and verified corrections

No implementation check failed.
Ruff formatting ran before the passing formatting checks.
A source inspection initially assumed `pytest_socket.py`; the installed distribution uses the `pytest_socket` package.
Importing the package identified its actual source path.
The first papercut report incorrectly attributed this to an external environment; a second report records the verified correction.

## Known limits and next step

Provider execution, retries, telemetry, and hosted resource limits remain in later tasks.
T005 implements the real model adapter and complete request metadata, including retries and failed request usage.
The current fake boundary records one attempt per decision and unknown usage and cost.
Storage failure handling can store a terminal state only while storage remains available.
Unexpected application errors, cancellation, and process restart handling remain in T014.
Real model and Logfire checks are development round 2 requirements, not round 1 gates.
