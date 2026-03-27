# Technical Concerns

_Last updated: 2026-03-22_

## Summary

The deen-backend is an AI-powered Islamic education API built on FastAPI + LangGraph. The most severe issues are security-related: authentication guards are disabled at the router level, leaving all primary AI endpoints fully public and exposing a PII-rich admin dashboard with no access control. A second cluster of concerns covers performance and reliability (synchronous LLM calls inside an async event loop, unbounded in-process memory growth per request). Several incomplete features are registered in the routing table but silently fail at runtime. No linter or formatter is configured, creating consistency risk as the codebase grows.

---

## Critical Concerns

### 1. All primary AI endpoints are unauthenticated

- **Files:** `main.py` lines 51–58
- **Issue:** The `Depends(auth)` guards for `chat_router`, `ref_router`, and `hikmah_router` are commented out. The active lines register the same routers with no dependency at all. Anyone on the internet can call `/chat/stream/agentic`, `/references`, and `/hikmah/elaborate` without a token.
- **Impact:** Unlimited access to OpenAI and Pinecone spend; no user attribution; no audit trail.
- **Fix approach:** Uncomment lines 51–54 and remove the bare `app.include_router(...)` calls on lines 56–58. Also remove the duplicate commented-out block on lines 60–62.

```python
# main.py — current (broken):
# app.include_router(reference.ref_router, dependencies=[Depends(auth)])  # commented out
app.include_router(reference.ref_router)  # active, no auth

# Correct state:
app.include_router(reference.ref_router, dependencies=[Depends(auth)])
```

### 2. `/admin/memory` dashboard is fully public

- **Files:** `api/memory_admin.py`, `main.py` line 69
- **Issue:** The router at `/admin/memory` exposes a full HTML dashboard and four JSON endpoints (`/{user_id}/profile`, `/{user_id}/notes`, `/{user_id}/events`, `/{user_id}/consolidations`) with zero authentication. Any caller who knows (or guesses) a `user_id` can read that user's complete learning history, behavioral profile, knowledge gaps, and interest notes.
- **Impact:** Direct GDPR/CCPA exposure; full PII leak of every user's memory profile.
- **Fix approach:** Add `dependencies=[Depends(auth)]` when registering the router in `main.py`, and restrict to admin-role claims. Alternatively, block the router entirely in production via an `ENV` guard.

### 3. JWT token expiration is never validated — expired tokens are accepted

- **Files:** `models/JWTBearer.py` lines 60–63
- **Issue:** The bearer class calls `jwt.get_unverified_claims()` and `jwt.get_unverified_header()`, then verifies only the cryptographic signature via `key.verify()`. The `exp` claim is never checked. A token issued last year with a valid signature will be accepted indefinitely.
- **Impact:** Revoked or expired sessions remain permanently valid. Account deletion (`DELETE /account/me`) leaves the former user's token still accepted by the API.
- **Fix approach:** Replace `get_unverified_claims` with `jwt.decode(jwt_token, key, algorithms=[...], options={"verify_exp": True})` from `python-jose`. The JWKS public key required for this is already loaded in `core/auth.py`.

```python
# models/JWTBearer.py — current (broken):
claims=jwt.get_unverified_claims(jwt_token),  # exp never checked

# Correct:
claims=jwt.decode(jwt_token, public_key, algorithms=["RS256"])
```

### 4. Global exception middleware leaks raw exception messages to clients

- **Files:** `main.py` lines 77–84
- **Issue:** The `catch_exceptions_mw` middleware catches all unhandled exceptions and returns `{"detail": "internal_error", "error": str(e)}`. The `str(e)` field may contain internal SQL errors, file paths, LLM API error bodies, or secrets embedded in exception messages.
- **Impact:** Information disclosure that aids attackers in understanding the system internals.
- **Fix approach:** Remove `"error": str(e)` from the JSON response. The full traceback is already printed to server logs via `print(tb)`, which is sufficient for debugging.

```python
# main.py line 84 — current (leaks):
return JSONResponse(status_code=500, content={"detail": "internal_error", "error": str(e)})

# Safe:
return JSONResponse(status_code=500, content={"detail": "internal_error"})
```

