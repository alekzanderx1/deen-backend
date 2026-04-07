# Deen Backend - AI-Powered Islamic Education Platform

This is the backend service for the **Deen AI platform**, built with **FastAPI**. It provides intelligent API endpoints for Islamic education, featuring a RAG-powered chatbot, reference lookup system, and AI-driven learning courses (Hikmah Trees) with adaptive memory capabilities.

## Features

- **AI Chatbot** - Conversational AI with RAG pipeline for Islamic Q&A
- **Reference Lookup** - Semantic search across Islamic texts (Shia & Sunni sources)
- **Hikmah Trees** - AI-powered courses and lessons with interactive elaboration
- **Universal Memory Agent** - Intelligent system that learns from user interactions
- **Streaming Responses** - Real-time AI response streaming for better UX
- **Multi-language Support** - Translation capabilities for global accessibility

## Quick Start

### Prerequisites

- Python 3.8+
- Supabase account (Postgres + Auth)
- Redis server
- Pinecone account (for vector search)
- OpenAI API key

### 1. Clone and Setup Virtual Environment

```bash
# Clone the repository
git clone <repository-url>
cd deen-backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate      # On Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory by copying the template:

```bash
cp .env.example .env
# Edit .env and fill in your real values.
# See the "Environment Variables" section below for descriptions of each variable.
```

### 4. Run Database Migrations

```bash
alembic upgrade head
```

### 5. Start the Development Server

```bash
uvicorn main:app --port 8080 --reload --host 0.0.0.0
```

The server will start at `http://127.0.0.1:8080`

### 6. Access API Documentation

- **Swagger UI**: `http://127.0.0.1:8080/docs`
- **ReDoc**: `http://127.0.0.1:8080/redoc`
- **Memory Admin Dashboard**: `http://127.0.0.1:8080/admin/memory/dashboard`

## Setting Up a New Supabase Project

Use this when provisioning a new environment (e.g. staging → prod). The steps below recreate the database schema and auth configuration from scratch.

### 1. Create the Supabase project

