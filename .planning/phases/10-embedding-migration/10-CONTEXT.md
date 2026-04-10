# Phase 10: Embedding Migration - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Swap the pgvector embedding provider from OpenAI `text-embedding-3-small` (1536-dim) to HuggingFace `all-mpnet-base-v2` (768-dim) across `services/embedding_service.py`, `db/models/embeddings.py`, the Alembic migration chain, and the backfill script. Also remove the `VOYAGE_API_KEY` startup guard from `core/config.py` (added in Phase 8 but now obsolete) and update `EMBEDDING_MODEL`/`EMBEDDING_DIMENSIONS` defaults to reflect HuggingFace. Pinecone retrieval embeddings (`modules/embedding/embedder.py`) are **not touched** — they already use HuggingFace and are unaffected.

**Provider decision overrides REQUIREMENTS.md:** EMBED-01..05 still say Voyage AI — the planner must update REQUIREMENTS.md and ROADMAP.md Phase 10 entries to reflect HuggingFace/768-dim as part of this phase.

</domain>

<decisions>
## Implementation Decisions

### Embedding Provider (EMBED-01, EMBED-02)

- **D-01:** `services/embedding_service.py` uses **HuggingFace `all-mpnet-base-v2`**, 768-dimensional. Voyage AI is dropped entirely — no `voyageai.Client`, no `VOYAGE_API_KEY` dependency.
- **D-02:** `EmbeddingService` **reuses** the already-loaded `getDenseEmbedder()` from `modules.embedding.embedder` — avoids loading the 400MB model a second time. `generate_embedding(text)` calls `embedder.embed_query(text)`; `generate_embeddings_batch(texts)` calls `embedder.embed_documents(texts)`. The `self.client = OpenAI(...)` instantiation in `__init__` is removed.

### Config Cleanup (CONF-01 guard update)

- **D-03:** The Phase 8 startup guard `if not ANTHROPIC_API_KEY or not VOYAGE_API_KEY or not PINECONE_API_KEY` is updated to remove `VOYAGE_API_KEY` — new guard: `if not ANTHROPIC_API_KEY or not PINECONE_API_KEY`. HuggingFace requires no API key.
- **D-04:** `EMBEDDING_MODEL` default updated from `"voyage-4"` → `"sentence-transformers/all-mpnet-base-v2"`. `EMBEDDING_DIMENSIONS` default updated from `"1024"` → `"768"`.
- **D-05:** `VOYAGE_API_KEY` removed from `core/config.py` (the `os.getenv("VOYAGE_API_KEY")` line) and from `.env.example`. The `voyageai` package stays in `requirements.txt` for now — Phase 11 handles package cleanup.

### DB Models (EMBED-04)

- **D-06:** `db/models/embeddings.py` module-level constant updated: `EMBEDDING_DIMENSIONS = 1536` → `EMBEDDING_DIMENSIONS = 768`. Both `NoteEmbedding` and `LessonChunkEmbedding` use this constant for their `Vector(EMBEDDING_DIMENSIONS)` columns.

### Alembic Migration (EMBED-05)

- **D-07:** Migration strategy: **DROP + recreate** (not add-column swap). No production rows worth preserving — backfill script regenerates all embeddings. Migration steps:
  1. Drop HNSW indexes on both tables
  2. `DROP TABLE lesson_chunk_embeddings` (FK child first)
  3. `DROP TABLE note_embeddings`
  4. Recreate both tables with `Vector(768)` columns
  5. Recreate HNSW indexes
  - Migration revision chains from `embeddings_001` (the existing 1536-dim migration).

### Backfill Script (EMBED-03)

- **D-08:** `scripts/migrate_embeddings.py` is **renamed** to `scripts/reembed_pgvector.py` and updated to use the new `EmbeddingService` (which now uses HuggingFace). The existing script logic (process lessons + user note profiles, batch commit, stats reporting) is preserved — only the underlying embedding call changes. A git `mv` is used so history is traceable.

