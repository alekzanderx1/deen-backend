# Milestones

## v1.0 Fiqh Agentic RAG MVP (Shipped: 2026-03-25)

**Phases completed:** 4 phases, 12 plans, 17 tasks

**Key accomplishments:**

- pymupdf and pinecone-text pinned in requirements.txt, fiqh Pinecone index env vars exported from core/config.py, and data/ directory scaffolded with BM25 encoder gitignored
- PyMuPDF-based PDF parsing with ruling-boundary chunking producing 3000 structured chunks from 2796 Sistani rulings, with chapter/section/topic metadata on every chunk
- Full Pinecone fiqh ingestion pipeline: BM25Encoder fitted on 3000 chunks + dense embedding via all-mpnet-base-v2 + dual upsert to deen-fiqh-dense and deen-fiqh-sparse indexes with idempotent index creation
- 6-category fiqh classifier (classify_fiqh_query, gpt-4o-mini) added to modules/fiqh/classifier.py; fiqh_category field added to ChatState for downstream routing
- Query decomposer (decompose_query) with JSON fence stripping and safe fallback to original query; unit tests for classifier and decomposer (mocked LLM)
- Hybrid fiqh retriever using BM25 sparse + dense Pinecone raw index queries merged with Reciprocal Rank Fusion (k=60), returning up to 20 deduplicated docs per query via decomposed sub-queries.
- LLM-based evidence filter (gpt-4.1) and Structured Evidence Assessment (gpt-4o-mini with Pydantic structured output) for the FAIR-RAG pipeline — 23 mock-based unit tests, all pass
- Query refiner (gpt-4.1) targeting SEA gaps + confirmed facts, and answer generator (gpt-4.1) with inline [n] citations, ## Sources section, mandatory fatwa disclaimer, and insufficient-evidence warning — 23 mock-based unit tests, all pass
- Pure Python FAIR-RAG coordinator wiring all Phase 3 modules (filter, SEA, refiner, generator) with Phase 2 retriever into a max-3-iteration retrieve-filter-assess-refine loop — 9 mock-based unit tests, all pass
- FiqhState TypedDict (7 fields), ChatState fiqh result fields, and format_fiqh_references_as_json() — state contracts enabling Plans 02 and 03 to import concrete types without circular uncertainty

---
