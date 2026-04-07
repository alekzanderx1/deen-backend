# Pitfalls: Supabase Migration (v1.1)

**Project:** Deen Backend — v1.1 Supabase Migration
**Researched:** 2026-04-06
**Scope:** Migrating existing FastAPI + SQLAlchemy (psycopg2 + asyncpg) + Cognito app to Supabase Postgres + Supabase Auth
**Confidence:** HIGH (direct code inspection + official Supabase docs + confirmed GitHub issues)

---

## Database / SQLAlchemy Pitfalls

### CRITICAL: asyncpg + Supavisor Transaction Pooler = Prepared Statement Crashes

**What goes wrong:** The `ASYNC_DATABASE_URL` (asyncpg driver) will throw
`prepared statement "asyncpg_stmt_X" does not exist` under any meaningful concurrency
when pointed at Supabase's transaction-mode pooler (port 6543). Setting
`statement_cache_size=0` alone in `connect_args` is insufficient — asyncpg internally
creates named prepared statements regardless.

**Why it happens:** Supavisor in transaction mode routes each transaction to potentially
a different Postgres backend connection. Prepared statements are scoped to a specific
backend connection. When the next transaction lands elsewhere, the statement is gone.
asyncpg's internal caching creates these statements even when the developer-visible
cache is disabled.

**Codebase impact:** `ASYNC_DATABASE_URL` is configured but not yet actively wired into
request paths (noted in `CLAUDE.md` — async DB configured but not yet used in routers).
When it is activated, this will immediately fail under load.

**Confirmed fix for async engine:**
```python
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

engine = create_async_engine(
    ASYNC_DATABASE_URL,  # transaction pooler, port 6543
    poolclass=NullPool,  # let Supavisor manage connections externally
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "server_settings": {"jit": "off"},
    },
)
```

**For sync psycopg2 engine** (`db/session.py`): psycopg2 does not create prepared
statements by default. The existing `connect_args={"sslmode": "require"}` is safe
through the pooler. NullPool is not required for the sync engine.

**Phase:** DB migration phase.

