# API Reference - Complete Endpoint Documentation

Complete reference for all API endpoints in the Deen backend.

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Chat Endpoints](#chat-endpoints)
- [Reference Lookup](#reference-lookup)
- [Hikmah Trees](#hikmah-trees)
- [Account Management](#account-management)
- [Memory Admin](#memory-admin)
- [Learning Platform CRUD](#learning-platform-crud)
- [Health & Debug](#health--debug)
- [Error Responses](#error-responses)

## Base URL

**Development**: `http://localhost:8000`
**Production**: `https://your-domain.com`

## Authentication

Most endpoints require JWT authentication via AWS Cognito.

**Header**:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Obtaining Token**: Authenticate with AWS Cognito (frontend responsibility)

**Protected Endpoints**: All endpoints except `/health` and admin dashboard

## Chat Endpoints

### POST /chat/

Non-streaming chat endpoint.

**Authentication**: Required

**Request**:
```json
{
  "user_query": "What is Tawhid?",
  "session_id": "user123:thread-1",
  "language": "english"
}
```

**Response**:
```json
{
  "response": "Tawhid is the fundamental concept of monotheism in Islam..."
}
```

**Status Codes**:
- `200`: Success
- `400`: Invalid request (missing fields)
- `401`: Unauthorized (invalid/missing token)
- `500`: Internal server error

---

### POST /chat/stream

**Recommended** streaming chat endpoint for better UX.

**Authentication**: Required

**Request**:
```json
{
  "user_query": "Explain the concept of Imamate",
  "session_id": "user123:thread-1",
  "language": "english"
}
```

**Response**: Server-Sent Events (text/event-stream)

```
Imamate is a fundamental concept...
[continues streaming]

[REFERENCES]
[{"book": "Al-Kafi", "text": "..."}]
```

**Curl Example**:
```bash
curl -X POST "http://localhost:8000/chat/stream" \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "What is justice in Islam?",
    "session_id": "user123:thread-1",
    "language": "english"
  }'
```

---

### DELETE /chat/session/{session_id}

Clear conversation history for a session.

**Authentication**: Required

**Parameters**:
- `session_id` (path): Session identifier

**Response**:
```json
{
  "status": "ok"
}
```

**Example**:
```bash
curl -X DELETE "http://localhost:8000/chat/session/user123:thread-1" \
  -H "Authorization: Bearer YOUR_JWT"
```

## Reference Lookup

### POST /references

Semantic search for Islamic texts.

**Authentication**: Required

**Query Parameters**:
- `sect` (optional): `"shia"` | `"sunni"` | `"both"` (default: `"both"`)
- `limit` (optional): 1-50 (default: 10)

**Request**:
```json
{
  "user_query": "charity in Islam"
}
```

**Response**:
```json
{
  "response": {
    "shia": [
      {
        "book": "Al-Kafi",
        "chapter": "Book of Charity",
        "hadith_number": "3",
        "text": "...",
        "author": "Shaykh al-Kulaynī",
        "volume": "Volume 2",
        "source": "Shi'i Hadith",
        "sect": "shia"
      }
    ],
    "sunni": [
      {
        "book": "Sahih al-Bukhari",
        "chapter": "Book of Zakat",
        "hadith_number": "1",
        "text": "...",
        "author": "Imam al-Bukhari",
        "sect": "sunni"
      }
    ]
  }
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/references?sect=shia&limit=5" \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"user_query": "prayer times"}'
```

## Hikmah Trees

### POST /hikmah/elaborate/stream

Request AI elaboration on selected lesson text.

**Authentication**: Required

**Request**:
```json
{
  "selected_text": "What is Taqwa?",
  "context_text": "Full lesson text for context...",
  "hikmah_tree_name": "Foundations of Faith",
  "lesson_name": "Understanding Piety",
  "lesson_summary": "Lesson summary...",
  "user_id": "user123"
}
```

**Response**: Server-Sent Events (text/event-stream)

```
The concept of Taqwa, which you've highlighted, is central to Islamic spirituality...
[continues streaming]
```

**Notes**:
- `user_id` is optional but recommended for memory tracking
- Background memory agent processes after streaming completes

---

### GET /hikmah-trees

List all Hikmah Trees.

**Authentication**: Required

**Response**:
```json
[
  {
    "id": 1,
    "title": "Foundations of Shia Faith",
    "summary": "Core beliefs and practices",
    "tags": ["aqeedah", "basics"],
    "skill_level": 3,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### GET /lessons

Get lessons for a Hikmah Tree.

**Authentication**: Required

**Query Parameters**:
- `hikmah_tree_id` (required): Tree ID

**Response**:
```json
[
  {
    "id": 101,
    "slug": "understanding-tawhid",
    "title": "Understanding Tawhid",
    "summary": "The concept of monotheism",
    "hikmah_tree_id": 1,
    "order_position": 1,
    "estimated_minutes": 15,
    "tags": ["tawhid", "monotheism"]
  }
]
```

---

### GET /lesson-content

Get content blocks for a lesson.

**Authentication**: Required

**Query Parameters**:
- `lesson_id` (required): Lesson ID

**Response**:
```json
[
  {
    "id": 1001,
    "lesson_id": 101,
    "content_type": "text",
    "content": "Tawhid is...",
    "order_position": 1
  }
]
```

## Account Management

### GET /account/me

Get authenticated user information from JWT token.

**Authentication**: Required

**Response**:
```json
{
  "user_id": "abc-123-def",
  "email": "user@example.com",
  "username": "user123",
  "claims": {
    "sub": "abc-123-def",
    "email": "user@example.com",
    "cognito:username": "user123"
  }
}
```

---

### DELETE /account/me

Delete authenticated user's account.

**Authentication**: Required

**Description**: Deletes:
1. All user data from database (progress, memory, etc.)
2. Redis session data
3. User from AWS Cognito

**Response**: `204 No Content`

**Example**:
```bash
curl -X DELETE "http://localhost:8000/account/me" \
  -H "Authorization: Bearer YOUR_JWT"
```

## Memory Admin

### GET /admin/memory/dashboard

Interactive web UI for inspecting user memory.

**Authentication**: None (developer tool)

**Response**: HTML page

**Access**: `http://localhost:8000/admin/memory/dashboard`

---

### GET /admin/memory/{user_id}/profile

Get user memory profile summary (JSON endpoint for dashboard).

**Authentication**: None

**Response**:
```json
{
  "user_id": "user123",
  "memory_version": 3,
  "total_interactions": 45,
  "total_notes": 47,
  "last_significant_update": "2024-01-15T10:30:00Z",
  "note_counts": {
    "learning_notes": 12,
    "knowledge_notes": 15,
    "interest_notes": 10,
    "behavior_notes": 7,
    "preference_notes": 3
  }
}
```

---

### GET /admin/memory/{user_id}/notes

Get all notes for a user.

**Authentication**: None

**Response**:
```json
{
  "learning_notes": [...],
  "knowledge_notes": [...],
  "interest_notes": [...],
  "behavior_notes": [...],
  "preference_notes": [...]
}
```

---

### GET /admin/memory/{user_id}/events

Get recent memory events.

**Authentication**: None

**Query Parameters**:
- `limit` (optional): Default 50

**Response**:
```json
[
  {
    "id": "event-uuid",
    "event_type": "hikmah_elaboration",
    "processing_status": "processed",
    "processed_at": "2024-01-15T10:30:00Z",
    "reasoning": "User requested elaboration on Wilayah...",
    "notes_added": 2,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### GET /admin/memory/{user_id}/consolidations

Get consolidation history.

**Authentication**: None

**Query Parameters**:
- `limit` (optional): Default 20

**Response**:
```json
[
  {
    "id": "consolidation-uuid",
    "consolidation_type": "automatic",
    "created_at": "2024-01-14T03:00:00Z",
    "notes_before": 105,
    "notes_after": 78,
    "notes_removed": 27,
    "reasoning": "Merged duplicate and similar observations..."
  }
]
```

## Learning Platform CRUD

### User Progress

**POST /user-progress**: Create/update progress
**GET /user-progress**: Get user progress (filter by user_id, tree_id, lesson_id)
**PATCH /user-progress/{id}**: Update progress
**DELETE /user-progress/{id}**: Delete progress record

### Users

**POST /users**: Create user
**GET /users/{id}**: Get user
**GET /users**: List users
**PATCH /users/{id}**: Update user
**DELETE /users/{id}**: Delete user

### Lessons

**POST /lessons**: Create lesson
**GET /lessons/{id}**: Get lesson
**GET /lessons**: List lessons
**PATCH /lessons/{id}**: Update lesson
**DELETE /lessons/{id}**: Delete lesson

## Health & Debug

### GET /health

Basic health check.

**Authentication**: None

**Response**:
```json
{
  "status": "ok"
}
```

---

### GET /_debug/db

Test database connectivity.

**Authentication**: None

**Response**:
```json
{
  "ok": true,
  "version": "PostgreSQL 14.5..."
}
```

---

### GET /_routes

List all registered routes (debugging).

**Authentication**: None

**Response**:
```json
[
  {"path": "/chat", "methods": ["POST"]},
  {"path": "/references", "methods": ["POST"]},
  ...
]
```

## Error Responses

### Standard Error Format

```json
{
  "detail": "Error message here"
}
```

### Common Status Codes

- `200`: Success
- `201`: Created
- `204`: No Content (successful deletion)
- `400`: Bad Request (invalid input)
- `401`: Unauthorized (missing/invalid token)
- `403`: Forbidden (valid token, insufficient permissions)
- `404`: Not Found
- `422`: Unprocessable Entity (validation error)
- `500`: Internal Server Error

### Example Error Responses

**400 Bad Request**:
```json
{
  "detail": "Please provide an appropriate query."
}
```

**401 Unauthorized**:
```json
{
  "detail": "Not authenticated"
}
```

**404 Not Found**:
```json
{
  "detail": "User not found"
}
```

**422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "user_query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Rate Limiting

Currently no rate limiting implemented.

**Recommendations for Production**:
- Implement per-user rate limits
- Use Redis for rate limit tracking
- Consider tiered limits based on user type

## CORS Configuration

**Allowed Origins** (configured via env):
```bash
CORS_ALLOW_ORIGINS=https://deen-frontend.vercel.app
```

**Development** automatically allows:
- `http://localhost:5173`
- `http://localhost:3000`
- `http://127.0.0.1:5173`
- `http://127.0.0.1:3000`

## API Versioning

Currently no API versioning.

**Future Consideration**:
- Use `/v1/` prefix for all endpoints
- Maintain backward compatibility
- Deprecation warnings before breaking changes

## See Also

- [Chatbot Documentation](CHATBOT.md) - Chat endpoint details
- [Reference Lookup](REFERENCE_LOOKUP.md) - Reference endpoint details
- [Hikmah Trees](HIKMAH_TREES.md) - Hikmah endpoints details
- [Memory Agent](MEMORY_AGENT.md) - Memory endpoints details
- [Authentication](AUTHENTICATION.md) - JWT authentication details
