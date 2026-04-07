---
phase: 06-auth-migration
plan: P01
subsystem: auth
tags: [supabase, cognito, config, env-vars, startup-guard]

# Dependency graph
requires: []
provides:
  - "SUPABASE_URL module-level constant in core/config.py"
  - "SUPABASE_SERVICE_ROLE_KEY module-level constant in core/config.py"
  - "Startup ValueError guard — server refuses to boot without both Supabase vars"
  - "COGNITO_REGION and COGNITO_POOL_ID fully removed from config"
affects: [06-P02, 06-P03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Startup guard pattern: ValueError raised at module import time when required env vars are absent"

key-files:
  created: []
  modified:
    - core/config.py

key-decisions:
  - "Supabase vars placed adjacent to existing Redis/LLM vars (lines 25-26) — same logical config section"
  - "ValueError guard added as a new block (not merged into the existing OPENAI/PINECONE guard) — keeps guard granularity clear for operators"
  - "COGNITO_REGION and COGNITO_POOL_ID fully deleted (not commented out) per D-03 — clean removal, no dead code"

patterns-established:
  - "Single source of truth: downstream files (core/auth.py, api/account.py) import SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from core/config.py"

requirements-completed: [AUTH-03]

# Metrics
duration: 1min
completed: 2026-04-07
---

# Phase 06 Plan P01: Config — Replace Cognito with Supabase Env Vars Summary

**Supabase env vars (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) replace Cognito constants in core/config.py with startup ValueError guard**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-07T04:18:51Z
- **Completed:** 2026-04-07T04:19:50Z
- **Tasks:** 1 of 1
- **Files modified:** 1

## Accomplishments
- Replaced `COGNITO_REGION` and `COGNITO_POOL_ID` with `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `core/config.py`
- Added startup ValueError guard that prevents server boot when either Supabase var is absent
- Established `core/config.py` as the single source of truth for Supabase env vars (Wave 2 plans import from here)

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace Cognito env vars with Supabase vars in core/config.py** - `f47a8b2` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified
- `core/config.py` — Removed COGNITO_REGION/COGNITO_POOL_ID; added SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY constants; added ValueError startup guard

## Decisions Made
- Supabase vars placed in the same logical section as REDIS_URL and LLM vars (adjacent to existing Redis constants) — consistent grouping
- ValueError guard added as a standalone `if` block below the existing OPENAI/PINECONE guard — keeps operator error messages specific and actionable
- COGNITO vars fully deleted (not commented out) — clean per D-03, no residual dead code

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Verification script false negative due to multi-occurrence string split**
- **Found during:** Task 1 (verification step)
- **Issue:** The plan's automated check used `content.split('SUPABASE_SERVICE_ROLE_KEY')[1][:300]` to find the ValueError guard. Because `SUPABASE_SERVICE_ROLE_KEY` appears 4 times in the file (assignment, getenv arg, guard condition, error message), `[1]` resolves to ` = os.getenv("` which does not contain `raise ValueError`. The guard is correctly present; the script's split index is off.
- **Fix:** No code change needed — the guard is correct. The verification was confirmed correct via direct acceptance criteria checks (grep, startup import test), all of which passed.
- **Files modified:** None
- **Verification:** `python3 -c "import os; os.environ.pop('SUPABASE_URL', None); from core import config"` raises `ValueError: Missing Supabase config! ...`
- **Committed in:** f47a8b2 (Task 1 commit)

---

**Total deviations:** 1 (false negative in verification script — no code impact)
**Impact on plan:** None — the actual file changes satisfy all acceptance criteria. Script logic issue only.

## Issues Encountered
- The plan's inline `content.split(...)[1]` check produced a false failure because SUPABASE_SERVICE_ROLE_KEY appears multiple times (constant definition, getenv argument, guard condition, error message string). Confirmed correctness via direct grep checks and import test.

## User Setup Required
None - no external service configuration required at this stage. Env var values (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) must be added to `.env` before server start — documented in Phase 6 context.

## Next Phase Readiness
- `core/config.py` now exports `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` for Wave 2 imports
- Wave 2 plans (P02: core/auth.py, P03: api/account.py) can now `from core.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY`
- No blockers

---
*Phase: 06-auth-migration*
*Completed: 2026-04-07*
