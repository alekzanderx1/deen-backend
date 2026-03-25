# Phase 2: Routing and Retrieval - Research

**Researched:** 2026-03-23
**Domain:** LLM-based classification, query decomposition, hybrid Pinecone retrieval, RRF merging
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Classifier Architecture**
- D-01: New `modules/fiqh/classifier.py` — do NOT modify existing `modules/classification/classifier.py`. The hadith pipeline calls `classifier.py` and must remain untouched.
- D-02: The new classifier returns one of exactly 6 category strings: `VALID_OBVIOUS`, `VALID_SMALL`, `VALID_LARGE`, `VALID_REASONER`, `OUT_OF_SCOPE_FIQH`, `UNETHICAL` (per CLAS-01).
- D-03: Uses gpt-4o-mini (small LLM) per CLAS-04.
- D-04: `OUT_OF_SCOPE_FIQH` and `UNETHICAL` both produce a rejection response before any retrieval runs (per CLAS-02, CLAS-03).

**ChatState**
- D-05: Add `fiqh_category: str` field to `agents/state/chat_state.py` alongside the existing `is_fiqh: bool`. Do NOT remove `is_fiqh` — it is still used by existing routing logic. Phase 4 migrates routing to `fiqh_category`.

**Code Organization**
- D-06: All new fiqh pipeline code lives in `modules/fiqh/` package:
  - `modules/fiqh/__init__.py`
  - `modules/fiqh/classifier.py` — 6-category classification
  - `modules/fiqh/decomposer.py` — query decomposition into sub-queries
  - `modules/fiqh/retriever.py` — hybrid dense+sparse retrieval with inline RRF merge
- D-07: Existing `modules/classification/`, `modules/retrieval/`, `modules/reranking/` directories are NOT modified.

**Query Decomposition**
- D-08: `decompose_query(query: str) -> list[str]` returns 1-4 semantically independent, keyword-rich sub-queries (per QPRO-01, QPRO-02). Uses gpt-4o-mini (per QPRO-03).
- D-09: Sub-queries should include domain-specific fiqh terminology (Arabic/Persian transliterated terms) where appropriate.

**Hybrid Retrieval and RRF**
- D-10: For each sub-query, perform hybrid retrieval: dense search against `DEEN_FIQH_DENSE_INDEX_NAME` and sparse search against `DEEN_FIQH_SPARSE_INDEX_NAME` (per RETR-01).
- D-11: Dense embedding uses `getDenseEmbedder()` from `modules/embedding/embedder.py` — same embedder as Phase 1 ingestion (NOT OpenAI text-embedding, uses all-mpnet-base-v2).
- D-12: Sparse encoding uses BM25Encoder loaded from `data/fiqh_bm25_encoder.json` — the encoder persisted by Phase 1 ingestion script. NOT TF-IDF (`getSparseEmbedder()` from existing embedder).
- D-13: RRF merge (k=60) is implemented inline in `modules/fiqh/retriever.py` — do NOT use or extend `modules/reranking/reranker.py` (wrong algorithm, keyed on `hadith_id`). RRF score = `1/(60 + rank_dense) + 1/(60 + rank_sparse)` (per RETR-02).
- D-14: Top-5 docs per sub-query retained after RRF (per RETR-03). Retrieved docs include source metadata: book, chapter, section, ruling_number (per RETR-04).
- D-15: Vector IDs in the fiqh index use `ruling_number` + chunk index format (from Phase 1 D-13) — NOT `hadith_id`.

**Sub-query Retrieval Contract**
- D-16: `retrieve_fiqh_documents(query: str) -> list[dict]` is the public interface. Internally it decomposes the query, retrieves top-5 per sub-query, deduplicates by chunk ID, and returns a flat list of up to ~20 unique docs. Phase 3 receives a single evidence pool.
- D-17: Each doc in the returned list has shape: `{"chunk_id": str, "metadata": dict, "page_content": str}`.

