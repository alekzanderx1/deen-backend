# Requirements: Deen Backend — Fiqh Agentic RAG

**Defined:** 2026-03-23
**Core Value:** Every fiqh answer must be strictly grounded in retrieved evidence from Ayatollah Sistani's published rulings — the system refuses to answer rather than hallucinate or speculate.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Ingestion

- [x] **INGE-01**: System can parse Sistani's "Islamic Laws" (4th edition) PDF into structured text preserving chapter/section hierarchy and ruling numbers
- [x] **INGE-02**: System chunks parsed text at ~300-400 tokens with ruling-number boundaries as primary split points, paragraph boundaries as secondary
- [x] **INGE-03**: Each chunk is tagged with metadata: source book, chapter, section, ruling number(s), topic tags (tahara, salah, sawm, hajj, khums, etc.)
- [x] **INGE-04**: System generates dense embeddings for all chunks and uploads to a dedicated Pinecone fiqh dense index
- [x] **INGE-05**: System generates sparse embeddings using Pinecone's sparse encoder (pinecone-text BM25) for all chunks and uploads to a dedicated Pinecone fiqh sparse index
- [x] **INGE-06**: Sparse encoder is initialized with the fiqh corpus vocabulary for consistent encoding at both ingestion and query time

### Query Classification

- [x] **CLAS-01**: System classifies incoming queries into exactly one of 6 categories: VALID_OBVIOUS, VALID_SMALL, VALID_LARGE, VALID_REASONER, OUT_OF_SCOPE_FIQH, UNETHICAL
- [x] **CLAS-02**: OUT_OF_SCOPE_FIQH queries are politely rejected with a redirect message before any retrieval occurs
- [x] **CLAS-03**: UNETHICAL queries are immediately rejected
- [x] **CLAS-04**: Classification uses the small LLM (gpt-4o-mini) for cost efficiency
- [x] **CLAS-05**: Negative rejection accuracy targets >95% — system correctly refuses out-of-scope and unanswerable questions at both the classification and generation layers

### Query Processing

- [x] **QPRO-01**: Complex fiqh queries are decomposed into 1-4 semantically independent, keyword-rich sub-queries optimized for retrieval
- [x] **QPRO-02**: Sub-queries include domain-specific fiqh terminology (Arabic/Persian transliterated terms) where appropriate
- [x] **QPRO-03**: Query decomposition uses the small LLM (gpt-4o-mini)

### Retrieval

- [x] **RETR-01**: System performs hybrid retrieval (dense + sparse) from dedicated fiqh Pinecone indexes for each sub-query
- [x] **RETR-02**: Dense and sparse results are merged using Reciprocal Rank Fusion (RRF, k=60)
- [x] **RETR-03**: Top-5 documents per sub-query are retained after RRF merging
- [x] **RETR-04**: Retrieved documents include source metadata (book, chapter, section, ruling number) for citation

### Evidence Assessment

- [x] **EVID-01**: LLM-based evidence filter removes clearly irrelevant documents while preserving partially relevant ones (inclusive approach)
- [x] **EVID-02**: Evidence filtering uses the large LLM (gpt-4.1) for subtle relevance judgments
- [x] **EVID-03**: Structured Evidence Assessment (SEA) deconstructs the query into a numbered checklist of required findings
- [x] **EVID-04**: SEA checks each required finding against retrieved evidence, classifying as confirmed (with logical inferences) or gap
- [x] **EVID-05**: SEA produces a sufficiency verdict (Yes/No) — "Yes" only when ALL required findings are confirmed
- [x] **EVID-06**: When SEA identifies gaps, the system generates 1-4 targeted refinement queries using confirmed facts to narrow the search
- [x] **EVID-07**: The retrieval-assess-refine loop runs a maximum of 3 iterations, with early exit when SEA declares sufficiency
- [x] **EVID-08**: Query refinement uses the large LLM (gpt-4.1) and never repeats or rephrases previous queries

### Answer Generation

- [x] **AGEN-01**: Final answer is generated exclusively from retrieved evidence — no parametric LLM knowledge used
- [x] **AGEN-02**: Every factual claim includes an inline citation token [n] linking to the source document
- [x] **AGEN-03**: Response includes a references list at the end with book, chapter, section, and ruling number for each cited source
- [x] **AGEN-04**: Every response that states a ruling includes a fatwa disclaimer: "This is based on Ayatollah Sistani's published works. For a definitive ruling, consult a qualified jurist or Sistani's official office."
- [x] **AGEN-05**: When evidence is insufficient after max iterations, system provides a partial answer with an explicit warning and redirect to official sources
- [x] **AGEN-06**: When no relevant evidence exists, system states this clearly and redirects to Sistani's official resources
- [x] **AGEN-07**: Answer generation uses the large LLM (gpt-4.1)
- [x] **AGEN-08**: Dynamic LLM allocation routes small tasks (classification, decomposition, SEA) to gpt-4o-mini and heavy tasks (filtering, refinement, generation) to gpt-4.1

