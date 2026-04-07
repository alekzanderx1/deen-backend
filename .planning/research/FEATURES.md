# Features: Supabase Migration

**Domain:** Infrastructure migration — AWS RDS + Cognito → Supabase Postgres + Supabase Auth
**Researched:** 2026-04-06
**Overall confidence:** HIGH (verified against official Supabase docs + codebase inspection)

---

## Database Migration (RDS → Supabase Postgres)

### What This Actually Means

The project uses SQLAlchemy (psycopg2 sync + asyncpg async) with 7 Alembic migration files. `db/session.py` builds the engine with `sslmode=require` and `pool_pre_ping=True`. `alembic/env.py` reads the DB URL from `db/config.py`'s `Settings` object, which constructs it from individual `DB_*` env vars. No data migration is needed — fresh Supabase project.

### Table Stakes Steps

**1. Get the right connection string from the Supabase dashboard.**

Supabase provides two families of connection strings (Project Settings → Database → Connection string):

| Type | Port | Use For |
|------|------|---------|
| Direct connection | 5432 | Alembic migrations, pg_dump, management tools |
| Supavisor session mode | 5432 (pooler host) | Long-running app servers (IPv4 compatible) |
| Supavisor transaction mode | 6543 | Serverless, short-lived connections only |

Direct format: `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`
Session pooler format: `postgres://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres`

For Alembic migrations: always use the direct connection (port 5432), not the pooler. The pooler's transaction mode drops session-level state that Alembic relies on.

**2. Update env vars.**

`db/config.py` already supports either individual `DB_*` vars or a combined `DATABASE_URL` via `AliasChoices`. The Supabase default DB user is `postgres`, default DB name is `postgres`.

Minimum change is setting:
```
DB_HOST=db.[PROJECT-REF].supabase.co
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=[your-supabase-db-password]
DB_NAME=postgres
```

**3. Run Alembic migrations against the fresh Supabase DB.**

`alembic/env.py` already uses `pool.NullPool` in online mode — this is correct for migration runs and compatible with Supabase's direct connection. No changes needed to `env.py`.

```bash
alembic upgrade head
```

This applies all 7 migration files in sequence, creating the 13 tables in the `public` schema.

**4. SSL is already handled.**

`db/session.py` has `connect_args={"sslmode": "require"}` — Supabase requires SSL, so this is already correct. No change needed.

### What to Watch For

**Schema namespace collision.** Supabase pre-provisions several schemas (`auth`, `storage`, `realtime`, `extensions`). The app's tables all live in `public` — no collision. Do not name any table to match these reserved schemas.

**`auth` schema foreign key error.** If any SQLAlchemy model references `auth.users` (e.g., via a foreign key), SQLAlchemy/Alembic throws `NoReferencedTableError` because it does not resolve cross-schema references by default. The current app's models do not reference `auth.users`, so this is not an issue for this migration.

**asyncpg + transaction-mode pooler incompatibility (HIGH severity, confirmed 2024-2025).** `core/config.py` configures `ASYNC_DATABASE_URL` with `postgresql+asyncpg://...`. If this URL points to Supabase's transaction-mode pooler (port 6543), asyncpg will produce `PreparedStatementError` ("prepared statement does not exist") under any load. This is a confirmed, ongoing issue with multiple open GitHub reports as of 2025. Mitigation: point `ASYNC_DATABASE_URL` at the direct connection (port 5432) or the session-mode pooler. The workaround of setting `statement_cache_size=0` in `connect_args` has also been reported as unreliable.

The async DB path is currently unused in routers (per CLAUDE.md). This means the asyncpg issue is low-risk — point `ASYNC_DATABASE_URL` at the direct connection and move on.

### Dashboard Configuration Required

- Copy the database password from Project Settings → Database. This is set at project creation and is distinct from the service role key.
- SSL certificates are available in the dashboard but not required when using `sslmode=require` with the default cert store.
- After running migrations, verify tables in the Supabase dashboard's Table Editor or SQL editor (`SELECT tablename FROM pg_tables WHERE schemaname = 'public';`).

---

## Auth Migration (Cognito → Supabase Auth)

### Current Implementation (What Exists)

`core/auth.py` fetches Cognito's JWKS at startup:
```python
jwks = JWKS.model_validate(
    requests.get(
        f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_POOL_ID}/.well-known/jwks.json"
    ).json()
)
auth = JWTBearer(jwks)
```

`models/JWTBearer.py` uses `python-jose` to verify asymmetric signatures via `kid`-based key lookup and `key.verify()`. This is already a JWKS-based asymmetric pattern — not HS256. The class itself does not need changes; only the JWKS URL source changes.

### Supabase Auth JWT Configuration (Critical Decision Point)

Supabase has two JWT signing modes:

**Legacy (HS256, shared secret):** Default for most existing projects. A symmetric key visible in Settings → Auth → JWT Settings. The JWKS endpoint returns an empty key set for HS256 projects — the current `JWTBearer` startup code would fail with an empty `kid_to_jwk` dict.

