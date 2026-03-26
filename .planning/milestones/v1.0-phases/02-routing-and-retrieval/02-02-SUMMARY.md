---
phase: 02-routing-and-retrieval
plan: "02"
subsystem: fiqh-decomposer
tags: [decomposer, fiqh, unit-tests, classifier-tests, gpt-4o-mini]
dependency_graph:
  requires:
    - modules/fiqh/classifier.py::classify_fiqh_query
    - core/chat_models.py::get_classifier_model
  provides:
    - modules/fiqh/decomposer.py::decompose_query
    - tests/test_fiqh_classifier.py
    - tests/test_fiqh_decomposer.py
  affects: []
tech_stack:
  added: []
  patterns:
    - ChatPromptTemplate inline system prompt (mirrors classifier.py structure)
    - get_classifier_model() for gpt-4o-mini dynamic allocation (QPRO-03)
    - JSON fence stripping via split("```") before json.loads()
    - unittest.mock.patch for LLM isolation in unit tests
key_files:
  created:
    - modules/fiqh/decomposer.py
    - tests/test_fiqh_classifier.py
    - tests/test_fiqh_decomposer.py
  modified: []
decisions:
  - "decompose_query uses get_classifier_model() (gpt-4o-mini) not get_generator_model() per QPRO-03: cost efficiency for decomposition step"
  - "Fallback returns [query] (original as single item) not [] on any parse/exception: caller always gets at least one retrieval query"
  - "Cap at sub_queries[:4] applied after filtering blanks: ensures max 4 semantically independent sub-queries"
metrics:
  duration: "1 minute"
  completed_date: "2026-03-24"
  tasks_completed: 2
  files_created: 3
  files_modified: 0
---

# Phase 02 Plan 02: Query Decomposer and Unit Tests Summary

**One-liner:** Fiqh query decomposer using gpt-4o-mini that returns 1-4 keyword-rich sub-queries with JSON fence stripping and [query] fallback, plus 21 mocked unit tests for both decomposer and classifier modules.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create modules/fiqh/decomposer.py | 288d263 | modules/fiqh/decomposer.py |
| 2 | Write unit tests for classifier and decomposer | 069003f | tests/test_fiqh_classifier.py, tests/test_fiqh_decomposer.py |

## What Was Built

### modules/fiqh/decomposer.py

Implements `decompose_query(query: str) -> list[str]` which:
- Uses `get_classifier_model()` (gpt-4o-mini via SMALL_LLM) per QPRO-03 — never hardcodes a model name
- Decomposes any fiqh query into 1-4 keyword-rich sub-queries via a detailed inline system prompt with Arabic/Persian terminology examples
- Strips markdown code fences (`\`\`\`json`) before `json.loads()` to handle LLM wrapping behavior
- Returns `[query]` as fallback on any parse error, empty list, or exception — never empty, never raises
- Caps result at `sub_queries[:4]` after filtering blank strings

### tests/test_fiqh_classifier.py

13 tests (5 named functions + 8 parametrize cases) covering:
- `VALID_CATEGORIES` set contains exactly 6 expected strings
- All 6 category labels returned correctly from mocked LLM output
- Case-insensitive matching (lowercase LLM output normalised to uppercase)
- Whitespace trimming on LLM response
- `OUT_OF_SCOPE_FIQH` fallback on unknown LLM output
- `OUT_OF_SCOPE_FIQH` fallback on exception
- Never raises guarantee

### tests/test_fiqh_decomposer.py

8 tests covering:
- Single-part query returns list of length 1 with expected terminology
- Multi-part query returns multiple sub-queries
- Cap at 4 sub-queries when LLM returns 5
- `[query]` fallback on JSON parse error
- `[query]` fallback on empty list from LLM
- `[query]` fallback on LLM exception
- Markdown code fence stripping (`\`\`\`json...\`\`\``)
- Never returns empty list guarantee

## Verification Results

```
pytest tests/test_fiqh_classifier.py tests/test_fiqh_decomposer.py -v
# 21 passed in 0.17s

python -c "
from modules.fiqh.classifier import classify_fiqh_query
from modules.fiqh.decomposer import decompose_query
print('both modules importable')
"
# both modules importable
```

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - decomposer logic is fully implemented. The function makes a real LLM call via `get_classifier_model()` and processes the JSON response. All test mocks are intentional test isolation, not production stubs.

## Self-Check: PASSED

Files confirmed present:
- modules/fiqh/decomposer.py — FOUND
- tests/test_fiqh_classifier.py — FOUND
- tests/test_fiqh_decomposer.py — FOUND

Commits confirmed:
- 288d263 — FOUND
- 069003f — FOUND
