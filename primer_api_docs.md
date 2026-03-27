# Primer API Docs

This document covers the Primer APIs in `api/primers.py` for frontend integration.

## Base Path

- Local/dev base URL: `http://localhost:8000`
- Primer routes are under: `/primers`

## Auth

- Current implementation does **not** enforce JWT auth on primer routes in `main.py`.
- If auth is re-enabled later, expect standard `Authorization: Bearer <token>` headers.

---

## 1) Get Baseline Primer

`GET /primers/{lesson_id}/baseline`

Returns static lesson primer content (same for all users).

### Path Params

- `lesson_id` (number, required)

### Success Response (`200`)

```json
{
  "lesson_id": 12,
  "baseline_bullets": ["Understand key term A", "Review concept B"],
  "glossary": {
    "ijtihad": "Independent legal reasoning"
  },
  "updated_at": "2026-01-19T22:11:04.123456+00:00"
}
```

### Error Responses

- `404` if lesson does not exist

```json
{ "detail": "Lesson not found" }
```

- `500` on unhandled server error

---

## 2) Get Personalized Primer (non-streaming)

`POST /primers/personalized`

Generates or returns cached personalized bullets for a user+lesson.

### Request Body

```json
{
  "user_id": "user_123",
  "lesson_id": 12,
  "force_refresh": false,
  "filter": true
}
```

### Request Fields

- `user_id` (string, required)
- `lesson_id` (number, required)
- `force_refresh` (boolean, optional, default `false`)
  - `true`: skip cache and regenerate
- `filter` (boolean, optional, default `false`)
  - `true`: use relevance filtering (embeddings/tag fallback)
  - `false`: use all available notes

### Success Response (`200`)

```json
{
  "personalized_bullets": [
    "You previously struggled with pronunciation; focus on makharij examples first.",
    "Because you prefer practical learning, start with the guided recitation section."
  ],
  "generated_at": "2026-02-03T18:40:10.991623+00:00",
  "from_cache": false,
  "stale": false,
  "personalized_available": true
}
```

### Fallback Response (`200`, personalization unavailable)

```json
{
  "personalized_bullets": [],
  "generated_at": null,
  "from_cache": false,
  "stale": false,
  "personalized_available": false
}
```

### Error Responses

- `404` if lesson does not exist

```json
{ "detail": "Lesson not found" }
```

- `422` on request validation errors

### Notes

- Service requires at least 2 generated bullets for a personalized success.
- Max returned bullets is 3.
- Unexpected internal errors are converted to fallback `200` (not `500`) for this endpoint.

---

## 3) Stream Personalized Primer (SSE)

`POST /primers/personalized/stream`

Streams status and generation progress as Server-Sent Events.

### Request Body

Same schema as non-streaming endpoint:

```json
{
  "user_id": "user_123",
  "lesson_id": 12,
  "force_refresh": false,
  "filter": true
}
```

### Response

- Content-Type: `text/event-stream`
- Headers include:
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no`

### SSE Event Format

Each message is:

```text
event: <event_name>
data: <json_payload>

```

### Event Types

#### `status`

Progress updates.

```text
event: status
data: {"message":"Checking cache..."}
```

#### `llm_chunk`

Raw streamed model chunk/token text.

```text
event: llm_chunk
data: {"content":"{\"personalized_"}
```

#### `bullet`

Parsed bullet item.

```text
event: bullet
data: {"index":0,"content":"Start with pronunciation drills before theory."}
```

#### `metadata`

Final generation metadata.

```text
event: metadata
data: {"from_cache":false,"generated_at":"2026-02-03T18:40:10.991623+00:00","stale":false,"personalized_available":true}
```

#### `error`

Error details. Payload shape can vary:

- `{"error":"Lesson not found"}`
- `{"error":"Internal server error","personalized_available":false}`
- `{"message":"<exception message>","personalized_available":false}`

#### `done`

Stream completion marker.

```text
event: done
data: {"success":true}
```

`success` may be `false` for endpoint-level failures (for example, lesson not found before generation starts).

### Recommended Client Handling

- Treat `metadata.personalized_available` as the primary success signal for personalization.
- Treat any `error` event as failure, even if a later `done` has `success: true`.
- Use `done` to close UI loading state.

---

## TypeScript Interfaces (Suggested)

```ts
export interface BaselinePrimerResponse {
  lesson_id: number;
  baseline_bullets: string[];
  glossary: Record<string, unknown>;
  updated_at: string | null;
}