### Claude's Discretion
- Exact prompt templates for the 6-category classifier and decomposer
- Maximum doc count in the final flat list (suggested: 20, deduplicated by chunk_id)
- How the decomposer handles single-part queries (returns list of length 1)
- Namespace used for Pinecone fiqh index queries (use `ns1` consistent with Phase 1 ingestion)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLAS-01 | System classifies queries into exactly one of 6 categories: VALID_OBVIOUS, VALID_SMALL, VALID_LARGE, VALID_REASONER, OUT_OF_SCOPE_FIQH, UNETHICAL | Existing `classify_fiqh_query()` in `modules/classification/classifier.py` shows the LangChain prompt → invoke → parse pattern; new classifier follows same pattern but returns string, not bool |
| CLAS-02 | OUT_OF_SCOPE_FIQH queries are politely rejected before any retrieval occurs | Rejection logic is a simple branch on return value of `classify_fiqh_query()` before entering retrieval; same pattern as existing binary classifier |
| CLAS-03 | UNETHICAL queries are immediately rejected | Same rejection branch — different message tone (firm vs. polite) |
| CLAS-04 | Classification uses gpt-4o-mini | `chat_models.get_classifier_model()` already provides gpt-4o-mini; new classifier reuses this function |
| CLAS-05 | Negative rejection accuracy >95% | Satisfied by prompt engineering and a 50+ labeled query evaluation test; test harness needed in `tests/test_fiqh_classifier.py` |
| QPRO-01 | Complex fiqh queries decomposed into 1-4 semantically independent, keyword-rich sub-queries | New `decompose_query()` using gpt-4o-mini with structured JSON output |
| QPRO-02 | Sub-queries include domain-specific fiqh terminology | Enforced via decomposer prompt instructions |
| QPRO-03 | Query decomposition uses gpt-4o-mini | `get_classifier_model()` reused |
| RETR-01 | Hybrid retrieval (dense + sparse) from dedicated fiqh Pinecone indexes | Both `deen-fiqh-dense` and `deen-fiqh-sparse` confirmed populated with 3000 vectors |
| RETR-02 | Dense and sparse results merged using RRF (k=60) | Inline RRF in `modules/fiqh/retriever.py` — confirmed existing reranker uses wrong algorithm (weighted score addition) and wrong key (`hadith_id`) |
| RETR-03 | Top-5 documents per sub-query after RRF | Slice `sorted_rrf[:5]` after RRF sort |
| RETR-04 | Retrieved documents include source metadata (book, chapter, section, ruling number) | Phase 1 upserted metadata keys: `text_en`, `source_book`, `chapter`, `section`, `ruling_number`, `topic_tags` — all present in Pinecone |
</phase_requirements>

---

## Summary

Phase 2 builds three independently testable modules inside a new `modules/fiqh/` package. The work is primarily prompt-engineering and Pinecone query wiring — no new Python dependencies are required beyond what Phase 1 already pinned. All three modules (classifier, decomposer, retriever) follow patterns already established in the codebase (`modules/classification/classifier.py` for LLM calls, `modules/retrieval/retriever.py` for Pinecone queries).

The critical implementation constraint is BM25 encoding for sparse queries. The existing `getSparseEmbedder()` returns a TF-IDF vectorizer that is **not** fit on the fiqh corpus and cannot produce valid sparse vectors for the fiqh index. The correct path is to load `BM25Encoder` from `data/fiqh_bm25_encoder.json` (confirmed present and reloadable — produces valid `{indices, values}` dicts) and call `.encode_queries()`. This is already proven in Phase 1.

For RRF merging, the existing `reranker.py` must not be used: it is keyed on `hadith_id`, uses weighted-score-addition (not RRF), and does normalization math that is entirely incompatible with the fiqh index's `ruling_number`-based IDs. The inline RRF implementation is a short, well-understood algorithm: for each document, sum `1/(60 + rank_dense) + 1/(60 + rank_sparse)` across the two result lists, then sort descending.

**Primary recommendation:** Write `modules/fiqh/` as three thin functions — `classify_fiqh_query()`, `decompose_query()`, `retrieve_fiqh_documents()` — each independently testable with mocks. The entire phase is a code-only deliverable; no schema migrations, no new dependencies, no new environment variables.

---

## Standard Stack

### Core (all already in requirements.txt)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pinecone` | 7.3.0 | Dense and sparse index queries | Already used by existing retrieval layer |
| `pinecone-text` | 0.11.0 | `BM25Encoder.load()` and `.encode_queries()` | Same encoder used for Phase 1 ingestion — mandatory for query-time consistency |
| `langchain-openai` | 0.3.25 | LLM calls via `init_chat_model` | Existing pattern in `chat_models.py` |
| `sentence-transformers` | 3.4.1 | `HuggingFaceEmbeddings` (all-mpnet-base-v2) | Must use same embedding model as ingestion |
| `pytest` | 8.4.1 | Unit testing | Project standard |
| `pytest-asyncio` | 0.26.0 | Async test support | Project standard |

**No new dependencies required.** All libraries are already pinned in `requirements.txt`.

### Key Functions (already available, no import changes needed)

| Import | From | What It Provides |
|--------|------|-----------------|
| `get_classifier_model()` | `core.chat_models` | gpt-4o-mini LangChain model |
| `getDenseEmbedder()` | `modules.embedding.embedder` | all-mpnet-base-v2 HuggingFaceEmbeddings |
| `_get_vectorstore(index_name)` | `core.vectorstore` | `PineconeVectorStore` for dense similarity_search |
| `_get_sparse_vectorstore(index_name)` | `core.vectorstore` | Raw `pinecone.Index` for sparse + direct queries |
| `DEEN_FIQH_DENSE_INDEX_NAME` | `core.config` | `"deen-fiqh-dense"` |
| `DEEN_FIQH_SPARSE_INDEX_NAME` | `core.config` | `"deen-fiqh-sparse"` |
| `BM25Encoder` | `pinecone_text.sparse` | Sparse encoder; `.load()` from `data/fiqh_bm25_encoder.json` |

