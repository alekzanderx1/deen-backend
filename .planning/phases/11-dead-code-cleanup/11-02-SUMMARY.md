---
phase: 11
plan: 02
subsystem: tests
tags: [test-mocks, embedding-service, cleanup, huggingface]
dependency_graph:
  requires: [11-01]
  provides: [clean-test-suite]
  affects: [tests/test_embedding_service.py]
tech_stack:
  added: []
  patterns: [mock-embedder-fixture, getDenseEmbedder-patch]
key_files:
  modified: [tests/test_embedding_service.py]
decisions:
  - mock_embedder fixture patches getDenseEmbedder at services.embedding_service.getDenseEmbedder — consistent with how the service imports and calls it
metrics:
  duration: "~2 minutes"
  completed: "2026-04-10T16:14:44Z"
  tasks_completed: 5
  files_modified: 1
---

# Phase 11 Plan 02: Update Stale Test Mocks + Verify Clean State Summary

**One-liner:** Replace OpenAI-based test fixtures with HuggingFace mock_embedder; all 30 embedding service tests pass against 768-dim vectors.

## What Was Done

Fixed `tests/test_embedding_service.py` to match the updated `EmbeddingService` implementation (which now uses `getDenseEmbedder()` from HuggingFace, 768-dim, instead of OpenAI client, 1536-dim).

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| 1 | Replace `mock_openai_client` fixture with `mock_embedder` | Done |
| 2 | Replace `embedding_service` fixture (patch `getDenseEmbedder`) | Done |
| 3 | Update `TestEmbeddingGeneration` assertions (1536 → 768, method calls) | Done |
| 4 | Remove `mock_openai_client` param from 4 test method signatures | Done |
| 5 | Update 1536-dim vector literals in `TestSimilaritySearch` to 768 | Done |

## Verification Results

```
# Test suite: 30/30 passed
pytest tests/test_embedding_service.py -v
→ 30 passed in 4.89s

# No 'from openai' in app code
grep -r "from openai" . --include="*.py" | grep -v "venv/|__pycache__|worktrees/"
→ 0 lines

# No OPENAI_API_KEY in app code
grep -r "OPENAI_API_KEY" . --include="*.py" | grep -v "venv/|__pycache__|worktrees/|tests/|scripts/"
→ 0 lines

# openai/langchain-openai/voyageai absent from requirements.txt
grep -i "^openai|^langchain-openai|^voyageai" requirements.txt
→ 0 lines
```

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Out-of-Scope Pre-existing Failures

During full test suite run (`pytest tests/ -q --ignore=tests/db ...`), 6 failures were found that pre-existed before plan 11-02 on the `feature/supabase-migration` branch:

- `tests/test_fiqh_integration.py::TestFiqhRouting::test_out_of_scope_routes_to_exit` — routing behavior test
- `tests/test_primer_service.py` — 5 primer service tests

These failures are unrelated to the OpenAI mock cleanup. Per scope boundary rules, they were logged as deferred items and not fixed.

Also, `tests/test_agentic_streaming_pipeline.py` fails to collect due to missing `sys.path.insert(0, ...)` — also pre-existing.

## Commits

| Hash | Message |
|------|---------|
| 9c46271 | feat(11-02): update test_embedding_service mocks to HuggingFace; verify clean state |

## Self-Check: PASSED

- [x] `tests/test_embedding_service.py` modified — confirmed
- [x] Commit `9c46271` exists
- [x] 30 tests pass
- [x] All app code clean of OpenAI direct imports
