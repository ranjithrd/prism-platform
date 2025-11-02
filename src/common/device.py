import datetime

from .db import Device

ONLINE_THRESHOLD_SECONDS = 5


def calculate_status(
    last_seen: datetime.datetime | None, custom_threshold: int | None
) -> str:
    threshold = (
        ONLINE_THRESHOLD_SECONDS if custom_threshold is None else custom_threshold
    )
    if last_seen is None:
        return "offline"
    delta = datetime.datetime.now(datetime.timezone.utc) - last_seen.replace(
        tzinfo=datetime.timezone.utc
    )
    if delta.total_seconds() < threshold:
        return "online"
    return "offline"


def get_status_and_host(device: Device | None) -> tuple[str, str | None]:
    """Determine the status and host of a device based on its last seen timestamp."""
    last_seen = device.last_seen if device else None
    host = device.host if device else None

    if last_seen is None:
        return "offline", host
    delta = datetime.datetime.now(datetime.timezone.utc) - last_seen
    if delta.total_seconds() < ONLINE_THRESHOLD_SECONDS:
        return "online", host
    return "offline", host
