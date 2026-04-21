# Phase 6: Auth Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-06
**Phase:** 06-auth-migration
**Areas discussed:** Startup guard for SUPABASE_URL, Deletion failure semantics, /account/me username field

---

## Startup Guard for SUPABASE_URL

| Option | Description | Selected |
|--------|-------------|----------|
| Hard fail with ValueError | Add SUPABASE_URL to the existing validation block in core/config.py. Server refuses to boot without it — same pattern as the other critical vars. | ✓ |
| Soft fail — auth disabled | Log a warning, let server start, but auth middleware will 403 every request. | |
| No guard — fail on first request | Keep current behavior: JWKS fetch fails at import time with an unhandled exception. | |

**User's choice:** Hard fail with ValueError
**Notes:** Consistent with existing OPENAI_API_KEY / PINECONE_API_KEY validation pattern in core/config.py

---

## Deletion Failure Semantics

| Option | Description | Selected |
|--------|-------------|----------|
| Log but don't fail — keep 204 | Same pattern as current Cognito code. DB data already deleted; Supabase admin error is logged but doesn't block the 204. | ✓ |
| Hard fail — 500 if Supabase delete fails | Stricter: if Supabase admin delete fails, endpoint returns 500. Ensures auth record is always cleaned up. | |

**User's choice:** Log but don't fail — keep 204
**Notes:** Preserve exact existing error-handling pattern from lines 108-120 of api/account.py

---

## /account/me Username Field

| Option | Description | Selected |
|--------|-------------|----------|
| Drop the field entirely | Remove username from the response dict. cognito:username claim has no Supabase equivalent. | ✓ |
| Keep as None | Leave the key in the response but return None. | |
| Remap to email | Set username = credentials.claims.get('email'). | |

**User's choice:** Drop the field entirely
**Notes:** clients already get user_id (sub) and email; full claims dict still returned

---

## Claude's Discretion

- Whether to use httpx.Client() (context manager) or bare httpx.delete() for the one-shot Admin API call
- Whether `404 UserNotFound` from Supabase Admin API is treated as success-equivalent (like Cognito's UserNotFoundException)

## Deferred Ideas

- boto3 removal from requirements.txt — Phase 7 (CLEAN-01)
- Supabase Auth user creation/signup flow — out of scope (frontend responsibility)
