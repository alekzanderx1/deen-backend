# Architecture Research: Claude + Voyage AI Migration

**Project:** Deen Backend v1.2 — Claude + Voyage AI Migration
**Researched:** 2026-04-09
**Confidence:** HIGH (all claims verified against source code, official LangChain docs, Voyage AI docs, pgvector docs)

---

## Context

This is a targeted replacement migration, not a redesign. The existing FastAPI + LangGraph + Pinecone + Redis architecture is unchanged. Every decision below is scoped to the minimum diff that moves LLM calls from OpenAI to Anthropic Claude and embedding calls from OpenAI to Voyage AI.

---

## Modified Files

### 1. `core/config.py`

**What changes:**
- Remove `OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")`
- Remove the inline `if not OPENAI_API_KEY` raise guard (line 44-45)
- Add `ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")` — reason: the Anthropic SDK, `langchain-anthropic`, and `init_chat_model(model_provider="anthropic")` all read `ANTHROPIC_API_KEY` from the environment automatically. Using `ANTHROPIC_API_KEY` (the canonical name) means zero explicit key-passing is needed in `init_chat_model` calls — the library picks it up natively. The user's `.env` currently has `CLAUDE_API_KEY`; that name must be renamed to `ANTHROPIC_API_KEY` in `.env` and `.env.example`.
- Add `VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")` — `voyageai.Client` and `langchain-voyageai`'s `VoyageAIEmbeddings` both auto-read `VOYAGE_API_KEY` from the environment.
- Update `EMBEDDING_MODEL` default: `"text-embedding-3-small"` -> `"voyage-4"`
- Update `EMBEDDING_DIMENSIONS` default: `"1536"` -> `"1024"` (voyage-4 default dimension is 1024; this is also the dimension recorded in the new Alembic migration)
- Add startup guard for `ANTHROPIC_API_KEY` in the existing inline validation block or alongside `validate_supabase_config()`.

**API key naming decision — ANTHROPIC_API_KEY, not CLAUDE_API_KEY:**
The Anthropic Python SDK (used by `langchain-anthropic` and directly by `init_chat_model`) unconditionally reads `os.environ["ANTHROPIC_API_KEY"]`. Using any other name (e.g., `CLAUDE_API_KEY`) requires passing `anthropic_api_key=value` explicitly at every call site and breaks auto-inference. The `generate_hikmah_tree.py` script already uses `ANTHROPIC_API_KEY` and passes it as `anthropic_api_key=anthropic_key` — that usage pattern becomes unnecessary once the env var is correctly named `ANTHROPIC_API_KEY`. Use the canonical name.

---

### 2. `core/chat_models.py`

**What changes:**
- Remove `from core.config import OPENAI_API_KEY`
- Add `from langchain_anthropic import ChatAnthropic` — use `ChatAnthropic` directly, not `init_chat_model`

**Why `ChatAnthropic` directly, not `init_chat_model`:**
`init_chat_model` with `model_provider="anthropic"` works and is valid, but it performs a runtime dispatch that requires `langchain-anthropic` to be installed and adds a layer of indirection. Since this codebase is permanently switching to Claude (not dynamically dispatching between providers), using `ChatAnthropic(model=...)` directly is cleaner, more explicit, and avoids the `openai_api_key` parameter footgun entirely. It also makes the provider dependency visible at import time rather than at first call. The `generate_hikmah_tree.py` script already uses `init_chat_model(model=model_id, anthropic_api_key=anthropic_key)` — that works too, but direct instantiation is preferred for the application path.

**Concrete change for each factory function:**

