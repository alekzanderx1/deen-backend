import requests
from core.config import SUPABASE_URL

from models.JWTBearer import JWKS, JWTBearer

jwks = JWKS.model_validate(
    requests.get(
        f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    ).json()
)

auth = JWTBearer(jwks)
optional_auth = JWTBearer(jwks, auto_error=False)
