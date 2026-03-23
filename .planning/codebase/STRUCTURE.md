# Project Structure
_Last updated: 2026-03-22_

## Summary

FastAPI backend for an AI-powered Islamic education platform. The codebase is organized into discrete layers: thin API route handlers in `api/`, an agentic AI pipeline in `agents/` and `modules/`, shared utilities in `core/`, a full database layer in `db/`, and business services in `services/`. Tests are split between `tests/` (mock-based unit tests) and `agent_tests/` (integration tests requiring live services).

## Top-Level Layout

```
deen-backend/
├── main.py                     # FastAPI app factory, router registration, CORS config
├── requirements.txt            # Pinned Python dependencies
├── alembic.ini                 # Alembic configuration (URL injected from db/config.py)
├── Dockerfile                  # Python 3.11-slim image, Gunicorn + UvicornWorker
├── docker-compose.yml          # Services: api (FastAPI) + caddy (reverse proxy)
├── .env                        # Local secrets (git-ignored)
├── .gitignore
├── CLAUDE.md                   # Developer guidance for Claude Code
├── AGENTS.md                   # Agent system documentation
├── IMPLEMENTATION_SUMMARY.md   # High-level feature implementation notes
├── README.md                   # Project README
├── api/                        # HTTP route handlers (thin layer, no business logic)
├── agents/                     # LangGraph agent orchestration
├── core/                       # Shared utilities: pipeline, auth, memory, config
├── modules/                    # Discrete AI pipeline stages
├── services/                   # Business logic services consumed by routes and agents
├── db/                         # SQLAlchemy models, Pydantic schemas, repositories, CRUD
├── alembic/                    # Database migration scripts
├── models/                     # HTTP-layer Pydantic schemas and JWT bearer
├── tests/                      # Mock-based unit/integration tests (pytest)
├── agent_tests/                # Live-service integration tests
├── scripts/                    # One-off operational scripts
├── caddy/                      # Reverse proxy config (Caddyfile)
├── documentation/              # Architecture, API, and deployment docs
├── updates_documentation/      # Changelog and troubleshooting notes
└── .planning/                  # GSD planning artifacts (not deployed)
```

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | App entry point. Creates the `FastAPI` instance, registers all routers, configures CORS from `CORS_ALLOW_ORIGINS` env var, attaches a global exception-catching middleware, and exposes `/_debug/db`, `/_routes`, `/`, and `/health` utility endpoints. |
| `requirements.txt` | Fully pinned dependency list. Notable packages: `fastapi`, `langgraph`, `langchain`, `openai`, `pinecone`, `redis`, `SQLAlchemy`, `asyncpg`, `psycopg2-binary`, `alembic`, `pytest`, `sentence-transformers`. |
| `alembic.ini` | Alembic runner config. The `sqlalchemy.url` placeholder is overridden at runtime by `alembic/env.py` using `db/config.py:Settings`. |
| `Dockerfile` | Builds a `python:3.11-slim` image, runs as a non-root `appuser`, starts with `gunicorn -k uvicorn.workers.UvicornWorker -w 2`. |
| `docker-compose.yml` | Defines two services: `api` (FastAPI app on port 8000, not exposed publicly) and `caddy` (reverse proxy on 80/443). |
| `caddy/Caddyfile` | Routes `deen-fastapi.duckdns.org` → `api:8000` with gzip compression. |

## Directory Purposes

### `api/`
Thin FastAPI `APIRouter` modules. Each file maps to a feature domain. No business logic—delegates to `services/`, `core/`, or `modules/`.

- `api/chat.py` — `/chat/*` endpoints: legacy non-streaming, agentic streaming SSE (`/chat/stream/agentic`), non-streaming agentic (`/chat/agentic`), and saved chat retrieval.
- `api/reference.py` — `/references` semantic reference lookup with sect filtering.
- `api/hikmah.py` — `/hikmah/elaborate` elaboration endpoint.
- `api/account.py` — Account-related routes.
- `api/primers.py` — `/primers` personalized primer retrieval.
- `api/memory_admin.py` — `/admin/memory` memory admin dashboard.

### `core/`
Shared infrastructure used across `api/`, `agents/`, and `services/`.