**Sources:** [Supabase issue #39227](https://github.com/supabase/supabase/issues/39227),
[Supabase Supavisor FAQ](https://supabase.com/docs/guides/troubleshooting/supavisor-faq-YyP5tI)

---

### CRITICAL: Alembic Must Use the Direct Connection String, Not the Pooler

**What goes wrong:** Running `alembic upgrade head` against the transaction-mode pooler
(port 6543) will fail. Alembic holds an open connection across an entire migration
transaction and uses DDL statements. The pooler recycles connections between transactions,
which is incompatible with this model. Specific failures: `CREATE TABLE` inside a
`BEGIN...COMMIT` block will see the connection dropped mid-migration.

**Supabase provides three different connection strings — pick the right one per use:**

| Purpose | Port | Username format | Where to get it |
|---------|------|-----------------|----------------|
| Alembic migrations | 5432 | `postgres` | Dashboard → Database → Direct |
| Runtime psycopg2 (sync) | 5432 | `postgres` | Direct or session pooler |
| Runtime asyncpg (async) | 6543 | `postgres.<ref>` | Dashboard → Database → Transaction Pooler |

**The username format differs between direct and pooler.** Direct uses `postgres`. Pooler
uses `postgres.<project-ref>`. Mixing these up produces cryptic authentication failures,
not helpful error messages.

**Current `alembic/env.py` already uses `NullPool` — this is correct.** The only change
needed is ensuring `settings.DATABASE_URL` (the psycopg2 URL) points at the direct
connection (port 5432) for migration runs.

**Recommended env var split:**
- `DATABASE_URL` — direct connection (port 5432), used by Alembic and sync SQLAlchemy
- `ASYNC_DATABASE_URL` — transaction pooler (port 6543), used by async SQLAlchemy

**Phase:** DB migration phase.

**Source:** [Supabase Connect to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres)

---

### MODERATE: SSL Parameter Syntax Is Different for asyncpg vs psycopg2

**What goes wrong:** The current `db/session.py` uses `connect_args={"sslmode": "require"}`.
This is correct psycopg2 syntax. asyncpg does NOT accept `sslmode` — it silently ignores
it, potentially connecting without SSL. asyncpg requires `ssl="require"` in `connect_args`.

**Why it matters:** Supabase requires SSL on all connections. A misconfigured asyncpg
connection may appear to work in dev (if Supabase instance permits unencrypted) but fail
in production, or it may accept connections without encryption silently.

**Correct per-driver syntax:**
```python
# psycopg2 sync engine — existing, correct
connect_args={"sslmode": "require"}

# asyncpg async engine — must be ssl=, not sslmode=
connect_args={
    "ssl": "require",
    "statement_cache_size": 0,
    "prepared_statement_cache_size": 0,
}
```

**Phase:** DB migration phase.

**Sources:** [asyncpg sslmode issue #737](https://github.com/MagicStack/asyncpg/issues/737),
[SQLAlchemy sslmode asyncpg issue #6275](https://github.com/sqlalchemy/sqlalchemy/issues/6275)

---

### MODERATE: Direct Connection Is IPv6-Only by Default

**What goes wrong:** Supabase direct connections (port 5432) resolve to an IPv6 address
only by default. If the deployment environment does not support outbound IPv6 — common on
some cloud VMs, Docker hosts, CI runners — the direct connection fails with a timeout or
DNS resolution failure, not a clear IPv6 error.

**When this typically bites:** Local Mac development usually has IPv6 (works). Docker
on some cloud providers does not. Migration CI pipelines on GitHub Actions support IPv6
but not all self-hosted runners do.

**Mitigation options:**
1. Use the session pooler (also port 5432, but dual-stack IPv4+IPv6) instead of the
   raw direct connection for both migrations and runtime sync connections.
2. Purchase the Supabase IPv4 add-on (paid) to get an IPv4-reachable direct connection.
3. Test connectivity from the actual deployment host before assuming it works.

**Phase:** DB migration phase.

**Source:** [Supabase IPv4/IPv6 guide](https://supabase.com/docs/guides/troubleshooting/supabase--your-network-ipv4-and-ipv6-compatibility-cHe3BP)

---

### MODERATE: postgres Role Is Not a True Superuser (Security Patch Applied)

**What goes wrong:** Supabase revoked the PostgreSQL superuser privilege from the `postgres`
role as a security patch. The `postgres` role is highly privileged but cannot perform
superuser-only operations: creating event triggers, modifying Supabase-managed schemas
(`auth`, `storage`, `realtime`), or certain extension installation paths.

**Impact on this project:** The 13 SQLAlchemy ORM tables live in the `public` schema.
Alembic migrations using the `postgres` role can CREATE, ALTER, DROP, and INDEX tables
in `public` without issue. This limitation only matters if migrations attempt to create
extensions (use the Supabase dashboard Extensions page instead) or touch `auth`/`storage`
schemas (don't do this from Alembic).

**Phase:** DB migration phase.

**Sources:** [Supabase security patch](https://github.com/supabase/supabase/discussions/9314),
[Roles superuser docs](https://supabase.com/docs/guides/database/postgres/roles-superuser)

---

## Auth Migration Pitfalls

### CRITICAL: Supabase Defaults to HS256 — JWKS Endpoint Returns Empty Keys

**What goes wrong:** The existing `JWTBearer` in `models/JWTBearer.py` fetches the JWKS
endpoint at startup, builds `self.kid_to_jwk = {jwk["kid"]: jwk for jwk in jwks.keys}`,
and verifies tokens by looking up the key by `kid` header. This is correct for Cognito
(always RS256, always has JWKS keys).

Supabase, by default, signs JWTs with **HS256** (symmetric shared secret). When a project
uses HS256, the JWKS endpoint at
`https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json` returns
`{"keys": []}` — an empty keys array. Asymmetric key entries are only listed when the
project has been configured to use RS256 or ES256.

**Consequence for this codebase:** `self.kid_to_jwk` will be `{}`. Every incoming token
has a `kid` header. The lookup `self.kid_to_jwk[jwt_credentials.header["kid"]]` raises
`KeyError`, which is caught and re-raised as `HTTPException 403: JWK public key not found`.
Every authenticated request will fail immediately after deployment.

**How to detect before writing code:**
```bash
curl https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
# If {"keys":[]}, your project uses HS256 — JWKS approach will not work.
# If {"keys":[{...}]}, your project uses asymmetric keys — existing approach works.
```

**Two resolution paths:**

**Path A — Switch Supabase project to asymmetric keys (recommended):**
In Supabase Dashboard → Authentication → Signing Keys, generate a new RS256 or ES256
key. The JWKS endpoint will then return keys. The existing `JWTBearer` JWKS verification
approach works with only a URL change in `core/auth.py`. This is the Supabase-recommended
approach and preserves the existing architecture.

**Path B — Rewrite JWTBearer for HS256 symmetric verification (faster, default):**
Replace the JWKS-based verifier with a direct decode using the Supabase JWT secret
from Dashboard → Settings → API → JWT Secret. Use `jose.jwt.decode(token, secret,
algorithms=["HS256"])`. The secret must be stored as an environment variable — never
hardcoded.

**Phase:** Auth migration phase. This is the single most likely failure point.

**Sources:** [Supabase JWT docs](https://supabase.com/docs/guides/auth/jwts),
[JWT Signing Keys](https://supabase.com/docs/guides/auth/signing-keys),
[Empty JWKS discussion](https://github.com/orgs/supabase/discussions/36212)

---

### MODERATE: Audience Claim Value Is Incompatible With Cognito Pattern

**What goes wrong:** Cognito ID tokens set `aud` to the Cognito App Client ID (a UUID-like
string, e.g., `3abc456def...`). Supabase JWTs set `aud` to the literal string
`"authenticated"` for logged-in users or `"anon"` for anonymous/unauthenticated tokens.

**Impact on this codebase:** The current `JWTBearer` does NOT explicitly validate the
`aud` claim — it only checks the signature. No immediate break here. However:
1. If audience validation is added as a hardening step during the rewrite, the expected
   value must be `"authenticated"`, not a Cognito pool ID.
2. Any code that reads `credentials.claims["aud"]` expecting a UUID will get a string.
3. The Supabase `anon` role token (issued for unauthenticated browser clients) will have
   `aud="anon"` — this must not be treated as an authenticated user.

**Phase:** Auth migration phase.

**Source:** [Supabase JWT Claims Reference](https://supabase.com/docs/guides/auth/jwt-fields)

---

### MODERATE: cognito:username Claim Does Not Exist in Supabase JWTs

**What goes wrong:** `api/account.py` extracts `credentials.claims.get("cognito:username")`
to look up the Cognito username for the `admin_delete_user` API call. Supabase JWTs have
no `cognito:username` claim. The account deletion flow will silently find `None` for the
username and either fail or skip the deletion.

**The `sub` claim is safe:** Both Cognito and Supabase use `sub` as the user UUID.
`_extract_user_id` in `api/chat.py` and `api/account.py` using `claims.get("sub")` will
continue to work correctly. The user ID format changes (Cognito UUID vs Supabase UUID)
but both are UUID strings — no format incompatibility.

**What needs rewriting:** The entire account deletion path that calls `cognito-idp`
(`boto3`) must be replaced with the Supabase Admin API:
```python
# Supabase equivalent of admin_delete_user
supabase.auth.admin.delete_user(user_id)  # user_id is the sub claim UUID
```

Additionally, `core/auth.py` currently imports `COGNITO_REGION` and `COGNITO_POOL_ID`
from `core/config.py`. These env vars must be replaced with Supabase equivalents
(`SUPABASE_URL`, `SUPABASE_JWT_SECRET` or `SUPABASE_ANON_KEY`).

**Phase:** Auth migration phase.

---

### MODERATE: JWKS URL Must Change and Fetch-at-Startup Pattern Has Key Rotation Risk

**What goes wrong:** `core/auth.py` fetches JWKS synchronously at startup:
```python
requests.get(f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_POOL_ID}/.well-known/jwks.json")
```

For Supabase (asymmetric key path), the new URL is:
```
https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
```

**Key rotation subtlety:** Supabase caches the JWKS response at the edge for 10 minutes
and recommends applications not cache it longer than 10 minutes to support key rotation.
The current app fetches JWKS once at process startup and holds it for the process lifetime.
After a key rotation in Supabase, the app will continue rejecting all new tokens until
the process restarts.

This was also true for Cognito (Cognito rarely rotates keys, so it was not a practical
issue). For Supabase, key rotation is an explicit supported operation. Consider adding
periodic JWKS refresh (every 5-10 minutes) if key rotation is planned.

**Phase:** Auth migration phase.

---

### MODERATE: JWT Expiry Currently Not Validated — Behavior Changes With HS256 Decode

**What goes wrong:** The current `JWTBearer.verify_jwk_token` only verifies the signature.
It does NOT validate the `exp` claim — `jwt.get_unverified_claims()` is used, which skips
all claim validation. This means expired Cognito tokens are currently accepted.

When rewriting for Supabase HS256 using `jose.jwt.decode(token, secret, algorithms=["HS256"])`,
`exp` IS validated by default. Tokens expired by even one second will be rejected with a
`JWTError`. This is the correct behavior but is a breaking change from current behavior —
clients that hold expired tokens (e.g., no refresh logic) will suddenly get 403 errors.

**Clock skew risk:** If there is any clock skew between the Supabase Auth server and the
FastAPI host, tokens may be rejected before they should be. A confirmed real case showed a
PostgREST instance 15+ hours ahead of the Auth server, instantly rejecting all tokens.

**Prevention:**
- When using `jose.jwt.decode()`, add `options={"leeway": 10}` to allow 10 seconds of
  clock skew tolerance.
- Ensure the FastAPI host has NTP time sync (Docker containers can drift).
- For the asymmetric key path, add explicit `exp` validation to the existing
  `verify_jwk_token` method — it is currently absent.

**Phase:** Auth migration phase.

**Sources:** [Supabase clock skew issue](https://github.com/supabase/supabase/issues/41294),
[PyJWT leeway](https://pyjwt.readthedocs.io/en/latest/usage.html)

---

### LOW: Supabase anon Key Token May Reach Optional Auth Routes

**What goes wrong:** Supabase issues two types of tokens to browser clients: user JWTs
(after sign-in, `aud="authenticated"`) and anon tokens (before sign-in, `aud="anon"`).
If a frontend client sends an anon token in the Authorization header (which some Supabase
SDKs do by default), the middleware may accept it as an authenticated request because
the signature is valid, but `sub` may be a meaningless UUID or empty.

**Codebase impact:** The optional auth pattern (`auto_error=False`) means the middleware
accepts or ignores the token. `_extract_user_id` returns `credentials.claims.get("sub")`.
For anon tokens, `sub` is present but is not a real user UUID. Code checks `if user_id:`
before scoping Redis history — this is partially protective. The gap is that anon-token
sub values could be stored in the DB as if they were real users.

**Prevention:** After extracting `sub`, check that `aud != "anon"` before treating the
request as authenticated. Or validate that the sub UUID exists in the `users` table before
creating user-scoped data.

**Phase:** Auth migration phase.

---

## Supabase-Specific Gotchas

### CRITICAL: RLS With No Policies Silently Returns Zero Rows — Not an Error

**What goes wrong:** If RLS is enabled on a table with no policies, `SELECT` returns
zero rows and `INSERT`/`UPDATE`/`DELETE` return success but affect zero rows. No exception
is raised by Postgres or SQLAlchemy. The application behaves as if the table is empty.

**For this project:** This only applies when connecting as a role other than `postgres`
(which bypasses RLS). Since all current connections use the `postgres` role via
SQLAlchemy direct connections, RLS does not apply to any existing query. RLS is only
enforced on the PostgREST/Supabase client API layer.

**When it bites:** A developer sees the dashboard nudge to "enable RLS for security" and
enables it on, say, `chat_sessions`. The backend continues working (postgres role bypasses
RLS). Then a developer tests via the Supabase table editor (uses the `anon` role) and
sees zero rows. Confusion about whether data was inserted. Time wasted debugging.

**Decision to make:** Either explicitly leave RLS disabled on all tables (document why —
app uses direct Postgres connection, not PostgREST) or enable RLS with a blanket
`USING (true)` policy for `service_role` on all tables. Do not enable RLS without policies.

**Phase:** DB migration phase.

---

### MODERATE: public Schema Permissions Needed for anon/authenticated Roles Post-Migration

**What goes wrong:** Alembic migrations run as the `postgres` role and create tables owned
by `postgres`. By default, `anon` and `authenticated` roles may lack SELECT/INSERT on
newly created tables. This only matters if the Supabase REST API or dashboard is used —
not for direct SQLAlchemy connections. But it causes confusion when testing via the
Supabase dashboard Table Editor or SQL Editor.

**What the error looks like:** `ERROR: 42501: permission denied for table <name>` in the
Supabase dashboard table viewer after running migrations.

**One-time fix** (run after `alembic upgrade head`):
```sql
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT ALL ON TABLES TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;
```

These grants are idempotent and safe to re-run. Best captured in a `post_migrate.sql`
file committed alongside Alembic migrations.

**Phase:** DB migration phase.

**Source:** [Permission denied discussion](https://github.com/orgs/supabase/discussions/14393),
[Database API 42501 errors](https://supabase.com/docs/guides/troubleshooting/database-api-42501-errors)

---

### MODERATE: Alembic Autogenerate May Detect Supabase System Tables

**What goes wrong:** `alembic revision --autogenerate` compares `Base.metadata` against
what's in the database. Supabase creates many system tables in `auth`, `storage`, and
`realtime` schemas. If the autogenerate configuration does not exclude these schemas, the
generated migration will attempt to DROP or ALTER Supabase-managed tables, causing
immediate failures on the next `alembic upgrade head`.

**Current state:** The existing `alembic/env.py` uses `target_metadata = Base.metadata`
which only contains models defined in the project. As long as Supabase system tables are
never reflected into SQLAlchemy models, autogenerate is safe. The risk is additive —
do not add `autoload_with=engine` on Supabase's system schemas.

**Additional risk (April 2025 change):** Supabase restricted write access to `auth`,
`storage`, and `realtime` schemas. Any migration touching these schemas will fail with
a permission error.

**Prevention:** Never `reflect` Supabase system tables into SQLAlchemy. If autogenerate
produces unexpected drops, add `include_schemas` filtering to `alembic/env.py`.

**Phase:** DB migration phase.

**Source:** [Auth schema restriction](https://github.com/orgs/supabase/discussions/34270)

---

### LOW: Free Tier Connection Limit

**What goes wrong:** Supabase free tier limits direct database connections to approximately
60. The sync SQLAlchemy engine uses a default pool of up to 15 connections per worker.
With 2 Gunicorn workers, that's up to 30 sync connections. Add asyncpg connections and the
limit can be hit under any significant load.

**Prevention:** The asyncpg engine should use `NullPool` (already recommended above), which
routes all connections through Supavisor and does not hold persistent connections from the
app. The sync engine's default pool of 15 per worker is acceptable for the free tier.
Watch the Database → Connections panel in the Supabase dashboard during initial load testing.

**Phase:** DB migration phase (configure; monitor ongoing).

---

## Prevention Strategies

### Phase: DB Migration

| Pitfall | Prevention |
|---------|-----------|
| asyncpg prepared statements crash | Use `NullPool` + `statement_cache_size=0` + `prepared_statement_cache_size=0` + `jit=off` in async engine |
| Alembic fails through pooler | `DATABASE_URL` (port 5432 direct) for Alembic; `ASYNC_DATABASE_URL` (port 6543 pooler) for async runtime |
| Wrong SSL syntax for asyncpg | `connect_args={"ssl": "require"}` — not `sslmode` |
| IPv6 direct connection fails | Test direct connection from deployment host first; use session pooler as fallback |
| postgres role not superuser | Use Supabase dashboard for extension management; do not add extension DDL to Alembic |
| Schema permissions 42501 error | Run one-time grants SQL after migration; save as `post_migrate.sql` |
| Autogenerate picks up system tables | Keep `Base.metadata` to project models only; never reflect Supabase schemas |
| Connection string format confusion | Copy directly from Supabase dashboard tabs; document which env var maps to which string |

### Phase: Auth Migration

| Pitfall | Prevention |
|---------|-----------|
| JWKS empty, JWTBearer breaks entirely | `curl` the JWKS endpoint first; if empty keys, switch Supabase to asymmetric OR rewrite for HS256 |
| HS256 symmetric verification | Store JWT secret in env var only; use `jose.jwt.decode(token, secret, algorithms=["HS256"])` |
| Audience claim mismatch | Accept `"authenticated"` as valid `aud`; reject `"anon"` tokens from user-scoped paths |
| cognito:username claim missing | Rewrite account deletion to use Supabase Admin API; remove boto3 Cognito calls |
| JWKS URL out of date | Update `core/auth.py` URL to `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json` |
| Clock skew rejects valid tokens | Add `options={"leeway": 10}` to `jwt.decode()`; ensure host NTP sync |
| anon token treated as user | Check `aud != "anon"` before treating token as authenticated |

---

## Severity Summary

| Pitfall | Severity | Phase |
|---------|----------|-------|
| asyncpg prepared statements with Supavisor transaction pooler | CRITICAL | DB migration |
| Alembic must use direct connection, not pooler | CRITICAL | DB migration |
| Supabase HS256 default breaks existing JWKS-based JWTBearer | CRITICAL | Auth migration |
| SSL parameter syntax differs: asyncpg needs `ssl=` not `sslmode=` | MODERATE | DB migration |
| IPv6-only direct connection in some environments | MODERATE | DB migration |
| postgres role not a full superuser | MODERATE | DB migration |
| Audience claim is `"authenticated"` string, not Cognito pool ID | MODERATE | Auth migration |
| `cognito:username` claim absent from Supabase JWTs | MODERATE | Auth migration |
| JWKS URL must change; key rotation caching risk | MODERATE | Auth migration |
| JWT `exp` not currently validated; behavior changes with HS256 decode | MODERATE | Auth migration |
| public schema permissions 42501 after Alembic run | MODERATE | DB migration |
| Connection string format variants (username differs) | MODERATE | DB migration |
| Alembic autogenerate may detect Supabase system tables | MODERATE | DB migration |
| RLS silently blocks data if enabled without policies | CRITICAL (if triggered) | DB migration |
| Free tier connection limit | LOW | DB migration |
| anon key token accepted on optional auth routes | LOW | Auth migration |

---

## Sources

- [Supabase Connect to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase Supavisor FAQ](https://supabase.com/docs/guides/troubleshooting/supavisor-faq-YyP5tI)
- [asyncpg burst request failures issue #39227](https://github.com/supabase/supabase/issues/39227)
- [Supabase JWT documentation](https://supabase.com/docs/guides/auth/jwts)
- [Supabase JWT Claims Reference](https://supabase.com/docs/guides/auth/jwt-fields)
- [Supabase JWT Signing Keys](https://supabase.com/docs/guides/auth/signing-keys)
- [Empty JWKS endpoint discussion](https://github.com/orgs/supabase/discussions/36212)
- [asyncpg sslmode GitHub issue #737](https://github.com/MagicStack/asyncpg/issues/737)
- [SQLAlchemy sslmode asyncpg issue #6275](https://github.com/sqlalchemy/sqlalchemy/issues/6275)
- [Supabase Postgres Roles](https://supabase.com/docs/guides/database/postgres/roles)
- [Supabase security patch discussion](https://github.com/supabase/supabase/discussions/9314)
- [Permission denied for schema public](https://github.com/orgs/supabase/discussions/14393)
- [Database API 42501 errors](https://supabase.com/docs/guides/troubleshooting/database-api-42501-errors)
- [Auth schema restriction April 2025](https://github.com/orgs/supabase/discussions/34270)
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase IPv4/IPv6 guide](https://supabase.com/docs/guides/troubleshooting/supabase--your-network-ipv4-and-ipv6-compatibility-cHe3BP)
- [Supabase clock skew issue #41294](https://github.com/supabase/supabase/issues/41294)
- [Cognito JWT documentation (AWS)](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-with-identity-providers.html)
