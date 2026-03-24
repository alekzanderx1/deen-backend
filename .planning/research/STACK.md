# Technology Stack — Fiqh Agentic RAG (FAIR-RAG Pipeline)

**Project:** Deen Backend — Fiqh Q&A Milestone
**Researched:** 2026-03-23
**Scope:** New libraries/components required. Does not re-document the existing stack (see `.planning/codebase/STACK.md`).

---

## What This File Covers

The existing stack (FastAPI 0.115.8, LangGraph 0.2.64, Pinecone 7.3.0, Redis 6.4.0, PostgreSQL, OpenAI) is already in place. This document covers **only the incremental stack needed for the fiqh pipeline** — i.e., the libraries and patterns that are new, upgraded, or configured differently for FAIR-RAG.

---

## Incremental Stack — New Libraries Required

### PDF Parsing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pymupdf4llm` | `0.0.17` | Extract structured Markdown from "Islamic Laws" PDF | Converts Sistani's PDF into clean Markdown with preserved heading hierarchy and paragraph boundaries — critical for chapter/section metadata extraction during chunking. PyMuPDF is the fastest PDF renderer in Python (C-based), and `pymupdf4llm` adds LLM-optimized output. Produces better structure than `pdfplumber` (which is row/table-oriented) or `pypdf` (which loses formatting). |

**Why not `pdfplumber`:** Optimized for tabular data extraction; produces noisy output for running prose text like legal rulings.

**Why not `pypdf`:** Extracts raw text with no layout awareness; paragraph boundaries are lost, which breaks the chunking strategy.

**Why not `docling`:** IBM's Docling is comprehensive but adds heavy ML dependencies (vision models for PDF layout detection) that are overkill for a clean, single-column English PDF like "Islamic Laws." PyMuPDF handles this PDF class with zero ML overhead.

**Confidence:** MEDIUM. PyMuPDF and pymupdf4llm are well-established as of August 2025. Version 0.0.17 was current at knowledge cutoff — verify latest on PyPI before pinning.

---

### Chunking

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `langchain-text-splitters` | `0.3.9` (already installed) | `RecursiveCharacterTextSplitter` for paragraph-boundary-aware chunking | Already in requirements. Splits on `\n\n` first (paragraph), then `\n` (line), then space — exactly matching the FARSIQA chunking strategy. Target: 300–400 tokens (~1,400–1,600 characters with `chunk_size=1500`, `chunk_overlap=150`). |

**Chunk size rationale from FARSIQA research:** The paper used 378 tokens based on their embedding model architecture. With `all-mpnet-base-v2` (512 token max) and `text-embedding-3-small` (8191 token max), staying at 300–400 tokens preserves full semantic context per chunk without hitting context limits.

**No new library needed.** `langchain-text-splitters` is already pinned and its `RecursiveCharacterTextSplitter` covers this use case completely.

---

### Embedding for Fiqh Index

The existing pipeline uses `sentence-transformers/all-mpnet-base-v2` (via `langchain-huggingface==0.1.2`) for dense embeddings and `TfidfVectorizer` (via `scikit-learn`) for sparse embeddings. **Both can be reused for the fiqh index without modification.**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `sentence-transformers/all-mpnet-base-v2` | loaded via `sentence-transformers==3.4.1` (already installed) | Dense embeddings for fiqh chunks | The existing dense model is already loaded at startup. Reusing it avoids cold-start overhead of a second model. `all-mpnet-base-v2` scores well on semantic similarity benchmarks (BEIR) across domain-general legal/religious text. English-only corpus means no multilingual model is needed. |
| `TfidfVectorizer` (scikit-learn) | `scikit-learn==1.6.1` (already installed) | Sparse embeddings for fiqh chunks | The existing sparse mechanism works for BM25-style keyword matching. Fiqh-specific Arabic terms (`wudu`, `najasah`, `tayammum`) will appear as high-IDF tokens automatically. However, see note below on TF-IDF vs BM25. |

