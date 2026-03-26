# Integrations

_Last updated: 2026-03-22_

## Summary

The deen-backend FastAPI application integrates with OpenAI for LLM-based generation and translation, Pinecone for dense and sparse vector retrieval, and AWS Cognito for JWT-based authentication. Conversation history is persisted in Redis, while structured application data lives in a PostgreSQL database accessed via SQLAlchemy (sync and async drivers).

---

## External APIs & Services

**OpenAI:**
- Used for: LLM response generation, translation, classification, query enhancement, memory consolidation
- SDK: `openai==1.91.0`, accessed via `langchain-openai==0.3.25`
- Auth env var: `OPENAI_API_KEY`
- Models: `LARGE_LLM` (default `gpt-4.1-2025-04-14`), `SMALL_LLM` (default `gpt-4o-mini-2024-07-18`)
- Model selection: `core/chat_models.py` (referenced by `modules/generation/generator.py`, `modules/translation/translator.py`, `modules/classification/classifier.py`)

**Pinecone:**
- Used for: Semantic document retrieval using hybrid dense + sparse vector search over Islamic texts
- SDK: `pinecone==7.3.0`, `langchain-pinecone==0.2.8`
- Auth env var: `PINECONE_API_KEY`
- Init: `core/vectorstore.py`
- Indexes:
  - `DEEN_DENSE_INDEX_NAME` — dense vectors, namespace `ns1`, text key `text_en`
  - `DEEN_SPARSE_INDEX_NAME` — sparse TF-IDF vectors
  - `QURAN_DENSE_INDEX_NAME` — dense vectors for Quranic content
- Retrieval weighting: `DENSE_RESULT_WEIGHT` (default `0.8`) and `SPARSE_RESULT_WEIGHT` (default `0.2`)
- Result count: `REFERENCE_FETCH_COUNT` (default `10`)

**HuggingFace (local inference):**
- Used for: Dense embeddings for Pinecone upsert and query-time lookup
- SDK: `langchain-huggingface==0.1.2`, `sentence-transformers==3.4.1`, `transformers==4.48.2`
- Model: `sentence-transformers/all-mpnet-base-v2` (loaded locally at startup via `modules/embedding/embedder.py`)
- No external API call; model weights downloaded from HuggingFace Hub and run locally

---

## Authentication & Identity

**AWS Cognito:**
- Used for: User pool JWT authentication (Bearer token scheme)
- SDK: `boto3==1.35.96` (for admin operations), `python-jose==3.5.0` (JWT verification)
- Auth env vars: `COGNITO_REGION`, `COGNITO_POOL_ID`
- JWKS endpoint fetched at startup: `https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_POOL_ID}/.well-known/jwks.json`
- JWT verification: `models/JWTBearer.py` — validates `kid`, verifies RS256 signature against public JWKS
- Boto3 usage: `api/account.py` — calls `cognito_client.admin_delete_user()` using IAM role credentials attached to the EC2 host (no access key env vars required)
- User identifier extracted from JWT claim: `sub` (Cognito UUID)

---

## Data Stores

**PostgreSQL:**
- Used for: All structured application data — users, lessons, lesson content, chat sessions, chat messages, user progress, hikmah trees, personalized primers, quiz questions/choices/attempts, memory consolidation events, memory profiles, and vector embeddings
- Driver (sync): `psycopg2-binary==2.9.10` via `postgresql+psycopg2` — `db/session.py`
- Driver (async): `asyncpg==0.30.0` via `postgresql+asyncpg` — referenced in `core/config.py` (`ASYNC_DATABASE_URL`)
- ORM: `SQLAlchemy==2.0.41` with `declarative_base` in `db/session.py`
- SSL: `connect_args={"sslmode": "require"}` enforced in `db/session.py`
- Connection env vars: `DATABASE_URL` / `ASYNC_DATABASE_URL` (full DSN), or individual components `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (also accepts `POSTGRES_*` / `PG*` aliases via `db/config.py`)
- pgvector extension: `pgvector==0.3.6` — `db/models/embeddings.py` stores 1536-dimension `Vector` columns in `note_embeddings` and `lesson_chunk_embeddings` tables for semantic similarity search
- Migrations: Alembic (`alembic==1.14.0`), config in `alembic.ini`, versions in `alembic/versions/`

---

## Caching & Message Queues

**Redis:**
- Used for: Per-user conversation history storage with TTL-based expiry
- SDK: `redis==6.4.0`, `langchain-community==0.3.27` (`RedisChatMessageHistory`)
- Connection env var: `REDIS_URL` (default `redis://localhost:6379/0`)
- Key scheme: `{REDIS_KEY_PREFIX}:{session_id}` — prefix controlled by `REDIS_KEY_PREFIX` (default `dev:chat`)
- TTL: `REDIS_TTL_SECONDS` (default `12000` seconds)
- Max messages per session: `REDIS_MAX_MESSAGES` (default `30`), enforced by `core/memory.py:trim_history()`
- Fallback: If Redis is unreachable at startup, `core/memory.py` falls back to in-process ephemeral `ChatMessageHistory` (non-persistent)
- Admin: session inspection and management exposed at `/admin/memory` via `api/memory_admin.py`

---

## Infrastructure & Deployment

**Docker + Caddy:**
- Application containerized via `Dockerfile` — Python 3.11-slim base, non-root `appuser`
- Process: `gunicorn` with `UvicornWorker`, 2 workers, binding `0.0.0.0:8000`
- Compose: `docker-compose.yml` defines two services — `deen-backend` (FastAPI app) and `deen-caddy` (reverse proxy)
- TLS termination: Caddy 2 (`caddy:2`) handles HTTPS on ports 80/443, proxies to `api:8000`
- Domain: `deen-fastapi.duckdns.org` (configured in `caddy/Caddyfile`)

**CORS:**
- Configured in `main.py` via `CORSMiddleware`
- Allowed origins: `CORS_ALLOW_ORIGINS` env var (default `https://deen-frontend.vercel.app`)
- Development mode (`ENV=development`): additionally allows `localhost:5173`, `localhost:3000`

**Logging:**
- No external observability service (Sentry, Datadog, etc.) detected
- Custom `ExtraFormatter` with ANSI color output via `core/logging_config.py`
- SQLAlchemy and httpx log levels suppressed to `WARNING` to reduce noise

**LangSmith:**
- `langsmith==0.4.4` is installed as a transitive LangChain dependency but no explicit `LANGSMITH_API_KEY` or `LANGCHAIN_TRACING_V2` configuration was detected in the codebase
