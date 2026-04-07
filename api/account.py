"""
Account management API endpoints.

This module provides endpoints for user account management,
including account deletion.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import httpx
import logging

from models.JWTBearer import JWTAuthorizationCredentials
from core.auth import auth
from db.session import get_db
from core.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from services.account_service import delete_user_data, clear_user_redis_sessions, AccountDeletionError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/account",
    tags=["account"]
)


@router.delete("/me", status_code=204)
async def delete_my_account(
    credentials: JWTAuthorizationCredentials = Depends(auth),
    db: Session = Depends(get_db)
):
    """
    Delete the authenticated user's account.

    This endpoint:
    1. Extracts the user's sub (UUID) from the JWT token
    2. Deletes all user-related data from the database (progress, memory, etc.)
    3. Clears Redis session data
    4. Deletes the user from Supabase Auth via Admin API

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 500 if database deletion fails, 403 if token is invalid
    """
    # Extract user_id from JWT claims
    user_id = credentials.claims.get("sub")
    if not user_id:
        logger.error("JWT token missing 'sub' claim")
        raise HTTPException(
            status_code=403,
            detail="Invalid token: missing user identifier"
        )

    logger.info(f"Account deletion requested for user: {user_id}")

    # Debug: Log all JWT claims to identify available fields
    logger.info(f"JWT Claims for user {user_id}: {credentials.claims}")

    # Step 1: Delete all user data from database
    try:
        deleted_counts = delete_user_data(user_id, db)
        logger.info(f"Database deletion successful for user {user_id}: {deleted_counts}")
    except AccountDeletionError as e:
        logger.error(f"Database deletion failed for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete user data from database"
        )

    # Step 2: Clear Redis sessions (best effort)
    try:
        sessions_cleared = clear_user_redis_sessions(user_id)
        if sessions_cleared > 0:
            logger.info(f"Cleared {sessions_cleared} Redis sessions for user {user_id}")
    except Exception as e:
        # Log but don't fail - this is not critical
        logger.warning(f"Redis cleanup failed for user {user_id}: {str(e)}")

    # Step 3: Delete user from Supabase Auth using Admin API
    try:
        response = httpx.delete(
            f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"},
        )
        if response.status_code == 404:
            # User not found in Supabase Auth — treat as success (already deleted)
            logger.warning(f"Supabase user {user_id} not found during deletion (already removed?)")
        elif not response.is_success:
            logger.error(
                f"Supabase Admin API deletion failed for user {user_id}: "
                f"HTTP {response.status_code} — {response.text}"
            )
        else:
            logger.info(f"Successfully deleted user {user_id} from Supabase Auth")
    except Exception as e:
        # Log unexpected errors but don't fail — DB data is already deleted
        logger.error(f"Unexpected error during Supabase Auth deletion for user {user_id}: {str(e)}")

    logger.info(f"Account deletion completed for user {user_id}")
    return None  # 204 No Content


@router.get("/me", tags=["account"])
async def get_my_account_info(
    credentials: JWTAuthorizationCredentials = Depends(auth)
):
    """
    Get information about the authenticated user from their JWT token.

    This is a utility endpoint that returns the claims from the user's JWT token.
    Useful for debugging and verifying authentication.

    Returns:
        dict: user_id (sub), email, and full claims dict
    """
    user_id = credentials.claims.get("sub")
    email = credentials.claims.get("email")

    return {
        "user_id": user_id,
        "email": email,
        "claims": credentials.claims
    }
