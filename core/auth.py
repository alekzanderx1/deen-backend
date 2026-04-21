import requests
from core.config import SUPABASE_URL, ENV

from models.JWTBearer import JWKS, JWTBearer, DevBypassBearer

jwks = JWKS.model_validate(
    requests.get(
        f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    ).json()
)

# Single auth dependency: dev bypass in development, strict in production.
# Routes import only `auth` — optional_auth is no longer needed.
auth = DevBypassBearer(jwks, env=ENV)
