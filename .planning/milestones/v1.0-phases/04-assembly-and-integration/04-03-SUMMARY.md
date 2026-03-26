---
phase: 04-assembly-and-integration
plan: 03
subsystem: core/pipeline
tags: [fiqh, sse, streaming, fair-rag, pipeline, integration, tests]
dependency_graph:
  requires:
    - 04-01 (FiqhState, ChatState fiqh fields, format_fiqh_references_as_json)
    - 04-02 (FiqhAgent sub-graph, ChatAgent _route_after_fiqh_check, fiqh_filtered_docs/fiqh_sea_result in ChatState)
    - 03-03 (run_fair_rag coordinator — modules/fiqh/*)
    - 03-02 (modules/fiqh/generator.py — _prompt, _format_evidence, _build_references_section)
  provides:
    - core/pipeline_langgraph.py — fiqh SSE path (status events, token streaming, fiqh_references)
    - tests/test_fiqh_integration.py — integration tests for fiqh SSE path and routing
  affects:
    - /chat/stream/agentic endpoint — now emits fiqh-specific SSE events for fiqh queries
tech_stack:
  added: []
  patterns:
    - Fiqh path detection via fiqh_category in VALID_FIQH_CATEGORIES constant
    - Lazy import of fiqh modules inside streaming path (avoids circular imports at module load)
    - Pre-canned stage SSE status events emitted synchronously after sub-graph completes
    - Token-by-token streaming via fiqh-specific ChatPromptTemplate (_prompt | model).stream()
    - Post-processing order: token chunks -> references section -> disclaimer -> response_end -> fiqh_references
key_files:
  created:
    - tests/test_fiqh_integration.py
  modified:
    - core/pipeline_langgraph.py
decisions:
  - Pre-canned fiqh stage status events: sub-graph runs as a black box; pipeline emits pre-canned messages rather than reading FiqhState.status_events which are not propagated to ChatState
  - Lazy imports inside fiqh path block: avoids circular import at module load time for modules.fiqh.generator and core.utils
  - VALID_FIQH_CATEGORIES constant defined at module level: reuses same set as chat_agent._route_after_fiqh_check to ensure path detection consistency
  - Fallback message emitted without LLM call when fiqh_filtered_docs is empty: avoids LLM hallucination when no evidence is available
metrics:
  duration_minutes: 4
  completed_date: "2026-03-24"
  tasks_completed: 2
  files_modified: 2
---

# Phase 4 Plan 3: SSE Streaming Integration for Fiqh Path Summary

Fiqh SSE path wired in `core/pipeline_langgraph.py`: detects VALID_FIQH_CATEGORIES, emits per-stage status events, streams the fiqh answer token-by-token using `modules/fiqh/generator._prompt`, emits `fiqh_references` SSE event, with existing hadith/non-fiqh path unchanged.

## What Was Built

### Task 1: Extend core/pipeline_langgraph.py with fiqh SSE path (commit: 211d83c)

Extended `core/pipeline_langgraph.py` with three targeted changes:

1. **Extended NODE_STATUS_MESSAGES** — added entries for `fiqh_subgraph`, `generate_fiqh_response`, `fiqh_decompose`, `fiqh_retrieve`, `fiqh_filter`, `fiqh_assess`, `fiqh_refine`

2. **Added VALID_FIQH_CATEGORIES constant** — `{"VALID_OBVIOUS", "VALID_SMALL", "VALID_LARGE", "VALID_REASONER"}` at module level for consistent fiqh path detection

3. **Replaced streaming block with fiqh-aware branching** — `if final_state.get("fiqh_category") in VALID_FIQH_CATEGORIES:` detects the fiqh path:
   - Emits pre-canned stage status events for each FAIR-RAG pipeline stage
   - Streams answer token-by-token via `fiqh_prompt | model` chain
   - Post-processes: appends `## Sources` section, insufficient warning, fatwa disclaimer as additional `response_chunk` events
   - Persists to conversation history via `chat_persistence_service`
   - Emits `fiqh_references` SSE event with book/chapter/section/ruling_number per doc
   - Empty docs path: emits hardcoded fallback referencing sistani.org without LLM call
   - `else:` branch preserves existing hadith/non-fiqh streaming path completely unchanged

### Task 2: Write integration tests for fiqh SSE path (commit: f834eae)

Created `tests/test_fiqh_integration.py` with 8 mock-based tests:

**TestFiqhSSEPath (5 tests):**
- `test_fiqh_path_emits_stage_status_events` — verifies all 5 fiqh stage status events are emitted
- `test_fiqh_path_emits_response_chunks` — verifies response_chunk and response_end events
- `test_fiqh_path_emits_fiqh_references_event` — verifies fiqh_references event with correct metadata fields
- `test_non_fiqh_path_no_fiqh_references_event` — verifies isolation (non-fiqh never emits fiqh_references)
- `test_fiqh_path_empty_docs_returns_fallback` — verifies fallback message, no LLM call, no fiqh_references

**TestFiqhRouting (3 tests):**
- `test_valid_fiqh_routes_to_fiqh` — VALID_OBVIOUS/SMALL/LARGE/REASONER all route to "fiqh"
- `test_out_of_scope_routes_to_exit` — OUT_OF_SCOPE_FIQH/UNETHICAL route to "exit"
- `test_empty_category_routes_to_continue` — empty category routes to "continue"

All 8 tests pass. No real LLM, Pinecone, or Redis calls.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — no stubs or hardcoded placeholders in the fiqh SSE path. The fallback message for empty docs is intentional behavior (not a stub) as documented in the plan.

## Pre-existing Test Failures (out of scope)

`tests/test_primer_service.py` has 5 pre-existing failures unrelated to this plan (primer service embedding quality logic). These existed on the shawn-dev base before this plan's execution and are out of scope for this plan.

## Self-Check: PASSED

- core/pipeline_langgraph.py: FOUND
- tests/test_fiqh_integration.py: FOUND
- Commit 211d83c: FOUND
- Commit f834eae: FOUND
- VALID_FIQH_CATEGORIES constant: FOUND (line 48)
- fiqh_references SSE event: FOUND (line 230)
- hadith_references SSE event: FOUND (line 294)
- quran_references SSE event: FOUND (line 298)
- TestFiqhSSEPath: FOUND (5 tests, all pass)
- TestFiqhRouting: FOUND (3 tests, all pass)
