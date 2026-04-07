# Roadmap: Deen Backend — Fiqh Agentic RAG

## Milestones

- ✅ **v1.0 Fiqh Agentic RAG MVP** — Phases 1-4 (shipped 2026-03-25)
- [ ] **v1.1 Supabase Migration** — Phases 5-7 (in progress)

## Phases

<details>
<summary>✅ v1.0 Fiqh Agentic RAG MVP (Phases 1-4) — SHIPPED 2026-03-25</summary>

- [x] Phase 1: Data Foundation (3/3 plans) — completed 2026-03-24
- [x] Phase 2: Routing and Retrieval (3/3 plans) — completed 2026-03-25
- [x] Phase 3: FAIR-RAG Core Modules (3/3 plans) — completed 2026-03-25
- [x] Phase 4: Assembly and Integration (3/3 plans) — completed 2026-03-25

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### v1.1 Supabase Migration

- [ ] **Phase 5: Database Migration** — Supabase Postgres provisioned with pgvector; all 13 tables present via alembic; DB env vars updated
- [ ] **Phase 6: Auth Migration** — JWTBearer middleware verifies Supabase JWTs; account deletion uses Supabase Admin API; Cognito env vars removed
- [ ] **Phase 7: Cleanup** — boto3 removed from all dependency files; environment variable changes documented

## Phase Details

### Phase 5: Database Migration
**Goal**: The application connects to Supabase Postgres with all tables present and DB environment variables updated — no code changes required
**Depends on**: Nothing (first phase of v1.1)
**Requirements**: DB-01, DB-02, DB-03
**Success Criteria** (what must be TRUE):
  1. Supabase dashboard shows the project is active with pgvector enabled under Database Extensions
  2. Running `alembic upgrade head` against the Supabase connection string completes without errors and alembic_version shows the latest revision
  3. All 13 SQLAlchemy tables are visible in the Supabase Table Editor (or `\dt` in psql)
  4. The running application connects successfully — `GET /_debug/db` returns 200 and no SQLAlchemy connection errors appear in logs
**Plans**: 2 plans
- [ ] 05-01-PLAN.md — Provision Supabase project and populate .env with DB_* vars + ASYNC_DATABASE_URL (DB-01, DB-03)
- [ ] 05-02-PLAN.md — Run alembic upgrade head, verify 13 tables + pgvector HNSW, confirm /_debug/db returns 200 (DB-02)

### Phase 6: Auth Migration
**Goal**: The application verifies Supabase Auth JWTs and performs account deletion via the Supabase Admin API — Cognito is fully replaced
**Depends on**: Phase 5
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Success Criteria** (what must be TRUE):
  1. `curl <SUPABASE_URL>/auth/v1/keys` returns a non-empty `keys` array confirming asymmetric JWT signing is active
  2. A valid Supabase Auth JWT is accepted by a protected endpoint; an invalid or Cognito-issued JWT is rejected with 403
  3. `COGNITO_REGION` and `COGNITO_POOL_ID` are absent from `.env` and `core/config.py`; `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are present and loaded
  4. `DELETE /account/me` deletes the user via the Supabase Admin API (`httpx` call to `<SUPABASE_URL>/auth/v1/admin/users/{uid}`) and returns 204 (boto3 import remains in `api/account.py` until Phase 7 cleanup per D-03a)
**Plans**: 3 plans
- [x] 06-P01-PLAN.md — Replace COGNITO_* env vars with SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in core/config.py, add startup guard (AUTH-03)
- [ ] 06-P02-PLAN.md — Update core/auth.py JWKS fetch URL from Cognito to Supabase /auth/v1/keys (AUTH-01, AUTH-02)
- [x] 06-P03-PLAN.md — Replace boto3 AdminDeleteUser with httpx Supabase Admin API call; remove username field from /account/me (AUTH-04)

### Phase 7: Cleanup
**Goal**: The dependency tree and deployment configuration contain no AWS references — boto3 is removed and all environment variable changes are documented
**Depends on**: Phase 6
**Requirements**: CLEAN-01, CLEAN-02
**Success Criteria** (what must be TRUE):
  1. `pip install -r requirements.txt` and `docker compose build` succeed with boto3 absent from both `requirements.txt` and the Dockerfile
  2. Running `grep -r boto3 .` (excluding `.git` and `venv`) returns no matches in application code or config files
  3. A deployment runbook or updated `.env.example` lists all removed Cognito vars and all added Supabase vars with descriptions, so a fresh deploy can be completed without consulting git history
**Plans**: 1 plan
- [ ] 07-01-PLAN.md — Remove boto3 from requirements.txt and api/account.py; create .env.example; update README.md env documentation (CLEAN-01, CLEAN-02)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 3/3 | Complete | 2026-03-24 |
| 2. Routing and Retrieval | v1.0 | 3/3 | Complete | 2026-03-25 |
| 3. FAIR-RAG Core Modules | v1.0 | 3/3 | Complete | 2026-03-25 |
| 4. Assembly and Integration | v1.0 | 3/3 | Complete | 2026-03-25 |
| 5. Database Migration | v1.1 | 0/2 | Not started | - |
| 6. Auth Migration | v1.1 | 2/3 | In Progress|  |
| 7. Cleanup | v1.1 | 0/1 | Not started | - |
