# Pitfalls Research: v1.2 Claude + Voyage AI Migration

**Project:** Deen Backend — v1.2 Claude Migration (OpenAI → Claude + Voyage AI)
**Researched:** 2026-04-09
**Scope:** Migrating LLM provider from OpenAI to Claude, embeddings from text-embedding-3-small to Voyage AI voyage-4, and pgvector column resizing from 1536 → 1024 dimensions
**Confidence:** HIGH (direct code inspection + installed package source + GitHub issue tracking + official docs)

---

## Critical (breaks on deploy)

### CRITICAL-1: `openai_api_key` kwarg passed to `init_chat_model` silently becomes an invalid kwarg for Claude

**What goes wrong:**
`agents/core/chat_agent.py` `_create_llm_with_tools()` calls:
```python
init_chat_model(
    model=self.config.model.agent_model,
    openai_api_key=OPENAI_API_KEY,   # <-- THIS LINE
    temperature=...,
    max_tokens=...,
)
```

`core/chat_models.py` repeats this across all four getter functions (`get_generator_model`, `get_classifier_model`, `get_enhancer_model`, `get_translator_model`).

When the model name is a Claude model (e.g., `claude-sonnet-4-6`), `init_chat_model` infers `model_provider="anthropic"` and instantiates `ChatAnthropic(model=model, **kwargs)`. The `openai_api_key` kwarg is not a recognized field on `ChatAnthropic` and will raise a `pydantic.ValidationError` at startup — specifically: `ChatAnthropic.__init__() got an unexpected keyword argument 'openai_api_key'`.

**Why it happens:**
`init_chat_model` passes `**kwargs` directly to the provider class constructor (confirmed in `venv/lib/python3.11/site-packages/langchain/chat_models/base.py` lines 352-356). There is no kwarg translation between providers.

**What breaks:** The server fails to start. Every call to `get_generator_model()`, `get_classifier_model()`, `get_enhancer_model()` or the `ChatAgent.__init__()` raises before handling any request.

**Files that must change:**
- `agents/core/chat_agent.py` — `_create_llm_with_tools()`: remove `openai_api_key=`, add `anthropic_api_key=`
- `core/chat_models.py` — all four model getter functions: same replacement

**Prevention:** Replace `openai_api_key=OPENAI_API_KEY` with `anthropic_api_key=os.getenv("CLAUDE_API_KEY")` in all call sites. Never use provider-specific kwarg names in calls to `init_chat_model` unless you control which provider will be selected.

---

### CRITICAL-2: `CLAUDE_API_KEY` env var name is not the SDK default — silent None unless wired explicitly

**What goes wrong:**
`langchain-anthropic` version 0.3.22 (installed in this project) reads the API key via:
```python
anthropic_api_key: SecretStr = Field(
    alias="api_key",
    default_factory=secret_from_env("ANTHROPIC_API_KEY", default=""),
)
```
The fallback default is an **empty string**, not a runtime error. If `ANTHROPIC_API_KEY` is not set and the key is not passed explicitly, `ChatAnthropic` initializes with an empty API key. The first actual API call fails with an `AuthenticationError` (HTTP 401), not at startup.

The user has named their env var `CLAUDE_API_KEY`. The Anthropic SDK and `langchain-anthropic` both default to `ANTHROPIC_API_KEY`. These are different names and there is no automatic aliasing.

**Failure mode:** The server starts without error. The first user request that reaches an LLM call gets a 401/AuthenticationError, which propagates as an unhandled exception from inside a LangGraph node and results in an HTTP 500 to the user.

**Prevention:** Pass the key explicitly in all `init_chat_model` or `ChatAnthropic` calls:
```python
import os
anthropic_api_key = os.getenv("CLAUDE_API_KEY")
# Then pass: anthropic_api_key=anthropic_api_key (or api_key=anthropic_api_key)
```
Alternatively, add `ANTHROPIC_API_KEY=${CLAUDE_API_KEY}` to `.env` so both names resolve. The explicit pass is safer — it fails fast at construction time rather than at first API call.

**Detection:** Add a startup guard in `core/config.py` analogous to the existing `OPENAI_API_KEY` check. Replace the current `if not OPENAI_API_KEY` guard with one for `CLAUDE_API_KEY`.

