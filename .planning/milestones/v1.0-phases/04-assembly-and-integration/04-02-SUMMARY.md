---
phase: 04-assembly-and-integration
plan: 02
subsystem: agents
tags: [fiqh, langgraph, subgraph, routing, classification, fair-rag]
dependency_graph:
  requires:
    - 04-01 (FiqhState, ChatState fiqh fields)
    - 03-03 (run_fair_rag coordinator — modules/fiqh/*)
    - 02-01 (modules/fiqh/classifier.py — 6-category classifier)
  provides:
    - agents/fiqh/fiqh_graph.py — compiled FiqhAgent sub-graph
    - agents/core/chat_agent.py — updated with 3-path routing and fiqh nodes
  affects:
    - core/pipeline_langgraph.py (Plan 03 will consume fiqh_filtered_docs/fiqh_sea_result from ChatState)
tech_stack:
  added: []
  patterns:
    - LangGraph sub-graph composition (checkpointer=False for session isolation)
    - LangGraph node returning dict (partial state update) vs full state
    - Wrapper node pattern for projecting ChatState -> FiqhState -> ChatState
key_files:
  created:
    - agents/fiqh/__init__.py
    - agents/fiqh/fiqh_graph.py
  modified:
    - agents/core/chat_agent.py
decisions:
  - "checkpointer=False on fiqh_subgraph: stateless per-invocation; prevents cross-session state leakage (Pitfall 2)"
  - "Wrapper node pattern: _call_fiqh_subgraph_node projects ChatState to fresh FiqhState dict and maps results back; shares no keys between state schemas"
  - "3-path routing: VALID_* categories route to fiqh sub-graph; OUT_OF_SCOPE_FIQH/UNETHICAL route to check_early_exit with LLM-generated personalized rejection; all others continue to agent"
  - "LLM-generated rejection messages (D-12): get_classifier_model() (gpt-4o-mini) generates personalized 1-2 sentence rejections based on query context and category"
  - "Node functions return dict (not full state): aligns with LangGraph partial-update pattern; avoids stale-reference issues"
  - "Pre-existing test_primer_service.py failure: pre-exists in shawn-dev branch, unrelated to this plan"
metrics:
  duration: "4 minutes"
  completed_date: "2026-03-25"
  tasks_completed: 2
  files_changed: 3
---

# Phase 4 Plan 02: FiqhAgent Sub-Graph and ChatAgent Integration Summary

Wired Phase 3 FAIR-RAG module functions into a LangGraph sub-graph and updated ChatAgent with 6-category classifier, 3-path routing, sub-graph invocation wrapper, non-streaming fiqh generation node, and LLM-personalized rejection messages.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Create agents/fiqh/fiqh_graph.py — compiled FiqhAgent sub-graph | 28fca5f | agents/fiqh/__init__.py, agents/fiqh/fiqh_graph.py |
| 2 | Update agents/core/chat_agent.py — replace classifier, expand routing, add sub-graph and generation nodes | a6255d8 | agents/core/chat_agent.py |

## What Was Built

### agents/fiqh/fiqh_graph.py (new)

Compiled LangGraph sub-graph implementing the FAIR-RAG iterative loop:

- 5 nodes: `decompose` → `retrieve` → `filter` → `assess` → conditional: `refine` (loops back to `retrieve`) or `END`
- Max 3 iterations enforced via `FiqhState.iteration` counter incremented in `_retrieve_node`
- `checkpointer=False` for stateless per-invocation execution (session isolation)
- Each node appends `{"step": ..., "message": ...}` to `status_events` for Plan 03 SSE surfacing
- Doc deduplication by `chunk_id` across iterations in `_retrieve_node`
- All nodes fail-open: errors are logged and execution continues with best available state

### agents/core/chat_agent.py (modified)

Six targeted changes:

1. **_build_graph**: Added `fiqh_subgraph` and `generate_fiqh_response` node registrations plus edge wiring
2. **_fiqh_classification_node**: Replaced binary classifier with 6-category `classify_fiqh_query` (1-arg, no session_id)
3. **_route_after_fiqh_check**: Expanded from 2 paths to 3 — `fiqh`/`exit`/`continue`
4. **_check_early_exit_node**: Replaced hardcoded `EARLY_EXIT_FIQH` with LLM-generated personalized rejections via `get_classifier_model()`
5. **_call_fiqh_subgraph_node** (new): Wrapper that projects `ChatState` → fresh `FiqhState`, invokes `fiqh_subgraph.invoke()`, maps `accumulated_docs`/`sea_result` back to `ChatState`
6. **_generate_fiqh_response_node** (new): Non-streaming fiqh generation using `modules/fiqh/generator._prompt`, formats filtered docs with inline [n] citations, appends `## Sources`, insufficient-evidence warning, and fatwa disclaimer

## Routing Flow After This Plan

```
fiqh_classification
  ├── VALID_* category → fiqh_subgraph → generate_fiqh_response → END
  ├── OUT_OF_SCOPE_FIQH / UNETHICAL → check_early_exit (LLM rejection) → END
  └── other / not fiqh → agent (existing hadith/Quran pipeline) → ...
```

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `checkpointer=False` on sub-graph | Prevents `MemorySaver` from leaking state between user sessions (Pitfall 2 from RESEARCH.md) |
| Wrapper node pattern | ChatState and FiqhState share no keys; clean projection avoids TypedDict conflicts |
| Dict return from nodes | LangGraph merges partial updates; returning full state creates stale-reference bugs when multiple nodes update same fields |
| LLM-generated rejection (D-12) | Personalized 1-2 sentence responses feel less robotic than static text; uses cheap gpt-4o-mini classifier model |
| 3-path routing | VALID_* categories route to evidence pipeline; rejected categories get polite explanation; non-fiqh continues through existing agent |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes

- Pre-existing test failure in `tests/test_primer_service.py::TestFetchUserSignals::test_fetch_signals_with_embeddings` — confirmed pre-existing in shawn-dev baseline, unrelated to this plan's changes. All 167 other tests pass.
- Merged `shawn-dev` into worktree via fast-forward before implementation (worktree was on `origin/main`, missing all Phase 1-4.01 prerequisite code).

## Known Stubs

None. The `_generate_fiqh_response_node` is fully wired to `modules/fiqh/generator._prompt` and `fiqh_filtered_docs` from the sub-graph. The streaming path (Plan 03) bypasses this node and streams tokens directly — that path is documented in node docstring.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| agents/fiqh/__init__.py | FOUND |
| agents/fiqh/fiqh_graph.py | FOUND |
| agents/core/chat_agent.py | FOUND |
| .planning/phases/04-assembly-and-integration/04-02-SUMMARY.md | FOUND |
| commit 28fca5f (Task 1) | FOUND |
| commit a6255d8 (Task 2) | FOUND |
