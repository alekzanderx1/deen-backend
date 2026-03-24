# Requirements: Deen Backend — Fiqh Agentic RAG

**Defined:** 2026-03-23
**Core Value:** Every fiqh answer must be strictly grounded in retrieved evidence from Ayatollah Sistani's published rulings — the system refuses to answer rather than hallucinate or speculate.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Ingestion

- [ ] **INGE-01**: System can parse Sistani's "Islamic Laws" (4th edition) PDF into structured text preserving chapter/section hierarchy and ruling numbers
- [ ] **INGE-02**: System chunks parsed text at ~300-400 tokens with ruling-number boundaries as primary split points, paragraph boundaries as secondary
- [ ] **INGE-03**: Each chunk is tagged with metadata: source book, chapter, section, ruling number(s), topic tags (tahara, salah, sawm, hajj, khums, etc.)
- [ ] **INGE-04**: System generates dense embeddings for all chunks and uploads to a dedicated Pinecone fiqh dense index
- [ ] **INGE-05**: System generates sparse embeddings using Pinecone's sparse encoder (pinecone-text BM25) for all chunks and uploads to a dedicated Pinecone fiqh sparse index
- [ ] **INGE-06**: Sparse encoder is initialized with the fiqh corpus vocabulary for consistent encoding at both ingestion and query time

### Query Classification

- [ ] **CLAS-01**: System classifies incoming queries into exactly one of 6 categories: VALID_OBVIOUS, VALID_SMALL, VALID_LARGE, VALID_REASONER, OUT_OF_SCOPE_FIQH, UNETHICAL
- [ ] **CLAS-02**: OUT_OF_SCOPE_FIQH queries are politely rejected with a redirect message before any retrieval occurs
- [ ] **CLAS-03**: UNETHICAL queries are immediately rejected
- [ ] **CLAS-04**: Classification uses the small LLM (gpt-4o-mini) for cost efficiency
- [ ] **CLAS-05**: Negative rejection accuracy targets >95% — system correctly refuses out-of-scope and unanswerable questions at both the classification and generation layers

### Query Processing

- [ ] **QPRO-01**: Complex fiqh queries are decomposed into 1-4 semantically independent, keyword-rich sub-queries optimized for retrieval
- [ ] **QPRO-02**: Sub-queries include domain-specific fiqh terminology (Arabic/Persian transliterated terms) where appropriate
- [ ] **QPRO-03**: Query decomposition uses the small LLM (gpt-4o-mini)

### Retrieval

- [ ] **RETR-01**: System performs hybrid retrieval (dense + sparse) from dedicated fiqh Pinecone indexes for each sub-query
- [ ] **RETR-02**: Dense and sparse results are merged using Reciprocal Rank Fusion (RRF, k=60)
- [ ] **RETR-03**: Top-5 documents per sub-query are retained after RRF merging
- [ ] **RETR-04**: Retrieved documents include source metadata (book, chapter, section, ruling number) for citation

### Evidence Assessment

- [ ] **EVID-01**: LLM-based evidence filter removes clearly irrelevant documents while preserving partially relevant ones (inclusive approach)
- [ ] **EVID-02**: Evidence filtering uses the large LLM (gpt-4.1) for subtle relevance judgments
- [ ] **EVID-03**: Structured Evidence Assessment (SEA) deconstructs the query into a numbered checklist of required findings
- [ ] **EVID-04**: SEA checks each required finding against retrieved evidence, classifying as confirmed (with logical inferences) or gap
- [ ] **EVID-05**: SEA produces a sufficiency verdict (Yes/No) — "Yes" only when ALL required findings are confirmed
- [ ] **EVID-06**: When SEA identifies gaps, the system generates 1-4 targeted refinement queries using confirmed facts to narrow the search
- [ ] **EVID-07**: The retrieval-assess-refine loop runs a maximum of 3 iterations, with early exit when SEA declares sufficiency
- [ ] **EVID-08**: Query refinement uses the large LLM (gpt-4.1) and never repeats or rephrases previous queries

