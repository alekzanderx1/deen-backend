from .base import CRUDBase
from ..models.lesson_content import LessonContent
from ..schemas.lesson_content import LessonContentCreate, LessonContentUpdate

class CRUDLessonContent(CRUDBase[LessonContent, LessonContentCreate, LessonContentUpdate]):
    pass

lesson_content_crud = CRUDLessonContent(LessonContent)