```python
# BEFORE
from core.config import OPENAI_API_KEY
from langchain.chat_models import init_chat_model

def get_generator_model():
    from core.config import LARGE_LLM
    return init_chat_model(model=LARGE_LLM, openai_api_key=OPENAI_API_KEY)

def get_enhancer_model():
    from core.config import SMALL_LLM
    return init_chat_model(model=SMALL_LLM, openai_api_key=OPENAI_API_KEY)

def get_classifier_model():
    from core.config import LARGE_LLM
    return init_chat_model(model=LARGE_LLM, openai_api_key=OPENAI_API_KEY)

def get_translator_model():
    from core.config import LARGE_LLM
    base = init_chat_model(model=LARGE_LLM, openai_api_key=OPENAI_API_KEY)
    return base.bind(temperature=0)

# AFTER
from langchain_anthropic import ChatAnthropic
from core.config import LARGE_LLM, SMALL_LLM

def get_generator_model() -> ChatAnthropic:
    return ChatAnthropic(model=LARGE_LLM)

def get_enhancer_model() -> ChatAnthropic:
    return ChatAnthropic(model=SMALL_LLM)

def get_classifier_model() -> ChatAnthropic:
    return ChatAnthropic(model=SMALL_LLM)

def get_translator_model() -> ChatAnthropic:
    return ChatAnthropic(model=LARGE_LLM, temperature=0)
```

`ChatAnthropic` reads `ANTHROPIC_API_KEY` automatically from the environment; no explicit key passing needed.

**Note on `get_classifier_model`:** Currently it uses `LARGE_LLM` (gpt-4.1). With Claude, `SMALL_LLM` (claude-haiku-4-5) is appropriate for classification — cheaper, fast, sufficient for binary classification. The factory function name stays the same; only the model constant changes.

---

### 3. `agents/core/chat_agent.py`

**What changes:**
- Remove `from core.config import OPENAI_API_KEY` (line 33)
- Change `_create_llm_with_tools`:

```python
# BEFORE
from langchain.chat_models import init_chat_model
llm = init_chat_model(
    model=self.config.model.agent_model,
    openai_api_key=OPENAI_API_KEY,
    temperature=self.config.model.temperature,
    max_tokens=self.config.model.max_tokens,
)

# AFTER
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(
    model=self.config.model.agent_model,
    temperature=self.config.model.temperature,
    max_tokens=self.config.model.max_tokens,
)
```

---

### 4. `agents/config/agent_config.py`

**What changes:**
- `ModelConfig.agent_model` default fallback: `LARGE_LLM or "gpt-4o"` -> `LARGE_LLM or "claude-sonnet-4-6"`
- Same in `json_schema_extra` example.
- `ModelConfig.temperature` validator: change `le=2.0` to `le=1.0` — Claude's valid temperature range is 0-1; values above 1.0 will error on the Anthropic API.

This is a guard string used only when `LARGE_LLM` env var is not set. The actual model is always controlled by the env var in practice.

---

### 5. `services/embedding_service.py`

