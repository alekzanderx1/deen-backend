from .base import CRUDBase
from ..models.hikmah_trees import HikmahTree
from ..schemas.hikmah_trees import HikmahTreeCreate, HikmahTreeUpdate

class CRUDHikmahTree(CRUDBase[HikmahTree, HikmahTreeCreate, HikmahTreeUpdate]):
    pass

hikmah_tree_crud = CRUDHikmahTree(HikmahTree)