### 5. Debug endpoints exposed publicly in all environments

- **Files:** `main.py` lines 89–93 (`/_debug/db`), lines 107–109 (`/_routes`)
- **Issue:** `GET /_debug/db` runs a live `SELECT version()` query against the production database and returns the full PostgreSQL version string. `GET /_routes` enumerates every registered route, method, and path — a complete API map for attackers. Neither endpoint has an `ENV` guard or authentication.
- **Impact:** Database fingerprinting; full attack-surface enumeration.
- **Fix approach:** Guard both endpoints with an `if os.getenv("ENV") == "development":` block, or delete them entirely before production deployment.

---

## High Priority

### 6. CRUD user endpoints are fully unauthenticated and admin-capable

- **Files:** `db/routers/users.py`, `main.py` line 64
- **Issue:** `GET /users` returns a paginated list of all user records (up to 500 at once). `POST /users` creates a user. `PATCH /users/{id}` updates any user. `DELETE /users/{id}` deletes any user. None of these endpoints require a token or an admin role.
- **Impact:** Any caller can enumerate, modify, or delete user accounts.
- **Fix approach:** Either remove the `/users` router from production registration, or add `dependencies=[Depends(auth)]` with an admin-claim check.

### 7. `/account` router is imported and wired but never registered

- **Files:** `main.py` lines 6 and 54, `api/account.py`
- **Issue:** `from api import account` is imported at the top. Line 54 shows the correct `app.include_router(account.router, dependencies=[Depends(auth)])` call — but it is commented out. The account deletion endpoint (`DELETE /account/me`) is therefore unreachable even though it was fully implemented. Users cannot delete their own accounts despite the feature existing.
- **Impact:** Feature regression; GDPR right-to-erasure cannot be exercised by users.
- **Fix approach:** Uncomment line 54. Because `api/account.py` already uses `Depends(auth)` per-route, the `dependencies=` kwarg at router registration is redundant but harmless.

### 8. No input length limits on `user_query` fields

