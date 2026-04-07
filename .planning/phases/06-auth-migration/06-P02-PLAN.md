---
phase: 06-auth-migration
plan: P02
type: execute
wave: 2
depends_on:
  - 06-P01
files_modified:
  - core/auth.py
autonomous: true
requirements:
  - AUTH-01
  - AUTH-02

must_haves:
  truths:
    - "Server fetches JWKS from Supabase at startup, not from AWS Cognito"
    - "A valid Supabase Auth JWT is accepted by JWTBearer middleware"
    - "An invalid or Cognito-issued JWT is rejected with 403"
    - "core/auth.py contains no COGNITO_REGION or COGNITO_POOL_ID references"
  artifacts:
    - path: "core/auth.py"
      provides: "JWKS fetched from SUPABASE_URL/auth/v1/keys at module import time"
      contains: "SUPABASE_URL"
  key_links:
    - from: "core/auth.py"
      to: "models/JWTBearer.py"
      via: "jwks = JWKS.model_validate(...) passed to JWTBearer(jwks)"
      pattern: "JWTBearer\\(jwks\\)"
    - from: "core/config.py"
      to: "core/auth.py"
      via: "from core.config import SUPABASE_URL"
      pattern: "from core\\.config import SUPABASE_URL"
---

<objective>
Update core/auth.py to fetch JWKS from the Supabase Auth endpoint instead of AWS Cognito.

Purpose: This is the single change that makes the JWTBearer middleware verify Supabase Auth JWTs. The JWTBearer class itself (models/JWTBearer.py) is provider-agnostic and unchanged — only the JWKS source URL changes.
Output: core/auth.py that fetches from {SUPABASE_URL}/auth/v1/keys at startup, with COGNITO_* imports removed.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/06-auth-migration/06-CONTEXT.md
@.planning/phases/06-auth-migration/06-P01-SUMMARY.md
</context>

<interfaces>
<!-- Key types and contracts from models/JWTBearer.py — DO NOT modify this file. -->

From models/JWTBearer.py:
```python
class JWKS(BaseModel):
    keys: List[JWK]

class JWTBearer(HTTPBearer):
    def __init__(self, jwks: JWKS, auto_error: bool = True): ...
```

From core/config.py (after P01):
```python
SUPABASE_URL = os.getenv("SUPABASE_URL")           # e.g. "https://xyzabc.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Update JWKS fetch URL from Cognito to Supabase in core/auth.py</name>
  <files>core/auth.py</files>

  <read_first>
    - core/auth.py — read the current 11-line file before changing it; understand the import and the JWKS fetch call
    - core/config.py — confirm SUPABASE_URL is now exported (P01 must be complete)
    - models/JWTBearer.py — confirms JWKS and JWTBearer signatures; DO NOT modify this file
  </read_first>

  <action>
Replace the entire content of core/auth.py with the following (the file is currently 11 lines):

```python
import requests
from core.config import SUPABASE_URL

from models.JWTBearer import JWKS, JWTBearer

jwks = JWKS.model_validate(
    requests.get(
        f"{SUPABASE_URL}/auth/v1/keys"
    ).json()
)

auth = JWTBearer(jwks)
optional_auth = JWTBearer(jwks, auto_error=False)
```

Key changes per D-02:
- Import changed from `COGNITO_POOL_ID, COGNITO_REGION` to `SUPABASE_URL`
- JWKS URL changed from `https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_POOL_ID}/.well-known/jwks.json` to `{SUPABASE_URL}/auth/v1/keys`
- `optional_auth = JWTBearer(jwks, auto_error=False)` added — currently missing from core/auth.py but used in main.py; add it here so both instances come from the same JWKS

Note: The `JWTBearer` class in `models/JWTBearer.py` is NOT modified — it is already provider-agnostic and handles RS256 keys from any JWKS endpoint.
  </action>

  <verify>
    <automated>cd /Users/shawn.n/Desktop/Deen/deen-backend && python -c "
import sys
with open('core/auth.py') as f:
    content = f.read()
checks = [
    ('SUPABASE_URL' in content, 'SUPABASE_URL imported'),
    ('COGNITO_REGION' not in content, 'COGNITO_REGION removed'),
    ('COGNITO_POOL_ID' not in content, 'COGNITO_POOL_ID removed'),
    ('/auth/v1/keys' in content, 'Supabase JWKS endpoint present'),
    ('optional_auth = JWTBearer' in content, 'optional_auth defined'),
    ('auth = JWTBearer(jwks)' in content, 'auth defined'),
]
failed = [msg for ok, msg in checks if not ok]
if failed:
    print('FAILED:', failed); sys.exit(1)
print('All checks passed')
"</automated>
  </verify>

  <acceptance_criteria>
    - `grep "COGNITO" core/auth.py` returns zero matches
    - `grep "SUPABASE_URL" core/auth.py` returns a line with `from core.config import SUPABASE_URL`
    - `grep "/auth/v1/keys" core/auth.py` returns one match with the JWKS URL
    - `grep "optional_auth" core/auth.py` returns `optional_auth = JWTBearer(jwks, auto_error=False)`
    - `grep "auth = JWTBearer(jwks)" core/auth.py` returns one match
    - With valid SUPABASE_URL set and network access: `python -c "from core.auth import auth, optional_auth"` completes without error (JWKS fetch succeeds and JWTBearer instances created)
  </acceptance_criteria>

  <done>core/auth.py fetches JWKS from {SUPABASE_URL}/auth/v1/keys, exports both auth and optional_auth JWTBearer instances, and contains zero Cognito references.</done>
</task>

</tasks>

<verification>
After completing Task 1:
- `grep "COGNITO" core/auth.py` → zero matches
- `grep "auth/v1/keys" core/auth.py` → one match
- With SUPABASE_URL set to a real Supabase project URL: `python -c "from core.auth import auth"` loads without error
- curl {SUPABASE_URL}/auth/v1/keys should return `{"keys":[...]}` with at least one key (AUTH-01 verification — confirm asymmetric signing is active before running this plan)
</verification>

<success_criteria>
core/auth.py fetches JWKS from Supabase at module import time. The JWTBearer instances (auth and optional_auth) verify RS256 tokens issued by Supabase Auth. Cognito references are fully removed.
</success_criteria>

<output>
After completion, create `.planning/phases/06-auth-migration/06-P02-SUMMARY.md`
</output>
