---
phase: 10-embedding-migration
plan: 02
subsystem: database
tags: [alembic, migration, pgvector, embeddings, backfill]
dependency_graph:
  requires: [10-01]
  provides: [EMBED-03, EMBED-05]
  affects: [note_embeddings, lesson_chunk_embeddings, scripts/reembed_pgvector.py]
tech_stack:
  added: []
  patterns: [DROP+recreate migration strategy, git mv rename tracking]
key_files:
  created:
    - alembic/versions/20260410_resize_embedding_vectors_768.py
  modified:
    - scripts/reembed_pgvector.py (renamed from scripts/migrate_embeddings.py via git mv)
decisions:
  - embeddings_002 migration uses DROP+recreate strategy — safe because no production rows exist; backfill script regenerates all
  - downgrade() raises NotImplementedError to prevent silent data loss — explicit rollback instructions provided in error message
  - git mv used for rename to preserve git history (shows as 93% rename, not delete+add)
metrics:
  duration: 77s
  completed: "2026-04-10"
  tasks_completed: 2
  files_changed: 2
---

# Phase 10 Plan 02: DB Migration + Backfill Script Rename Summary

**One-liner:** Alembic embeddings_002 migration drops+recreates both embedding tables with Vector(768), chaining from memory_agent_001; backfill script renamed to reembed_pgvector.py via git mv with updated HuggingFace docstring.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create Alembic migration — DROP + recreate with Vector(768) | 5cd4d27 | alembic/versions/20260410_resize_embedding_vectors_768.py |
| 2 | Rename backfill script via git mv; update docstring/header | a2386cf | scripts/reembed_pgvector.py (renamed from scripts/migrate_embeddings.py) |

## What Was Built

### Task 1: Alembic Migration `embeddings_002`

File: `alembic/versions/20260410_resize_embedding_vectors_768.py`

- Chains from `memory_agent_001` (new alembic head: `embeddings_002`)
- Drops `lesson_chunk_embeddings` first (FK child of `lessons`), then `note_embeddings` — correct FK ordering
- Drops all indexes (HNSW + regular) before dropping tables
- Recreates both tables with `Vector(768)` (HuggingFace all-mpnet-base-v2 dimensions)
- Recreates all regular indexes plus HNSW indexes with identical params (cosine distance, m=16, ef_construction=64)
- `downgrade()` raises `NotImplementedError` — no silent data destruction

### Task 2: Backfill Script Rename

- `scripts/migrate_embeddings.py` renamed to `scripts/reembed_pgvector.py` via `git mv` (git tracks as 93% rename)
- Module docstring updated: references HuggingFace all-mpnet-base-v2, `alembic upgrade head`, and all CLI flags including `--stats-only`
- Log header updated to `"Embedding Backfill Script — HuggingFace all-mpnet-base-v2 (768-dim)"`
- All function logic preserved unchanged (`migrate_lesson_embeddings`, `migrate_user_note_embeddings`, `get_migration_stats`, `main`)
- No direct OpenAI or Voyage AI imports — uses `EmbeddingService` which delegates to HuggingFace internally

## Verification Results

1. `alembic head` → `embeddings_002` (PASS)
2. `grep "Vector(768)\|EMBEDDING_DIMENSIONS = 768"` → line 22, 45, 71 (PASS)
3. `grep "down_revision"` → `'memory_agent_001'` (PASS)
4. `grep "raise NotImplementedError"` → line 99 in `downgrade()` (PASS)
5. `ls scripts/reembed_pgvector.py` → exists; `scripts/migrate_embeddings.py` → does not exist (PASS)
6. `python -c "import ast; ast.parse(...)"` → OK (PASS)
7. `grep "HuggingFace\|768" scripts/reembed_pgvector.py` → docstring line 2, log line 249 (PASS)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — both artifacts are complete and functional.

## Self-Check: PASSED

- alembic/versions/20260410_resize_embedding_vectors_768.py: FOUND
- scripts/reembed_pgvector.py: FOUND
- scripts/migrate_embeddings.py: correctly absent
- commit 5cd4d27: FOUND
- commit a2386cf: FOUND
