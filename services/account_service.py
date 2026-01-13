"""
Account management service for user account deletion.

This service handles the deletion of all user-related data from the database,
including user progress, memory profiles, events, and consolidations.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


class AccountDeletionError(Exception):
    """Raised when account deletion fails"""
    pass


def delete_user_data(user_id: str, db: Session) -> dict:
    """
    Delete all user-related data from the database.
    
    This function deletes records from all tables that contain user data:
    1. memory_events (references user_memory_profiles)
    2. memory_consolidations (references user_memory_profiles)
    3. user_memory_profiles (has user_id)
    4. user_progress (has user_id)
    5. users table (optional, if user exists there)
    
    Args:
        user_id: The Cognito sub (UUID) of the user to delete
        db: SQLAlchemy database session
        
    Returns:
        dict: Summary of deleted records
        
    Raises:
        AccountDeletionError: If deletion fails
    """
    try:
        deleted_counts = {
            "memory_events": 0,
            "memory_consolidations": 0,
            "user_memory_profiles": 0,
            "user_progress": 0,
            "users": 0
        }
        
        # Step 1: Find user_memory_profile_id(s) for this user
        profile_result = db.execute(
            text("SELECT id FROM user_memory_profiles WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        profile_ids = [row[0] for row in profile_result.fetchall()]
        
        if profile_ids:
            logger.info(f"Found {len(profile_ids)} memory profile(s) for user {user_id}")
            
            # Step 2: Delete memory_events for these profiles
            for profile_id in profile_ids:
                result = db.execute(
                    text("DELETE FROM memory_events WHERE user_memory_profile_id = :profile_id"),
                    {"profile_id": profile_id}
                )
                deleted_counts["memory_events"] += result.rowcount
            
            # Step 3: Delete memory_consolidations for these profiles
            for profile_id in profile_ids:
                result = db.execute(
                    text("DELETE FROM memory_consolidations WHERE user_memory_profile_id = :profile_id"),
                    {"profile_id": profile_id}
                )
                deleted_counts["memory_consolidations"] += result.rowcount
            
            # Step 4: Delete user_memory_profiles
            result = db.execute(
                text("DELETE FROM user_memory_profiles WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            deleted_counts["user_memory_profiles"] = result.rowcount
        
        # Step 5: Delete user_progress records
        result = db.execute(
            text("DELETE FROM user_progress WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        deleted_counts["user_progress"] = result.rowcount
        
        # Step 6: Delete from users table (if exists)
        # Note: The users table uses email, not Cognito sub, so we skip this
        # unless we can find a mapping. For now, we'll try to delete by email
        # if the user_id looks like an email, otherwise skip.
        if "@" in user_id:
            result = db.execute(
                text("DELETE FROM users WHERE email = :email"),
                {"email": user_id}
            )
            deleted_counts["users"] = result.rowcount
        
        # Commit the transaction
        db.commit()
        
        logger.info(f"Successfully deleted user data for {user_id}: {deleted_counts}")
        return deleted_counts
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete user data for {user_id}: {str(e)}")
        raise AccountDeletionError(f"Database deletion failed: {str(e)}")


def clear_user_redis_sessions(user_id: str) -> int:
    """
    Clear Redis session data for the user.
    
    This function attempts to clear chat history stored in Redis for sessions
    that belong to the user. Session IDs typically follow the pattern "user_id:*"
    
    Args:
        user_id: The Cognito sub (UUID) of the user
        
    Returns:
        int: Number of sessions cleared
        
    Note:
        This is a best-effort operation. If Redis is unavailable or sessions
        don't follow the expected pattern, this will fail silently.
    """
    try:
        import redis
        from core.config import REDIS_URL, KEY_PREFIX
        
        r = redis.from_url(REDIS_URL)
        
        # Find all keys matching the user's session pattern
        pattern = f"{KEY_PREFIX}:{user_id}:*"
        keys = r.keys(pattern)
        
        if keys:
            deleted = r.delete(*keys)
            logger.info(f"Cleared {deleted} Redis sessions for user {user_id}")
            return deleted
        else:
            logger.info(f"No Redis sessions found for user {user_id}")
            return 0
            
    except Exception as e:
        logger.warning(f"Failed to clear Redis sessions for user {user_id}: {str(e)}")
        # Don't raise - this is a best-effort cleanup
        return 0
