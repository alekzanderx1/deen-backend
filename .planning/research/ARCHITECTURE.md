# Architecture: Supabase Migration

**Project:** Deen Backend v1.1 — Supabase Postgres + Auth
**Researched:** 2026-04-06
**Scope:** Integration points for replacing AWS RDS + Cognito with Supabase Postgres + Supabase Auth in the existing FastAPI + SQLAlchemy + JWTBearer stack

---

## Files That Change

### `core/auth.py` — MODIFY

Currently fetches JWKS from Cognito at startup using `requests.get` to:
`https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_POOL_ID}/.well-known/jwks.json`

**What changes:**
- Replace the JWKS URL with Supabase's endpoint: `https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`
- Replace `from core.config import COGNITO_POOL_ID, COGNITO_REGION` with `from core.config import SUPABASE_URL`
- Construct the URL as `f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"`
- The `JWTBearer` class import, the `JWKS.model_validate()` call, and the `auth = JWTBearer(jwks)` line all remain unchanged — the JWKS JSON response format (`{"keys": [...]}`) is the same standard structure in both Cognito and Supabase.

**Confidence:** HIGH — Supabase JWKS endpoint is at the same standard path; the existing `python-jose`-based `JWTBearer` is algorithm-agnostic and works with Supabase's asymmetric keys.

---

### `core/config.py` — MODIFY

Currently exposes `COGNITO_REGION` and `COGNITO_POOL_ID` as module-level variables.

