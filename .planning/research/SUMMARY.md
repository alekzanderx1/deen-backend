# Project Research Summary

**Project:** Deen Backend — Fiqh Agentic RAG (FAIR-RAG Pipeline)
**Domain:** Agentic RAG for Islamic legal (fiqh) Q&A — Ayatollah Sistani's published rulings
**Researched:** 2026-03-23
**Confidence:** HIGH

## Executive Summary

This milestone adds a FAIR-RAG (Fiqh Agentic Iterative RAG) pipeline to the existing Deen Backend. The system answers Shia Islamic legal questions grounded strictly in Ayatollah Sistani's published "Islamic Laws" (4th edition). The recommended architecture is a LangGraph sub-graph that the existing main ChatAgent routes into on fiqh-classified queries — replacing the current hard-exit with a full iterative decompose → retrieve → filter → assess → refine loop (max 3 iterations) before generating a grounded answer. This pattern is directly validated by the FARSIQA paper which achieved 97% negative rejection accuracy and 62.5% faithfulness on Islamic domain queries using dynamic LLM allocation.

The stack is almost entirely reused: FastAPI, LangGraph 0.2.64, Pinecone, Redis, OpenAI, and the existing sentence-transformers/all-mpnet-base-v2 + TF-IDF sparse embedding pair all carry forward unchanged. The only net-new pip dependency is `pymupdf4llm` for PDF parsing. Two new Pinecone indexes (dense + sparse) are required to keep the fiqh corpus isolated from the hadith/Quran indexes. A one-time ingestion script processes the Sistani PDF into ~300-400 token chunks with chapter/section/ruling-number metadata, after which the live pipeline is fully data-driven.

The dominant risk is **generation hallucination**: in the Islamic domain specifically, 54.9% of pipeline errors originate in the generation step — the LLM synthesizing rulings from parametric memory rather than retrieved evidence. Mitigating this requires hard grounding constraints in the generation prompt (temperature=0, explicit "cite or omit" instruction) plus a post-generation faithfulness check. The second major risk is the existing fiqh classifier performing poorly (noted in PROJECT.md) — it must be replaced with a typed 6-category router before the FAIR-RAG pipeline can route correctly. Both risks have clear, well-researched mitigations and must be addressed in the first two phases.

---

## Key Findings

### Recommended Stack

The incremental stack is minimal. The existing FastAPI + LangGraph + Pinecone + OpenAI infrastructure handles everything; the only additions are `pymupdf4llm` (PDF parsing), two new Pinecone indexes, and a pure-Python RRF merge function (~20 lines). The existing `langchain-text-splitters`, `tiktoken`, `sentence-transformers`, and `scikit-learn` packages already cover chunking, token counting, dense embedding, and sparse embedding respectively.

**Core technologies:**
- `pymupdf4llm==0.0.17`: PDF → structured Markdown — fastest Python PDF renderer with LLM-optimized output; preserves heading hierarchy critical for chapter/section metadata
- Custom RRF function (pure Python): merge dense + sparse Pinecone results by rank — more robust than weighted score fusion for cross-modal merging; k=60 requires no tuning
- `langgraph==0.2.64` (existing): FAIR-RAG iterative loop as a compiled sub-graph — sub-graph composition is stable in 0.2.x; maps directly to the deterministic loop structure FAIR-RAG requires
- Dynamic LLM allocation (config-only): `gpt-4o-mini` for routing/decomposition/SEA, `gpt-4.1` for filtering/refinement/generation — 13% cheaper than static large-model usage with higher faithfulness
- Two new Pinecone indexes (`FIQH_DENSE_INDEX_NAME`, `FIQH_SPARSE_INDEX_NAME`): isolated fiqh corpus with chunk metadata schema including `chunk_id`, `chapter`, `section`, `page_number`, `ruling_number`

**New env vars required:** `FIQH_DENSE_INDEX_NAME`, `FIQH_SPARSE_INDEX_NAME`

**Net new pip dependency: 1** (`pymupdf4llm`)

### Expected Features

