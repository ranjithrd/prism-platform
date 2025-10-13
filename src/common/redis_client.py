import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Literal, Optional

import redis
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Type Definitions for Status Literals ---
HostStatus = Literal["online", "offline"]
DeviceStatus = Literal["online", "offline", "busy"]


class RedisHelper:
    """
    A helper class to interact with a Redis server, providing methods to manage
    structured data for host and device statuses.
    """

    HOST_PREFIX = "status:host"
    DEVICE_PREFIX = "status:device"

    def __init__(self, url: str, db: int = 0):
        """
        Initializes the Redis client and verifies the connection.

        Args:
            url (str): The connection URL for the Redis server (e.g., "redis://localhost:6379").
            db (int): The Redis database number to use.
        """
        if not url:
            raise ValueError("Redis URL must be provided.")

        try:
            self.client = redis.from_url(url, db=db, decode_responses=True)
            self.client.ping()
            logging.info(f"RedisHelper initialized and connected to {url}, DB: {db}")
        except redis.exceptions.ConnectionError as exc:
            logging.error(f"Failed to connect to Redis at {url}: {exc}")
            raise

    # --- Private Key Management ---

    def _get_host_key(self, host_id: str) -> str:
        """Constructs the Redis key for a host."""
        return f"{self.HOST_PREFIX}:{host_id}"

    def _get_device_key(self, device_id: str) -> str:
        """Constructs the Redis key for a device."""
        return f"{self.DEVICE_PREFIX}:{device_id}"

    # --- Host Status Management ---

    def update_host_status(self, host_id: str, status: HostStatus):
        """
        Sets or updates the status for a given host.

        Args:
            host_id (str): The unique identifier for the host.
            status (HostStatus): The current status ('online' or 'offline').
        """
        try:
            key = self._get_host_key(host_id)
            value = {
                "status": status,
                "last_seen": datetime.utcnow().isoformat()
            }
            self.client.set(key, json.dumps(value))
            logging.info(f"Updated host '{host_id}' status to '{status}'.")
        except redis.exceptions.RedisError as exc:
            logging.error(f"Error updating host status for '{host_id}': {exc}")
            raise

    def get_host_status(self, host_id: str) -> Optional[Dict]:
        """
        Retrieves the status record for a specific host.

        Args:
            host_id (str): The unique identifier for the host.

        Returns:
            Optional[Dict]: A dictionary with 'status' and 'last_seen', or None if not found.
        """
        try:
            key = self._get_host_key(host_id)
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except redis.exceptions.RedisError as exc:
            logging.error(f"Error getting host status for '{host_id}': {exc}")
            return None

    def get_all_host_statuses(self, host_ids: Optional[List[str]] = None) -> Dict[str, Dict]:
        """
        Retrieves the status records for all hosts.

        It can operate in two modes:
        1. Scan: If host_ids is None, it scans Redis for all keys matching the host prefix.
        2. Direct Fetch: If a list of host_ids is provided, it fetches them directly.

        Args:
            host_ids (Optional[List[str]]): A list of specific host IDs to fetch.

        Returns:
            Dict[str, Dict]: A dictionary mapping host IDs to their status data.
        """
        statuses = {}
        try:
            if host_ids:
                keys = [self._get_host_key(hid) for hid in host_ids]
            else:
                keys = [key for key in self.client.scan_iter(match=f"{self.HOST_PREFIX}:*")]

            if not keys:
                return {}

            values = self.client.mget(keys)
            for key, value in zip(keys, values):
                if value:
                    host_id = key.split(":")[-1]
                    statuses[host_id] = json.loads(value)
            return statuses
        except redis.exceptions.RedisError as exc:
            logging.error(f"Error getting all host statuses: {exc}")
            return {}

    # --- Device Status Management ---

    def update_device_status(
            self,
            device_id: str,
            status: DeviceStatus,
            current_host: Optional[str] = None
    ):
        """
        Sets or updates the status for a given device. If current_host is not provided,
        it preserves the existing value.

        Args:
            device_id (str): The unique identifier for the device.
            status (DeviceStatus): The current status ('online', 'offline', or 'busy').
            current_host (Optional[str]): The hostname of the host the device is connected to.
        """
        try:
            key = self._get_device_key(device_id)
            # Fetch existing data to preserve fields that aren't being updated
            existing_data = self.get_device_status(device_id) or {}

            value = {
                "status": status,
                "last_seen": datetime.utcnow().isoformat(),
                "current_host": current_host if current_host is not None else existing_data.get("current_host")
            }
            self.client.set(key, json.dumps(value))
            logging.info(f"Updated device '{device_id}' status to '{status}'.")
        except redis.exceptions.RedisError as exc:
            logging.error(f"Error updating device status for '{device_id}': {exc}")
            raise

    def get_device_status(self, device_id: str) -> Optional[Dict]:
        """
        Retrieves the status record for a specific device.

        Args:
            device_id (str): The unique identifier for the device.

        Returns:
            Optional[Dict]: A dictionary with 'status', 'last_seen', and 'current_host', or None if not found.
        """
        try:
            key = self._get_device_key(device_id)
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except redis.exceptions.RedisError as exc:
            logging.error(f"Error getting device status for '{device_id}': {exc}")
            return None

    def get_all_device_statuses(self, device_ids: Optional[List[str]] = None) -> Dict[str, Dict]:
        """
        Retrieves the status records for all devices.

        It can operate in two modes:
        1. Scan: If device_ids is None, it scans Redis for all keys matching the device prefix.
        2. Direct Fetch: If a list of device_ids is provided, it fetches them directly.

        Args:
            device_ids (Optional[List[str]]): A list of specific device IDs to fetch.

        Returns:
            Dict[str, Dict]: A dictionary mapping device IDs to their status data.
        """
        statuses = {}
        try:
            if device_ids:
                keys = [self._get_device_key(did) for did in device_ids]
            else:
                keys = [key for key in self.client.scan_iter(match=f"{self.DEVICE_PREFIX}:*")]

            if not keys:
                return {}

            values = self.client.mget(keys)
            for key, value in zip(keys, values):
                if value:
                    device_id = key.split(":")[-1]
                    statuses[device_id] = json.loads(value)
            return statuses
        except redis.exceptions.RedisError as exc:
            logging.error(f"Error getting all device statuses: {exc}")
            return {}


# --- Global Instance and Initializer ---

redis_helper_client: Optional[RedisHelper] = None


def initialize_redis_client():
    """
    Initializes the global Redis client from environment variables.
    This should be called once when the application starts.
    """
    global redis_helper_client
    if redis_helper_client is None:
        logging.info("Initializing Redis client...")
        try:
            redis_url = os.environ.get("REDIS_URL")
            redis_db = int(os.environ.get("REDIS_DB", 0))
            redis_helper_client = RedisHelper(url=redis_url, db=redis_db)
            logging.info("Redis client initialized successfully.")
        except (ValueError, redis.exceptions.ConnectionError) as e:
            logging.error(f"Failed to initialize Redis client: {e}")
            redis_helper_client = None


def get_redis_client() -> Optional[RedisHelper]:
    """
    Returns the global Redis client instance.
    Ideal for use with dependency injection systems like FastAPI's Depends().
    """
    return redis_helper_client
