---
phase: 10-embedding-migration
plan: "01"
subsystem: embedding
tags: [embedding, huggingface, config, pgvector, planning-docs]
dependency_graph:
  requires: [09-02-PLAN.md]
  provides: [HuggingFace-backed EmbeddingService, 768-dim pgvector constants, corrected planning docs]
  affects: [services/embedding_service.py, core/config.py, db/models/embeddings.py, .env.example, REQUIREMENTS.md, ROADMAP.md]
tech_stack:
  added: []
  patterns: [getDenseEmbedder() reuse, HuggingFaceEmbeddings.embed_query/embed_documents]
key_files:
  created: []
  modified:
    - services/embedding_service.py
    - core/config.py
    - db/models/embeddings.py
    - .env.example
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
decisions:
  - "D-01/D-02: EmbeddingService reuses getDenseEmbedder() from modules.embedding.embedder — no second model load; 768-dim vectors"
  - "D-03: VOYAGE_API_KEY removed from startup guard; guard now checks ANTHROPIC_API_KEY + PINECONE_API_KEY only"
  - "D-04: EMBEDDING_MODEL default -> sentence-transformers/all-mpnet-base-v2; EMBEDDING_DIMENSIONS default -> 768"
  - "D-05: VOYAGE_API_KEY removed from core/config.py and .env.example"
  - "D-06: db/models/embeddings.py EMBEDDING_DIMENSIONS 1536 -> 768"
metrics:
  duration_seconds: 159
  completed_date: "2026-04-10"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 6
  commits: 3
---

# Phase 10 Plan 01: Swap EmbeddingService to HuggingFace/768-dim Summary

**One-liner:** EmbeddingService now uses HuggingFace all-mpnet-base-v2 via getDenseEmbedder() (768-dim, no API key) replacing OpenAI client; VOYAGE_API_KEY guard removed from startup; planning docs updated to match.

## What Was Built

Three targeted changes that close the gap between Phase 8's Voyage AI assumptions and the actual Phase 10 provider decision (HuggingFace reuse):

1. **EmbeddingService backend swap** — `services/embedding_service.py` now imports `getDenseEmbedder` from `modules.embedding.embedder` instead of `OpenAI`. `__init__` sets `self.embedder = getDenseEmbedder()`; `generate_embedding(text)` calls `embedder.embed_query(text)`; `generate_embeddings_batch(texts)` calls `embedder.embed_documents(texts)`. All downstream methods (`store_note_embedding`, `store_lesson_chunk_embeddings`, `find_similar_notes_to_lesson`, etc.) are unchanged — they call the two generation methods and are unaffected.

2. **Config + model constant cleanup** — `core/config.py` no longer loads `VOYAGE_API_KEY`, no longer checks it in the startup guard, and defaults `EMBEDDING_MODEL` to `sentence-transformers/all-mpnet-base-v2` and `EMBEDDING_DIMENSIONS` to `768`. `db/models/embeddings.py` `EMBEDDING_DIMENSIONS` constant is `768`, so both `Vector(EMBEDDING_DIMENSIONS)` columns are ready for the DROP+recreate migration in plan 10-02. `.env.example` reflects all three changes.

3. **Planning doc alignment** — `REQUIREMENTS.md` EMBED-01..05 now describe HuggingFace/768-dim instead of Voyage AI. Traceability table rows point to the correct plan files. `ROADMAP.md` Phase 10 goal, success criteria, and plans section all describe the HuggingFace/768-dim approach.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Swap EmbeddingService to HuggingFace getDenseEmbedder | 48db73e | services/embedding_service.py |
| 2 | Update config.py defaults + remove VOYAGE_API_KEY guard | 2359f8a | core/config.py, db/models/embeddings.py, .env.example |
| 3 | Update REQUIREMENTS.md and ROADMAP.md to HuggingFace/768-dim | 53659cd | .planning/REQUIREMENTS.md, .planning/ROADMAP.md |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing fix] Remove VOYAGE_API_KEY reference from validate_supabase_config docstring**
- **Found during:** Task 2
- **Issue:** The `validate_supabase_config()` docstring in `core/config.py` referenced `ANTHROPIC_API_KEY/VOYAGE_API_KEY/PINECONE_API_KEY` in its description of the inline guards. After removing `VOYAGE_API_KEY` from the guards, the docstring was stale.
- **Fix:** Updated docstring to `ANTHROPIC_API_KEY/PINECONE_API_KEY` to match the actual guard.
- **Files modified:** core/config.py
- **Commit:** 2359f8a

## Known Stubs

None — all changes are concrete swaps to existing live code paths. The HuggingFace model is already loaded at module import time via `modules/embedding/embedder.py`; no placeholder implementations remain.

## Self-Check: PASSED
