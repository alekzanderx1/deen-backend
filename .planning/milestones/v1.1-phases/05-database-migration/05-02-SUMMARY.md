---
plan: 05-02
phase: 05-database-migration
status: complete
completed: 2026-04-06
wave: 2
---

## Summary

Applied all alembic migrations against the freshly-provisioned Supabase project, verified all 13 ORM tables exist, proved the pgvector HNSW index is functional via EXPLAIN, and confirmed the FastAPI app boots against Supabase with `GET /_debug/db` returning HTTP 200.

**Key deviation:** The existing migration chain had no genesis migration — it assumed pre-alembic tables (`users`, `lessons`, `lesson_content`, `user_progress`, `hikmah_trees`) existed in the database already (as they did on the original RDS instance). A genesis migration (`0000_initial_schema.py`, revision `initial_schema_001`) was created to establish these tables before the existing chain runs. `userid_to_string` was updated from `down_revision = None` to `down_revision = 'initial_schema_001'`. All 8 migrations (genesis + 7 original) now run cleanly on a fresh database.

## Alembic Upgrade Output

```
INFO  [alembic.runtime.migration] Running upgrade  -> initial_schema_001, Initial schema — base tables
INFO  [alembic.runtime.migration] Running upgrade initial_schema_001 -> userid_to_string, ...
INFO  [alembic.runtime.migration] Running upgrade userid_to_string -> a12c6d22b9d9, ...
INFO  [alembic.runtime.migration] Running upgrade a12c6d22b9d9 -> baseline_primers_001, ...
INFO  [alembic.runtime.migration] Running upgrade baseline_primers_001 -> personalized_primers_001, ...
INFO  [alembic.runtime.migration] Running upgrade personalized_primers_001 -> embeddings_001, ...
INFO  [alembic.runtime.migration] Running upgrade embeddings_001 -> page_quiz_001, ...
INFO  [alembic.runtime.migration] Running upgrade page_quiz_001 -> chat_history_001, ...
```

Exit code: 0. `alembic current` output: `chat_history_001 (head)`

## Final Table List (14 total)

```
alembic_version
chat_messages
chat_sessions
hikmah_trees
lesson_chunk_embeddings
lesson_content
lesson_page_quiz_attempts
lesson_page_quiz_choices
lesson_page_quiz_questions
lessons
note_embeddings
personalized_primers
user_progress
users
```

(13 ORM tables + alembic_version = 14)

## pgvector EXPLAIN Plan (HNSW Verified)

```
Limit  (cost=2.88..3.55 rows=5 width=24)
  ->  Index Scan using idx_note_embeddings_vector on note_embeddings  (cost=2.88..15.00 rows=90 width=24)
        Order By: (embedding <=> '[0.01,...1536 dims...]'::vector)
```

HNSW index `idx_note_embeddings_vector` used by planner (no `enable_seqscan=OFF` needed — real Index Scan from first attempt). Cosine distance for identical vectors = 0.00e+00.

## `GET /_debug/db` Response

```
HTTP/1.1 200 OK
content-type: application/json

{"ok":true,"version":"PostgreSQL 17.6 on aarch64-unknown-linux-gnu, compiled by gcc (GCC) 15.2.0, 64-bit"}
```

uvicorn log: CLEAN (no errors, no tracebacks, no OperationalError).

## Supabase DSN Structure (for Phase 7 runbook)

```
Host: db.qcxbhxfsdhnjakpkoagx.supabase.co  (direct connection, port 5432)
DB:   postgres
User: postgres
Password: [REDACTED]
DSN:  postgresql+psycopg2://postgres:[REDACTED]@db.qcxbhxfsdhnjakpkoagx.supabase.co:5432/postgres
```

## Application Code Changes

Minimal — only the alembic migration chain was updated:
1. **New:** `alembic/versions/0000_initial_schema.py` — genesis migration creating 5 pre-alembic base tables
2. **Modified:** `alembic/versions/20251008_rename_user_id_to_text.py` — `down_revision = None` → `'initial_schema_001'`

No changes to `db/config.py`, `db/session.py`, `alembic/env.py`, `core/config.py`, or any FastAPI route/service code.

`git status --porcelain` shows zero `.py` modifications outside `alembic/versions/`.
