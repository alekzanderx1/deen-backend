# Stack: Supabase Migration

**Project:** Deen Backend v1.1 — Supabase Migration
**Researched:** 2026-04-06
**Scope:** AWS RDS + Cognito → Supabase Postgres + Supabase Auth

---

## What Changes

### Packages to REMOVE

None need to be removed from `requirements.txt`. `boto3` is listed in requirements; it can stay if used for other AWS services — it is not actively used for Cognito JWT verification (that is handled by `python-jose` + JWKS fetch, not boto3).

### Packages to ADD

**None required.** The existing `python-jose`, `psycopg2-binary`, and `asyncpg` all work with Supabase without any additions.

**Do NOT add `supabase-py`:** The supabase-py SDK wraps Supabase's PostgREST REST API, Auth REST API, Storage, and Realtime — none of which this app needs. This backend uses SQLAlchemy directly against the Postgres TCP connection string, and verifies JWTs locally via JWKS. Adding supabase-py introduces 10+ transitive dependencies for zero benefit. A recent supabase-py issue (v2.15 migration to JWKS) caused `get_user()` to break silently — the manual JWKS verification approach this app already uses is more robust and fully under your control.

### Environment Variables to CHANGE

| Old Variable | Old Value Example | New Variable | New Value Example |
|-------------|-------------------|-------------|-------------------|
| `COGNITO_REGION` | `us-east-1` | `SUPABASE_PROJECT_REF` | `abcdefghijkl` (the subdomain portion of your project URL) |
| `COGNITO_POOL_ID` | `us-east-1_XxXxXxXx` | *(derived from `SUPABASE_PROJECT_REF`)* | — |
| `DB_HOST` | `*.rds.amazonaws.com` | `DB_HOST` | `db.<project-ref>.supabase.co` |
| `DB_PORT` | `5432` | `DB_PORT` | `5432` (unchanged — use direct connection, NOT 6543) |
| `DB_USER` | *(whatever RDS user)* | `DB_USER` | `postgres` (Supabase default) |
| `DB_PASSWORD` | *(RDS password)* | `DB_PASSWORD` | Supabase DB password from dashboard |
| `DB_NAME` | *(whatever RDS DB)* | `DB_NAME` | `postgres` (Supabase default) |

`DATABASE_URL` and `ASYNC_DATABASE_URL` in `.env` continue to work if set directly, since `core/config.py`'s `build_database_url()` uses them as-is. The `db/config.py` `Settings` class builds `DATABASE_URL` from `DB_*` vars via `URL.create()` — no change to that code is needed.

### Code Changes Required

**`core/auth.py`** — swap the JWKS endpoint URL (one line change):

```python
# OLD (Cognito)
f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_POOL_ID}/.well-known/jwks.json"

# NEW (Supabase)
f"https://{SUPABASE_PROJECT_REF}.supabase.co/auth/v1/.well-known/jwks.json"
```

Also update the config imports: replace `COGNITO_REGION`, `COGNITO_POOL_ID` with `SUPABASE_PROJECT_REF` in `core/config.py` and `core/auth.py`.

**`models/JWTBearer.py`** — no changes. The JWKS-based `kid` lookup + signature verification using `python-jose` is provider-agnostic and works identically for Supabase RS256/ES256 keys.

**`db/session.py`** — no changes. The `connect_args={"sslmode": "require"}` already set is correct for Supabase.

**`core/config.py`** — remove `COGNITO_REGION`, `COGNITO_POOL_ID`; add `SUPABASE_PROJECT_REF`.

---

## What Stays the Same

| Component | Notes |
|-----------|-------|
| `psycopg2-binary==2.9.10` | Works with Supabase Postgres direct connection unchanged |
| `asyncpg==0.30.0` | Works with Supabase Postgres **on port 5432 only** (see connection string section) |
| `SQLAlchemy==2.0.41` | Same ORM, same session factory, same engine config |
| `alembic==1.14.0` | All 13 tables and 6 migration files apply unmodified to Supabase Postgres |
| `python-jose==3.5.0` | Already handles RS256/ES256 via JWKS `kid` lookup — same code path for Supabase |
| `pydantic-settings` DB config | `db/config.py` `Settings` class unchanged |
| `db/session.py` engine | `connect_args={"sslmode": "require"}` already set — correct for Supabase |
| All 13 SQLAlchemy models | Schema is standard SQL, fully portable |
| `models/JWTBearer.py` | JWKS verification logic is provider-agnostic |
| Redis conversation memory | No Supabase involvement whatsoever |
| All API endpoints | Zero behavior changes — infrastructure swap only |

