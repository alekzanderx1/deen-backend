# Roadmap: Deen Backend — Fiqh Agentic RAG

## Overview

Four phases build the FAIR-RAG pipeline from the ground up: first the fiqh corpus is ingested into dedicated Pinecone indexes (nothing else is testable without data), then the query routing and retrieval layers are established, then the core FAIR-RAG iterative modules are built and unit-tested in isolation, and finally everything is assembled into a LangGraph sub-graph wired into the live SSE streaming endpoint. Each phase delivers a coherent, independently verifiable capability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Foundation** - Ingest Sistani's "Islamic Laws" into dedicated Pinecone fiqh indexes (completed 2026-03-24)
- [ ] **Phase 2: Routing and Retrieval** - Upgrade query classifier and build hybrid fiqh retrieval
- [ ] **Phase 3: FAIR-RAG Core Modules** - Build evidence filtering, SEA, query refinement, and answer generation
- [x] **Phase 4: Assembly and Integration** - Wire sub-graph into the main agent and SSE streaming layer (completed 2026-03-25)

## Phase Details

### Phase 1: Data Foundation
**Goal**: Sistani's "Islamic Laws" is fully ingested and searchable in dedicated Pinecone fiqh indexes
**Depends on**: Nothing (first phase)
**Requirements**: INGE-01, INGE-02, INGE-03, INGE-04, INGE-05, INGE-06
**Success Criteria** (what must be TRUE):
  1. Running `ingest_fiqh.py` completes without errors and populates both Pinecone fiqh indexes
  2. Each chunk in Pinecone contains source metadata: book, chapter, section, and ruling number
  3. A test query to the dense index returns semantically relevant rulings from the correct chapter
  4. A test query to the sparse index returns keyword-matched results including Arabic/Persian fiqh terms
  5. The BM25 encoder is persisted to disk and reloadable for query-time sparse encoding
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Add dependencies (pymupdf, pinecone-text) and register fiqh env vars in core/config.py
- [x] 01-02-PLAN.md — Write PDF parsing and chunking layer (parse_pdf, chunk_rulings, --dry-run)
- [x] 01-03-PLAN.md — Implement embedding + dual Pinecone upsert; run full ingestion and verify

### Phase 2: Routing and Retrieval
**Goal**: Fiqh queries are accurately classified and retrieved against the fiqh corpus with hybrid search
**Depends on**: Phase 1
**Requirements**: CLAS-01, CLAS-02, CLAS-03, CLAS-04, CLAS-05, QPRO-01, QPRO-02, QPRO-03, RETR-01, RETR-02, RETR-03, RETR-04
**Success Criteria** (what must be TRUE):
  1. The classifier correctly routes a 50+ labeled query set: fiqh queries classified as VALID_*, out-of-scope queries as OUT_OF_SCOPE_FIQH or UNETHICAL (>95% accuracy)
  2. OUT_OF_SCOPE_FIQH and UNETHICAL queries receive a rejection response before any retrieval runs
  3. A complex multi-part fiqh query is decomposed into 2-4 independent, terminology-rich sub-queries
  4. Hybrid retrieval (dense + sparse + RRF) returns top-5 documents with source metadata for each sub-query
  5. Dense-only and sparse-only queries on fiqh terminology differ in ranking, confirming both paths are active
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Create modules/fiqh package, 6-category classifier, and ChatState fiqh_category field
- [x] 02-02-PLAN.md — Build query decomposer and unit tests for classifier + decomposer (mocked LLM)
- [x] 02-03-PLAN.md — Build hybrid RRF retriever and unit tests for retriever (mocked Pinecone)

### Phase 3: FAIR-RAG Core Modules
**Goal**: The four FAIR-RAG processing modules — evidence filter, SEA, query refiner, and answer generator — each work correctly in isolation against synthetic evidence sets
**Depends on**: Phase 1
**Requirements**: EVID-01, EVID-02, EVID-03, EVID-04, EVID-05, EVID-06, EVID-07, EVID-08, AGEN-01, AGEN-02, AGEN-03, AGEN-04, AGEN-05, AGEN-06, AGEN-07, AGEN-08
**Success Criteria** (what must be TRUE):
  1. The evidence filter removes clearly irrelevant documents while preserving partially relevant ones when given a synthetic evidence set
  2. SEA produces a numbered findings checklist, classifies each as confirmed (with exact textual citation) or gap, and returns a sufficiency verdict of Yes only when all findings are confirmed
  3. When SEA identifies gaps, the query refiner produces 1-4 new refinement queries that reference confirmed facts and do not repeat prior queries
  4. The answer generator produces a response citing only retrieved evidence, with inline [n] tokens, a references list, and a fatwa disclaimer on every ruling answer
  5. When evidence is insufficient after max iterations, the generator produces a partial answer with an explicit insufficient-evidence warning and redirect to official sources — not a hallucinated ruling
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md — Build filter.py (evidence filter) and sea.py (SEA with Pydantic structured output) + tests
- [x] 03-02-PLAN.md — Build refiner.py (query refinement) and generator.py (answer generation with citations) + tests
- [ ] 03-03-PLAN.md — Build fair_rag.py (FAIR-RAG coordinator: max-3-iteration loop) + tests

### Phase 4: Assembly and Integration
**Goal**: The complete FAIR-RAG pipeline runs end-to-end as a LangGraph sub-graph invoked by the live SSE streaming chat endpoint
**Depends on**: Phase 2, Phase 3
**Requirements**: INTG-01, INTG-02, INTG-03, INTG-04, INTG-05
**Success Criteria** (what must be TRUE):
  1. A fiqh query sent to `/chat/stream/agentic` triggers the FiqhAgent sub-graph and streams SSE status events for each pipeline stage (classifying, decomposing, retrieving, filtering, assessing, refining, generating)
  2. The final answer streams token-by-token via the existing `response_chunk` SSE event type
  3. Fiqh citations are emitted as a `fiqh_references` SSE event with book, chapter, section, and ruling number for each source
  4. A non-fiqh query sent to the same endpoint follows the existing non-fiqh path — FiqhAgent is not invoked
  5. Two concurrent fiqh sessions do not share state — each session's FiqhState is isolated and independent
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — State foundations: FiqhState TypedDict, ChatState fiqh fields, format_fiqh_references_as_json
- [x] 04-02-PLAN.md — FiqhAgent sub-graph + updated ChatAgent routing and generation nodes
- [x] 04-03-PLAN.md — SSE streaming integration: fiqh path detection, token streaming, fiqh_references event + tests

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

Note: Phase 3 depends only on Phase 1 (data), so it can begin in parallel with Phase 2 once Phase 1 is complete.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 3/3 | Complete   | 2026-03-24 |
| 2. Routing and Retrieval | 0/3 | Not started | - |
| 3. FAIR-RAG Core Modules | 2/3 | In Progress|  |
| 4. Assembly and Integration | 3/3 | Complete   | 2026-03-25 |
