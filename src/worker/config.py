import json
import os

from src.common.host_token import decode_host_token

WORKER_CONFIG_PATH = "config.json"


def get_value_from_config(key, default=None):
    if os.path.exists(WORKER_CONFIG_PATH):
        with open(WORKER_CONFIG_PATH, "r") as f:
            config_data = json.load(f)
            return config_data.get(key, default)
    else:
        with open(WORKER_CONFIG_PATH, "w") as f:
            json.dump({}, f)
    return default


def set_value_in_config(key, value):
    if os.path.exists(WORKER_CONFIG_PATH):
        with open(WORKER_CONFIG_PATH, "r") as f:
            config_data = json.load(f)
    else:
        config_data = {}

    config_data[key] = value

    with open(WORKER_CONFIG_PATH, "w") as f:
        json.dump(config_data, f, indent=4)


class WorkerConfig:
    hostname = ""
    api_url = ""
    auth_token = get_value_from_config("auth_token", "")

    def __init__(self):
        if not os.path.exists(WORKER_CONFIG_PATH):
            with open(WORKER_CONFIG_PATH, "w") as f:
                json.dump({}, f)

    @classmethod
    def update_config(cls, auth_token=None):
        if auth_token is not None:
            cls.auth_token = auth_token
            set_value_in_config("auth_token", auth_token)

    def refresh_config(self):
        at = get_value_from_config("auth_token", "")

        if not at:
            self.hostname = ""
            self.api_url = ""
            self.auth_token = ""
            return

        self.auth_token = at

        decoded_token = decode_host_token(at, ignore_secret=True)
        self.hostname = decoded_token.hostname if decoded_token else "localhost"
        self.api_url = (
            decoded_token.api_url if decoded_token else "http://localhost:8000"
        )


# singleton instance
worker_config = WorkerConfig()
