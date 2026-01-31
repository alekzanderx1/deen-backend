# Personalized Lesson Primers – Development Plan

## Goal
Deliver per-lesson guidance that combines instant baseline primers with a “For you” personalized section that targets a user’s gaps/interests, without slowing lesson load times.

## Experience Overview
- Baseline primers (2–3 bullets + optional mini glossary) ship with the lesson and render instantly.
- A “For you” section is fetched in parallel when a lesson opens; UI shows a loader until personalized bullets arrive.
- If personalization is unavailable (no signals, failure), baseline still shows; personalized section can display a friendly “nothing extra yet” state.

## API Shape (proposed)
- `GET /lessons/{id}/primer-baseline`
  - Auth required, no `user_id`.
  - Returns preset bullets and glossary for the lesson. Always fast; can be bundled into the lesson fetch.
- `GET /lessons/{id}/primer-for-you?user_id=...&force_refresh=...`
  - Auth required, `user_id` required.
  - Returns: `personalized_bullets` (2–3), `generated_at`, `from_cache`, `stale` (optional), `personalized_available` (bool).
  - No source note IDs in the response (kept internally for traceability/telemetry).

## Personalization Inputs
- User signals: memory notes (learning gaps, interests, behavior) relevant to this lesson’s tags/tree; recent elaborations; user_progress (completion/recency).
- Lesson signals: summary, tags, skill_level, updated_at.
- Confidence gating: if signals are weak/old → respond with empty personalized list and `personalized_available=false`.

## Generation Triggers and Freshness
- On lesson open: check cache; if fresh → return cached. If stale/absent → generate on the spot while UI shows loader.
- `force_refresh=true` bypasses cache.
- Freshness conditions (all must hold):
  - `lesson_version` unchanged (e.g., lesson updated_at).
  - `memory_version` unchanged (max updated_at of relevant user notes).
  - `ttl_expires_at` not passed (e.g., 3–7 days TTL).
- Stale-while-revalidate (optional in a single call): serve cached if present; if stale, regenerate and return new; otherwise return cached with `stale=true`.

## Guardrails
- Length: 2–3 personalized bullets, ~150–220 words total.
- Additive only: do not duplicate or contradict baseline primers.
- Failure handling: on AI/memory fetch error, return baseline only with `personalized_available=false`.
- Low-signal handling: if relevance/confidence is low, skip personalization rather than send noisy bullets.

## Data Storage (suggested)
- Baseline primers: stored with lesson metadata in Postgres (existing lessons table or an attached JSONB field).
- Personalized cache: new Postgres table (suggested schema below) to persist per-user, per-lesson personalized primers.

### Suggested Table: `personalized_primers`
*(Example schema; adjust as needed.)*
- `user_id` (pk part, string)
- `lesson_id` (pk part, bigint)
- `personalized_bullets` (JSONB) — array of strings or objects `{text, emphasis?}`
- `generated_at` (TIMESTAMP with tz)
- `inputs_hash` (TEXT) — hash of lesson summary/tags + relevant note IDs/timestamps + TTL bucket
- `lesson_version` (TIMESTAMP with tz) — copy of lesson updated_at when generated
- `memory_version` (TIMESTAMP with tz) — max updated_at of user notes used
- `ttl_expires_at` (TIMESTAMP with tz)
- `stale` (BOOLEAN) — optional quick flag

**Indexes:** `(user_id, lesson_id)` primary key; optional index on `ttl_expires_at` for cleanup.

## Caching Logic
- Cache key: `(user_id, lesson_id, inputs_hash)`.
- Fresh if lesson_version and memory_version match current, and TTL not expired.
- On stale hit: either regenerate synchronously (preferred) or return stale with `stale=true` and regenerate inline if latency acceptable.

### What “stale-while-revalidate” Means
- Serve the last cached primer immediately, even if it is past its TTL or inputs have changed (mark it `stale=true`).
- In the same request, kick off regeneration; once the new primer is ready, return it (replacing the stale copy) and update the cache.
- Net effect: users see something right away, but the system refreshes in the background so the next request is fresh.

## Telemetry
- Log (internal only): cache hit/miss, generation time, note IDs used, force_refresh usage, `personalized_available` status.
- User feedback (thumbs) can be stored separately for later tuning.

## Agentic AI Recommendation
- Use a LangGraph agent to orchestrate the personalized primer flow: fetching relevant user memory, deciding whether personalization is warranted, and generating/validating the “For you” bullets.
- Typical use: nodes (or steps) for (1) gathering lesson context, (2) fetching/filtering relevant user notes, (3) deciding if signals are strong enough to personalize, (4) drafting personalized bullets, and (5) validating length/style/guardrails before storing to cache.
- Benefit: clearer control over when to skip personalization (low signals), explicit branching for fallbacks, and easier extension later (e.g., adding more checks or sources without rewriting the whole flow).

## Implementation Notes (suggested order, not prescriptive)
- Seed baselines first: create concise, relevant 2–3 baseline primers per lesson (placeholder AI-generated is fine) and store them with the lesson so they ship instantly.
- Set up storage: add the `personalized_primers` table (or equivalent) and data access layer to hold per-user cached personalized bullets.
- Build personalized endpoint: wire cache lookup + freshness checks + generation fallback; ensure graceful fallback to baseline when signals are weak or on failure.
- Add telemetry and handling: log cache behavior and failures; support `force_refresh`; consider stale-while-revalidate if latency allows.
