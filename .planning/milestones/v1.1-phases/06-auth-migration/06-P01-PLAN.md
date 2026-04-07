---
phase: 06-auth-migration
plan: P01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/config.py
autonomous: true
requirements:
  - AUTH-03

must_haves:
  truths:
    - "Server refuses to start when SUPABASE_URL is absent from environment"
    - "Server refuses to start when SUPABASE_SERVICE_ROLE_KEY is absent from environment"
    - "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are exported as module-level constants from core/config.py"
    - "COGNITO_REGION and COGNITO_POOL_ID are absent from core/config.py"
  artifacts:
    - path: "core/config.py"
      provides: "Module-level SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY constants; startup ValueError guard"
      contains: "SUPABASE_URL"
  key_links:
    - from: "core/config.py"
      to: "core/auth.py"
      via: "import SUPABASE_URL"
      pattern: "from core\\.config import.*SUPABASE_URL"
    - from: "core/config.py"
      to: "api/account.py"
      via: "import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY"
      pattern: "from core\\.config import.*SUPABASE_SERVICE_ROLE_KEY"
---

<objective>
Update core/config.py to replace Cognito env vars with Supabase equivalents and add startup guards.

Purpose: Every downstream file (core/auth.py, api/account.py) imports from core/config.py. This plan establishes the single source of truth for Supabase env vars before those files are touched in Wave 2.
Output: core/config.py with SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY constants, COGNITO_* constants removed, and ValueError guard updated.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/06-auth-migration/06-CONTEXT.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace Cognito env vars with Supabase vars in core/config.py</name>
  <files>core/config.py</files>

  <read_first>
    - core/config.py — read the entire file before making any changes; understand the existing ValueError guard pattern and line positions of COGNITO_* constants
  </read_first>

  <action>
Make the following surgical changes to core/config.py:

1. REMOVE these two lines (currently lines 25-26):
   ```python
   COGNITO_REGION = os.getenv("COGNITO_REGION")
   COGNITO_POOL_ID = os.getenv("COGNITO_POOL_ID")
   ```

2. ADD these two lines in their place (keep them in the same logical section near REDIS_URL):
   ```python
   SUPABASE_URL = os.getenv("SUPABASE_URL")
   SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
   ```

3. UPDATE the existing ValueError guard block (currently lines 42-43):
   FROM:
   ```python
   if not OPENAI_API_KEY or not PINECONE_API_KEY:
       raise ValueError("Missing API keys! Ensure they are set in the .env file.")
   ```
   TO:
   ```python
   if not OPENAI_API_KEY or not PINECONE_API_KEY:
       raise ValueError("Missing API keys! Ensure they are set in the .env file.")

   if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
       raise ValueError("Missing Supabase config! Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env.")
   ```

Do NOT change any other lines. Do NOT add or remove any imports. The existing `import os` and `from dotenv import load_dotenv` stay as-is.

Per D-01 and D-01a: both vars must be validated at startup — server must not boot without them.
Per D-03: COGNITO_REGION and COGNITO_POOL_ID are fully removed (not commented out).
  </action>

  <verify>
    <automated>cd /Users/shawn.n/Desktop/Deen/deen-backend && python -c "
import sys
with open('core/config.py') as f:
    content = f.read()
checks = [
    ('SUPABASE_URL = os.getenv' in content, 'SUPABASE_URL constant present'),
    ('SUPABASE_SERVICE_ROLE_KEY = os.getenv' in content, 'SUPABASE_SERVICE_ROLE_KEY constant present'),
    ('COGNITO_REGION' not in content, 'COGNITO_REGION removed'),
    ('COGNITO_POOL_ID' not in content, 'COGNITO_POOL_ID removed'),
    ('SUPABASE_SERVICE_ROLE_KEY' in content and 'raise ValueError' in content.split('SUPABASE_SERVICE_ROLE_KEY')[1][:300], 'ValueError guard present for Supabase vars'),
]
failed = [msg for ok, msg in checks if not ok]
if failed:
    print('FAILED:', failed); sys.exit(1)
print('All checks passed')
"</automated>
  </verify>

  <acceptance_criteria>
    - `grep "SUPABASE_URL" core/config.py` returns `SUPABASE_URL = os.getenv("SUPABASE_URL")`
    - `grep "SUPABASE_SERVICE_ROLE_KEY" core/config.py` returns `SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")`
    - `grep "COGNITO_REGION" core/config.py` returns no matches
    - `grep "COGNITO_POOL_ID" core/config.py` returns no matches
    - `grep -A2 "SUPABASE_SERVICE_ROLE_KEY" core/config.py` shows a `raise ValueError(` within 5 lines
    - `python -c "import os; os.environ.pop('SUPABASE_URL', None); from core import config"` raises `ValueError: Missing Supabase config!`
  </acceptance_criteria>

  <done>core/config.py exports SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY, raises ValueError at startup if either is absent, and contains no COGNITO_* references.</done>
</task>

</tasks>

<verification>
After completing Task 1:
- `grep "SUPABASE_URL" core/config.py` → matches `SUPABASE_URL = os.getenv("SUPABASE_URL")`
- `grep "SUPABASE_SERVICE_ROLE_KEY" core/config.py` → matches constant + ValueError guard
- `grep "COGNITO" core/config.py` → zero matches
- With SUPABASE_URL unset in env: `python -c "from core import config"` raises ValueError
</verification>

<success_criteria>
core/config.py is the single source of truth for Supabase env vars: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are defined as module-level constants with a ValueError guard, and all COGNITO_* vars are removed.
</success_criteria>

<output>
After completion, create `.planning/phases/06-auth-migration/06-P01-SUMMARY.md`
</output>
