from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..session import get_db
from ..crud.user_progress import user_progress_crud
from ..models.user_progress import UserProgress
from ..schemas.user_progress import UserProgressCreate, UserProgressRead, UserProgressUpdate

router = APIRouter(prefix="/user-progress", tags=["user_progress"])

@router.post("", response_model=UserProgressRead)
def create_user_progress(payload: UserProgressCreate, db: Session = Depends(get_db)):
    return user_progress_crud.create(db, payload)

@router.get("", response_model=List[UserProgressRead])
def list_user_progress(
    db: Session = Depends(get_db),
    user_id: Optional[int] = None,
    lesson_id: Optional[int] = None,
    content_id: Optional[int] = None,
    skip: int = 0,
    limit: int = Query(200, le=1000),
):
    q = db.query(UserProgress)
    if user_id is not None:
        q = q.filter(UserProgress.user_id == user_id)
    if lesson_id is not None:
        q = q.filter(UserProgress.lesson_id == lesson_id)
    if content_id is not None:
        q = q.filter(UserProgress.content_id == content_id)
    q = q.order_by(UserProgress.updated_at.desc())
    return q.offset(skip).limit(limit).all()

@router.get("/{progress_id}", response_model=UserProgressRead)
def get_user_progress(progress_id: int, db: Session = Depends(get_db)):
    obj = user_progress_crud.get(db, progress_id)
    if not obj:
        raise HTTPException(404, "User progress not found")
    return obj

@router.patch("/{progress_id}", response_model=UserProgressRead)
def update_user_progress(progress_id: int, payload: UserProgressUpdate, db: Session = Depends(get_db)):
    obj = user_progress_crud.get(db, progress_id)
    if not obj:
        raise HTTPException(404, "User progress not found")
    return user_progress_crud.update(db, obj, payload)

@router.delete("/{progress_id}", status_code=204)
def delete_user_progress(progress_id: int, db: Session = Depends(get_db)):
    obj = user_progress_crud.get(db, progress_id)
    if not obj:
        raise HTTPException(404, "User progress not found")
    user_progress_crud.delete(db, obj)
    return