**What changes:**
- Remove: `COGNITO_REGION = os.getenv("COGNITO_REGION")` and `COGNITO_POOL_ID = os.getenv("COGNITO_POOL_ID")`
- Add: `SUPABASE_URL = os.getenv("SUPABASE_URL")` — the base URL used in `core/auth.py`
- Add: `SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")` — used in `api/account.py` for admin user deletion
- DB env var names (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DATABASE_URL`, `ASYNC_DATABASE_URL`) do not change. Only the `.env` values change to point at Supabase.

---

### `db/session.py` — MODIFY (only if using transaction pooler; no change for direct connection)

Currently: `create_engine(..., connect_args={"sslmode": "require"})` — no pool configuration beyond `pool_pre_ping=True`.

**If using the transaction pooler (port 6543):** Supavisor's transaction mode does not support named prepared statements across connection hops. Add:
```python
connect_args={
    "sslmode": "require",
    "prepare_threshold": None,   # disables named prepared statements
},
pool_recycle=60,   # recycle before Supavisor's idle timeout
```

**If using the direct connection (port 5432):** No changes to `db/session.py`. Direct connections behave identically to RDS Postgres — `pool_pre_ping=True` and `sslmode=require` are both fine as-is.

The choice of direct vs pooler is deployment-environment dependent (see Database Connection Changes section).

---

### `api/account.py` — MODIFY

Contains the `DELETE /account` endpoint which, after deleting DB rows and clearing Redis, calls `boto3.client('cognito-idp').admin_delete_user()` to delete the user from Cognito.

**What changes:**
- Remove the `boto3` import and the Cognito deletion block (the `Step 3` block, approximately lines 82–120).
- Remove `from core.config import COGNITO_REGION, COGNITO_POOL_ID`.
- Replace with a call to the Supabase Admin API:
  `DELETE https://<project-ref>.supabase.co/auth/v1/admin/users/<user_id>`
  using `httpx` (already in `requirements.txt`) with `Authorization: Bearer <SUPABASE_SERVICE_ROLE_KEY>`.
- The `credentials.claims.get("sub")` call (line ~49) is unchanged — `sub` is present with identical semantics (UUID user ID) in both Cognito and Supabase JWTs.
- Remove the `credentials.claims.get("cognito:username")` call (line ~90) — this claim does not exist in Supabase JWTs. The Supabase Admin API uses the user UUID (`sub`) for deletion, so no equivalent is needed.

**Confidence:** HIGH — Supabase provides an Admin REST API for user management; `sub` is the user UUID in both systems.

---

### `.env` — MODIFY (values and keys)

**Remove keys:**
```
COGNITO_REGION=
COGNITO_POOL_ID=
```

**Add keys:**
```
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service-role-key-from-supabase-dashboard>
```

**Change values (key names stay the same):**
```
DB_HOST=db.<project-ref>.supabase.co        # direct connection host
DB_PORT=5432                                 # 5432 direct, or 6543 for transaction pooler
DB_NAME=postgres
DB_USER=postgres                             # or postgres.<project-ref> for transaction pooler
DB_PASSWORD=<supabase-db-password>
```

---

## Files That Stay the Same

| File | Reason |
|------|--------|
| `models/JWTBearer.py` | Purely JWKS-based. Verifies JWT signature by looking up the `kid` from the token header, constructing a `jwk` object via `python-jose`, and verifying the signature. This logic is algorithm-agnostic — it works identically with Supabase's ES256 or RS256 keys. No code changes. |
| `api/chat.py` | Extracts user ID via `credentials.claims.get("sub")`. The `sub` claim is semantically identical in Supabase JWTs (UUID user ID). All Redis key scoping and DB session lookups use this value unchanged. |
| `db/config.py` | Pydantic `Settings` reads `DB_*` env vars and constructs `DATABASE_URL`. The structure is unchanged; only the env var values change. |
| `alembic/env.py` | Already reads `settings.DATABASE_URL` from `db.config` at runtime. No code change. Only env values change. |
| `alembic.ini` | The `sqlalchemy.url` placeholder is overridden by `env.py` at runtime. No change. |
| `alembic/versions/` (all 7 migrations) | Plain DDL migrations. Supabase Postgres is standard PostgreSQL 15+. All migrations run without modification. |
| `db/models/` (all 13 models) | Standard SQLAlchemy ORM models. No RDS-specific or Cognito-specific code. |
| `main.py` | `from core.auth import jwks` and `auth = JWTBearer(jwks)` are unchanged. `core/auth.py` handles the Supabase URL internally. |
| `core/memory.py` | Redis — entirely unaffected. |
| `core/vectorstore.py` | Pinecone — entirely unaffected. |
| `agents/`, `modules/`, `services/` | No auth construction or DB session creation. Entirely unaffected. |
| `core/pipeline_langgraph.py` | No auth or DB session construction. Entirely unaffected. |

---

## Supabase Auth JWT Structure

### Signing Algorithm

Supabase defaults to **ES256** (NIST P-256 elliptic curve) for new projects. Legacy projects may use **RS256** or the discouraged **HS256** (shared secret). The existing `JWTBearer.verify_jwk_token()` uses `python-jose`'s `jwk.construct()`, which supports both RSA and EC key types. ES256 and RS256 both work with the existing verification code without any algorithm-specific changes — the JWKS `kid` lookup drives the right key.

**If the Supabase project uses HS256 (legacy/shared secret):** The existing JWKS-based flow breaks because Supabase's JWKS endpoint returns nothing when HS256 is configured — shared secrets are not public. In that case, verification requires a different approach: decode locally using the JWT secret string from Supabase dashboard settings (Project Settings → API → JWT Secret) with `jose.jwt.decode(..., algorithms=["HS256"])`. This is a separate code path that the existing `JWTBearer` class does not support. **Recommendation: configure Supabase to use ES256 (the default for new projects) to avoid this.**

**Confidence:** HIGH — from Supabase signing keys documentation.

### Claims Comparison: Cognito vs Supabase

| Claim | AWS Cognito (ID token) | Supabase Auth |
|-------|------------------------|---------------|
| `iss` | `https://cognito-idp.<region>.amazonaws.com/<pool-id>` | `https://<project-ref>.supabase.co/auth/v1` |
| `aud` | `<app-client-id>` (a specific client UUID) | `"authenticated"` (literal string) |
| `sub` | UUID — user's Cognito ID | UUID — user's Supabase ID |
| `email` | `email` | `email` |
| `role` | Not present | `"authenticated"` or `"anon"` |
| `cognito:username` | Present | **Absent** |
| `token_use` | `"id"` | **Absent** |
| `session_id` | Absent | Present (Supabase session UUID) |
| `aal` | Absent | `"aal1"` or `"aal2"` (auth assurance level) |
| `is_anonymous` | Absent | Present (boolean) |
| `app_metadata` | Absent | Present (object, optional) |
| `user_metadata` | Absent | Present (object, optional) |
| `amr` | Absent | Present (authentication methods reference, optional) |

### Impact on Claim Reads in the Codebase

- **`credentials.claims.get("sub")`** — Used in `api/chat.py` (`_extract_user_id`), `api/account.py`, and transitively via all user-scoped Redis key construction. Identical in both systems. No change.
- **`credentials.claims.get("email")`** — Used in `api/account.py` for logging. Present in Supabase. No change.
- **`credentials.claims.get("cognito:username")`** — Used only in `api/account.py` to determine the Cognito username for `admin_delete_user`. This claim does not exist in Supabase JWTs and the entire Cognito deletion block is being replaced. Remove this line.
- **`credentials.claims.get("aud")`** — Not read anywhere in the codebase. The existing `JWTBearer` does not validate audience. No change needed.
- **`credentials.claims.get("iss")`** — Not read anywhere in the codebase. No change needed.

---

## Database Connection Changes

### Direct Connection (Recommended for this deployment)

The backend is a persistent FastAPI server running under Gunicorn with Uvicorn workers — not serverless or edge-function based. Supabase's own documentation explicitly recommends direct connections for persistent servers.

```
Host:     db.<project-ref>.supabase.co
Port:     5432
Database: postgres
User:     postgres
SSL:      sslmode=require  (already set, no change needed)
```

**IPv6 caveat:** Supabase direct connections resolve to IPv6 addresses only. If the deployment host (VM, VPS, Docker host) does not support IPv6, the direct connection will fail. Verify the host supports IPv6 before committing to this option. If not, use the session pooler (same config but via `aws-0-<region>.pooler.supabase.com` at port 5432, with `DB_USER=postgres.<project-ref>`).

**Confidence:** HIGH — Supabase docs; direct connection behavior is standard PostgreSQL.

### Transaction Pooler (Only if IPv4 is strictly required)

```
Host:     aws-0-<region>.pooler.supabase.com
Port:     6543
Database: postgres
User:     postgres.<project-ref>   (note: includes project ref)
SSL:      sslmode=require
```

If using the transaction pooler, update `db/session.py`:
```python
connect_args={
    "sslmode": "require",
    "prepare_threshold": None,   # required: disables named prepared statements for Supavisor compat
},
pool_recycle=60,   # recycle connections before Supavisor idle timeout
```

Named prepared statements do not survive connection hops in transaction mode — omitting `prepare_threshold=None` causes intermittent `PreparedStatementError` in production under load.

**Confidence:** HIGH — documented in Supabase community discussions and GitHub issues.

### Session Pooler (Alternative for IPv4)

```
Host:     aws-0-<region>.pooler.supabase.com
Port:     5432
Database: postgres
User:     postgres.<project-ref>
SSL:      sslmode=require
```

Session pooler is similar to direct but works over IPv4. It maintains one real DB connection per app-level connection, so it does not have the prepared statement issue. No changes to `db/session.py` required beyond the env var values. Suitable as a drop-in replacement for direct connections when IPv4 is required and the persistent-server pool model is preferred.

### Alembic

`alembic/env.py` already calls `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)` at runtime, pulling from `db.config.Settings`. After updating `.env` values to point at Supabase, run:

```bash
alembic upgrade head
```

This applies all 7 migrations to the fresh Supabase Postgres database. No changes to `alembic.ini` or `alembic/env.py` are needed.

**Pre-migration step:** Enable the `pgvector` extension in the Supabase dashboard before running migrations (Database tab → Extensions → search "vector" → enable). The `db/models/embeddings.py` model likely depends on this extension. If it is not enabled, the migration that creates the embeddings table will fail.

---

## Build Order

The two workstreams (DB and Auth) are independent and can be developed in parallel. However, they must both be complete before end-to-end integration testing.

### Phase 1 — Database (infra + env only, zero code changes)

1. Provision a Supabase project.
2. Enable the `pgvector` extension in the Supabase dashboard.
3. Update `.env`: set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` to Supabase values.
4. Run `alembic upgrade head` to apply all 7 migrations.
5. Validate with `GET /_debug/db` — confirms SQLAlchemy engine connects and returns the Postgres version string.
6. Run `pytest tests -q` — confirms the DB layer functions identically.

**Rationale:** No code risk. Completing this first proves the schema is intact before any application code is touched.

### Phase 2 — Auth (code changes in 3 files)

1. Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to `.env`.
2. Update `core/config.py`: remove Cognito vars, add Supabase vars.
3. Update `core/auth.py`: replace JWKS URL construction.
4. Update `api/account.py`: remove boto3 Cognito deletion block, replace with Supabase Admin API call using `httpx`.
5. Remove `COGNITO_REGION` and `COGNITO_POOL_ID` from `.env`.
6. Test the auth flow end-to-end by hitting `/chat/stream/agentic` with a real Supabase-issued JWT.

**Dependency on Phase 1:** Auth changes can be written and unit-tested without a live Supabase DB. But full end-to-end testing requires Phase 1 to be complete (the app needs a working DB connection at startup).

### Phase 3 — Cleanup

1. Remove `boto3==1.35.96` from `requirements.txt` (it has no remaining users after Phase 2).
2. Remove Cognito env var entries from all Dockerfiles and CI configs.
3. Verify `CORS_ALLOW_ORIGINS` still covers the frontend origin (unchanged — no Supabase dependency here).
4. Update deployment runbook with new env var list.

---

## New Components Needed

No new files are required. All changes are modifications to existing files.

### New Environment Variables

| Variable | Purpose | Replaces |
|----------|---------|---------|
| `SUPABASE_URL` | Base URL for JWKS endpoint in `core/auth.py` (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`) | `COGNITO_REGION` + `COGNITO_POOL_ID` (both were used only to construct the Cognito JWKS URL) |
| `SUPABASE_SERVICE_ROLE_KEY` | Authorization header for Supabase Admin API calls in `api/account.py` | Implicitly used Cognito via boto3 AWS credentials chain |

