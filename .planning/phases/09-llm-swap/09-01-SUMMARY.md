---
phase: 09-llm-swap
plan: 01
subsystem: api
tags: [anthropic, langchain-anthropic, chat-models, config, pydantic]

# Dependency graph
requires:
  - phase: 08-config-dependencies
    provides: ANTHROPIC_API_KEY, VOYAGE_API_KEY exported from core/config.py; langchain-anthropic 0.3.22 installed
provides:
  - ChatAnthropic factory functions (get_generator_model, get_enhancer_model, get_classifier_model, get_translator_model) in core/chat_models.py
  - OPENAI_API_KEY compatibility shim in core/config.py for legacy pipeline modules
  - ModelConfig with Claude-compatible constraints (temperature le=1.0, max_tokens=4096 default, agent_model fallback claude-sonnet-4-6)
affects: [09-02-agent-graph, modules/fiqh, agents/core/chat_agent, core/pipeline_langgraph]

# Tech tracking
tech-stack:
  added: [langchain-anthropic (ChatAnthropic)]
  patterns: [ChatAnthropic factory pattern with lazy LARGE_LLM/SMALL_LLM import, compatibility shim for legacy import names]

key-files:
  created: []
  modified:
    - core/config.py
    - core/chat_models.py
    - agents/config/agent_config.py

key-decisions:
  - "OPENAI_API_KEY shim set to empty string (not os.getenv) — legacy modules must not use it for actual API calls; Phase 11 removes these imports entirely"
  - "get_classifier_model() uses LARGE_LLM not SMALL_LLM — D-07 SMALL_LLM correction deferred to Phase 11 per plan"
  - "max_tokens per D-02: generator=4096, enhancer=512, classifier=2048, translator=1024 — set at construction time not via .bind()"
  - "Optional removed from typing imports in agent_config.py — max_tokens is the only field that used it; confirmed no other Optional fields"

patterns-established:
  - "ChatAnthropic instantiation: ChatAnthropic(model=LLM, api_key=ANTHROPIC_API_KEY, max_tokens=N) — use api_key kwarg, not anthropic_api_key"
  - "Lazy config import inside factory function: from core.config import LARGE_LLM inside def — preserves hot-reload and test isolation"

requirements-completed: [LLM-01, LLM-03, LLM-04]

# Metrics
duration: 15min
completed: 2026-04-10
---

# Phase 09 Plan 01: LLM Swap Foundation Summary

**ChatAnthropic replaces init_chat_model/OpenAI in all four factory functions, OPENAI_API_KEY shim added for legacy import compat, ModelConfig updated with Claude API constraints (temperature<=1.0, max_tokens=4096)**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-10T00:00:00Z
- **Completed:** 2026-04-10T00:15:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Replaced all four `init_chat_model`/OpenAI factory functions in `core/chat_models.py` with `ChatAnthropic` equivalents, each with correct `max_tokens` per D-02
- Added `OPENAI_API_KEY = ""` shim to `core/config.py` so legacy pipeline modules (classification, enhancement, generation) don't crash at import time until Phase 11 cleanup
- Updated `ModelConfig` in `agents/config/agent_config.py`: temperature capped at 1.0, max_tokens defaults to 4096 (not None), agent_model fallback changed from `gpt-4o` to `claude-sonnet-4-6`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add OPENAI_API_KEY compatibility shim** - `71c5e73` (feat)
2. **Task 2: Replace chat_models.py with ChatAnthropic factory functions** - `011e188` (feat)
3. **Task 3: Update ModelConfig for Claude compatibility** - `d7e44bc` (feat)

## Files Created/Modified

- `core/config.py` - Added `OPENAI_API_KEY = ""` shim at bottom with explanatory comment
- `core/chat_models.py` - Completely replaced with ChatAnthropic factory functions; removed init_chat_model, OPENAI_API_KEY, try/except wrappers, debug prints
- `agents/config/agent_config.py` - Updated ModelConfig: agent_model fallback, temperature le, max_tokens type/default; removed Optional import

## Decisions Made

- `get_classifier_model()` uses `LARGE_LLM` not `SMALL_LLM` — per plan D-07, SMALL_LLM correction for classifier is deferred to Phase 11 to avoid scope creep in this plan
- The compatibility shim `OPENAI_API_KEY = ""` is intentionally an empty string (not `os.getenv()`), making it explicit that no real API key is expected from env for this name
- Merged `feature/supabase-migration` into worktree branch before executing — worktree started from `main` but Phase 9 depends on Phase 8 changes (ANTHROPIC_API_KEY in config.py, langchain-anthropic installed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Merged feature/supabase-migration base into worktree**
- **Found during:** Pre-task setup
- **Issue:** Worktree branch was created from `main` (38a98bb) but Phase 8 changes (ANTHROPIC_API_KEY in config.py, langchain-anthropic package) only existed on `feature/supabase-migration`. Plan execution would have failed — config.py still had old OPENAI_API_KEY as real env var.
- **Fix:** Fast-forward merged `feature/supabase-migration` into worktree branch before executing any tasks
- **Files modified:** All Phase 8 files (core/config.py, requirements.txt, etc.)
- **Verification:** `from core.config import ANTHROPIC_API_KEY` succeeded after merge
- **Committed in:** Fast-forward merge (no separate commit — worktree now at 1d68831)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required to establish Phase 8 baseline. No scope creep — no plan tasks changed.

## Issues Encountered

None beyond the worktree base branch deviation documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `core/chat_models.py` exports four ChatAnthropic factory functions ready for use by all consumers (agents, modules/fiqh, pipeline_langgraph)
- `agents/core/chat_agent.py` still uses `init_chat_model` directly for its `agent_llm` — Plan 09-02 will update chat_agent.py to use `get_generator_model()` or direct ChatAnthropic
- `LARGE_LLM` env var in local `.env` still set to `gpt-4.1-2025-04-14` — Plan 09-02 or environment update will switch this to `claude-sonnet-4-6`
- Legacy modules (modules/classification, modules/enhancement, modules/generation) still import `OPENAI_API_KEY` and use `init_chat_model`/OpenAI — Phase 11 scope

---
*Phase: 09-llm-swap*
*Completed: 2026-04-10*
