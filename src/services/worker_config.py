import json
import os

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
    hostname = get_value_from_config("hostname", "localhost")
    api_url = get_value_from_config("api_url", "http://localhost:8000")
    auth_token = get_value_from_config("auth_token", "")

    def __init__(self):
        if not os.path.exists(WORKER_CONFIG_PATH):
            with open(WORKER_CONFIG_PATH, "w") as f:
                json.dump({}, f)

    @classmethod
    def update_config(cls, hostname=None, api_url=None, auth_token=None):
        if hostname is not None:
            cls.hostname = hostname
            set_value_in_config("hostname", hostname)
        if api_url is not None:
            cls.api_url = api_url
            set_value_in_config("api_url", api_url)
        if auth_token is not None:
            cls.auth_token = auth_token
            set_value_in_config("auth_token", auth_token)


# singleton instance
worker_config = WorkerConfig()