---

### CRITICAL-3: `core/config.py` raises `ValueError` on startup if `OPENAI_API_KEY` is absent after package removal

**What goes wrong:**
`core/config.py` line 44:
```python
if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("Missing API keys! Ensure they are set in the .env file.")
```

If `langchain-openai` is removed from `requirements.txt` AND the `.env` no longer has `OPENAI_API_KEY`, this guard fires on every server startup before any request is handled — before `main.py` runs, before uvicorn is ready.

**Files that must change:** `core/config.py` — replace or remove `OPENAI_API_KEY` guard; add `CLAUDE_API_KEY` guard in its place.

**When it bites:** Phase that removes `langchain-openai` from `requirements.txt` must simultaneously update `core/config.py` guards. Doing one without the other breaks startup in opposite directions (missing package vs. missing env var).

---

### CRITICAL-4: Three files instantiate a global `OpenAI` client at module import time

**What goes wrong:**
Three files create a module-level `OpenAI` client instance:
- `services/embedding_service.py` line 46: `self.client = OpenAI(api_key=OPENAI_API_KEY)` — inside `__init__`, safe.
- `modules/generation/stream_generator.py` line 13: `client = OpenAI(api_key=OPENAI_API_KEY)` — **module-level global**.
- `modules/classification/classifier.py` line 1: `from openai import OpenAI` with module-level usage.
- `core/pipeline.py` line 13: `client = OpenAI(api_key=OPENAI_API_KEY)` — **module-level global**.

If `openai` package is removed from `requirements.txt`, these `from openai import OpenAI` statements raise `ImportError` at module load time. FastAPI imports these modules transitively at startup (through route handlers and service imports), causing the application to fail to start entirely.

**Cascade risk:** `modules/generation/stream_generator.py` is imported by `core/pipeline.py`, and `modules/classification/classifier.py` is imported by `core/pipeline.py`. Even if the primary streaming path no longer uses the legacy pipeline, FastAPI's import chain pulls these in.

**Prevention:** Before removing `openai` from `requirements.txt`:
1. Audit all `from openai import` and `import openai` statements.
2. Remove the dead global `client = OpenAI(...)` instances in `stream_generator.py` and `pipeline.py`.
3. Replace `EmbeddingService.generate_embedding()` with Voyage AI calls.
4. Only then safely remove `openai` and `langchain-openai` from requirements.

**Phase ordering:** Dead code cleanup (global OpenAI clients) must happen before or in the same phase as `openai` package removal. Do not split across phases with the package removal first.

---

### CRITICAL-5: pgvector — altering vector column dimension requires DROP + recreate, not ALTER COLUMN

**What goes wrong:**
The `note_embeddings` and `lesson_chunk_embeddings` tables use `Vector(1536)` columns (defined in `db/models/embeddings.py` and `alembic/versions/20260122_create_embedding_tables.py`). After the migration, the target is `Vector(1024)` (Voyage AI voyage-4 default output).

PostgreSQL's pgvector extension does **not support `ALTER COLUMN ... TYPE vector(1024)`** on a column already defined as `vector(1536)`. Attempting this in an Alembic migration produces:
```
ERROR: operator does not exist: vector = vector(1024)
```
or similar cast failure depending on pgvector version.