### Integration

- [x] **INTG-01**: FAIR-RAG pipeline is implemented as a compiled LangGraph sub-graph invoked by the main ChatAgent when a query is classified as fiqh
- [x] **INTG-02**: The existing `fiqh_classification` node routes to the fiqh sub-graph instead of the current early-exit behavior
- [x] **INTG-03**: SSE status events are emitted for each fiqh pipeline stage: classifying, decomposing, retrieving, filtering, assessing, refining, generating
- [ ] **INTG-04**: The final answer is streamed token-by-token via the existing SSE `response_chunk` protocol
- [x] **INTG-05**: Fiqh references (citations with source metadata) are emitted as a new SSE event type alongside the existing hadith/quran reference events

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Extended Corpus

- **XCOR-01**: Ingest Sistani.org official Q&A data with question prepended to answer chunks
- **XCOR-02**: Ingest additional Sistani publications (A Code of Practice for Muslims in the West, etc.)

### Advanced Features

- **ADVF-01**: VALID_OBVIOUS queries bypass RAG entirely and answer from common Islamic knowledge
- **ADVF-02**: Topic-scoped retrieval using metadata tags (e.g., only retrieve from tahara section for purity questions)
- **ADVF-03**: Extra disclaimer triggers for sensitive categories (khums, inheritance, divorce, personal fatwas)
- **ADVF-04**: Reasoning model routing for complex multi-step calculations (inheritance shares, khums)

### Evaluation

- **EVAL-01**: Systematic LLM-as-Judge evaluation harness for faithfulness, correctness, and negative rejection
- **EVAL-02**: Component-level quality metrics for each pipeline stage

## Out of Scope

| Feature | Reason |
|---------|--------|
| Other maraji beyond Sistani | Single-scholar focus prevents dangerous cross-marja conflation |
| Arabic/Persian fiqh pipeline | English-first; existing translation tool handles non-English queries |
| Model fine-tuning or training | Agentic pipeline architecture only per project scope |
| Frontend or UI changes | Backend API milestone; frontend consumes existing SSE protocol |
| Sistani.org Q&A scraping | Book corpus is bounded and sufficient for MVP; deferred to v2 |
| LLM-as-Judge evaluation harness | Manual spot-checks this milestone; systematic eval in future milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGE-01 | Phase 1 | Complete |
| INGE-02 | Phase 1 | Complete |
| INGE-03 | Phase 1 | Complete |
| INGE-04 | Phase 1 | Complete |
| INGE-05 | Phase 1 | Complete |
| INGE-06 | Phase 1 | Complete |
| CLAS-01 | Phase 2 | Complete |
| CLAS-02 | Phase 2 | Complete |
| CLAS-03 | Phase 2 | Complete |
| CLAS-04 | Phase 2 | Complete |
| CLAS-05 | Phase 2 | Complete |
| QPRO-01 | Phase 2 | Complete |
| QPRO-02 | Phase 2 | Complete |
| QPRO-03 | Phase 2 | Complete |
| RETR-01 | Phase 2 | Complete |
| RETR-02 | Phase 2 | Complete |
| RETR-03 | Phase 2 | Complete |
| RETR-04 | Phase 2 | Complete |
| EVID-01 | Phase 3 | Complete |
| EVID-02 | Phase 3 | Complete |
| EVID-03 | Phase 3 | Complete |
| EVID-04 | Phase 3 | Complete |
| EVID-05 | Phase 3 | Complete |
| EVID-06 | Phase 3 | Complete |
| EVID-07 | Phase 3 | Complete |
| EVID-08 | Phase 3 | Complete |
| AGEN-01 | Phase 3 | Complete |
| AGEN-02 | Phase 3 | Complete |
| AGEN-03 | Phase 3 | Complete |
| AGEN-04 | Phase 3 | Complete |
| AGEN-05 | Phase 3 | Complete |
| AGEN-06 | Phase 3 | Complete |
| AGEN-07 | Phase 3 | Complete |
| AGEN-08 | Phase 3 | Complete |
| INTG-01 | Phase 4 | Complete |
| INTG-02 | Phase 4 | Complete |
| INTG-03 | Phase 4 | Complete |
| INTG-04 | Phase 4 | Pending |
| INTG-05 | Phase 4 | Complete |

**Coverage:**
- v1 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 after roadmap creation — all 39 requirements mapped*
