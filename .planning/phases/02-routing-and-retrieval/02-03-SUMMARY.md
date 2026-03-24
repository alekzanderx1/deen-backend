---
phase: 02-routing-and-retrieval
plan: "03"
subsystem: fiqh-retriever
tags: [retriever, fiqh, pinecone, bm25, rrf, hybrid-search, unit-tests]
dependency_graph:
  requires:
    - modules/fiqh/decomposer.py::decompose_query
    - core/vectorstore.py::_get_sparse_vectorstore
    - core/config.py::DEEN_FIQH_DENSE_INDEX_NAME
    - core/config.py::DEEN_FIQH_SPARSE_INDEX_NAME
    - data/fiqh_bm25_encoder.json
  provides:
    - modules/fiqh/retriever.py::retrieve_fiqh_documents
    - modules/fiqh/retriever.py::_rrf_merge
    - tests/test_fiqh_retriever.py
  affects:
    - Phase 03 evidence assessment (FAIR-RAG iterative loop consumes retrieve_fiqh_documents)
tech_stack:
  added:
    - pinecone-text==0.11.0 (BM25Encoder — already in requirements.txt)
  patterns:
    - _get_sparse_vectorstore() for BOTH dense and sparse raw Pinecone index queries
    - sparse_vector= kwarg for sparse index query (not vector=)
    - Path(__file__).resolve() for encoder path — process-cwd-independent
    - Module-level lazy singleton for BM25Encoder (_bm25_encoder)
    - RRF merge (k=60): score = sum of 1/(k + rank + 1) across dense and sparse rank lists
    - deduplicate-by-chunk_id across sub-queries, return[:20]
    - All errors caught, returns [] on failure — never raises
key_files:
  created:
    - modules/fiqh/retriever.py
    - tests/test_fiqh_retriever.py
  modified: []
key-decisions:
  - "Use _get_sparse_vectorstore() for both dense and sparse index access: raw index query returns match.id (chunk_id) needed for deduplication; PineconeVectorStore does not expose this"
  - "sparse_vector= kwarg for sparse index query: mixing with vector= causes 400 error on sparse-type indexes"
  - "BM25_ENCODER_PATH via Path(__file__).resolve(): ensures path is correct regardless of process cwd (server startup vs test vs ingestion)"
  - "Module-level lazy singleton for BM25Encoder: encoder.load() is expensive, cache after first call"
  - "RRF k=60: standard value from information retrieval literature, same as used in existing reranker"
  - "top_n=5 per sub-query, deduplicated across sub-queries, cap at 20 total: matches plan spec D-17"

patterns-established:
  - "Hybrid retrieval pattern: dense raw index query (vector=) + sparse raw index query (sparse_vector=) + RRF merge"
  - "RRF merge function is pure (no I/O) — tested in isolation without mocking Pinecone"
  - "Integration mocking: patch _get_sparse_vectorstore, getDenseEmbedder, _get_bm25_encoder at the retriever module namespace"

requirements-completed: [RETR-01, RETR-02, RETR-03, RETR-04]

duration: 5min
completed: 2026-03-24
---

# Phase 02 Plan 03: Hybrid Fiqh Retriever with RRF Summary

**Hybrid fiqh retriever using BM25 sparse + dense Pinecone raw index queries merged with Reciprocal Rank Fusion (k=60), returning up to 20 deduplicated docs per query via decomposed sub-queries.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-24T11:02:05Z
- **Completed:** 2026-03-24T11:07:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `retrieve_fiqh_documents(query)` public interface built and exportable — consumes `decompose_query`, issues per-sub-query hybrid retrieval, deduplicates, returns `list[dict]` with `chunk_id`, `metadata`, `page_content`
- `_rrf_merge()` implements pure RRF formula (1/(k+rank+1) summed across dense and sparse lists) with no external dependencies — independently testable
- 10 unit tests covering RRF correctness, doc shape, deduplication, error handling, 20-doc cap, and required metadata fields — all pass with mocked Pinecone

## Task Commits

Each task was committed atomically:

1. **Task 1: Create modules/fiqh/retriever.py with hybrid RRF retrieval** - `cae804e` (feat)
2. **Task 2: Write unit tests for the fiqh retriever** - `39f9802` (test)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `modules/fiqh/retriever.py` - Hybrid fiqh retriever: decompose → dense/sparse Pinecone query → RRF merge → dedup → return up to 20 docs
- `tests/test_fiqh_retriever.py` - 10 unit tests with mocked Pinecone and embedding calls

## Decisions Made

- Used `_get_sparse_vectorstore()` for both dense and sparse index access: the raw Pinecone index returns `match.id` (chunk_id) which is required for deduplication. `_get_vectorstore()` (PineconeVectorStore) does not expose vector IDs on Document objects.
- `sparse_vector=sparse_vec` kwarg for sparse index query: using `vector=` on a sparse-type index causes a Pinecone 400 error.
- `Path(__file__).resolve()` for BM25 encoder path: ensures the path resolves correctly from any working directory (server startup, test runner, ingestion scripts).
- Module-level lazy singleton `_bm25_encoder`: `BM25Encoder().load()` reads and deserializes a JSON file — worth caching after first call.
- `top_n=5` per sub-query, deduplicated, capped at 20 total: matches the plan spec D-17 requirement for Phase 3 consumption.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. The `data/fiqh_bm25_encoder.json` file was generated in Phase 1 (Plan 03) and must be present on disk.

## Next Phase Readiness

- `retrieve_fiqh_documents(query: str) -> list[dict]` is the retrieval foundation Phase 3 evidence assessment consumes
- All 3 `modules/fiqh/` modules (classifier, decomposer, retriever) are importable and tested — 31 unit tests pass
- BM25 encoder lazy-loaded on first real call; requires `data/fiqh_bm25_encoder.json` to be present (generated in Phase 1)
- Phase 3 can immediately call `retrieve_fiqh_documents` and receive structured `{chunk_id, metadata, page_content}` dicts ready for evidence filtering and SEA assessment

---
*Phase: 02-routing-and-retrieval*
*Completed: 2026-03-24*
