from typing import Generic, TypeVar, Type, List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        return db.get(self.model, id)

    # get by user_id and lesson_id (composite key) - used in personalized primers
    def get_by_user_and_lesson(
        self,
        db: Session,
        user_id: str,
        lesson_id: int
    ) -> Optional[ModelType]:
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.lesson_id == lesson_id
        )
        return db.execute(stmt).scalars().first()

    def list(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars())

    def create(self, db: Session, obj_in: CreateSchemaType) -> ModelType:
        data = obj_in.model_dump(exclude_unset=True)
        obj = self.model(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        data = obj_in.model_dump(exclude_unset=True)
        for k, v in data.items():
            if v is not None:
                setattr(db_obj, k, v)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: ModelType) -> None:
        db.delete(db_obj)
        db.commit()