**Must have (table stakes):**
- Fiqh corpus ingestion pipeline — no other feature is testable without a populated Pinecone index
- Upgraded query classifier (6-category router) — current binary classifier is known-broken; all routing depends on this
- Negative rejection (97% target) — wrong answer is worse than no answer in a religious legal context; two-layer defense required
- Hybrid retrieval (dense + sparse + RRF) — fiqh Arabic/Persian terminology (wudu, najasah, tayammum) is out-of-distribution for dense-only embeddings
- Inline citations linking to source passages — trust-critical; every factual claim needs a `[n]` token + chapter/ruling references
- Fatwa disclaimer on every ruling response (complete, partial, or uncertain) — non-negotiable; applies to all ruling responses without exception
- Insufficient evidence partial answer + redirect — must not silently hallucinate when evidence is exhausted after 3 iterations
- SSE status streaming for FAIR-RAG stages — pipeline takes 15-25s; UI appears frozen without intermediate events

**Should have (differentiators):**
- Structured Evidence Assessment (SEA) — core innovation enabling 97% negative rejection; three-step checklist audit is what distinguishes this from naive RAG
- Query decomposition into independent sub-queries (1-4 per iteration) — handles multi-hop fiqh questions that require separate retrieval for base ruling + exception + conditions
- Iterative query refinement using confirmed facts — highest-scoring FARSIQA component (4.45-4.61/5.0); eliminates re-stating the original question on subsequent passes
- Dynamic LLM allocation — empirically validated cost/quality tradeoff; 13% cheaper, better faithfulness
- Topic-tagged chunk metadata (chapter/section/ruling number) — enables verifiable citations and future scoped retrieval

**Defer to v2+:**
- Reasoning model routing (o1/o3 for complex inheritance): FARSIQA showed static reasoner is 11.8x more expensive with worse faithfulness — do not build
- Multi-marja support (Khamenei, Fadlallah): religious sensitivity risk; each marja needs separate corpus and evaluation
- Sistani.org Q&A scraping: legal/maintenance risk; add after book pipeline is validated
- Arabic/Persian query answering: doubles embedding complexity; English-first
- LLM-as-Judge evaluation harness: valuable but should not block pipeline; build as a separate milestone
- Frontend or UI changes: backend-only milestone

### Architecture Approach

The FAIR-RAG system integrates as a LangGraph sub-graph within the existing `ChatAgent`. The main graph's `fiqh_classification` node is upgraded from a binary exit to a typed 6-category router; on `is_fiqh=True`, the main graph hands off to the compiled `FiqhAgent` sub-graph which owns the full iterative loop. The final answer flows back into `ChatState.early_exit_message`, following the existing Redis + Postgres persistence path unchanged. SSE streaming happens at the `pipeline_langgraph.py` orchestration layer — graph nodes use `llm.invoke()` (non-streaming), and the orchestrator streams the final answer token-by-token exactly as the non-fiqh path does today.

**Major components:**

1. `scripts/ingest_fiqh.py` (DataIngestionPipeline) — one-time script: PDF parse → paragraph-boundary chunking (300-400 tokens, ruling-number anchored) → dense + sparse embeddings → Pinecone upload with chapter/section/ruling metadata; persists fitted TF-IDF vectorizer to disk
2. `modules/classification/fiqh_classifier.py` (FiqhClassifier) — replaces binary `classify_fiqh_query`; returns typed `FiqhCategory` enum (VALID_OBVIOUS / VALID_SMALL / VALID_LARGE / OUT_OF_SCOPE_FIQH / UNETHICAL); uses `gpt-4o-mini`
3. `agents/fiqh/fiqh_agent.py` (FiqhAgent) — compiled `StateGraph(FiqhState)`; owns the full FAIR-RAG iterative loop; called as a black-box node from `ChatAgent`, not as a tool
4. `modules/fiqh/retriever.py` (FiqhRetriever) — hybrid Pinecone search (dense + sparse) → RRF merge (k=60); top-3 per retriever per sub-query → RRF → top-5
5. `modules/fiqh/sea_module.py` (SEAModule) — Structured Evidence Assessment; deconstructs query into required-findings checklist, checks each against accumulated evidence, produces confirmed_facts + gaps + sufficient verdict; uses `gpt-4o-mini`
6. `modules/fiqh/evidence_filter.py` (FiqhEvidenceFilter) — inclusive filter using `gpt-4.1`; anchored to original user query, not sub-query; removes only clearly irrelevant documents
7. `modules/fiqh/query_refiner.py` (QueryRefiner) — generates targeted refinement sub-queries using confirmed facts; uses `gpt-4.1`; never repeats prior queries
8. `modules/fiqh/generator.py` (FiqhGenerator) — strictly evidence-grounded generation with inline citations, mandatory fatwa disclaimer, partial-answer fallback; uses `gpt-4.1` at temperature=0

### Critical Pitfalls