- `core/config.py` — Loads all environment variables via `python-dotenv`. Central source for `OPENAI_API_KEY`, `PINECONE_API_KEY`, `REDIS_*`, `COGNITO_*`, `LARGE_LLM`, `SMALL_LLM`, database URLs, embedding config, and similarity thresholds.
- `core/pipeline_langgraph.py` — Active agentic pipeline. Wraps `agents/core/chat_agent.py` as a LangGraph graph, emits SSE events with node/tool status messages.
- `core/pipeline.py` — Legacy hardcoded pipeline (non-agentic). Kept for reference.
- `core/auth.py` — Fetches Cognito JWKS and constructs a `JWTBearer` instance.
- `core/memory.py` — Low-level Redis access: stores/retrieves per-user conversation history under `REDIS_KEY_PREFIX`.
- `core/vectorstore.py` — Initializes Pinecone dense and sparse index clients.
- `core/prompt_templates.py` — Prompt strings for the LLM.
- `core/logging_config.py` — `setup_logging()` and `get_memory_logger()`. Uses a custom `ExtraFormatter` that colorizes log levels and appends extra key=value fields.
- `core/constants.py` — Project-wide constant definitions.
- `core/utils.py` — Shared utility functions.
- `core/chat_models.py` — Pydantic models shared across pipeline layers.

### `agents/`
LangGraph agent orchestration layer.

- `agents/core/chat_agent.py` — Primary agent. Builds and runs the LangGraph graph; decides which tools to invoke.
- `agents/core/memory_consolidator.py` — Agent that consolidates conversation history into long-term memory notes.
- `agents/core/universal_memory_agent.py` — General-purpose memory agent.
- `agents/tools/classification_tools.py` — LangGraph-compatible wrappers for `modules/classification/`.
- `agents/tools/retrieval_tools.py` — LangGraph-compatible wrappers for `modules/retrieval/`.
- `agents/tools/enhancement_tools.py` — LangGraph-compatible wrappers for `modules/enhancement/`.
- `agents/tools/translation_tools.py` — LangGraph-compatible wrappers for `modules/translation/`.
- `agents/state/chat_state.py` — `TypedDict` defining the graph state passed between nodes.
- `agents/config/agent_config.py` — `AgentConfig` and `RetrievalConfig` Pydantic models; `DEFAULT_AGENT_CONFIG` constant.
- `agents/prompts/agent_prompts.py` — System prompts for the agent.
- `agents/prompts/memory_prompts.py` — Prompts for memory consolidation.
- `agents/prompts/note_templates.py` — Templates for memory note generation.
- `agents/models/user_memory_models.py` — Pydantic models for user memory data.
- `agents/models/db_config.py` — Database config specific to the agents layer.

### `modules/`
Stateless AI pipeline stages. Each subdirectory contains one or two Python files implementing a single processing step.

| Module | File(s) | Responsibility |
|--------|---------|---------------|
| `modules/classification/` | `classifier.py` | Classifies query type (Islamic vs. non-Islamic, fiqh routing) |
| `modules/embedding/` | `embedder.py`, `proprecessor.py` | Generates dense + sparse embeddings |
| `modules/retrieval/` | `retriever.py` | Queries Pinecone indices |
| `modules/reranking/` | `reranker.py` | Reranks retrieved documents |
| `modules/generation/` | `generator.py`, `stream_generator.py` | Generates LLM responses (sync and streaming) |
| `modules/translation/` | `translator.py` | Translates queries to English |
| `modules/enhancement/` | `enhancer.py` | Post-processes generated responses |
| `modules/context/` | `context.py` | Builds context strings from retrieved documents |

### `services/`
Business logic layer. Consumed by route handlers and agents.

- `services/chat_persistence_service.py` — Saves and retrieves chat sessions from the database.
- `services/memory_service.py` — High-level memory operations (read/write user memory).
- `services/consolidation_service.py` — Triggers memory consolidation jobs.
- `services/embedding_service.py` — Manages embedding storage and lookup.
- `services/primer_service.py` — Generates and caches personalized primers.
- `services/hikmah_quiz_service.py` — Business logic for Hikmah page quizzes.
- `services/account_service.py` — Account-related business logic.

