"""
Onboarding API endpoints.

Persists user onboarding preferences (tradition, goals, knowledge level, topics)
collected across pages 3–6 of the frontend onboarding flow.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from models.JWTBearer import JWTAuthorizationCredentials
from core.auth import auth
from db.session import get_db
from db.schemas.user_onboarding_profiles import OnboardingSubmitRequest, OnboardingRead
import db.crud.user_onboarding_profiles as onboarding_crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("", response_model=OnboardingRead)
def submit_onboarding(
    payload: OnboardingSubmitRequest,
    credentials: JWTAuthorizationCredentials = Depends(auth),
    db: Session = Depends(get_db),
):
    """
    Submit or update onboarding answers for the authenticated user.

    Performs an idempotent upsert — calling this multiple times with updated
    answers is safe and will overwrite the previous submission.
    """
    user_id = credentials.claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=403, detail="Invalid token: missing user identifier")

    profile = onboarding_crud.upsert(db, user_id, payload)
    return profile


@router.get("/me", response_model=OnboardingRead)
def get_onboarding(
    credentials: JWTAuthorizationCredentials = Depends(auth),
    db: Session = Depends(get_db),
):
    """
    Retrieve the authenticated user's onboarding answers.

    Returns 404 if the user has not yet completed onboarding.
    """
    user_id = credentials.claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=403, detail="Invalid token: missing user identifier")

    profile = onboarding_crud.get_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Onboarding not completed")
    return profile
