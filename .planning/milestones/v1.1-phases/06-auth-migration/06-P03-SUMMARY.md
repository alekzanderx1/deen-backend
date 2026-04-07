---
phase: 06-auth-migration
plan: P03
subsystem: auth
tags: [supabase, cognito, httpx, account-deletion, api]

# Dependency graph
requires:
  - phase: 06-P01
    provides: "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY module-level constants in core/config.py"
provides:
  - "DELETE /account/me deletes user via httpx to Supabase Admin API (not boto3 Cognito)"
  - "GET /account/me returns {user_id, email, claims} — no username field"
  - "api/account.py imports SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from core.config"
affects: [07-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Synchronous httpx.delete() for Supabase Admin API calls inside async FastAPI handlers — consistent with existing sync-inside-async pattern (D-04)"
    - "log-but-don't-fail: non-success Supabase responses logged at error level, 204 still returned — DB data already deleted (D-05)"

key-files:
  created: []
  modified:
    - api/account.py
    - core/config.py

key-decisions:
  - "boto3 import retained in api/account.py through Phase 6 per D-03a — physical removal is Phase 7 CLEAN-01"
  - "httpx.delete() used synchronously per D-04: consistent with existing sync-inside-async pattern"
  - "404 from Supabase treated as success-equivalent per D-05: user already deleted, log warning only"
  - "SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY also applied to this worktree's core/config.py as P01 prerequisite in parallel execution context"

patterns-established:
  - "Supabase Admin API pattern: DELETE {SUPABASE_URL}/auth/v1/admin/users/{user_id} with Authorization: Bearer {SUPABASE_SERVICE_ROLE_KEY}"

requirements-completed: [AUTH-04]

# Metrics
duration: 5min
completed: 2026-04-07
---

# Phase 06 Plan P03: Account API — Supabase Auth Deletion Summary

**httpx DELETE to Supabase Admin API replaces boto3 AdminDeleteUser in account deletion; GET /account/me cleaned of Cognito username field**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-07T04:21:00Z
- **Completed:** 2026-04-07T04:23:27Z
- **Tasks:** 1 of 1
- **Files modified:** 2

## Accomplishments
- Replaced `boto3.client('cognito-idp') + admin_delete_user()` block with `httpx.delete()` to `{SUPABASE_URL}/auth/v1/admin/users/{user_id}` using `Authorization: Bearer {SUPABASE_SERVICE_ROLE_KEY}`
- Preserved "log but don't fail" semantics: 404 = already deleted (warning), non-success = error log, 204 still returned
- Removed `cognito:username` claim reference and `username` field from `GET /account/me` response
- `boto3` import kept per D-03a; boto3 *call* is gone; all `COGNITO_*` references removed

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace boto3 Cognito deletion with httpx Supabase Admin API call** - `3f4397e` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified
- `api/account.py` — Replaced Cognito deletion block with Supabase Admin API httpx call; removed username field from /account/me response
- `core/config.py` — Applied P01 prerequisite changes: replaced COGNITO_REGION/COGNITO_POOL_ID with SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY plus ValueError startup guard (parallel execution context)

## Decisions Made
- boto3 import retained per D-03a — Phase 7 CLEAN-01 handles physical removal from api/account.py and requirements.txt
- Synchronous `httpx.delete()` used per D-04 — consistent with existing pattern of sync calls inside async handlers
- 404 response treated as success-equivalent per D-05 — user already removed, warn and continue to return 204

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Applied P01 config.py changes to this parallel worktree**
- **Found during:** Task 1 setup (reading core/config.py)
- **Issue:** Parallel execution worktrees branch from main, not from feature/supabase-migration. This worktree's core/config.py still had COGNITO_REGION/COGNITO_POOL_ID instead of SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY. P03 depends on P01's config exports.
- **Fix:** Applied the same diff P01 committed (f47a8b2) — replaced COGNITO_REGION/COGNITO_POOL_ID with SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY, added ValueError startup guard
- **Files modified:** core/config.py
- **Verification:** `python -c "import ast; ast.parse(open('core/config.py').read()); print('OK')"` — syntax clean; both constants present; no COGNITO references
- **Committed in:** 3f4397e (Task 1 commit — bundled with api/account.py changes)

---

**Total deviations:** 1 auto-fixed (blocking prerequisite)
**Impact on plan:** Necessary for parallel execution correctness. The orchestrator will merge this worktree with the feature branch where P01's changes already exist; git will see the config.py changes as equivalent.

## Issues Encountered
None — all checks passed on first attempt.

## User Setup Required
None - no new external service configuration required at this stage. The SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be in `.env` before server start — documented in Phase 6 context.

## Next Phase Readiness
- `api/account.py` is fully Supabase-native: no Cognito references, no boto3 calls
- `core/auth.py` (P02) handles JWT verification — together P02 + P03 complete the full Supabase Auth migration
- Phase 7 (CLEAN-01) can safely remove `import boto3` and `from botocore.exceptions import ClientError` from api/account.py

---
*Phase: 06-auth-migration*
*Completed: 2026-04-07*
