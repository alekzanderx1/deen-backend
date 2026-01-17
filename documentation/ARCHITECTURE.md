# Deen Backend Architecture

This document provides a comprehensive overview of the Deen backend system architecture, including the technology stack, module organization, data flows, and design patterns.

## Table of Contents

- [System Overview](#system-overview)
- [Technology Stack](#technology-stack)
- [Architecture Layers](#architecture-layers)
- [Module Organization](#module-organization)
- [Data Flow](#data-flow)
- [Database Architecture](#database-architecture)
- [AI Pipeline Architecture](#ai-pipeline-architecture)
- [Memory System Architecture](#memory-system-architecture)
- [Deployment Architecture](#deployment-architecture)

## System Overview

Deen is an AI-powered Islamic education platform backend that combines:

- **RAG (Retrieval-Augmented Generation)** for accurate, source-backed AI responses
- **Hybrid Vector Search** for semantic similarity and keyword matching
- **Adaptive Memory System** that learns from user interactions
- **Streaming Responses** for real-time user experience
- **Multi-language Support** for global accessibility

### High-Level Architecture

```mermaid
graph TB
    subgraph Client
        Frontend[Web/Mobile Client]
    end
    
    subgraph Backend[FastAPI Backend]
        API[API Layer]
        Core[Core Business Logic]
        Modules[AI Pipeline Modules]
        Agents[Memory Agents]
    end
    
    subgraph DataStores[Data Stores]
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis)]
        Pinecone[(Pinecone Vector DB)]
    end
    
    subgraph External[External Services]
        OpenAI[OpenAI API]
        Cognito[AWS Cognito]
    end
    
    Frontend -->|HTTP/WebSocket| API
    API --> Core
    Core --> Modules
    Core --> Agents
    Modules --> Pinecone
    Modules --> OpenAI
    API --> Cognito
    Core --> Redis
    Agents --> PostgreSQL
    Core --> PostgreSQL
```

## Technology Stack

### Core Framework

- **FastAPI** (v0.115.8) - High-performance web framework with automatic API documentation
- **Python 3.8+** - Programming language
- **Uvicorn/Gunicorn** - ASGI server for production deployment

### AI/ML Stack

- **OpenAI GPT-4** - Large language model for generation
- **LangChain** (v0.3.27) - LLM application framework
- **LangGraph** (v0.2.64) - Agent workflow orchestration
- **Sentence Transformers** (v3.4.1) - Dense embeddings
- **Pinecone** (v7.3.0) - Vector database for semantic search

### Data Storage

- **PostgreSQL** - Primary relational database (RDS in production)
- **Redis** - Session storage and conversation memory
- **Pinecone** - Vector embeddings for semantic search
  - Dense index (OpenAI embeddings)
  - Sparse index (keyword-based)

### Infrastructure

- **Docker** - Containerization
- **Docker Compose** - Local development orchestration
- **Caddy** - Reverse proxy and HTTPS termination
- **AWS Cognito** - User authentication and management
- **Alembic** - Database migration tool

### Development Tools

- **SQLAlchemy** (v2.0.41) - ORM and database toolkit
- **Pydantic** (v2.10.6) - Data validation and settings
- **pytest** - Testing framework

## Architecture Layers

The backend follows a layered architecture pattern:

### 1. API Layer (`api/`)

**Responsibility**: HTTP endpoint handlers, request/response validation

```
api/
├── account.py       # User account management
├── chat.py          # Chatbot endpoints
├── hikmah.py        # Hikmah tree elaboration
├── memory_admin.py  # Memory admin dashboard
└── reference.py     # Reference lookup
```

**Key Features**:
- JWT authentication via AWS Cognito
- Request validation with Pydantic models
- Streaming response support
- Error handling middleware

### 2. Core Layer (`core/`)

**Responsibility**: Business logic, AI pipelines, configuration

```
core/
├── pipeline.py           # Main AI pipelines
├── memory.py             # Redis conversation memory
├── config.py             # Environment configuration
├── auth.py               # JWT authentication logic
├── chat_models.py        # LLM model instances
├── prompt_templates.py   # System prompts
├── utils.py              # Utility functions
└── vectorstore.py        # Pinecone connection
```

**Key Features**:
- Orchestrates AI pipelines
- Manages Redis-backed conversation history
- Configures LLM models and prompts
- Handles authentication logic

### 3. Modules Layer (`modules/`)

**Responsibility**: AI pipeline components (RAG system)

```
modules/
├── classification/    # Query type classification
├── embedding/         # Dense + sparse embeddings
├── enhancement/       # Query enhancement
├── retrieval/         # Document retrieval
├── reranking/         # Result reranking
├── generation/        # Response generation
└── translation/       # Multi-language support
```

**Key Features**:
- Modular, reusable AI components
- Hybrid search (dense + sparse)
- Context-aware query enhancement
- Streaming generation

### 4. Agents Layer (`agents/`)

**Responsibility**: Agentic AI behaviors (memory system)

```
agents/
├── core/
│   ├── universal_memory_agent.py  # Universal memory agent
│   └── memory_consolidator.py     # Memory consolidation
├── models/
│   ├── user_memory_models.py      # SQLAlchemy models
│   └── db_config.py                # Database configuration
└── prompts/
    ├── memory_prompts.py           # Memory agent prompts
    └── note_templates.py           # Note templates
```

**Key Features**:
- Learns from user interactions
- Consolidates memory to prevent bloat
- Prevents duplicate notes
- Background processing

### 5. Database Layer (`db/`)

**Responsibility**: Data persistence, CRUD operations

```
db/
├── models/         # SQLAlchemy ORM models
├── schemas/        # Pydantic schemas
├── repositories/   # Data access layer
├── routers/        # CRUD API endpoints
├── crud/           # Legacy CRUD operations
└── session.py      # Database session management
```

**Key Features**:
- Repository pattern for data access
- Type-safe schemas with Pydantic
- RESTful CRUD endpoints
- Alembic migrations

### 6. Services Layer (`services/`)

**Responsibility**: Business logic services

```
services/
├── account_service.py          # Account operations
├── memory_service.py           # Memory operations
└── consolidation_service.py    # Memory consolidation
```

**Key Features**:
- Encapsulates complex business logic
- Reusable across multiple endpoints
- Transaction management

## Module Organization

### Separation of Concerns

The codebase follows **domain-driven design** principles:

1. **API Handlers** - Only handle HTTP concerns
2. **Core Logic** - Domain logic lives here
3. **Modules** - Reusable AI components
4. **Agents** - Autonomous behaviors
5. **Database** - Data persistence only
6. **Services** - Cross-cutting concerns

### Dependency Flow

```mermaid
graph LR
    API[API Layer] --> Core[Core Layer]
    API --> Services[Services]
    Core --> Modules[Modules]
    Core --> Agents[Agents]
    Services --> DB[Database]
    Agents --> DB
    Core --> DB
    Modules --> External[External APIs]
```

**Rule**: Lower layers never depend on upper layers.

## Data Flow

### Chat Pipeline Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Pipeline
    participant Classifier
    participant Enhancer
    participant Retriever
    participant Generator
    participant Redis
    participant Pinecone
    participant OpenAI
    
    Client->>API: POST /chat/stream
    API->>Pipeline: chat_pipeline_streaming()
    Pipeline->>Classifier: classify_query()
    Classifier->>OpenAI: Check if Islamic/Fiqh
    OpenAI-->>Classifier: Classification result
    
    alt Non-Islamic Query
        Classifier-->>Client: Rejection message
    else Valid Query
        Pipeline->>Enhancer: enhance_query()
        Enhancer->>Redis: Get chat history
        Redis-->>Enhancer: Recent messages
        Enhancer->>OpenAI: Enhance with context
        OpenAI-->>Enhancer: Enhanced query
        
        Pipeline->>Retriever: retrieve_documents()
        Retriever->>Pinecone: Dense + Sparse search
        Pinecone-->>Retriever: Relevant docs
        Retriever-->>Pipeline: Reranked results
        
        Pipeline->>Generator: generate_response_stream()
        Generator->>Redis: Get history
        Redis-->>Generator: Chat context
        Generator->>OpenAI: Stream generation
        OpenAI-->>Generator: Response chunks
        Generator-->>Client: Stream response
        Generator->>Redis: Save interaction
    end
```

### Hikmah Elaboration Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Pipeline
    participant Retriever
    participant Generator
    participant Thread
    participant MemoryAgent
    participant DB
    
    Client->>API: POST /hikmah/elaborate/stream
    API->>Pipeline: hikmah_elaboration_pipeline()
    Pipeline->>Retriever: retrieve_documents()
    Retriever-->>Pipeline: Relevant references
    
    Pipeline->>Generator: generate_elaboration_stream()
    Generator->>OpenAI: Stream elaboration
    OpenAI-->>Generator: Response chunks
    Generator-->>Client: Stream to client
    
    Note over Generator,Thread: After streaming completes
    Generator->>Thread: Spawn background thread
    Thread->>MemoryAgent: analyze_hikmah_elaboration()
    MemoryAgent->>DB: Get/create user profile
    DB-->>MemoryAgent: User memory profile
    MemoryAgent->>OpenAI: Analyze interaction
    OpenAI-->>MemoryAgent: Memory insights
    MemoryAgent->>DB: Save notes & events
    Thread-->>Generator: Complete (fire-and-forget)
```

### Memory Update Flow

```mermaid
graph TB
    Interaction[User Interaction] --> Agent[Memory Agent]
    Agent --> LLM[LLM Analysis]
    LLM --> Decision{Should Update?}
    
    Decision -->|No| Event1[Create Event: No Update]
    Decision -->|Yes| DupeCheck[Check Duplicates]
    
    DupeCheck --> Filter[Filter Duplicates]
    Filter --> AddNotes[Add Notes to Profile]
    AddNotes --> CheckSize{Check Note Count}
    
    CheckSize -->|Under Threshold| Event2[Create Event: Updated]
    CheckSize -->|Over Threshold| Consolidate[Trigger Consolidation]
    
    Consolidate --> LLMConsolidate[LLM Consolidates Notes]
    LLMConsolidate --> SaveConsolidation[Save Consolidation Record]
    SaveConsolidation --> Event2
    
    Event1 --> Commit[Commit Transaction]
    Event2 --> Commit
```

## Database Architecture

### Schema Overview

The database uses PostgreSQL with two main domains:

1. **Learning Platform Domain**
   - `users` - User accounts
   - `hikmah_trees` - Course structures
   - `lessons` - Individual lessons
   - `lesson_content` - Lesson content blocks
   - `user_progress` - User learning progress

2. **Memory System Domain**
   - `user_memory_profiles` - User memory profiles
   - `memory_events` - Interaction tracking
   - `memory_consolidations` - Consolidation history

### Entity Relationships

```mermaid
erDiagram
    USERS ||--o{ USER_PROGRESS : tracks
    HIKMAH_TREES ||--o{ LESSONS : contains
    LESSONS ||--o{ LESSON_CONTENT : has
    LESSONS ||--o{ USER_PROGRESS : tracks
    
    USER_MEMORY_PROFILES ||--o{ MEMORY_EVENTS : records
    USER_MEMORY_PROFILES ||--o{ MEMORY_CONSOLIDATIONS : undergoes
    
    USERS {
        bigint id PK
        text email
        text name
        timestamp created_at
    }
    
    HIKMAH_TREES {
        bigint id PK
        text title
        text summary
        text[] tags
        int skill_level
        jsonb meta
    }
    
    LESSONS {
        bigint id PK
        text slug
        text title
        text summary
        text[] tags
        bigint hikmah_tree_id FK
        int order_position
    }
    
    USER_MEMORY_PROFILES {
        text id PK
        text user_id UK
        json learning_notes
        json knowledge_notes
        json interest_notes
        json behavior_notes
        json preference_notes
        int memory_version
    }
    
    MEMORY_EVENTS {
        text id PK
        text user_memory_profile_id FK
        text event_type
        json event_data
        text processing_status
        json notes_added
    }
```

See [Database Documentation](DATABASE.md) for complete schema details.

## AI Pipeline Architecture

### Hybrid Retrieval System

The system uses a hybrid approach combining:

1. **Dense Retrieval** - Semantic similarity via OpenAI embeddings
2. **Sparse Retrieval** - Keyword matching via BM25-style sparse vectors
3. **Re-ranking** - Weighted combination of both results

```mermaid
graph LR
    Query[User Query] --> Dense[Dense Vectorstore]
    Query --> Sparse[Sparse Vectorstore]
    
    Dense -->|Top 20 docs| Reranker
    Sparse -->|Top 20 docs| Reranker
    
    Reranker[Reranker<br/>80% dense, 20% sparse] --> Results[Top N Results]
```

### Classification System

Multi-stage query classification:

1. **Islamic Relevance** - Is the query about Islam?
2. **Fiqh Detection** - Does it require a religious ruling?

```mermaid
graph TD
    Query[User Query] --> IsIslamic{Is Islamic?}
    IsIslamic -->|No| Reject[Reject Query]
    IsIslamic -->|Yes| IsFiqh{Is Fiqh?}
    IsFiqh -->|Yes| Defer[Defer to Scholar]
    IsFiqh -->|No| Process[Process Query]
```

### Generation Pipeline

```mermaid
graph LR
    Context[Retrieved Context] --> Prompt[System Prompt]
    History[Chat History] --> Prompt
    Query[User Query] --> Prompt
    
    Prompt --> LLM[OpenAI GPT-4]
    LLM --> Stream[Streaming Response]
    Stream --> Client[Client]
    Stream --> Save[Save to Redis]
```

## Memory System Architecture

### Universal Memory Agent

The memory agent is **interaction-agnostic** and can process:

- Chat conversations
- Lesson completions
- Quiz results
- Hikmah elaboration requests
- User feedback
- And any future interaction types

### Note Categories

Memory is organized into 5 categories:

1. **Learning Notes** - What user is studying, current focus
2. **Knowledge Notes** - What user knows/doesn't know
3. **Interest Notes** - Topics that engage the user
4. **Behavior Notes** - Learning patterns and habits
5. **Preference Notes** - Learning style preferences

### Consolidation Strategy

When notes exceed threshold (e.g., 100 notes), the system:

1. Identifies redundant notes
2. Merges similar observations
3. Creates summary notes
4. Removes outdated information

See [Memory Agent Documentation](MEMORY_AGENT.md) for details.

## Deployment Architecture

### Docker Compose Setup

```mermaid
graph TB
    subgraph DockerNetwork[Docker Network]
        Caddy[Caddy<br/>Reverse Proxy<br/>:80,:443]
        Backend[FastAPI Backend<br/>:8000]
    end
    
    subgraph External[External Services]
        PostgreSQL[(PostgreSQL RDS)]
        Redis[(Redis)]
        Pinecone[(Pinecone)]
        OpenAI[OpenAI API]
        Cognito[AWS Cognito]
    end
    
    Internet[Internet] --> Caddy
    Caddy --> Backend
    Backend --> PostgreSQL
    Backend --> Redis
    Backend --> Pinecone
    Backend --> OpenAI
    Backend --> Cognito
```

### Production Deployment (EC2)

- **Application**: Docker containers on EC2
- **Database**: PostgreSQL RDS
- **Cache**: Redis (ElastiCache or self-hosted)
- **Vector DB**: Pinecone (SaaS)
- **Auth**: AWS Cognito
- **Proxy**: Caddy for HTTPS termination

See [Deployment Documentation](DEPLOYMENT.md) for complete guide.

## Design Patterns

### Repository Pattern

Data access is abstracted through repositories:

```python
# Repository handles all database operations
class MemoryProfileRepository:
    def get_by_user_id(self, db: Session, user_id: str) -> UserMemoryProfile:
        pass
    
    def create(self, db: Session, user_id: str, defaults: dict) -> UserMemoryProfile:
        pass
```

### Service Layer Pattern

Complex business logic lives in services:

```python
# Service coordinates multiple repositories and logic
class MemoryService:
    def __init__(self, db: Session):
        self.profile_repo = MemoryProfileRepository()
        self.event_repo = MemoryEventRepository()
    
    def add_notes(self, profile: UserMemoryProfile, notes: List[Dict]):
        # Complex logic here
        pass
```

### Dependency Injection

FastAPI's dependency injection for database sessions:

```python
@router.get("/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    # db session automatically injected
    pass
```

### Streaming Response Pattern

For real-time user experience:

```python
async def generate_stream():
    for chunk in llm.stream(...):
        yield chunk

return StreamingResponse(generate_stream(), media_type="text/event-stream")
```

## Performance Considerations

### Redis for Session Storage

- **TTL-based expiration** prevents memory bloat
- **Message limit** (default: 30 messages) keeps context manageable
- **Key prefixes** enable multi-tenant support

### Background Processing

- **Fire-and-forget threads** for memory updates
- **Daemon threads** don't block shutdown
- **Separate event loops** prevent conflicts

### Vector Search Optimization

- **Sect filtering** at Pinecone query level
- **Reranking** reduces LLM input tokens
- **Cached embeddings** in Pinecone

### Database Connection Pooling

- SQLAlchemy connection pool
- Single source of truth for database config
- Reused across application and agents

## Security

### Authentication

- JWT tokens via AWS Cognito
- Token validation with JWKS
- Protected endpoints with `Depends(auth)`

### CORS

- Environment-based allowed origins
- Credentials support for cookies
- Development localhost exemptions

### Database

- Parameterized queries (SQL injection prevention)
- Connection string from environment
- No credentials in code

## Monitoring & Debugging

### Health Endpoints

- `GET /health` - Basic health check
- `GET /_debug/db` - Database connectivity
- `GET /_routes` - List all routes

### Logging

- Structured logging with `logging_config.py`
- Memory agent debug logs
- LLM interaction logging

### Memory Admin Dashboard

Interactive web UI at `/admin/memory/dashboard` for:
- Inspecting user memory profiles
- Viewing memory events
- Debugging consolidation

See [Memory Agent Documentation](MEMORY_AGENT.md) for dashboard usage.

## See Also

- [Chatbot Documentation](CHATBOT.md) - RAG pipeline details
- [AI Pipeline Documentation](AI_PIPELINE.md) - Module-by-module breakdown
- [Database Documentation](DATABASE.md) - Schema and migrations
- [Deployment Documentation](DEPLOYMENT.md) - Production setup
- [API Reference](API_REFERENCE.md) - Complete endpoint documentation
