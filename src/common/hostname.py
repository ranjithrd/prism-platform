import os

import dotenv

dotenv.load_dotenv()


def get_hostname() -> str:
    hostname = os.getenv("HOSTNAME")
    if not hostname:
        raise ValueError("HOSTNAME environment variable is not set")
    return hostname
