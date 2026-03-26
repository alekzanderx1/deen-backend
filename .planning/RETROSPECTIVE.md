# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Fiqh Agentic RAG MVP

**Shipped:** 2026-03-25
**Phases:** 4 | **Plans:** 12 | **Commits:** 78 (2026-03-23 → 2026-03-25)

### What Was Built

- **Ingestion pipeline:** PyMuPDF-based PDF parsing, ruling-boundary chunking (3000 chunks from 2796 Sistani rulings), BM25 sparse + dense embedding, dual Pinecone upsert
- **FAIR-RAG modules:** 6-category classifier, query decomposer, hybrid RRF retriever, evidence filter, SEA (structured evidence assessment), query refiner, answer generator — all unit-tested with mocked LLM
- **Coordinator + sub-graph:** Pure Python FAIR-RAG coordinator (max-3-iteration loop) wrapped in a LangGraph sub-graph invoked by the main ChatAgent, with session isolation via `checkpointer=False`
- **SSE integration:** Fiqh path detection in `pipeline_langgraph.py` with pre-canned status events, token-by-token streaming, and `fiqh_references` SSE event
- **39 requirements satisfied, 5 E2E flows verified, 0 blockers at ship**

### What Worked

- **Phased isolation:** Building modules in isolation (Phase 3) with mocked LLM tests before wiring (Phase 4) caught interface issues early without needing live infra
- **Sub-graph composition:** LangGraph `checkpointer=False` pattern cleanly solved the session isolation requirement without custom state management
- **Dynamic LLM allocation pattern:** Routing gpt-4o-mini for classification/SEA and gpt-4.1 for generation/refinement kept costs low while maintaining quality
- **BM25 JSON serialization:** Persisting BM25 encoder to `data/fiqh_bm25_encoder.json` (not pickle) made it portable across ingestion and query-time environments
- **Fails-open evidence filtering:** Returning all docs when the filter LLM returns an empty list prevented silent context loss

### What Was Inefficient

- **ROADMAP.md progress table went stale:** Phase 2 showed "Not started" and Phase 3 showed "In Progress" at archive time despite all work being complete — the progress table needs updating at each plan completion, not just at phase start
- **Pre-canned SSE status events:** The decision to emit pre-canned `fiqh_refine` events (instead of reading live `FiqhState.status_events`) deferred a real UX accuracy problem to tech debt; the clean solution existed but was skipped for speed
- **Phase 02-01/02-02 SUMMARY.md missing one_liner field:** Two summary files lacked the `one_liner` frontmatter field, causing "One-liner:" placeholders to appear in MILESTONES.md from the CLI tool

### Patterns Established

- **Wrapper node pattern:** `_call_fiqh_subgraph_node` projects `ChatState → FiqhState → ChatState` without sharing keys between schemas — clean interface for sub-graph composition
- **Fails-open for LLM tools:** When LLM output is ambiguous or empty, return all input docs rather than filtering aggressively — better to over-include than silently drop evidence
- **No module-level env var guards for optional features:** Guard inside the function/script, not at import time, to avoid breaking server startup for developers without fiqh indexes configured
- **Mock-first unit tests for pipeline modules:** All FAIR-RAG modules have `unittest.mock.patch` tests that run without LLM or Pinecone — enables fast CI and clear interface contracts

### Key Lessons

1. **Sub-graph state isolation requires explicit design:** LangGraph's MemorySaver checkpointer persists across invocations by default — always set `checkpointer=False` for sub-graphs that must be stateless per request
2. **Chunk count from research papers may not match your PDF:** Expected 1000–1600 chunks per FAIR-RAG paper assumptions; actual PDF produced 3000 chunks (2796 unique rulings). Always verify before committing to index sizing
3. **The "One-liner" frontmatter field in SUMMARY.md is load-bearing:** The milestone CLI depends on it; files missing this field silently produce placeholder text in MILESTONES.md
4. **ROADMAP.md progress table requires active maintenance:** It's not auto-updated by gsd-tools — mark phases complete in the table at the end of each plan execution, not just at phase start

### Cost Observations

- Model mix: Sonnet 4.6 (primary executor across all phases)
- Sessions: ~78 commits over 2 days
- Notable: Dynamic LLM allocation (gpt-4o-mini for 60%+ of inference steps) achieved research-validated 13% cost savings vs all-large allocation; fast iteration over 2 days suggests good session continuity

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 4 | 12 | First milestone; established FAIR-RAG module isolation + sub-graph patterns |

### Cumulative Quality

| Milestone | Tests Added | Modules | Zero-Dep Additions |
|-----------|-------------|---------|-------------------|
| v1.0 | ~55 mock-based unit tests | 8 fiqh modules | modules/fiqh/ (fully isolated from agents layer) |

### Top Lessons (Verified Across Milestones)

1. Build and test modules in isolation before wiring into the graph — Phase 3 isolation caught interface bugs before Phase 4 integration
2. Pre-canned workarounds for SSE/event propagation accrue UX debt — invest in proper event propagation at design time