1. **LLM synthesizes rulings from parametric memory (54.9% of Islamic domain errors)** — hard grounding constraint in generation prompt ("cite or omit"), temperature=0, post-generation faithfulness check; this is the highest-severity failure for this product
2. **PDF parsing breaks ruling continuity at page boundaries** — extract as continuous text first, then chunk anchored to ruling numbers; never break a ruling number boundary to hit the token target; validate chunks for mid-sentence starts
3. **SEA declares sufficiency too early (premature loop exit)** — require SEA to cite the exact evidence sentence for each confirmed finding; prohibit logical inference for fiqh rulings; assert that multi-hop queries iterate at least 2 times in tests
4. **Dense retrieval alone misses Arabic/Persian fiqh terminology** — hybrid retrieval (dense + sparse + RRF) must be in place from day one, not added as an optimization; do not prototype with dense-only
5. **Existing binary fiqh classifier mis-routes edge cases** — replace with 6-category typed router before wiring FAIR-RAG; build a 50+ labeled example evaluation set covering edge cases
6. **LangGraph sub-graph state leak between sessions** — FiqhState must be freshly instantiated per request; do not share thread ID or checkpointer with ChatState; write cross-contamination integration test

---

## Implications for Roadmap

The dependency chain is strict: data must exist before retrieval can be tested, retrieval must work before the iterative loop can be built, and the loop must be correct before SSE integration makes sense. Modules with no retrieval dependency (FiqhClassifier, FiqhEvidenceFilter, SEAModule, QueryRefiner, FiqhGenerator) can be developed in parallel once the data foundation is ready.

### Phase 1: Data Foundation (Fiqh Corpus Ingestion)

**Rationale:** No other component is testable without a populated fiqh Pinecone index. PDF parsing quality and chunking strategy directly determine the ceiling for every downstream component — re-chunking requires re-embedding the entire corpus, making mistakes here the most expensive to fix. Must be solved before any embeddings are generated.

**Delivers:** Populated `FIQH_DENSE_INDEX_NAME` and `FIQH_SPARSE_INDEX_NAME` Pinecone indexes; persisted TF-IDF vectorizer; `scripts/ingest_fiqh.py`; two new Pinecone indexes created in dashboard; `FIQH_DENSE_INDEX_NAME` + `FIQH_SPARSE_INDEX_NAME` added to `.env`

**Addresses:** Fiqh corpus ingestion (table stakes), hybrid retrieval prerequisite, topic-tagged chunk metadata

**Avoids:**
- Pitfall 3: cross-page ruling fragments — extract continuous text, anchor chunks to ruling numbers, allow up to 500 tokens to keep rulings intact
- Pitfall 12: missing chapter/section metadata — extract and store chapter, section, ruling_number per chunk
- Pitfall 4 (partial): sparse index built alongside dense from the start

### Phase 2: Query Classification Upgrade

**Rationale:** The existing binary fiqh classifier is acknowledged as underperforming in PROJECT.md and is the first gate all traffic passes through. Building the FAIR-RAG loop on a broken classifier wastes engineering effort — every end-to-end test will produce wrong routing. This can be developed in parallel with Phase 1 since it has no retrieval dependency.

**Delivers:** `modules/classification/fiqh_classifier.py` (FiqhClassifier) returning typed `FiqhCategory` enum; unit test suite with 50+ labeled edge-case examples; updated `ChatAgent` routing function reading category instead of boolean

**Addresses:** Improved query classifier + negative rejection (table stakes), routing for VALID_OBVIOUS shortcut

**Avoids:**
- Pitfall 6: binary classifier boundary errors — 6-category taxonomy with labeled evaluation set
- Prevents over-classification (expensive pipeline runs on history questions) and under-classification (fiqh questions get generic hadith answers)

### Phase 3: Hybrid Retrieval Module

**Rationale:** With data in Pinecone and classification logic in place, retrieval is the next unblocked dependency. The FiqhRetriever is the foundation that SEA, filtering, and the iterative loop all depend on. Must use hybrid dense + sparse + RRF from the start — not prototyped with dense-only.

**Delivers:** `modules/fiqh/retriever.py` (FiqhRetriever) with RRF merge (k=60); top-3 per retriever per sub-query → RRF → top-5; retrieval recall measurement for k tuning

**Uses:** `pymupdf4llm` (already ingested), `all-mpnet-base-v2` + TF-IDF vectorizer (existing), `core/vectorstore.py` helpers (existing), custom RRF function