### `db/`
Full database layer using SQLAlchemy.

- `db/config.py` — `pydantic-settings` `Settings` class; builds `DATABASE_URL` from individual `DB_*` env vars. Used by `db/session.py` and `alembic/env.py`.
- `db/session.py` — Sync SQLAlchemy engine + `SessionLocal` factory + `get_db()` dependency. Uses `sslmode=require`.
- `db/models/` — 13 SQLAlchemy ORM model files (one per table):
  - `users.py`, `chat_sessions.py`, `chat_messages.py`, `embeddings.py`
  - `lessons.py`, `lesson_content.py`, `user_progress.py`
  - `hikmah_trees.py`, `personalized_primers.py`
  - `lesson_page_quiz_questions.py`, `lesson_page_quiz_choices.py`, `lesson_page_quiz_attempts.py`
- `db/schemas/` — Pydantic response/request schemas for database entities (separate from `models/schemas.py`).
  - `chat_history.py`, `hikmah_trees.py`, `lesson_content.py`, `lessons.py`, `personalized_primers.py`, `user_progress.py`, `users.py`
- `db/repositories/` — Repository pattern for memory-related tables:
  - `memory_consolidation_repository.py`, `memory_event_repository.py`, `memory_profile_repository.py`
- `db/routers/` — CRUD `APIRouter` modules mounted directly in `main.py`:
  - `users.py`, `lessons.py`, `lesson_content.py`, `user_progress.py`, `hikmah_trees.py`
- `db/crud/` — Low-level CRUD helper functions:
  - `base.py`, `users.py`, `lessons.py`, `lesson_content.py`, `hikmah_trees.py`, `personalized_primers.py`, `user_progress.py`
- `db/utils/` — Database utility helpers.

### `alembic/`
Migration management.

- `alembic/env.py` — Injects the real `DATABASE_URL` from `db/config.py:Settings` at migration time.
- `alembic/versions/` — 7 migration scripts (chronological):
  1. `20251008_rename_user_id_to_text.py`
  2. `20260119_add_baseline_primers_to_lessons.py`
  3. `20260119_create_personalized_primers_table.py`
  4. `20260122_create_embedding_tables.py`
  5. `20260218_create_lesson_page_quiz_tables.py`
  6. `20260305_create_chat_history_tables.py`
  7. `a12c6d22b9d9_make_hikmah_tree_id_nullable.py`

### `models/`
HTTP-layer models (distinct from `db/models/`).

- `models/schemas.py` — Pydantic request/response models for API endpoints: `ChatRequest`, `ElaborationRequest`, `ReferenceRequest`, `PersonalizedPrimerRequest/Response`, quiz request/response models.
- `models/JWTBearer.py` — `JWTBearer` FastAPI dependency and `JWKS` model for Cognito token validation.

### `tests/`
Pytest test suite. Mock-based; does not require live external services by default.

- `tests/test_agentic_streaming_pipeline.py` — Agentic pipeline streaming tests.
- `tests/test_agentic_streaming_sse.py` — SSE endpoint tests.
- `tests/test_chat_persistence_service.py` — Chat save/load service tests.
- `tests/test_embedding_service.py` — Embedding service tests.
- `tests/test_hikmah_quiz_service.py` — Quiz service tests.
- `tests/test_primer_service.py` — Primer service tests.
- `tests/db/` — Database compatibility tests that require `DATABASE_URL`:
  - `test_baseline_primers_compatibility.py`
  - `test_db_premiers_table.py`

### `agent_tests/`
Integration tests requiring live external services (Redis, Pinecone, OpenAI).

- `agent_tests/test_memory_agent.py` — Memory agent integration test.
- `agent_tests/test_consolidation.py`, `test_realistic_memory.py`, `test_universal_memory.py` — Memory system integration tests.
- `agent_tests/test_db_connection.py` — Database connectivity check.
- Other debug and threading test files.

### `scripts/`
One-off operational scripts, not part of the application runtime.

- `scripts/generate_primers.py` — Batch-generates primers for lessons.
- `scripts/migrate_embeddings.py` — Migrates embedding data.
- `scripts/set_baseline_primers.py` — Seeds baseline primer content.

