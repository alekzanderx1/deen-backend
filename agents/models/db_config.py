from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from .user_memory_models import Base
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from core.config import FINAL_DATABASE_URL, FINAL_ASYNC_DATABASE_URL

# Database configuration
DATABASE_URL = FINAL_DATABASE_URL
ASYNC_DATABASE_URL = FINAL_ASYNC_DATABASE_URL

if not DATABASE_URL:
    raise ValueError("Database configuration is missing. Please check your .env file and ensure either DATABASE_URL or individual DB components (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD) are set.")

# Create engines with connection pooling optimized for threading
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,   # Recycle connections after 1 hour
    pool_size=10,        # Connection pool size
    max_overflow=20,      # Max connections beyond pool_size
    connect_args={"sslmode": "require"}
)
async_engine = create_async_engine(ASYNC_DATABASE_URL or DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))

# Create session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Dependency for FastAPI
def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    """Dependency to get async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Initialize database tables
def init_db():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

async def init_async_db():
    """Create all tables asynchronously"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
