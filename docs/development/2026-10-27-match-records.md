# Match storage and replay reads

## Objective and scope

T003 implements storage for development round 1.
Relevant specification sections are 5.5, 7.3, 8, 9.1–9.3, 15.2, and 16.
Store immutable settings, observations, outcomes, attempts, timestamps, and trace references.
Commit each outcome with match progress. Reconstruct replay totals without external services.
Admission, events, startup coordination, and provider execution remain in their assigned tasks.

## Decisions and simplicity review

SQLite persistence requires an external boundary that the pure Game context cannot provide.
One adapter and explicit record contracts satisfy this requirement without an object-relational mapping library.
The standard library supplies SQLite; no new dependency is needed.
Transactions introduce lock contention and partial-write risks.
Tests must cover migration rollback, outcome rollback, concurrent writes, and replay consistency.
The architecture and storage decision describe the public contracts and operational limits.

## Files and contracts changed

- `records/models.py` defines permitted observations, attempts, committed rounds, and replay contracts.
- `records/sqlite.py` supplies ordered migrations, atomic writes, and consistent replay reads.
- `records/migrations/` contains the initial match, round, and attempt schemas.
- `tests/integration/test_records.py` exercises storage behavior with temporary databases and fixed decisions.
- `README.md` documents the implemented API and replay use.
- `docs/architecture.md` describes the Match Record boundary and technical terms.
- `docs/decisions/001-sqlite-match-records.md` records the storage choice and consequences.
- `.gitignore` covers SQLite journals in addition to existing caches and database files.

No runtime dependency was added. No build artifact is tracked.

## Checks and results

The first complete check passed all 109 tests. Additional integrity checks increased the total to 115.
The current suite passes with network sockets disabled on Python 3.14.3.
Ruff and Mypy pass after the corrections below.

Tests cover fresh migrations, upgrades, repeated migration calls, changed history, and migration rollback.
A failing database trigger proves that outcome insertion and progress updates roll back together.
Concurrent commits of the same round produce exactly one stored outcome.
Tests verify foreign keys, duplicate rejection, attempt ordering, legal transitions, and partial-match preservation.
Replay tests reopen the database and reconstruct totals of 30/30, 50/0, 21/36, and 14/9.
Domain tests also verify 10/10 for ten mutual betrayals.

Tests compare stored settings, observations, outcomes, timestamps, attempts, and trace references.
Corrupted observations, totals, usage, progress, and relational keys are rejected.
Retry tests aggregate known usage and preserve unknown cost as null.
Replay tests remove the trace identifier and retain an unavailable public URL without making network requests.
Database dumps remain unchanged across repeated reads.
Independent writer checks confirm that storage operations release locks between requests.

No external service or container was created.
Temporary database filenames use `LOOPER_RESOURCE_PREFIX` when available.
Pytest owns its temporary directories. Private verification files use the ignored `.verification/` directory.
Existing cleanup registration remains unchanged.

## Final verification

| Command | Actual result |
| --- | --- |
| `uv sync --locked` | Passed with the existing lockfile. |
| `uv run --offline --locked pytest` | All 115 tests passed on Python 3.14.3. |
| `uv run --offline --locked ruff check .` | Passed. |
| `uv run --offline --locked ruff format --check .` | All 11 Python files passed. |
| `uv run --offline --locked mypy` | No issues in 11 source files. |
| `uv build --offline --no-build-isolation` | Built the source archive and wheel. |
| `uv sync --locked --python /usr/bin/python3` | Installed into a fresh private Python 3.12.3 environment. |
| `uv run --offline --locked pytest` in that environment | All 115 tests passed. |
| `uv pip install --offline --no-deps --reinstall --python <private-python> dist/pylemma-0.1.0-py3-none-any.whl` | Installed the built wheel. |
| Installed-wheel Python check | Imported from site-packages, applied packaged migrations twice, and verified a missing replay lookup. |
| `git diff --check` | Passed. |

The Python 3.12 checks set `UV_PROJECT_ENVIRONMENT` to `.verification/$LOOPER_RESOURCE_PREFIX/check-env`.
The wheel check used that environment's Python executable and a temporary database with the resource prefix.

A file snapshot compared names and SHA-256 hashes before setup and after all final checks.
All 29 tracked and unignored files remained identical, including the pre-existing task context files.
Generated environments, databases, editorial references, caches, and build output remained ignored.
This evidence update is an intentional documentation edit after verification.

## Failures and verified corrections

The initial Ruff check found import ordering and long lines. Formatting corrected these findings.
Mypy found inferred strings in score-matrix construction and an indirect resource import in a test.
Explicit choice types and a direct standard-library import corrected these errors.
A subsequent consistency check needed an explicit optional-value guard for Mypy.
The final type check passes.

The web tool returned HTTP 403 for the official editorial reference.
Python `urllib.request` downloaded the same official PDF, and `pdftotext` extracted the text.
Papercut `pc_01M5X9JC3Y4E94D3PJ20G3WWRH` records this workaround.
Editorial review consulted the official [Issue 9 rules and dictionary](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf).
The review covered technical terms, gradual explanations, sentence limits, and the dictionary entries for record and store.
The architecture document defines transaction, migration, commit, and rollback.
This review does not claim independent certification.

## Known limits and next step

T004 supplies the runner and fake player integration.
Later tasks supply admission, events, startup interruption, and reviewed public trace management.
