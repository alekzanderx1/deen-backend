# Phase 7: Cleanup - Research

**Researched:** 2026-04-07
**Domain:** Dependency cleanup and deployment documentation
**Confidence:** HIGH

## Summary

Phase 7 is a two-task cleanup phase with no architectural ambiguity. The work is fully scoped by the CONTEXT.md decisions and the current state of the codebase. Both tasks involve straightforward file edits with no risk of regressions.

Task 1 (CLEAN-01) removes boto3 from the dependency tree. `boto3==1.35.96` appears on line 8 of `requirements.txt` and is the only explicit boto3 entry — `botocore`, `s3transfer`, and `jmespath` are transitive deps that will disappear automatically when pip resolves the updated requirements. In `api/account.py`, there are TWO import lines that must both be removed: `import boto3` (line 10) and `from botocore.exceptions import ClientError` (line 11). Neither symbol appears anywhere else in the file body — the account deletion logic was fully replaced with httpx in Phase 6. No Dockerfile edits are needed; it installs from `requirements.txt` directly.

Task 2 (CLEAN-02) creates a `.env.example` file at the repo root and adds an environment variable documentation section to `README.md`. The authoritative source for all runtime vars is `core/config.py` (lines 1–94), supplemented by `db/config.py` for the DB_* alias names. The current README already has a "Configure Environment Variables" section under Quick Start that references `COGNITO_REGION` and `COGNITO_POOL_ID` — this section is outdated and must be replaced/updated. The README also references "AWS Cognito" in Troubleshooting (line 361), Prerequisites are missing Supabase, and the documentation link at line 142 still points to `documentation/AUTHENTICATION.md` which likely has Cognito content. These are documentation consistency issues the planner should address.

**Primary recommendation:** Execute as two sequential tasks — (1) remove boto3 lines and verify grep, (2) create `.env.example` and update README.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Remove `boto3==1.35.96` from `requirements.txt` (line 8). No other packages need to be removed — `botocore`, `s3transfer`, and `jmespath` are boto3 transitive deps and will also disappear from `pip install`.
- **D-02:** Remove `import boto3` from `api/account.py` (line 10). This is the only remaining boto3 reference in application code after Phase 6 replaced the boto3 call with httpx.
- **D-03:** Create a `.env.example` file at the repo root. This is the machine-readable template — checked into git, usable as a starting point for a fresh deploy.
- **D-04:** Add a section to `README.md` explaining the environment variables. This is the human-readable companion — groups vars by service, explains what each does and where to get it.
- **D-05:** Document ALL required env vars (full template, not just the COGNITO→Supabase delta). Operators deploying fresh should not need git history.
  - Group 1: OpenAI (`OPENAI_API_KEY`, `LARGE_LLM`, `SMALL_LLM`)
  - Group 2: Pinecone (`PINECONE_API_KEY`, `DEEN_DENSE_INDEX_NAME`, `DEEN_SPARSE_INDEX_NAME`, `QURAN_DENSE_INDEX_NAME`, `DEEN_FIQH_DENSE_INDEX_NAME`, `DEEN_FIQH_SPARSE_INDEX_NAME`, `DENSE_RESULT_WEIGHT`, `SPARSE_RESULT_WEIGHT`, `REFERENCE_FETCH_COUNT`)
  - Group 3: Supabase (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`)
  - Group 4: Database (`DATABASE_URL`, `ASYNC_DATABASE_URL`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`)
  - Group 5: Redis (`REDIS_URL`, `REDIS_KEY_PREFIX`, `REDIS_TTL_SECONDS`, `REDIS_MAX_MESSAGES`)
  - Group 6: App (`ENV`, `CORS_ALLOW_ORIGINS`)
- **D-06:** The `.env.example` uses placeholder values (e.g., `your-openai-key-here`, `https://xxxx.supabase.co`) so it's clear which fields need real values vs which have safe defaults.
- **D-07:** The README section should note that `COGNITO_REGION` and `COGNITO_POOL_ID` are **removed** as of v1.1 — so anyone upgrading from v1.0 knows to drop them.
- **D-08:** Do NOT remove `COGNITO_REGION` / `COGNITO_POOL_ID` from the local `.env` file. They are ignored by the application (no longer read by `core/config.py`) and are harmless.

### Claude's Discretion
- Exact README section name and placement (e.g., "Environment Variables" near the top, or as a setup subsection)
- Whether `.env.example` includes inline comments per var or groups them with header comments only

### Deferred Ideas (OUT OF SCOPE)
- Removing COGNITO_REGION / COGNITO_POOL_ID from the local `.env` — user will do this manually
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLEAN-01 | boto3 removed from requirements.txt and all deployment configs (Dockerfile, CI) | boto3==1.35.96 is on line 8 of requirements.txt. botocore/s3transfer/jmespath are transitive-only. Two import lines in api/account.py (lines 10-11) reference boto3 and botocore.exceptions — both unused in function bodies. Dockerfile installs from requirements.txt directly so no separate Dockerfile change is needed. |
| CLEAN-02 | Environment variable changes documented in .env.example or deployment runbook | core/config.py lines 1-94 is the authoritative var source. db/config.py documents DB_* alias names. README.md currently has an outdated env block referencing COGNITO vars. A full .env.example does not yet exist. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pip | (system) | Dependency resolution | Removing boto3 from requirements.txt causes pip to drop transitive deps automatically on next install |
| python-dotenv | 1.0.1 | `.env` file parsing | Already in use; `.env.example` is the template counterpart |