---

## Architecture Patterns

### Recommended Project Structure

```
modules/fiqh/
├── __init__.py          # empty or re-exports public API
├── classifier.py        # classify_fiqh_query(query) -> str (6 categories)
├── decomposer.py        # decompose_query(query) -> list[str]
└── retriever.py         # retrieve_fiqh_documents(query) -> list[dict]
                         # internally: decompose → per-sub-query hybrid → RRF → dedup
```

### Pattern 1: 6-Category LLM Classifier

**What:** Single LLM call returning one of 6 exact strings. Parse the raw string content; no JSON needed.

**When to use:** All incoming fiqh queries before decomposition or retrieval.

**Pattern (follows existing `modules/classification/classifier.py` exactly):**
```python
# modules/fiqh/classifier.py
from core import chat_models
from langchain.prompts import ChatPromptTemplate

VALID_CATEGORIES = {
    "VALID_OBVIOUS", "VALID_SMALL", "VALID_LARGE",
    "VALID_REASONER", "OUT_OF_SCOPE_FIQH", "UNETHICAL"
}

SYSTEM_PROMPT = """..."""  # 6-category instructions with examples

_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{query}")
])

def classify_fiqh_query(query: str) -> str:
    """Returns one of 6 category strings. Never raises — returns OUT_OF_SCOPE_FIQH on error."""
    model = chat_models.get_classifier_model()
    response = model.invoke(_prompt.format_messages(query=query))
    category = response.content.strip().upper()
    if category not in VALID_CATEGORIES:
        return "OUT_OF_SCOPE_FIQH"  # safe fallback on unexpected output
    return category
```

**Key insight on prompt engineering:** Provide 2-3 examples per category. For `VALID_SMALL` vs. `VALID_LARGE`, distinguish by whether the answer requires multiple rulings and cross-referencing. For `VALID_REASONER`, distinguish queries that require procedural reasoning (e.g., "how many rakats do I owe if..."). For `UNETHICAL`, keep examples focused on clearly harmful requests, not borderline Islamic topics.

### Pattern 2: Query Decomposer with JSON Output

**What:** LLM call that returns a JSON array of 1-4 sub-query strings. Parse with `json.loads()`.

**When to use:** After a VALID_* classification, before retrieval.

```python
# modules/fiqh/decomposer.py
import json
from core import chat_models
from langchain.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """You decompose a user's fiqh question into 1-4 independent, keyword-rich
sub-queries for retrieval from Ayatollah Sistani's "Islamic Laws" (4th edition).

Rules:
- Return ONLY a JSON array of strings: ["sub-query 1", "sub-query 2"]
- Simple questions → list of length 1 (the original query, enriched with terminology)
- Complex multi-part questions → 2-4 independent sub-queries
- Each sub-query MUST include relevant Arabic/Persian fiqh terminology in transliteration
  (e.g., wudu, ghusl, salah, tahara, najis, halal, haram, khums, zakat, nikah, talaq, iddah)
- Sub-queries must be self-contained for standalone retrieval
- Do NOT include overlap between sub-queries

Examples:
Q: "Is my wudu broken if I sleep?"
A: ["wudu validity sleep nullifier istinja"]

Q: "Can I pray with wet socks and do I need to remove my ring for wudu?"
A: ["khuffayn wet socks prayer validity wudu", "ring jewelry obstruction wudu ghusl ruling"]
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Query: {query}")
])

def decompose_query(query: str) -> list[str]:
    """Returns 1-4 sub-queries. Falls back to [query] on parse error."""
    model = chat_models.get_classifier_model()
    response = model.invoke(_prompt.format_messages(query=query))
    try:
        sub_queries = json.loads(response.content.strip())
        if not isinstance(sub_queries, list) or not sub_queries:
            return [query]
        return [str(q) for q in sub_queries[:4]]  # cap at 4
    except (json.JSONDecodeError, ValueError):
        return [query]  # safe fallback
```

### Pattern 3: Hybrid Retrieval with Inline RRF

**What:** Dense + sparse Pinecone query per sub-query, merged with RRF (k=60), top-5 retained.

**Critical distinction from existing retriever.py:**
- Uses `BM25Encoder.encode_queries()` (NOT `generate_sparse_embedding()` which calls TF-IDF)
- Keys results by `chunk_id` (NOT `hadith_id`)
- Uses RRF score formula (NOT weighted score addition)
- The sparse Pinecone index for fiqh is a **sparse-only** index — query must provide `sparse_vector`, NOT `vector`

