"""
Database configuration for the memory agent system.

IMPORTANT: This module now uses the same database configuration as the main application
(db/session.py and db/config.py) to avoid duplicate engine creation and credential caching issues.

This ensures:
1. Single source of truth for database credentials
2. Automatic credential updates when .env changes (after app restart)
3. Consistent connection pooling across the entire application
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the main application's database configuration
# This ensures we use the SAME engine and session makers as the rest of the app
from db.session import engine, SessionLocal, get_db, Base as MainBase
from db.config import settings

# Re-export for backward compatibility with existing code
from .user_memory_models import Base as MemoryBase

# Verify database configuration is available
if not settings.DATABASE_URL:
    raise ValueError(
        "Database configuration is missing. Please check your .env file and ensure "
        "DB_HOST, DB_NAME, DB_USER, and DB_PASSWORD are set."
    )

# Note: We no longer create separate engines here - we reuse the main app's engine
# This prevents credential caching issues and ensures consistency

# Initialize memory-specific database tables
def init_db():
    """Create all memory-related tables using the main app's engine"""
    MemoryBase.metadata.create_all(bind=engine)

# For backward compatibility, keep these available
DATABASE_URL = settings.DATABASE_URL
