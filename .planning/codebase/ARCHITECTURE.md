# Architecture
_Last updated: 2026-03-22_

## Summary

Deen Backend is a FastAPI application implementing a layered, pipeline-driven architecture for an AI-powered Islamic education platform. The primary chat flow routes HTTP requests through thin API handlers into a LangGraph agentic pipeline (`core/pipeline_langgraph.py`), which orchestrates an LLM agent that autonomously selects retrieval tools (Pinecone vector search) and generates responses streamed back as Server-Sent Events. A legacy synchronous pipeline (`core/pipeline.py`) coexists for non-agentic endpoints.

---

## High-Level Pattern

**Layered architecture with an agentic AI core.**

```
HTTP Client
    ↓
FastAPI (main.py)          ← CORS, auth middleware, router registration
    ↓
api/                       ← Thin route handlers, input validation, auth extraction
    ↓
core/pipeline_langgraph.py ← Active agentic pipeline (primary)
core/pipeline.py           ← Legacy pipeline (still used by /chat/ and /references)
    ↓
agents/core/chat_agent.py  ← LangGraph graph: fiqh_classification → agent ↔ tools → generate_response
    ↓
agents/tools/              ← LangGraph @tool wrappers around modules/
    ↓
modules/                   ← Discrete AI pipeline stages (classification, embedding, retrieval, etc.)
    ↓
services/                  ← Business logic: chat persistence, memory, primers
    ↓
db/                        ← SQLAlchemy models, repositories, routers (PostgreSQL)
core/memory.py             ← Redis-backed conversation history (LangChain RedisChatMessageHistory)
core/vectorstore.py        ← Pinecone client initialization
```

---

## Layers and Responsibilities

**`main.py` — Application Entry Point**
- Creates the FastAPI `app`, registers all routers, adds CORS and exception-catching middleware.
- Auth dependency (`JWTBearer`) is defined here but currently commented out on most routers (optional auth via `Depends(optional_auth)` in individual routes).
- Exposes `/_debug/db` and `/_routes` debug endpoints.

**`api/` — HTTP Route Handlers**
- One file per feature domain: `chat.py`, `reference.py`, `hikmah.py`, `primers.py`, `memory_admin.py`, `account.py`.
- Responsibility: parse request, extract optional JWT user ID, call into `core/` pipeline or `services/`, return response.
- No business logic lives here; handler bodies are 10–30 lines.
- DB sessions are injected via `Depends(get_db)` from `db/session.py`.
- Auth is optional (`JWTBearer(jwks, auto_error=False)`); authenticated paths get user-scoped Redis history hydration.

**`core/pipeline_langgraph.py` — Agentic Pipeline Orchestrator**
- The primary path for all `/chat/stream/agentic` and `/chat/agentic` traffic.
- Instantiates `ChatAgent`, drives it via `agent.astream()` (streaming) or `agent.invoke()` (non-streaming).
- Translates LangGraph node events into SSE events: `status`, `response_chunk`, `response_end`, `hadith_references`, `quran_references`, `error`, `done`.
- Handles the streaming generation step itself (post-retrieval LLM token streaming via `chain.stream()`), since LangGraph hands back retrieved docs before generation.
- Calls `chat_persistence_service.append_turn_to_runtime_history()` after every completed turn.

**`core/pipeline.py` — Legacy Pipeline**
- Sequential, synchronous pipeline still used by `POST /chat/`, `POST /chat/stream`, and `POST /references`.
- Steps: classify → translate → enhance → retrieve (Shia + Sunni) → generate/stream.
- Returns `StreamingResponse` for streaming variant.

**`agents/core/chat_agent.py` — LangGraph Agent**
- Defines the `ChatAgent` class: builds a `StateGraph(ChatState)` with 5 nodes and compiles it with `MemorySaver` checkpointing.
- Graph nodes: `fiqh_classification`, `agent`, `tools`, `generate_response`, `check_early_exit`.
- The LLM (`LARGE_LLM`, defaults to `gpt-4.1-2025-04-14`) is bound to 6 tools via `.bind_tools()`.
- Routing decisions (`_should_continue`, `_route_after_fiqh_check`) are pure functions over `ChatState`.
- Loads conversation history from Redis via `core.memory.make_history()` at the start of each `invoke`/`astream` call.