**Important: `_get_vectorstore` text_key mismatch.** The existing `_get_vectorstore()` is hardcoded with `text_key="text_en"`. The fiqh index uses the same key (`text_en` is stored in metadata per Phase 1 ingest at line 359 of `ingest_fiqh.py`). This means `_get_vectorstore(DEEN_FIQH_DENSE_INDEX_NAME)` can be reused for dense search and `.similarity_search_with_score(query, k=20)` will return `Document` objects with `page_content` populated correctly.

```python
# modules/fiqh/retriever.py — core RRF logic
from pinecone_text.sparse import BM25Encoder
from core.vectorstore import _get_vectorstore, _get_sparse_vectorstore
from core.config import DEEN_FIQH_DENSE_INDEX_NAME, DEEN_FIQH_SPARSE_INDEX_NAME
from modules.embedding.embedder import getDenseEmbedder
from modules.fiqh.decomposer import decompose_query
import logging
import traceback

logger = logging.getLogger(__name__)

BM25_ENCODER_PATH = "data/fiqh_bm25_encoder.json"

# Module-level BM25 encoder (loaded once at import time)
_bm25_encoder: BM25Encoder | None = None

def _get_bm25_encoder() -> BM25Encoder:
    global _bm25_encoder
    if _bm25_encoder is None:
        enc = BM25Encoder()
        enc.load(BM25_ENCODER_PATH)
        _bm25_encoder = enc
    return _bm25_encoder


def _rrf_merge(
    dense_results: list,       # list of (Document, score) tuples from PineconeVectorStore
    sparse_matches: list,      # list of Pinecone match objects (have .id, .metadata)
    k: int = 60,
    top_n: int = 5,
) -> list[dict]:
    """Merge dense and sparse results using Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    metadata_store: dict[str, dict] = {}
    content_store: dict[str, str] = {}

    # Dense pass — rank by position in similarity_search_with_score list (already sorted desc)
    for rank, (doc, _score) in enumerate(dense_results):
        chunk_id = doc.metadata.get("id") or doc.id  # Pinecone doc id
        # Note: PineconeVectorStore does not expose vector id cleanly on the doc object.
        # Use metadata approach described in Architecture Notes below.
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
        metadata_store[chunk_id] = doc.metadata
        content_store[chunk_id] = doc.page_content

    # Sparse pass
    for rank, match in enumerate(sparse_matches):
        md = getattr(match, "metadata", {}) or {}
        chunk_id = match.id
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
        if chunk_id not in metadata_store:
            metadata_store[chunk_id] = md
        if chunk_id not in content_store:
            content_store[chunk_id] = md.get("text_en", "")

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)[:top_n]
    return [
        {
            "chunk_id": cid,
            "metadata": metadata_store[cid],
            "page_content": content_store[cid],
        }
        for cid in sorted_ids
    ]


def _retrieve_for_sub_query(sub_query: str) -> list[dict]:
    """Dense + sparse retrieval + RRF for a single sub-query. Returns top-5."""
    try:
        # Dense
        dense_store = _get_vectorstore(DEEN_FIQH_DENSE_INDEX_NAME)
        dense_results = dense_store.similarity_search_with_score(sub_query, k=20)

        # Sparse
        encoder = _get_bm25_encoder()
        sparse_vec = encoder.encode_queries(sub_query)  # {"indices": [...], "values": [...]}
        sparse_index = _get_sparse_vectorstore(DEEN_FIQH_SPARSE_INDEX_NAME)
        sparse_response = sparse_index.query(
            top_k=20,
            include_metadata=True,
            sparse_vector=sparse_vec,
            namespace="ns1",
        )
        sparse_matches = sparse_response.matches if hasattr(sparse_response, "matches") else \
                         sparse_response.get("matches", [])

        return _rrf_merge(dense_results, sparse_matches, k=60, top_n=5)
    except Exception as e:
        logger.error("[FIQH_RETRIEVER] sub-query retrieval error: %s\n%s", e, traceback.format_exc())
        return []


def retrieve_fiqh_documents(query: str) -> list[dict]:
    """
    Public interface for Phase 3.
    Decomposes query, retrieves top-5 per sub-query, deduplicates by chunk_id.
    Returns up to 20 unique docs.
    """
    sub_queries = decompose_query(query)
    seen: set[str] = set()
    result: list[dict] = []
    for sq in sub_queries:
        for doc in _retrieve_for_sub_query(sq):
            if doc["chunk_id"] not in seen:
                seen.add(doc["chunk_id"])
                result.append(doc)
    return result[:20]
```

### Architecture Note: Chunk ID in Dense Results

`PineconeVectorStore.similarity_search_with_score()` returns `(Document, float)` tuples. The `Document.metadata` dict contains all fields upserted at ingestion time — which in Phase 1 does NOT include `id` as a metadata key. The vector ID (e.g., `"ruling_0712_chunk0"`) is the Pinecone record's primary key and is **not** automatically placed in `doc.metadata`.

