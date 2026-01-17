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
- PostgreSQL database
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

Create a `.env` file in the root directory with the following variables:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
LARGE_LLM=gpt-4o
SMALL_LLM=gpt-4o-mini

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
DEEN_DENSE_INDEX_NAME=your_dense_index_name
DEEN_SPARSE_INDEX_NAME=your_sparse_index_name
DENSE_RESULT_WEIGHT=0.8
SPARSE_RESULT_WEIGHT=0.2
REFERENCE_FETCH_COUNT=10

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_KEY_PREFIX=dev:chat
REDIS_TTL_SECONDS=12000
REDIS_MAX_MESSAGES=30

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/deen
DB_HOST=localhost
DB_PORT=5432
DB_NAME=deen
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# AWS Cognito (for authentication)
COGNITO_REGION=us-east-1
COGNITO_POOL_ID=your_pool_id

# CORS Configuration
CORS_ALLOW_ORIGINS=https://deen-frontend.vercel.app
ENV=development
```

### 4. Run Database Migrations

```bash
alembic upgrade head
```

### 5. Start the Development Server

```bash
uvicorn main:app --reload
```

The server will start at `http://127.0.0.1:8000`

### 6. Access API Documentation

- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`
- **Memory Admin Dashboard**: `http://127.0.0.1:8000/admin/memory/dashboard`

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
- [**Authentication**](documentation/AUTHENTICATION.md) - AWS Cognito JWT authentication setup
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

## Development Tools

### Memory Admin Dashboard

Access the interactive developer dashboard to inspect and debug the memory agent:

```
http://localhost:8000/admin/memory/dashboard
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
curl http://localhost:8000/health

# Database connection check
curl http://localhost:8000/_debug/db

# List all routes
curl http://localhost:8000/_routes
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

## API Examples

### Chat with the AI

```bash
curl -X POST "http://localhost:8000/chat/stream" \
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
curl -X POST "http://localhost:8000/references?sect=shia&limit=5" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "user_query": "Justice in Islam"
  }'
```

### Request Elaboration on a Lesson

```bash
curl -X POST "http://localhost:8000/hikmah/elaborate/stream" \
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
- Check Cognito configuration in `.env`

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
