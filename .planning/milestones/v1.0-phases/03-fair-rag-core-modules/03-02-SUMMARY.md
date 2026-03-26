---
phase: 03-fair-rag-core-modules
plan: 02
subsystem: api
tags: [fiqh, fair-rag, llm, langchain, query-refiner, answer-generator, citations, fatwa-disclaimer, tdd]

# Dependency graph
requires:
  - phase: 03-fair-rag-core-modules
    plan: 01
    provides: "modules/fiqh/sea.py — SEAResult, Finding, assess_evidence(); modules/fiqh/filter.py — filter_evidence()"
  - phase: 02-routing-and-retrieval
    provides: "core/chat_models.py — get_generator_model() confirmed function name"
provides:
  - "modules/fiqh/refiner.py — refine_query(original_query, sea_result, prior_queries) -> list[str] using gpt-4.1 (LARGE_LLM)"
  - "modules/fiqh/generator.py — generate_answer(query, docs, sea_result, is_sufficient) -> str using gpt-4.1 (LARGE_LLM)"
  - "tests/test_fiqh_refiner.py — 11 mock-based unit tests (class TestRefineQuery)"
  - "tests/test_fiqh_generator.py — 12 mock-based unit tests (class TestGenerateAnswer)"
affects: [03-03, fair-rag-loop, fiqh-agent-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "refine_query: SEA gaps + confirmed_facts → targeted sub-queries (same fence-stripping pattern as decomposer.py)"
    - "generate_answer: _build_references_section uses re.findall(r'\\[(\\d+)\\]') to extract [n] citation tokens"
    - "FATWA_DISCLAIMER always appended at end; INSUFFICIENT_WARNING conditionally prepended before disclaimer"
    - "TDD: RED (failing import) -> GREEN (implementation) -> commit each phase separately"

key-files:
  created:
    - modules/fiqh/refiner.py
    - modules/fiqh/generator.py
    - tests/test_fiqh_refiner.py
    - tests/test_fiqh_generator.py
  modified: []

key-decisions:
  - "refine_query uses get_generator_model() (gpt-4.1): query refinement requires nuanced cross-referencing per EVID-08"
  - "generate_answer uses get_generator_model() (gpt-4.1): answer synthesis is the highest-stakes step per AGEN-07"
  - "re.findall post-processing for citations: LLM produces [n] inline tokens; parser extracts them to build ## Sources — ensures Sources section is grounded in actual LLM output"
  - "Fail-safe fallback with sistani.org reference: on LLM failure, user gets a non-empty response directing them to authoritative source"

patterns-established:
  - "Evidence citation pattern: _format_evidence() numbers docs 1-N for LLM, _build_references_section() parses [n] tokens back to doc metadata"
  - "Safety-first generation: fatwa disclaimer is not optional — appended in both success and fallback paths"
  - "Fallback chain: try LLM → except → return sistani.org redirect + FATWA_DISCLAIMER"

requirements-completed: [EVID-06, EVID-08, AGEN-01, AGEN-02, AGEN-03, AGEN-04, AGEN-05, AGEN-06, AGEN-07]

# Metrics
duration: 2min
completed: 2026-03-24
---

# Phase 3 Plan 2: Query Refiner and Answer Generator Summary

**Query refiner (gpt-4.1) targeting SEA gaps + confirmed facts, and answer generator (gpt-4.1) with inline [n] citations, ## Sources section, mandatory fatwa disclaimer, and insufficient-evidence warning — 23 mock-based unit tests, all pass**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-24T21:56:57Z
- **Completed:** 2026-03-24T21:59:00Z
- **Tasks:** 2 (each with TDD RED + GREEN commits)
- **Files modified:** 2 created (modules), 2 created (tests)

## Accomplishments

- `refine_query(original_query, sea_result, prior_queries)` — uses gpt-4.1 to generate 1-4 targeted retrieval sub-queries grounded in SEA confirmed_facts and targeting identified gaps; strips markdown code fences; falls back to [original_query] on any LLM error, invalid JSON, or empty list; never raises
- `generate_answer(query, docs, sea_result, is_sufficient)` — uses gpt-4.1 to synthesize answer exclusively from numbered evidence passages with inline [n] citations; builds ## Sources section by parsing [n] tokens via re.findall and mapping to doc metadata; always appends FATWA_DISCLAIMER; appends INSUFFICIENT_WARNING when is_sufficient=False; never raises
- 23 unit tests total (11 for refiner, 12 for generator), all mocked, no network calls

## Task Commits

Each task was committed atomically (TDD = test + impl commits):

1. **Task 1: refiner.py RED** - `8b793a0` (test: add failing tests for refine_query)
2. **Task 1: refiner.py GREEN** - `67c524a` (feat: implement query refiner for FAIR-RAG pipeline)
3. **Task 2: generator.py RED** - `31d5a86` (test: add failing tests for generate_answer)
4. **Task 2: generator.py GREEN** - `647bd58` (feat: implement answer generator for FAIR-RAG pipeline)

_Note: TDD tasks have separate RED (test) and GREEN (implementation) commits_

## Files Created/Modified

- `modules/fiqh/refiner.py` — query refiner, exports `refine_query(original_query, sea_result, prior_queries) -> list[str]`
- `modules/fiqh/generator.py` — answer generator, exports `generate_answer(query, docs, sea_result, is_sufficient) -> str`
- `tests/test_fiqh_refiner.py` — 11 unit tests for refine_query (mock-based, class TestRefineQuery)
- `tests/test_fiqh_generator.py` — 12 unit tests for generate_answer (mock-based, class TestGenerateAnswer)

## Decisions Made

- `refine_query` uses `get_generator_model()` (gpt-4.1): refinement needs nuanced cross-referencing, large model per EVID-08
- `generate_answer` uses `get_generator_model()` (gpt-4.1): answer synthesis is highest-stakes step, large model per AGEN-07
- `re.findall` citation extraction: LLM embeds [n] inline tokens; post-processor extracts them to build Sources — faithful to actual LLM output
- Fail-safe fallback with sistani.org: even on exception, user receives a safe non-empty response

## Deviations from Plan

None — plan executed exactly as written. The implementations match the reference code in the plan spec.

## Issues Encountered

None. 5 pre-existing failures in `test_primer_service.py` are unrelated to this plan and pre-date this work.

## Known Stubs

None. Both modules are fully wired to their LLM models via `core.chat_models`.

## User Setup Required

None — no external service configuration required beyond what was set up in previous phases.

## Next Phase Readiness

- `refine_query` is ready to be consumed by the FAIR-RAG loop orchestration (Plan 3): call when SEA returns INSUFFICIENT and iterations < MAX_ITERATIONS
- `generate_answer` is ready to be called after the final retrieval iteration regardless of sufficiency verdict
- Both modules follow the structural pattern of existing fiqh modules; SEAResult flows through: assess_evidence → refine_query (gaps/confirmed_facts) → generate_answer (sea_result param)
- The complete FAIR-RAG stage sequence is now: classify → decompose → retrieve → filter → assess (SEA) → [refine → retrieve → filter → assess] × max 3 → generate

---
*Phase: 03-fair-rag-core-modules*
*Completed: 2026-03-24*

## Self-Check: PASSED

- FOUND: modules/fiqh/refiner.py
- FOUND: modules/fiqh/generator.py
- FOUND: tests/test_fiqh_refiner.py
- FOUND: tests/test_fiqh_generator.py
- FOUND commit: 8b793a0 (test RED refiner)
- FOUND commit: 67c524a (feat GREEN refiner)
- FOUND commit: 31d5a86 (test RED generator)
- FOUND commit: 647bd58 (feat GREEN generator)