**Two options for getting chunk_id from dense results:**

1. **Use raw index query instead of PineconeVectorStore** — call `pc.Index(DEEN_FIQH_DENSE_INDEX_NAME).query(vector=..., top_k=20, include_metadata=True, namespace="ns1")` which returns match objects with `.id`. This is the cleanest approach and mirrors the existing `retrieve_quran_documents()` pattern already in `modules/retrieval/retriever.py` (line 96-103).

2. **Use `similarity_search_with_score` and extract id from `doc.id`** — `LangChain Document` objects from Pinecone do carry `.id` when the underlying LangChain-Pinecone integration sets it, but this is integration-version-dependent.

**Recommendation (use option 1 — raw index query):** Use the same pattern as `retrieve_quran_documents()` for dense search. Call `embedder.getDenseEmbedder().embed_query(sub_query)` to get the dense vector, then query the index directly. This guarantees `.id` access on match objects and is already proven in this codebase.

```python
# Dense query using raw index (like retrieve_quran_documents):
query_vec = getDenseEmbedder().embed_query(sub_query)
dense_index = _get_sparse_vectorstore(DEEN_FIQH_DENSE_INDEX_NAME)  # raw index
dense_response = dense_index.query(
    vector=query_vec,
    top_k=20,
    include_metadata=True,
    namespace="ns1",
)
dense_matches = dense_response.matches
```

This approach means `_rrf_merge` receives two uniform lists of Pinecone match objects (each with `.id`, `.metadata`, `.score`) — simpler than the mixed `(Document, float)` + match-object handling.

### Pattern 4: ChatState Extension

**What:** Add a single optional field to `ChatState` TypedDict.

**Where:** `agents/state/chat_state.py`

```python
# Add after is_fiqh field (line 51 of current chat_state.py):
fiqh_category: str
"""6-category fiqh classification result ('', VALID_OBVIOUS, VALID_SMALL,
VALID_LARGE, VALID_REASONER, OUT_OF_SCOPE_FIQH, UNETHICAL)"""
```

**And in `create_initial_state()`, add:**
```python
fiqh_category="",   # default empty string; populated by Phase 4 routing node
```

### Anti-Patterns to Avoid

- **Using `getSparseEmbedder()` for fiqh sparse queries:** This returns an unfitted TF-IDF vectorizer. It calls `fit_transform([query])` on a single query, producing indices that are meaningless against the BM25-encoded fiqh sparse index. This will silently return incorrect results.
- **Using `reranker.rerank_documents()` for fiqh:** The reranker looks for `hadith_id` in metadata. Fiqh chunks use `ruling_number` as their ID. Every doc will be silently dropped by the `if not hadith_id: continue` guard.
- **Calling `encoder.encode_queries()` before `.load()`:** BM25Encoder must be loaded from disk first. Module-level lazy initialization (load once on first call) is the right pattern.
- **Raising exceptions from retrieval functions:** Follow the existing tool error pattern — catch all exceptions, log them, return `[]` or `{"error": str(e), ...}`. Keeps Phase 3's evidence assessment loop alive even on retrieval failure.
- **Hard-coding the BM25 encoder path:** Use `Path(__file__).parent.parent.parent / "data" / "fiqh_bm25_encoder.json"` or resolve from project root via `sys.path`, not a literal string. This makes the module work from any working directory.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sparse BM25 encoding at query time | Custom BM25 implementation | `BM25Encoder.load() + .encode_queries()` from `pinecone-text==0.11.0` | The encoder must match ingestion-time vocabulary exactly; any reimplementation will produce different indices |
| Dense vector embedding | New embedding model or OpenAI embeddings | `getDenseEmbedder().embed_query()` (all-mpnet-base-v2) | Must be the same model used at ingestion; dimension mismatch (768 for all-mpnet-base-v2 vs 1536 for text-embedding-3-small) will cause Pinecone query errors |
| RRF merge with normalization | Weighted-score addition | Pure RRF: `1/(k + rank)` sum, no normalization | RRF is a rank-based fusion — scores across different retrieval systems are incomparable; normalization breaks RRF semantics |
| JSON output parsing from LLM | Regex or brittle string splitting | `json.loads()` with `list` type check + fallback | LLMs occasionally output trailing text or markdown fences; a `try/except json.JSONDecodeError` with fallback to `[query]` is safer |

---

## Common Pitfalls

### Pitfall 1: BM25 Encoder Path Resolution Fails at Runtime

**What goes wrong:** `enc.load("data/fiqh_bm25_encoder.json")` works when `cwd` is the project root but fails when tests or the server is started from a different directory.

**Why it happens:** Relative path resolution depends on the process working directory, which differs between `pytest` runs and `uvicorn` startup.

