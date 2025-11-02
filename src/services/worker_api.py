import logging
import os
from typing import List, Optional

import httpx

from src.services.worker_config import worker_config

logger = logging.getLogger(__name__)


class WorkerAPIClient:
    """HTTP client for calling the worker API endpoints."""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        # Use worker_config as the source of truth, with fallback to env vars
        self.base_url = (
            base_url
            or worker_config.api_url
            or os.getenv("WORKER_API_URL", "http://localhost:8000")
        )
        self.token = (
            token
            or worker_config.auth_token
            or os.getenv("WORKER_API_TOKEN", "default-token")
        )
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.timeout = 30.0

        logger.info(f"WorkerAPIClient initialized with base_url={self.base_url}")

    def _make_request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request with error handling and logging."""
        url = f"{self.base_url}{endpoint}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(method, url, headers=self.headers, **kwargs)
                response.raise_for_status()
                return response.json() if response.content else None
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP {e.response.status_code} error calling {method} {url}: {e.response.text}"
            )
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error calling {method} {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling {method} {url}: {str(e)}")
            return None

    def fetch_pending_jobs(self) -> List[dict]:
        """Fetch pending jobs from the API."""
        result = self._make_request("GET", "/v1/api/worker/jobs/pending")
        return result if result else []

    def get_config(self, config_id: str) -> Optional[dict]:
        """Fetch config by ID from the API."""
        return self._make_request("GET", f"/v1/api/worker/configs/{config_id}")

    def get_device_by_serial(self, device_serial: str) -> Optional[dict]:
        """Fetch device by serial from the API."""
        return self._make_request(
            "GET", f"/v1/api/worker/devices/by-serial/{device_serial}"
        )

    def get_existing_devices(self) -> List[dict]:
        """Fetch existing devices from the API."""
        result = self._make_request("GET", "/v1/api/worker/devices")
        return result if result else []

    def add_new_device(self, device: dict) -> Optional[dict]:
        """Add a new device via API."""
        return self._make_request("POST", "/v1/api/worker/devices", json=device)

    def update_device(self, device_id: str, device: dict) -> Optional[dict]:
        """Update an existing device via API."""
        return self._make_request(
            "PUT", f"/v1/api/worker/devices/{device_id}", json=device
        )

    def upload_trace_file(
        self, bucket: str, object_name: str, trace_file: bytes
    ) -> Optional[dict]:
        """Upload trace file via API to storage.

        Sends the file bytes as raw request body with bucket and object_name as query params.
        """
        url = f"{self.base_url}/v1/api/worker/storage/upload"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    params={"bucket": bucket, "object_name": object_name},
                    content=trace_file,
                    headers=self.headers,
                )
                response.raise_for_status()
                result = response.json() if response.content else None
                logger.info(f"Uploaded {object_name} to {bucket}")
                return result
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP {e.response.status_code} error uploading file: {e.response.text}"
            )
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error uploading file: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {str(e)}")
            return None

    def create_trace_record(self, trace_payload: dict) -> Optional[dict]:
        """Create trace record via API."""
        return self._make_request("POST", "/v1/api/worker/traces", json=trace_payload)

    def send_job_update(
        self,
        job_id: str,
        device_id: str,
        status: str,
        message: str = "",
        trace_id: Optional[str] = None,
    ) -> Optional[dict]:
        """Send job progress update via API."""
        payload = {
            "device_id": device_id,
            "status": status,
            "message": message,
        }
        if trace_id:
            payload["trace_id"] = trace_id

        return self._make_request(
            "POST", f"/v1/api/worker/jobs/{job_id}/updates", json=payload
        )

    def update_job_device_status(
        self, job_device_id: str, status: str
    ) -> Optional[dict]:
        """Update JobDevice status via API."""
        payload = {
            "job_device_id": job_device_id,
            "status": status,
        }
        return self._make_request(
            "POST", "/v1/api/worker/job-devices/status", json=payload
        )

    def update_job_status(
        self, job_id: str, status: str, result_summary: Optional[str] = None
    ) -> Optional[dict]:
        """Update job status via API."""
        payload = {"status": status}
        if result_summary:
            payload["result_summary"] = result_summary

        return self._make_request(
            "POST", f"/v1/api/worker/jobs/{job_id}/status", json=payload
        )


_client_instance: Optional[WorkerAPIClient] = None


def get_worker_client() -> WorkerAPIClient:
    """Get or create the singleton worker API client.

    Uses worker_config for base_url and auth_token configuration.
    The singleton is created on first access and reused thereafter.
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = WorkerAPIClient()
        logger.info("Created singleton WorkerAPIClient instance")
    return _client_instance


def reset_worker_client() -> None:
    """Reset the singleton client instance. Useful after config changes."""
    global _client_instance
    _client_instance = None
    logger.info("Reset WorkerAPIClient singleton")
