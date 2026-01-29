# Database - Schema and Data Layer

The Deen backend uses PostgreSQL for structured data storage with SQLAlchemy ORM and Alembic for migrations.

## Table of Contents

- [Overview](#overview)
- [Database Configuration](#database-configuration)
- [Core Schema](#core-schema)
- [Memory System Schema](#memory-system-schema)
- [Repositories](#repositories)
- [Migrations](#migrations)
- [CRUD Operations](#crud-operations)

## Overview

### Database Stack

- **Database**: PostgreSQL 14+
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Connection Pooling**: SQLAlchemy engine
- **Session Management**: Dependency injection

### Two Main Domains

1. **Learning Platform** - Courses, lessons, user progress
2. **Memory System** - User memory profiles, events, consolidations

## Database Configuration

### Single Source of Truth

**Important**: The application uses a **single database configuration** to avoid credential caching issues.

**File**: `db/session.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from db.config import settings

# Build DATABASE_URL from settings
DATABASE_URL = settings.DATABASE_URL or settings.build_database_url()

# Create engine (single source of truth)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base for declarative models
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Environment Variables

```bash
# Option 1: Full DATABASE_URL
DATABASE_URL=postgresql://user:password@localhost:5432/deen

# Option 2: Individual components (auto-builds URL)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=deen
DB_USER=your_user
DB_PASSWORD=your_password
```

### Agent Configuration

**File**: `agents/models/db_config.py`

```python
# Reuses main app's database engine (no separate config)
from db.session import engine, SessionLocal, get_db
from db.config import settings

# Now agents use the same engine as main app
# No credential caching issues!
```

See `updates_documentation/DATABASE_CONFIG_CONSOLIDATION.md` for details on this fix.

## Core Schema

### Entity Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ USER_PROGRESS : tracks
    HIKMAH_TREES ||--o{ LESSONS : contains
    LESSONS ||--o{ LESSON_CONTENT : has
    LESSONS ||--o{ USER_PROGRESS : tracks
    USER_PROGRESS }o--|| LESSON_CONTENT : references
    
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
        text_array tags
        int skill_level
        jsonb meta
        timestamp created_at
        timestamp updated_at
    }
    
    LESSONS {
        bigint id PK
        text slug UK
        text title
        text summary
        text_array tags
        text status
        text language_code
        bigint author_user_id
        int estimated_minutes
        timestamp published_at
        bigint hikmah_tree_id FK
        int order_position
        timestamp created_at
        timestamp updated_at
    }
    
    LESSON_CONTENT {
        bigint id PK
        bigint lesson_id FK
        text content_type
        text content
        int order_position
        jsonb meta
        timestamp created_at
        timestamp updated_at
    }
    
    USER_PROGRESS {
        bigint id PK
        string user_id
        bigint hikmah_tree_id FK
        bigint lesson_id FK
        bigint content_id FK
        boolean is_completed
        numeric percent_complete
        int last_position
        text notes
        jsonb meta
        timestamp created_at
        timestamp updated_at
    }
```

### hikmah_trees Table

**File**: `db/models/hikmah_trees.py`

```sql
CREATE TABLE hikmah_trees (
    id BIGSERIAL PRIMARY KEY,
    title TEXT,
    summary TEXT,
    tags TEXT[],
    skill_level INTEGER,  -- 1-10 scale
    meta JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Python Model**:
```python
class HikmahTree(Base):
    __tablename__ = "hikmah_trees"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(Text)
    summary = Column(Text)
    tags = Column(ARRAY(Text))
    skill_level = Column(Integer)
    meta = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
```

### lessons Table

**File**: `db/models/lessons.py`

```sql
CREATE TABLE lessons (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT UNIQUE,
    title TEXT NOT NULL,
    summary TEXT,
    tags TEXT[],
    status TEXT,
    language_code TEXT,
    author_user_id BIGINT,
    estimated_minutes INTEGER,
    published_at TIMESTAMP WITH TIME ZONE,
    hikmah_tree_id BIGINT,
    order_position INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### lesson_content Table

**File**: `db/models/lesson_content.py`

```sql
CREATE TABLE lesson_content (
    id BIGSERIAL PRIMARY KEY,
    lesson_id BIGINT,
    content_type TEXT,
    content TEXT,
    order_position INTEGER,
    meta JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### user_progress Table

**File**: `db/models/user_progress.py`

```sql
CREATE TABLE user_progress (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    hikmah_tree_id BIGINT,
    lesson_id BIGINT,
    content_id BIGINT,
    is_completed BOOLEAN DEFAULT FALSE,
    percent_complete NUMERIC(5,2),
    last_position INTEGER,
    notes TEXT,
    meta JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_progress_user_id ON user_progress(user_id);
```

## Memory System Schema

### user_memory_profiles Table

**File**: `agents/models/user_memory_models.py`

```sql
CREATE TABLE user_memory_profiles (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR UNIQUE NOT NULL,
    display_name VARCHAR,
    preferred_language VARCHAR DEFAULT 'english',
    timezone VARCHAR,
    
    -- Memory storage (JSON arrays)
    learning_notes JSON DEFAULT '[]',
    interest_notes JSON DEFAULT '[]',
    knowledge_notes JSON DEFAULT '[]',
    behavior_notes JSON DEFAULT '[]',
    preference_notes JSON DEFAULT '[]',
    
    -- Metadata
    total_interactions INTEGER DEFAULT 0,
    last_significant_update TIMESTAMP,
    memory_version INTEGER DEFAULT 1,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_memory_profiles_user_id ON user_memory_profiles(user_id);
```

**Note Structure** (stored in JSON):
```json
{
  "id": "uuid",
  "content": "User struggles with Wilayah concept",
  "evidence": "Requested elaboration 3 times",
  "confidence": 0.85,
  "category": "learning_gap",
  "tags": ["wilayah", "imamate"],
  "note_type": "knowledge_notes",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### memory_events Table

```sql
CREATE TABLE memory_events (
    id VARCHAR PRIMARY KEY,
    user_memory_profile_id VARCHAR NOT NULL,
    
    -- Event details
    event_type VARCHAR NOT NULL,
    event_data JSON NOT NULL,
    trigger_context JSON,
    
    -- Processing results
    notes_added JSON DEFAULT '[]',
    memory_updates JSON DEFAULT '[]',
    processing_reasoning TEXT,
    processing_status VARCHAR DEFAULT 'pending',
    
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    
    FOREIGN KEY (user_memory_profile_id) REFERENCES user_memory_profiles(id)
);
```

### memory_consolidations Table

```sql
CREATE TABLE memory_consolidations (
    id VARCHAR PRIMARY KEY,
    user_memory_profile_id VARCHAR NOT NULL,
    
    -- Consolidation details
    consolidation_type VARCHAR NOT NULL,
    notes_before_count INTEGER,
    notes_after_count INTEGER,
    
    -- What changed
    consolidated_notes JSON,
    removed_notes JSON,
    new_summary_notes JSON,
    
    consolidation_reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (user_memory_profile_id) REFERENCES user_memory_profiles(id)
);
```

## Repositories

### Repository Pattern

The application uses the **Repository Pattern** to abstract database operations.

**Benefits**:
- Decouples business logic from database
- Easier testing (mock repositories)
- Consistent data access patterns
- Single place to optimize queries

### Memory Profile Repository

**File**: `db/repositories/memory_profile_repository.py`

```python
class MemoryProfileRepository:
    def get_by_user_id(self, db: Session, user_id: str) -> Optional[UserMemoryProfile]:
        """Get user memory profile by user_id"""
        return db.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()
    
    def create(self, db: Session, user_id: str, defaults: dict) -> UserMemoryProfile:
        """Create new memory profile"""
        profile = UserMemoryProfile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            **defaults
        )
        db.add(profile)
        db.flush()  # Get ID without committing
        return profile
    
    def update_note_lists(self, db: Session, profile: UserMemoryProfile, **kwargs):
        """Update note arrays"""
        for key, value in kwargs.items():
            setattr(profile, key, value)
        db.flush()
```

### CRUD Repositories

**Location**: `db/crud/`

Generic CRUD operations for each model:

```python
# db/crud/hikmah_trees.py
def get_hikmah_tree(db: Session, tree_id: int):
    return db.query(HikmahTree).filter(HikmahTree.id == tree_id).first()

def create_hikmah_tree(db: Session, tree: HikmahTreeCreate):
    db_tree = HikmahTree(**tree.dict())
    db.add(db_tree)
    db.commit()
    db.refresh(db_tree)
    return db_tree
```

## Migrations

### Alembic Setup

**Configuration**: `alembic.ini`

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://user:password@localhost/deen

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
```

### Migration Files

**Location**: `alembic/versions/`

Example migration:

```python
# alembic/versions/a12c6d22b9d9_make_hikmah_tree_id_nullable.py

def upgrade():
    op.alter_column('lessons', 'hikmah_tree_id',
                    existing_type=sa.BigInteger(),
                    nullable=True)

def downgrade():
    op.alter_column('lessons', 'hikmah_tree_id',
                    existing_type=sa.BigInteger(),
                    nullable=False)
```

### Common Commands

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Revert last migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history --verbose
```

### Best Practices

1. **Always review auto-generated migrations** - Alembic isn't perfect
2. **Test migrations on dev database first**
3. **Include both upgrade() and downgrade()**
4. **Use descriptive migration names**
5. **Commit migrations to version control**

## CRUD Operations

### Using Dependency Injection

FastAPI endpoints use dependency injection for database sessions:

```python
@router.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson
```

### Transaction Management

**Service Layer** controls transactions:

```python
class MemoryService:
    def __init__(self, db: Session):
        self.db = db
    
    def add_notes(self, profile, notes):
        # Multiple operations in one transaction
        self.profile_repo.update_note_lists(self.db, profile, ...)
        self.event_repo.create(self.db, ...)
        # No commit here - caller controls transaction
    
    def commit(self):
        self.db.commit()
    
    def rollback(self):
        self.db.rollback()
```

**Agent Layer** commits:

```python
try:
    # Do work
    memory_service.add_notes(...)
    
    # Commit if successful
    memory_service.commit()
except Exception:
    # Rollback on error
    memory_service.rollback()
    raise
```

### Query Optimization

**Use Joins**:
```python
# Bad: N+1 query problem
lessons = db.query(Lesson).all()
for lesson in lessons:
    tree = lesson.hikmah_tree  # Separate query for each!

# Good: Single query with join
lessons = db.query(Lesson).options(
    joinedload(Lesson.hikmah_tree)
).all()
```

**Use Filters Efficiently**:
```python
# Good: Index on user_id
progress = db.query(UserProgress).filter(
    UserProgress.user_id == user_id
).all()
```

**Limit Results**:
```python
# Get only what you need
recent_events = db.query(MemoryEvent).order_by(
    MemoryEvent.created_at.desc()
).limit(50).all()
```

## Connection Pooling

### Configuration

```python
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Test connections before use
    pool_size=10,             # Number of connections in pool
    max_overflow=20,          # Additional connections if needed
    pool_recycle=3600,        # Recycle connections after 1 hour
    echo=False                # Set True for SQL logging
)
```

### Pool Settings

- **pool_size=10**: Base pool of 10 connections
- **max_overflow=20**: Can grow to 30 total connections
- **pool_pre_ping=True**: Validates connection before use (prevents stale connections)
- **pool_recycle=3600**: Recycles connections hourly (prevents timeout issues)

## Database Utilities

### Health Check

```python
@app.get("/_debug/db")
def db_ping():
    """Test database connectivity"""
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version();")).scalar()
    return {"ok": True, "version": version}
```

### Create Tables

```python
# One-time setup (use Alembic in production)
from db.session import Base, engine
Base.metadata.create_all(bind=engine)
```

## Troubleshooting

### Common Issues

**Connection Refused**:
```
sqlalchemy.exc.OperationalError: could not connect to server
```
- Check PostgreSQL is running
- Verify DATABASE_URL is correct
- Check firewall/network settings

**Authentication Failed**:
```
password authentication failed for user "postgres"
```
- Verify DB_PASSWORD in .env
- Restart application after changing credentials
- Check database user exists

**Too Many Connections**:
```
FATAL: remaining connection slots are reserved
```
- Reduce pool_size and max_overflow
- Check for connection leaks (not closing sessions)
- Increase max_connections in PostgreSQL

**Stale Connections**:
```
server closed the connection unexpectedly
```
- Enable pool_pre_ping=True
- Reduce pool_recycle time
- Check PostgreSQL logs

### Debugging Queries

Enable SQL logging:

```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Or in create_engine
engine = create_engine(DATABASE_URL, echo=True)
```

## See Also

- [Architecture Documentation](ARCHITECTURE.md) - Database in system context
- [Memory Agent Documentation](MEMORY_AGENT.md) - Memory schema usage
- [API Reference](API_REFERENCE.md) - CRUD API endpoints
- [Deployment Documentation](DEPLOYMENT.md) - Production database setup
