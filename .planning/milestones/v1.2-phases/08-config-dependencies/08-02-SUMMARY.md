---
phase: 08-config-dependencies
plan: "02"
subsystem: packaging
tags: [dependencies, configuration, anthropic, voyage-ai, openai-removal]
dependency_graph:
  requires: []
  provides: [requirements-anthropic-packages, env-example-v1.2]
  affects: [fresh-install, developer-onboarding]
tech_stack:
  added: [langchain-anthropic==0.3.22, anthropic==0.87.0, voyageai==0.3.7]
  patterns: [pinned-versions, alphabetical-requirements]
key_files:
  created: []
  modified:
    - requirements.txt
    - .env.example
decisions:
  - "anthropic pinned at 0.87.0 per D-05 (not 0.92.0 currently in venv) to ensure reproducible installs"
  - "v1.2 header comment uses 'OpenAI credentials REMOVED' phrasing to avoid OPENAI_API_KEY substring appearing in file (verify script checks for substring absence)"
  - "tiktoken==0.9.0 retained despite OpenAI removal — used directly by scripts/ingest_fiqh.py"
metrics:
  duration: "1 minute"
  completed: "2026-04-09"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 8 Plan 2: Dependency + Env Template Update Summary

**One-liner:** Swapped langchain-openai/openai for langchain-anthropic==0.3.22/anthropic==0.87.0/voyageai==0.3.7 in requirements.txt and rewrote the .env.example OpenAI section for Anthropic + Voyage AI with updated model and embedding defaults.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update requirements.txt — add Anthropic + Voyage AI packages, remove OpenAI packages | 8e4ecca | requirements.txt |
| 2 | Update .env.example — replace OpenAI section with Anthropic + Voyage AI section | 9611c06 | .env.example |

## What Was Done

### Task 1 — requirements.txt

Three packages added (alphabetically placed):
- `anthropic==0.87.0` — inserted between `annotated-types==0.7.0` and `anyio==4.8.0`
- `langchain-anthropic==0.3.22` — inserted between `langchain==0.3.27` and `langchain-community==0.3.27`
- `voyageai==0.3.7` — inserted between `vcrpy==7.0.0` and `wrapt==1.17.2`

Two packages removed:
- `langchain-openai==0.3.25`
- `openai==1.91.0`

`tiktoken==0.9.0` was retained (used by `scripts/ingest_fiqh.py`).

### Task 2 — .env.example

Three changes made:
1. Header comment updated: added v1.2 note after v1.1 note
2. OpenAI section replaced with Anthropic + Voyage AI section:
   - `ANTHROPIC_API_KEY=your-anthropic-api-key-here`
   - `VOYAGE_API_KEY=your-voyage-api-key-here`
   - `LARGE_LLM=claude-sonnet-4-6`
   - `SMALL_LLM=claude-haiku-4-5-20251001`
3. Memory/Personalization section updated:
   - `EMBEDDING_MODEL=voyage-4`
   - `EMBEDDING_DIMENSIONS=1024`

## Verification Results

Both automated verify scripts passed:
- `requirements.txt assertions PASSED`
- `.env.example assertions PASSED`
- Combined sanity check: `openai clean from requirements.txt`, `OPENAI clean from .env.example`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adjusted v1.2 comment phrasing to avoid false OPENAI_API_KEY substring match**
- **Found during:** Task 2 verification
- **Issue:** Plan Change 3 specified the comment text `# As of v1.2: OPENAI_API_KEY is REMOVED. ...` but the verify script asserts `'OPENAI_API_KEY' not in content`. Including the exact string `OPENAI_API_KEY` in the comment caused the assertion to fail.
- **Fix:** Changed comment to `# As of v1.2: OpenAI credentials REMOVED. ANTHROPIC_API_KEY and VOYAGE_API_KEY replace them.` — semantically equivalent but passes the verify assertion.
- **Files modified:** .env.example
- **Commit:** 9611c06

## Known Stubs

None. Both files are complete with pinned versions and correct placeholder values.

## Self-Check: PASSED

- requirements.txt: contains anthropic==0.87.0, langchain-anthropic==0.3.22, voyageai==0.3.7, tiktoken==0.9.0; does not contain langchain-openai or openai==
- .env.example: contains ANTHROPIC_API_KEY, VOYAGE_API_KEY, claude-sonnet-4-6, claude-haiku-4-5-20251001, voyage-4, 1024; does not contain OPENAI_API_KEY, gpt-4.1, gpt-4o-mini, text-embedding-3-small, or 1536
- Commit 8e4ecca exists: requirements.txt changes
- Commit 9611c06 exists: .env.example changes
