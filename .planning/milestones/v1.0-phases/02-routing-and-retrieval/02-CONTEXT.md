# Phase 2: Routing and Retrieval - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade fiqh query classification from binary to a 6-category system, build query decomposition for complex fiqh queries, and implement hybrid fiqh retrieval with RRF merging. Delivers three independently testable modules in a new `modules/fiqh/` package. No integration with the LangGraph agent yet — that is Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Classifier Architecture
- **D-01:** New `modules/fiqh/classifier.py` — do NOT modify existing `modules/classification/classifier.py`. The hadith pipeline calls `classifier.py` and must remain untouched.
- **D-02:** The new classifier returns one of exactly 6 category strings: `VALID_OBVIOUS`, `VALID_SMALL`, `VALID_LARGE`, `VALID_REASONER`, `OUT_OF_SCOPE_FIQH`, `UNETHICAL` (per CLAS-01).
- **D-03:** Uses gpt-4o-mini (small LLM) per CLAS-04.
- **D-04:** `OUT_OF_SCOPE_FIQH` and `UNETHICAL` both produce a rejection response before any retrieval runs (per CLAS-02, CLAS-03).

### ChatState
- **D-05:** Add `fiqh_category: str` field to `agents/state/chat_state.py` alongside the existing `is_fiqh: bool`. Do NOT remove `is_fiqh` — it is still used by existing routing logic. Phase 4 migrates routing to `fiqh_category`.

### Code Organization
- **D-06:** All new fiqh pipeline code lives in `modules/fiqh/` package:
  - `modules/fiqh/__init__.py`
  - `modules/fiqh/classifier.py` — 6-category classification
  - `modules/fiqh/decomposer.py` — query decomposition into sub-queries
  - `modules/fiqh/retriever.py` — hybrid dense+sparse retrieval with inline RRF merge
- **D-07:** Existing `modules/classification/`, `modules/retrieval/`, `modules/reranking/` directories are NOT modified.

### Query Decomposition
- **D-08:** `decompose_query(query: str) -> list[str]` returns 1-4 semantically independent, keyword-rich sub-queries (per QPRO-01, QPRO-02). Uses gpt-4o-mini (per QPRO-03).
- **D-09:** Sub-queries should include domain-specific fiqh terminology (Arabic/Persian transliterated terms) where appropriate.

### Hybrid Retrieval and RRF
- **D-10:** For each sub-query, perform hybrid retrieval: dense search against `DEEN_FIQH_DENSE_INDEX_NAME` and sparse search against `DEEN_FIQH_SPARSE_INDEX_NAME` (per RETR-01).
- **D-11:** Dense embedding uses `getDenseEmbedder()` from `modules/embedding/embedder.py` — same embedder as Phase 1 ingestion (NOT OpenAI text-embedding, uses all-mpnet-base-v2).
- **D-12:** Sparse encoding uses BM25Encoder loaded from `data/fiqh_bm25_encoder.json` — the encoder persisted by Phase 1 ingestion script. NOT TF-IDF (`getSparseEmbedder()` from existing embedder).
- **D-13:** RRF merge (k=60) is implemented **inline** in `modules/fiqh/retriever.py` — do NOT use or extend `modules/reranking/reranker.py` (wrong algorithm, keyed on `hadith_id`). RRF score = `1/(60 + rank_dense) + 1/(60 + rank_sparse)` (per RETR-02).
- **D-14:** Top-5 docs per sub-query retained after RRF (per RETR-03). Retrieved docs include source metadata: book, chapter, section, ruling_number (per RETR-04).
- **D-15:** Vector IDs in the fiqh index use `ruling_number` + chunk index format (from Phase 1 D-13) — NOT `hadith_id`.

### Sub-query Retrieval Contract
- **D-16:** `retrieve_fiqh_documents(query: str) -> list[dict]` is the public interface. Internally it decomposes the query, retrieves top-5 per sub-query, deduplicates by chunk ID, and returns a flat list of up to ~20 unique docs. Phase 3 receives a single evidence pool.
- **D-17:** Each doc in the returned list has shape: `{"chunk_id": str, "metadata": dict, "page_content": str}`.

### Claude's Discretion
- Exact prompt templates for the 6-category classifier and decomposer
- Maximum doc count in the final flat list (suggested: 20, deduplicated by chunk_id)
- How the decomposer handles single-part queries (returns list of length 1)
- Namespace used for Pinecone fiqh index queries (use `ns1` consistent with Phase 1 ingestion)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Query Classification (CLAS-01 to CLAS-05) — 6-category classifier acceptance criteria
- `.planning/REQUIREMENTS.md` §Query Processing (QPRO-01 to QPRO-03) — decomposition acceptance criteria
- `.planning/REQUIREMENTS.md` §Retrieval (RETR-01 to RETR-04) — hybrid retrieval and RRF acceptance criteria

### Existing Code (read before writing — reuse or avoid as noted)
- `modules/classification/classifier.py` — existing binary classifier; DO NOT MODIFY; read to understand existing pattern only
- `modules/embedding/embedder.py` — `getDenseEmbedder()` IS reused for dense fiqh query embedding; `getSparseEmbedder()` is TF-IDF and must NOT be used for fiqh
- `modules/retrieval/retriever.py` — existing Pinecone query pattern; reference for how to call `_get_vectorstore()` and `_get_sparse_vectorstore()`
- `modules/reranking/reranker.py` — DO NOT USE for fiqh; uses wrong algorithm (weighted score addition) and wrong ID field (`hadith_id`)
- `agents/state/chat_state.py` — add `fiqh_category: str` field here

### Phase 1 Artifacts
- `data/fiqh_bm25_encoder.json` — BM25 encoder persisted by Phase 1; reload at query time for sparse fiqh encoding

### Config
- `core/config.py` — `DEEN_FIQH_DENSE_INDEX_NAME` and `DEEN_FIQH_SPARSE_INDEX_NAME` env vars already added in Phase 1

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `modules/embedding/embedder.py` → `getDenseEmbedder()`: Returns the all-mpnet-base-v2 sentence-transformer; call `.embed_query(text)` for a dense vector
- `core/vectorstore.py` → `_get_vectorstore(index_name)`: Returns a `PineconeVectorStore` for dense similarity search
- `core/vectorstore.py` → `_get_sparse_vectorstore(index_name)`: Returns raw `Pinecone.Index` for sparse or direct vector queries
- `core/config.py`: All env vars are loaded here; `DEEN_FIQH_DENSE_INDEX_NAME` and `DEEN_FIQH_SPARSE_INDEX_NAME` are already present

### Established Patterns
- Pinecone dense query: `vectorstore.similarity_search_with_score(query, k=N)` via `PineconeVectorStore`
- Pinecone sparse query: `index.query(top_k=N, include_metadata=True, sparse_vector=..., namespace="ns1")`
- LLM calls: `chat_models.get_classifier_model()` for small LLM (gpt-4o-mini); `chat_models.get_agent_model()` for large
- Tool error pattern: Return `{"error": str(e), ...}` instead of raising — keeps the LangGraph graph running

### Integration Points
- `agents/state/chat_state.py` — add `fiqh_category: str` with default `""`
- Phase 4 will import from `modules/fiqh/` and call `retrieve_fiqh_documents()` as a LangGraph tool

</code_context>

<specifics>
## Specific Ideas

No specific references or "I want it like X" moments during discussion — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-routing-and-retrieval*
*Context gathered: 2026-03-23*
