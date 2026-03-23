# Technology Stack

_Last updated: 2026-03-22_

## Summary

Deen Backend is a Python 3.11 FastAPI application serving an AI-powered Islamic education platform. It uses LangChain and LangGraph to orchestrate a multi-stage RAG pipeline backed by OpenAI LLMs, Pinecone vector search, and a PostgreSQL relational database. The server runs as a Dockerized Gunicorn/Uvicorn process behind a Caddy reverse proxy.

## Languages

**Primary:**
- Python 3.11 (Dockerfile base image: `python:3.11-slim`) — all application code

**Secondary:**
- None — the project is pure Python

## Runtime

**Environment:**
- CPython 3.11 (system version: 3.11.4)
- Virtual environment: `venv/` at project root

**Package Manager:**
- `pip` — no Poetry or pipenv
- Lockfile: `requirements.txt` (pinned versions, committed)

## Frameworks

**Web:**
- `fastapi==0.115.8` — HTTP framework, route definitions, dependency injection
- `starlette==0.45.3` — ASGI foundation; SSE streaming via `StreamingResponse`
- `uvicorn==0.34.0` — ASGI server for local dev (`uvicorn main:app --reload`)
- `gunicorn==23.0.0` — production process manager with Uvicorn workers (`-w 2`)

**AI / LLM Orchestration:**
- `langchain==0.3.27` — core LangChain framework; prompt templates, runnables, history
- `langchain-core==0.3.74` — base abstractions
- `langchain-openai==0.3.25` — OpenAI chat model bindings via `init_chat_model`
- `langchain-community==0.3.27` — `RedisChatMessageHistory`, `ChatMessageHistory`
- `langchain-pinecone==0.2.8` — `PineconeVectorStore` integration
- `langchain-huggingface==0.1.2` — `HuggingFaceEmbeddings` for dense embedding
- `langgraph==0.2.64` — agentic graph orchestration; active pipeline in `core/pipeline_langgraph.py`
- `langgraph-checkpoint==2.1.1` — LangGraph state checkpointing
- `langgraph-sdk==0.1.74` — LangGraph SDK utilities
- `langsmith==0.4.4` — tracing/observability for LangChain runs

**Database / ORM:**
- `SQLAlchemy==2.0.41` — ORM + Core; both sync (`db/session.py`) and async (`ASYNC_DATABASE_URL`) sessions
- `alembic==1.14.0` — schema migrations (`alembic/versions/`, 7 migration files)
- `psycopg2-binary==2.9.10` — sync PostgreSQL driver
- `asyncpg==0.30.0` — async PostgreSQL driver
- `pgvector==0.3.6` — PostgreSQL vector extension support

**Data Validation:**
- `pydantic==2.10.6` — request/response models, config validation
- `pydantic-settings==2.10.1` — `BaseSettings` for `db/config.py`

**Testing:**
- `pytest==8.4.1` — test runner
- `pytest-asyncio==0.26.0` — async test support
- `pytest-benchmark==5.1.0` — performance benchmarks
- `pytest-recording==0.13.4` — VCR cassette-based HTTP recording
- `pytest-socket==0.7.0` — network isolation for unit tests
- `vcrpy==7.0.0` — HTTP interaction recording/replay
- `syrupy==4.9.1` — snapshot testing
- `langchain-tests==0.3.20` — LangChain test utilities

## Key Dependencies

**Critical AI Pipeline:**
- `openai==1.91.0` — direct OpenAI client (also used under LangChain)
- `pinecone==7.3.0` — Pinecone SDK for vector index operations
- `sentence-transformers==3.4.1` — HuggingFace sentence-transformer models; `all-mpnet-base-v2` loaded at startup via `modules/embedding/embedder.py`
- `torch==2.6.0` — required by sentence-transformers
- `transformers==4.48.2` — HuggingFace transformers library
- `scikit-learn==1.6.1` — `TfidfVectorizer` for sparse embeddings
- `tiktoken==0.9.0` — OpenAI token counting
- `numpy==2.2.2` — vector math for sparse embedding generation

**Caching / Memory:**
- `redis==6.4.0` — Redis client for conversation history persistence (`core/memory.py`)

**Auth:**
- `python-jose==3.5.0` — JWT decode and JWK verification for AWS Cognito tokens (`models/JWTBearer.py`)

**HTTP / Networking:**
- `httpx==0.28.1` — async HTTP client
- `httpx-sse==0.4.1` — SSE client support
- `requests==2.32.3` — sync HTTP (used for JWKS endpoint fetch at startup)
- `boto3==1.35.96` — AWS SDK (present in requirements; used for any AWS service calls)
- `aiohttp==3.12.13` — async HTTP (used by LangChain internals)

**Serialization:**
- `orjson==3.10.18` — fast JSON
- `ormsgpack==1.10.0` — MessagePack serialization

## Configuration

**Environment:**
- All secrets and runtime config loaded via `python-dotenv==1.0.1` in `core/config.py`
- `.env` file at project root (not committed)
- `db/config.py` uses `pydantic-settings` `BaseSettings` with env file loading

**Key required env vars:**
```
OPENAI_API_KEY
PINECONE_API_KEY
DEEN_DENSE_INDEX_NAME
DEEN_SPARSE_INDEX_NAME
QURAN_DENSE_INDEX_NAME
REDIS_URL
DATABASE_URL  (or DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD separately)
ASYNC_DATABASE_URL
COGNITO_REGION
COGNITO_POOL_ID
LARGE_LLM           # default: gpt-4.1-2025-04-14
SMALL_LLM           # default: gpt-4o-mini-2024-07-18
```

**Optional tuning vars:**
```
DENSE_RESULT_WEIGHT          # default: 0.8
SPARSE_RESULT_WEIGHT         # default: 0.2
REFERENCE_FETCH_COUNT        # default: 10
REDIS_KEY_PREFIX             # default: dev:chat
REDIS_TTL_SECONDS            # default: 12000
REDIS_MAX_MESSAGES           # default: 30
EMBEDDING_MODEL              # default: text-embedding-3-small
EMBEDDING_DIMENSIONS         # default: 1536
NOTE_FILTER_THRESHOLD        # default: 0.4
SIGNAL_QUALITY_THRESHOLD     # default: 0.5
CORS_ALLOW_ORIGINS           # default: https://deen-frontend.vercel.app
ENV                          # development/production
```

**Build:**
- `Dockerfile` — `python:3.11-slim` base, installs `requirements.txt`, runs as non-root `appuser`
- `docker-compose.yml` — defines `api` service (this app) and `caddy` reverse proxy service
- No build step required; Python is interpreted

## Platform Requirements

**Development:**
- Python 3.11
- Redis (optional; falls back to in-process ephemeral history if unreachable)
- PostgreSQL with SSL (`sslmode=require` in `db/session.py`)
- Pinecone account with 3 indexes (dense Deen, sparse Deen, dense Quran)
- OpenAI API access

**Production:**
- Docker + Docker Compose
- Caddy 2 (reverse proxy with automatic HTTPS via `caddy:2` image)
- External Redis, PostgreSQL, Pinecone, OpenAI, AWS Cognito
- Hostname: `deen-fastapi.duckdns.org` (configured in `caddy/Caddyfile`)

---

_Stack analysis: 2026-03-22_
