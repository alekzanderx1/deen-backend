# Agentic Chatbot API Integration

## Purpose

This document explains how to integrate the new agentic streaming chatbot endpoint:

- New endpoint: `POST /chat/stream/agentic`
- Old endpoint: `POST /chat/stream`

The request body is similar to the legacy stream API, but the response contract is different. The old API streamed plain text and then appended a `"[REFERENCES]"` marker. The new API streams named SSE events with structured JSON payloads.

## Endpoint Summary

**Method:** `POST`  
**Path:** `/chat/stream/agentic`  
**Response content type:** `text/event-stream`

Optional authentication is supported:

- If a JWT is provided, the backend hydrates prior chat history for that `session_id` and persists the conversation.
- If no JWT is provided, the endpoint still works, but persistence is skipped.

There is also a non-streaming debug/testing endpoint:

- `POST /chat/agentic`

## Request Body

The endpoint accepts the same core fields the frontend already sends for the legacy stream API:

```json
{
  "user_query": "What does Islam say about patience?",
  "session_id": "user42:thread-7",
  "language": "english",
  "config": {
    "retrieval": {
      "shia_doc_count": 5,
      "sunni_doc_count": 2
    },
    "model": {
      "agent_model": "gpt-4o",
      "temperature": 0.7
    },
    "max_iterations": 5,
    "enable_classification": true,
    "enable_translation": true,
    "enable_enhancement": true,
    "stream_intermediate_steps": false
  }
}
```

### Required fields

- `user_query: string`
- `session_id: string`
- `language: string`

### Optional field

- `config: object`

### Important request notes

- `session_id` is still required. Keep it stable for a single conversation thread.
- `language` is still part of the request schema. Continue sending it even if it is usually `"english"`.
- `config` is optional.
- If `config` fails backend parsing, the current implementation logs the error and falls back to defaults instead of returning `400`.

## What Changed From `/chat/stream`

### Legacy `/chat/stream`

The old endpoint returned a plain streaming body:

1. Raw text chunks for the answer
2. A final `"[REFERENCES]"` marker
3. JSON references appended after that marker

Frontend implication:

- The client had to concatenate raw text.
- The client had to detect and parse the `"[REFERENCES]"` delimiter manually.

### New `/chat/stream/agentic`

The new endpoint returns proper SSE events:

1. `status`
2. `response_chunk`
3. `response_end`
4. `hadith_references` and/or `quran_references`
5. `done`

Frontend implication:

- Do not look for `"[REFERENCES]"`.
- Parse the stream as SSE frames.
- Route behavior by `event` name.
- Build the answer by concatenating `response_chunk.data.token`.
- Store references from dedicated reference events.

## SSE Event Contract

Each SSE frame follows standard SSE format:

```text
event: <event_name>
data: <json>

```

The current implementation emits these event types.

### 1. `status`

Emitted for major graph steps and first-seen tool calls.

```json
{
  "step": "agent",
  "message": "Agent thinking..."
}
```

Possible examples:

- `fiqh_classification`
- `agent`
- `tools`
- `generate_response`
- `check_if_non_islamic_tool`
- `check_if_fiqh_tool`
- `translate_to_english_tool`
- `enhance_query_tool`
- `retrieve_shia_documents_tool`
- `retrieve_sunni_documents_tool`
- `retrieve_combined_documents_tool`
- `retrieve_quran_tafsir_tool`

Use these to power loading states or step indicators. They are informational, not required to render the final answer.

### 2. `response_chunk`

Emitted for answer text tokens/chunks.

```json
{
  "token": "Patience in Islam is closely tied to trust in Allah..."
}
```

Frontend rule:

- Append `token` to the current assistant message buffer.

### 3. `response_end`

Emitted after the last answer token.

```json
{}
```

Frontend rule:

- Mark the assistant message text as complete.
- Do not assume the stream is over yet; references may still follow.

### 4. `hadith_references`

Emitted once if hadith/source documents were retrieved.