### Removed Environment Variables

| Variable | Why Removed |
|----------|-------------|
| `COGNITO_REGION` | Only used to build Cognito JWKS URL and Cognito `admin_delete_user` call |
| `COGNITO_POOL_ID` | Only used to build Cognito JWKS URL and Cognito `admin_delete_user` call |

### Removable Dependency

`boto3==1.35.96` in `requirements.txt` is used exclusively by `api/account.py` for the Cognito `admin_delete_user` call. After the migration, it has no callers and can be removed. This is cosmetic but reduces Docker image size.

---

## Sources

- [Supabase JWT Claims Reference](https://supabase.com/docs/guides/auth/jwt-fields) — HIGH confidence, official docs
- [Supabase JSON Web Token (JWT)](https://supabase.com/docs/guides/auth/jwts) — HIGH confidence, official docs
- [Supabase JWT Signing Keys](https://supabase.com/docs/guides/auth/signing-keys) — HIGH confidence, official docs
- [Supabase Connect to Database](https://supabase.com/docs/guides/database/connecting-to-postgres) — HIGH confidence, official docs
- [Supabase SSL Enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement) — HIGH confidence, official docs
- [SQLAlchemy with Supabase Community Discussion](https://github.com/orgs/supabase/discussions/27071) — MEDIUM confidence, community-verified patterns
- [FastAPI + Supabase JWT verification (Python)](https://dev.to/zwx00/validating-a-supabase-jwt-locally-with-python-and-fastapi-59jf) — MEDIUM confidence, community article