- **Files:** `models/schemas.py` line 7, `api/chat.py` lines 154, 222
- **Issue:** `ChatRequest.user_query` is declared as `str` with no `Field(max_length=...)` constraint. A caller can send arbitrarily large text (megabytes) which will be passed verbatim into Pinecone embedding calls, the LLM context window, and stored in Redis. The same issue applies to `ReferenceRequest.user_query` and `ElaborationRequest.selected_text`/`context_text`.
- **Impact:** Cost amplification (very long inputs consume disproportionate token budget); potential DoS by overwhelming embedding/LLM APIs with huge payloads; Redis memory pressure.
- **Fix approach:** Add `Field(max_length=4000)` (or a similar limit matching the embedding model's context) to all free-text query fields in `models/schemas.py`.

### 9. No rate limiting on any endpoint

- **Files:** `main.py`, all `api/` routers
- **Issue:** There is no rate-limiting middleware, no per-IP throttling, and no per-user request quota. `slowapi` or equivalent is absent from `requirements.txt`.
- **Impact:** A single caller can exhaust OpenAI and Pinecone quotas, spike Redis connections, and deny service to other users. Combined with the lack of authentication on primary routes (concern #1), this is effectively an open DoS vector.
- **Fix approach:** Add `slowapi` to `requirements.txt` and apply a rate limiter to at minimum the `/chat/stream/agentic` endpoint. Per-IP limits (e.g., 20 req/min) are a starting point.

### 10. Synchronous LLM call (`chain.stream()`) blocks the async event loop

- **Files:** `core/pipeline_langgraph.py` lines 158–169, `modules/generation/stream_generator.py` line 36
- **Issue:** Inside `response_generator()` — an `async def` function running on the uvicorn event loop — `chain.stream(...)` is called synchronously with a `for` loop. This is a blocking call that occupies the event loop thread for the entire LLM generation duration (potentially many seconds), preventing all other concurrent requests from being served.
- **Impact:** Under any meaningful concurrent load, users experience request queuing and elevated latency. With multiple users active simultaneously, the server effectively becomes single-threaded.
- **Fix approach:** Replace with `await chain.astream(...)` using `async for chunk in chain.astream(...)`. LangChain's `RunnableSequence` supports async streaming. The same applies to `stream_generator.py`.

```python
# core/pipeline_langgraph.py — current (blocks event loop):
for chunk in chain.stream({...}):
    yield sse_event("response_chunk", {"token": token})

# Correct:
async for chunk in chain.astream({...}):
    yield sse_event("response_chunk", {"token": token})
```

---

## Medium Priority

### 11. `MemorySaver` grows unbounded in-process memory per session

- **Files:** `agents/core/chat_agent.py` lines 53–54
- **Issue:** `ChatAgent.__init__` instantiates a `MemorySaver()` checkpointer (LangGraph's in-memory store) on every `ChatAgent` construction. A new `ChatAgent` is created on every request (see `core/pipeline_langgraph.py` lines 63–64). Each `MemorySaver` stores all graph state snapshots in a Python dict keyed by `thread_id`. Because the object is local to a single request invocation, no state actually persists across requests — but if the pattern were ever changed to a module-level singleton (a natural optimization), all checkpoints would accumulate indefinitely with no eviction.
- **Additionally:** The `thread_id` passed to `compiled_graph.invoke()` is the raw `session_id` from the client. With no TTL or cleanup, state accumulates for as long as the process runs.
- **Impact:** Memory leak risk if the per-request instantiation pattern changes; architectural friction preventing the natural optimization of sharing a compiled graph.
- **Fix approach:** Instantiate `ChatAgent` once at module level (or use a proper persistent checkpointer like `AsyncSqliteSaver` or `RedisSaver`), and add TTL-based eviction.

### 12. `translate_response_tool` is a registered but non-functional stub

- **Files:** `agents/tools/translation_tools.py` lines 57–104
- **Issue:** The tool is fully wired into the agent's tool list (its docstring advertises "translate English text to the user's preferred language"), but its implementation always returns the original English text with a `"note": "Response translation not yet implemented, returning English"` field. The `TODO` comment on line 92 confirms this. If the agent calls this tool for a non-English user, they silently receive an English response with no error surfaced to the client.
- **Impact:** Multilingual support is broken without any user-facing indication. Agent spends tokens on a tool call that has no effect.
- **Fix approach:** Either implement `translator.translate_from_english(text, target_language)` in `modules/translation/`, or remove `translate_response_tool` from the agent's tool list until it is implemented.

### 13. `account.py` logs full JWT claims at INFO level

- **Files:** `api/account.py` line 60
- **Issue:** `logger.info(f"JWT Claims for user {user_id}: {credentials.claims}")` dumps the complete decoded JWT payload (which may include email, phone, groups, and other identity fields) to application logs on every account deletion request. A comment on lines 98–100 shows this was added for debugging and was never removed.
- **Impact:** PII in log aggregation systems (CloudWatch, Datadog, etc.); potential compliance issue.
- **Fix approach:** Remove line 60. The user_id is already logged on line 57.

### 14. Dual pipeline paths create maintenance ambiguity

- **Files:** `core/pipeline.py` (legacy), `core/pipeline_langgraph.py` (active), `api/chat.py`
- **Issue:** Both `POST /chat/` and `POST /chat/stream` still use `core/pipeline.py` (the non-agentic legacy pipeline). Only `/chat/stream/agentic` and `/chat/agentic` use the LangGraph pipeline. This means two separate retrieval and generation code paths are maintained, with divergent behavior and different memory handling.
- **Impact:** Bug fixes or prompt changes made in one pipeline are not reflected in the other. Tests for the legacy pipeline may give false confidence. Newcomers are unclear which path is canonical.
- **Fix approach:** Migrate `/chat/` and `/chat/stream` to the LangGraph pipeline and deprecate `core/pipeline.py`, or explicitly document that `POST /chat/` and `POST /chat/stream` are legacy endpoints with a sunset date.

### 15. DB routers for lessons, progress, and hikmah-trees are unauthenticated

- **Files:** `db/routers/lessons.py`, `db/routers/lesson_content.py`, `db/routers/user_progress.py`, `db/routers/hikmah_trees.py`, `main.py` lines 65–68
- **Issue:** These CRUD routers are registered with no `dependencies=[Depends(auth)]`. Lesson content, user progress records, and hikmah tree data are fully readable and writable by unauthenticated callers.
- **Fix approach:** Add `dependencies=[Depends(auth)]` at registration, or use per-route guards for read-only vs. write operations.

---

## Low Priority / Nice-to-Have

### 16. No linter or formatter configured

- **Files:** Repository root (no `.flake8`, `pyproject.toml`, `ruff.toml`, or `.pre-commit-config.yaml` found)
- **Issue:** There is no `ruff`, `flake8`, `black`, or `isort` configuration. Code style is enforced only by convention. `requirements.txt` does not include any linting tool.
- **Impact:** Inconsistent formatting accumulates over time; no automated gate to catch common errors before commit.
- **Fix approach:** Add `ruff` (covers linting + formatting) to `requirements.txt` and a `ruff.toml` or `[tool.ruff]` section in `pyproject.toml`. Add a pre-commit hook.

### 17. `api/account.py` Cognito username fallback is fragile

- **Files:** `api/account.py` lines 88–96
- **Issue:** The Cognito deletion call attempts to derive the username by checking four different JWT claim fields in order (`cognito:username`, `username`, `email`, `preferred_username`). The guard that raises `ValueError` for a missing username is commented out (lines 98–100). If none of the four fields is present, `cognito_username` will be `None`, and `admin_delete_user` will be called with `Username=None` — likely raising an unhandled `ClientError` that is silently swallowed.
- **Impact:** Account deletion may complete for the database and Redis but silently skip the Cognito deletion, leaving a dangling identity provider entry.
- **Fix approach:** Uncomment the guard on lines 98–100 and raise a proper `HTTPException(400)` if the username cannot be determined.

### 18. Pinecone and OpenAI clients initialized at module import time

- **Files:** `core/vectorstore.py`, `modules/generation/stream_generator.py` line 13
- **Issue:** External service clients are created as module-level globals when Python imports the module. If `OPENAI_API_KEY` or `PINECONE_API_KEY` is absent (e.g., in a test environment), the import itself will fail or silently produce a broken client.
- **Impact:** Complicates unit testing; any test that imports these modules requires all credentials to be set.
- **Fix approach:** Use lazy initialization (create client on first use) or dependency injection, and rely on mock fixtures in tests.

### 19. SSE error event exposes raw exception message

- **Files:** `core/pipeline_langgraph.py` line 220
- **Issue:** On pipeline exception, `yield sse_event("error", {"message": str(e)})` sends the raw Python exception string to the SSE stream. This is a client-visible information leak analogous to concern #4, but specifically in the streaming path.
- **Fix approach:** Replace with a generic message like `"An error occurred. Please try again."` and rely on server-side logging for the actual exception.

---

## Positive Notes

- **Auth infrastructure is correctly built.** `models/JWTBearer.py` and `core/auth.py` implement proper AWS Cognito JWKS validation. The code is sound; it simply needs to be re-enabled at the router level.
- **`/chat/saved` and `/chat/saved/{id}` are correctly guarded.** The saved-chat retrieval endpoints use `Depends(auth)` and call `_require_user_id()`, serving as the correct template for all other endpoints.
- **Exception handling in route handlers is generally safe.** `api/chat.py` catches exceptions and raises `HTTPException(500, "Internal Server Error")` without leaking details — the right pattern. The global middleware (concern #4) is the outlier.
- **Pydantic validation on quiz schemas is thorough.** `models/schemas.py` uses `model_validator` to enforce quiz choice constraints, demonstrating the team knows how to use Pydantic's validation features — the same approach should be extended to `user_query` length limits.
- **Alembic migrations are used.** Schema changes are tracked with 6 versioned migration files, reducing the risk of schema drift.
- **Memory service has TTL configuration.** Redis TTL (`REDIS_TTL_SECONDS`) and max-message cap (`REDIS_MAX_MESSAGES`) are configurable via environment variables, showing awareness of memory management concerns even if some in-process patterns (concern #11) still need work.