No new libraries are introduced in this phase.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `.env.example` | Inline README-only docs | `.env.example` is machine-usable (`cp .env.example .env`); README is human-readable companion — D-03/D-04 require both |

## Architecture Patterns

### Pattern 1: Two-file documentation model
**What:** `.env.example` serves as the machine-readable template (checked into git, `cp .env.example .env` workflow); `README.md` serves as the human-readable explanation with context about each group.
**When to use:** Standard for any project with non-trivial env configuration.

### Pattern 2: Group-by-service in `.env.example`
**What:** Vars are grouped under comment headers by service (OpenAI, Pinecone, Supabase, Database, Redis, App). Within each group, vars with safe defaults show the default value; required vars show a visually obvious placeholder.
**Example:**
```bash
# === OpenAI ===
OPENAI_API_KEY=your-openai-api-key-here
LARGE_LLM=gpt-4.1-2025-04-14
SMALL_LLM=gpt-4o-mini-2024-07-18

# === Supabase ===
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

### Pattern 3: Migration callout in README
**What:** The README env section calls out the v1.0→v1.1 transition explicitly so operators upgrading from Cognito auth know which vars to remove and add.
**Example:**
```markdown
> **Upgrading from v1.0?** Remove `COGNITO_REGION` and `COGNITO_POOL_ID` from your `.env`.
> Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` instead.
```

### Anti-Patterns to Avoid
- **Leaving `import boto3` without also removing `from botocore.exceptions import ClientError`:** The botocore import on line 11 of `api/account.py` is also dead code referencing a boto3 transitive dep. Both lines must be removed together.
- **Partial var documentation:** Documenting only the COGNITO→Supabase delta (per D-05, the full var set must be documented so operators need no git history).
- **Hardcoding real credentials in `.env.example`:** The file is committed to git; all sensitive fields must use placeholder strings.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Transitive dep removal | Manually hunt for botocore/s3transfer/jmespath lines | Remove only the boto3 line | pip resolves the full dep tree; removing the direct dep is sufficient |

## Common Pitfalls

### Pitfall 1: Missing botocore import line
**What goes wrong:** Only `import boto3` (line 10) is removed but `from botocore.exceptions import ClientError` (line 11) is left in place. `grep -r boto3 .` passes but `grep -r botocore .` would still match — and more importantly, importing botocore at runtime would fail once boto3 is absent from the env.
**Why it happens:** CONTEXT.md D-02 mentions "line 10" specifically, but the actual file has two boto-related import lines. The second was added alongside the original boto3 usage.
**How to avoid:** Remove both lines 10 and 11 from `api/account.py`. Confirm neither `boto3` nor `ClientError` nor `botocore` appears anywhere else in the file body.
**Warning signs:** `from botocore.exceptions import ClientError` surviving after the edit.

### Pitfall 2: README env section not fully replaced
**What goes wrong:** A new "Environment Variables" section is added but the old Quick Start "Configure Environment Variables" block (lines 47–84 of README.md) still references `COGNITO_REGION` and `COGNITO_POOL_ID`, creating contradictory docs.
**Why it happens:** Additive edits that don't remove the outdated block.
**How to avoid:** The old inline `.env` example inside Quick Start (lines 47–84) should be replaced or removed; the new dedicated section is the canonical reference. At minimum, the COGNITO vars must be removed from the Quick Start block.
**Warning signs:** `grep -n "COGNITO" README.md` returns matches after the edit.

### Pitfall 3: Outdated README references not updated
**What goes wrong:** README.md line 142 links to `documentation/AUTHENTICATION.md` which likely still describes AWS Cognito setup. Troubleshooting section (line 361) says "Check Cognito configuration in `.env`". These create operator confusion.
**Why it happens:** CONTEXT.md scope is focused on the env var section; other README locations with stale references can be missed.
**How to avoid:** When writing the env section, also scan README.md for remaining "Cognito" references and update them (at minimum, change the Troubleshooting line to reference Supabase Auth).
**Warning signs:** `grep -n -i "cognito" README.md` returning matches after edits.

### Pitfall 4: Missing vars from `.env.example`
**What goes wrong:** Vars added in Phase 6 (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) or Phase 1 (`DEEN_FIQH_DENSE_INDEX_NAME`, `DEEN_FIQH_SPARSE_INDEX_NAME`) are absent from `.env.example` because they weren't in the original README template.
**Why it happens:** The old README env block predates v1.1; copying it verbatim misses new vars.
**How to avoid:** Use `core/config.py` (lines 1–94) as the authoritative source, not the old README block. Cross-reference against D-05's var list in CONTEXT.md.
**Warning signs:** `.env.example` does not contain `SUPABASE_URL` or `DEEN_FIQH_DENSE_INDEX_NAME`.

