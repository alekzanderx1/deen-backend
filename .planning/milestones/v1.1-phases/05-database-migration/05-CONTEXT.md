# Phase 5: Database Migration - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 provisions a fresh Supabase Postgres project, applies all 13 SQLAlchemy tables via `alembic upgrade head`, and points the running app at it via env vars only. **No application code changes.** The phase succeeds when the existing app boots against Supabase, `GET /_debug/db` returns 200, and pgvector-backed embedding tables are functional.

Out of scope for this phase (deferred to Phase 6 / 7):
- Auth/JWT changes (Phase 6)
- Removing Cognito or boto3 (Phase 6 / 7)
- Building any async engine
- Data migration from RDS (none — fresh start)

</domain>

<decisions>
## Implementation Decisions

### pgvector Enablement
- **D-01:** pgvector is enabled by the existing alembic migration `alembic/versions/20260122_create_embedding_tables.py:25` which already runs `CREATE EXTENSION IF NOT EXISTS vector`. The Supabase direct connection (port 5432, `postgres` superuser role) has `CREATE` privilege, so this succeeds without any manual dashboard step. `alembic upgrade head` is fully self-contained — no runbook click required.

### Async Database Path
- **D-02:** Stay with the sync engine. No `create_async_engine(...)` is added in Phase 5. Rationale: nothing in the codebase currently calls async DB code; chat-endpoint latency is dominated by OpenAI/Pinecone, not Postgres; FastAPI runs sync deps in a threadpool so the event loop is not blocked; and asyncpg-on-Supabase has multiple silent-failure modes (`ssl=` vs `sslmode=`, `statement_cache_size=0`, `prepared_statement_cache_size=0`, `NullPool`, `jit=off`) that are paper risks until an async engine actually exists.
- **D-02a:** `ASYNC_DATABASE_URL` env var **is** set in `.env` to a valid Supabase asyncpg DSN on port 5432 (`postgresql+asyncpg://postgres:[PWD]@db.[ref].supabase.co:5432/postgres`). This satisfies DB-03 literally. No code reads it at runtime — it is dead plumbing kept warm for a future async path.

