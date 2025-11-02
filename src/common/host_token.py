import uuid

from .jwt import create_jwt_token, decode_jwt_token


class HostTokenPayload:
    hostname: str
    api_url: str
    identifier: str

    def __init__(self, hostname: str, api_url: str):
        self.hostname = hostname
        self.api_url = api_url
        self.identifier = uuid.uuid4().hex


def create_host_token(payload: HostTokenPayload) -> str:
    """Create a JWT token for host authentication."""
    token_payload = {
        "hostname": payload.hostname,
        "api_url": payload.api_url,
        "identifier": payload.identifier,
    }
    token = create_jwt_token(
        token_payload, expires_in_minutes=6 * 30 * 24 * 60
    )  # 6 months
    return token


def decode_host_token(
    token: str, ignore_secret: bool = False
) -> HostTokenPayload | None:
    """Decode a JWT token for host authentication."""
    try:
        payload = decode_jwt_token(token, ignore_secret=ignore_secret)
        host_token_payload = HostTokenPayload(
            hostname=payload.get("hostname", ""),
            api_url=payload.get("api_url", ""),
        )
        return host_token_payload
    except ValueError:
        return None