**Asymmetric (ES256 / RS256, JWKS):** Recommended; becoming the new default. New projects created after May 2025 use asymmetric keys by default. JWKS endpoint: `https://[PROJECT-REF].supabase.co/auth/v1/.well-known/jwks.json`.

Because the existing `JWTBearer` already does asymmetric JWKS-based verification, the cleanest path is to enable asymmetric signing on the Supabase project and point `core/auth.py` at Supabase's JWKS endpoint. This requires zero structural changes to `JWTBearer` — only the URL in `core/auth.py` changes.

### Table Stakes Steps

**1. Enable asymmetric JWT signing in the Supabase dashboard.**

Settings → Auth → JWT Settings → "Migrate JWT secret" → follow prompts to rotate to an asymmetric key (ES256 is the Supabase recommendation). For new projects created after May 2025, asymmetric is already the default. Confirm by fetching the JWKS endpoint and checking the `keys` array is non-empty.

**2. Update `core/auth.py` to fetch from Supabase's JWKS endpoint.**

The change is minimal — replace the Cognito URL construction with the Supabase JWKS URL:

```
Old: https://cognito-idp.{REGION}.amazonaws.com/{POOL_ID}/.well-known/jwks.json
New: https://[PROJECT-REF].supabase.co/auth/v1/.well-known/jwks.json
```

The `JWTBearer` class itself needs no changes.

**3. Update `core/config.py` env var reads.**

