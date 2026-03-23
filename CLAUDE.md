# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

# Run locally (http://127.0.0.1:8000)
uvicorn main:app --reload

# Run specific port
uvicorn main:app --port 8080 --reload --host 0.0.0.0

# Tests
pytest tests -q                             # primary test suite
pytest tests/db -q                          # DB compatibility (requires DATABASE_URL)
python agent_tests/test_memory_agent.py     # memory agent integration
pytest tests/test_agentic_streaming_sse.py -v -s

# Docker
docker compose build --no-cache && docker compose up -d

# Verify agentic endpoint
curl -X POST http://127.0.0.1:8000/chat/stream/agentic ...
```

## Architecture

**FastAPI backend for an AI-powered Islamic education platform.**

The AI pipeline flows: HTTP request → `api/` → `core/pipeline_langgraph.py` → `agents/` → `modules/` pipeline stages → response.

### Layer responsibilities

- **`api/`** — Thin route handlers. Business logic belongs in `services/`, `core/`, or `modules/`.
- **`core/`** — Shared utilities: `pipeline_langgraph.py` (active agentic pipeline), `pipeline.py` (legacy), `auth.py` (JWT via AWS Cognito), `memory.py` (Redis), `vectorstore.py` (Pinecone init), `config.py` (env loader).
- **`agents/`** — LangGraph agent orchestration. `core/chat_agent.py` drives the graph; `tools/` wraps pipeline stages as LangGraph-compatible tools; `state/chat_state.py` manages agent state; `config/agent_config.py` controls behavior.
- **`modules/`** — Discrete AI pipeline stages: classification → embedding (dense + sparse) → retrieval (Pinecone) → reranking → generation (OpenAI) → translation/enhancement.
- **`services/`** — Business services consumed by routes and agents: chat persistence, embedding management, primer generation, memory consolidation.
- **`db/`** — SQLAlchemy models, Pydantic schemas, repository pattern (data access), routers (CRUD endpoints), `session.py` (sync engine), `config.py` (Pydantic DB settings).
- **`alembic/`** — DB migrations. Always run `alembic upgrade head` after pulling.

### Chat endpoints (key paths)

| Endpoint | Description |
|---|---|
| `POST /chat/stream/agentic` | Streaming agentic chat (SSE), primary endpoint |
| `POST /chat/agentic` | Non-streaming agentic chat |
| `GET /references` | Semantic reference lookup with sect filtering |
| `POST /hikmah/elaborate` | Hikmah tree elaboration |
| `GET /primers` | Personalized primer retrieval |
| `GET /admin/memory` | Memory admin dashboard |

### Key environment variables

```
OPENAI_API_KEY, LARGE_LLM, SMALL_LLM
PINECONE_API_KEY, DEEN_DENSE_INDEX_NAME, DEEN_SPARSE_INDEX_NAME, QURAN_DENSE_INDEX_NAME
REDIS_URL, REDIS_KEY_PREFIX, REDIS_TTL_SECONDS, REDIS_MAX_MESSAGES
DATABASE_URL, ASYNC_DATABASE_URL
COGNITO_REGION, COGNITO_POOL_ID
CORS_ALLOW_ORIGINS
ENV (development/production)
```

Current LLM defaults: `LARGE_LLM=gpt-4.1-2025-04-14`, `SMALL_LLM=gpt-4o-mini-2024-07-18`.

### Agentic pipeline (LangGraph)

`core/pipeline_langgraph.py` implements the active pipeline as a LangGraph graph. The agent uses 8 tools across 4 stages. Key early-exit conditions: `non_islamic` classification and `fiqh` routing. When adding new agentic behavior, write tests around tool-selection outcomes and these early-exit paths.

### Memory system

Redis stores per-user conversation history (`REDIS_KEY_PREFIX` namespaced). `services/memory_service.py` and `services/consolidation_service.py` handle memory operations; `core/memory.py` provides low-level Redis access. Memory admin is exposed at `/admin/memory`.

### Database

13 SQLAlchemy tables in `db/models/`. 6 Alembic migrations in `alembic/versions/`. The project uses both sync (`db/session.py`) and async (`ASYNC_DATABASE_URL`) database sessions.

## Coding conventions

- `snake_case` for modules/functions/variables; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants.
- Add type hints to new/changed functions.
- `pytest` with `pytest-asyncio` for async tests. Mock-based unit tests go in `tests/`; environment-dependent integration tests go in `tests/db/` or `agent_tests/`.
- Commit style: short imperative subjects, e.g. `feat: add primer cache invalidation`.

## PR checklist

Include: purpose, impacted endpoints (especially `/chat/stream/agentic`), migration notes (`alembic/versions/...`), env var changes, test evidence.
