---
phase: 06-auth-migration
plan: P03
type: execute
wave: 2
depends_on:
  - 06-P01
files_modified:
  - api/account.py
autonomous: true
requirements:
  - AUTH-04

must_haves:
  truths:
    - "DELETE /account/me deletes the Supabase Auth user via httpx and returns 204"
    - "GET /account/me response does not contain a username field"
    - "api/account.py imports SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from core.config, not COGNITO_*"
    - "api/account.py makes no boto3 client calls (boto3 import may remain for Phase 7 cleanup)"
  artifacts:
    - path: "api/account.py"
      provides: "Account deletion via Supabase Admin API, cleaned-up /account/me response"
      contains: "SUPABASE_URL"
  key_links:
    - from: "api/account.py"
      to: "SUPABASE_URL/auth/v1/admin/users/{user_id}"
      via: "httpx.delete() with Authorization: Bearer SUPABASE_SERVICE_ROLE_KEY"
      pattern: "httpx\\.delete"
---

<objective>
Replace the boto3 AdminDeleteUser call in api/account.py with an httpx DELETE to the Supabase Admin API, and clean up the /account/me response by removing the Cognito-specific username field.

Purpose: This makes account deletion work against Supabase Auth. The boto3 call is dead code after the Cognito env vars are gone; httpx is already in requirements.txt so no new dependency is needed.
Output: api/account.py that calls DELETE {SUPABASE_URL}/auth/v1/admin/users/{user_id} with service role auth, preserves the "log but don't fail" pattern, and returns {user_id, email, claims} from /account/me.
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
<!-- Key contracts from dependencies — read before implementing. -->

From core/config.py (after P01):
```python
SUPABASE_URL = os.getenv("SUPABASE_URL")                         # e.g. "https://xyzabc.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # service role JWT
```

From models/JWTBearer.py:
```python
class JWTAuthorizationCredentials(BaseModel):
    jwt_token: str
    header: Dict[str, Any]
    claims: Dict[str, Any]   # sub = Supabase Auth user UUID
    signature: str
    message: str
```

Supabase Admin API contract:
- Endpoint: DELETE {SUPABASE_URL}/auth/v1/admin/users/{user_id}
- Header: Authorization: Bearer {SUPABASE_SERVICE_ROLE_KEY}
- Success: HTTP 200
- User not found: HTTP 404 (treat as success-equivalent per D-05 "log but don't fail")
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Replace boto3 Cognito deletion with httpx Supabase Admin API call</name>
  <files>api/account.py</files>

  <read_first>
    - api/account.py — read the full 149-line file before making changes; understand all imports, both route handlers, and the existing "log but don't fail" exception pattern in the Cognito deletion block (lines 82-121)
    - core/config.py — confirm SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are now exported (P01 must be complete)
  </read_first>

  <action>
Make the following changes to api/account.py:

**1. Update imports block (top of file):**

REMOVE:
```python
import boto3
from botocore.exceptions import ClientError
```
```python
from core.config import COGNITO_REGION, COGNITO_POOL_ID
```

ADD (keep httpx import near the top with other third-party imports):
```python
import httpx
```

ADD to config import:
```python
from core.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
```

Per D-03a: boto3 import removed here because we also remove the boto3 call. Phase 7 (CLEAN-01) removes boto3 from requirements.txt and Dockerfile — that is separate work. The import here is safe to remove since no boto3 call remains.

**2. Replace the entire "Step 3: Delete user from AWS Cognito" block** in `delete_my_account` (currently lines 82-121 — the try/except that creates a boto3 client and calls `admin_delete_user`).

Replace it with:

```python
    # Step 3: Delete user from Supabase Auth using Admin API
    try:
        response = httpx.delete(
            f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"},
        )
        if response.status_code == 404:
            # User not found in Supabase Auth — treat as success (already deleted)
            logger.warning(f"Supabase user {user_id} not found during deletion (already removed?)")
        elif not response.is_success:
            logger.error(
                f"Supabase Admin API deletion failed for user {user_id}: "
                f"HTTP {response.status_code} — {response.text}"
            )
        else:
            logger.info(f"Successfully deleted user {user_id} from Supabase Auth")
    except Exception as e:
        # Log unexpected errors but don't fail — DB data is already deleted
        logger.error(f"Unexpected error during Supabase Auth deletion for user {user_id}: {str(e)}")
```

