from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..session import get_db
from ..crud.hikmah_trees import hikmah_tree_crud
from ..models.hikmah_trees import HikmahTree
from ..schemas.hikmah_trees import HikmahTreeCreate, HikmahTreeRead, HikmahTreeUpdate

router = APIRouter(prefix="/hikmah-trees", tags=["hikmah_trees"])


@router.post("", response_model=HikmahTreeRead)
def create_hikmah_tree(payload: HikmahTreeCreate, db: Session = Depends(get_db)):
    return hikmah_tree_crud.create(db, payload)


@router.get("", response_model=List[HikmahTreeRead])
def list_hikmah_trees(
        db: Session = Depends(get_db),
        q: Optional[str] = Query(None, description="Search by title/summary"),
        tag: Optional[str] = None,
        skill_level: Optional[str] = None,
        skip: int = 0,
        limit: int = Query(100, le=500),
):
    query = db.query(HikmahTree)
    if q:
        like = f"%{q}%"
        query = query.filter((HikmahTree.title.ilike(like)) | (HikmahTree.summary.ilike(like)))
    if tag:
        query = query.filter(HikmahTree.tags.contains([tag]))
    if skill_level:
        query = query.filter(HikmahTree.skill_level == skill_level)
    query = query.order_by(HikmahTree.id.asc())
    return query.offset(skip).limit(limit).all()


@router.get("/{tree_id}", response_model=HikmahTreeRead)
def get_hikmah_tree(tree_id: int, db: Session = Depends(get_db)):
    obj = hikmah_tree_crud.get(db, tree_id)
    if not obj:
        raise HTTPException(404, "Hikmah tree not found")
    return obj


@router.patch("/{tree_id}", response_model=HikmahTreeRead)
def update_hikmah_tree(tree_id: int, payload: HikmahTreeUpdate, db: Session = Depends(get_db)):
    obj = hikmah_tree_crud.get(db, tree_id)
    if not obj:
        raise HTTPException(404, "Hikmah tree not found")
    return hikmah_tree_crud.update(db, obj, payload)


@router.delete("/{tree_id}", status_code=204)
def delete_hikmah_tree(tree_id: int, db: Session = Depends(get_db)):
    obj = hikmah_tree_crud.get(db, tree_id)
    if not obj:
        raise HTTPException(404, "Hikmah tree not found")
    hikmah_tree_crud.delete(db, obj)
    return