**The only valid migration path:**
```sql
-- Drop HNSW index first (required before altering type)
DROP INDEX idx_note_embeddings_vector;
DROP INDEX idx_lesson_chunk_embeddings_vector;

-- Drop and recreate columns (pgvector cannot cast between fixed dimensions)
ALTER TABLE note_embeddings DROP COLUMN embedding;
ALTER TABLE note_embeddings ADD COLUMN embedding vector(1024) NOT NULL;

ALTER TABLE lesson_chunk_embeddings DROP COLUMN embedding;
ALTER TABLE lesson_chunk_embeddings ADD COLUMN embedding vector(1024) NOT NULL;

-- Recreate HNSW indexes for new dimension
CREATE INDEX idx_note_embeddings_vector
    ON note_embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_lesson_chunk_embeddings_vector
    ON lesson_chunk_embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

**Data consequence:** Dropping the column destroys all existing 1536-dim embeddings. There is no in-place migration of existing embedding data. Existing rows have their embedding column set to NULL after the drop. The NOT NULL constraint means existing rows without new embeddings cannot be inserted.

**Resolution:** The migration must either:
- Accept data loss (existing embeddings destroyed, regenerated on demand)
- Run a re-embedding pass before the migration: generate 1024-dim embeddings for all existing notes and lesson chunks, store in a temp column, then do the swap
- Use `ADD COLUMN embedding_new vector(1024)`, backfill, then `DROP COLUMN embedding`, `RENAME COLUMN embedding_new TO embedding`

**Alembic model sync:** Update `db/models/embeddings.py` `EMBEDDING_DIMENSIONS = 1536` to `1024`. Update `alembic/versions/20260122_create_embedding_tables.py` comment. Update `core/config.py` `EMBEDDING_DIMENSIONS` default from `"1536"` to `"1024"`.

---

## High (data integrity)

### HIGH-1: Stale 1536-dim embeddings mixed with new 1024-dim embeddings = silently wrong similarity scores

**What goes wrong:**
If the pgvector migration runs (column changed to 1024) but some existing rows still hold 1536-dim embeddings, pgvector will reject INSERT/UPDATE for those rows (`ERROR: expected 1024 dimensions, not 1536`). However, if the column is not yet migrated but Voyage AI is already generating 1024-dim vectors, pgvector rejects the inserts the other way.

The more dangerous scenario is the period between when the column is migrated to 1024 and when the re-embedding pass completes: similarity queries during this window operate against partially populated data (many rows have null embeddings or zero vectors), producing silently wrong results. Primer recommendations and note-to-lesson matching will match incorrectly or not match at all.

**Where this surfaces:**
- `services/embedding_service.py` `find_similar_notes_to_lesson()` — the raw SQL cosine distance query against `note_embeddings`. During the transition, this returns garbage scores or empty results.
- `services/primer_service.py` — personalized primers depend on similarity search; stale embeddings produce wrong personalization.

**Prevention strategy:**
1. Run migration during a maintenance window or low-traffic period.
2. Generate new Voyage AI embeddings for all existing `note_embeddings` and `lesson_chunk_embeddings` rows BEFORE dropping the old column.
3. Use the temp-column swap pattern: add `embedding_voyage vector(1024)`, batch-fill it, then atomically `DROP COLUMN embedding; RENAME COLUMN embedding_voyage TO embedding`.
4. Add a data integrity check: count rows where `embedding IS NULL` after migration and alert if > 0.

**Confidence:** HIGH — confirmed from pgvector behavior and the similarity search SQL in `embedding_service.py`.

---

### HIGH-2: `EmbeddingService` still holds an `OpenAI` client instance — Voyage AI replacement is not a simple swap

**What goes wrong:**
`services/embedding_service.py` defines `self.client = OpenAI(api_key=OPENAI_API_KEY)` and calls:
```python
self.client.embeddings.create(model=EMBEDDING_MODEL, input=text, dimensions=EMBEDDING_DIMENSIONS)
```

The Voyage AI Python SDK (`voyageai==0.3.7`, already installed) uses a completely different API:
```python
import voyageai
vo = voyageai.Client(api_key=VOYAGE_API_KEY)
result = vo.embed(["text"], model="voyage-4", output_dimension=1024)
result.embeddings[0]  # list of floats
```

The `langchain-voyageai` package is not installed (confirmed via glob — no `langchain_voyageai-*.dist-info`). Only the raw `voyageai` package is present. The function signature, return type structure, and error types all differ.

**What must change:** `EmbeddingService.generate_embedding()` and `generate_embeddings_batch()` must be rewritten from `OpenAI.embeddings.create()` to `voyageai.Client.embed()`. The batch interface in Voyage AI (`embed(texts_list)`) maps well to `generate_embeddings_batch()` but the response path is `result.embeddings` not `response.data[n].embedding`.

**Rate limit difference:** Voyage AI free tier is 3 RPM / 1M TPM. The `store_note_embeddings_batch()` and `store_lesson_chunk_embeddings()` methods may need retry logic with backoff if batches are large. The existing code has no retry logic for embedding calls.

---

### HIGH-3: Voyage AI `output_dimension` parameter is a Literal type — passing 1024 as int works but other values silently fail validation

**What goes wrong:**
The installed `voyageai` SDK (0.3.7) and the `langchain-voyageai` package (when added) both accept `output_dimension` as `Optional[Literal[256, 512, 1024, 2048]]`. Passing any other integer (e.g., `768`, `1536`, or `None`) does not raise a type error at call time because Python Literals are not enforced at runtime — but the Voyage AI API server rejects it with a 422 error.

The current `core/config.py` has:
```python
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
```
If the env var is not updated to `"1024"` (or one of the valid Voyage values), the `EmbeddingService` passes the wrong dimension and gets a 422 from Voyage AI.

**Prevention:** Pin `output_dimension=1024` in the `EmbeddingService` constructor rather than reading it from `EMBEDDING_DIMENSIONS` env var during the transition. Once migration is complete and stable, env var control can be restored.

---

## Medium (behavior differences)

### MEDIUM-1: Claude forbids empty assistant messages — known LangGraph incompatibility with multi-turn tool flows

**What goes wrong:**
When Claude returns a tool call with no accompanying text content (a common pattern when following instructions like "call this tool without adding commentary"), the resulting `AIMessage` has `content=""`. On the next turn of the LangGraph loop, this empty `AIMessage` is included in the conversation history passed to the API. Anthropic's Messages API explicitly forbids non-final assistant messages from being empty:
```
anthropic.BadRequestError: 400 - all messages must have non-empty content except for the optional final assistant message
```

This is a confirmed active issue in LangGraph (Issue #3168, reported January 2025, still open as of the research date). OpenAI permits empty content in intermediate messages; Anthropic does not.

**Where this surfaces in this codebase:**
The `_agent_node` in `agents/core/chat_agent.py` appends the LLM response to `state["messages"]` and then loops back through the graph. In multi-iteration tool-calling scenarios (the agent calls `retrieve_shia_documents_tool` then loops back to decide on next tool), Claude may emit tool calls with empty content after the first retrieval. The second turn then fails with a 400.

**Prevention:** After `response = self.llm.invoke(messages)`, add a filter before appending:
```python
# Claude-specific: remove empty intermediate messages from history
messages = [m for m in messages if not (hasattr(m, 'content') and m.content == '' and not getattr(m, 'tool_calls', None))]
```
Apply this filter inside `_agent_node` before passing `messages` to the LLM. This is the standard community workaround per LangGraph Issue #3168.

**Confidence:** HIGH — confirmed from GitHub issue, code inspection of `_agent_node` message accumulation pattern.

---

### MEDIUM-2: `with_structured_output(SEAResult)` has reported reliability issues with Anthropic — intermittent validation failures

**What goes wrong:**
`modules/fiqh/sea.py` uses:
```python
model = chat_models.get_classifier_model()
structured_model = model.with_structured_output(SEAResult)
result = structured_model.invoke(...)
```

`SEAResult` contains nested Pydantic models: a list of `Finding` objects, each with `description: str`, `confirmed: bool`, `citation: str`, `gap_summary: str`. This is a moderately complex nested schema.

Community-verified issue (LangChain GitHub #30158): `ChatAnthropic.with_structured_output()` exhibits intermittent validation errors — required fields go missing from the response, causing `ValidationError`. In one documented case, only 1 of 50 executions succeeded. The failure is non-deterministic, making it hard to catch in testing.

**Why `SEAResult` is specifically at risk:** The schema has 4 fields in `Finding` and 4 top-level fields in `SEAResult`, including a `Literal["SUFFICIENT", "INSUFFICIENT"]` constrained field. Claude's implementation of structured output uses tool calling under the hood (not true JSON schema enforcement), so the model can occasionally omit fields it deems irrelevant.

**Mitigation options (in order of reliability):**
1. `model.with_structured_output(SEAResult, include_raw=True)` — wrap in try/except and check `parsing_error` field; return the INSUFFICIENT fallback on parse failure (the existing `except` clause already does this for exceptions, but not for validation errors that resolve to a wrong object).
2. Add explicit field descriptions to `Finding` and `SEAResult` Pydantic fields via `Field(description="...")` — more verbose prompt guidance improves schema adherence.
3. Use the `instructor` library as a drop-in replacement for `with_structured_output` — reported as more reliable for Anthropic in community testing.

**Current safety:** The existing `assess_evidence()` already wraps in `try/except Exception` and returns an `INSUFFICIENT` fallback. This is the right behavior, but if intermittent failures increase from rare to frequent (as reported), the FAIR-RAG pipeline will always conclude INSUFFICIENT and always exhaust all 3 iterations without finding sufficient evidence, degrading answer quality.

**Confidence:** MEDIUM — community-verified issue, but severity depends on model version and schema complexity. Warrants a smoke test with `SEAResult` specifically against Claude.

---

### MEDIUM-3: Fiqh classifier uses raw `response.content.strip()` — Claude adds prefix text unlike OpenAI

**What goes wrong:**
`modules/fiqh/classifier.py` `classify_fiqh_query()`:
```python
response = model.invoke(_prompt.format_messages(query=query))
category = response.content.strip().upper()
if category not in VALID_CATEGORIES:
    return "OUT_OF_SCOPE_FIQH"
