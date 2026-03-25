# Phase 1: Data Foundation - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Ingest Sistani's "Islamic Laws" (4th edition) PDF into two dedicated Pinecone fiqh indexes (dense + sparse), producing a fully searchable fiqh knowledge base. Output is a populated index pair with structured metadata per chunk — nothing else is in scope. No retrieval logic, no query-time code, no integration with the agentic pipeline.

</domain>

<decisions>
## Implementation Decisions

### PDF Source & Parsing
- **D-01:** The PDF is committed in the repository. Researcher to locate the exact file path.
- **D-02:** Ruling numbers follow the format `"Ruling 1"`, `"Ruling 2"`, etc. The chunking regex anchors on this prefix: `Ruling\s+\d+`. Ruling-number boundaries are the primary split points (per INGE-02); paragraph boundaries are secondary.

### Sparse Encoder
- **D-03:** Use `pinecone-text` BM25Encoder for sparse embeddings (per INGE-05, INGE-06). This differs from the existing `modules/embedding/embedder.py` which uses TF-IDF fitted at query-time. The fiqh ingestion pipeline uses BM25 and persists the fitted encoder to disk for consistent query-time encoding in Phase 2.
- **D-04:** TF-IDF (existing embedder) is NOT used for the fiqh indexes. Do not reuse `getSparseEmbedder()` from `modules/embedding/embedder.py` for fiqh.

### Pinecone Indexes
- **D-05:** Dense index env var: `DEEN_FIQH_DENSE_INDEX_NAME` (value: `deen-fiqh-dense`). Already added to `.env`.
- **D-06:** Sparse index env var: `DEEN_FIQH_SPARSE_INDEX_NAME` (value: `deen-fiqh-sparse`). Already added to `.env`.
- **D-07:** Dense index config: 768 dimensions, cosine metric, serverless. Matches `sentence-transformers/all-mpnet-base-v2` output dimensions.
- **D-08:** Sparse index config: Sparse type, dotproduct metric, serverless. No fixed dimension (BM25 vectors are variable-length).
- **D-09:** Both indexes use the same cloud/region as the existing `DEEN_DENSE_INDEX_NAME` and `DEEN_SPARSE_INDEX_NAME` indexes.

### Ingestion Script
- **D-10:** Script lives in `scripts/ingest_fiqh.py` — consistent with existing scripts in `scripts/`.
- **D-11:** Re-runnable with Pinecone upsert semantics. Re-running is safe if chunking strategy or metadata changes mid-process. Indexes do not need to be cleared manually between runs.
- **D-12:** Progress reporting: batch-level logs, e.g. `"Uploaded 200/1400 chunks"`. Not per-chunk verbose. Not summary-only.

### Document ID & Metadata
- **D-13:** Each chunk's Pinecone vector ID must be derived from ruling number + chunk index (not `hadith_id` — that key is specific to the existing hadith pipeline). Downstream retrieval and reranking for fiqh must use a different ID field.
- **D-14:** Required metadata per chunk (INGE-03): `source_book`, `chapter`, `section`, `ruling_number`, `topic_tags` (e.g. tahara, salah, sawm, hajj, khums).

### Claude's Discretion
- Exact chunk overlap strategy (e.g. zero overlap vs. N-token overlap between adjacent chunks)
- Batch size for Pinecone upsert calls
- Filename/path where the fitted BM25 encoder is persisted (e.g. `data/fiqh_bm25_encoder.pkl`)
- Whether to include a dry-run mode that prints detected ruling numbers without uploading

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Data Ingestion — INGE-01 through INGE-06 define all acceptance criteria for this phase

### Existing embedding patterns (read before writing new embedding code)
- `modules/embedding/embedder.py` — existing TF-IDF sparse embedder; fiqh pipeline does NOT reuse this, but the dense embedder (`getDenseEmbedder`) IS reused for dense embedding
- `modules/retrieval/retriever.py` — shows how existing indexes are queried; fiqh retrieval (Phase 2) must follow the same pattern with fiqh-specific index names

### Existing ingestion scripts (reference for style/structure)
- `scripts/generate_primers.py` — example of a standalone script that uses the project's config/env pattern

### Config pattern
- `core/config.py` — env var loading pattern; new `DEEN_FIQH_DENSE_INDEX_NAME` and `DEEN_FIQH_SPARSE_INDEX_NAME` vars must be added here

</canonical_refs>

<deferred>
## Deferred Ideas

None raised during discussion.

## Reviewed Todos

None pending at time of discussion.
</deferred>
