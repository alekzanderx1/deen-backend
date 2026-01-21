from .base import CRUDBase
from ..models.personalized_primers import PersonalizedPrimer
from ..schemas.personalized_primers import PersonalizedPrimerCreate, PersonalizedPrimerUpdate


class CRUDPersonalizedPrimer(CRUDBase[PersonalizedPrimer, PersonalizedPrimerCreate, PersonalizedPrimerUpdate]):
    """CRUD operations for personalized primers"""
    pass

personalized_primer_crud = CRUDPersonalizedPrimer(PersonalizedPrimer)