### Pitfall 5: boto3 still present in worktree copies
**What goes wrong:** `grep -r boto3 .` finds matches in `.claude/worktrees/` directories, causing the success criterion to fail.
**Why it happens:** Agent worktrees under `.claude/worktrees/` are copies of older repo state; they contain the old files.
**How to avoid:** The `grep` success criterion should exclude `.claude/` in addition to `.git` and `venv/`. The phase success criteria already says "excluding `.git` and `venv`" — the planner's verification step should use `grep -r boto3 . --exclude-dir=.git --exclude-dir=venv --exclude-dir=.claude`.

## Code Examples

### Exact lines to remove from `api/account.py`
```python
# Remove both of these lines (lines 10-11):
import boto3
from botocore.exceptions import ClientError
```
After removal, the import block becomes:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import httpx
import logging
```

### Exact line to remove from `requirements.txt`
```
boto3==1.35.96     # line 8 — remove this entire line
```

### Verification command
```bash
grep -r boto3 . --exclude-dir=.git --exclude-dir=venv --exclude-dir=.claude
# Expected output: (empty — no matches)
```

### `.env.example` structure (per D-05 and D-06)
```bash
# === OpenAI ===
OPENAI_API_KEY=your-openai-api-key-here
LARGE_LLM=gpt-4.1-2025-04-14
SMALL_LLM=gpt-4o-mini-2024-07-18

# === Pinecone ===
PINECONE_API_KEY=your-pinecone-api-key-here
DEEN_DENSE_INDEX_NAME=deen-dense
DEEN_SPARSE_INDEX_NAME=deen-sparse
QURAN_DENSE_INDEX_NAME=quran-dense
DEEN_FIQH_DENSE_INDEX_NAME=deen-fiqh-dense
DEEN_FIQH_SPARSE_INDEX_NAME=deen-fiqh-sparse
DENSE_RESULT_WEIGHT=0.8
SPARSE_RESULT_WEIGHT=0.2
REFERENCE_FETCH_COUNT=10

# === Supabase (replaces AWS Cognito as of v1.1) ===
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# === Database (Supabase Postgres direct connection, port 5432) ===
DATABASE_URL=postgresql://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
ASYNC_DATABASE_URL=postgresql+asyncpg://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
DB_HOST=aws-0-us-east-1.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.xxxx
DB_PASSWORD=your-db-password-here

# === Redis ===
REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=dev:chat
REDIS_TTL_SECONDS=12000
REDIS_MAX_MESSAGES=30

# === App ===
ENV=development
CORS_ALLOW_ORIGINS=http://localhost:3000
```

## Current State Inventory (What Exists vs What's Needed)

| Item | Current State | Required State |
|------|---------------|----------------|
| `requirements.txt` line 8 | `boto3==1.35.96` | Removed |
| `api/account.py` line 10 | `import boto3` | Removed |
| `api/account.py` line 11 | `from botocore.exceptions import ClientError` | Removed |
| `.env.example` | Does not exist | Created at repo root |
| `README.md` Quick Start env block | Has COGNITO vars; missing Supabase/Fiqh vars | Updated (COGNITO removed, Supabase added) |
| `README.md` Troubleshooting line 361 | "Check Cognito configuration in `.env`" | Updated to reference Supabase Auth |
| `README.md` new env var section | Does not exist | Added (D-04) |

## Environment Availability

Step 2.6: SKIPPED — this phase is purely code/config file changes with no external dependencies.

## Sources

### Primary (HIGH confidence)
- `requirements.txt` — direct inspection, line 8 confirmed as `boto3==1.35.96`; no botocore/s3transfer/jmespath explicit entries
- `api/account.py` — direct inspection; lines 10-11 are the only boto-related code; neither symbol used in function bodies
- `core/config.py` — authoritative runtime env var list, lines 1-94
- `db/config.py` — DB_* alias names (DB_USER / POSTGRES_USER / PGUSER pattern)
- `README.md` — current content reviewed; COGNITO references located at lines 77-80 and 361
- `.planning/phases/07-cleanup/07-CONTEXT.md` — all implementation decisions

### Secondary (MEDIUM confidence)
- pip dependency resolution behavior: removing a top-level package removes its transitive deps on next install — well-established pip behavior

## Metadata

**Confidence breakdown:**
- CLEAN-01 (boto3 removal): HIGH — file line numbers verified by direct inspection; no ambiguity
- CLEAN-02 (documentation): HIGH — var sources verified from core/config.py; README current state inspected; only discretionary element is exact README section placement/wording
- Pitfalls: HIGH — all identified from direct code inspection, not inference

**Research date:** 2026-04-07
**Valid until:** 2026-05-07 (stable — no moving parts)
