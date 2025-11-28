import json
import os
import platform

from src.common.host_token import decode_host_token


def get_user_config_path(app_name="PRISM_Platform", filename="config.json"):
    """
    Returns the full path to a writable configuration file in the user's
    OS-specific data directory.
    """
    system = platform.system()

    if system == "Windows":
        # Usually C:\Users\<User>\AppData\Local
        base_path = (
            os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or os.path.expanduser("~")
        )
    elif system == "Darwin":
        # /Users/<User>/Library/Application Support
        base_path = os.path.expanduser("~/Library/Application Support")
    else:
        # Linux/Unix: ~/.config
        base_path = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))

    # Ensure base_path is a string for type-checkers
    if base_path is None:
        base_path = os.path.expanduser("~")

    # Ensure the directory exists (e.g., .../Application Support/PRISM_Platform/)
    app_dir = os.path.join(base_path, app_name)
    os.makedirs(app_dir, exist_ok=True)

    return os.path.join(app_dir, filename)


# Set the global path variable to the safe, writable location
WORKER_CONFIG_PATH = get_user_config_path()

print(f"Config file location: {WORKER_CONFIG_PATH}")

# --- PATH CONFIGURATION END ---


def get_value_from_config(key, default=None):
    if os.path.exists(WORKER_CONFIG_PATH):
        try:
            with open(WORKER_CONFIG_PATH, "r") as f:
                config_data = json.load(f)
                return config_data.get(key, default)
        except json.JSONDecodeError:
            return default
    else:
        with open(WORKER_CONFIG_PATH, "w") as f:
            json.dump({}, f)
    return default


def set_value_in_config(key, value):
    config_data = {}

    if os.path.exists(WORKER_CONFIG_PATH):
        try:
            with open(WORKER_CONFIG_PATH, "r") as f:
                config_data = json.load(f)
        except json.JSONDecodeError:
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

        # If decode_host_token fails, handle it gracefully
        try:
            decoded_token = decode_host_token(at, ignore_secret=True)
            self.hostname = decoded_token.hostname if decoded_token else "localhost"
            self.api_url = (
                decoded_token.api_url if decoded_token else "http://localhost:8000"
            )
        except Exception as e:
            print(f"Error decoding token: {e}")
            self.hostname = "localhost"
            self.api_url = "http://localhost:8000"


# singleton instance
worker_config = WorkerConfig()