**Important caveat on sparse embeddings:** The existing TF-IDF approach works but requires `fit_transform` on a fixed corpus (the vectorizer must be fitted first). For a static ingestion pipeline (single book, one-time ingest), this is acceptable. At query time, `transform` must be called with the same fitted vectorizer — which means the fitted vectorizer must be persisted (pickled) after ingest and loaded at query time. **This is the same pattern needed for the hadith index; verify the existing pipeline handles vectorizer persistence before ingest.**

**Alternative considered — Pinecone's native BM25:** Pinecone offers a hosted `BM25Encoder` (via `pinecone-text`) that eliminates vectorizer persistence concerns. However, the existing codebase uses Pinecone sparse indexes with TF-IDF vectors already. Changing to `BM25Encoder` would require migrating existing indexes or maintaining two different sparse strategies in one codebase. **Defer this optimization** — TF-IDF is sufficient for the bounded fiqh corpus.

**No new embedding library needed.**

---

### Hybrid Retrieval with RRF

The existing `reranker.py` implements a **weighted score merge** (not RRF). For the fiqh pipeline, the FAIR-RAG and FARSIQA papers use **Reciprocal Rank Fusion (RRF)** with `k=60`. RRF is parameterless and rank-based, making it more robust than weighted score fusion for cross-modal merging.

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Custom RRF implementation | N/A (pure Python, ~20 lines) | Merge dense + sparse results by rank for fiqh retrieval | RRF is a standard formula: `score(d) = Σ 1/(k + rank_i(d))` with `k=60`. No library is needed — `langchain`'s `EnsembleRetriever` wraps RRF but adds unnecessary abstraction layers over the direct Pinecone calls. A standalone function is cleaner, testable in isolation, and consistent with the project's existing module pattern. |

**Why not `langchain.retrievers.EnsembleRetriever`:** It wraps two `BaseRetriever` instances and applies RRF internally, but it requires adapting both dense and sparse Pinecone calls into LangChain retriever interfaces. The existing retriever code calls Pinecone directly; a custom RRF function avoids that refactor. The math is 20 lines — write it directly.

**Why not the existing weighted merge:** Weighted score merge is sensitive to score normalization and score distribution differences between dense cosine similarity scores and sparse BM25 scores. RRF is rank-based and eliminates this problem.

---

### LangGraph Sub-Graph (FAIR-RAG Loop)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `langgraph==0.2.64` (already installed) | existing | FAIR-RAG iterative loop as a LangGraph sub-graph | The existing `ChatAgent` is built on LangGraph's `StateGraph`. LangGraph supports composable sub-graphs — the FAIR-RAG loop (decompose → retrieve → filter → assess → refine → repeat) maps cleanly to a `StateGraph` with a conditional loop back edge. The main agent routes fiqh queries to this sub-graph at the `fiqh_classification` node, replacing the existing early-exit with a sub-graph invocation. |

**Sub-graph integration pattern:** The main graph's `fiqh_classification` node currently exits early with a canned response. The replacement: on `is_fiqh=True`, invoke the fiqh sub-graph as a compiled graph call (LangGraph supports this via `graph.invoke()` returning state). The sub-graph manages its own iteration counter (max 3), SEA verdicts, and accumulated evidence before returning a structured result to the main graph's `generate_response` node.

**No new library needed.** LangGraph 0.2.64 supports sub-graphs. Verify that `StateGraph.compile()` with nested graph invocations is stable in this version — it was in active development as of late 2024.

**Confidence:** MEDIUM. Sub-graph composition in LangGraph was stabilized in 0.2.x but the exact API surface (`.invoke()` vs `.stream()` for nested graphs) should be verified against LangGraph 0.2.64 release notes before implementation.

---

### Dynamic LLM Routing

No new library. This is a configuration pattern using existing `langchain-openai` and OpenAI models.