### Env Var Strategy
- **D-03:** Use individual `DB_*` env vars (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`). The Supabase DSN is parsed **once** when populating `.env`:
  - `DB_HOST=db.[project-ref].supabase.co`
  - `DB_PORT=5432`
  - `DB_NAME=postgres`
  - `DB_USER=postgres`
  - `DB_PASSWORD=[from Supabase dashboard]`
- **D-03a:** No edits to `db/config.py`, `db/session.py`, or `alembic/env.py`. The existing `Settings` class in `db/config.py` already constructs the URL via `URL.create(...)` from these components. Sync engine + alembic continue to use the existing path unchanged.

### Verification
- **D-04:** Phase 5 verification is the 4 ROADMAP success criteria **plus** one targeted pgvector smoke test. After `alembic upgrade head` completes:
  1. Insert a dummy row into `note_embeddings` with a real 1536-dim vector
  2. Run a cosine-similarity SELECT against the HNSW index (`ORDER BY embedding <=> $1 LIMIT k`)
  3. Confirm the row comes back and the query plan uses the HNSW index, not a sequential scan
  This is the single highest-risk slice (extension install + `pgvector.sqlalchemy.Vector` type resolution + HNSW `vector_cosine_ops` operator class) and the basic `\dt` / `/_debug/db` checks would not catch a silent misconfiguration here.

### Claude's Discretion
- Exact mechanics of the pgvector smoke test (raw SQL via `psql` vs a one-off Python script vs a pytest in `tests/db/`) — pick whichever is cleanest. Document the chosen approach in the plan.
- Whether the smoke test row gets cleaned up after the assertion or left in place — pick one.
- How to display/save the alembic upgrade output for the verification record.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing application code (read before changing anything)
- `db/config.py` — Pydantic Settings class that builds DATABASE_URL from `DB_*` env vars via `URL.create()`. **Do not modify.**
- `db/session.py` — Sync SQLAlchemy engine with `sslmode=require`, `pool_pre_ping=True`. **Do not modify.**
- `alembic/env.py` — Alembic config that imports `Base` from `db.session` and `settings` from `db.config`. **Do not modify.**
- `alembic/versions/20260122_create_embedding_tables.py` §line 25 — `CREATE EXTENSION IF NOT EXISTS vector` is already here. This is the load-bearing line for pgvector enablement.
- `core/config.py` §lines 30-72 — `DATABASE_URL`, `ASYNC_DATABASE_URL`, `build_async_database_url()`. The async URL is dead plumbing per D-02a.

### Prior research (already consumed)
- `.planning/research/PITFALLS.md` — Catalog of asyncpg + Supavisor pitfalls. **Relevant for Phase 5 only as a "do not touch" warning.** Phase 5 explicitly defers all of these by not building an async engine.
- `.planning/research/STACK.md` §"asyncpg" — Confirms `postgresql+asyncpg://...:5432/postgres` is the correct DSN format for Supabase direct connection.
- `.planning/research/FEATURES.md` — Confirms async DB path is currently unused in routers, supporting D-02.
- `.planning/research/ARCHITECTURE.md` §line 34 — Confirms `DB_*` env var names do not change; only `.env` values change.

### External (Supabase docs)
- Supabase project provisioning flow (Dashboard → New Project) — the human step that produces the connection string. No URL pinned because Supabase docs change.
- `db.[project-ref].supabase.co:5432` is the **direct connection** host pattern, not the pooler (`aws-0-[region].pooler.supabase.com:6543`). This distinction is critical.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `db/config.py` `Settings` class — already accepts Supabase credentials with zero modification. The `AliasChoices` on each field even supports `POSTGRES_*` and `PG*` aliases if the operator prefers those.
- `alembic/versions/20260122_create_embedding_tables.py` — already creates the `vector` extension AND the HNSW indexes with `vector_cosine_ops`. Phase 5 just needs to run it against Supabase.
- 7 existing alembic migrations (`alembic/versions/`) — `alembic upgrade head` chains through all of them on a fresh DB.

### Established Patterns
- `db/session.py` uses `connect_args={"sslmode": "require"}` for psycopg2. Supabase requires SSL, so this is already correct.
- `db/config.py` `URL.create(...)` properly URL-escapes credentials, so a Supabase password with special characters will work without manual escaping in `.env`.

### Integration Points
- `.env` — single touch point for Phase 5. `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, plus the literal `ASYNC_DATABASE_URL` per D-02a.
- `GET /_debug/db` (in `main.py`) — the existing health check that hits the sync engine. This is the canonical "the app sees the database" check from criterion 4.

### Constraints from existing architecture
- `db/session.py` engine is module-level and built at import time. Misconfigured `.env` → import error at server boot. Mitigation: verify `alembic upgrade head` and a manual `python -c "from db.session import engine; engine.connect()"` before starting uvicorn.

</code_context>

<specifics>
## Specific Ideas

- The pgvector smoke test should assert the query uses the HNSW index, not just that it returns a row. Sequential scan would still return the row but would silently mean the index is broken. `EXPLAIN` output should mention `Index Scan using idx_note_embeddings_vector` or equivalent.
- The fresh Supabase project should be created in a region close to the existing app deployment to minimize round-trip latency. Region selection is a manual dashboard step — note it in the runbook output for Phase 7 (CLEAN-02).
- Capture the exact connection string structure the operator received from Supabase in the verification record (with password redacted). This makes Phase 7 documentation easier.

</specifics>

<deferred>
## Deferred Ideas

- **Async engine wiring** (`create_async_engine` + `AsyncSession` + `get_async_db` dependency): deferred indefinitely. Would only be revisited if a profiling hot spot shows DB-bound concurrency as a real bottleneck. At that point, all the asyncpg-on-Supabase pitfalls in `.planning/research/PITFALLS.md` apply.
- **Switch to single `DATABASE_URL` env var**: deferred. Cosmetic improvement only; current `DB_*` components work fine and require zero code change.
- **Row Level Security (RLS) policies**: already deferred to a future milestone per REQUIREMENTS.md SUPA-01. App operates as `postgres` superuser which bypasses RLS regardless.
- **Session pooler / IPv4 fallback**: already deferred per REQUIREMENTS.md SUPA-04. Revisit only if direct-connection IPv6 is unreachable from the deploy environment.
- **Schema permission grants**: out of scope per REQUIREMENTS.md (cosmetic only when running as superuser).
- **Removing `ASYNC_DATABASE_URL` entirely**: rejected — DB-03 explicitly names it as a deliverable. Keep set, just don't read it.

</deferred>

---

*Phase: 05-database-migration*
*Context gathered: 2026-04-06*
</content>
</invoke>