Create a new project in the [Supabase dashboard](https://supabase.com/dashboard). Once provisioned, collect the following from **Project Settings → API**:

- **Project URL** → `SUPABASE_URL`
- **`service_role` key** → `SUPABASE_SERVICE_ROLE_KEY`
- **DB password** (set during project creation)
- **Connection string** → Database → Connection string → URI (use port **5432**)

### 2. Configure environment variables

```bash
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL, ASYNC_DATABASE_URL
```

Use the **direct connection** (port `5432`), not the transaction pooler (port `6543` is incompatible with asyncpg):

```
DATABASE_URL=postgresql://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
ASYNC_DATABASE_URL=postgresql+asyncpg://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

### 3. Run database migrations

```bash
source venv/bin/activate
alembic upgrade head
```

This runs all migrations in order and creates all 13 tables. The command is idempotent — safe to re-run.

### 4. Configure Supabase Auth

The backend validates JWTs only — no manual key configuration is needed. The JWKS endpoint is fetched automatically at startup from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`.

In the Supabase dashboard → **Authentication → Providers**:
- Enable **Email** (or whichever providers the frontend uses)
- Set redirect URLs and JWT expiry to match your environment

### Full sequence

```bash
cp .env.example .env          # fill in prod values
alembic upgrade head           # create all tables
docker compose up -d           # or: uvicorn main:app --reload
```

## Architecture Overview

The Deen backend follows a modular architecture with clear separation of concerns:

```
deen-backend/
├── api/              # API route handlers
├── core/             # Core business logic and pipelines
├── modules/          # AI pipeline components (RAG, embeddings, etc.)
├── agents/           # Agentic AI components (memory agent)
├── db/               # Database models, schemas, and repositories
├── models/           # Pydantic schemas and JWT authentication
└── services/         # Business logic services
```

For detailed architecture information, see [Architecture Documentation](documentation/ARCHITECTURE.md).

## Core Features Documentation

### AI & RAG Pipeline

- [**Chatbot**](documentation/CHATBOT.md) - RAG-powered conversational AI with query classification and context-aware responses
- [**Reference Lookup**](documentation/REFERENCE_LOOKUP.md) - Semantic search across Islamic texts with sect filtering
- [**AI Pipeline**](documentation/AI_PIPELINE.md) - Detailed breakdown of classification, embedding, retrieval, and generation modules

### Learning Platform

- [**Hikmah Trees**](documentation/HIKMAH_TREES.md) - AI-powered courses and lessons with interactive elaboration
- [**Memory Agent**](documentation/MEMORY_AGENT.md) - Universal memory system that learns from user interactions

### Technical Documentation

- [**Database**](documentation/DATABASE.md) - PostgreSQL schema, models, and migrations
- [**API Reference**](documentation/API_REFERENCE.md) - Complete API endpoint documentation
- [**Authentication**](documentation/AUTHENTICATION.md) - Supabase Auth JWT authentication setup (v1.1+)
- [**Deployment**](documentation/DEPLOYMENT.md) - Docker and production deployment guide

## Key Technologies

- **FastAPI** - Modern, fast web framework for building APIs
- **PostgreSQL** - Primary database for structured data
- **Redis** - Session and conversation memory storage
- **Pinecone** - Vector database for semantic search
- **OpenAI LLMs** - Large language model for AI responses
- **LangChain** - Framework for LLM application development
- **SQLAlchemy** - ORM for database operations
- **Alembic** - Database migration tool

## Environment Variables

Copy `.env.example` to `.env` and fill in the real values. All variables are described below.

> **Upgrading from v1.0?** Remove `COGNITO_REGION` and `COGNITO_POOL_ID` from your `.env` — these are no longer used. Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` instead.

### OpenAI

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key. Get from [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `LARGE_LLM` | Yes | Large model ID for generation, filtering, refinement. Default: `gpt-4.1-2025-04-14` |
| `SMALL_LLM` | Yes | Small model ID for classification, routing, decomposition. Default: `gpt-4o-mini-2024-07-18` |

### Pinecone

| Variable | Required | Description |
|----------|----------|-------------|
| `PINECONE_API_KEY` | Yes | Pinecone API key. Get from [app.pinecone.io](https://app.pinecone.io) |
| `DEEN_DENSE_INDEX_NAME` | Yes | Dense vector index for hadith/Islamic content |
| `DEEN_SPARSE_INDEX_NAME` | Yes | Sparse vector index for hadith/Islamic content |
| `QURAN_DENSE_INDEX_NAME` | No | Dense vector index for Quran tafsir |
| `DEEN_FIQH_DENSE_INDEX_NAME` | No* | Dense vector index for Sistani fiqh rulings. *Required for fiqh queries |
| `DEEN_FIQH_SPARSE_INDEX_NAME` | No* | Sparse vector index for Sistani fiqh rulings. *Required for fiqh queries |
| `DENSE_RESULT_WEIGHT` | No | Weight for dense retrieval results (default: `0.8`). Must sum to 1.0 with `SPARSE_RESULT_WEIGHT` |
| `SPARSE_RESULT_WEIGHT` | No | Weight for sparse retrieval results (default: `0.2`) |
| `REFERENCE_FETCH_COUNT` | No | Number of references to fetch per query (default: `10`) |

### Supabase

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Project URL. Supabase Dashboard → Project Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Service role secret key. Supabase Dashboard → Project Settings → API → `service_role` |

### Database

Provide either `DATABASE_URL` / `ASYNC_DATABASE_URL` directly, or provide all `DB_*` components and the app will build the URL.

Use the **direct connection** (port 5432), not the transaction pooler (port 6543 is incompatible with asyncpg).

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes* | Sync PostgreSQL connection string (`postgresql://...`) |
| `ASYNC_DATABASE_URL` | Yes* | Async PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `DB_HOST` | Yes* | Database host (alternative to `DATABASE_URL`) |
| `DB_PORT` | No | Database port (default: `5432`) |
| `DB_NAME` | Yes* | Database name (alternative to `DATABASE_URL`) |
| `DB_USER` | Yes* | Database user (alternative to `DATABASE_URL`) |
| `DB_PASSWORD` | Yes* | Database password (alternative to `DATABASE_URL`) |

*Either `DATABASE_URL` + `ASYNC_DATABASE_URL`, or all `DB_*` components must be provided.

### Redis

| Variable | Required | Description |
|----------|----------|-------------|
| `REDIS_URL` | No | Redis connection URL (default: `redis://localhost:6379/0`). Falls back to in-process ephemeral history if unreachable |
| `REDIS_KEY_PREFIX` | No | Namespace prefix for Redis keys (default: `dev:chat`) |
| `REDIS_TTL_SECONDS` | No | Conversation TTL in seconds (default: `12000` ~3.3 hours) |
| `REDIS_MAX_MESSAGES` | No | Max messages kept per session (default: `30`) |

### Memory / Personalization

| Variable | Required | Description |
|----------|----------|-------------|
| `EMBEDDING_MODEL` | No | OpenAI embedding model for user memory note vectors (default: `text-embedding-3-small`). Must match the dimension count of the Pinecone memory index |
| `EMBEDDING_DIMENSIONS` | No | Vector dimension count matching `EMBEDDING_MODEL` (default: `1536`) |
| `NOTE_FILTER_THRESHOLD` | No | Minimum cosine similarity score (0.0-1.0) for a memory note to be injected into context (default: `0.4`) |
| `SIGNAL_QUALITY_THRESHOLD` | No | Minimum quality score (0.0-1.0) required before a memory signal is persisted (default: `0.5`) |

### App

| Variable | Required | Description |
|----------|----------|-------------|
| `ENV` | No | Runtime environment. `development` enables auth bypass for local testing (default: `development`) |
| `CORS_ALLOW_ORIGINS` | No | Comma-separated list of allowed CORS origins (default: `*`) |

## Development Tools

### Memory Admin Dashboard

Access the interactive developer dashboard to inspect and debug the memory agent:

```
http://localhost:8080/admin/memory/dashboard
```

Features:

- View user memory profiles
- Browse notes by category (learning, knowledge, interest, behavior, preference)
- Inspect memory events and processing status
- View consolidation history

See [Memory Agent Documentation](documentation/MEMORY_AGENT.md) for details.

### Health Check Endpoints

```bash
# General health check
curl http://localhost:8080/health

# Database connection check
curl http://localhost:8080/_debug/db

# List all routes
curl http://localhost:8080/_routes
```

## Docker Deployment

### Quick Start with Docker

```bash
# Stop any existing containers
docker compose down

# Optional: Clean up (recommended on small instances)
docker system prune -af

# Rebuild with no cache
docker compose build --no-cache

# Start services
docker compose up -d

# Check logs
docker logs --tail=200 deen-backend
docker logs --tail=200 deen-caddy
```

For complete deployment instructions, see [Deployment Documentation](documentation/DEPLOYMENT.md).

## Testing

Run the test suite:

```bash
# Test database connection
python agent_tests/test_db_connection.py

# Test memory agent
python agent_tests/test_memory_agent.py

# Test Hikmah memory integration
python agent_tests/test_hikmah_memory_integration.py
```

### Testing the agentic streaming API

This test runs the agentic streaming pipeline and writes the combined SSE output to a markdown file (as the UI would show it: response + hadith and Quran references).

**Recommended: use a virtual environment** so dependencies and paths match the rest of the project:

```bash
# From repository root (deen-backend)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

Ensure `.env` is configured (OpenAI, Redis, Pinecone, etc.). You do **not** need to start the server.

Run from the **project root**:

```bash
python tests/test_agentic_streaming_sse.py
```

The script prints the path to the generated markdown file (e.g. a temp file). Open it to see the full response and references.

Optional env vars: `AGENTIC_TEST_QUERY`, `AGENTIC_TEST_SESSION`, `AGENTIC_TEST_OUTPUT` (output file path).

With pytest installed: `python -m pytest tests/test_agentic_streaming_sse.py -v -s`

## API Examples

### Chat with the AI

```bash
curl -X POST "http://localhost:8080/chat/stream" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "user_query": "What is the concept of Imamate in Shia Islam?",
    "session_id": "user123:thread-1",
    "language": "english"
  }'