| Task | Model | Rationale |
|------|-------|-----------|
| Query validation/routing | `gpt-4o-mini` (`SMALL_LLM`) | Simple classification — 3-way category (valid/out-of-scope/unethical). Cheap. |
| Query decomposition | `gpt-4o-mini` (`SMALL_LLM`) | Pattern-based decomposition into sub-queries. Small model handles this well per FARSIQA ablation. |
| Structured Evidence Assessment (SEA) | `gpt-4o-mini` (`SMALL_LLM`) | Checklist-based gap analysis with a structured output format. Small model with structured JSON output is sufficient. |
| Evidence filtering | `gpt-4.1` (`LARGE_LLM`) | Subtle relevance judgments between fiqh topics require stronger reasoning to avoid over-filtering. |
| Query refinement | `gpt-4.1` (`LARGE_LLM`) | Precision task — bad refinement queries waste iterations. Large model's instruction-following is critical here. |
| Faithful answer generation | `gpt-4.1` (`LARGE_LLM`) | Highest-stakes step. Evidence-only grounding with citations. Large model's lower hallucination rate is essential for religious legal content. |

**Cost rationale from FARSIQA Table 6:** Dynamic allocation is 13% cheaper than static large-model usage while achieving 97% negative rejection vs 94%. The incremental cost of using the large model for filtering/refinement/generation is justified by the gain in faithfulness and refusal accuracy.

**env vars:** Reuse existing `LARGE_LLM=gpt-4.1-2025-04-14` and `SMALL_LLM=gpt-4o-mini-2024-07-18`. No new env vars needed for model routing.

---

### Pinecone Index Configuration (Fiqh-Specific)

No new SDK needed. Two new Pinecone indexes must be created (separate from existing hadith/Quran indexes):

| Index | Type | Dimensions | Metric | Namespace |
|-------|------|-----------|--------|-----------|
| `FIQH_DENSE_INDEX_NAME` | Dense | 768 (all-mpnet-base-v2 output) | cosine | `ns1` |
| `FIQH_SPARSE_INDEX_NAME` | Sparse | N/A (TF-IDF vocabulary size) | dotproduct | `ns1` |

**Chunk metadata schema per Pinecone record:**

```python
{
    "chunk_id": "sistani-laws-ch03-p047",   # stable ID for citations
    "text": "...",                            # decompressed chunk text
    "source_book": "Islamic Laws 4th Ed",
    "chapter": "Chapter 3: Najasaat",
    "section": "Types of Najis Things",
    "page_number": 47,                        # PDF page number
    "token_count": 312
}
```

**New env vars needed:**
```
FIQH_DENSE_INDEX_NAME
FIQH_SPARSE_INDEX_NAME
```

---

### Citation and Reference Formatting

No new library. The inline citation pattern `[n]` with a trailing references list is implemented via prompt engineering in the generation step. The `chunk_id` metadata field in each Pinecone record serves as the stable citation anchor.

---

### Ingestion Pipeline (One-Time Script)

The data ingestion (PDF → chunks → embeddings → Pinecone upload) is a one-time offline script, not part of the live API. Required components:

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pymupdf4llm` | `0.0.17` | PDF → structured Markdown | See PDF Parsing section above |
| `langchain-text-splitters` | `0.3.9` (already installed) | Markdown-aware chunking | `MarkdownHeaderTextSplitter` to split on `#` headings first, then `RecursiveCharacterTextSplitter` for token-length control |
| `tiktoken` | `0.9.0` (already installed) | Token counting to enforce 300–400 token budget | Already installed |
| `tqdm` | `4.67.1` (already installed) | Progress bars for batch embedding/upload | Already installed |

**Ingestion sequence:**
1. `pymupdf4llm.to_markdown()` → Markdown string with heading hierarchy
2. `MarkdownHeaderTextSplitter` on `#`, `##`, `###` → sections with chapter/section metadata
3. `RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)` → final chunks at ~300–400 tokens
4. For each chunk: generate dense embedding (all-mpnet-base-v2) + sparse embedding (TF-IDF, fitted on all chunks first)
5. Upload to Pinecone (batched, 100 records/batch)
6. Persist fitted TF-IDF vectorizer to disk (pickle) for query-time use

---

## Summary: What's New vs What's Reused

