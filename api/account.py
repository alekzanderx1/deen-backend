"""
Account management API endpoints.

This module provides endpoints for user account management,
including account deletion.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import boto3
from botocore.exceptions import ClientError
import logging

from models.JWTBearer import JWTAuthorizationCredentials
from core.auth import auth
from db.session import get_db
from core.config import COGNITO_REGION, COGNITO_POOL_ID
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
    1. Extracts the user's Cognito sub (UUID) from the JWT token
    2. Deletes all user-related data from the database (progress, memory, etc.)
    3. Clears Redis session data
    4. Deletes the user from AWS Cognito
    
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
    
    # Step 3: Delete user from AWS Cognito using AdminDeleteUser
    # This uses the IAM role attached to the EC2 instance (no access keys needed)
    try:
        cognito_client = boto3.client('cognito-idp', region_name=COGNITO_REGION)
        
        # Get the username from JWT claims
        # Try multiple possible claim fields in order of preference
        cognito_username = (
            credentials.claims.get("cognito:username") or 
            credentials.claims.get("username") or
            credentials.claims.get("email") or
            credentials.claims.get("preferred_username")
        )
        
        logger.info(f"Attempting Cognito deletion with username: {cognito_username}")
        
        # if not cognito_username:
        #     logger.error(f"Cannot determine Cognito username for user {user_id}. Available claims: {list(credentials.claims.keys())}")
        #     raise ValueError("Missing username in JWT claims")
        
        # Use AdminDeleteUser which works with IAM credentials
        cognito_client.admin_delete_user(
            UserPoolId=COGNITO_POOL_ID,
            Username=cognito_username
        )
        logger.info(f"Successfully deleted user {cognito_username} (sub: {user_id}) from Cognito")
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        
        # Log the error but don't fail the request since database data is already deleted
        logger.error(f"Cognito deletion failed for user {user_id}: {error_code} - {error_message}")
        
        # If the user is already deleted from Cognito, that's okay
        if error_code not in ['UserNotFoundException']:
            logger.warning(f"Unexpected Cognito error during deletion: {error_code}")
    except Exception as e:
        # Log unexpected errors but don't fail
        logger.error(f"Unexpected error during Cognito deletion for user {user_id}: {str(e)}")
    
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
        dict: JWT claims including user_id (sub), email, etc.
    """
    user_id = credentials.claims.get("sub")
    email = credentials.claims.get("email")
    username = credentials.claims.get("cognito:username")
    
    return {
        "user_id": user_id,
        "email": email,
        "username": username,
        "claims": credentials.claims
    }
