# Phase 6: Auth Migration - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 replaces AWS Cognito JWT verification and account deletion with Supabase Auth equivalents. The changes are **middleware-only** — three files change (`core/auth.py`, `core/config.py`, `api/account.py`); the rest of the stack (JWTBearer logic, SQLAlchemy schema, Redis, LangGraph pipeline) is untouched.

Phase succeeds when:
1. A valid Supabase Auth JWT is accepted; an invalid or Cognito-issued JWT is rejected with 403
2. `DELETE /account/me` deletes the Supabase Auth user via Admin API (httpx, no boto3)
3. `COGNITO_REGION` and `COGNITO_POOL_ID` are gone from `.env` and `core/config.py`; `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are present and loaded

Out of scope for this phase (deferred to Phase 7):
- Removing boto3 from `requirements.txt` and `Dockerfile` (CLEAN-01)
- Documenting all env var changes (CLEAN-02)

</domain>

<decisions>
## Implementation Decisions

### Startup Guard
- **D-01:** Add `SUPABASE_URL` to the existing validation block in `core/config.py`. If `SUPABASE_URL` is absent, raise `ValueError` at startup — same pattern as `OPENAI_API_KEY` and `PINECONE_API_KEY`. Server must not boot without a valid Supabase URL to fetch JWKS from.
- **D-01a:** `SUPABASE_SERVICE_ROLE_KEY` should also be validated at startup (required for Admin API account deletion). Add it to the same ValueError guard block.

### JWKS URL Change
- **D-02:** `core/auth.py` changes only the JWKS fetch URL — from:
  `https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_POOL_ID}/.well-known/jwks.json`
  to:
  `{SUPABASE_URL}/auth/v1/keys`
  The `JWTBearer` class in `models/JWTBearer.py` is unchanged — it is already provider-agnostic via `jose.jwk.construct()`.

### Env Var Changes
- **D-03:** Remove `COGNITO_REGION` and `COGNITO_POOL_ID` from `core/config.py` and from the ValueError guard. Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` as module-level constants via `os.getenv()`.
- **D-03a:** boto3 import stays in `api/account.py` for Phase 6 — it is physically removed only in Phase 7 (CLEAN-01). Phase 6 only removes the boto3 *call* (replaces with httpx).

### Account Deletion
- **D-04:** Replace the boto3 `admin_delete_user` call in `api/account.py` with an httpx DELETE to `{SUPABASE_URL}/auth/v1/admin/users/{user_id}` using `Authorization: Bearer {SUPABASE_SERVICE_ROLE_KEY}`. Use synchronous `httpx.delete()` — consistent with the existing sync-inside-async pattern in the endpoint.
- **D-05:** Keep the **"log but don't fail"** pattern for Supabase Admin API errors. If the httpx call fails (network error, non-2xx, etc.), log the error and still return 204. Rationale: DB data is already deleted at that point; making the admin delete a hard requirement risks stranding users who need to retry deletion due to transient errors.

### `/account/me` Response
- **D-06:** Drop the `username` field entirely from the `GET /account/me` response. The `cognito:username` claim does not exist in Supabase JWTs. Removing it keeps the response clean; clients already get `user_id` (sub) and `email`. The `claims` dict (full JWT payload) is still returned, so nothing is hidden.
- **D-06a:** Also remove the `credentials.claims.get("cognito:username")` line from the handler — it will always return `None` and is misleading to leave in.

### Claude's Discretion
- Whether to use `httpx.Client()` (with context manager) or a bare `httpx.delete()` call — pick whichever is cleaner for a single one-shot request.
- Exact error classification for the httpx Supabase deletion (e.g., whether `404 UserNotFound` is treated as success-equivalent like the current Cognito `UserNotFoundException`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing auth code (read before changing anything)
- `core/auth.py` — current Cognito JWKS fetch; only the URL changes
- `models/JWTBearer.py` — JWTBearer class; **do not modify** — already provider-agnostic
- `core/config.py` — module-level env var loading; add SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY here, remove COGNITO_* here
- `api/account.py` — full account deletion + info endpoints; boto3 call replaced with httpx; username field removed

### Requirements (authoritative)
- `.planning/REQUIREMENTS.md` §Auth Migration — AUTH-01 through AUTH-04 (exact acceptance criteria)
- `.planning/ROADMAP.md` §Phase 6 — 4 success criteria (the curl test, JWT acceptance/rejection, env var check, Admin API delete)

### Phase 5 context (upstream dependency)
- `.planning/phases/05-database-migration/05-CONTEXT.md` — confirms DB is already on Supabase; Phase 6 builds on this

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `models/JWTBearer.py` `JWTBearer` class — zero changes needed; `jose.jwk.construct()` + `key.verify()` are provider-agnostic and handle RS256 keys from any JWKS endpoint including Supabase
- `core/auth.py` `JWKS.model_validate(requests.get(...).json())` pattern — keep the same; only the URL changes
- `api/account.py` httpx is already in `requirements.txt` — no new dependency needed for the Admin API call

### Established Patterns
- `core/config.py` validation block: `if not OPENAI_API_KEY or not PINECONE_API_KEY: raise ValueError(...)` — add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to this same block
- `api/account.py` "log but don't fail" pattern for Cognito errors (lines 108-120) — preserve exactly for Supabase Admin API errors
- Sync HTTP calls inside async route handlers: existing pattern in `core/auth.py` uses `requests.get()` at import time; `api/account.py` Cognito call is sync boto3 inside async def — use sync `httpx.delete()` to match

### Integration Points
- `core/config.py` — single source of truth for env vars; SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY added here, then imported by `core/auth.py` and `api/account.py`
- `core/auth.py` — imported by `main.py` at startup (line 9); JWKS fetch happens at module import time
- `main.py` `auth = JWTBearer(jwks)` and `optional_auth = JWTBearer(jwks, auto_error=False)` — both derive from the JWKS fetched in `core/auth.py`; no changes needed in `main.py`

### What does NOT change
- `models/JWTBearer.py` — untouched
- `main.py` — untouched (auth and optional_auth instances derived from same JWTBearer class)
- All other API routes — untouched (auth dependency pattern unchanged)
- Redis, Pinecone, LangGraph pipeline — fully out of scope

</code_context>

<specifics>
## Specific Ideas

- The Supabase JWKS endpoint (`/auth/v1/keys`) returns the same JWKS JSON structure as Cognito's `.well-known/jwks.json` — the `JWKS.model_validate(...)` call works as-is
- Supabase Auth JWTs use `sub` (UUID) as the user identifier — same as Cognito; no change needed to `user_id = credentials.claims.get("sub")` in either endpoint
- For the Admin API delete, the user ID from `sub` is the Supabase Auth user UUID — pass it directly as the path parameter: `DELETE /auth/v1/admin/users/{user_id}`
- Per AUTH-01 acceptance criteria: verify Supabase is using asymmetric signing by calling `curl {SUPABASE_URL}/auth/v1/keys` — must return non-empty `keys` array before writing auth code

</specifics>

<deferred>
## Deferred Ideas

- **boto3 removal from requirements.txt and Dockerfile** — Phase 7 (CLEAN-01); boto3 import stays in api/account.py through Phase 6 even though it's no longer called
- **Supabase Auth user creation/signup** — out of scope per REQUIREMENTS.md; frontend handles Supabase Auth SDK
- **Row Level Security** — out of scope per REQUIREMENTS.md SUPA-01

</deferred>

---

*Phase: 06-auth-migration*
*Context gathered: 2026-04-06*
