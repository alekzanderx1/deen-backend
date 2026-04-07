# Phase 5: Database Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Refer to `05-CONTEXT.md` for the actionable decisions.

**Date:** 2026-04-06
**Mode:** discuss (interactive)
**Phase:** 5 — Database Migration

---

## Gray Areas Presented

User selected all four:
1. pgvector enablement
2. Async engine SSL fix
3. Env var strategy
4. Verification depth

---

## Q1 — pgvector enablement

**Question:** How should pgvector get enabled on the new Supabase project?

**Options presented:**
- Dashboard toggle pre-alembic
- Let alembic do it
- Both — dashboard + new explicit migration

**User clarification:** Asked what the dashboard route would look like in practice and how the migration route accomplishes the same thing.

**Claude clarification:** Walked through the dashboard flow (Database → Extensions → toggle `vector`) and showed the migration line `op.execute('CREATE EXTENSION IF NOT EXISTS vector')` at `alembic/versions/20260122_create_embedding_tables.py:25`. Explained the only meaningful difference is which schema vector lives in (`extensions` vs `public`) and whether `alembic upgrade head` is fully self-contained.

**User selection:** "If we can reproduce from code alone, I would prefer that."

**Decision recorded:** D-01 — let the existing migration enable pgvector. No dashboard step.

---

## Q2 — Async engine SSL fix

**Question:** What should Phase 5 do about the async (asyncpg) database path?

**Options presented:**
- Leave it alone
- Add async engine + correct connect_args now
- Remove ASYNC_DATABASE_URL entirely

**User clarification:** Asked what an async engine actually is and what's currently in the code vs missing.

**Claude clarification:** Explained sync vs async SQLAlchemy engines, walked through the actual state: `core/config.py` exposes `FINAL_ASYNC_DATABASE_URL` but no code calls `create_async_engine(...)`. `db/session.py` only builds the sync engine. The only consumer of the async URL is `agent_tests/test_db_connection.py`. The asyncpg pitfalls (`ssl=`, `statement_cache_size=0`, `NullPool`) only matter once an async engine actually exists.

**User follow-up:** "So is async setup good or is it better to stay with what we have already?"

**Claude recommendation:** Stay with sync. Reasons given: DB is not the bottleneck (OpenAI/Pinecone latency dominates), FastAPI runs sync deps in a threadpool so the event loop is not blocked, async-on-Supabase has multiple silent-failure modes, and there's zero current consumer. Suggested keeping `ASYNC_DATABASE_URL` set as dead plumbing to satisfy DB-03 literally.

**User selection:** "Yup, do that, keep it set"

**Decision recorded:** D-02 / D-02a — sync engine only; `ASYNC_DATABASE_URL` env var stays set, unread by code.

---

## Q3 — Env var strategy

**Question:** How should the Supabase connection string be plumbed into the app?

**Options presented:**
- Keep `DB_*` components, no code change (Recommended)
- Switch to full `DATABASE_URL`
- Support both — prefer `DATABASE_URL` if set

**User selection:** Keep `DB_*` components, no code change.

**Decision recorded:** D-03 / D-03a — parse Supabase DSN into 5 components when populating `.env`; no edits to `db/config.py`, `db/session.py`, or `alembic/env.py`.

---

## Q4 — Verification depth

**Question:** How thorough should Phase 5's verification be?

**Options presented:**
- Roadmap criteria + pgvector smoke test (Recommended)
- Just the 4 roadmap criteria
- Full smoke test of every table

**User selection:** Roadmap criteria + pgvector smoke test.

**Decision recorded:** D-04 — execute 4 ROADMAP criteria plus a targeted pgvector insert + HNSW cosine query, asserting the query plan uses the HNSW index.

---

## Wrap-up

**Question:** Ready to write CONTEXT.md?
**User selection:** Write context.

**Output:** `.planning/phases/05-database-migration/05-CONTEXT.md`

---
</content>
</invoke>