Per D-04: Use synchronous `httpx.delete()` — consistent with existing sync-inside-async pattern.
Per D-05: "log but don't fail" — errors are logged but 204 is still returned.

Also update the docstring for `delete_my_account` to replace the Cognito reference:
- Change "4. Deletes the user from AWS Cognito" to "4. Deletes the user from Supabase Auth via Admin API"

**3. Update `get_my_account_info` handler** (currently lines 126-148):

REMOVE these two lines (per D-06 and D-06a):
```python
    username = credentials.claims.get("cognito:username")
```
```python
        "username": username,
```

The return dict should become:
```python
    return {
        "user_id": user_id,
        "email": email,
        "claims": credentials.claims
    }
```

Also update the docstring: remove the mention of "username" if present.
  </action>

  <verify>
    <automated>cd /Users/shawn.n/Desktop/Deen/deen-backend && python -c "
import sys
with open('api/account.py') as f:
    content = f.read()
checks = [
    ('SUPABASE_URL' in content, 'SUPABASE_URL imported'),
    ('SUPABASE_SERVICE_ROLE_KEY' in content, 'SUPABASE_SERVICE_ROLE_KEY imported'),
    ('COGNITO_REGION' not in content, 'COGNITO_REGION removed'),
    ('COGNITO_POOL_ID' not in content, 'COGNITO_POOL_ID removed'),
    ('admin_delete_user' not in content, 'boto3 admin_delete_user removed'),
    ('boto3.client' not in content, 'boto3 client call removed'),
    ('/auth/v1/admin/users/' in content, 'Supabase Admin API endpoint present'),
    ('httpx.delete' in content, 'httpx.delete call present'),
    ('cognito:username' not in content, 'cognito:username claim reference removed'),
    ('\"username\"' not in content, 'username field removed from /account/me response'),
]
failed = [msg for ok, msg in checks if not ok]
if failed:
    print('FAILED:', failed); sys.exit(1)
print('All checks passed')
"</automated>
  </verify>

  <acceptance_criteria>
    - `grep "boto3.client" api/account.py` returns zero matches
    - `grep "admin_delete_user" api/account.py` returns zero matches
    - `grep "COGNITO" api/account.py` returns zero matches
    - `grep "httpx.delete" api/account.py` returns one match with `f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}"`
    - `grep "Authorization" api/account.py` returns a line with `f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"`
    - `grep "cognito:username" api/account.py` returns zero matches
    - `grep '"username"' api/account.py` returns zero matches (field removed from return dict)
    - `python -c "from api.account import router"` imports without error (syntax check passes)
    - The httpx call is wrapped in `try/except Exception` that logs but does not re-raise (preserving "log but don't fail" per D-05)
  </acceptance_criteria>

  <done>api/account.py deletes users via httpx to Supabase Admin API with service role auth, preserves "log but don't fail" semantics, returns 204. GET /account/me returns {user_id, email, claims} with no username field. All COGNITO_* and boto3 references are removed from the file.</done>
</task>

</tasks>

<verification>
After completing Task 1:
- `grep "boto3" api/account.py` → zero matches (import and call both gone)
- `grep "COGNITO" api/account.py` → zero matches
- `grep "auth/v1/admin/users" api/account.py` → one match in the httpx.delete call
- `python -c "from api.account import router"` → exits 0

End-to-end verification (requires running server with valid Supabase creds):
- Obtain a valid Supabase Auth JWT → `DELETE /account/me` returns 204 and user is deleted in Supabase dashboard
- Invalid JWT → 403 returned by JWTBearer (unchanged behavior)
- `GET /account/me` response body contains `user_id`, `email`, `claims` keys and does NOT contain `username` key
</verification>

<success_criteria>
api/account.py makes a synchronous httpx DELETE to {SUPABASE_URL}/auth/v1/admin/users/{user_id} with Authorization: Bearer {SUPABASE_SERVICE_ROLE_KEY} header. Errors are logged but don't fail the request. GET /account/me returns user_id, email, and claims — no username field.
</success_criteria>

<output>
After completion, create `.planning/phases/06-auth-migration/06-P03-SUMMARY.md`
</output>
