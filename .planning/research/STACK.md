# Stack Research: v1.2 Claude + Voyage AI Migration

**Project:** Deen Backend v1.2 — Claude + Voyage AI Migration
**Researched:** 2026-04-09
**Scope:** Replace OpenAI LLM + embeddings with Anthropic Claude (LLM) + Voyage AI (embeddings)

---

## Packages to Add

### 1. `langchain-anthropic==0.3.22`

**Why:** Provides `ChatAnthropic`, the LangChain-native wrapper for Claude models. This is the drop-in replacement for `langchain-openai`'s `ChatOpenAI` within the existing LangChain/LangGraph stack.

**Compatibility with existing stack:** `langchain-anthropic 0.3.22` requires `langchain-core>=0.3.31,<0.4.0`. The installed `langchain-core==0.3.74` satisfies this range. No LangChain version upgrades required.

**Key capabilities confirmed:**
- `init_chat_model()` works with Anthropic. Pass `model_provider="anthropic"` or prefix the model string with `"anthropic:"`. The `anthropic_api_key` parameter replaces `openai_api_key`.
- `.bind_tools()` is supported. `ChatAnthropic.bind_tools()` accepts the same LangChain tool list format used in `ChatAgent._create_llm_with_tools()`. Tool calling uses Anthropic's `tool_use` content block protocol internally; LangChain abstracts this — the agent graph code is unchanged.
- `.stream()` and `.astream()` are supported. The existing `chain.stream()` call in `pipeline_langgraph.py` and `agent.astream()` in the LangGraph graph work without modification.

**Dependency pulled in:** `anthropic>=0.52.0,<1.0.0` (see below).