### Claude's Discretion

- Whether `EMBEDDING_MODEL` env var is still read by `EmbeddingService` after the swap (it could be hardcoded to `"sentence-transformers/all-mpnet-base-v2"` since the model is not configurable via env without code changes anyway, or kept for symmetry). Claude decides.
- Exact revision ID and description string for the new Alembic migration file.
- Whether the `CHUNK_SIZE` and `CHUNK_OVERLAP` constants in `db/models/embeddings.py` need updating (they're token-based; `all-mpnet-base-v2` uses wordpiece tokenization, 512-token max — current 256/50 values are conservative and fine as-is).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Files Being Modified
- `services/embedding_service.py` — Primary target: swap OpenAI client for HuggingFace embedder (D-01, D-02)
- `db/models/embeddings.py` — `EMBEDDING_DIMENSIONS` constant update (D-06)
- `core/config.py` — Guard update + default updates (D-03, D-04, D-05)
- `.env.example` — Remove `VOYAGE_API_KEY` entry (D-05)
- `scripts/migrate_embeddings.py` → `scripts/reembed_pgvector.py` — Rename + update (D-08)

### New File
- `alembic/versions/<timestamp>_resize_embedding_vectors_768.py` — Drop+recreate migration (D-07)

### Reference Implementations
- `modules/embedding/embedder.py` — `getDenseEmbedder()` returns the shared `HuggingFaceEmbeddings` instance; D-02 imports from here
- `alembic/versions/20260122_create_embedding_tables.py` — Existing 1536-dim migration; new migration chains from `embeddings_001`
- `.planning/phases/08-config-dependencies/08-CONTEXT.md` — Shows the guard pattern added in Phase 8 (D-03 reverts part of it)

### Phase Requirements (need updating)
- `.planning/REQUIREMENTS.md` §Embedding Migration (EMBED-01..05) — Planner must update these to say HuggingFace/768-dim before creating plans
- `.planning/ROADMAP.md` Phase 10 section — Goal and success criteria still say Voyage AI/1024-dim; planner updates these too

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `modules/embedding/embedder.py` `getDenseEmbedder()` — Returns `HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")` loaded at module level. D-02 imports this directly.
- `scripts/migrate_embeddings.py` — Existing backfill script with full lesson + note migration logic; renamed and updated (not rewritten from scratch).

### Established Patterns
- `EmbeddingService.__init__(self, db: Session)` — Currently instantiates `self.client = OpenAI(...)`. After D-02, this line is replaced with `self.embedder = getDenseEmbedder()`.
- `generate_embedding(text)` → `self.client.embeddings.create(...)` — Replaced with `self.embedder.embed_query(text)`.
- `generate_embeddings_batch(texts)` → `self.client.embeddings.create(input=texts)` — Replaced with `self.embedder.embed_documents(texts)`.
- `HuggingFaceEmbeddings` interface: `.embed_query(text: str) -> List[float]`, `.embed_documents(texts: List[str]) -> List[List[float]]` — drop-in for current signatures.

### Integration Points
- `services/memory_service.py` and `services/consolidation_service.py` call `EmbeddingService` — interface unchanged (same method signatures), so no changes needed there.
- `alembic/versions/20260122_create_embedding_tables.py` revision `embeddings_001` — new migration sets `down_revision = 'embeddings_001'`.
- `core/config.py` `OPENAI_API_KEY` import in `services/embedding_service.py` — removed (replaced by embedder import).

</code_context>

<specifics>
## Specific Ideas

- D-02: `from modules.embedding.embedder import getDenseEmbedder` at top of `embedding_service.py`; `self.embedder = getDenseEmbedder()` in `__init__`.
- D-07: Migration drops `lesson_chunk_embeddings` before `note_embeddings` (FK constraint ordering).
- D-08: Use `git mv scripts/migrate_embeddings.py scripts/reembed_pgvector.py` in the plan step so git tracks it as a rename.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-embedding-migration*
*Context gathered: 2026-04-10*
