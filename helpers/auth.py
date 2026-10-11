from jose import JWTError, jwt
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")


TOKEN_EXPIRE_DAYS = int(os.getenv("TOKEN_EXPIRE_DAYS", 7))


def generate_token(user_id: str):
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        payload,
        str(JWT_SECRET_KEY),
        algorithm=str(JWT_ALGORITHM),
    )  # noqa


def extract_id_from_token(token: str) -> str | None:
    try:
        decoded = jwt.decode(
            token, str(JWT_SECRET_KEY), algorithms=[str(JWT_ALGORITHM)]
        )
        return decoded.get("sub")
    except JWTError:
        return None
