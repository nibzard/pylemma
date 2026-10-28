# Prepare the client at startup and simplify entry

## Objective

Move reusable OpenAI client preparation into startup and reduce arena entry to one checkbox.

## Relevant specification sections

The generation, hosted startup, public discovery, simple arena, and section 16.1 contracts apply.

## Files and contracts changed

Profile generation preparation, initialize reusable client state before serving, and simplify the browser form.

## Decisions and reasons

The user selected startup initialization, not a longer idle timeout or a larger container.
Initialization must not make provider calls or consume generation quota.
One required checkbox explicitly covers public records, listing, and eligibility as an arena opponent.
An optional review button replaces the preview checkbox. Existing stored visibility remains unchanged.

## Simplicity review

Use the existing generator constructor and form submission flow.
Do not add background jobs, synthetic provider requests, or a new service.
Tests must prove startup makes no network request and form submission preserves explicit consent.

## Checks run and results

The offline profile used the deployed Python 3.12 image with network disabled and a fake provider transport.
The first request spent 0.612 process CPU seconds resolving `client.chat` and importing SDK resources.
After moving resource resolution and schema generation to construction, first-call elapsed time fell from 0.806 to 0.034 seconds.
These profile runs had no CPU quota and are not hosted latency measurements.
The second calls took 0.009 and 0.008 seconds respectively.
- `uv run --offline --locked pytest -q`: 246 tests passed.
- `uv run --offline --locked ruff check .`: passed.
- `uv run --offline --locked ruff format --check .`: 39 files unchanged.
- `uv run --offline --locked mypy`: passed for 39 source files.
- `node --test tests/web/*.test.mjs`: eight tests passed.
- JavaScript module syntax and `git diff --check`: passed.
- Before-and-after file fingerprints matched for tracked and unignored files.
- Browser checks confirmed one unchecked required checkbox and invalid submission before consent.
- Direct entry completed a public game using a fake builder.
- The review button opened a stored preview without entering the arena.
- Docker build and registry push passed.

One hosted preview generation will verify request preparation within the existing USD 0.01 reservation.
Startup initialization itself makes no provider request.

## Failures and verified corrections

The first profiling script name shadowed the standard Python profile module. Renaming the mounted script corrected the failure.

## Known limits

Moving preparation to startup can shift cold-start time rather than remove it.
A cold container still starts on demand under the existing thirty-second idle policy.

## Next implementation step

Identify reusable preparation, validate both entry actions, and deploy.
