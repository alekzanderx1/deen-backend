import requests
from core.config import COGNITO_POOL_ID, COGNITO_REGION

from models.JWTBearer import JWKS, JWTBearer

jwks = JWKS.model_validate(
    requests.get(
        f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
        f"{COGNITO_POOL_ID}/.well-known/jwks.json"
    ).json()
)

auth = JWTBearer(jwks)