**What changes:**
- Remove `from openai import OpenAI`
- Remove `from core.config import OPENAI_API_KEY` (keep `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `NOTE_FILTER_THRESHOLD`)
- Add `import voyageai`
- Change `__init__`:

```python
# BEFORE
self.client = OpenAI(api_key=OPENAI_API_KEY)

# AFTER
self.client = voyageai.Client()  # reads VOYAGE_API_KEY from env automatically
```

- Change `generate_embedding`:

```python
# BEFORE
response = self.client.embeddings.create(
    model=EMBEDDING_MODEL, input=text, dimensions=EMBEDDING_DIMENSIONS
)
return response.data[0].embedding

# AFTER
result = self.client.embed([text], model=EMBEDDING_MODEL)
return result.embeddings[0]
```

- Change `generate_embeddings_batch`:

```python
# BEFORE
response = self.client.embeddings.create(
    model=EMBEDDING_MODEL, input=texts, dimensions=EMBEDDING_DIMENSIONS
)
return [item.embedding for item in response.data]

# AFTER
result = self.client.embed(texts, model=EMBEDDING_MODEL)
return result.embeddings
```

**Why `voyageai.Client` (native SDK), not `langchain-voyageai`:**
`EmbeddingService` is not a LangChain component — it is a plain Python service that calls the embedding API and stores vectors in pgvector. The native `voyageai.Client` gives direct control over batching, output dimensions, and error handling without a LangChain wrapper layer. `langchain-voyageai`'s `VoyageAIEmbeddings` is appropriate when plugging into a LangChain `PineconeVectorStore` or chain, which is not what this service does. The native SDK is the simpler and more correct choice here.

**Voyage AI model selection:**
Use `voyage-4` (not `voyage-4-large`). Rationale: `voyage-4` is the production general-purpose model with 1024-dim default output, appropriate for user notes and lesson chunks. `voyage-4-large` is intended for maximum accuracy scenarios with higher cost. For pgvector semantic similarity over user memory notes and lesson content, `voyage-4` quality is sufficient and cost-proportionate.

**Output dimensions:**
`voyage-4` default dimension is 1024. The `output_dimension` parameter does not need to be passed explicitly if 1024 is acceptable (it is the default). For explicitness and alignment with `EMBEDDING_DIMENSIONS=1024` in config, passing it is fine but not required.

**Voyage AI batch size limit:** `voyageai.Client.embed()` has a max of 128 texts per call. The existing `generate_embeddings_batch` sends all texts in a single call. For lesson chunk embedding (typically small), this is fine in practice. If batches ever exceed 128, the implementation must chunk input into groups of 128.

---

### 6. `db/models/embeddings.py`

**What changes:**
- Change module-level constant: `EMBEDDING_DIMENSIONS = 1536` -> `EMBEDDING_DIMENSIONS = 1024`
- Update docstring comment from "OpenAI text-embedding-3-small" to "Voyage AI voyage-4"
- The `Vector(EMBEDDING_DIMENSIONS)` column definitions on `NoteEmbedding.embedding` and `LessonChunkEmbedding.embedding` update automatically from the constant.

No structural change to the ORM model — the `Vector(n)` type is the only thing that changes.

---

### 7. `modules/generation/stream_generator.py` — Dead code cleanup

- Remove `from openai import OpenAI` (line 2)
- Remove `from core.config import OPENAI_API_KEY` (line 3)
- Remove `client = OpenAI(api_key=OPENAI_API_KEY)` (line 13, module-level instantiation)
- These are unused — the module already delegates to `core.chat_models` for actual LLM calls.

---

### 8. `modules/classification/classifier.py` — Dead code cleanup

- Remove `from openai import OpenAI` (line 1)
- Remove `from core.config import OPENAI_API_KEY` (line 6)
- The `OpenAI` import is never used; the module uses `chat_models.get_classifier_model()`.

---

### 9. `scripts/hikmah_generation/generate_hikmah_tree.py`

**What changes:**
- Remove the `else` branch that initializes the OpenAI path (`init_chat_model(model=LARGE_LLM, openai_api_key=OPENAI_API_KEY)`)
- Remove `from core.config import OPENAI_API_KEY` import in that branch
- The existing anthropic branch (`init_chat_model(model=model_id, anthropic_api_key=anthropic_key)`) can remain as-is, or be simplified to `ChatAnthropic(model=model_id)` once `ANTHROPIC_API_KEY` is the env var name (eliminating the explicit key lookup)
- The `model_choice` CLI flag stays, but only Claude model IDs are valid

---

### 10. `.env.example`

**What changes:**
- Replace `OPENAI_API_KEY=your-openai-api-key-here` with `ANTHROPIC_API_KEY=your-anthropic-api-key-here`
- Add `VOYAGE_API_KEY=your-voyage-api-key-here`
- Update `LARGE_LLM=gpt-4.1-2025-04-14` -> `LARGE_LLM=claude-sonnet-4-6`
- Update `SMALL_LLM=gpt-4o-mini-2024-07-18` -> `SMALL_LLM=claude-haiku-4-5`
- Update `EMBEDDING_MODEL=text-embedding-3-small` -> `EMBEDDING_MODEL=voyage-4`
- Update `EMBEDDING_DIMENSIONS=1536` -> `EMBEDDING_DIMENSIONS=1024`

---

## New Files

### Alembic Migration: `alembic/versions/20260409_resize_embedding_dimensions.py`

This is a new migration file, not a modification to the existing `20260122_create_embedding_tables.py`. The existing migration must stay unchanged to preserve the chain.

---

## Data Flow Changes

### LLM Call Path (before vs after)

```
BEFORE:
ChatRequest -> core/pipeline_langgraph.py -> agents/core/chat_agent.py
    -> init_chat_model(model, openai_api_key=OPENAI_API_KEY)
    -> langchain-openai -> openai SDK -> OpenAI API

AFTER:
ChatRequest -> core/pipeline_langgraph.py -> agents/core/chat_agent.py
    -> ChatAnthropic(model, ...)
    -> langchain-anthropic -> anthropic SDK -> Anthropic API
```

The LangGraph graph structure, tool definitions, state machine, and SSE streaming path are all unchanged. `ChatAnthropic` implements the same `BaseChatModel` interface as the OpenAI model, so `.bind_tools()`, `.invoke()`, `.stream()`, and `.astream()` all work identically.

### Embedding Call Path (before vs after)

```
BEFORE:
services/embedding_service.py -> openai.OpenAI(api_key=...).embeddings.create(
    model="text-embedding-3-small", input=text, dimensions=1536
) -> 1536-dim vector -> pgvector Vector(1536) column

AFTER:
services/embedding_service.py -> voyageai.Client().embed(
    [text], model="voyage-4"
) -> 1024-dim vector -> pgvector Vector(1024) column
```

The pgvector similarity queries (`<=>` cosine distance operator) in `find_similar_notes_to_lesson` are unaffected by the dimension change — the SQL expression is dynamically built from stored embedding values, and the operator works for any fixed dimension.

### What Does NOT Change

- Pinecone retrieval for hadith/Quran/fiqh corpora — those vectors use HuggingFace `all-mpnet-base-v2` (768-dim) for dense and BM25 for sparse. Neither is affected.
- `modules/embedding/embedder.py` — uses `sentence-transformers`, not OpenAI. Not affected.
- BM25 sparse retrieval (`modules/fiqh/retriever.py`) — uses `pinecone-text` BM25Encoder from a pre-trained vocabulary file. Not affected.
- Redis conversation memory — not affected.
- SSE streaming protocol — not affected.
- Supabase Auth JWT validation — not affected.
- LangGraph graph topology — not affected.

---

## Alembic Strategy

### The Problem

The `note_embeddings` and `lesson_chunk_embeddings` tables were created in `20260122_create_embedding_tables.py` with `Vector(1536)`. They also have HNSW indexes built on those columns. Changing the vector dimension requires:

1. Dropping the HNSW indexes (indexes are dimension-specific in pgvector; they cannot be reused after a type change)
2. `ALTER COLUMN embedding TYPE vector(1024)` on both tables
3. Recreating the HNSW indexes

### ALTER vs Drop/Recreate Table

`ALTER TABLE ... ALTER COLUMN embedding TYPE vector(1024)` works in pgvector — it is not a "drop and recreate the table" operation. The column is retyped in place. However, pgvector requires that the HNSW index be dropped first because it is tied to the specific dimension.

**Critical:** All existing 1536-dim float arrays in the column would be reinterpreted after the ALTER, producing corrupt vectors. The migration must therefore also TRUNCATE both tables before the ALTER. Since the embedding tables are a regenerable cache (they are rebuilt from source data by calling the embedding service), truncating them is safe. The first run after migration will regenerate embeddings via `voyage-4` at 1024 dims.

### Migration Sequence

```
1. DROP INDEX IF EXISTS idx_note_embeddings_vector
2. DROP INDEX IF EXISTS idx_lesson_chunk_embeddings_vector
3. TRUNCATE TABLE note_embeddings
4. TRUNCATE TABLE lesson_chunk_embeddings
5. ALTER TABLE note_embeddings ALTER COLUMN embedding TYPE vector(1024) USING embedding::text::vector(1024)
6. ALTER TABLE lesson_chunk_embeddings ALTER COLUMN embedding TYPE vector(1024) USING embedding::text::vector(1024)
7. CREATE INDEX idx_note_embeddings_vector ON note_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
8. CREATE INDEX idx_lesson_chunk_embeddings_vector ON lesson_chunk_embeddings USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
```

**Note on `USING` clause:** The `ALTER COLUMN TYPE` requires a USING clause to cast existing data. The cast `embedding::text::vector(1024)` is the standard pgvector approach for in-place ALTER. Since we TRUNCATE first, there are no rows to cast — but the USING clause is still required syntactically by Postgres for type changes on vector columns. It executes on zero rows.

**Migration file template:**

```python
"""Resize embedding vector columns 1536 -> 1024 dims for Voyage AI

Revision ID: embeddings_002
Revises: embeddings_001
Create Date: 2026-04-09
"""
from alembic import op
from pgvector.sqlalchemy import Vector

revision = 'embeddings_002'
down_revision = 'embeddings_001'
branch_labels = None
depends_on = None


def upgrade():
    # Drop HNSW indexes first (dimension-specific, must precede ALTER)
    op.execute('DROP INDEX IF EXISTS idx_note_embeddings_vector')
    op.execute('DROP INDEX IF EXISTS idx_lesson_chunk_embeddings_vector')

    # Truncate: existing 1536-dim vectors are incompatible with 1024-dim type.
    # These tables are a regenerable cache; truncation is safe.
    op.execute('TRUNCATE TABLE note_embeddings')
    op.execute('TRUNCATE TABLE lesson_chunk_embeddings')

    # Resize columns
    op.alter_column(
        'note_embeddings', 'embedding',
        type_=Vector(1024),
        postgresql_using='embedding::text::vector(1024)'
    )
    op.alter_column(
        'lesson_chunk_embeddings', 'embedding',
        type_=Vector(1024),
        postgresql_using='embedding::text::vector(1024)'
    )

    # Recreate HNSW indexes with same parameters as original migration
    op.execute("""
        CREATE INDEX idx_note_embeddings_vector
        ON note_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute("""
        CREATE INDEX idx_lesson_chunk_embeddings_vector
        ON lesson_chunk_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade():
    op.execute('DROP INDEX IF EXISTS idx_note_embeddings_vector')
    op.execute('DROP INDEX IF EXISTS idx_lesson_chunk_embeddings_vector')
    op.execute('TRUNCATE TABLE note_embeddings')
    op.execute('TRUNCATE TABLE lesson_chunk_embeddings')
    op.alter_column(
        'note_embeddings', 'embedding',
        type_=Vector(1536),
        postgresql_using='embedding::text::vector(1536)'
    )
    op.alter_column(
        'lesson_chunk_embeddings', 'embedding',
        type_=Vector(1536),
        postgresql_using='embedding::text::vector(1536)'
    )
    op.execute("""
        CREATE INDEX idx_note_embeddings_vector
        ON note_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute("""
        CREATE INDEX idx_lesson_chunk_embeddings_vector
        ON lesson_chunk_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
```

---

## Dependency Changes

### Add

```
langchain-anthropic>=0.3.0    # ChatAnthropic; reads ANTHROPIC_API_KEY from env
voyageai>=0.3.0               # voyageai.Client; reads VOYAGE_API_KEY from env
```

### Remove

```
openai==1.91.0                # No longer used in application code
langchain-openai==0.3.25      # No longer used in application code
```

**Why `langchain-openai` can be fully removed:**
- `init_chat_model` in `chat_models.py` and `chat_agent.py` is replaced by `ChatAnthropic`
- `EmbeddingService` switches to `voyageai.Client`
- The BM25 sparse encoder (`pinecone-text`) does NOT depend on `langchain-openai` — it uses a pre-trained vocabulary file and `pinecone-text` library
- `langchain-openai` is currently only in the application dependency graph because of the `init_chat_model` + `openai_api_key` calls. Once those are gone, no application code imports from `langchain_openai`

**Tests that need updating:**
- `tests/test_embedding_service.py` — mocks `services.embedding_service.OpenAI`. Must be updated to mock `voyageai.Client` and the new response shape (`result.embeddings` not `result.data[0].embedding`).
- `tests/test_agentic_streaming_sse.py` — integration test that mentions `OPENAI_API_KEY` in docstring. Update docstring to `ANTHROPIC_API_KEY`.

**Keep:**
- `pinecone-text` — BM25 encoder for fiqh sparse retrieval (runtime, not just ingestion)
- `langchain-huggingface` + `sentence-transformers` — Pinecone dense embedder for hadith/Quran/fiqh, unaffected
- `langchain-pinecone` — PineconeVectorStore integration, unaffected
- `langchain` (core) — graph orchestration, prompts, runnables

---

## Build Order

Dependency graph:

```
env vars (ANTHROPIC_API_KEY, VOYAGE_API_KEY rename in .env)
    |
    v
core/config.py + requirements.txt          [Phase 1 — unblocks everything]
    |
    v
core/chat_models.py                        [Phase 2 — LLM swap]
agents/core/chat_agent.py                  [Phase 2 — LLM swap]
agents/config/agent_config.py              [Phase 2 — fallback string + temperature bound]
    |
    v
services/embedding_service.py              [Phase 3 — embedding swap]
db/models/embeddings.py                    [Phase 3 — ORM dim constant]
Alembic migration (embeddings_002)         [Phase 3 — DB schema, run before server starts]
    |
    v
Dead code cleanup                          [Phase 4 — no functional impact]
modules/generation/stream_generator.py
modules/classification/classifier.py
scripts/hikmah_generation/generate_hikmah_tree.py
.env.example + test updates                [Phase 4 — documentation + tests]
```

### Rationale

1. **Config first** — every other file imports from `core/config.py`. Until `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` are present in config (and in `.env`), no model code can be tested. The inline guard (raise if missing) must swap from `OPENAI_API_KEY` to `ANTHROPIC_API_KEY` here too, otherwise server startup fails even after keys are correct.

2. **LLM swap before embedding swap** — chat models affect the primary request path (`/chat/stream/agentic`). Isolating this change and validating it end-to-end before touching the embedding subsystem keeps scope narrow and rollback clean.

3. **Embedding swap + DB migration together** — `EmbeddingService` and `db/models/embeddings.py` must change simultaneously with the Alembic migration. If the ORM model says `Vector(1024)` but the DB still has `Vector(1536)` columns, every embedding write will fail. Run `alembic upgrade head` before starting the server after Phase 3.

4. **Dead code cleanup last** — the three dead-import files have zero functional impact on the OpenAI to Claude switch. Cleaning them up after the functional changes are validated keeps each phase's diff focused and rollback straightforward.

### Phase Summary

| Phase | Files | Gate |
|-------|-------|------|
| 1: Config + Deps | `core/config.py`, `requirements.txt`, `.env`, `.env.example` | `import core.config` succeeds; `pip install` clean |
| 2: LLM Swap | `core/chat_models.py`, `agents/core/chat_agent.py`, `agents/config/agent_config.py` | `POST /chat/agentic` returns a Claude response; streaming SSE events flow correctly |
| 3: Embedding + DB | `services/embedding_service.py`, `db/models/embeddings.py`, new Alembic migration | `alembic upgrade head` clean; embedding write/read round-trip passes |
| 4: Cleanup + Tests | Dead imports, `generate_hikmah_tree.py`, `.env.example`, test mocks | `pytest tests -q` green |

---

## Integration Points Summary

| Integration Point | Before | After | Risk |
|-------------------|--------|-------|------|
| `core/chat_models.py` 4 factory functions | `init_chat_model(..., openai_api_key=)` | `ChatAnthropic(model=...)` | LOW — same BaseChatModel interface |
| `agents/core/chat_agent.py` `_create_llm_with_tools` | `init_chat_model(..., openai_api_key=)` | `ChatAnthropic(model=..., temperature=..., max_tokens=...)` | LOW — `.bind_tools()` works identically |
| `services/embedding_service.py` `generate_embedding` | `openai.Client.embeddings.create(...)` | `voyageai.Client().embed([text], model=...)` | MEDIUM — response shape differs; index into `.embeddings[0]` not `.data[0].embedding` |
| `db/models/embeddings.py` `Vector(1536)` | 1536 dims | 1024 dims | MEDIUM — requires Alembic migration before first write |
| `core/config.py` API key guard | `OPENAI_API_KEY` raise | `ANTHROPIC_API_KEY` raise | LOW — same guard pattern |
| `agents/config/agent_config.py` fallback + temperature bound | `"gpt-4o"`, `le=2.0` | `"claude-sonnet-4-6"`, `le=1.0` | LOW — guard only; temperature bound is a correctness fix |
| Dead imports (3 files) | Module-level `OpenAI()` client | Remove | LOW — currently unused |

---

## Open Questions / Flags for Phase Research

1. **Claude tool-calling streaming events:** Claude's streaming tool-call event format differs from OpenAI's. The SSE event extraction in `core/pipeline_langgraph.py` reads `response_chunk` and `response_end` events from LangGraph's `astream()` output. LangGraph abstracts this difference, but the actual token chunking in `chain.stream()` (which is called directly in the generate_response node) may emit differently shaped events. Smoke-test the full streaming SSE path after Phase 2 before proceeding to Phase 3.

2. **`max_tokens` required by Claude:** Claude requires `max_tokens` to be set explicitly — there is no server-side default, unlike OpenAI. `ModelConfig.max_tokens` is currently `Optional[int]` defaulting to `None`. With `ChatAnthropic`, passing `None` will likely raise a validation error. A sensible default (e.g., 4096) should be added to `ModelConfig` in Phase 2. Check the Anthropic API docs for the maximum allowed value per model.

3. **`get_translator_model` uses `.bind(temperature=0)`:** The existing code does `base.bind(temperature=0)` after `init_chat_model`. `ChatAnthropic` supports `.bind()` — but the recommended pattern is to pass `temperature=0` directly to the constructor, which is what the After example shows. Verify that `.bind()` is not needed.

4. **`modules/fiqh/` LLM calls:** The fiqh module (`modules/fiqh/classifier.py`, `modules/fiqh/generator.py`, etc.) imports from `core.chat_models` via the factory functions. Because those factory functions are being replaced, fiqh module behavior automatically follows. No direct changes needed in `modules/fiqh/` — but the fiqh pipeline should be included in Phase 2 smoke testing.

---

## Sources

- [LangChain ChatAnthropic integration](https://docs.langchain.com/oss/python/integrations/chat/anthropic) — HIGH confidence
- [langchain-anthropic on PyPI](https://pypi.org/project/langchain-anthropic/) — HIGH confidence
- [Voyage AI Embeddings API docs](https://docs.voyageai.com/docs/embeddings) — HIGH confidence (voyage-4 default dim = 1024 verified directly)
- [voyageai Python SDK on GitHub](https://github.com/voyage-ai/voyageai-python) — HIGH confidence
- [langchain-voyageai on PyPI](https://pypi.org/project/langchain-voyageai/) — MEDIUM confidence (langchain wrapper; confirmed not used for EmbeddingService)
- [pgvector ALTER COLUMN discussion](https://github.com/pgvector/pgvector/issues/183) — MEDIUM confidence (community-confirmed; standard Postgres ALTER TABLE behavior)
- Source code: all file-level claims verified against repo files read above
