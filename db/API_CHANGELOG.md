# API Changelog

## 2025-10-08: User Progress API - `user_id` Type Change

### Breaking Change

The `user_progress` table's `user_id` field has been changed from `INTEGER` to `VARCHAR(128)` to support AWS Cognito usernames.

### Impact

**Affected Endpoints:**

- `POST /user-progress` - Create user progress
- `GET /user-progress` - List user progress (filter by `user_id`)
- `PATCH /user-progress/{progress_id}` - Update user progress
- `GET /user-progress/{progress_id}` - Get single progress record

### Migration Details

- **Database:** Column `user_progress.user_id` migrated from `BIGINT` to `VARCHAR(128)`
- **Index:** Added `ix_user_progress_user_id` for query performance
- **Alembic Revision:** `userid_to_string`

### Required Frontend Changes

**Before:**

```javascript
// Old - sending integer user_id
const response = await fetch("/user-progress", {
  method: "POST",
  body: JSON.stringify({
    user_id: 42, // ❌ Integer
    lesson_id: 100,
    percent_complete: 50.0,
  }),
});
```

**After:**

```javascript
// New - sending string username from AWS Cognito
const response = await fetch("/user-progress", {
  method: "POST",
  body: JSON.stringify({
    user_id: "john.doe@example.com", // ✅ String (username/email)
    lesson_id: 100,
    percent_complete: 50.0,
  }),
});

// Or using Cognito username
const username = user.getUsername(); // from AWS Cognito
const response = await fetch("/user-progress", {
  method: "POST",
  body: JSON.stringify({
    user_id: username, // ✅ String from Cognito
    lesson_id: 100,
    percent_complete: 50.0,
  }),
});
```

**Query Parameters:**

```javascript
// Before
const url = `/user-progress?user_id=42`; // ❌ Integer

// After
const url = `/user-progress?user_id=${encodeURIComponent(username)}`; // ✅ String
```

### Schema Changes

**Request Schema (`UserProgressCreate`):**

```python
{
  "user_id": "string",  # Changed from int
  "lesson_id": int,
  "content_id": int (optional),
  "percent_complete": float (optional),
  "is_completed": bool (optional),
  "notes": str (optional),
  "meta": dict (optional),
  "hikmah_tree_id": int (optional)
}
```

**Response Schema (`UserProgressRead`):**

```python
{
  "id": int,
  "user_id": "string",  # Changed from int
  "lesson_id": int,
  "content_id": int,
  "is_completed": bool,
  "percent_complete": float,
  "last_position": int,
  "notes": str,
  "meta": dict,
  "hikmah_tree_id": int,
  "created_at": datetime,
  "updated_at": datetime
}
```

### Backwards Compatibility

⚠️ **This is a breaking change.** Existing frontend code sending integer `user_id` will fail validation.

### Action Items for Frontend Team

1. ✅ Update all API calls to send string `user_id` (AWS Cognito username)
2. ✅ Update TypeScript interfaces/types for `UserProgress`
3. ✅ Update query parameter encoding to handle string usernames
4. ✅ Test with real Cognito usernames
5. ✅ Remove any integer casting on `user_id`

### Notes

- The `users` table is not actively used for authentication (AWS Cognito handles that)
- `user_id` should be the username/identifier from AWS Cognito
- Maximum length: 128 characters
- Index added for efficient filtering by `user_id`

### Questions?

Contact backend team or see `/db/models/user_progress.py` for schema details.
