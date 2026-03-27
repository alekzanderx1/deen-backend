# Lesson Page Quiz API Docs

This guide covers the two learner-facing quiz APIs in `api/hikmah.py`:

- `GET /hikmah/pages/{lesson_content_id}/quiz-questions`
- `POST /hikmah/pages/{lesson_content_id}/quiz-submit`

## URL

- Quiz routes are under: `/hikmah`

## Auth

- Include `Authorization: Bearer <token>`.

---

## 1) Get Lesson Page Quiz Questions

`GET /hikmah/pages/{lesson_content_id}/quiz-questions`

### When to call

- Call when a lesson page is opened (or when user navigates to a page section with quiz).
- Use response to render all active MCQ questions for that page.

### Path Params

- `lesson_content_id` (number, required): ID of the lesson page (`lesson_content.id`).

### Success Response (`200`)

```json
{
  "lesson_content_id": 45,
  "questions": [
    {
      "id": 1201,
      "prompt": "What is the key point of this section?",
      "order_position": 1,
      "choices": [
        {
          "id": 5501,
          "choice_key": "A",
          "choice_text": "First option",
          "order_position": 1
        },
        {
          "id": 5502,
          "choice_key": "B",
          "choice_text": "Second option",
          "order_position": 2
        }
      ],
      "correct_choice_id": 5502,
      "explanation": "Second option is correct because ..."
    }
  ]
}
```

### Response Notes

- Returns only **active** questions.
- Questions are sorted by `order_position`, then `id`.
- Choices are sorted by `order_position`, then `id`.
- `questions` can be an empty array if page exists but has no active quiz questions.
- `correct_choice_id` is included in this response.

### Error Responses

- `404` if lesson content page does not exist:

```json
{ "detail": "Lesson content page not found" }
```

- `500` for unexpected server/configuration issues.

---

## 2) Submit Lesson Page Quiz Answer

`POST /hikmah/pages/{lesson_content_id}/quiz-submit`

### When to call

- Call immediately after user submits an answer for a specific question.
- This endpoint is for persistence + background memory processing (fire-and-forget).

### Request Body

```json
{
  "user_id": "user_123",
  "question_id": 1201,
  "selected_choice_id": 5502,
  "answered_at": "2026-02-18T17:45:12.000Z"
}
```

### Request Fields

- `user_id` (string, required)
- `question_id` (number, required, must be `> 0`)
- `selected_choice_id` (number, required, must be `> 0`)
- `answered_at` (ISO datetime string, optional)
  - If omitted, server uses current UTC time.

### Success Ack (`202 Accepted`)

```json
{
  "status": "received"
}
```

### Important Behavior

- Processing happens asynchronously in a background task.
- `202` means request was accepted for processing, not that answer validity was confirmed.
- If IDs are mismatched/invalid (for example wrong `question_id` for that page), backend logs and ignores during background processing; the HTTP response is still `202`.
- If you need immediate correctness UI, compute it client-side using `correct_choice_id` from the questions API.

### Validation Errors

- `422` if request payload is invalid (for example missing required fields, non-integer IDs, or IDs `<= 0`).

---

## Recommended Frontend Integration Flow

1. On lesson page load, call `GET /hikmah/pages/{lesson_content_id}/quiz-questions`.
2. Render questions/choices in returned order.
3. When user answers:
   - Determine correctness in UI using `selected_choice_id === correct_choice_id`.
   - Optionally show `explanation`.
   - Send `POST /hikmah/pages/{lesson_content_id}/quiz-submit` in background.
4. Treat `202` as delivery acknowledgement only.
5. Prevent duplicate submissions client-side if user taps multiple times (backend currently records each accepted attempt).

---

## Suggested TypeScript Interfaces

```ts
export interface QuizChoiceResponse {
  id: number;
  choice_key: string;
  choice_text: string;
  order_position: number;
}

export interface QuizQuestionResponse {
  id: number;
  prompt: string;
  order_position: number;
  choices: QuizChoiceResponse[];
  correct_choice_id: number;
  explanation: string | null;
}

export interface LessonPageQuizQuestionsResponse {
  lesson_content_id: number;
  questions: QuizQuestionResponse[];
}

export interface SubmitLessonPageQuizAnswerRequest {
  user_id: string;
  question_id: number;
  selected_choice_id: number;
  answered_at?: string; // ISO datetime
}

export interface QuizSubmissionAckResponse {
  status: "received";
}
```

---

## Quick cURL Examples

### Get Questions

```bash
curl -X GET "http://localhost:8000/hikmah/pages/45/quiz-questions"
```

### Submit Answer

```bash
curl -X POST "http://localhost:8000/hikmah/pages/45/quiz-submit" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "question_id": 1201,
    "selected_choice_id": 5502,
    "answered_at": "2026-02-18T17:45:12.000Z"
  }'
```