| Component | New? | Library | Notes |
|-----------|------|---------|-------|
| PDF parsing | NEW | `pymupdf4llm==0.0.17` | Only new pip dependency |
| Chunking | Reuse | `langchain-text-splitters==0.3.9` | Already installed |
| Dense embedding | Reuse | `all-mpnet-base-v2` via `sentence-transformers==3.4.1` | Same model, new index |
| Sparse embedding | Reuse | `TfidfVectorizer` via `scikit-learn==1.6.1` | Vectorizer must be persisted |
| Hybrid RRF | New pattern | Pure Python (~20 lines) | Replace weighted merge for fiqh only |
| FAIR-RAG loop | New graph | `langgraph==0.2.64` | Sub-graph composition |
| Dynamic LLM routing | New pattern | `langchain-openai==0.3.25` | Config change, no new lib |
| Pinecone indexes | New indexes | `pinecone==7.3.0` | 2 new indexes, existing SDK |
| Citation formatting | New prompt | N/A | Prompt engineering only |

**Net new pip dependency: 1** (`pymupdf4llm`)

---

## Installation

```bash
# Only one new package
pip install pymupdf4llm==0.0.17
```

Add to `requirements.txt`:
```
pymupdf4llm==0.0.17
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| PDF parsing | `pymupdf4llm` | `docling` | Adds vision ML models (heavy); overkill for single-column clean PDF |
| PDF parsing | `pymupdf4llm` | `pdfplumber` | Table-optimized; loses paragraph boundaries in prose text |
| PDF parsing | `pymupdf4llm` | `pypdf` | No layout awareness; paragraph structure lost |
| Sparse retrieval | TF-IDF (existing) | Pinecone BM25Encoder | Would require migrating existing sparse indexes; not worth inconsistency |
| RRF fusion | Custom Python | `EnsembleRetriever` | Forces refactor of Pinecone calls into LangChain retriever interface; 20-line formula doesn't need abstraction |
| Embedding model | `all-mpnet-base-v2` (existing) | `text-embedding-3-small` (OpenAI) | OpenAI embeddings add per-token cost for every ingestion and query; existing local model is free at inference time |
| Embedding model | `all-mpnet-base-v2` (existing) | `intfloat/multilingual-e5-large` | English-only corpus; multilingual overhead is unnecessary |
| FAIR-RAG loop | LangGraph sub-graph | Separate FastAPI endpoint | Breaks the single agentic graph model; harder to maintain state across the pipeline |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| PDF parsing library choice | MEDIUM | `pymupdf4llm` is well-established but version should be verified on PyPI at implementation time |
| Chunking strategy (300–400 tokens) | HIGH | Directly from FARSIQA paper's empirical results; validated against the same book type |
| Reusing existing embedding model | HIGH | `all-mpnet-base-v2` is domain-general and handles English religious text; no research gap |
| RRF over weighted merge | HIGH | Standard algorithm from IR literature; FAIR-RAG and FARSIQA both validate it for this pipeline type |
| LangGraph sub-graph composition | MEDIUM | Sub-graphs were stabilized in 0.2.x but implementation details need verification against the exact version in use (0.2.64) |
| Dynamic LLM allocation | HIGH | Directly from FARSIQA Table 6 empirical results; cost/quality tradeoffs are well-characterized |
| TF-IDF vectorizer persistence requirement | HIGH | This is a known constraint of TF-IDF in batch ingestion; must be addressed in the ingestion design |

---

## Sources

- FAIR_RAG_Fiqh_Implementation_Guide.md — internal synthesis of FAIR-RAG and FARSIQA papers
- `.planning/codebase/STACK.md` — existing stack audit (2026-03-22)
- `requirements.txt` — pinned versions of all installed packages
- `modules/embedding/embedder.py` — confirmed `all-mpnet-base-v2` and TF-IDF usage
- `modules/reranking/reranker.py` — confirmed weighted score merge (not RRF) in existing pipeline
- `agents/core/chat_agent.py` — confirmed LangGraph 0.2.64 StateGraph pattern and fiqh early-exit node
- PyMuPDF documentation: https://pymupdf.readthedocs.io/en/latest/ (HIGH confidence for library capabilities; version pinning needs current PyPI check)
- FARSIQA paper (Section 4, Table 6) — dynamic LLM allocation cost/quality data
- RRF algorithm: Cormack et al. 2009 — standard IR result, no version concerns
