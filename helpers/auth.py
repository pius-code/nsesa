from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone

from core.config import get_auth_config

auth_cfg = get_auth_config()


def generate_token(user_id: str):
    expire = datetime.now(timezone.utc) + timedelta(minutes=auth_cfg.token_expire_minutes)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        payload,
        auth_cfg.jwt_secret,
        algorithm=auth_cfg.jwt_algorithm,
    )


def extract_id_from_token(token: str) -> str | None:
    try:
        decoded = jwt.decode(
            token,
            auth_cfg.jwt_secret,
            algorithms=[auth_cfg.jwt_algorithm],
        )
        return decoded.get("sub")
    except JWTError:
        return None