**Avoids:**
- Pitfall 4: dense-only misses Arabic/Persian fiqh terms — sparse index built alongside dense
- Pitfall 13: wrong k value for small corpus — start with top-3 per retriever, measure recall before committing

### Phase 4: FAIR-RAG Core Modules (Parallelizable)

**Rationale:** FiqhEvidenceFilter, SEAModule, QueryRefiner, and FiqhGenerator all have no retrieval dependency and can be unit-tested with synthetic evidence sets. They can be built in parallel by independent work streams and integrated once FiqhRetriever (Phase 3) is complete.

**Delivers:**
- `modules/fiqh/evidence_filter.py` (FiqhEvidenceFilter) — inclusive filter, anchored to original query, gpt-4.1
- `modules/fiqh/sea_module.py` (SEAModule) — required-findings checklist with explicit textual citation per confirmed finding, gpt-4o-mini
- `modules/fiqh/query_refiner.py` (QueryRefiner) — confirmed-facts-driven refinement, no query repetition, gpt-4.1
- `modules/fiqh/generator.py` (FiqhGenerator) — temperature=0, hard grounding constraint, fatwa disclaimer injected as post-processing (not prompt-only), partial-answer fallback, gpt-4.1

**Avoids:**
- Pitfall 1: parametric memory synthesis — hard grounding constraint + faithfulness post-check in FiqhGenerator
- Pitfall 2: premature SEA sufficiency — require textual citation per confirmed finding, prohibit inference
- Pitfall 5: over-aggressive evidence filtering — anchor to original query, default to inclusive
- Pitfall 10: missing disclaimer on partial answers — post-processing injection, unconditional

### Phase 5: FAIR-RAG Sub-Graph Assembly and Main Agent Integration

**Rationale:** Once all modules are tested independently, assemble the FiqhAgent StateGraph and wire it into the main ChatAgent. This is the integration point where state management, loop control, and routing all converge. Sub-graph state isolation must be enforced here.

**Delivers:** `agents/fiqh/fiqh_state.py` (FiqhState TypedDict); `agents/fiqh/fiqh_agent.py` (compiled StateGraph with iterative loop, max 3 iterations, conditional edges); updated `agents/core/chat_agent.py` with `fiqh_subgraph` node; extended `ChatState` with `fiqh_category` and `fiqh_citations`

**Implements:** FiqhAgent sub-graph architecture; main agent routing via FiqhClassifier output

**Avoids:**
- Pitfall 9: state leak between sessions — FiqhState freshly instantiated per request, not sharing checkpointer with ChatState
- Anti-Pattern 1: FAIR-RAG folded into free-form tool loop — compiled sub-graph with explicit edges enforces deterministic loop sequence

### Phase 6: SSE Streaming Integration and End-to-End Validation

**Rationale:** SSE integration is the final wiring step that makes the feature usable in the existing frontend. End-to-end tests close the loop on negative rejection accuracy, citation format, and cross-session state isolation.

**Delivers:** Updated `core/pipeline_langgraph.py` with `fiqh_status` event type (per FAIR-RAG stage with iteration number) and `fiqh_references` SSE event; `NODE_STATUS_MESSAGES` extended for FAIR-RAG nodes; integration test suite (`tests/test_fiqh_pipeline.py`) covering scope routing accuracy, SEA sufficiency verdicts, negative rejection rate (>95% target), citation format, and cross-session non-contamination

**Avoids:**
- Pitfall 11: blocking SSE status events — fire-and-forget, minimal payloads (<100 bytes), no intermediate evidence dumps
- Pitfall 14: negative rejection only tested end-to-end — unit test classifier layer separately from generation layer

### Phase Ordering Rationale

- Phases 1 and 2 can run in parallel (ingestion and classification have no mutual dependency)
- Phase 3 (retrieval) blocks Phase 5 (sub-graph assembly) but not Phase 4 (module development)
- Phases 4a-4d (individual modules) can be developed in parallel once Phase 3 is unblocked
- Phase 5 requires all of Phases 3 and 4 to be complete
- Phase 6 requires Phase 5 to be complete
- This ordering matches the build layer structure identified in ARCHITECTURE.md (Layers 0-7)

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (PDF Parsing):** `pymupdf4llm` version must be verified on PyPI at implementation time; ruling-number detection regex needs testing against the actual 4th edition PDF structure — the PDF's heading and ruling-number format may differ from assumptions
- **Phase 3 (Retrieval / TF-IDF persistence):** TF-IDF vectorizer pickle persistence pattern needs to be validated against how the existing pipeline handles the fitted vectorizer at query time; if the existing code doesn't persist it, this is a blocker that must be resolved before ingestion