```

### Look Up References

```bash
curl -X POST "http://localhost:8080/references?sect=shia&limit=5" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "user_query": "Justice in Islam"
  }'
```

### Request Elaboration on a Lesson

```bash
curl -X POST "http://localhost:8080/hikmah/elaborate/stream" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "selected_text": "What is Taqwa?",
    "context_text": "Full lesson context...",
    "hikmah_tree_name": "Foundations of Faith",
    "lesson_name": "Understanding Piety",
    "lesson_summary": "This lesson covers...",
    "user_id": "user123"
  }'
```

## Project Structure

```
deen-backend/
├── api/                      # API endpoints
│   ├── account.py           # Account management
│   ├── chat.py              # Chat endpoints
│   ├── hikmah.py            # Hikmah elaboration
│   ├── memory_admin.py      # Memory admin dashboard
│   └── reference.py         # Reference lookup
├── agents/                   # Agentic AI components
│   ├── core/                # Memory agent and consolidator
│   ├── models/              # Memory data models
│   └── prompts/             # AI prompts and templates
├── core/                     # Core business logic
│   ├── pipeline.py          # Main AI pipelines
│   ├── memory.py            # Redis memory management
│   ├── config.py            # Configuration
│   └── auth.py              # JWT authentication
├── modules/                  # AI pipeline modules
│   ├── classification/      # Query classification
│   ├── embedding/           # Dense & sparse embeddings
│   ├── enhancement/         # Query enhancement
│   ├── retrieval/           # Vector retrieval
│   ├── reranking/           # Result reranking
│   ├── generation/          # Response generation
│   └── translation/         # Multi-language support
├── db/                       # Database layer
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── repositories/        # Data access layer
│   └── routers/             # CRUD API routers
├── services/                 # Business logic services
├── documentation/            # Detailed documentation
└── alembic/                  # Database migrations
```

## Contributing

When contributing to this project:

1. Follow the existing code structure
2. Add type hints to all functions
3. Update documentation for new features
4. Write tests for new functionality
5. Ensure all tests pass before submitting

## Troubleshooting

### Common Issues

**Database Connection Errors**

- Verify `.env` file has correct database credentials
- Ensure PostgreSQL is running
- Check database exists: `psql -l`

**Redis Connection Errors**

- Verify Redis is running: `redis-cli ping`
- Check `REDIS_URL` in `.env`

**Authentication Errors**

- Verify JWT token is valid
- Check `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set in `.env`
- Verify the Supabase JWT signing key is asymmetric (RS256/ES256): `curl <SUPABASE_URL>/auth/v1/keys` should return a non-empty `keys` array

**Memory Agent Not Working**

- Check database consolidation: See `updates_documentation/DATABASE_CONFIG_CONSOLIDATION.md`
- Verify background thread logs in console

For more troubleshooting help, see `updates_documentation/TROUBLESHOOTING.md`.

## License

[Your License Here]

## Support

For questions or issues, please contact the development team or open an issue in the repository.

---

**Documentation Last Updated**: January 2026
