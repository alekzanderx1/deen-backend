from .base import CRUDBase
from ..models.user_progress import UserProgress
from ..schemas.user_progress import UserProgressCreate, UserProgressUpdate

class CRUDUserProgress(CRUDBase[UserProgress, UserProgressCreate, UserProgressUpdate]):
    pass

user_progress_crud = CRUDUserProgress(UserProgress)
