# Model selection and request limits

Status: accepted for local integration. Date: 2026-10-27.

## Problem and constraints

T005 needs real decisions through Pydantic AI and a maximum of two requests per round.
The model must support structured output without tools.
Ordinary tests must remain offline. Paid checks need an authorized allowance.

## Options considered

- GPT-4o mini and GPT-4.1 mini have documented structured output and small token prices.
  Their current model pages mark them as deprecated.
- GPT-5.4 nano supports structured output, but its current page also marks it as deprecated.
- GPT-6 Luna supports structured output and offers a lower documented standard token price.
- An automatic agent loop would require coordination between validation retries and transport retries.

## Decision and reason

Use OpenAI Chat Completions through Pydantic AI direct model requests.
Pin the identifier to `gpt-6-luna`. The model page lists no dated snapshot for this model.
This pins the selected identifier; it does not promise unchanged provider behavior or deterministic responses.
Use `reasoning_effort="none"`, `service_tier="default"`, and a maximum of 256 completion tokens.
Omit temperature and seed. Give the model no tools.
Set both the client timeout and the complete request deadline to 15 seconds.

Use one explicit two-iteration loop.
Set OpenAI software development kit (SDK) retries to zero and disable HTTP redirects.
An invalid decision permits one repair request with the unchanged strategy.
A transient failure uses the same remaining request allowance.
Retry connection failures, timeouts, and HTTP 408, 409, 429, and server errors.
Stop immediately for authentication, permission, quota, billing, and other request errors.
Recognize quota errors by machine code or type, including quota errors with HTTP 429.
Store safe categories without provider error text.

Use native JSON Schema output with application validation after every response.
Pydantic AI removes unsupported length constraints from the provider schema.
The application still trims reasons and enforces 1–240 characters.
Unknown fields and invalid choices fail application validation.
Repair input contains a fixed instruction, not the rejected output or validation details.

## Cost basis

The model page lists USD 0.10 per million input tokens and USD 0.50 per million output tokens.
It lists cache writes at USD 0.125 per million tokens.
Use the cache-write rate for all input tokens as a conservative estimate.
Do not apply cached-input discounts.
Record this estimation basis with each attempt.
Missing usage produces unknown cost, including failed requests and timeouts.

Limit serialized prompt and schema input to 32,000 bytes.
Reserve 65,536 input tokens per request, including space for provider framing.
The input remains below the documented long-context price threshold.
Reserve all twenty possible requests before each evaluation match.
The resulting ceiling is USD 0.16640 per match at the recorded rates.
Keep the full reservation when usage is unknown.
This evaluation allowance does not implement persistent hosted admission accounting.

## Consequences

The adapter contains no automatic agent loop or tool execution.
It uses Pydantic AI for provider requests, schema conversion, and response handling.
The dependency is `pydantic-ai-slim[openai]==1.107.0` with `openai==2.29.0`.
The SDK pin preserves the compatible HTTP client contract.
A small response override preserves missing usage before Pydantic AI replaces it with zero.
Dependency upgrades must repeat the HTTP boundary tests.

Successful and failed attempts carry timestamps, actual generation parameters, token usage, estimated cost, and the estimation basis.
The runner asks the selected adapter to validate stored execution settings before starting a match.
A mismatch raises `ValueError` without issuing requests or changing stored state.
The adapter compares all parameters, including the output schema; JSON formatting and key order do not affect compatibility.
The runner assigns match, round, and attempt identifiers before storage.
Round totals remain unknown if any attempt has unknown usage.
The evaluation report records prompts, settings, repetitions, failures, and costs.
Use only synthetic strategies in shared evaluation reports.

## Evidence and reconsideration

Sources checked on 2026-10-27:

- [GPT-6 Luna model, prices, and capabilities](https://developers.openai.com/api/docs/models/gpt-6-luna).
- [GPT-4o mini status](https://developers.openai.com/api/docs/models/gpt-4o-mini).
- [GPT-4.1 mini status](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
- [GPT-5.4 nano status](https://developers.openai.com/api/docs/models/gpt-5.4-nano).
- [Pydantic AI OpenAI integration](https://ai.pydantic.dev/models/openai/).

Offline evidence appears in the [development record](../development/2026-10-27-bounded-model.md).
Account access, latency, and live response quality remain unverified until T007 and T008.
Reconsider this decision if access fails, prices change, a dated snapshot appears, or the response limit prevents valid decisions.
