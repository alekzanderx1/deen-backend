from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..session import get_db
from ..crud.lesson_content import lesson_content_crud
from ..models.lesson_content import LessonContent
from ..schemas.lesson_content import LessonContentCreate, LessonContentRead, LessonContentUpdate

router = APIRouter(prefix="/lesson-content", tags=["lesson_content"])

@router.post("", response_model=LessonContentRead)
def create_lesson_content(payload: LessonContentCreate, db: Session = Depends(get_db)):
    return lesson_content_crud.create(db, payload)

@router.get("", response_model=List[LessonContentRead])
def list_lesson_content(
    db: Session = Depends(get_db),
    lesson_id: Optional[int] = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
):
    q = db.query(LessonContent)
    if lesson_id is not None:
        q = q.filter(LessonContent.lesson_id == lesson_id)
    q = q.order_by(LessonContent.order_position.asc(), LessonContent.id.asc())
    return q.offset(skip).limit(limit).all()

@router.get("/{content_id}", response_model=LessonContentRead)
def get_lesson_content(content_id: int, db: Session = Depends(get_db)):
    obj = lesson_content_crud.get(db, content_id)
    if not obj:
        raise HTTPException(404, "Lesson content not found")
    return obj

@router.patch("/{content_id}", response_model=LessonContentRead)
def update_lesson_content(content_id: int, payload: LessonContentUpdate, db: Session = Depends(get_db)):
    obj = lesson_content_crud.get(db, content_id)
    if not obj:
        raise HTTPException(404, "Lesson content not found")
    return lesson_content_crud.update(db, obj, payload)

@router.delete("/{content_id}", status_code=204)
def delete_lesson_content(content_id: int, db: Session = Depends(get_db)):
    obj = lesson_content_crud.get(db, content_id)
    if not obj:
        raise HTTPException(404, "Lesson content not found")
    lesson_content_crud.delete(db, obj)
    return