**How to avoid:** Resolve path relative to the module file:
```python
from pathlib import Path
BM25_ENCODER_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "fiqh_bm25_encoder.json"
```

**Warning signs:** `FileNotFoundError` on `enc.load()` in CI or when tests run from a non-root directory.

### Pitfall 2: Sparse Index Queried with `vector=` Instead of `sparse_vector=`

**What goes wrong:** The fiqh sparse index (`deen-fiqh-sparse`) is a `vector_type="sparse"` Pinecone index (created without a dimension parameter). Querying it with a dense `vector=` argument raises a Pinecone API error.

**Why it happens:** Pinecone has separate index types for dense and sparse. The sparse index only accepts `sparse_vector={"indices": [...], "values": [...]}` in the query call.

**How to avoid:** Always use `sparse_vector=sparse_vec` (not `vector=`) when querying the sparse fiqh index.

**Warning signs:** `PineconeApiException` with a 400 status on `index.query()`.

### Pitfall 3: LLM Returns Extra Text Around JSON (Decomposer)

**What goes wrong:** gpt-4o-mini occasionally wraps JSON in markdown fences (` ```json\n[...]\n``` `) or adds a preamble like "Here are the sub-queries:".

**Why it happens:** Chat models are trained to be helpful and sometimes add formatting even when instructed not to.

**How to avoid:** Strip markdown fences before `json.loads()`:
```python
content = response.content.strip()
if content.startswith("```"):
    content = content.split("```")[1]
    if content.startswith("json"):
        content = content[4:]
```
Or simply catch `json.JSONDecodeError` and fall back to `[query]`.

**Warning signs:** `json.JSONDecodeError` on valid-looking responses containing markdown.

### Pitfall 4: Classifier Returns a Category String With Surrounding Whitespace or Lowercase

**What goes wrong:** `response.content.strip()` may return `"valid_obvious"` (lowercase) or `" VALID_OBVIOUS "` (with spaces), causing the membership check against `VALID_CATEGORIES` to fail.

**Why it happens:** LLMs don't always respect casing instructions perfectly.

**How to avoid:** Normalize before checking: `category = response.content.strip().upper()`.

**Warning signs:** Frequent fallback to `"OUT_OF_SCOPE_FIQH"` in tests; category membership check always False.

### Pitfall 5: Dense and Sparse Results Have Different ID Formats

**What goes wrong:** If dense results are pulled via `PineconeVectorStore.similarity_search_with_score()`, the `Document` object does not reliably expose the Pinecone vector ID. The RRF merge then cannot de-duplicate correctly because it cannot identify which dense doc corresponds to which sparse match.

**Why it happens:** LangChain's `PineconeVectorStore` returns `langchain_core.documents.Document` objects; the vector ID is not always placed in `.metadata`.

**How to avoid:** Use raw `pc.Index().query(vector=..., ...)` for dense search, not `PineconeVectorStore`. This returns Pinecone match objects with `.id` populated. The pattern is already used in `retrieve_quran_documents()` in `modules/retrieval/retriever.py` (lines 96–103).

### Pitfall 6: BM25 Encoder Loaded at Every Function Call

**What goes wrong:** Loading the BM25 encoder JSON (which can be several MB) on every query call adds significant latency.

**Why it happens:** No caching of the encoder object.

**How to avoid:** Use module-level lazy initialization (load once on first call, cache in `_bm25_encoder` global within the module). This is safe for single-process deployments and the existing server architecture.

### Pitfall 7: ChatState fiqh_category Field Missing from create_initial_state()

**What goes wrong:** `TypedDict` fields added to the class declaration but not initialized in `create_initial_state()` will cause `KeyError` when any code accesses `state["fiqh_category"]`.

**Why it happens:** `TypedDict` does not enforce presence of keys at runtime — the error only surfaces on access.

**How to avoid:** Whenever a field is added to `ChatState`, immediately add its default value to `create_initial_state()`.

---

## Code Examples

### BM25 Encoder Load and Query-Time Encode
```python
# Source: pinecone-text==0.11.0 (verified via venv — BM25 reload confirmed OK)
from pinecone_text.sparse import BM25Encoder
from pathlib import Path

_BM25_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "fiqh_bm25_encoder.json"
_encoder: BM25Encoder | None = None

def _get_encoder() -> BM25Encoder:
    global _encoder
    if _encoder is None:
        enc = BM25Encoder()
        enc.load(str(_BM25_PATH))
        _encoder = enc
    return _encoder

# Usage at query time:
sparse_vec = _get_encoder().encode_queries("wudu sleep nullifier ruling")
# Returns: {"indices": [int, ...], "values": [float, ...]}
```

### Raw Pinecone Dense Query (mirrors retrieve_quran_documents pattern)
```python
# Source: modules/retrieval/retriever.py lines 92-103 (existing pattern, verified)
from core.vectorstore import _get_sparse_vectorstore  # raw index
from modules.embedding.embedder import getDenseEmbedder
from core.config import DEEN_FIQH_DENSE_INDEX_NAME

