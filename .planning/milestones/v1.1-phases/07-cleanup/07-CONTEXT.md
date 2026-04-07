# Phase 7: Cleanup - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 7 removes all boto3/AWS traces from the dependency tree and application code, and documents the full environment variable set for operators deploying from scratch.

Phase succeeds when:
1. `boto3==1.35.96` is absent from `requirements.txt`; `import boto3` is absent from `api/account.py`
2. `grep -r boto3 .` (excluding `.git` and `venv/`) returns no matches
3. A `.env.example` file exists at the repo root with all required vars described
4. `README.md` contains a section explaining each env var group (what it does, where it comes from)

Out of scope:
- Removing COGNITO vars from the local `.env` file — leave as-is
- Any code changes beyond the boto3 import removal
- Changes to Dockerfile (it installs from `requirements.txt` directly — boto3 removal there is sufficient)

</domain>

<decisions>
## Implementation Decisions

### boto3 Removal
- **D-01:** Remove `boto3==1.35.96` from `requirements.txt` (line 8). No other packages need to be removed — `botocore`, `s3transfer`, and `jmespath` are boto3 transitive deps and will also disappear from `pip install`.
- **D-02:** Remove `import boto3` from `api/account.py` (line 10). This is the only remaining boto3 reference in application code after Phase 6 replaced the boto3 call with httpx.

### Documentation Format
- **D-03:** Create a `.env.example` file at the repo root. This is the machine-readable template — checked into git, usable as a starting point for a fresh deploy.
- **D-04:** Add a section to `README.md` explaining the environment variables. This is the human-readable companion — groups vars by service, explains what each does and where to get it.

### Documentation Completeness
- **D-05:** Document ALL required env vars (full template, not just the COGNITO→Supabase delta). Operators deploying fresh should not need git history.
  - Group 1: OpenAI (`OPENAI_API_KEY`, `LARGE_LLM`, `SMALL_LLM`)
  - Group 2: Pinecone (`PINECONE_API_KEY`, `DEEN_DENSE_INDEX_NAME`, `DEEN_SPARSE_INDEX_NAME`, `QURAN_DENSE_INDEX_NAME`, `DEEN_FIQH_DENSE_INDEX_NAME`, `DEEN_FIQH_SPARSE_INDEX_NAME`, `DENSE_RESULT_WEIGHT`, `SPARSE_RESULT_WEIGHT`, `REFERENCE_FETCH_COUNT`)
  - Group 3: Supabase (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`)
  - Group 4: Database (`DATABASE_URL`, `ASYNC_DATABASE_URL`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`)
  - Group 5: Redis (`REDIS_URL`, `REDIS_KEY_PREFIX`, `REDIS_TTL_SECONDS`, `REDIS_MAX_MESSAGES`)
  - Group 6: App (`ENV`, `CORS_ALLOW_ORIGINS`)
- **D-06:** The `.env.example` uses placeholder values (e.g., `your-openai-key-here`, `https://xxxx.supabase.co`) so it's clear which fields need real values vs which have safe defaults.
- **D-07:** The README section should note that `COGNITO_REGION` and `COGNITO_POOL_ID` are **removed** as of v1.1 — so anyone upgrading from v1.0 knows to drop them.

### Local .env File
- **D-08:** Do NOT remove `COGNITO_REGION` / `COGNITO_POOL_ID` from the local `.env` file. They are ignored by the application (no longer read by `core/config.py`) and are harmless. The user will clean them up manually if/when desired.

### Claude's Discretion
- Exact README section name and placement (e.g., "Environment Variables" near the top, or as a setup subsection)
- Whether `.env.example` includes inline comments per var or groups them with header comments only

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Files being changed
- `requirements.txt` — remove `boto3==1.35.96` (line 8)
- `api/account.py` — remove `import boto3` (line 10); no other changes

### Files being created
- `.env.example` — new file at repo root; full variable template
- `README.md` — add env var documentation section

### Authoritative var source
- `core/config.py` — canonical list of all env vars loaded at runtime (lines 1–55)
- `db/config.py` — DB_* vars loaded via pydantic-settings (DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)

### Requirements
- `.planning/REQUIREMENTS.md` §CLEAN-01, CLEAN-02 — acceptance criteria for this phase
- `.planning/ROADMAP.md` §Phase 7 — 3 success criteria

### No external specs — requirements fully captured in decisions above

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `core/config.py` lines 1–55 — authoritative list of every env var the app reads; use this as the source of truth for `.env.example` content
- `db/config.py` — DB_* pydantic-settings model; documents alias names (DB_USER / POSTGRES_USER / PGUSER)

### Established Patterns
- No `.env.example` exists yet — create from scratch
- `README.md` exists; env var section will be added (not replace existing content)
- Dockerfile installs `requirements.txt` directly — removing boto3 from that file is sufficient for Docker; no Dockerfile edits needed

### Integration Points
- `requirements.txt` → `Dockerfile` — single source; fix requirements.txt, Docker is fixed
- `api/account.py` line 10 — only remaining boto3 import after Phase 6; removal is self-contained (no other code in the file references boto3)

</code_context>

<specifics>
## Specific Ideas

- `.env.example` should use visually obvious placeholder values so it's immediately clear what's real vs template
- README env section should call out the v1.0→v1.1 migration explicitly: COGNITO vars removed, SUPABASE vars added

</specifics>

<deferred>
## Deferred Ideas

- Removing COGNITO_REGION / COGNITO_POOL_ID from the local `.env` — user will do this manually
- None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-cleanup*
*Context gathered: 2026-04-07*
