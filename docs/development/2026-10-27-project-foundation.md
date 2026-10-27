# Phase 0 project foundation

## Objective and scope

Task T001 establishes an installable package with offline contributor checks.
Relevant requirements are `SPEC.md` sections 3, 7, 16, and phase 0 in section 17.
Later game behavior and release gates remain assigned to T002 through T024.
This record does not claim that the product is released.

## Files and contracts changed

- `pyproject.toml` defines package metadata, Python support, dependencies, and check configuration.
- `uv.lock` fixes dependency versions and artifact hashes.
- `src/pylemma/__init__.py` exposes version `0.1.0`.
- `tests/test_package.py` checks installed metadata and Python requirements.
- `.gitignore` excludes environments, caches, build output, local secrets, and database files.
- `README.md` defines installation, offline checks, and distribution builds.
- `AGENTS.md` requires factual evidence, relevant tests, documentation updates, and simplicity reviews.
- `docs/architecture.md` describes context ownership and implementation terms.

## Decisions and reasons

Use Python 3.12 as the minimum supported version.
Use a source directory layout to separate importable code from repository files.
Use Hatchling for package builds and `uv` for locked installation.
Include the pinned build backend in development dependencies to support offline builds without build isolation.
Use pytest-socket to disable sockets during ordinary tests.
Use Ruff for formatting and code checks, and Mypy for strict type checks.
Add no runtime dependencies before a feature needs them.
Keep future context modules and operational documents absent until their phases start.

## Checks and results

Verification ran on Linux with `uv 0.10.0` and Python 3.12.3.
Initial editable installation and package tests also passed on Python 3.14.3.
The clean verification used an empty cache and new environment under `.verification/$LOOPER_RESOURCE_PREFIX/`.
`UV_CACHE_DIR` and `UV_PROJECT_ENVIRONMENT` selected those private locations.
`UV_PYTHON_DOWNLOADS=never` required the installed interpreter.
Installation used network access. All subsequent checks used offline mode.

| Command | Actual result |
| --- | --- |
| `uv lock` | Resolved 16 packages and wrote `uv.lock`. |
| `uv sync --locked --python /usr/bin/python3` | Installed 15 packages into the fresh Python 3.12.3 environment. |
| `uv run --offline --locked pytest` | Two tests passed with sockets disabled. |
| `uv run --offline --locked ruff check .` | All checks passed. |
| `uv run --offline --locked ruff format --check .` | Two Python files were already formatted. |
| `uv run --offline --locked mypy` | No issues in two source files. |
| `uv build --offline --no-build-isolation` | Built the source archive and its wheel. |
| `uv venv --offline --python /usr/bin/python3 "$wheel_env"` | Created a separate environment without project dependencies. |
| `uv pip install --offline --python "$wheel_env/bin/python3" dist/pylemma-0.1.0-py3-none-any.whl` | Installed the wheel successfully. |
| `git diff --check` | Passed. |

Here, `$wheel_env` identifies a directory under the private verification directory.
The wheel interpreter ran with `-I` from outside the source tree.
It imported `pylemma` from its own `site-packages` directory.
It confirmed that package and distribution versions both equal `0.1.0`.

A file snapshot covered tracked files and unignored files before setup and after verification.
The snapshot compared file names and SHA-256 content hashes.
Both snapshots matched, including the lockfile, specification, and pre-existing task context.
All generated verification files remained ignored.
No external service, database, or container was created.

## Failures and verified corrections

Ruff 0.17.2 initially checked a Python example inside `SPEC.md` during formatting verification.
The example's layout failed that check.
Explicit Python and `pyproject.toml` include patterns now define Ruff's scope.
The corrected formatting check passed without changing `SPEC.md`.
This tool behavior was recorded with `papercut` as `pc_01M5X8X5ND3M5NTDV0AZRSSTWZ`.

A repeated verification stopped because `uv venv` refused the existing wheel environment.
The verification script now creates a fresh private directory for each run.

## Simplicity review

Phase 0 requires installation and repeatable checks; it does not require application abstractions.
No existing package or check configuration was present.
One package module satisfies the current import contract.
The new tooling can fail during dependency downloads or interpreter selection.
The lockfile, clean installation check, and explicit Python requirement address these risks.
Packaging tests and installation documentation cover the new boundary.
No service interfaces, framework, command dispatcher, or empty context modules were added.

## Known limits and next step

A cold installation needs package downloads.
Offline checks require completed installation and cached build requirements.
Verification covers Linux; other operating systems were not tested.
The documentation follows the project's language rules without claiming independently verified ASD-STE100 compliance.
No model provider, Logfire integration, game runner, storage, or browser interface exists yet.
T002 next implements and tests deterministic game contracts and rules in development round 1.