query_vec = getDenseEmbedder().embed_query(sub_query)
dense_index = _get_sparse_vectorstore(DEEN_FIQH_DENSE_INDEX_NAME)
dense_response = dense_index.query(
    vector=query_vec,
    top_k=20,
    include_metadata=True,
    namespace="ns1",
)
# dense_response.matches: list of ScoredVector with .id, .score, .metadata
```

### Sparse Index Query
```python
# Source: modules/retrieval/retriever.py lines 24-30 (existing pattern for DEEN_SPARSE_INDEX_NAME)
sparse_index = _get_sparse_vectorstore(DEEN_FIQH_SPARSE_INDEX_NAME)
sparse_response = sparse_index.query(
    top_k=20,
    include_metadata=True,
    sparse_vector=sparse_vec,  # {"indices": [...], "values": [...]}
    namespace="ns1",
)
# sparse_response.matches: same ScoredVector structure
```

### RRF Merge (minimal canonical implementation)
```python
# Standard RRF formula — no external dependency
def rrf_merge(
    dense_matches: list,
    sparse_matches: list,
    k: int = 60,
    top_n: int = 5,
) -> list[dict]:
    scores: dict[str, float] = {}
    store: dict[str, tuple[dict, str]] = {}  # chunk_id -> (metadata, page_content)

    for rank, m in enumerate(dense_matches):
        cid = m.id
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        store[cid] = (m.metadata or {}, (m.metadata or {}).get("text_en", ""))

    for rank, m in enumerate(sparse_matches):
        cid = m.id
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        if cid not in store:
            store[cid] = (m.metadata or {}, (m.metadata or {}).get("text_en", ""))

    top = sorted(scores, key=lambda x: scores[x], reverse=True)[:top_n]
    return [{"chunk_id": cid, "metadata": store[cid][0], "page_content": store[cid][1]} for cid in top]
```

### Classifier Pattern (follows existing modules/classification/classifier.py)
```python
# Source: modules/classification/classifier.py (existing verified pattern)
from core import chat_models
from langchain.prompts import ChatPromptTemplate

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{query}"),
])

def classify_fiqh_query(query: str) -> str:
    model = chat_models.get_classifier_model()  # gpt-4o-mini via SMALL_LLM env var
    response = model.invoke(_PROMPT.format_messages(query=query))
    category = response.content.strip().upper()
    return category if category in VALID_CATEGORIES else "OUT_OF_SCOPE_FIQH"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Binary fiqh classifier (true/false) | 6-category classifier | Phase 2 | Enables differentiated routing in Phase 4 (VALID_OBVIOUS may bypass RAG; VALID_LARGE implies full iteration budget) |
| TF-IDF sparse embedding (existing pipeline) | BM25 sparse encoding (fiqh pipeline) | Phase 1/2 | BM25 is vocabulary-consistent across ingestion and query time; TF-IDF requires refitting per query which destroys index-query alignment |
| Weighted-score fusion (existing reranker) | RRF rank-based fusion | Phase 2 | RRF is score-scale-independent; weighted fusion breaks when dense cosine similarity and sparse dot-product scores are on different scales |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `pinecone-text` BM25Encoder | Sparse fiqh encoding | Yes | 0.11.0 | None — required |
| `deen-fiqh-dense` Pinecone index | Dense retrieval | Yes | 3000 vectors in ns1 | None — Phase 1 prerequisite |
| `deen-fiqh-sparse` Pinecone index | Sparse retrieval | Yes | 3000 vectors in ns1 | None — Phase 1 prerequisite |
| `data/fiqh_bm25_encoder.json` | BM25 query encoding | Yes | Loadable, produces valid {indices, values} | None — Phase 1 prerequisite |
| `getDenseEmbedder()` (all-mpnet-base-v2) | Dense query embedding | Yes | sentence-transformers 3.4.1 | None — required for consistent embeddings |
| `DEEN_FIQH_DENSE_INDEX_NAME` env var | Config | Yes | "deen-fiqh-dense" | None — already in config.py |
| `DEEN_FIQH_SPARSE_INDEX_NAME` env var | Config | Yes | "deen-fiqh-sparse" | None — already in config.py |

**Missing dependencies with no fallback:** None — all dependencies confirmed available.

**Missing dependencies with fallback:** None.

---

## Open Questions