### Answer Generation

- [ ] **AGEN-01**: Final answer is generated exclusively from retrieved evidence — no parametric LLM knowledge used
- [ ] **AGEN-02**: Every factual claim includes an inline citation token [n] linking to the source document
- [ ] **AGEN-03**: Response includes a references list at the end with book, chapter, section, and ruling number for each cited source
- [ ] **AGEN-04**: Every response that states a ruling includes a fatwa disclaimer: "This is based on Ayatollah Sistani's published works. For a definitive ruling, consult a qualified jurist or Sistani's official office."
- [ ] **AGEN-05**: When evidence is insufficient after max iterations, system provides a partial answer with an explicit warning and redirect to official sources
- [ ] **AGEN-06**: When no relevant evidence exists, system states this clearly and redirects to Sistani's official resources
- [ ] **AGEN-07**: Answer generation uses the large LLM (gpt-4.1)
- [ ] **AGEN-08**: Dynamic LLM allocation routes small tasks (classification, decomposition, SEA) to gpt-4o-mini and heavy tasks (filtering, refinement, generation) to gpt-4.1

### Integration

- [ ] **INTG-01**: FAIR-RAG pipeline is implemented as a compiled LangGraph sub-graph invoked by the main ChatAgent when a query is classified as fiqh
- [ ] **INTG-02**: The existing `fiqh_classification` node routes to the fiqh sub-graph instead of the current early-exit behavior
- [ ] **INTG-03**: SSE status events are emitted for each fiqh pipeline stage: classifying, decomposing, retrieving, filtering, assessing, refining, generating
- [ ] **INTG-04**: The final answer is streamed token-by-token via the existing SSE `response_chunk` protocol
- [ ] **INTG-05**: Fiqh references (citations with source metadata) are emitted as a new SSE event type alongside the existing hadith/quran reference events

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
| INGE-01 | Phase 1 | Pending |
| INGE-02 | Phase 1 | Pending |
| INGE-03 | Phase 1 | Pending |
| INGE-04 | Phase 1 | Pending |
| INGE-05 | Phase 1 | Pending |
| INGE-06 | Phase 1 | Pending |
| CLAS-01 | Phase 2 | Pending |
| CLAS-02 | Phase 2 | Pending |
| CLAS-03 | Phase 2 | Pending |
| CLAS-04 | Phase 2 | Pending |
| CLAS-05 | Phase 2 | Pending |
| QPRO-01 | Phase 2 | Pending |
| QPRO-02 | Phase 2 | Pending |
| QPRO-03 | Phase 2 | Pending |
| RETR-01 | Phase 2 | Pending |
| RETR-02 | Phase 2 | Pending |
| RETR-03 | Phase 2 | Pending |
| RETR-04 | Phase 2 | Pending |
| EVID-01 | Phase 3 | Pending |
| EVID-02 | Phase 3 | Pending |
| EVID-03 | Phase 3 | Pending |
| EVID-04 | Phase 3 | Pending |
| EVID-05 | Phase 3 | Pending |
| EVID-06 | Phase 3 | Pending |
| EVID-07 | Phase 3 | Pending |
| EVID-08 | Phase 3 | Pending |
| AGEN-01 | Phase 3 | Pending |
| AGEN-02 | Phase 3 | Pending |
| AGEN-03 | Phase 3 | Pending |
| AGEN-04 | Phase 3 | Pending |
| AGEN-05 | Phase 3 | Pending |
| AGEN-06 | Phase 3 | Pending |
| AGEN-07 | Phase 3 | Pending |
| AGEN-08 | Phase 3 | Pending |
| INTG-01 | Phase 4 | Pending |
| INTG-02 | Phase 4 | Pending |
| INTG-03 | Phase 4 | Pending |
| INTG-04 | Phase 4 | Pending |
| INTG-05 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-23*
*Last updated: 2026-03-23 after roadmap creation — all 39 requirements mapped*