```

The prompt instructs: "Respond with ONLY the category name — no punctuation, no explanation, no quotes."

OpenAI models (`gpt-4o-mini`) reliably follow this instruction. Claude models frequently add preamble text even when instructed not to: "The category is: VALID_SMALL" or "Based on my analysis, VALID_LARGE". The `strip().upper()` check will not match these responses, causing every fiqh query to route as `OUT_OF_SCOPE_FIQH` and fall through to the regular hadith pipeline instead of the FAIR-RAG path.

**Similar risk:** `modules/classification/classifier.py` (legacy pipeline) uses the same pattern for `classify_fiqh_query()` and `classify_non_islamic_query()` — these check for `"true" in response.lower()`, which is more robust but still fragile if Claude returns "True" capitalized mid-sentence.

**Prevention:** For single-token classifications, use `with_structured_output` with a simple Pydantic model (`class Category(BaseModel): value: Literal[...]`) rather than raw content parsing. If staying with raw content parsing, use a contains-check instead of exact match:
```python
for cat in VALID_CATEGORIES:
    if cat in response.content.upper():
        return cat
return "OUT_OF_SCOPE_FIQH"
```

**Confidence:** HIGH — this is a well-documented behavioral difference between OpenAI and Claude models. Claude 3.x and Claude 4.x both exhibit this with strict instruction-following prompts.

---

### MEDIUM-4: `chain.stream()` (sync) inside async generator — behavior is preserved but blocks event loop

**What goes wrong:**
`core/pipeline_langgraph.py` uses `chain.stream()` (synchronous iterator) inside an `async def response_generator()` function. This pattern works today with OpenAI because `langchain-openai`'s `chain.stream()` releases the GIL during HTTP I/O. With `langchain-anthropic`, the same pattern is used — `ChatAnthropic` also implements `stream()` (sync) and `astream()` (async).

The issue is not a crash but a performance regression: `for chunk in chain.stream(...)` blocks the asyncio event loop for the duration of each network round-trip during the streaming response. Under concurrent users, this means one user's stream blocks other users from receiving SSE events.

**Confirmed behavior:** `langchain-anthropic` does implement proper async streaming via `astream()`. The current sync `chain.stream()` call works but degrades concurrent performance.

**How to fix:** Replace `for chunk in chain.stream({...}):` with:
```python
async for chunk in chain.astream({...}):
```
This is a non-breaking change (same chunk format — `AIMessageChunk` with `.content`), but requires the enclosing function to be `async def` (it already is). Both the fiqh path and the hadith/non-fiqh path in `pipeline_langgraph.py` use sync `chain.stream()` and should be converted.

**When it bites:** Only under concurrent load. Single-user testing will not surface this. If concurrent usage is expected, convert to `astream()` in the same phase as the LLM swap.

---

### MEDIUM-5: `init_chat_model` model name inference — Claude model names must match Anthropic's format exactly

**What goes wrong:**
`init_chat_model` infers the provider from the model name via `_attempt_infer_model_provider()`. For Anthropic, it checks if the model name starts with `"claude"`. If the model is specified as `"claude-sonnet-4-6"` (without version suffix like `-20250929`), `init_chat_model` infers `model_provider="anthropic"` correctly, but Anthropic's API may reject the model name if it is not a recognized alias.

Anthropic uses two naming formats: stable model aliases (e.g., `claude-sonnet-4-5`) and dated versions (e.g., `claude-sonnet-4-5-20250929`). The user's target model is `claude-sonnet-4-6` — verify this is a valid Anthropic API model name. If it is a hypothetical or internal name, the API returns a 404 or 400 at the first LLM call, not at startup.

**Prevention:** Set `LARGE_LLM` and `SMALL_LLM` env vars to verified Anthropic model names from the [Anthropic models docs](https://docs.anthropic.com/en/docs/about-claude/models) before deploying. Test with `ChatAnthropic(model=LARGE_LLM).invoke([HumanMessage(content="hi")])` in isolation before wiring into the full pipeline.

---

### MEDIUM-6: `get_translator_model()` uses `.bind(temperature=0)` — not valid for Claude via `init_chat_model`

**What goes wrong:**
`core/chat_models.py` `get_translator_model()`:
```python
base = init_chat_model(model=LARGE_LLM, openai_api_key=OPENAI_API_KEY)
return base.bind(temperature=0)
```

`ChatOpenAI.bind(temperature=0)` works because OpenAI models accept `temperature` as a call-time kwarg. `ChatAnthropic` also supports `.bind(temperature=...)` via LangChain's Runnable interface, so this should work after fixing the `openai_api_key` kwarg. However, Claude's valid temperature range is 0.0–1.0 (same as OpenAI), so `temperature=0` is valid.

The safer pattern is to pass temperature at construction:
```python
init_chat_model(model=LARGE_LLM, anthropic_api_key=..., temperature=0)
```

This is low severity but worth noting for clean migration.

---

### MEDIUM-7: `langchain-openai` is a hard dependency of no other installed package — safe to remove after dead code cleanup

**What goes wrong (if NOT properly verified):**
Before removing `langchain-openai` from `requirements.txt`, verify that no other installed package lists it as a dependency. Based on inspection of installed package metadata:
- `langchain-anthropic==0.3.22` depends on: `anthropic`, `langchain-core`, `pydantic` — does NOT require `openai` or `langchain-openai`.
- `langchain-community==0.3.27` depends on: `langchain-core`, `langchain`, `SQLAlchemy`, `requests`, etc. — does NOT require `langchain-openai`.
- `voyageai==0.3.7` depends on: `aiohttp`, `numpy`, `pydantic`, `requests`, `tenacity`, `tokenizers` — does NOT require `openai`.
- `langchain-pinecone==0.2.8` — does NOT require `langchain-openai` (confirmed by package metadata inspection).
- `langchain-huggingface==0.1.2` — does NOT require `openai`.
- `sentence-transformers==3.4.1` — does NOT require `openai`.

The `tiktoken` package (currently in `requirements.txt` as a standalone dep) IS a dependency of `langchain-openai`. If `tiktoken` is only present as a transitive dep of `langchain-openai`, it may also be removable. However, `tiktoken` is used by OpenAI tokenization internally and likely not needed after the OpenAI package is removed.

**Safe removal order:** (1) Remove global `OpenAI` client instances, (2) replace `openai` calls with Voyage AI calls, (3) remove `langchain-openai`, `openai`, `tiktoken` from `requirements.txt`.

**Confidence:** HIGH — verified by reading `METADATA` files of all installed packages.

---

### MEDIUM-8: Claude rate limits at Tier 1 are significantly lower than OpenAI Tier 1 — affects FAIR-RAG 3-iteration loop

**What goes wrong:**
Claude API Tier 1 limits (as of April 2026):
- **claude-sonnet-4-x**: 50 RPM, 40,000 ITPM (input tokens per minute)
- OpenAI GPT-4.1 Tier 1: 500 RPM, significantly higher TPM

The FAIR-RAG pipeline for a single fiqh query invokes the LLM approximately 5-8 times per request (fiqh classification + decomposition + up to 3 × [filter + SEA] + final generation). Under concurrent users, this rapidly exhausts the 50 RPM limit.

**When it bites:** Low-traffic testing (1-2 concurrent users) will not surface this. Any load test with 5+ concurrent users running fiqh queries will hit 429 rate limit errors. These surface inside LangGraph nodes as unhandled exceptions, setting `state["errors"]` and potentially terminating the FAIR-RAG loop early.

**Mitigation:**
1. Add exponential backoff retry logic to LLM calls (the `tenacity` library is already in `requirements.txt`).
2. Use Anthropic prompt caching for repeated system prompts — the FAIR-RAG pipeline uses the same system prompts across iterations; caching dramatically reduces effective ITPM consumption.
3. Apply for higher tier access before going to production.

**Confidence:** MEDIUM — rate limit numbers sourced from public Anthropic docs; exact behavior under concurrent load requires live testing.

---

## Minor

### MINOR-1: `get_classifier_model()` currently uses `LARGE_LLM` instead of `SMALL_LLM`

**What goes wrong:**
`core/chat_models.py`:
```python
def get_classifier_model():
    from core.config import LARGE_LLM
    chat_model = init_chat_model(model=LARGE_LLM, ...)