1. **Classifier prompt: exact category boundary definitions**
   - What we know: Categories are named; VALID_OBVIOUS/SMALL/LARGE/REASONER all map to valid fiqh questions
   - What's unclear: Whether the boundary between VALID_SMALL and VALID_LARGE should be codified as "single ruling vs. multiple rulings" or something else. CLAS-05 requires >95% negative rejection accuracy — the positive category boundaries do not have an explicit accuracy target in REQUIREMENTS.md.
   - Recommendation: Use Claude's Discretion. For the v1 prompt, define VALID_OBVIOUS as "common well-known rulings requiring no multi-step reasoning", VALID_SMALL as "requires 1-3 rulings to answer", VALID_LARGE as "requires 4+ rulings or cross-chapter synthesis", VALID_REASONER as "requires procedural calculation (e.g., inheritance shares, prayer makeup)". The 50+ labeled query set in CLAS-05 will validate this.

2. **Decomposer: single-part query handling**
   - What we know: Declared as Claude's Discretion; returns `list[str]` of length 1
   - What's unclear: Whether the single sub-query should be returned verbatim or enriched with terminology
   - Recommendation: Enrich with terminology even for single-part queries. The prompt should instruct the model to "enrich with relevant fiqh terminology" regardless of length. This improves sparse retrieval hit rate.

3. **Maximum doc count in flat deduplicated list**
   - What we know: Declared as Claude's Discretion; D-16 suggests 20
   - Recommendation: Cap at 20. With 4 sub-queries × 5 docs = 20 max before deduplication; typical unique count will be 10-15. Phase 3 evidence assessment is designed to work with a pool of this size.

---

## Project Constraints (from CLAUDE.md)

These directives apply to all code produced in this phase:

- **Code organization:** All new fiqh code in `modules/fiqh/` — consistent with `modules/` layer responsibility (discrete AI pipeline stages)
- **Naming:** `snake_case` for functions and modules; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants
- **Type hints:** All new functions must carry complete type hints (return types, parameter types)
- **Error handling:** Tool functions catch all exceptions and return error payloads (`{"error": str(e), ...}` or `[]`) — do NOT raise; this keeps LangGraph graph running
- **Logging:** Use `logger.*` (not `print()`) in new code; obtain logger via `logging.getLogger(__name__)`
- **LLM provider:** OpenAI models only — gpt-4o-mini via `get_classifier_model()` for CLAS-04 and QPRO-03
- **Testing:** `pytest` with `pytest-asyncio`; mock-based unit tests in `tests/`; environment-dependent tests in `tests/db/` or `agent_tests/`
- **Imports:** Standard library first, then third-party, then local
- **Forbidden:** Modifying `modules/classification/classifier.py`, `modules/retrieval/retriever.py`, `modules/reranking/reranker.py` (D-07)
- **Forbidden:** Removing `is_fiqh` field from `ChatState` (D-05)
- **No new dependencies** — all required libraries already in `requirements.txt`

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `modules/classification/classifier.py` — establishes the exact LLM call pattern to replicate
- Direct code inspection of `modules/retrieval/retriever.py` — establishes the Pinecone query patterns; `retrieve_quran_documents()` is the exact template for raw index dense query
- Direct code inspection of `modules/reranking/reranker.py` — confirms the wrong algorithm (`hadith_id` key, weighted score addition) and validates DO NOT USE directive
- Direct code inspection of `agents/state/chat_state.py` — confirms `is_fiqh: bool` exists and must not be removed; `fiqh_category: str` is the correct addition
- Direct code inspection of `core/vectorstore.py` — confirms `_get_vectorstore()` uses `text_key="text_en"` (matches Phase 1 ingestion metadata key) and `_get_sparse_vectorstore()` returns raw `Pinecone.Index`
- Direct code inspection of `core/config.py` — confirms `DEEN_FIQH_DENSE_INDEX_NAME` and `DEEN_FIQH_SPARSE_INDEX_NAME` are exported without module-level guards
- Pinecone live query: `deen-fiqh-dense` has 3000 vectors in ns1; `deen-fiqh-sparse` has 3000 vectors in ns1 (verified 2026-03-23)
- BM25 encoder reload test: `enc.load('data/fiqh_bm25_encoder.json')` succeeds; `enc.encode_queries('ablution ruling water')` returns `{'indices': [...], 'values': [...]}` with 3 indices (verified 2026-03-23)

### Secondary (MEDIUM confidence)
- Phase 1 VERIFICATION.md — documents chunk metadata schema (7 keys: `text_en`, `source_book`, `chapter`, `section`, `ruling_number`, `topic_tags`, `id` as Pinecone vector ID)
- Phase 1 `ingest_fiqh.py` lines 354-368 — confirms `text_en` is the metadata key for chunk text; `ruling_number` is in metadata (not the vector ID)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in requirements.txt; versions verified from pyproject
- Architecture: HIGH — patterns directly copied from existing working code in this codebase
- Pitfalls: HIGH — identified from direct code inspection of the incompatible existing modules
- BM25/Pinecone integration: HIGH — confirmed via live tests against actual populated indexes

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable stack; Pinecone SDK and pinecone-text are pinned)
