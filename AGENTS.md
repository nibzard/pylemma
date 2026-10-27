# Development instructions

## Scope and language

Read `SPEC.md` and the current task before changing code.
Implement only the current phase and its required dependencies.
Use ASD-STE100 Simplified Technical English, Issue 9, and the Google developer documentation style guide.
Follow the language rules in `SPEC.md` section 3.
Limit instruction sentences to 20 words and description sentences to 25 words.
Use the official rules and dictionary during editorial review.
Sentence checks do not establish compliance.
Use the terms in `docs/architecture.md` consistently.
Use `python3` for Python commands.

## Implementation procedure

1. Identify the relevant specification sections and intended behavior in a development record.
2. Add meaningful tests for new game behavior and external boundaries.
3. Make the smallest implementation change.
4. Run relevant checks from `README.md`.
5. Record actual results, failures, verified corrections, and remaining limitations.
6. Update affected documentation and complete the simplicity review.
7. Confirm that setup and checks leave tracked and unignored files unchanged.

Use fake players for ordinary tests.
Keep ordinary tests offline and independent of credentials.
Live checks require explicit configuration and an authorized spending limit.
Never remove failing tests or weaken acceptance criteria to claim success.
Ignore generated output and remove tracked build artifacts if introduced.

## Evidence and documentation

Create `docs/development/YYYY-MM-DD-short-topic.md` for each implementation task.
Include every field required by `SPEC.md` section 16.1.
Record commands actually run and their results.
Do not present a planned check as passed.
Do not store credentials, private prompts, or full tool transcripts.

Use the authoritative documentation locations in `SPEC.md` section 3.1.
Link to existing facts instead of copying them.
Create documents only when their phase starts.
Create consequential decision records as required by section 16.2.
Do not create empty directories or documents for future work.
Document public contracts and invariants near their implementation.
Update architecture when boundaries change and runbooks when operational commands change.

## Simplicity review

Record these answers before adding an abstraction:

- Which current requirement needs it?
- Why can the existing implementation not satisfy that requirement?
- Can one function or module solve the problem?
- Which failure modes does the abstraction add?
- Which documentation and tests does it need?

Prefer explicit functions and data contracts.
Keep dependencies few and explain their purpose.
Follow the context boundaries in `docs/architecture.md`.
Do not add generic utility collections, speculative interfaces, or a dependency injection framework.
