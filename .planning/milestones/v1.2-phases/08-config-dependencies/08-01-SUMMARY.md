---
phase: 08-config-dependencies
plan: "01"
subsystem: core-config
tags: [config, anthropic, voyage-ai, credentials, migration]
dependency_graph:
  requires: []
  provides: [ANTHROPIC_API_KEY, VOYAGE_API_KEY, LARGE_LLM-default, SMALL_LLM-default, EMBEDDING_MODEL-default, EMBEDDING_DIMENSIONS-default]
  affects: [core/config.py, all-importers-of-core-config]
tech_stack:
  added: []
  patterns: [env-var-guard, fail-fast-startup]
key_files:
  created: []
  modified:
    - core/config.py
decisions:
  - "ANTHROPIC_API_KEY and VOYAGE_API_KEY replace OPENAI_API_KEY as required startup guards"
  - "LARGE_LLM defaults to claude-sonnet-4-6; SMALL_LLM defaults to claude-haiku-4-5-20251001"
  - "EMBEDDING_MODEL defaults to voyage-4 (1024 dims) replacing text-embedding-3-small (1536 dims)"
metrics:
  duration: "1 minute"
  completed: "2026-04-09T17:30:41Z"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 1
---

# Phase 08 Plan 01: Config + Credentials Summary

## One-liner

Replaced OpenAI startup guard with Anthropic + Voyage AI credential guards and updated all LLM/embedding defaults to Claude and Voyage AI values in `core/config.py`.

## What Was Done

Updated `core/config.py` with four targeted changes as the foundational step for the v1.2 Claude Migration:

1. **API key block**: Replaced `OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")` with two lines — `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY`.
2. **Startup guard**: Updated from `if not OPENAI_API_KEY or not PINECONE_API_KEY` to `if not ANTHROPIC_API_KEY or not VOYAGE_API_KEY or not PINECONE_API_KEY` with an updated error message naming all three required keys.
3. **LLM defaults**: `LARGE_LLM` now defaults to `claude-sonnet-4-6`; `SMALL_LLM` to `claude-haiku-4-5-20251001`.
4. **Embedding defaults**: `EMBEDDING_MODEL` now defaults to `voyage-4`; `EMBEDDING_DIMENSIONS` to `1024`.
5. **Docstring correction**: Updated `validate_supabase_config` comment to reference `ANTHROPIC_API_KEY/VOYAGE_API_KEY/PINECONE_API_KEY` guards.

## Verification Results

Both verification checks passed:
- Full assertions script: all 7 assertions passed (ANTHROPIC_API_KEY, VOYAGE_API_KEY, LARGE_LLM, SMALL_LLM, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, no OPENAI_API_KEY)
- Guard fires correctly: `ValueError` raised with message mentioning `ANTHROPIC_API_KEY` when key is absent

## Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Replace OPENAI_API_KEY guard with ANTHROPIC + VOYAGE guard; update defaults | 79107a8 | core/config.py |

## Deviations from Plan

None — plan executed exactly as written. The comment update to `validate_supabase_config` docstring was listed in the action section and was applied.

## Known Stubs

None. This plan modifies only configuration defaults. No data flows to UI from these changes.

## Important Notes for Downstream Phases

After this change, 7 files import `OPENAI_API_KEY` from `core.config` and will raise `ImportError`:
- `core/chat_models.py`
- `agents/core/chat_agent.py`
- `modules/classification/classifier.py`
- `modules/enhancement/enhancer.py`
- `modules/generation/stream_generator.py`
- `modules/generation/generator.py`
- `services/embedding_service.py`

This is expected and intentional — those imports are fixed in Phases 9 and 11.

## Self-Check: PASSED

- core/config.py exists and contains all required changes
- Commit 79107a8 exists in git log
- All acceptance criteria satisfied:
  - `ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")` present
  - `VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")` present
  - `if not ANTHROPIC_API_KEY or not VOYAGE_API_KEY or not PINECONE_API_KEY:` present
  - `LARGE_LLM = os.getenv("LARGE_LLM", "claude-sonnet-4-6")` present
  - `SMALL_LLM = os.getenv("SMALL_LLM", "claude-haiku-4-5-20251001")` present
  - `EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-4")` present
  - `EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))` present
  - `OPENAI_API_KEY` NOT present in core/config.py
  - `text-embedding-3-small` NOT present in core/config.py
  - `"1536"` NOT present in core/config.py