**`agents/state/chat_state.py` — Agent State Schema**
- `ChatState` is a `TypedDict` carrying all state through the graph.
- Key fields: `messages` (LangGraph `add_messages` reducer), `user_query`, `working_query`, `retrieved_docs`, `quran_docs`, `source_coverage`, `early_exit_message`, `errors`, `iterations`.
- `create_initial_state()` is the canonical state factory; always call this — never construct `ChatState` directly.

**`agents/tools/` — LangGraph Tool Wrappers**
- `classification_tools.py`: `check_if_non_islamic_tool`, `check_if_fiqh_tool`
- `translation_tools.py`: `translate_to_english_tool`, `translate_response_tool`
- `enhancement_tools.py`: `enhance_query_tool`
- `retrieval_tools.py`: `retrieve_shia_documents_tool`, `retrieve_sunni_documents_tool`, `retrieve_combined_documents_tool`, `retrieve_quran_tafsir_tool`
- All decorated with `@tool` (LangChain). Tool docstrings are consumed by the LLM to decide when to call each tool.
- Each tool delegates directly to the corresponding `modules/` function.

**`agents/config/agent_config.py` — Agent Configuration**
- Pydantic models: `RetrievalConfig`, `ModelConfig`, `AgentConfig`.
- Controls doc counts per source, model/temperature, max iterations, and feature flags (enable_classification, enable_translation, enable_enhancement).
- `DEFAULT_AGENT_CONFIG = AgentConfig()` used when no per-request config is provided.
- Clients can override via the `config` field in the `ChatRequest` body.

**`modules/` — Discrete AI Pipeline Stages**
- `classification/classifier.py`: Classifies queries as non-Islamic or fiqh using the LLM.
- `embedding/embedder.py`: Dense embeddings (OpenAI `text-embedding-3-small`) and sparse embeddings for hybrid search.
- `retrieval/retriever.py`: Hybrid Pinecone search (dense + sparse) with metadata filtering by `sect` (`shia`/`sunni`). Quran uses a dense-only dedicated index.
- `reranking/reranker.py`: Reranks merged dense+sparse results using configurable weights (`DENSE_RESULT_WEIGHT`, `SPARSE_RESULT_WEIGHT`).
- `enhancement/enhancer.py`: Rewrites the user query to improve retrieval quality.
- `translation/translator.py`: Translates non-English queries to English.
- `generation/generator.py` + `generation/stream_generator.py`: LLM response generation (used by legacy pipeline).
- `context/`: Context assembly utilities.

**`services/` — Business Services**
- `chat_persistence_service.py`: Manages `ChatSession` and `ChatMessage` DB rows, hydrates Redis history from DB on session load, wraps streaming responses to collect and persist assistant text after stream completes.
- `memory_service.py`: Coordinates `UserMemoryProfile` and `MemoryEvent` persistence (structured long-term memory, separate from Redis chat history).
- `consolidation_service.py`: Periodic memory consolidation logic.
- `embedding_service.py`: Generates and stores embeddings for user memory notes.
- `primer_service.py`: Generates baseline and personalized lesson primers, caches results in `personalized_primers` table.
- `hikmah_quiz_service.py`: Hikmah elaboration and quiz logic.
- `account_service.py`: Account management.

**`db/` — Data Access Layer**
- `models/`: SQLAlchemy ORM models (13 tables).
- `schemas/`: Pydantic schemas for API request/response validation.
- `repositories/`: Repository pattern classes wrapping raw SQLAlchemy queries (e.g., `MemoryProfileRepository`, `MemoryEventRepository`).
- `routers/`: CRUD FastAPI routers for `users`, `lessons`, `lesson_content`, `user_progress`, `hikmah_trees` — registered directly in `main.py`.
- `crud/`: Thin CRUD helpers (e.g., `lesson_crud`).
- `session.py`: Sync SQLAlchemy engine (`postgresql+psycopg2`) with SSL, `get_db()` dependency.
- `config.py`: Pydantic `Settings` reading `DB_*` env vars; builds `DATABASE_URL` via `sqlalchemy.engine.URL.create`.

