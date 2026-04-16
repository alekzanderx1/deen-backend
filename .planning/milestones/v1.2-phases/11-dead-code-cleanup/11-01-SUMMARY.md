---
phase: 11-dead-code-cleanup
plan: "01"
subsystem: api
tags: [openai, cleanup, dead-code, requirements, voyageai]

# Dependency graph
requires:
  - phase: 09-llm-swap
    provides: ChatAnthropic wired in all LLM call sites; OPENAI_API_KEY shim = "" added to config.py
  - phase: 10-embedding-migration
    provides: HuggingFace embeddings in place; VOYAGE_API_KEY removed from startup guard
provides:
  - Zero openai imports in application code
  - OPENAI_API_KEY compatibility shim deleted from core/config.py
  - voyageai removed from requirements.txt
  - Stale OpenAI comments updated to LLM in core/pipeline.py
affects: [phase-12, future-phases, requirements-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dead import cleanup: remove unused imports rather than leaving compatibility shims"

key-files:
  created: []
  modified:
    - modules/classification/classifier.py
    - modules/generation/stream_generator.py
    - modules/enhancement/enhancer.py
    - modules/generation/generator.py
    - core/config.py
    - core/pipeline.py
    - requirements.txt

key-decisions:
  - "OPENAI_API_KEY shim deleted from core/config.py after all import sites cleaned — ImportError now raised on attempted import, confirming removal"
  - "voyageai dropped from requirements.txt — Voyage AI replaced by HuggingFace all-mpnet-base-v2 in Phase 10"

patterns-established:
  - "Verify removal via expected ImportError: python -c 'from core.config import OPENAI_API_KEY' should fail after cleanup"

requirements-completed: [CLEAN-03]

# Metrics
duration: 5min
completed: 2026-04-10
---

# Phase 11 Plan 01: Remove Dead OpenAI Imports from Application Code Summary

**Dead `openai` imports, `OPENAI_API_KEY` references, and `voyageai` dependency fully excised from application code — zero OpenAI import sites remain**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-10T16:10:00Z
- **Completed:** 2026-04-10T16:15:00Z
- **Tasks:** 7
- **Files modified:** 7

## Accomplishments

- Removed `from openai import OpenAI` from `classifier.py` and `stream_generator.py`
- Removed all `OPENAI_API_KEY` imports from 4 modules (classifier, stream_generator, enhancer, generator)
- Deleted module-level `client = OpenAI(api_key=OPENAI_API_KEY)` instantiation from `stream_generator.py`
- Deleted the 5-line `OPENAI_API_KEY` compatibility shim from `core/config.py`
- Updated stale `# Step 5: Generate AI response using OpenAI` comments to `using LLM` in `pipeline.py`
- Removed `voyageai==0.3.7` from `requirements.txt`

## Task Commits

All 7 tasks were batched into one atomic commit (plan calls for a single commit):

1. **Tasks 1-7: Remove dead OpenAI imports; drop voyageai from requirements** - `3f32045` (feat)

## Files Created/Modified

- `modules/classification/classifier.py` - Removed `from openai import OpenAI` and `from core.config import OPENAI_API_KEY`
- `modules/generation/stream_generator.py` - Removed `from openai import OpenAI`, `from core.config import OPENAI_API_KEY`, and `client = OpenAI(api_key=OPENAI_API_KEY)`
- `modules/enhancement/enhancer.py` - Removed `from core.config import OPENAI_API_KEY`
- `modules/generation/generator.py` - Removed `from core.config import OPENAI_API_KEY`
- `core/config.py` - Deleted OPENAI_API_KEY compatibility shim (5 lines: comment block + assignment)
- `core/pipeline.py` - Updated stale OpenAI comments (2 occurrences) to reference LLM generically
- `requirements.txt` - Removed `voyageai==0.3.7`

## Decisions Made

None — followed plan as specified. The shim deletion was confirmed correct by verifying `ImportError` is raised on attempted import, matching the plan's verification step.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. All 4 modules imported cleanly after removal. `OPENAI_API_KEY` import raises `ImportError` as expected.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CLEAN-03 satisfied: zero `openai` import sites in application code, `OPENAI_API_KEY` shim deleted, `voyageai` removed from requirements
- Ready for Plan 11-02 (CLEAN-04): remaining dead code cleanup tasks
- No blockers

---
*Phase: 11-dead-code-cleanup*
*Completed: 2026-04-10*
