---
phase: 03-fair-rag-core-modules
plan: 01
subsystem: api
tags: [fiqh, fair-rag, llm, pydantic, langchain, evidence-filter, sea, structured-output]

# Dependency graph
requires:
  - phase: 02-routing-and-retrieval
    provides: "modules/fiqh/classifier.py, modules/fiqh/decomposer.py, modules/fiqh/retriever.py — fiqh pipeline foundation"
  - phase: 02-routing-and-retrieval
    provides: "core/chat_models.py — get_generator_model() and get_classifier_model() function names"
provides:
  - "modules/fiqh/filter.py — filter_evidence(query, docs) -> list[dict] using gpt-4.1 (LARGE_LLM)"
  - "modules/fiqh/sea.py — assess_evidence(query, docs) -> SEAResult using gpt-4o-mini (SMALL_LLM) with structured output"
  - "SEAResult and Finding Pydantic models for FAIR-RAG evidence assessment"
  - "tests/test_fiqh_filter.py and tests/test_fiqh_sea.py — full mock-based unit tests (23 total)"
affects: [03-02, 03-03, fair-rag-loop, fiqh-agent-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LLM-based evidence filter with inclusive bias (fail-open on empty list or error)"
    - "Pydantic structured output via model.with_structured_output(SEAResult)"
    - "TDD: RED (failing import) -> GREEN (implementation) -> commit each phase separately"
    - "Markdown fence stripping pattern: split on backtick-triple, strip 'json' prefix"

key-files:
  created:
    - modules/fiqh/filter.py
    - modules/fiqh/sea.py
    - tests/test_fiqh_filter.py
    - tests/test_fiqh_sea.py
  modified: []

key-decisions:
  - "filter_evidence uses get_generator_model() (gpt-4.1): filtering requires nuanced relevance judgment, large model is appropriate per EVID-02"
  - "assess_evidence uses get_classifier_model() (gpt-4o-mini): structured output classification task, small model is sufficient and cheaper per AGEN-08"
  - "filter_evidence fails open on empty LLM list: empty list = over-aggressive filtering, treat as error per D-11"
  - "filter_evidence fails open when no chunk_ids match: silently ignores unknown IDs, falls back to returning all docs"
  - "SEAResult.verdict is Literal['SUFFICIENT','INSUFFICIENT']: constrains LLM output, enables deterministic routing in FAIR-RAG loop"

patterns-established:
  - "Fail-open pattern: evidence filter returns all input docs on empty list, exception, or no match"
  - "Structured output pattern: chat_models.get_classifier_model().with_structured_output(SEAResult) for SEA"
  - "Module structure: from __future__ import annotations, module-level logger, module-level _prompt, single public function, catch-all except returns safe fallback"

requirements-completed: [EVID-01, EVID-02, EVID-03, EVID-04, EVID-05, AGEN-08]

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 3 Plan 1: Evidence Filter and SEA Summary

**LLM-based evidence filter (gpt-4.1) and Structured Evidence Assessment (gpt-4o-mini with Pydantic structured output) for the FAIR-RAG pipeline — 23 mock-based unit tests, all pass**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T21:49:26Z
- **Completed:** 2026-03-24T21:52:00Z
- **Tasks:** 2 (each with TDD RED + GREEN commits)
- **Files modified:** 2 created (modules), 2 created (tests)

## Accomplishments
- `filter_evidence(query, docs)` — batch LLM call using gpt-4.1 to remove clearly irrelevant documents with inclusive bias; returns all docs on empty list, parse error, or any exception
- `assess_evidence(query, docs) -> SEAResult` — uses gpt-4o-mini with `with_structured_output(SEAResult)` to decompose query into findings, check each against evidence, return SUFFICIENT/INSUFFICIENT verdict plus confirmed facts and gaps
- `SEAResult` and `Finding` Pydantic models with `Literal["SUFFICIENT", "INSUFFICIENT"]` verdict field
- 23 unit tests across both modules (10 for filter, 13 for SEA), all mocked, no network calls

## Task Commits

Each task was committed atomically (TDD = test + impl commits):

1. **Task 1: filter.py RED** - `ef1a6f6` (test: add failing tests for filter_evidence)
2. **Task 1: filter.py GREEN** - `6705466` (feat: implement LLM-based evidence filter)
3. **Task 2: sea.py RED** - `a3a1b2b` (test: add failing tests for assess_evidence)
4. **Task 2: sea.py GREEN** - `6fe555e` (feat: implement Structured Evidence Assessment)

_Note: TDD tasks have separate RED (test) and GREEN (implementation) commits_

## Files Created/Modified
- `modules/fiqh/filter.py` — LLM-based evidence filter, exports `filter_evidence(query, docs) -> list[dict]`
- `modules/fiqh/sea.py` — Structured Evidence Assessment, exports `SEAResult`, `Finding`, `assess_evidence(query, docs) -> SEAResult`
- `tests/test_fiqh_filter.py` — 10 unit tests for filter_evidence (mock-based, class TestFilterEvidence)
- `tests/test_fiqh_sea.py` — 13 unit tests including TestSEAModels and TestAssessEvidence (mock-based)

## Decisions Made
- `filter_evidence` uses `get_generator_model()` (gpt-4.1): filtering requires nuanced relevance judgment, large model per EVID-02
- `assess_evidence` uses `get_classifier_model()` (gpt-4o-mini): structured output classification, small model per AGEN-08
- Fail-open on empty LLM keep list: empty list = over-aggressive filtering, D-11 decision
- `Literal["SUFFICIENT", "INSUFFICIENT"]` verdict type: constrains output, deterministic routing downstream

## Deviations from Plan

None — plan executed exactly as written. The implementations match the reference code in the plan spec line-for-line.

## Issues Encountered

None. Test runner executed cleanly. The 5 pre-existing failures in `test_primer_service.py` are unrelated to this plan and pre-date this work.

## Known Stubs

None. Both modules are fully wired to their LLM models via `core.chat_models`.

## User Setup Required

None — no external service configuration required beyond what was set up in previous phases.

## Next Phase Readiness
- `filter_evidence` and `assess_evidence` are ready to be consumed by Phase 3 Plan 2 (iterative refiner) and Plan 3 (FAIR-RAG loop orchestration)
- Both modules follow the structural pattern of existing fiqh modules; no special import adjustments needed
- SEAResult.gaps feeds directly into the refiner query construction in Plan 2
- SEAResult.confirmed_facts feeds into the faithful answer generator in Plan 3

---
*Phase: 03-fair-rag-core-modules*
*Completed: 2026-03-24*

## Self-Check: PASSED

- FOUND: modules/fiqh/filter.py
- FOUND: modules/fiqh/sea.py
- FOUND: tests/test_fiqh_filter.py
- FOUND: tests/test_fiqh_sea.py
- FOUND commit: ef1a6f6 (test RED filter)
- FOUND commit: 6705466 (feat GREEN filter)
- FOUND commit: a3a1b2b (test RED sea)
- FOUND commit: 6fe555e (feat GREEN sea)
