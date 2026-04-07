# Requirements: Deen Backend — Supabase Migration

**Defined:** 2026-04-06
**Core Value:** Every fiqh answer must be strictly grounded in retrieved evidence from Ayatollah Sistani's published rulings — the system refuses to answer rather than hallucinate or speculate.

## v1.1 Requirements

Requirements for the Supabase migration milestone. Each maps to roadmap phases.

### Database Migration

- [ ] **DB-01**: Supabase Postgres project is provisioned with pgvector extension enabled in the dashboard
- [ ] **DB-02**: All 13 SQLAlchemy tables and alembic_version table are present after running `alembic upgrade head` against Supabase
- [ ] **DB-03**: DATABASE_URL and ASYNC_DATABASE_URL point at Supabase direct connection (port 5432, no pooler)

### Auth Migration

- [ ] **AUTH-01**: Supabase Auth is configured with asymmetric JWT signing (RS256/ES256) — JWKS endpoint returns non-empty keys array
- [ ] **AUTH-02**: JWTBearer middleware verifies Supabase Auth JWTs (`core/auth.py` JWKS URL updated to Supabase)
- [ ] **AUTH-03**: COGNITO_REGION and COGNITO_POOL_ID env vars removed; SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY added
- [ ] **AUTH-04**: Account deletion in `api/account.py` uses Supabase Admin API (httpx call) instead of boto3 `admin_delete_user`

### Cleanup

- [ ] **CLEAN-01**: boto3 removed from requirements.txt and all deployment configs (Dockerfile, CI)
- [ ] **CLEAN-02**: Environment variable changes documented in .env.example or deployment runbook

## Future Requirements

Deferred to future milestones. Not in current roadmap.

### Supabase Enhanced Features

- **SUPA-01**: Row Level Security (RLS) policies on sensitive tables — deferred; app currently operates as postgres superuser which bypasses RLS
- **SUPA-02**: Supabase Realtime for live chat updates — deferred; SSE streaming handles this today
- **SUPA-03**: Supabase Storage for user uploads — deferred; no file upload features planned
- **SUPA-04**: Session pooler (port 5432 via pooler host) for IPv4-only deployment environments — defer until IPv6 issue confirmed

## Out of Scope

| Feature | Reason |
|---------|--------|
| supabase-py SDK | Not needed — app uses SQLAlchemy directly; SDK wraps PostgREST/storage/realtime which we don't use |
| Data migration (RDS → Supabase) | Fresh start on Supabase; no existing data to migrate |
| Supabase Auth user creation/signup flow | Backend only — frontend handles Supabase Auth SDK calls; backend validates JWTs only |
| Transaction pooler (port 6543) | asyncpg incompatibility; direct connection (port 5432) used for both sync and async |
| Schema permissions grants | Not required for app functionality (app uses postgres superuser); cosmetic only |
| Redis migration | Redis conversation memory unchanged in this milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DB-01 | Phase 5 | Pending |
| DB-02 | Phase 5 | Pending |
| DB-03 | Phase 5 | Pending |
| AUTH-01 | Phase 6 | Pending |
| AUTH-02 | Phase 6 | Pending |
| AUTH-03 | Phase 6 | Pending |
| AUTH-04 | Phase 6 | Pending |
| CLEAN-01 | Phase 7 | Pending |
| CLEAN-02 | Phase 7 | Pending |

**Coverage:**
- v1.1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-06*
*Last updated: 2026-04-06 — traceability confirmed after roadmap creation (phases 5-7 assigned)*
