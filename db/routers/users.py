from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..session import get_db
from ..crud.users import user_crud
from ..models.users import User
from ..schemas.users import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=UserRead)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    return user_crud.create(db, payload)

@router.get("", response_model=List[UserRead])
def list_users(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Search by display_name or email"),
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
):
    query = db.query(User)
    if q:
        like = f"%{q}%"
        query = query.filter((User.display_name.ilike(like)) | (User.email.ilike(like)))
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    query = query.order_by(User.id.asc())
    return query.offset(skip).limit(limit).all()

@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    obj = user_crud.get(db, user_id)
    if not obj:
        raise HTTPException(404, "User not found")
    return obj

@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    obj = user_crud.get(db, user_id)
    if not obj:
        raise HTTPException(404, "User not found")
    return user_crud.update(db, obj, payload)

@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    obj = user_crud.get(db, user_id)
    if not obj:
        raise HTTPException(404, "User not found")
    user_crud.delete(db, obj)
    return
