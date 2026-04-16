# Frontend Auth Migration Guide: Cognito → Supabase

This document describes all backend API changes resulting from the Supabase Auth migration. Use it as a reference when updating frontend authentication code.

---

## 1. Token Source Changed

The backend now validates JWTs issued by **Supabase Auth** instead of AWS Cognito.

**Before:** Tokens were obtained via AWS Amplify / Cognito SDK.  
**After:** Tokens must be obtained via the Supabase client.

```typescript
// Before (Cognito)
import { Auth } from 'aws-amplify';
const session = await Auth.currentSession();
const token = session.getIdToken().getJwtToken();

// After (Supabase)
import { createClient } from '@supabase/supabase-js';
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
const { data: { session } } = await supabase.auth.getSession();
const token = session?.access_token;
```

All API requests must include:
```
Authorization: Bearer <supabase_access_token>
```

---

## 2. All Routes Now Require Auth (Breaking)

Previously most routes accepted unauthenticated requests (auth was optional). Now **every route** requires a valid Bearer token. Requests without a token will receive `403 Forbidden`.

| Endpoint | Previously | Now |
|---|---|---|
| `POST /chat/` | optional | **required** |
| `POST /chat/stream` | optional | **required** |
| `POST /chat/stream/agentic` | optional | **required** |
| `GET /chat/agentic` | optional | **required** |
| `POST /references/` | optional | **required** |
| `POST /hikmah/elaborate` | optional | **required** |
| `GET /hikmah/*`, `POST /hikmah/*` | optional | **required** |
| `GET /primers`, `POST /primers/*` | optional | **required** |
| `DELETE /account/me` | required | required (no change) |
| `GET /account/me` | required | required (no change) |

> **Note:** The raw CRUD routers (`/users`, `/lessons`, `/lesson-content`, `/user-progress`, `/hikmah-trees`) do **not** require auth at the route level.

---

## 3. User ID Format Changed

Supabase uses **UUIDs** for the `sub` claim, replacing Cognito's username/email string.

**Before (Cognito):** `sub` = `"john.doe@example.com"` or `"us-east-1:abc123..."`  
**After (Supabase):** `sub` = `"550e8400-e29b-41d4-a716-446655440000"` (UUID v4)

Anywhere `user_id` is sent in a request body or query param, use `session.user.id` from the Supabase client:

```typescript
// Before (Cognito)
const user = await Auth.currentAuthenticatedUser();
const userId = user.getUsername(); // string username

// After (Supabase)
const { data: { session } } = await supabase.auth.getSession();
const userId = session?.user?.id; // UUID string
```

**Affected endpoints that accept `user_id`:**
- `POST /user-progress` — body field `user_id`
- `GET /user-progress?user_id=...` — query param
- Any other endpoint where you manually pass the user identifier

---

## 4. New Utility Endpoint: `GET /account/me`

Returns the authenticated user's identity derived from the JWT. Useful for verifying auth state and retrieving `user_id` after sign-in.

**Request:**
```
GET /account/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "claims": {
    "sub": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "role": "authenticated",
    "aud": "authenticated",
    "exp": 1234567890
  }
}
```

---

## 5. Account Deletion: `DELETE /account/me`

No change to the endpoint signature. Internally it now calls Supabase Admin API instead of Cognito, but the frontend contract is unchanged:

```
DELETE /account/me
Authorization: Bearer <token>
```

Returns `204 No Content` on success.

---

## 6. Token Refresh

Supabase access tokens expire (default 1 hour). Use the Supabase client's built-in session management to handle refresh automatically, or listen to `onAuthStateChange` to update the token used in API calls.

```typescript
// Option A: Let Supabase handle it — always get session before requests
const { data: { session } } = await supabase.auth.getSession();
const token = session?.access_token;

// Option B: Listen for token refresh events
supabase.auth.onAuthStateChange((event, session) => {
  if (event === 'TOKEN_REFRESHED') {
    // Update stored token / axios default header / etc.
  }
});
```

---

## 7. Local Development Bypass

When the backend is running with `ENV=development`, **JWT verification is skipped entirely**. Any Bearer value (including a dummy string) will be accepted, and the backend will use mock credentials:

```
sub: "dev-user-001"
email: "dev@local.test"
```

This means frontend local dev does not require a real Supabase session to hit the API, but you should still send _some_ Bearer token to satisfy the `HTTPBearer` scheme check:

```typescript
// Minimal dev token — just needs to be a non-empty bearer string
headers: { Authorization: 'Bearer dev' }
```

---

## Summary Checklist

- [ ] Replace Cognito/Amplify SDK with Supabase client for auth
- [ ] Update all API calls to include `Authorization: Bearer <supabase_access_token>`
- [ ] Replace `user.getUsername()` / Cognito `sub` with `session.user.id` (UUID)
- [ ] Update any `user_id` fields sent in request bodies (e.g. `/user-progress`) to use the Supabase UUID
- [ ] Handle `403` responses on routes that were previously unauthenticated
- [ ] Set up token refresh handling (`onAuthStateChange` or re-fetch session before each request)
- [ ] Remove any AWS Amplify / Cognito dependencies if no longer needed elsewhere