```

The v1.2 plan allocates `claude-haiku-4-5` (small) for SEA and classification to save cost. But `get_classifier_model()` currently uses `LARGE_LLM` (which will be `claude-sonnet-4-6`). This is an existing bug that the Claude migration exposes — previously `LARGE_LLM=gpt-4.1` and `SMALL_LLM=gpt-4o-mini` were both set, and the classifier inadvertently used the expensive model.

**Prevention:** Fix `get_classifier_model()` to use `SMALL_LLM`. This is a quick fix but must be done in the same phase as the model name updates to avoid a regression where `get_classifier_model()` tries to initialize `claude-haiku-4-5` using `LARGE_LLM`.

---

### MINOR-2: `EmbeddingService` docstring and module docstring say "OpenAI text-embedding-3-small" — misleading after migration

**What goes wrong:** Minor documentation debt. After migration, `services/embedding_service.py` and `db/models/embeddings.py` will have comments referencing `text-embedding-3-small` and 1536 dimensions. These are factually wrong post-migration and will confuse future developers.

**Prevention:** Update comments in the same PR as the embedding migration. Not blocking but catches tech debt at source.

---

### MINOR-3: `_parse_tool_payload()` in `_tool_node` handles string JSON parsing — Claude tool result format must stay JSON-serializable

**What goes wrong:**
`agents/core/chat_agent.py` `_parse_tool_payload()`:
```python
if isinstance(content, str):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw": content}
```

LangGraph's `ToolNode` serializes tool results as JSON strings before storing them in `ToolMessage.content`. With `langchain-anthropic`, `ToolMessage.content` may arrive as a list of content blocks (Anthropic's internal format) rather than a plain string in some edge cases. If `content` is a list, `isinstance(content, str)` is False and `isinstance(content, dict)` is also False — falling through to `return {}`.

This is a low-probability edge case with the current version of `langchain-anthropic==0.3.22`, which normalizes `ToolMessage` content to a string for the LangChain interface. But version upgrades to `langchain-anthropic` may change this.

**Prevention:** Add a list handling case:
```python
if isinstance(content, list):
    # Anthropic multi-block content — extract text blocks
    return {"raw": " ".join(b.get("text", "") for b in content if isinstance(b, dict))}