Remove reads of `COGNITO_REGION` and `COGNITO_POOL_ID`. Add `SUPABASE_URL` (the project's base URL, e.g. `https://abcdef.supabase.co`).

**4. Audience claim behavior.**

Supabase JWTs include `aud: "authenticated"` in the payload. The current `JWTBearer` does not check audience — it only verifies the signature. This is fine and matches Supabase's own guidance (their examples explicitly set `"verify_aud": False`). No change needed.

**5. HS256 fallback consideration.**

If asymmetric signing cannot be enabled (e.g., legacy project constraints), the JWKS endpoint returns an empty key set and startup will fail. Alternative for HS256 projects: verify using `jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})` using `python-jose`. This requires a different code path in `JWTBearer`. The simpler path is to just enable asymmetric signing — it is always available in the dashboard.

### User Management Approach

The migration is a fresh start — no user data from Cognito needs to be imported.

Supabase Auth provides REST endpoints directly. No Python SDK required for a backend-only service:

| Action | Endpoint |
|--------|----------|
| Sign up (email+password) | `POST https://[PROJECT].supabase.co/auth/v1/signup` |
| Sign in (email+password) | `POST https://[PROJECT].supabase.co/auth/v1/token?grant_type=password` |
| Get user info | `GET https://[PROJECT].supabase.co/auth/v1/user` with `Authorization: Bearer [access_token]` |
| Admin: create user | `POST https://[PROJECT].supabase.co/auth/v1/admin/users` with service role key |

All endpoints require `apikey: [SUPABASE_ANON_KEY]` in the request header. Sign-in returns `access_token` (a JWT) + `refresh_token`. The `access_token` is what gets passed to the FastAPI backend as a Bearer token — the same flow as Cognito.

The frontend handles auth flows (signup, signin, token storage). The backend only verifies the incoming JWT.

**Email confirmation:** Supabase requires email confirmation by default. Disable it in Settings → Auth → Email for development and testing. Configure SMTP in Settings → Auth → SMTP Settings for production.

### Dashboard Configuration Required

- Enable asymmetric JWT signing (Settings → Auth → JWT Settings → Migrate JWT secret)
- Note down: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- Disable email confirmation for development (Settings → Auth → Email → "Confirm email")
- Configure SMTP for production email delivery

---

## Supabase-Specific Features to Leverage

### Connection Pooling (Supavisor) — LOW priority for this migration

Supabase provides Supavisor automatically. For the current usage pattern (long-running FastAPI server, sync SQLAlchemy, low-to-medium traffic), the direct connection is simplest and sufficient. Supavisor session mode is a reasonable upgrade when connection count becomes a concern at scale.

Key fact: the sync SQLAlchemy engine (psycopg2) works with all three connection types (direct, session pooler, transaction pooler) without issues. The asyncpg issue only affects the async path.

### Row Level Security (RLS) — skip for this migration

RLS is a Postgres-native feature Supabase surfaces prominently, but it is not relevant for this project:

- Tables created via raw SQL (which Alembic does) do NOT have RLS enabled by default. Explicit `ALTER TABLE x ENABLE ROW LEVEL SECURITY;` is required.
- The FastAPI backend connects as the `postgres` role (superuser), which has `BYPASSRLS` privilege — RLS policies have no effect on any SQLAlchemy queries.
- RLS only matters for connections via Supabase's auto-generated REST API (PostgREST) using the `anon` or `authenticated` roles.
- The app uses SQLAlchemy directly, not PostgREST. RLS is irrelevant for all 13 tables.

Do not enable RLS on any table during this migration. It adds complexity without benefit given the current architecture.

### Supabase Dashboard SQL Editor

Useful for verifying Alembic migrations applied correctly. After `alembic upgrade head`, run:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
```
This should return 13 tables plus `alembic_version`.

### Postgres Extensions (pgvector)

Supabase pre-installs `pgvector`. The project already has `pgvector==0.3.6` in requirements. If a future phase uses Postgres vector columns, the extension is already available — no manual installation needed.

---

## Not Needed for This Migration

**Supabase Python SDK (`supabase-py`).** The backend verifies JWTs and queries Postgres via SQLAlchemy directly. The SDK wraps auth flows, storage, and PostgREST. None of those surfaces are used here.

**PostgREST (Supabase auto-generated REST API).** The app exposes its own FastAPI REST API. The Supabase-generated API is a separate interface not consumed by anything in this project.

**Supabase Storage.** The app does not store files.

**Supabase Realtime.** The app uses SSE via FastAPI's `StreamingResponse`. Supabase Realtime is not applicable.

**Supabase Edge Functions.** All compute runs in the FastAPI server.

**Supabase CLI / local development stack.** The migration targets Supabase Cloud. The CLI is useful for local dev but not required for this migration.

**Cognito as third-party JWT provider.** Supabase can accept Cognito JWTs alongside Supabase Auth via a third-party integration. This is for gradual dual-auth migrations. Since this is a fresh start, skip it entirely.

**User import tooling.** No data migration means no need to export Cognito user records or import into `auth.users`. Users re-register on Supabase Auth.

---

## Dependency Map: DB Migration vs Auth Migration

These two workstreams are independent and can proceed in parallel after the Supabase project is created:

```
Prerequisite: Create Supabase project
    |
    ├── DB migration path (independent)
    |     Update DB_* env vars
    |     → run alembic upgrade head
    |     → verify 13 tables in dashboard
    |
    └── Auth migration path (independent)
          Enable asymmetric signing in dashboard
          → update SUPABASE_URL env var
          → update core/auth.py fetch URL (3-line change)
          → remove COGNITO_* vars from config

Cutover gate (requires both complete):
    Verify /chat/stream/agentic end-to-end with:
    - Supabase-issued JWT (Bearer token from auth/v1/token)
    - Supabase Postgres-backed DB session
```

---

## Complexity Assessment

| Step | Complexity | Notes |
|------|------------|-------|
| Create Supabase project | Low | Dashboard, ~2 minutes |
| Update DB env vars | Low | Change 5 vars, zero code change |
| Run alembic upgrade head | Low | Already works; direct connection avoids pooler issues |
| Verify 13 tables applied | Low | SQL editor or psql |
| Enable asymmetric JWT in dashboard | Low | 2-3 clicks |
| Update JWKS fetch URL in core/auth.py | Low | 3-line change |
| Remove COGNITO_* vars, add SUPABASE_URL | Low | Config cleanup |
| Update ASYNC_DATABASE_URL | Low | Point at direct connection; async path currently unused |
| Test JWT verification end-to-end | Medium | Need Supabase Auth user, access token, send to /chat endpoint |
| RLS | None | Skip entirely for this migration |

**Total estimated implementation work: 2-4 hours including end-to-end testing.**

---

## Sources

- [Supabase: Connect to your database](https://supabase.com/docs/guides/database/connecting-to-postgres) — connection string formats, direct vs pooler guidance
- [Supabase: JWT documentation](https://supabase.com/docs/guides/auth/jwts) — JWKS endpoint URL, algorithm notes
- [Supabase: JWT Signing Keys](https://supabase.com/docs/guides/auth/signing-keys) — migration from HS256 to asymmetric
- [Supabase: Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security) — RLS defaults, service role bypass
- [Supabase: Password-based Auth](https://supabase.com/docs/guides/auth/passwords) — REST API endpoints for signup/signin
- [Supabase: AWS Cognito third-party integration](https://supabase.com/docs/guides/auth/third-party/aws-cognito) — why to skip this approach
- [objectgraph.com: Migrating Supabase JWT to JWKS](https://objectgraph.com/blog/migrating-supabase-jwt-jwks/) — Python HS256 vs JWKS verification code patterns
- [GitHub: asyncpg + Supabase prepared statement errors](https://github.com/supabase/supabase/issues/39227) — confirmed 2024-2025 incompatibility
- [GitHub Discussion: Asymmetric Keys default timeline 2025](https://github.com/orgs/supabase/discussions/29289) — May 2025 new project defaults
- [dev.to: Integrating FastAPI with Supabase Auth](https://dev.to/j0/integrating-fastapi-with-supabase-auth-780) — python-jose + audience claim pattern
