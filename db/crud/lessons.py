from .base import CRUDBase
from ..models.lessons import Lesson
from ..schemas.lessons import LessonCreate, LessonUpdate

class CRUDLesson(CRUDBase[Lesson, LessonCreate, LessonUpdate]):
    pass

lesson_crud = CRUDLesson(Lesson)
