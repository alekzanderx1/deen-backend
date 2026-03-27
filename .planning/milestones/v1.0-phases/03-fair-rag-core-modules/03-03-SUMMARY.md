---
phase: 03-fair-rag-core-modules
plan: 03
subsystem: api
tags: [fiqh, fair-rag, coordinator, orchestrator, iterative-retrieval, tdd]

# Dependency graph
requires:
  - phase: 03-fair-rag-core-modules
    plan: 01
    provides: "modules/fiqh/filter.py — filter_evidence(); modules/fiqh/sea.py — assess_evidence(), SEAResult"
  - phase: 03-fair-rag-core-modules
    plan: 02
    provides: "modules/fiqh/refiner.py — refine_query(); modules/fiqh/generator.py — generate_answer()"
  - phase: 02-routing-and-retrieval
    provides: "modules/fiqh/retriever.py — retrieve_fiqh_documents()"
provides:
  - "modules/fiqh/fair_rag.py — run_fair_rag(query: str) -> str — FAIR-RAG coordinator"
  - "Phase 4 integration point: import run_fair_rag from a Phase 4 graph node"
  - "tests/test_fair_rag.py — 9 mock-based unit tests (class TestRunFairRag)"
affects: [phase-04-agent-integration, fiqh-langgraph-node]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FAIR-RAG coordinator: range(1,4) loop with accumulator dict for chunk_id deduplication"
    - "Early exit on SEA verdict SUFFICIENT; refine_query called only on iterations 1 and 2"
    - "docs_for_generation = filtered_docs if filtered_docs else all_docs (fail-open for generation)"
    - "Never-raises pattern: outer try/except returns safe error fallback string with sistani.org redirect"
    - "TDD: RED (ModuleNotFoundError) -> GREEN (all 9 tests pass)"

key-files:
  created:
    - modules/fiqh/fair_rag.py
    - tests/test_fair_rag.py
  modified: []

key-decisions:
  - "run_fair_rag uses range(1, 4): enforces max 3 iterations per D-23 and EVID-07 (research shows diminishing returns beyond iteration 3)"
  - "Accumulate all_docs across iterations, deduplicate by chunk_id before filter/assess: ensures each iteration builds on prior evidence"
  - "refine_query called only when verdict=INSUFFICIENT and iteration < 3: avoids wasted call on final iteration where no next retrieval will occur"
  - "generate_answer receives filtered_docs if non-empty, else all_docs: fail-open for generation step"
  - "No LangGraph imports in fair_rag.py: pure Python module per D-02 (Phase 3 builds modules, Phase 4 integrates into graph)"

patterns-established:
  - "Coordinator pattern: thin orchestrator wires together modules without business logic of its own"
  - "Accumulator + deduplication: seen_ids set tracks chunk_ids across iterations to prevent redundant evidence"
  - "Error fallback with redirect: on total failure, user receives actionable sistani.org reference"

requirements-completed: [EVID-07]

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 3 Plan 3: FAIR-RAG Coordinator Summary

**Pure Python FAIR-RAG coordinator wiring all Phase 3 modules (filter, SEA, refiner, generator) with Phase 2 retriever into a max-3-iteration retrieve-filter-assess-refine loop — 9 mock-based unit tests, all pass**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T22:02:21Z
- **Completed:** 2026-03-24T22:05:30Z
- **Tasks:** 1 (with TDD RED + GREEN commits)
- **Files modified:** 1 created (module), 1 created (tests)

## Accomplishments

- `run_fair_rag(query: str) -> str` — orchestrates the FAIR-RAG iterative loop: retrieve → deduplicate → filter → assess (SEA) → [refine → repeat] x max 3 → generate_answer
- Doc accumulation across iterations: `all_docs` accumulator + `seen_ids` set ensures chunk_ids never appear twice in the evidence set passed to filter/assess
- Early exit on SUFFICIENT: loop breaks at iteration 1 if SEA is satisfied, avoiding unnecessary retrieval
- Max 3 iterations enforced via `range(1, 4)`: `refine_query` is called only on iterations 1 and 2 (never on the final iteration)
- `is_sufficient` passed faithfully to `generate_answer`: `True` when last SEA verdict was SUFFICIENT, `False` when all 3 iterations yield INSUFFICIENT
- Never raises: outer `try/except` returns safe error fallback with sistani.org redirect on total failure
- 9 unit tests covering all behavioral requirements, all mocked, no network calls

## Task Commits

Each TDD phase committed separately:

1. **Task 1: fair_rag.py RED** - `22b7f7a` (test: add failing tests for run_fair_rag TDD RED)
2. **Task 1: fair_rag.py GREEN** - `cc3cb63` (feat: implement FAIR-RAG coordinator run_fair_rag)

_Note: TDD tasks have separate RED (test) and GREEN (implementation) commits_

## Files Created/Modified

- `modules/fiqh/fair_rag.py` — FAIR-RAG coordinator, exports `run_fair_rag(query: str) -> str`
- `tests/test_fair_rag.py` — 9 unit tests for run_fair_rag (mock-based, class TestRunFairRag)

## Decisions Made

- `range(1, 4)` loop enforces max 3 iterations per D-23 and EVID-07; research papers show no improvement beyond iteration 3
- `refine_query` skipped on iteration 3: no next retrieval will occur, avoiding a wasted LLM call
- `filtered_docs if filtered_docs else all_docs` for generation: if filter removes everything (extreme edge case), all accumulated docs are used rather than passing empty list to generator
- No LangGraph imports: per D-02, Phase 3 modules are pure Python; Phase 4 wraps them into graph nodes

## Deviations from Plan

None — plan executed exactly as written. Implementation matches reference code in the plan spec line-for-line. The one minor difference: the docstring comment was updated to remove the literal word "LangGraph" to satisfy the acceptance criterion `grep -c "LangGraph" modules/fiqh/fair_rag.py == 0` (replaced with "Phase 4 graph node").

## Issues Encountered

None. 5 pre-existing failures in `test_primer_service.py` are unrelated to this plan and pre-date this work.

## Known Stubs

None. `run_fair_rag` is fully wired to all 5 dependency modules via direct imports.

## User Setup Required

None — no external service configuration required beyond what was established in previous phases.

## Phase 3 Completion

All Phase 3 plans are now complete. The full FAIR-RAG pipeline is built as pure Python modules:

1. **Plan 01**: `filter_evidence` (gpt-4.1) + `assess_evidence` (gpt-4o-mini, SEAResult)
2. **Plan 02**: `refine_query` (gpt-4.1) + `generate_answer` (gpt-4.1, citations, disclaimer)
3. **Plan 03**: `run_fair_rag` coordinator — wires all modules, enforces max-3-iteration loop

Phase 4 integration: `from modules.fiqh.fair_rag import run_fair_rag` — call from a Phase 4 LangGraph node.

Full Phase 3 test suite: 55 tests (23 filter+SEA + 23 refiner+generator + 9 coordinator), all pass.

---
*Phase: 03-fair-rag-core-modules*
*Completed: 2026-03-24*

## Self-Check: PASSED

- FOUND: modules/fiqh/fair_rag.py
- FOUND: tests/test_fair_rag.py
- FOUND commit: 22b7f7a (test RED fair_rag)
- FOUND commit: cc3cb63 (feat GREEN fair_rag)
