---
phase: 06-auth-migration
plan: P02
subsystem: auth
tags: [supabase, cognito, jwks, jwt, middleware]

# Dependency graph
requires:
  - "06-P01: SUPABASE_URL exported from core/config.py"
provides:
  - "core/auth.py fetches JWKS from Supabase at module import time"
  - "auth and optional_auth JWTBearer instances exported from core/auth.py"
  - "Zero Cognito references in core/auth.py"
affects: [main.py, all API routes using JWTBearer dependency]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "JWKS fetch at module import time via requests.get({SUPABASE_URL}/auth/v1/keys)"
    - "Both auth (strict) and optional_auth (permissive) exported from core/auth.py"

key-files:
  created: []
  modified:
    - core/auth.py
    - core/config.py

key-decisions:
  - "optional_auth = JWTBearer(jwks, auto_error=False) added to core/auth.py — was missing from the file; main.py already imports from here"
  - "P01 dependency (config.py Supabase vars) applied to worktree before Task 2 — worktree was on a branch that pre-dated P01 commits"
  - "JWKS URL changed from Cognito cognito-idp.{region}.amazonaws.com/{pool}/.well-known/jwks.json to {SUPABASE_URL}/auth/v1/keys — JWTBearer class unchanged (provider-agnostic)"

requirements-completed: [AUTH-01, AUTH-02]

# Metrics
duration: 1min
completed: 2026-04-07
---

# Phase 06 Plan P02: core/auth.py — JWKS Source Migration to Supabase Summary

**JWKS fetch URL in core/auth.py changed from AWS Cognito to Supabase Auth endpoint; Cognito references fully removed**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-04-07T04:22:33Z
- **Completed:** 2026-04-07T04:23:30Z
- **Tasks:** 2 of 2
- **Files modified:** 2

## Accomplishments
- Replaced `COGNITO_REGION`/`COGNITO_POOL_ID` imports in `core/auth.py` with `SUPABASE_URL`
- Changed JWKS fetch URL from Cognito's `.well-known/jwks.json` to `{SUPABASE_URL}/auth/v1/keys`
- Added `optional_auth = JWTBearer(jwks, auto_error=False)` export (was missing from original file)
- Applied P01 config dependency to worktree: replaced `COGNITO_REGION`/`COGNITO_POOL_ID` with `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` in `core/config.py`, added startup ValueError guard

## Task Commits

Each task was committed atomically:

1. **Task 1: AUTH-01 pre-check (SUPABASE_URL not set in .env — SKIP path)** — no commit (no files changed; verification skipped gracefully)
2. **Task 2: Update JWKS fetch URL from Cognito to Supabase in core/auth.py** — `d70db82` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified
- `core/auth.py` — Replaced Cognito imports with SUPABASE_URL; JWKS URL now points to Supabase; added optional_auth export
- `core/config.py` — P01 dependency applied: COGNITO vars replaced with SUPABASE vars, startup ValueError guard added

## Decisions Made
- `optional_auth` export added to `core/auth.py` — it was absent from the original file but used by `main.py`; both `auth` and `optional_auth` now come from the same JWKS object
- P01 config.py dependency was applied to this worktree directly since the worktree branch pre-dated the P01 commit (`f47a8b2` on `feature/supabase-migration`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Applied P01 dependency to worktree before Task 2**
- **Found during:** Task 2 pre-check
- **Issue:** The worktree branch (`worktree-agent-a3f6e39a`) pre-dated the P01 commits. `core/config.py` still had `COGNITO_REGION`/`COGNITO_POOL_ID` and no `SUPABASE_URL`. Task 2 requires `from core.config import SUPABASE_URL` to be valid.
- **Fix:** Applied the P01 config changes directly to this worktree's `core/config.py` (same changes as commit `f47a8b2` on `feature/supabase-migration`): replaced Cognito vars with Supabase vars, added ValueError guard.
- **Files modified:** `core/config.py`
- **Commit:** `d70db82` (bundled with Task 2 commit)

---

**Total deviations:** 1 (auto-fixed P01 dependency gap — no plan impact)

## User Setup Required
- Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to `.env` before server start
- Ensure Supabase project has asymmetric JWT signing enabled (Authentication > Settings in Supabase dashboard)
- Once `.env` is updated, verify with: `python -c "from core.auth import auth, optional_auth"` — should complete without error

## Next Phase Readiness
- `core/auth.py` now verifies Supabase Auth JWTs via RS256 JWKS
- Wave 2 plan P03 (`api/account.py`) can proceed — imports `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from `core/config.py`
- No blockers

---
*Phase: 06-auth-migration*
*Completed: 2026-04-07*