```json
{
  "references": [
    {
      "author": "Al-Kulayni",
      "volume": "2",
      "book_number": "1",
      "book_title": "Book of Faith",
      "chapter_number": "15",
      "chapter_title": "Patience",
      "collection": "Al-Kafi",
      "grade_ar": "صحيح",
      "grade_en": "Sahih",
      "hadith_id": "12345",
      "hadith_no": "10",
      "hadith_url": "https://example.com/hadith/12345",
      "lang": "en",
      "sect": "shia",
      "reference": "Al-Kafi, vol. 2, ch. 15, hadith 10",
      "text": "Patience is from faith...",
      "text_ar": "..."
    }
  ]
}
```

Frontend rule:

- Replace or populate the hadith references UI from `data.references`.

### 5. `quran_references`

Emitted once if Quran/Tafsir documents were retrieved.

```json
{
  "references": [
    {
      "surah_name": "Al-Baqarah",
      "title": "Tafsir al-Mizan",
      "chapter_number": "2",
      "verses_covered": "153-157",
      "starting_verse": "153",
      "ending_verse": "157",
      "author": "Allama Tabatabai",
      "collection": "Tafsir",
      "volume": "1",
      "sect": "shia",
      "quran_translation": "O you who believe, seek help through patience and prayer...",
      "tafsir_text": "These verses connect patience to steadfastness..."
    }
  ]
}
```

Frontend rule:

- Replace or populate the Quran/Tafsir references UI from `data.references`.

### 6. `error`

Emitted if the pipeline fails.

```json
{
  "message": "No response generated."
}
```

Frontend rule:

- Show the error state.
- Expect a trailing `done` event after `error`.

### 7. `done`

Always intended to be the terminal event.

```json
{}
```

Frontend rule:

- Finalize the stream lifecycle here.
- Stop loading indicators.
- Close any parser/state for the request.

## Expected Event Order

Typical successful order:

1. One or more `status`
2. One or more `response_chunk`
3. `response_end`
4. Zero or one `hadith_references`
5. Zero or one `quran_references`
6. `done`

Possible variants:

- Early exit for out-of-scope or fiqh queries:
  - `status` events may appear
  - a single `response_chunk`
  - `response_end`
  - `done`
- Failure:
  - `error`
  - `done`

Do not assume one network chunk equals one SSE event. Buffer and parse by SSE frame boundaries.

## Raw SSE Example

This is the wire format the frontend should expect:

```text
event: status
data: {"step":"fiqh_classification","message":"Checking query classification..."}

event: status
data: {"step":"agent","message":"Agent thinking..."}

event: status
data: {"step":"retrieve_shia_documents_tool","message":"Retrieving Shia documents..."}

event: status
data: {"step":"generate_response","message":"Generating response..."}

event: response_chunk
data: {"token":"Patience"}

event: response_chunk
data: {"token":" in Islam"}

event: response_chunk
data: {"token":" is closely tied to trust in Allah."}

event: response_end
data: {}

event: hadith_references
data: {"references":[{"author":"Al-Kulayni","collection":"Al-Kafi","reference":"Al-Kafi, vol. 2, hadith 10","text":"Patience is from faith...","text_ar":"..."}]}

event: quran_references
data: {"references":[{"surah_name":"Al-Baqarah","verses_covered":"153-157","quran_translation":"Seek help through patience and prayer...","tafsir_text":"These verses connect patience to steadfastness..."}]}

event: done
data: {}

```

## Frontend Integration Pattern

Because this is a `POST` endpoint with a JSON request body, do not use browser `EventSource`. Use `fetch()` and parse the streamed response body manually.

### Recommended client behavior

Maintain this local stream state:

```ts
type AgenticStreamState = {
  text: string;
  hadithReferences: unknown[];
  quranReferences: unknown[];
  statusSteps: Array<{ step: string; message: string }>;
  isResponseComplete: boolean;
  isDone: boolean;
  error: string | null;
};
```

### Example `fetch` integration

