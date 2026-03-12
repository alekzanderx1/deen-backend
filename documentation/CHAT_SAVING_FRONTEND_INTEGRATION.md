# Chat Saving Frontend Integration Guide

This guide explains how the frontend should integrate with the new chat saving behavior for:

- `POST /chat/stream`
- `POST /chat/stream/agentic`
- `GET /chat/saved`
- `GET /chat/saved/{session_id}`

It includes request/response contracts, auth behavior, and the expected UX flow for loading and resuming chats.

## Summary of Backend Behavior

1. Chat persistence is enabled only for authenticated users.
2. Saving is automatic and seamless for:
- `/chat/stream`
- `/chat/stream/agentic`
3. A saved chat is created as soon as the first user query is received.
4. Additional turns are appended incrementally to the same saved chat.
5. Chat title is auto-derived from the first query:
- first 50 characters of the first user message.
6. To continue an old conversation, reuse the same `session_id`.

## Important Auth Rules

### Streaming Endpoints

- `POST /chat/stream` and `POST /chat/stream/agentic` accept requests with or without `Authorization`.
- If token is present and valid:
- the turn is saved to Postgres.
- the chat is included in `/chat/saved` APIs.
- If token is missing/invalid:
- chat still works, but no save occurs.

### Saved Chat APIs

- `GET /chat/saved` requires auth.
- `GET /chat/saved/{session_id}` requires auth.
- Both are user-scoped: users only see their own saved chats.

## Session ID Rules (Critical)

`session_id` is the durable conversation key.

- New chat: frontend creates a new unique `session_id` (UUID recommended).
- Continue existing chat: frontend reuses that chat's existing `session_id`.
- If you accidentally create a new `session_id`, backend will treat it as a new chat.

## Streaming Endpoints (Unchanged Request Shape)

## `POST /chat/stream`

### Request Body

```json
{
  "user_query": "What does Islam say about justice?",
  "session_id": "9e53d0fc-7ca5-44d8-9f0e-8e103b1881b3",
  "language": "english"
}
```

### Auth Header (optional but required for saving)

```http
Authorization: Bearer <jwt>
```

### Response

- `text/event-stream` (same streaming behavior as before).
- Persisted assistant text excludes the trailing references payload.

## `POST /chat/stream/agentic`

### Request Body

```json
{
  "user_query": "Explain Tawhid with references",
  "session_id": "9e53d0fc-7ca5-44d8-9f0e-8e103b1881b3",
  "language": "english",
  "config": {
    "retrieval": {
      "shia_doc_count": 5,
      "sunni_doc_count": 2
    }
  }
}
```

### Auth Header (optional but required for saving)

```http
Authorization: Bearer <jwt>
```

### Response

- `text/event-stream` (same streaming behavior as before).

## New Saved Chat APIs

## `GET /chat/saved`

Returns current user's saved chat sessions, sorted by most recently active.

### Auth Header (required)

```http
Authorization: Bearer <jwt>
```

### Query Params

- `limit` (default `20`, min `1`, max `100`)
- `offset` (default `0`)

### Example Response

```json
{
  "items": [
    {
      "session_id": "9e53d0fc-7ca5-44d8-9f0e-8e103b1881b3",
      "title": "What does Islam say about justice?",
      "created_at": "2026-03-05T19:10:21.000000+00:00",
      "updated_at": "2026-03-05T19:11:04.000000+00:00",
      "last_message_at": "2026-03-05T19:11:04.000000+00:00",
      "message_count": 6
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### Notes

- `message_count` is the total number of saved messages in that chat.
- Each turn adds 2 messages (`user`, `assistant`) when response completes.

## `GET /chat/saved/{session_id}`

Returns one saved chat with ordered message history.

### Auth Header (required)

```http
Authorization: Bearer <jwt>
```

### Query Params

- `limit` (default `200`, min `1`, max `1000`)
- `offset` (default `0`)

### Example Response

```json
{
  "session_id": "9e53d0fc-7ca5-44d8-9f0e-8e103b1881b3",
  "title": "What does Islam say about justice?",
  "created_at": "2026-03-05T19:10:21.000000+00:00",
  "updated_at": "2026-03-05T19:11:04.000000+00:00",
  "last_message_at": "2026-03-05T19:11:04.000000+00:00",
  "messages": [
    {
      "id": 101,
      "role": "user",
      "content": "What does Islam say about justice?",
      "created_at": "2026-03-05T19:10:21.000000+00:00"
    },
    {
      "id": 102,
      "role": "assistant",
      "content": "In Twelver Shia Islam, justice is central...",
      "created_at": "2026-03-05T19:10:25.000000+00:00"
    }
  ],
  "total_messages": 2,
  "limit": 200,
  "offset": 0
}
```

### Errors

- `404`: chat not found for current user.
- `403`: invalid/missing auth token details.

## Recommended Frontend Flow

## 1. Start New Chat

1. Generate `session_id` client-side (`crypto.randomUUID()`).
2. Keep it in page/chat state.
3. Send all stream requests for that thread with same `session_id`.
4. Include bearer token if user is logged in.

## 2. Render Sidebar/List of Saved Chats

1. On app load (authenticated), call `GET /chat/saved?limit=20&offset=0`.
2. Render `title` and `last_message_at`.
3. Paginate with `offset`.

## 3. Open Existing Chat

1. User clicks a chat item.
2. Call `GET /chat/saved/{session_id}`.
3. Hydrate UI message list from returned `messages`.
4. Set active thread `session_id` to that same value.

## 4. Continue Existing Chat

1. Send new `POST /chat/stream` or `/chat/stream/agentic` with same `session_id`.
2. Backend appends new turn to existing saved chat automatically.

## Frontend Data Model Suggestion

```ts
type SavedChatListItem = {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  last_message_at: string;
  message_count: number;
};

type SavedChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};
```

## UX and Edge Cases

1. If user is unauthenticated:
- hide saved-chat sidebar, or show disabled state.
- chat still streams normally.
2. If stream is interrupted:
- partial assistant text may still be persisted if any text was generated.
3. Saved assistant content excludes trailing `[REFERENCES]` payload.
- If your chat UI shows references separately from stream payload, keep doing that from live stream data.
4. If user logs in mid-session:
- continue using same `session_id`; future turns will be saved (past unauthenticated turns are not backfilled).

## API Examples (Frontend)

## Fetch saved list

```bash
curl -H "Authorization: Bearer <jwt>" \
  "http://127.0.0.1:8000/chat/saved?limit=20&offset=0"
```

## Fetch saved chat detail

```bash
curl -H "Authorization: Bearer <jwt>" \
  "http://127.0.0.1:8000/chat/saved/9e53d0fc-7ca5-44d8-9f0e-8e103b1881b3"
```

## Send stream request with persistence

```bash
curl -N -X POST "http://127.0.0.1:8000/chat/stream" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt>" \
  -d '{
    "user_query": "Explain Imamate briefly",
    "session_id": "9e53d0fc-7ca5-44d8-9f0e-8e103b1881b3",
    "language": "english"
  }'
```

## Integration Checklist

- Generate stable `session_id` per chat thread.
- Reuse `session_id` when continuing an old chat.
- Include `Authorization` header on stream calls for logged-in users.
- Use `/chat/saved` for sidebar/history list.
- Use `/chat/saved/{session_id}` when opening a previous thread.
- Keep stream parsing logic unchanged.