**Source:** [langchain-anthropic PyPI](https://pypi.org/project/langchain-anthropic/), [LangChain ChatAnthropic reference](https://python.langchain.com/api_reference/anthropic/chat_models/langchain_anthropic.chat_models.ChatAnthropic.html)

---

### 2. `anthropic==0.87.0`

**Why:** The official Anthropic Python SDK. `langchain-anthropic` declares `anthropic>=0.52.0,<1.0.0` as a dependency, so it will be pulled in transitively — but pin it explicitly in `requirements.txt` to control the version used in production and Docker builds.

`0.87.0` is the latest stable release (April 8, 2026). It is within `langchain-anthropic 0.3.22`'s declared range.

**Note:** The direct `from anthropic import Anthropic` import is not needed by this codebase — all LLM calls go through LangChain's abstraction layer. The SDK is a transitive dependency only. Pin it to prevent unexpected upgrades.

**Source:** [anthropic PyPI](https://pypi.org/project/anthropic/)

---

### 3. `voyageai==0.3.7`

**Why:** The official Voyage AI Python SDK. Used to replace the `openai.OpenAI` client in `EmbeddingService` for generating dense embeddings. There is no LangChain wrapper required — the `voyageai` SDK is used directly, just as `openai.OpenAI` was used directly.

`0.3.7` is the latest stable release (December 2025 / early 2026).

**Client initialization:**
```python
import voyageai
vo = voyageai.Client(api_key=VOYAGE_API_KEY)  # sync
# or
vo = voyageai.AsyncClient(api_key=VOYAGE_API_KEY)  # async
```

**Embed method — sync:**
```python
result = vo.embed(
    texts,                      # List[str]
    model="voyage-4",           # model name
    input_type="document",      # "document" | "query" | None
    output_dimension=1024,      # optional; 1024 is the default for voyage-4
)
embeddings = result.embeddings  # List[List[float]]
```

**Embed method — async:**
```python
result = await vo.aembed(
    texts,
    model="voyage-4",
    input_type="document",
)
embeddings = result.embeddings
```

**Source:** [voyageai PyPI](https://pypi.org/project/voyageai/), [Voyage AI embeddings docs](https://docs.voyageai.com/docs/embeddings), [voyageai-python GitHub](https://github.com/voyage-ai/voyageai-python)

---

## Packages to Remove

### 1. `langchain-openai==0.3.25` — REMOVE

**Why:** All LLM calls will use `langchain-anthropic`. `langchain-openai` provides `ChatOpenAI` and `OpenAIEmbeddings`. Neither is used after migration. Removing it eliminates the transitive `openai` SDK dependency and prevents any accidental fallback to OpenAI models.

**Risk if kept:** Dead code in `requirements.txt`; `openai` SDK still installed; bloat. No functional risk since nothing will call it, but keeping it muddies the intent.

---

### 2. `openai==1.91.0` — REMOVE

**Why:** The `openai` SDK is used in 3 places via `from openai import OpenAI`:
- `services/embedding_service.py` — `OpenAI(api_key=OPENAI_API_KEY)` for generating embeddings
- `modules/generation/stream_generator.py` — `OpenAI(api_key=OPENAI_API_KEY)` (legacy pipeline, kept for `POST /chat/` non-agentic path)
- `modules/classification/classifier.py` — `from openai import OpenAI` import (unused in actual code — `chat_models.get_classifier_model()` is used instead; dead import)

After migration, `embedding_service.py` uses `voyageai.Client` instead. `stream_generator.py` and `classifier.py` dead imports are cleaned up. With no remaining `openai` usage, remove the package.

**Dependency chain:** Removing `openai` also removes `tiktoken==0.9.0` if it is only depended on by `openai`. Check whether `tiktoken` is used elsewhere before removing it.

---

### 3. `tiktoken==0.9.0` — REMOVE (conditional)

**Why:** `tiktoken` is an OpenAI tokenizer library. It is listed in `requirements.txt` but is not referenced in any application code (`grep` shows no direct `import tiktoken` in the codebase). It appears to be a transitive dependency pulled in by `langchain-openai` or `openai`. Once those are removed, `tiktoken` can be removed too.

**Confirm before removing:** Run `grep -r "import tiktoken"` in the codebase to verify there are no direct uses.

---

## Compatibility Notes

### LangChain version: no upgrade needed

The existing `langchain==0.3.27` + `langchain-core==0.3.74` stack is fully compatible with `langchain-anthropic==0.3.22`. Both packages track the same `0.3.x` release series. No LangChain version bump required.

**Warning about LangChain 1.0:** LangChain 1.0 was released in November 2025 (currently at ~1.2.x). The 1.x ecosystem uses `langchain-anthropic 1.x` (latest 1.3.4), which requires `langchain-core 1.x`. Do NOT upgrade to `langchain-anthropic 1.x` — it would force a full LangChain stack upgrade and is out of scope for this milestone.

### `init_chat_model` provider switching

The current `core/chat_models.py` calls `init_chat_model(model=LARGE_LLM, openai_api_key=OPENAI_API_KEY)`. After migration:

```python
# Before
from langchain.chat_models import init_chat_model
from core.config import OPENAI_API_KEY, LARGE_LLM

chat_model = init_chat_model(
    model=LARGE_LLM,
    openai_api_key=OPENAI_API_KEY
)

# After
from langchain.chat_models import init_chat_model
from core.config import CLAUDE_API_KEY, LARGE_LLM

chat_model = init_chat_model(
    model=LARGE_LLM,           # e.g. "claude-sonnet-4-6"
    model_provider="anthropic",
    anthropic_api_key=CLAUDE_API_KEY
)
```

The `model_provider="anthropic"` parameter is required when the model string does not include the `"anthropic:"` prefix. Alternatively, set `LARGE_LLM="anthropic:claude-sonnet-4-6"` in the `.env` and the provider is inferred automatically.

### `.bind_tools()` in `ChatAgent`

`agents/core/chat_agent.py` calls `init_chat_model(...).bind_tools(self.tools)`. `ChatAnthropic.bind_tools()` accepts the same `@tool`-decorated LangChain tool list format. The tool-use protocol differs internally (Anthropic uses `tool_use` content blocks vs OpenAI's `function_calling`), but LangChain normalizes this — `ToolNode` and the LangGraph graph are unaffected. No changes to `agents/tools/` or `agents/core/chat_agent.py` beyond the `init_chat_model` call are required.

**Known issue to watch:** A GitHub issue (#34406) reported empty `AIMessage` when using `astream()` with Anthropic tool calling in certain edge cases. This is in a narrow code path (streaming + tool invocation in the same turn). Monitor for this; the fix is to use `.invoke()` in those specific paths if streaming tool-call chunks are empty.

### Voyage AI model and embedding dimensions

**voyage-4** default output dimensions: **1024**. This is a breaking change from `text-embedding-3-small` which uses 1536 dimensions.

This affects two SQLAlchemy models in `db/models/embeddings.py`:
```python
# Before
EMBEDDING_DIMENSIONS = 1536

# After
EMBEDDING_DIMENSIONS = 1024
```

Both `NoteEmbedding.embedding` (`Vector(1536)`) and `LessonChunkEmbedding.embedding` (`Vector(1536)`) pgvector columns must be resized to `Vector(1024)`. This requires an Alembic migration (ALTER COLUMN with `USING` cast). All existing embeddings in `note_embeddings` and `lesson_chunk_embeddings` tables will be incompatible and must be regenerated after migration.

**voyage-4 dimension options:** 256, 512, 1024 (default), 2048. Use 1024 (the default) — it provides the best balance between storage and retrieval quality without requiring `output_dimension` to be specified explicitly.

**voyage-4 context length:** 320K tokens (vs 8,191 for `text-embedding-3-small`). This means the existing chunking logic in `EmbeddingService` is more than adequate; no chunk size changes are needed.

### `input_type` parameter

When generating embeddings for stored documents (lesson chunks, notes): use `input_type="document"`.
When generating embeddings for query lookup: use `input_type="query"`.

The current `EmbeddingService.generate_embedding()` does not distinguish between document and query embeddings — it uses a single method for all purposes. After migration, the query path in similarity search should use `input_type="query"` for best retrieval performance. This is an optimization, not a correctness requirement.

### `OPENAI_API_KEY` guard in `core/config.py`

Line 44 of `core/config.py`:
```python
if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("Missing API keys! Ensure they are set in the .env file.")
```

This guard must be updated to check `CLAUDE_API_KEY` and `VOYAGE_API_KEY` instead. Otherwise the server will fail to start without `OPENAI_API_KEY` even after migration.

### Pinecone dense vectors (no change needed)

The Pinecone dense indexes (deen-fiqh-dense, deen-dense, quran-dense) use embeddings generated by `sentence-transformers/all-mpnet-base-v2` (768 dims) via `langchain-huggingface`, NOT by OpenAI `text-embedding-3-small`. The `embedder.py` in `modules/embedding/` uses `HuggingFaceEmbeddings` for Pinecone retrieval. This path is unaffected by the Voyage AI migration.

**Only the pgvector tables (`note_embeddings`, `lesson_chunk_embeddings`) use OpenAI embeddings.** These are the only tables requiring the embedding model swap and column resize.

---

## SDK Usage Examples

### LLM Initialization (replaces `core/chat_models.py`)

```python
from langchain.chat_models import init_chat_model
from core.config import CLAUDE_API_KEY, LARGE_LLM, SMALL_LLM

def get_generator_model():
    return init_chat_model(
        model=LARGE_LLM,           # "claude-sonnet-4-6"
        model_provider="anthropic",
        anthropic_api_key=CLAUDE_API_KEY,
    )

def get_enhancer_model():
    return init_chat_model(
        model=SMALL_LLM,           # "claude-haiku-4-5-20251001"
        model_provider="anthropic",
        anthropic_api_key=CLAUDE_API_KEY,
    )

def get_translator_model():
    base = init_chat_model(
        model=LARGE_LLM,
        model_provider="anthropic",
        anthropic_api_key=CLAUDE_API_KEY,
    )
    return base.bind(temperature=0)
```

### ChatAgent LLM with tools (replaces `agents/core/chat_agent.py` `_create_llm_with_tools`)

```python
from langchain.chat_models import init_chat_model
from core.config import CLAUDE_API_KEY

llm = init_chat_model(
    model=self.config.model.agent_model,  # "claude-sonnet-4-6"
    model_provider="anthropic",
    anthropic_api_key=CLAUDE_API_KEY,
    temperature=self.config.model.temperature,
    max_tokens=self.config.model.max_tokens,
)
return llm.bind_tools(self.tools)
```

### Embedding generation (replaces `services/embedding_service.py`)

```python
import voyageai
from core.config import VOYAGE_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS

class EmbeddingService:
    def __init__(self, db: Session):
        self.db = db
        self.client = voyageai.Client(api_key=VOYAGE_API_KEY)

    def generate_embedding(self, text: str) -> List[float]:
        result = self.client.embed(
            [text],
            model=EMBEDDING_MODEL,        # "voyage-4"
            input_type="document",
        )
        return result.embeddings[0]

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        result = self.client.embed(
            texts,
            model=EMBEDDING_MODEL,
            input_type="document",
        )
        return result.embeddings
```

### Environment variable additions to `core/config.py`

```python
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "voyage-4")       # was "text-embedding-3-small"
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))  # was 1536

if not CLAUDE_API_KEY or not VOYAGE_API_KEY or not PINECONE_API_KEY:
    raise ValueError("Missing API keys! Set CLAUDE_API_KEY, VOYAGE_API_KEY, PINECONE_API_KEY.")
```

---

## New `.env` Variables Required

| Variable | Example Value | Replaces |
|----------|---------------|---------|
| `CLAUDE_API_KEY` | `sk-ant-...` | `OPENAI_API_KEY` |
| `VOYAGE_API_KEY` | `pa-...` | (was embedded in OpenAI SDK usage) |
| `LARGE_LLM` | `claude-sonnet-4-6` | `gpt-4.1-2025-04-14` |
| `SMALL_LLM` | `claude-haiku-4-5-20251001` | `gpt-4o-mini-2024-07-18` |
| `EMBEDDING_MODEL` | `voyage-4` | `text-embedding-3-small` |
| `EMBEDDING_DIMENSIONS` | `1024` | `1536` |

**Remove from `.env`:** `OPENAI_API_KEY`

---

## Files Requiring Changes

| File | Change Required |
|------|----------------|
| `requirements.txt` | Add `langchain-anthropic==0.3.22`, `anthropic==0.87.0`, `voyageai==0.3.7`; remove `langchain-openai==0.3.25`, `openai==1.91.0`, `tiktoken==0.9.0` |
| `core/config.py` | Replace `OPENAI_API_KEY` with `CLAUDE_API_KEY` + `VOYAGE_API_KEY`; update startup guard; update `EMBEDDING_MODEL` default to `"voyage-4"` and `EMBEDDING_DIMENSIONS` default to `1024` |
| `core/chat_models.py` | Replace `openai_api_key=OPENAI_API_KEY` with `model_provider="anthropic", anthropic_api_key=CLAUDE_API_KEY` in all 4 model factory functions |
| `agents/core/chat_agent.py` | Replace `openai_api_key=OPENAI_API_KEY` with `model_provider="anthropic", anthropic_api_key=CLAUDE_API_KEY` in `_create_llm_with_tools()` |
| `services/embedding_service.py` | Replace `from openai import OpenAI` + `OpenAI(api_key=...)` with `import voyageai` + `voyageai.Client(api_key=VOYAGE_API_KEY)` |
| `modules/classification/classifier.py` | Remove dead `from openai import OpenAI` and `from core.config import OPENAI_API_KEY` imports |
| `modules/generation/stream_generator.py` | Remove `from openai import OpenAI` + `OpenAI(api_key=OPENAI_API_KEY)` globals (legacy pipeline; assess whether this module still needs updating) |
| `modules/generation/generator.py` | Remove `from core.config import OPENAI_API_KEY` dead import |
| `modules/enhancement/enhancer.py` | Remove `from core.config import OPENAI_API_KEY` dead import |
| `db/models/embeddings.py` | Change `EMBEDDING_DIMENSIONS = 1536` to `EMBEDDING_DIMENSIONS = 1024` |
| `alembic/versions/` | New migration: resize `note_embeddings.embedding` and `lesson_chunk_embeddings.embedding` from `vector(1536)` to `vector(1024)` |

---

## What Does NOT Change

| Component | Reason |
|-----------|--------|
| `langchain-huggingface==0.1.2` | Pinecone dense embedding uses `HuggingFaceEmbeddings` (all-mpnet-base-v2, 768 dims) — unaffected |
| `langchain-pinecone==0.2.8` | Pinecone vector store integration unchanged |
| `langchain==0.3.27` | No version change needed; compatible with `langchain-anthropic 0.3.x` |
| `langchain-core==0.3.74` | Within the `>=0.3.31,<0.4.0` range required by `langchain-anthropic 0.3.22` |
| `langgraph==0.2.64` | LangGraph graph structure, nodes, tools, routing — unchanged |
| `sentence-transformers==3.4.1` | Used for Pinecone sparse/dense embeddings — unaffected |
| `torch==2.6.0` | Required by sentence-transformers — unaffected |
| `pgvector==0.3.6` | SQLAlchemy pgvector extension — unchanged, only column dimension changes |
| Redis, Pinecone, PostgreSQL, Alembic | Infrastructure unchanged |
| All API endpoints and SSE protocol | Zero behavioral changes from the frontend's perspective |

---

## Sources

- [langchain-anthropic PyPI](https://pypi.org/project/langchain-anthropic/) — version 0.3.22 exists; dependency range `langchain-core>=0.3.31,<0.4.0` (MEDIUM confidence — search result excerpt, not direct page read)
- [LangChain ChatAnthropic reference](https://python.langchain.com/api_reference/anthropic/chat_models/langchain_anthropic.chat_models.ChatAnthropic.html) — `bind_tools()` documented; streaming via Runnable interface (HIGH confidence — official docs)
- [LangChain init_chat_model reference](https://reference.langchain.com/python/langchain/chat_models/base/init_chat_model) — `model_provider="anthropic"` parameter (HIGH confidence — official docs)
- [anthropic PyPI](https://pypi.org/project/anthropic/) — latest version 0.87.0, April 2026 (MEDIUM confidence — search result)
- [voyageai PyPI](https://pypi.org/project/voyageai/) — version 0.3.7 (MEDIUM confidence — search result)
- [Voyage AI embeddings docs](https://docs.voyageai.com/docs/embeddings) — `vo.embed(texts, model, input_type)` method signature; `result.embeddings` accessor (HIGH confidence — official docs)
- [Voyage AI blog: voyage-4 family](https://blog.voyageai.com/2026/01/15/voyage-4/) — voyage-4 default 1024 dims, 320K token context (HIGH confidence — official blog)
- [Voyage AI flexible dimensions](https://docs.voyageai.com/docs/flexible-dimensions-and-quantization) — supported dimension values: 256, 512, 1024, 2048 (HIGH confidence — official docs)
- [voyageai-python GitHub](https://github.com/voyage-ai/voyageai-python) — `AsyncClient.aembed()` method available (MEDIUM confidence — GitHub repo)
- [langchain-ai/langchain #34406](https://github.com/langchain-ai/langchain/issues/34406) — empty AIMessage with astream + Anthropic tool calling edge case (MEDIUM confidence — GitHub issue)
- Codebase read: `services/embedding_service.py`, `core/chat_models.py`, `agents/core/chat_agent.py`, `db/models/embeddings.py`, `core/config.py`, `modules/generation/generator.py`, `modules/classification/classifier.py` — confirmed all OpenAI import sites and embedding dimension usage (HIGH confidence — direct source read)