```ts
async function streamAgenticChat({
  userQuery,
  sessionId,
  language = "english",
  token,
  config,
  onEvent,
}: {
  userQuery: string;
  sessionId: string;
  language?: string;
  token?: string;
  config?: Record<string, unknown>;
  onEvent: (event: { event: string; data: any }) => void;
}) {
  const response = await fetch("/chat/stream/agentic", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      user_query: userQuery,
      session_id: sessionId,
      language,
      ...(config ? { config } : {}),
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Missing response body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split(/\n\n/);
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const trimmed = frame.trim();
      if (!trimmed) continue;

      let eventName = "message";
      let dataText = "";

      for (const line of trimmed.split("\n")) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataText += line.slice(5).trim();
        }
      }

      let data: any = {};
      if (dataText) {
        try {
          data = JSON.parse(dataText);
        } catch {
          data = { raw: dataText };
        }
      }

      onEvent({ event: eventName, data });
    }
  }
}
```

### Example event reducer

```ts
function reduceAgenticEvent(
  state: AgenticStreamState,
  evt: { event: string; data: any },
): AgenticStreamState {
  switch (evt.event) {
    case "status":
      return {
        ...state,
        statusSteps: [
          ...state.statusSteps,
          {
            step: evt.data?.step ?? "",
            message: evt.data?.message ?? "",
          },
        ],
      };

    case "response_chunk":
      return {
        ...state,
        text: state.text + (evt.data?.token ?? ""),
      };

    case "response_end":
      return {
        ...state,
        isResponseComplete: true,
      };

    case "hadith_references":
      return {
        ...state,
        hadithReferences: Array.isArray(evt.data?.references) ? evt.data.references : [],
      };

    case "quran_references":
      return {
        ...state,
        quranReferences: Array.isArray(evt.data?.references) ? evt.data.references : [],
      };

    case "error":
      return {
        ...state,
        error: evt.data?.message ?? "Streaming failed",
      };

    case "done":
      return {
        ...state,
        isDone: true,
      };

    default:
      return state;
  }
}
```

## Migration Checklist

When replacing `/chat/stream` with `/chat/stream/agentic`, update the frontend in these areas:

1. Change the endpoint path from `/chat/stream` to `/chat/stream/agentic`.
2. Keep sending `user_query`, `session_id`, and `language`.
3. Stop parsing `"[REFERENCES]"` from the text stream.
4. Start parsing SSE frames by `event:` and `data:`.
5. Build the assistant message from `response_chunk` events only.
6. Treat `response_end` as text completion, not stream completion.
7. Read references from `hadith_references` and `quran_references`.
8. Treat `done` as the final lifecycle event.
9. Handle `error` separately from normal text rendering.
10. Continue using `fetch`, not `EventSource`, because the endpoint is `POST`.

## Important Implementation Notes

These are current backend behaviors that the frontend should assume for now:

- `status` events are emitted by the current pipeline implementation and can appear before any text.
- `stream_intermediate_steps` exists in the config model, but the current streaming pipeline emits `status` events regardless.
- `response_end` may arrive before reference events.
- `done` is the event that should end the request lifecycle.
- Early-exit responses for non-Islamic or fiqh queries can still arrive as normal `response_chunk` text.
- Reference events are separated by source type:
  - `hadith_references`
  - `quran_references`

## Recommended UI Behavior

- Render the assistant bubble as soon as the first `response_chunk` arrives.
- Optionally render `status` messages in a transient “thinking” area, not inside the final answer text.
- Attach references after `response_end` when reference events arrive.
- Keep the request open until `done`.
- If `error` arrives, surface the error and still wait for stream termination.

## Minimal cURL Example

```bash
curl -N \
  -X POST http://127.0.0.1:8000/chat/stream/agentic \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "What does Islam say about patience?",
    "session_id": "frontend-test-session",
    "language": "english"
  }'
```

## Summary

The migration is not just a route rename. The request body is mostly unchanged, but the response parser must move from:

- raw text streaming with a `"[REFERENCES]"` suffix

to:

- structured SSE event handling with separate event types for text, status, references, errors, and completion.

If the frontend updates its parser around the event contract above, it will be aligned with the current `/chat/stream/agentic` implementation.
