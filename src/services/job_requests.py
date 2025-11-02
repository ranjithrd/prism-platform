import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Session, select

from src.common.db import Device, JobDevice, JobRequest, JobUpdate

JOB_REQUEST_STREAM_NAME = "job_requests"


class JobRequestService:
    """Service for managing job requests using PostgreSQL only"""

    def __init__(self, session: Session):
        self.session = session

    def create_job_request(
        self, config_id: str, device_ids: List[str], duration: int
    ) -> JobRequest:
        """Create a new job request and send it to db"""
        job_id = str(uuid.uuid4())

        # Create job request in database
        job_request = JobRequest(
            job_id=job_id,
            config_id=config_id,
            status="pending",
            duration=duration,
        )

        for device_id in device_ids:
            job_request.job_devices.append(
                JobDevice(
                    job_id=job_id,
                    device_id=device_id,
                )
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
        """Generator for job updates from PostgreSQL JobUpdate table."""
        last_timestamp = datetime.min.replace(tzinfo=timezone.utc)
        no_data_count = 0
        max_no_data = 60  # Close after 60 heartbeats with no data (5 minutes)

        while True:
            try:
                from sqlmodel import col

                # Query for new updates since last timestamp
                updates = self.session.exec(
                    select(JobUpdate)
                    .where(col(JobUpdate.job_id) == job_id)
                    .where(col(JobUpdate.timestamp) > last_timestamp)
                    .order_by(col(JobUpdate.timestamp))
                ).all()

                if updates:
                    no_data_count = 0  # Reset counter when we get data
                    for update in updates:
                        last_timestamp = update.timestamp

                        # Get device info for the update
                        device = self.session.exec(
                            select(Device).where(
                                col(Device.device_id) == update.device_id
                            )
                        ).first()

                        update_data = {
                            "device_id": update.device_id,
                            "device_serial": device.device_uuid
                            if device
                            else update.device_id,
                            "status": update.status,
                            "message": update.message or "",
                            "timestamp": update.timestamp.isoformat(),
                        }

                        if update.trace_id:
                            update_data["trace_id"] = update.trace_id

                        yield f"data: {json.dumps(update_data)}\n\n"
                else:
                    # Send heartbeat to keep connection alive
                    no_data_count += 1
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

                    # Close connection after too long with no updates
                    if no_data_count >= max_no_data:
                        print(f"Closing SSE stream for job {job_id} due to inactivity")
                        break

                # Sleep briefly before checking again
                import time

                time.sleep(1)

            except Exception as e:
                print(f"Error reading job updates: {e}")
                import traceback

                traceback.print_exc()
                # Send error and close
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break

    def send_job_update(
        self,
        job_id: str,
        device_id: str,
        status: str,
        message: str = "",
        trace_id: Optional[str] = None,
    ):
        """Send a job update by inserting into JobUpdate table."""
        try:
            update = JobUpdate(
                update_id=str(uuid.uuid4()),
                job_id=job_id,
                device_id=device_id,
                status=status,
                message=message,
                timestamp=datetime.now(timezone.utc),
                trace_id=trace_id,
            )
            self.session.add(update)
            self.session.commit()
        except Exception as e:
            print(f"Failed to create job update in database: {e}")
            self.session.rollback()

    def get_all_devices_for_job(self, job_request: JobRequest) -> List[Device]:
        """Get all devices involved in a job request via JobDevice table."""
        device_ids = [jd.device_id for jd in job_request.job_devices]
        if not device_ids:
            return []

        from sqlmodel import col

        devices = self.session.exec(
            select(Device).where(col(Device.device_id).in_(device_ids))
        ).all()
        return list(devices)