---

## Connection String Format

### Direct Connection (use this — port 5432)

Supabase provides a direct PostgreSQL connection on port **5432** that bypasses all proxies. Use this for the FastAPI backend.

**psycopg2 (sync, `db/session.py`):**
```
postgresql+psycopg2://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

**asyncpg (async, `ASYNC_DATABASE_URL`):**
```
postgresql+asyncpg://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

The existing `db/config.py` `Settings.DATABASE_URL` property builds the correct string from `DB_*` env vars using `URL.create()` — set `DB_HOST=db.<project-ref>.supabase.co`, `DB_PORT=5432`, `DB_USER=postgres`, `DB_NAME=postgres`, `DB_PASSWORD=<your-password>`.

### Do NOT use the Transaction Pooler (port 6543)

Supabase also offers a PgBouncer transaction-mode pooler on port **6543**. Do not use it.

**Why:** asyncpg uses named prepared statements internally. PgBouncer transaction mode does not maintain prepared statements across pooled connections, causing `prepared statement '__asyncpg_stmt_1__' already exists` on startup. This is a confirmed, known incompatibility. The direct connection on 5432 bypasses PgBouncer entirely and works correctly.

**IPv4 fallback:** Supabase direct connections use IPv6 by default. If the deployment host only supports IPv4, use the **Session Mode pooler** instead — it is IPv4-compatible and session mode preserves prepared statements:
```
postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
```
Note: the username format changes to `postgres.<project-ref>` for pooler connections.

### SSL Configuration

The existing `db/session.py` sets `connect_args={"sslmode": "require"}`. This is correct and requires no change.

Supabase does not enforce SSL by default (for client compatibility), but `sslmode=require` is appropriate for any production deployment. No SSL certificate file download is needed unless you explicitly enable SSL enforcement with `verify-full` mode in the Supabase dashboard (which you do not need to do).

---

## Supabase Auth JWKS

### JWKS Endpoint URL

```
GET https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
```

Replace `<project-ref>` with your Supabase project reference ID (the subdomain of your project URL). The endpoint returns a standard JWKS response. It is cached at Supabase's edge for 10 minutes. The existing startup JWKS fetch in `core/auth.py` works identically — just point it at this URL.

### JWT Claims

| Claim | Value for Supabase Auth |
|-------|------------------------|
| `iss` | `https://<project-ref>.supabase.co/auth/v1` |
| `aud` | `authenticated` (logged-in users) or `anon` (anonymous) |
| `sub` | UUID — Supabase Auth user ID |
| `role` | `authenticated`, `anon`, or `service_role` |
| `exp` | Unix timestamp — expiry |
| `email` | User's email address |
| `session_id` | Unique session UUID |

**The `aud` claim is `"authenticated"`** for all non-anonymous user tokens. Cognito tokens had a different `aud` convention. The current `JWTBearer.verify_jwk_token()` only verifies the signature against the JWKS key — it does not validate `aud`, `iss`, or `exp` explicitly. This means the migration requires no claim-validation code changes. If you want to add `aud`/`iss` validation later, use `jose.jwt.decode()` with `audience="authenticated"` and `issuer=...`.

### JWT Signing Algorithm

New Supabase projects (created after May 2025) use **RS256 (RSA 2048)** asymmetric signing by default. Older projects may use HS256 (symmetric shared secret).

**Confirm which your project uses:** After creating a test user token, run:
```python
from jose import jwt
print(jwt.get_unverified_header(token))  # look at the "alg" field
```

Or check the Supabase dashboard under Authentication > Signing Keys.

**If RS256 (most likely for new projects):** The JWKS endpoint returns RSA public keys. The existing `JWTBearer` code handles this correctly — `jwk.construct(public_key)` in `python-jose` handles RS256 keys from JWKS without any code changes.

**If HS256 (older project or self-hosted):** The JWKS endpoint will return an empty `keys` array. The current `JWTBearer` will fail with "JWK public key not found" because there are no asymmetric keys to look up. In this case, replace the JWKS-based verification with symmetric verification:
```python
jose.jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
```
The `SUPABASE_JWT_SECRET` is available in the Supabase dashboard under Settings > API > JWT Secret.

