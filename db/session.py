from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# Set echo to False to avoid SQL statement noise in logs
engine = create_engine(
    settings.DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    echo=False,
    connect_args={"sslmode": "require"},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