```

---

## Prevention Checklist

### Phase: LLM Swap (Claude for OpenAI)

| Pitfall | Prevention |
|---------|-----------|
| `openai_api_key` kwarg breaks `ChatAnthropic` init | Replace with `anthropic_api_key=os.getenv("CLAUDE_API_KEY")` in `chat_agent.py` and all 4 `chat_models.py` getters |
| `CLAUDE_API_KEY` not read by SDK default | Pass key explicitly; add startup guard in `core/config.py` replacing `OPENAI_API_KEY` check |
| `OPENAI_API_KEY` guard in `core/config.py` fires on startup | Replace guard with `CLAUDE_API_KEY` check before removing OpenAI from `.env` |
| Claude returns prefix text in classifier | Replace exact-match with contains-check or use `with_structured_output` for classification |
| Empty assistant messages in multi-turn tool loop | Filter `content==""` intermediate messages before passing to LLM in `_agent_node` |
| Model name not recognized by Anthropic API | Test model names against Anthropic docs; verify `claude-sonnet-4-6` is a real alias |
| `get_translator_model()` uses `.bind()` workaround | Pass `temperature=0` at construction instead of via `.bind()` |

### Phase: pgvector Dimension Migration

| Pitfall | Prevention |
|---------|-----------|
| `ALTER COLUMN TYPE` fails for vector — cannot cast dimensions | Use DROP + ADD COLUMN pattern; never attempt direct type cast |
| Existing rows destroyed by DROP COLUMN | Pre-generate Voyage AI 1024-dim embeddings into temp column; atomic swap |
| Stale embeddings mixed with new during cutover | Run migration during low-traffic window; verify `COUNT(*) WHERE embedding IS NULL = 0` |
| `EMBEDDING_DIMENSIONS` env var not updated | Change default in `core/config.py` to `"1024"`; update `db/models/embeddings.py` constant |

### Phase: Embedding Service Swap (Voyage AI)

| Pitfall | Prevention |
|---------|-----------|
| `EmbeddingService` still imports `OpenAI` client | Rewrite `generate_embedding()` and `generate_embeddings_batch()` to use `voyageai.Client` |
| `output_dimension` invalid value rejected by Voyage API | Pin `output_dimension=1024` in code, not from env var, during migration |
| No retry logic for Voyage AI rate limits | Add `tenacity` retry with exponential backoff to embedding calls |

### Phase: Package Cleanup (Remove openai)

| Pitfall | Prevention |
|---------|-----------|
| Global `client = OpenAI(...)` causes ImportError | Remove dead globals in `stream_generator.py` and `pipeline.py` first |
| `modules/classification/classifier.py` imports `OpenAI` | Clean up dead import; verify it is unused in the active pipeline |
| `langchain-openai` removal breaks no transitive deps | Confirmed safe — no other installed package requires it |
| `tiktoken` orphaned after `langchain-openai` removal | Verify no other code uses `tiktoken` directly; remove if unused |

### Phase: Structured Output (SEA)

| Pitfall | Prevention |
|---------|-----------|
| `with_structured_output(SEAResult)` intermittent failures | Add `Field(description=...)` to all `Finding` fields; add explicit fallback test; smoke test 10+ invocations |
| `with_structured_output` parse error not caught | `assess_evidence()` already has `try/except` fallback — verify it catches `ValidationError` not just `Exception` base class |

---

## Sources

- [LangGraph Issue #3168: Anthropic empty content message API error](https://github.com/langchain-ai/langgraph/issues/3168)
- [LangChain Issue #30158: Anthropic structured output reliability](https://github.com/langchain-ai/langchain/issues/30158)
- [LangChain Issue #34406: Empty AIMessage with astream and Anthropic tool calling](https://github.com/langchain-ai/langchain/issues/34406)
- [langchain-anthropic 0.3.22 METADATA — confirmed no openai dep](venv/lib/python3.11/site-packages/langchain_anthropic-0.3.22.dist-info/METADATA)
- [langchain-anthropic chat_models.py — API key field reads ANTHROPIC_API_KEY env var](venv/lib/python3.11/site-packages/langchain_anthropic/chat_models.py)
- [langchain/chat_models/base.py — init_chat_model passes kwargs directly to ChatAnthropic](venv/lib/python3.11/site-packages/langchain/chat_models/base.py)
- [voyageai 0.3.7 METADATA — confirmed no openai dep](venv/lib/python3.11/site-packages/voyageai-0.3.7.dist-info/METADATA)
- [pgvector issue #183 — cannot reuse fixed-dimension column for different size vectors](https://github.com/pgvector/pgvector/issues/183)
- [Voyage AI Embeddings docs — output_dimension valid values: 256, 512, 1024, 2048](https://docs.voyageai.com/docs/embeddings)
- [Anthropic Rate Limits docs — Tier 1 limits](https://platform.claude.com/docs/en/api/rate-limits)
- [LangChain ChatAnthropic API reference — anthropic_api_key field](https://python.langchain.com/api_reference/anthropic/chat_models/langchain_anthropic.chat_models.ChatAnthropic.html)