**`core/memory.py` — Redis Conversation History**
- `make_history(session_id)` returns `RedisChatMessageHistory` when Redis is reachable, falls back to in-process `EphemeralHistory`.
- Keys are namespaced: `{REDIS_KEY_PREFIX}:{session_id}`.
- `trim_history()` enforces `MAX_MESSAGES` cap to prevent unbounded growth.
- `with_redis_history()` wraps a LangChain chain with session-aware history (used by legacy pipeline).

**`core/vectorstore.py` — Pinecone Client**
- `_get_vectorstore(index_name)`: Returns `PineconeVectorStore` for dense similarity search.
- `_get_sparse_vectorstore(index_name)`: Returns raw `Pinecone.Index` for sparse or direct vector queries.
- Used exclusively by `modules/retrieval/retriever.py`.

**`core/auth.py` — Authentication**
- Loads AWS Cognito JWKS at startup by fetching `/.well-known/jwks.json`.
- `JWTBearer` (in `models/JWTBearer.py`) is a FastAPI `HTTPBearer` dependency that validates JWT signatures against the loaded keys.
- `auth` (strict) and `optional_auth` (permissive) instances used across `api/` routes.

---

## Data Flow: Agentic Chat (Primary Path)

```
POST /chat/stream/agentic
    ↓
api/chat.py :: chat_pipeline_agentic_ep()
    - Extract optional JWT user_id
    - If user_id: hydrate Redis history from DB (chat_persistence_service)
    - If user_id: persist user message to DB
    - Parse optional AgentConfig from request body
    ↓
core/pipeline_langgraph.py :: chat_pipeline_streaming_agentic()
    - Instantiate ChatAgent(config)
    - Call agent.astream(..., streaming_mode=True)
    ↓
agents/core/chat_agent.py :: ChatAgent.astream()
    - create_initial_state() (loads Redis history)
    - compiled_graph.astream() — LangGraph event loop:

      [fiqh_classification node]
          → classify_fiqh_query() via modules/classification/classifier.py
          → if fiqh: route to [check_early_exit] → END
          → else: route to [agent]

      [agent node] (iterates up to max_iterations=5)
          → llm.invoke(messages) — tool-calling LLM decides next tool
          → if tool_calls: route to [tools]
          → if no tool calls + has docs: route to [generate_response] or END (streaming)
          → if no docs: END

      [tools node]
          → ToolNode executes selected tools from agents/tools/
          → check_if_non_islamic_tool → modules/classification/classifier.py
          → translate_to_english_tool → modules/translation/translator.py
          → enhance_query_tool → modules/enhancement/enhancer.py
          → retrieve_shia_documents_tool → modules/retrieval/retriever.py → Pinecone
          → retrieve_sunni_documents_tool → modules/retrieval/retriever.py → Pinecone
          → retrieve_quran_tafsir_tool → modules/retrieval/retriever.py → Pinecone
          → updates ChatState fields (retrieved_docs, quran_docs, etc.)
          → route back to [agent]

      [generate_response node] (non-streaming only)
          → get_generator_model().invoke() for final answer
    ↓
core/pipeline_langgraph.py (post-graph)
    - Early exit path: emit response_chunk with early_exit_message
    - Normal path: stream LLM tokens via chain.stream() (prompt | chat_model)
    - Emit SSE events: status, response_chunk, response_end, hadith_references, quran_references, done
    - append_turn_to_runtime_history() → Redis
    ↓
api/chat.py (wraps StreamingResponse)
    - chat_persistence_service.wrap_streaming_response_for_persistence()
    - Collects all chunks, extracts answer text, persists to DB after stream ends
    ↓
Client receives SSE stream
```

---

## State Management

**Short-term (per-request):**
- `ChatState` TypedDict passed between LangGraph nodes by value within a single request.
- LangGraph `MemorySaver` checkpointer maintains graph state across node executions within one `invoke`/`astream` call, keyed by `thread_id=session_id`.

