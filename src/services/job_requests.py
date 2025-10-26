import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Session, select

from src.common.db import Device, JobRequest
from src.common.redis_client import get_redis_client

JOB_REQUEST_STREAM_NAME = "job_requests"


class JobRequestService:
    """Service for managing job requests and Redis stream operations"""

    def __init__(self, session: Session):
        self.session = session
        self.redis_client = get_redis_client()

    def create_job_request(
        self, config_id: str, device_ids: List[str], duration: int
    ) -> JobRequest:
        """Create a new job request and send it to Redis stream"""
        job_id = str(uuid.uuid4())

        # Create job request in database
        job_request = JobRequest(
            job_id=job_id,
            config_id=config_id,
            device_serials=json.dumps(device_ids),
            status="pending",
            duration=duration,
        )

        device_serials = []
        devices = self.session.exec(
            select(Device).where(Device.device_id.in_(device_ids))
        ).all()
        for device in devices:
            device_serials.append(device.device_uuid)

        self.session.add(job_request)
        self.session.commit()
        self.session.refresh(job_request)

        # Send to Redis stream
        if self.redis_client:
            stream_data = {
                "job_id": job_id,
                "config_id": config_id,
                "devices": json.dumps(device_serials),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration": duration,
            }

            try:
                self.redis_client.client.publish(
                    JOB_REQUEST_STREAM_NAME, json.dumps(stream_data)
                )
            except Exception as e:
                print(f"Failed to send job request to Redis stream: {e}")

        return job_request

    def get_job_request(self, job_id: str) -> Optional[JobRequest]:
        """Get a job request by ID"""
        return self.session.exec(
            select(JobRequest).where(JobRequest.job_id == job_id)
        ).first()

    def update_job_status(
        self, job_id: str, status: str, result_summary: Optional[str] = None
    ):
        """Update job request status and result"""
        job_request = self.get_job_request(job_id)
        if job_request:
            job_request.status = status
            job_request.updated_at = datetime.now(timezone.utc)
            if result_summary:
                job_request.result_summary = result_summary

            self.session.add(job_request)
            self.session.commit()

    def get_job_updates_stream(self, job_id: str):
        """Generator for job updates from Redis stream"""
        if not self.redis_client:
            # Send heartbeat even without Redis to keep connection alive
            import time

            while True:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                time.sleep(5)
            return

        stream_key = f"{JOB_REQUEST_STREAM_NAME}:{job_id}"
        last_id = "0"
        no_data_count = 0
        max_no_data = 60  # Close after 60 heartbeats with no data (5 minutes)

        while True:
            try:
                # Read from stream with timeout
                streams = self.redis_client.client.xread(
                    {stream_key: last_id}, block=1000
                )

                if streams:
                    no_data_count = 0  # Reset counter when we get data
                    for stream_name, messages in streams:
                        for message_id, fields in messages:
                            last_id = message_id

                            # Decode bytes if needed
                            decoded_fields = {}
                            for key, value in fields.items():
                                if isinstance(key, bytes):
                                    key = key.decode("utf-8")
                                if isinstance(value, bytes):
                                    value = value.decode("utf-8")
                                decoded_fields[key] = value

                            yield f"data: {json.dumps(decoded_fields)}\n\n"
                else:
                    # Send heartbeat to keep connection alive
                    no_data_count += 1
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

                    # Close connection after too long with no updates
                    if no_data_count >= max_no_data:
                        print(f"Closing SSE stream for job {job_id} due to inactivity")
                        break

            except Exception as e:
                print(f"Error reading from Redis stream: {e}")
                import traceback

                traceback.print_exc()
                # Send error and close
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break

    def send_job_update(
        self,
        job_id: str,
        device_serial: str,
        status: str,
        message: str = "",
        trace_id: Optional[str] = None,
    ):
        """Send a job update to the Redis stream"""
        if not self.redis_client:
            return

        stream_key = f"{JOB_REQUEST_STREAM_NAME}:{job_id}"
        update_data = {
            "device_serial": device_serial,
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if trace_id:
            update_data["trace_id"] = trace_id

        try:
            self.redis_client.client.xadd(stream_key, update_data)
        except Exception as e:
            print(f"Failed to send job update to Redis stream: {e}")

    def get_all_devices_for_job(self, job_request: JobRequest) -> List[Device]:
        """Get all devices involved in a job request"""
        device_serials = json.loads(job_request.device_serials)
        devices = self.session.exec(
            select(Device).where(
                Device.device_uuid.in_(device_serials)
                | Device.device_id.in_(device_serials)
            )
        ).all()
        return list(devices)