Phases with standard patterns (skip additional research):
- **Phase 2 (Classifier):** prompt classification with structured output is well-documented; the 6-category taxonomy is fully specified in the FAIR-RAG implementation guide
- **Phase 4 (Core Modules):** all prompts and logic are fully specified in FAIR_RAG_Fiqh_Implementation_Guide.md with empirical backing from FARSIQA paper
- **Phase 5 (Sub-Graph Assembly):** LangGraph StateGraph with conditional loop edges is a documented pattern; FiqhState TypedDict schema is fully specified in ARCHITECTURE.md
- **Phase 6 (SSE Integration):** the existing SSE protocol and `NODE_STATUS_MESSAGES` pattern is understood; the change is additive

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All reused libraries are already in production; only new dependency is `pymupdf4llm` (version needs PyPI check); LangGraph sub-graph API is MEDIUM (needs verification against 0.2.64 release notes) |
| Features | HIGH | Feature prioritization directly from FARSIQA component-level scores and FAIR-RAG paper; PROJECT.md constraints confirm anti-feature decisions |
| Architecture | HIGH | Based on direct codebase analysis of `chat_agent.py`, `pipeline_langgraph.py`, `chat_state.py`; all component boundaries and data flow verified against existing patterns |
| Pitfalls | MEDIUM-HIGH | Error distributions from FARSIQA (122 samples) and FAIR-RAG (200 samples) are summarized via implementation guide, not direct paper access; prevention strategies are HIGH confidence from direct codebase knowledge |

**Overall confidence: HIGH**

### Gaps to Address

- **TF-IDF vectorizer persistence:** The existing pipeline uses TF-IDF for sparse embeddings, but it is unclear whether the fitted vectorizer is currently persisted to disk for query-time use. This must be audited in `modules/embedding/embedder.py` before the ingestion script is designed — if the pattern does not exist, it must be built.
- **LangGraph 0.2.64 sub-graph API:** Sub-graph composition (calling a compiled sub-graph from within a parent graph node) was in active development in late 2024. The exact `.invoke()` vs `.astream()` API for nested graphs in version 0.2.64 should be verified against release notes before Phase 5 implementation begins.
- **`pymupdf4llm` version on PyPI:** Version 0.0.17 was current at knowledge cutoff (August 2025). Verify the latest version and any breaking changes before pinning in `requirements.txt`.
- **Sistani PDF ruling-number format:** The chunking strategy assumes numbered rulings (e.g., "Issue 712:") can be detected via pattern matching. The actual format in the 4th edition PDF should be confirmed before the ingestion script's regex anchoring logic is written.

---

## Sources

### Primary (HIGH confidence)
- `documentation/fiqh_related_docs/FAIR_RAG_Fiqh_Implementation_Guide.md` — FAIR-RAG and FARSIQA synthesis; all pipeline design decisions
- `agents/core/chat_agent.py` — existing LangGraph graph structure, fiqh early-exit node, tool registration
- `core/pipeline_langgraph.py` — SSE event protocol, streaming orchestration, NODE_STATUS_MESSAGES
- `agents/state/chat_state.py` — ChatState TypedDict; extension points
- `modules/embedding/embedder.py` — confirmed all-mpnet-base-v2 and TF-IDF usage
- `modules/reranking/reranker.py` — confirmed weighted score merge (not RRF) in existing pipeline
- `.planning/PROJECT.md` — milestone scope, existing classifier weakness noted
- `.planning/codebase/STACK.md` — existing stack audit
- `requirements.txt` — pinned versions of all installed packages

### Secondary (MEDIUM confidence)
- FAIR-RAG paper (via implementation guide) — 200-sample error distribution (32.5% retrieval, 31% generation); RRF k=60 configuration; SEA three-step process
- FARSIQA paper (via implementation guide) — 122-sample Islamic domain error distribution (54.9% generation, 27.9% retrieval); dynamic LLM allocation Table 6; component-level quality scores; 97% negative rejection

### Tertiary (LOW confidence)
- LangGraph 0.2.64 sub-graph composition API — needs verification against official release notes before Phase 5 implementation
- `pymupdf4llm` v0.0.17 — version currency needs PyPI check; capabilities are HIGH confidence, version pinning is LOW

---
*Research completed: 2026-03-23*
*Ready for roadmap: yes*
