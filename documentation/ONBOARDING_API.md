# Onboarding API

Two endpoints that persist and retrieve user onboarding answers. Both require a valid Supabase JWT in the `Authorization` header.

---

## POST /onboarding

Submits (or updates) the authenticated user's onboarding answers. Safe to call multiple times — subsequent calls overwrite the previous submission.

### Request

```
POST /onboarding
Authorization: Bearer <supabase-jwt>
Content-Type: application/json
```

```json
{
  "tradition": "Twelver Shia (Ja'fari)",
  "goals": [
    "I want reliable answers with sources",
    "I want a structured learning path and don't know where to start"
  ],
  "knowledge_level": "Beginner",
  "topics": [
    "Beliefs (Aqa'id)",
    "Qur'an & Tafsir"
  ]
}
```

### Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `tradition` | string | yes | Single value from the tradition selector |
| `goals` | string[] | yes | One or more selections; must not be empty |
| `knowledge_level` | string | yes | Single value from the knowledge level selector |
| `topics` | string[] | yes | 1–3 selections; sending more than 3 returns a 422 |

### Response `200 OK`

```json
{
  "user_id": "a3f2c1d4-...",
  "tradition": "Twelver Shia (Ja'fari)",
  "goals": [
    "I want reliable answers with sources",
    "I want a structured learning path and don't know where to start"
  ],
  "knowledge_level": "Beginner",
  "topics": [
    "Beliefs (Aqa'id)",
    "Qur'an & Tafsir"
  ],
  "completed_at": "2026-04-14T10:23:00Z",
  "created_at": "2026-04-14T10:23:00Z",
  "updated_at": "2026-04-14T10:23:00Z"
}
```

### Error responses

| Status | Reason |
|---|---|
| `401` / `403` | Missing or invalid JWT |
| `422` | Validation failure — e.g. `topics` has more than 3 items, or `goals` is empty |

---

## GET /onboarding/me

Returns the authenticated user's stored onboarding answers.

### Request

```
GET /onboarding/me
Authorization: Bearer <supabase-jwt>
```

### Response `200 OK`

Same shape as the `POST` response above.

### Error responses

| Status | Reason |
|---|---|
| `401` / `403` | Missing or invalid JWT |
| `404` | User has not yet submitted onboarding |

---

## Accepted values

The backend accepts any string the frontend sends — there is no server-side allowlist. The values below match what is currently shown in the onboarding UI.

**tradition**
- `Twelver Shia (Ja'fari)`
- `Sunni (General)`
- `Other Muslim`
- `Non-Muslim`
- `I'm not sure`
- `Prefer not to say`

**goals** (multi-select)
- `I want a structured learning path and don't know where to start`
- `I want reliable answers with sources`
- `I'm interested in something specific right now`
- `Just general curiosity`

**knowledge_level**
- `Just starting`
- `Beginner`
- `Advanced`
- `I'm not sure`
- `Prefer not to say`

**topics** (multi-select, max 3)
- `Beliefs (Aqa'id)`
- `History (Seerah, Imams, events)`
- `Qur'an & Tafsir`
- `Spiritual growth`
- `Duas & Ziyarat`
- `Contemporary questions`
- `Hawza-style study / deeper dives`
- `I'm not sure yet`

---

## Suggested integration flow

1. After the user completes page 6, collect all four answers from local state.
2. Call `POST /onboarding` with the full payload.
3. On success, mark onboarding as complete in local state and navigate to the home screen.
4. On app load (for returning users), call `GET /onboarding/me`. A `200` means onboarding was already completed and can be skipped. A `404` means the user should be routed through the onboarding flow.