**Medium-term (cross-request, conversational):**
- Redis `RedisChatMessageHistory` keyed by `{REDIS_KEY_PREFIX}:{session_id}` (or `{user_id}:{session_id}` for authenticated users).
- TTL-capped (default 12,000 seconds) and message-count capped (`MAX_MESSAGES=30`).
- Loaded at the start of each `invoke`/`astream` as `initial_messages`.

**Long-term (persistent):**
- PostgreSQL via SQLAlchemy: `chat_sessions`, `chat_messages` tables store full conversation history.
- `user_memory_profiles` and `memory_events` tables store structured user learning notes.
- `personalized_primers` table caches primer generation results.

---

## Async vs Sync Patterns

- **FastAPI route handlers** are `async def` throughout.
- **Agentic pipeline streaming** (`chat_pipeline_streaming_agentic`) is fully async: `async for event in agent.astream(...)`, returns `StreamingResponse` with an `AsyncGenerator`.
- **LangGraph graph execution** uses `compiled_graph.astream()` (async) and `compiled_graph.invoke()` (sync).
- **LLM calls inside graph nodes** are synchronous (`llm.invoke()`, `chain.stream()`). The streaming token loop in `pipeline_langgraph.py` uses `chain.stream()` (sync iterator) inside an `async def` generator — this blocks the event loop briefly per iteration.
- **Database access** uses synchronous SQLAlchemy (`db/session.py`, `psycopg2` driver). Async DB via `asyncpg` is configured (`ASYNC_DATABASE_URL`) but not yet actively used in routers.
- **Redis** is accessed synchronously via `langchain_community.chat_message_histories.RedisChatMessageHistory`.

---

## Early Exit Conditions

Two hard exit paths short-circuit the full retrieval pipeline:

1. **Fiqh classification** (`fiqh_classification` node, runs first): if `classify_fiqh_query()` returns True, the graph routes to `check_early_exit` which sets `EARLY_EXIT_FIQH` message.
2. **Non-Islamic classification** (`check_if_non_islamic_tool`, called by the agent as a tool): if the tool returns `is_non_islamic=True`, `_should_continue()` routes to `check_early_exit` which sets `EARLY_EXIT_NON_ISLAMIC` message.

Both paths skip retrieval and generation entirely and emit a canned response.

---

## Error Handling

- **Global middleware** in `main.py` (`catch_exceptions_mw`) catches all unhandled exceptions, logs the traceback, and returns `{"detail": "internal_error"}` with HTTP 500.
- **Route handlers** have explicit try/except blocks, logging to stdout and raising `HTTPException(500)`.
- **LangGraph nodes** catch exceptions internally, append to `state["errors"]`, and set `state["should_end"] = True` rather than raising.
- **Tool functions** (`agents/tools/`) catch exceptions and return error dicts (`{"error": str(e), "documents": []}`) rather than raising, preventing graph termination on retrieval failure.
- **Streaming error recovery**: if `assistant_text` was partially collected before an error, `pipeline_langgraph.py` still attempts to persist it to Redis history.

---

## Key Architectural Decisions

1. **LangGraph over a fixed pipeline**: the agent decides which sources to retrieve based on query analysis, enabling adaptive retrieval (Shia-only, Shia+Sunni+Quran, etc.).
2. **Streaming mode flag in state**: `streaming_mode=True` tells the graph to stop before `generate_response` and return retrieved docs to the pipeline layer, which then streams tokens directly. This avoids buffering the full response in the graph.
3. **Dual persistence (Redis + PostgreSQL)**: Redis provides fast in-process conversation context; PostgreSQL provides durable history that can rebuild Redis on session reload (`hydrate_runtime_history_if_empty`).
4. **Optional auth**: JWT auth is present (`JWTBearer`) but deliberately optional on chat endpoints — unauthenticated requests work but don't get DB-persisted history or user-scoped Redis keys.
5. **Legacy pipeline coexistence**: `core/pipeline.py` is still used for `POST /chat/`, `POST /chat/stream`, and `POST /references`. New feature development should target `pipeline_langgraph.py`.