export interface PersonalizedPrimerRequest {
  user_id: string;
  lesson_id: number;
  force_refresh?: boolean;
  filter?: boolean;
}

export interface PersonalizedPrimerResponse {
  personalized_bullets: string[];
  generated_at: string | null;
  from_cache: boolean;
  stale: boolean;
  personalized_available: boolean;
}
```

---

## Quick cURL Examples

### Baseline

```bash
curl -X GET "http://localhost:8000/primers/12/baseline"
```

### Personalized (non-streaming)

```bash
curl -X POST "http://localhost:8000/primers/personalized" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "lesson_id": 12,
    "force_refresh": false,
    "filter": false
  }'
```

### Personalized (streaming SSE)

```bash
curl -N -X POST "http://localhost:8000/primers/personalized/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "lesson_id": 12,
    "force_refresh": false,
    "filter": true
  }'
```

Example streaming SSE response:

event: status
data: {"message": "Starting primer generation..."}

event: status
data: {"message": "Generating personalized primer..."}

event: status
data: {"message": "Fetching lesson details..."}

event: status
data: {"message": "Analyzing your learning history..."}

event: status
data: {"message": "Evaluating personalization potential..."}

event: status
data: {"message": "Generating personalized content..."}

event: llm_chunk
data: {"content": "{\n"}

event: llm_chunk
data: {"content": " "}

event: llm_chunk
data: {"content": " \""}

event: llm_chunk
data: {"content": "personal"}

event: llm_chunk
data: {"content": "ized"}

event: llm_chunk
data: {"content": "\_b"}

event: llm_chunk
data: {"content": "ul"}

event: llm_chunk
data: {"content": "lets"}

event: llm_chunk
data: {"content": "\":"}

event: llm_chunk
data: {"content": " [\n"}

event: llm_chunk
data: {"content": " "}

event: llm_chunk
data: {"content": " \""}

event: llm_chunk
data: {"content": "Understanding"}

event: llm_chunk
data: {"content": " the"}

event: llm_chunk
data: {"content": " distinction"}

event: llm_chunk
data: {"content": " between"}

event: llm_chunk
data: {"content": " Q"}

event: llm_chunk
data: {"content": "adha"}

event: llm_chunk
data: {"content": "'"}

event: llm_chunk
data: {"content": " and"}

event: llm_chunk
data: {"content": " Q"}

event: llm_chunk
data: {"content": "adar"}

event: llm_chunk
data: {"content": " is"}

event: llm_chunk
data: {"content": " crucial"}

event: llm_chunk
data: {"content": "."}

event: llm_chunk
data: {"content": " Q"}

event: llm_chunk
data: {"content": "adha"}

event: llm_chunk
data: {"content": "'"}

event: llm_chunk
data: {"content": " represents"}

event: llm_chunk
data: {"content": " the"}

event: llm_chunk
data: {"content": " execution"}

event: llm_chunk
data: {"content": " of"}

event: llm_chunk
data: {"content": " Allah"}

event: llm_chunk
data: {"content": "'s"}

event: llm_chunk
data: {"content": " divine"}

event: llm_chunk
data: {"content": " will"}

event: llm_chunk
data: {"content": ","}

event: llm_chunk
data: {"content": " while"}

event: llm_chunk
data: {"content": " Q"}

event: llm_chunk
data: {"content": "adar"}

event: llm_chunk
data: {"content": " refers"}

event: llm_chunk
data: {"content": " to"}

event: llm_chunk
data: {"content": " the"}

event: llm_chunk
data: {"content": " measured"}

event: llm_chunk
data: {"content": " destiny"}

event: llm_chunk
data: {"content": " that"}

event: llm_chunk
data: {"content": " reflects"}

event: llm_chunk
data: {"content": " divine"}

event: llm_chunk
data: {"content": " wisdom"}

event: llm_chunk
data: {"content": "."}

event: llm_chunk
data: {"content": " This"}

event: llm_chunk
data: {"content": " balance"}

event: llm_chunk
data: {"content": " is"}

event: llm_chunk
data: {"content": " essential"}

event: llm_chunk
data: {"content": " for"}

event: llm_chunk
data: {"content": " compreh"}

event: llm_chunk
data: {"content": "ending"}

event: llm_chunk
data: {"content": " how"}

event: llm_chunk
data: {"content": " human"}

event: llm_chunk
data: {"content": " actions"}

event: llm_chunk
data: {"content": ","}

event: llm_chunk
data: {"content": " including"}

event: llm_chunk
data: {"content": " sins"}

event: llm_chunk
data: {"content": " and"}

event: llm_chunk
data: {"content": " repentance"}

event: llm_chunk
data: {"content": ","}

event: llm_chunk
data: {"content": " fit"}

event: llm_chunk
data: {"content": " into"}

event: llm_chunk
data: {"content": " the"}

event: llm_chunk
data: {"content": " larger"}

event: llm_chunk
data: {"content": " framework"}

event: llm_chunk
data: {"content": " of"}

event: llm_chunk
data: {"content": " divine"}

event: llm_chunk
data: {"content": " decree"}

event: llm_chunk
data: {"content": ".\",\n"}

event: llm_chunk
data: {"content": " "}

event: llm_chunk
data: {"content": " \""}

event: llm_chunk
data: {"content": "The"}

event: llm_chunk
data: {"content": " Sh"}

event: llm_chunk
data: {"content": "ia"}

event: llm_chunk
data: {"content": " doctrine"}

event: llm_chunk
data: {"content": " of"}

event: llm_chunk
data: {"content": " '"}

event: llm_chunk
data: {"content": "al"}

event: llm_chunk
data: {"content": "-am"}

event: llm_chunk
data: {"content": "r"}

event: llm_chunk
data: {"content": " bay"}

event: llm_chunk
data: {"content": "n"}

event: llm_chunk
data: {"content": " al"}

event: llm_chunk
data: {"content": "-am"}

event: llm_chunk
data: {"content": "ray"}

event: llm_chunk
data: {"content": "n"}

event: llm_chunk
data: {"content": "'"}

event: llm_chunk
data: {"content": " highlights"}

event: llm_chunk
data: {"content": " the"}

event: llm_chunk
data: {"content": " middle"}

event: llm_chunk
data: {"content": " path"}

event: llm_chunk
data: {"content": " between"}

event: llm_chunk
data: {"content": " absolute"}

event: llm_chunk
data: {"content": " comp"}

event: llm_chunk
data: {"content": "ulsion"}

event: llm_chunk
data: {"content": " ("}

event: llm_chunk
data: {"content": "j"}

event: llm_chunk
data: {"content": "abr"}

event: llm_chunk
data: {"content": ")"}

event: llm_chunk
data: {"content": " and"}

event: llm_chunk
data: {"content": " absolute"}

event: llm_chunk
data: {"content": " delegation"}

event: llm_chunk
data: {"content": " ("}

event: llm_chunk
data: {"content": "ta"}

event: llm_chunk
data: {"content": "fw"}

event: llm_chunk
data: {"content": "\u012bd"}

event: llm_chunk
data: {"content": ")."}

event: llm_chunk
data: {"content": " This"}

event: llm_chunk
data: {"content": " principle"}

event: llm_chunk
data: {"content": " emphasizes"}

event: llm_chunk
data: {"content": " that"}

event: llm_chunk
data: {"content": " while"}

event: llm_chunk
data: {"content": " Allah"}

event: llm_chunk
data: {"content": "'s"}

event: llm_chunk
data: {"content": " will"}

event: llm_chunk
data: {"content": " is"}

event: llm_chunk
data: {"content": " paramount"}

event: llm_chunk
data: {"content": ","}

event: llm_chunk
data: {"content": " humans"}

event: llm_chunk
data: {"content": " retain"}

event: llm_chunk
data: {"content": " agency"}

event: llm_chunk
data: {"content": " in"}

event: llm_chunk
data: {"content": " their"}

event: llm_chunk
data: {"content": " choices"}

event: llm_chunk
data: {"content": ","}

event: llm_chunk
data: {"content": " making"}

event: llm_chunk
data: {"content": " accountability"}

event: llm_chunk
data: {"content": " meaningful"}

event: llm_chunk
data: {"content": " and"}

event: llm_chunk
data: {"content": " connecting"}

event: llm_chunk
data: {"content": " to"}

event: llm_chunk
data: {"content": " the"}

event: llm_chunk
data: {"content": " concepts"}

event: llm_chunk
data: {"content": " of"}

event: llm_chunk
data: {"content": " repentance"}

event: llm_chunk
data: {"content": " and"}

event: llm_chunk
data: {"content": " reliance"}

event: llm_chunk
data: {"content": " on"}

event: llm_chunk
data: {"content": " Allah"}

event: llm_chunk
data: {"content": " ("}

event: llm_chunk
data: {"content": "t"}

event: llm_chunk
data: {"content": "aw"}

event: llm_chunk
data: {"content": "akk"}

event: llm_chunk
data: {"content": "ul"}

event: llm_chunk
data: {"content": ")."}

event: llm_chunk
data: {"content": "\",\n"}

event: llm_chunk
data: {"content": " "}

event: llm_chunk
data: {"content": " \""}

event: llm_chunk
data: {"content": "In"}

event: llm_chunk
data: {"content": " the"}

event: llm_chunk
data: {"content": " context"}

event: llm_chunk
data: {"content": " of"}

event: llm_chunk
data: {"content": " Q"}

event: llm_chunk
data: {"content": "adha"}

event: llm_chunk
data: {"content": "'"}

event: llm_chunk
data: {"content": " and"}

event: llm_chunk
data: {"content": " Q"}

event: llm_chunk
data: {"content": "adar"}

event: llm_chunk
data: {"content": ","}

event: llm_chunk
data: {"content": " accountability"}

event: llm_chunk
data: {"content": " is"}

event: llm_chunk
data: {"content": " tied"}

event: llm_chunk
data: {"content": " to"}

event: llm_chunk
data: {"content": " how"}

event: llm_chunk
data: {"content": " human"}

event: llm_chunk
data: {"content": " actions"}

event: llm_chunk
data: {"content": " align"}

event: llm_chunk
data: {"content": " with"}

event: llm_chunk
data: {"content": " divine"}

event: llm_chunk
data: {"content": " decree"}

event: llm_chunk
data: {"content": "."}

event: llm_chunk
data: {"content": " Sh"}

event: llm_chunk
data: {"content": "ia"}

event: llm_chunk
data: {"content": " thought"}

event: llm_chunk
data: {"content": " maintains"}

event: llm_chunk
data: {"content": " that"}

event: llm_chunk
data: {"content": " Allah"}

event: llm_chunk
data: {"content": "'s"}

event: llm_chunk
data: {"content": " knowledge"}

event: llm_chunk
data: {"content": " encompasses"}

event: llm_chunk
data: {"content": " all"}

event: llm_chunk
data: {"content": " destiny"}

event: llm_chunk
data: {"content": ","}

event: llm_chunk
data: {"content": " yet"}

event: llm_chunk
data: {"content": " humans"}

event: llm_chunk
data: {"content": " are"}

event: llm_chunk
data: {"content": " responsible"}

event: llm_chunk
data: {"content": " for"}

event: llm_chunk
data: {"content": " their"}

event: llm_chunk
data: {"content": " choices"}

event: llm_chunk
data: {"content": ","}

event: llm_chunk
data: {"content": " particularly"}

event: llm_chunk
data: {"content": " regarding"}

event: llm_chunk
data: {"content": " actions"}

event: llm_chunk
data: {"content": " that"}

event: llm_chunk
data: {"content": " require"}

event: llm_chunk
data: {"content": " repentance"}

event: llm_chunk
data: {"content": " and"}

event: llm_chunk
data: {"content": " the"}

event: llm_chunk
data: {"content": " hope"}

event: llm_chunk
data: {"content": " for"}

event: llm_chunk
data: {"content": " Allah"}

event: llm_chunk
data: {"content": "'s"}

event: llm_chunk
data: {"content": " mercy"}

event: llm_chunk
data: {"content": ".\"\n"}

event: llm_chunk
data: {"content": " "}

event: llm_chunk
data: {"content": " ]\n"}

event: llm_chunk
data: {"content": "}"}

event: bullet
data: {"index": 0, "content": "Understanding the distinction between Qadha' and Qadar is crucial. Qadha' represents the execution of Allah's divine will, while Qadar refers to the measured destiny that reflects divine wisdom. This balance is essential for comprehending how human actions, including sins and repentance, fit into the larger framework of divine decree."}

event: bullet
data: {"index": 1, "content": "The Shia doctrine of 'al-amr bayn al-amrayn' highlights the middle path between absolute compulsion (jabr) and absolute delegation (tafw\u012bd). This principle emphasizes that while Allah's will is paramount, humans retain agency in their choices, making accountability meaningful and connecting to the concepts of repentance and reliance on Allah (tawakkul)."}

event: bullet
data: {"index": 2, "content": "In the context of Qadha' and Qadar, accountability is tied to how human actions align with divine decree. Shia thought maintains that Allah's knowledge encompasses all destiny, yet humans are responsible for their choices, particularly regarding actions that require repentance and the hope for Allah's mercy."}

event: status
data: {"message": "Saving for future use..."}

event: metadata
data: {"from_cache": false, "generated_at": "2026-02-03T01:46:50.651835+00:00", "stale": false, "personalized_available": true}

event: done
data: {"success": true}