### `documentation/`
Developer-facing Markdown documentation.

- `documentation/AI_PIPELINE.md`, `ARCHITECTURE.md`, `API_REFERENCE.md`
- `documentation/AUTHENTICATION.md`, `DEPLOYMENT.md`, `DATABASE.md`
- `documentation/CHATBOT.md`, `MEMORY_AGENT.md`, `HIKMAH_TREES.md`
- `documentation/Agentic_chatbot_API_integration.md`
- `documentation/fiqh_related_docs/` — Fiqh classification documentation.
- `documentation/new_feature_plans/` — Planned feature specs.

## Configuration Files

| File | Purpose |
|------|---------|
| `.env` | All secrets and environment-specific values (git-ignored). See `core/config.py` for the full list of variables read. |
| `core/config.py` | Primary env loader using `python-dotenv`. Read by most application modules. |
| `db/config.py` | Pydantic-settings `Settings` for database connection. Accepts `DB_USER/POSTGRES_USER/PGUSER` aliasing. |
| `alembic.ini` | Alembic runner settings. URL is overridden at runtime; do not edit `sqlalchemy.url` directly. |
| `agents/config/agent_config.py` | `AgentConfig` and `RetrievalConfig` Pydantic models controlling LangGraph agent behavior (document counts, LLM model selection). |
| `docker-compose.yml` | Container orchestration for local or server deployment. |
| `caddy/Caddyfile` | TLS termination and reverse proxy config for production. |

## Entry Points

**Development:**
```bash
uvicorn main:app --reload
# or with explicit port/host:
uvicorn main:app --port 8080 --reload --host 0.0.0.0
```

**Production (Docker):**
```bash
docker compose build --no-cache && docker compose up -d
# Internally runs: gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000 main:app
```

The `FastAPI` app object is `app` in `main.py`. All routers are registered there.

**Primary chat endpoint:** `POST /chat/stream/agentic` — SSE streaming, goes through `api/chat.py` → `core/pipeline_langgraph.py` → `agents/core/chat_agent.py` → tools in `agents/tools/` → stages in `modules/`.

## Notable Patterns in File Organization

**Dual config system:** `core/config.py` (dotenv-based, used by AI/Redis/Pinecone modules) and `db/config.py` (pydantic-settings, used by SQLAlchemy and Alembic). These are separate and must both be kept consistent.

**Dual schema directories:** `models/schemas.py` holds HTTP-layer Pydantic models (request/response shapes for API clients). `db/schemas/` holds Pydantic models for database entity serialization. These serve different purposes and should not be merged.

**Module-per-pipeline-stage:** Each stage in `modules/` is a directory with a single Python file (e.g., `modules/classification/classifier.py`). New pipeline stages follow this pattern.

**Tool wrappers pattern:** `agents/tools/` files wrap `modules/` functions as LangGraph-compatible tools. When adding a new pipeline stage, add a corresponding tool wrapper here.

**Test separation by dependency:** `tests/` uses mocks (no external services needed). `tests/db/` requires `DATABASE_URL`. `agent_tests/` requires all live services. Run only `pytest tests -q` in CI; the other suites are for local integration validation.

**`__init__.py` presence is inconsistent:** Some `db/` subdirs use `__int__.py` (typo — note the missing `i`). This is a known quirk; do not replicate it in new directories.

## Where to Add New Code

**New API endpoint:**
- Route handler: `api/<domain>.py`
- Register router in: `main.py`

**New business logic:**
- Implementation: `services/<domain>_service.py`

**New AI pipeline stage:**
- Core logic: `modules/<stage_name>/<stage_name>.py`
- LangGraph tool wrapper: `agents/tools/<stage_name>_tools.py`

**New database table:**
- ORM model: `db/models/<table_name>.py`
- Pydantic schema: `db/schemas/<table_name>.py`
- CRUD helpers: `db/crud/<table_name>.py`
- Migration: `alembic/versions/YYYYMMDD_<description>.py` (run `alembic revision --autogenerate -m "<description>"`)

**New unit test:**
- File: `tests/test_<module>.py`
- DB-dependent test: `tests/db/test_<module>.py`

**New integration test:**
- File: `agent_tests/test_<feature>.py`