The overwhelming recommendation — and Supabase's own guidance — is to use asymmetric JWKS verification (RS256/ES256). Use a new project or migrate to asymmetric keys if HS256 is the current state.

---

## Recommendations

### 1. Use Direct Connection on Port 5432

Set `DB_HOST=db.<project-ref>.supabase.co` and `DB_PORT=5432`. Zero code changes to `db/session.py`, `db/config.py`, or the SQLAlchemy engine. The existing `connect_args={"sslmode": "require"}` is correct.

### 2. Do Not Add supabase-py

This backend has no use for the Supabase REST wrappers. SQLAlchemy owns all DB access. JWT verification works via `python-jose` + JWKS. Adding supabase-py would introduce package bloat and a dependency that has caused known breakage post-JWKS migration.

### 3. The Auth Change is One URL String

`core/auth.py` changes one URL. `models/JWTBearer.py` is untouched. `python-jose` handles Supabase RS256 JWKS keys identically to Cognito RS256 JWKS keys — the JWKS key lookup by `kid` is the standard pattern and is provider-agnostic.

### 4. Verify JWT Algorithm Before Deploying

After spinning up the Supabase project, create a test token and inspect the header. Confirm `alg` is `RS256` (or `ES256`) before running in production. If it is `HS256`, the JWKS-based verification will silently fail at runtime.

### 5. Run Alembic Immediately Against Supabase

Supabase runs standard PostgreSQL 15. All 13 SQLAlchemy models and all 6 Alembic migration files apply without modification. Run `alembic upgrade head` with the new `DATABASE_URL` to provision the schema.

### 6. IPv4 Fallback if Needed

If your deployment environment (existing VPS, Docker host, or cloud region) does not support IPv6, direct connection to `db.<project-ref>.supabase.co` will time out. Switch to the Session Mode pooler (`aws-0-<region>.pooler.supabase.com:5432`) — it is IPv4-compatible, does not break prepared statements, and requires only changing `DB_HOST` and `DB_USER` (to `postgres.<project-ref>`).

---

## Sources

- [Supabase: Connect to your database](https://supabase.com/docs/guides/database/connecting-to-postgres) — direct vs pooler connection strings, port 5432 vs 6543, IPv4/IPv6 notes (MEDIUM confidence — official docs)
- [Supabase: JWT Claims Reference](https://supabase.com/docs/guides/auth/jwt-fields) — iss, aud, sub, role, session_id claim values (HIGH confidence — official docs)
- [Supabase: JWT Signing Keys](https://supabase.com/docs/guides/auth/signing-keys) — RS256/ES256/HS256 signing modes, JWKS discovery (HIGH confidence — official docs)
- [Supabase: JSON Web Token (JWT)](https://supabase.com/docs/guides/auth/jwts) — JWKS URL format, edge caching behavior (HIGH confidence — official docs)
- [Supabase: SSL Enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement) — sslmode=require is appropriate default (HIGH confidence — official docs)
- [Medium: Supabase Pooling and asyncpg Don't Mix](https://medium.com/@patrickduch93/supabase-pooling-and-asyncpg-dont-mix-here-s-the-real-fix-44f700b05249) — port 6543 breaks asyncpg prepared statements; fix is port 5432 (MEDIUM confidence — community, verified against Supabase docs behavior)
- [GitHub Discussion: Verifying Supabase JWT Myself](https://github.com/orgs/supabase/discussions/20763) — aud="authenticated", HS256 manual verification approach (MEDIUM confidence — community discussion)
- [GitHub: supabase-py issue #1183](https://github.com/supabase/supabase-py/issues/1183) — get_user() breakage after JWKS migration; manual JWKS verification is more robust (MEDIUM confidence — issue report)
- [GitHub Discussion: Using SQLAlchemy with Supabase](https://github.com/orgs/supabase/discussions/27071) — connect_args for disabling prepared statements relevant only for pooler mode (MEDIUM confidence — community discussion)
- Codebase read: `models/JWTBearer.py`, `core/auth.py`, `db/session.py`, `db/config.py`, `core/config.py` — confirmed current Cognito JWKS pattern, existing sslmode=require, existing DB config structure (HIGH confidence — direct source read)
