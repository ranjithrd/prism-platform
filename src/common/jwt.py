import os
from datetime import datetime, timedelta, timezone

import jsonwebtoken as jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")


def create_jwt_token(payload: dict, expires_in_minutes: int = 60) -> str:
    """Create a JWT token with the given payload and expiration time."""
    expiration = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    payload.update({"exp": expiration})
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def decode_jwt_token(token: str, ignore_secret: bool = False) -> dict:
    """Decode a JWT token and return the payload."""
    try:
        if ignore_secret:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
    except ValueError as ve:
        raise ve
