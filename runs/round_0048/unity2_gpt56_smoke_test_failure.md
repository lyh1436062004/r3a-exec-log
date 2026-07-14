# unity2.ai GPT-5.6 smoke test

- Date: 2026-07-15
- Requested model: `gpt-5.6`
- Wire API: Responses
- Credential handling: process environment only; no key persisted

## Results

- Root base URL model listing: request blocked before a usable model list was returned.
- `POST https://api.unity2.ai/responses`: HTTP 401 `INVALID_API_KEY`.
- `POST https://api.unity2.ai/v1/responses`: HTTP 401 `INVALID_API_KEY`.

Both Responses requests used `store=false`, `reasoning.effort=xhigh`, and a minimal output budget.

## Conclusion

The service received and parsed the Responses API requests but rejected the supplied credential. Model routing and the server-returned model identifier could not be verified. No formal experiment calls were started and no fallback model was used.
