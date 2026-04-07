# Phase 7: Cleanup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 07-cleanup
**Areas discussed:** Documentation format, Documentation completeness, Local .env cleanup

---

## Documentation Format

| Option | Description | Selected |
|--------|-------------|----------|
| `.env.example` only | Machine-readable template at repo root, checked into git | |
| Deployment runbook | Prose DEPLOYMENT.md or RUNBOOK.md with full setup instructions | |
| README section only | Inline env var docs within the existing README | |
| `.env.example` + README section | Both: machine-readable template AND human-readable explanation | ✓ |

**User's choice:** Both a `.env.example` file and a README section explaining it.
**Notes:** `.env.example` is the deployable template; README section is the human-readable companion with context.

---

## Documentation Completeness

| Option | Description | Selected |
|--------|-------------|----------|
| Delta only (v1.0→v1.1 changes) | Document only COGNITO→Supabase migration — what was removed, what was added | |
| Full template | All required env vars documented so a fresh deploy needs no git history | ✓ |

**User's choice:** Document all required env vars.
**Notes:** Operators deploying from scratch should have everything they need in `.env.example` + README without consulting git.

---

## Local .env Cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Remove COGNITO vars from .env | Clean up dead vars from local `.env` in this phase | |
| Leave .env as-is | COGNITO vars are ignored by the app; leave for manual cleanup | ✓ |

**User's choice:** Don't remove COGNITO vars from `.env` for now.
**Notes:** `COGNITO_REGION` and `COGNITO_POOL_ID` remain in `.env` but are inert — no code reads them anymore.

---

## Claude's Discretion

- Exact README section name and placement
- Whether `.env.example` uses inline per-var comments or group-level header comments

## Deferred Ideas

- Manual `.env` COGNITO var cleanup — user-driven, not in this phase
