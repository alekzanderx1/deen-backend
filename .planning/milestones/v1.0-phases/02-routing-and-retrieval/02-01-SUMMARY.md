---
phase: 02-routing-and-retrieval
plan: "01"
subsystem: fiqh-classifier
tags: [classifier, fiqh, langgraph, chat-state]
dependency_graph:
  requires: []
  provides:
    - modules/fiqh/classifier.py::classify_fiqh_query
    - agents/state/chat_state.py::ChatState.fiqh_category
  affects:
    - agents/state/chat_state.py
tech_stack:
  added: []
  patterns:
    - ChatPromptTemplate inline system prompt (no prompt_templates module)
    - get_classifier_model() for gpt-4o-mini dynamic allocation
    - TypedDict field addition with backward-compatible default
key_files:
  created:
    - modules/fiqh/__init__.py
    - modules/fiqh/classifier.py
  modified:
    - agents/state/chat_state.py
decisions:
  - "Inline SYSTEM_PROMPT in classifier.py instead of prompt_templates module per plan D-01: new standalone classifier, not a port of existing one"
  - "classify_fiqh_query takes no session_id parameter: FAIR-RAG classifier is stateless, no context needed"
  - "fiqh_category placed after is_fiqh in ChatState TypedDict to preserve field ordering for readability"
metrics:
  duration: "1 minute"
  completed_date: "2026-03-24"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 02 Plan 01: Fiqh Classifier and ChatState Extension Summary

**One-liner:** 6-category fiqh query classifier (VALID_OBVIOUS/SMALL/LARGE/REASONER, OUT_OF_SCOPE_FIQH, UNETHICAL) via gpt-4o-mini with ChatState fiqh_category field for FAIR-RAG routing.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create modules/fiqh package with 6-category classifier | d7447f4 | modules/fiqh/__init__.py, modules/fiqh/classifier.py |
| 2 | Extend ChatState with fiqh_category field | 7e7286a | agents/state/chat_state.py |

## What Was Built

### modules/fiqh/classifier.py

Implements `classify_fiqh_query(query: str) -> str` which:
- Uses `get_classifier_model()` (gpt-4o-mini via SMALL_LLM) — never hardcodes a model name
- Routes queries into one of 6 categories using a detailed inline system prompt with examples
- Returns `OUT_OF_SCOPE_FIQH` as safe fallback on any error or unexpected LLM output (never raises)
- Exports `VALID_CATEGORIES` set with exactly 6 strings

### agents/state/chat_state.py

- Added `fiqh_category: str` field to `ChatState` TypedDict (after `is_fiqh`)
- Added `fiqh_category=""` to `create_initial_state()` return dict
- All existing fields (`is_fiqh`, `classification_checked`, etc.) remain unchanged

## Verification Results

```
python -c "from modules.fiqh.classifier import classify_fiqh_query, VALID_CATEGORIES; print(len(VALID_CATEGORIES))"
# Output: 6

python -c "
from agents.state.chat_state import create_initial_state
s = create_initial_state('test query', 'session-123')
assert s['fiqh_category'] == ''
assert s['is_fiqh'] is None
assert s['classification_checked'] == False
print('ChatState OK')
"
# Output: ChatState OK
```

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - classifier logic is fully implemented. The function makes a real LLM call via `get_classifier_model()` and returns a real category string. The `fiqh_category` field defaults to `""` correctly, ready for the Phase 02 routing logic that will populate it.

## Self-Check: PASSED

Files confirmed present:
- modules/fiqh/__init__.py — FOUND
- modules/fiqh/classifier.py — FOUND
- agents/state/chat_state.py — FOUND (modified)

Commits confirmed:
- d7447f4 — FOUND
- 7e7286a — FOUND
