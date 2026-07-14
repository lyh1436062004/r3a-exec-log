# cun.ai GPT-5.5 smoke test

- Date: 2026-07-15
- Base URL tested: `https://www.cun.ai/v1`
- Requested model: `gpt-5.5`
- Credential handling: process environment only; no key persisted

## Results

- `GET /v1/models`: HTTP 403, Cloudflare, `Your request was blocked.`
- Minimal Chat Completions request: HTTP 403, `PermissionDeniedError: Your request was blocked.`
- Unauthenticated `GET /`: HTTP 403, Cloudflare, `Your request was blocked.`

## Conclusion

The request is blocked at the Cloudflare/site edge before model authentication or routing can be verified. The API key's validity and the server-returned model therefore cannot be determined from this environment. No formal generation or judging calls were started, and no fallback model was used.
