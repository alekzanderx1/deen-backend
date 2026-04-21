---
phase: quick-260408-m7e
plan: 01
subsystem: account-deletion
tags:
  - supabase
  - auth
  - bugfix
  - admin-api
  - kong
requirements:
  - QUICK-260408-m7e
dependency-graph:
  requires:
    - core/config.py (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY — already imported)
    - Supabase GoTrue Admin API via Kong gateway
  provides:
    - api/account.py:delete_my_account — corrected Supabase Admin API headers
  affects:
    - DELETE /account/me endpoint runtime behavior (no API surface change)
tech-stack:
  added: []
  patterns:
    - "Dual-header Supabase Admin API call: apikey (Kong tenant routing) + Authorization Bearer (GoTrue role check)"
key-files:
  created: []
  modified:
    - api/account.py
decisions:
  - "Both apikey and Authorization headers carry SUPABASE_SERVICE_ROLE_KEY value (canonical Supabase Admin API pattern)"
  - "No regression test added — explicitly out of scope per approved plan; documented as follow-up"
metrics:
  duration: ~3min
  completed: 2026-04-08
  tasks_completed: 1
  files_modified: 1
  files_created: 0
---

# Quick Task 260408-m7e: Fix Supabase Admin API 401 in account deletion — Summary

**One-liner:** Added the `apikey` header alongside the existing `Authorization: Bearer` header in `api/account.py` Step 3 so that Supabase's Kong gateway accepts the `DELETE /auth/v1/admin/users/{user_id}` call instead of rejecting it at the edge with HTTP 401.

## What Changed

A single, surgical edit inside `delete_my_account` Step 3 in `api/account.py`. The headers dict was expanded from a single-key inline literal into a two-key multi-line literal carrying both `apikey` and `Authorization`.

### Diff applied to `api/account.py`

```diff
         response = httpx.delete(
             f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
-            headers={"Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"},
+            headers={
+                "apikey": SUPABASE_SERVICE_ROLE_KEY,
+                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
+            },
         )
```

Net change: `1 file changed, 4 insertions(+), 1 deletion(-)`.

The 404-is-success branch, the non-2xx error logging, the success log line, and the outer `try/except Exception` "log but don't fail" wrapper (per D-05) are byte-for-byte unchanged. No new imports were added — `SUPABASE_SERVICE_ROLE_KEY` was already imported on line 16. No other files were touched.

## Why

Supabase's Kong API gateway sits in front of GoTrue and requires an `apikey` header for tenant routing. Without it, Kong rejects requests at the edge with HTTP 401 (`{"message":"No API key found in request"}`) before GoTrue ever sees the `Authorization: Bearer` token. For Admin API calls, both headers conventionally take the **service role key** value: `apikey` satisfies Kong's tenant check, `Authorization: Bearer` satisfies GoTrue's role check.

Without this fix, deleting an account left an orphaned Supabase auth row, so the user could not re-sign-up with the same email. The endpoint still returned 204 (per D-05 the Supabase failure is logged-but-swallowed), making the bug silent at the HTTP level but user-visible in practice.

## Tasks

| Task | Name                                                  | Commit    | Files            |
| ---- | ----------------------------------------------------- | --------- | ---------------- |
| 1    | Add apikey header to Supabase Admin API delete call   | `1fb9a2b` | `api/account.py` |
| 2    | Runtime verification of account deletion (checkpoint) | —         | (verification)   |

## Verification

### Static / structural

- `python -c "import ast; ast.parse(open('api/account.py').read())"` → parses cleanly (no syntax errors).
- `grep -n '"apikey": SUPABASE_SERVICE_ROLE_KEY' api/account.py` → exactly one match at line 86, inside the `delete_my_account` Step 3 block.
- `git status --short` → only `api/account.py` modified (plus the new `.planning/quick/260408-m7e-…/` directory).
- Surrounding control flow (404 branch, error log, success log, outer try/except) is byte-for-byte unchanged from the pre-edit version.

### Runtime (Task 2 — auto-approved under auto-mode)

Task 2 is a `checkpoint:human-verify` that requires hitting `DELETE /account/me` end-to-end against a live Supabase project (sign up a throwaway test user, trigger deletion, confirm the success log line, confirm the user disappears from the Supabase dashboard, confirm re-signup with the same email works). Under the active GSD auto-advance mode this checkpoint is **auto-approved** and the edit is shipped on the strength of the static verification above plus the well-known Supabase `apikey`-header convention.

**Auto-approval log entry:** `Auto-approved: api/account.py Step 3 dual-header fix for Supabase Admin API DELETE`.

The user should still perform the runtime walkthrough described in the plan's `<how-to-verify>` block at their convenience and report back if Supabase still rejects the call — at which point a follow-up quick task should investigate Kong's tenant resolution further (e.g., custom header overrides, or the URL needing the project-ref subdomain).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Follow-ups

- **No regression test added** — a `respx`/`httpx.MockTransport` test asserting both `apikey` and `Authorization` headers are present on the outbound `DELETE` to `/auth/v1/admin/users/{user_id}` is a worthwhile follow-up. Out of scope for this quick task per the approved plan.
- **Runtime confirmation** — when the user is next exercising account deletion in the frontend, confirm the Step 3 log line reads `Successfully deleted user <uuid> from Supabase Auth` (and not the previous `HTTP 401 — {"message":"No API key found in request",...}`).

## Self-Check: PASSED

- File `api/account.py` exists and contains the new dual-header dict at line 86.
- Commit `1fb9a2b` exists in the branch history (`fix(quick-260408-m7e): add apikey header to Supabase Admin API delete call`).
- Python AST parse of `api/account.py` succeeds.
- Only one file modified by this task (`api/account.py`), exactly as scoped.
