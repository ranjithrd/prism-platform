import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import or_, select

from src.common.db import (
    Config,
    Device,
    Host,
    JobDevice,
    JobRequest,
    JobUpdate,
    SessionDepType,
    Trace,
    get_session,
)
from src.common.host_token import decode_host_token
from src.common.minio import MinioHelper, get_minio_client
from src.common.simpleperf_html import generate_simpleperf_html

router = APIRouter(prefix="/v1/api/worker", tags=["worker"])


def get_hostname_from_token(token: str) -> str:
    """Extract hostname from bearer token."""
    return token  # In this stub, we treat the token as the hostname directly.


async def verify_worker_token(
    authorization: Optional[str] = Header(None),
    session: SessionDepType = Depends(get_session),
) -> bool:
    """Stub authentication - accepts any bearer token for now."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")

    # treat bearer token as hostname
    token = authorization[len("Bearer ") :].strip()
    host_details = decode_host_token(token)

    if not host_details:
        raise HTTPException(status_code=401, detail="Invalid host token")

    host = session.exec(
        select(Host).where(Host.host_name == host_details.hostname)
    ).first()

    if not host:
        raise HTTPException(status_code=401, detail="Host not registered")

    if host.host_key != token:
        raise HTTPException(status_code=401, detail="Invalid host key")

    host.last_seen = datetime.now(timezone.utc)
    host.host_type = "worker"

    session.add(host)
    session.commit()

    return True


class PendingJob(BaseModel):
    job_device_id: str  # JobDevice.id
    job_id: str
    config_id: str
    device_id: str
    device_uuid: str  # For ADB connection check
    duration: int
    status: str  # JobDevice status

    class Config:
        from_attributes = True


class ConfigResponse(BaseModel):
    config_id: str
    config_name: str
    config_text: str
    tracing_tool: Optional[str] = None
    default_duration: Optional[int] = None

    class Config:
        from_attributes = True


class DeviceResponse(BaseModel):
    device_id: str
    device_name: str
    device_uuid: Optional[str] = None

    class Config:
        from_attributes = True


class TraceCreateRequest(BaseModel):
    trace_id: str
    trace_name: str
    device_id: Optional[str] = None
    trace_timestamp: str
    trace_filename: str
    host_name: Optional[str] = None
    configuration_id: Optional[str] = None
    trace_html_filename: Optional[str] = None


class TraceCreateResponse(BaseModel):
    trace_id: str
    trace_name: str
    trace_timestamp: str
    trace_filename: str

    class Config:
        from_attributes = True


class JobStatusUpdate(BaseModel):
    status: str
    result_summary: Optional[str] = None


class JobProgressUpdate(BaseModel):
    device_id: str  # Changed from device_serial
    status: str
    message: Optional[str] = None
    trace_id: Optional[str] = None


@router.get("/jobs/pending", response_model=List[PendingJob])
def get_pending_jobs(
    session: SessionDepType = Depends(get_session),
    authenticated: bool = Depends(verify_worker_token),
):
    """Fetch pending job-device pairs for worker processing."""
    from sqlmodel import col

    # Get all JobDevice entries with status='pending' and join with Device
    job_devices = session.exec(
        select(JobDevice, JobRequest, Device)
        .join(JobRequest, col(JobDevice.job_id) == col(JobRequest.job_id))
        .join(Device, col(JobDevice.device_id) == col(Device.device_id))
        .where(col(JobDevice.status) == "pending")
    ).all()

    result = []
    for job_device, job_request, device in job_devices:
        result.append(
            PendingJob(
                job_device_id=job_device.id,
                job_id=job_request.job_id,
                config_id=job_request.config_id,
                device_id=device.device_id,
                device_uuid=device.device_uuid or device.device_id,
                duration=job_request.duration or 10,
                status=job_device.status,
            )
        )

    return result


@router.get("/configs/{config_id}", response_model=ConfigResponse)
def get_config(
    config_id: str,
    session: SessionDepType = Depends(get_session),
    authenticated: bool = Depends(verify_worker_token),
):
    """Fetch configuration by ID."""
    config = session.exec(select(Config).where(Config.config_id == config_id)).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config


@router.get("/devices/by-serial/{device_serial}", response_model=DeviceResponse)
def get_device_by_serial(
    device_serial: str,
    session: SessionDepType = Depends(get_session),
    authenticated: bool = Depends(verify_worker_token),
):
    """Fetch device by serial (device_uuid or device_id)."""
    device = session.exec(
        select(Device).where(
            or_(Device.device_uuid == device_serial, Device.device_id == device_serial)
        )
    ).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("/devices")
def get_devices(
    session: SessionDepType = Depends(get_session),
    authenticated: bool = Depends(verify_worker_token),
):
    """Fetch all devices."""
    devices = session.exec(select(Device)).all()
    return devices


class DeviceCreateRequest(BaseModel):
    device_id: str
    device_name: str
    device_uuid: Optional[str] = None
    last_seen: Optional[str] = None
    last_status: Optional[str] = None
    host: Optional[str] = None


class DeviceUpdateRequest(BaseModel):
    device_name: Optional[str] = None
    device_uuid: Optional[str] = None
    last_seen: Optional[str] = None
    last_status: Optional[str] = None
    host: Optional[str] = None


@router.post("/devices")
def create_device(
    device_data: DeviceCreateRequest,
    session: SessionDepType = Depends(get_session),
    authenticated: bool = Depends(verify_worker_token),
):
    """Create a new device."""
    from datetime import datetime

    device_kwargs = {
        "device_id": device_data.device_id,
        "device_name": device_data.device_name,
    }
    if device_data.device_uuid:
        device_kwargs["device_uuid"] = device_data.device_uuid
    if device_data.last_seen:
        device_kwargs["last_seen"] = datetime.fromisoformat(device_data.last_seen)
    if device_data.last_status:
        device_kwargs["last_status"] = device_data.last_status
    if device_data.host:
        device_kwargs["host"] = device_data.host

    device = Device(**device_kwargs)
    session.add(device)
    session.commit()
    session.refresh(device)
    return {"status": "success", "device_id": device.device_id}


@router.put("/devices/{device_id}")
def update_device(
    device_id: str,
    device_data: DeviceUpdateRequest,
    session: SessionDepType = Depends(get_session),
    authenticated: bool = Depends(verify_worker_token),
):
    """Update an existing device."""
    from datetime import datetime

    device = session.exec(select(Device).where(Device.device_id == device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device_data.device_name is not None:
        device.device_name = device_data.device_name
    if device_data.device_uuid is not None:
        device.device_uuid = device_data.device_uuid
    if device_data.last_seen is not None:
        device.last_seen = datetime.fromisoformat(device_data.last_seen)
    if device_data.last_status is not None:
        device.last_status = device_data.last_status
    if device_data.host is not None:
        device.host = device_data.host

    session.add(device)
    session.commit()
    return {"status": "success", "device_id": device.device_id}


@router.post("/traces", response_model=TraceCreateResponse)
def create_trace(
    trace_data: TraceCreateRequest,
    session: SessionDepType = Depends(get_session),
    authenticated: bool = Depends(verify_worker_token),
    minio: MinioHelper = Depends(get_minio_client),
):
    """Create a trace record."""
    from datetime import datetime

    trace_kwargs = {
        "trace_id": trace_data.trace_id,
        "trace_name": trace_data.trace_name,
        "trace_timestamp": datetime.fromisoformat(trace_data.trace_timestamp),
        "trace_filename": trace_data.trace_filename,
        "trace_html_filename": trace_data.trace_html_filename,
    }
    if trace_data.device_id:
        trace_kwargs["device_id"] = trace_data.device_id
    if trace_data.host_name:
        trace_kwargs["host_name"] = trace_data.host_name
    if trace_data.configuration_id:
        trace_kwargs["configuration_id"] = trace_data.configuration_id
    if trace_data.trace_html_filename:
        trace_kwargs["trace_html_filename"] = trace_data.trace_html_filename

    logging.info("Checking if HTML generation is needed for trace...")
    logging.info(
        f"trace_html_filename: {trace_data.trace_html_filename}, configuration_id: {trace_data.configuration_id}"
    )

    if not trace_data.trace_html_filename and trace_data.configuration_id:
        config = session.exec(
            select(Config).where(Config.config_id == trace_data.configuration_id)
        ).first()

        logging.info("Generating HTML for trace based on configuration...")
        logging.info(f"Trace filename: {trace_data.trace_filename}")
        logging.info(f"Configuration: {config.tracing_tool}")

        if config and config.tracing_tool == "simpleperf":
            html_filename = generate_simpleperf_html(trace_data.trace_filename, minio)
            if html_filename:
                trace_kwargs["trace_html_filename"] = html_filename

    trace = Trace(**trace_kwargs)
    session.add(trace)
    session.commit()
    session.refresh(trace)

    return TraceCreateResponse(
        trace_id=trace.trace_id,
        trace_name=trace.trace_name,
        trace_timestamp=trace.trace_timestamp.isoformat(),
        trace_filename=trace.trace_filename,
    )


@router.post("/jobs/{job_id}/status")
def update_job_status(
    job_id: str,
    update: JobStatusUpdate,
    session: SessionDepType = Depends(get_session),
    authenticated: bool = Depends(verify_worker_token),
):
    """Update job status."""
    from datetime import datetime, timezone

    job = session.exec(select(JobRequest).where(JobRequest.job_id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = update.status
    job.updated_at = datetime.now(timezone.utc)
    if update.result_summary:
        job.result_summary = update.result_summary

    session.add(job)
    session.commit()
    return {"status": "success"}


@router.post("/jobs/{job_id}/updates")
def add_job_update(
    job_id: str,
    update: JobProgressUpdate,
    session: SessionDepType = Depends(get_session),
    authenticated: bool = Depends(verify_worker_token),
):
    """Record a job progress update for a specific device."""
    from datetime import datetime, timezone

    job_update = JobUpdate(
        update_id=str(uuid.uuid4()),
        job_id=job_id,
        device_id=update.device_id,
        status=update.status,
        message=update.message,
        timestamp=datetime.now(timezone.utc),
        trace_id=update.trace_id,
    )
    session.add(job_update)
    session.commit()
    return {"status": "success"}


class JobDeviceStatusUpdate(BaseModel):
    job_device_id: str
    status: str  # pending, running, completed, failed


@router.post("/job-devices/status")
def update_job_device_status(
    update: JobDeviceStatusUpdate,
    session: SessionDepType = Depends(get_session),
    authenticated: bool = Depends(verify_worker_token),
):
    """Update the status of a specific job-device pair."""
    from sqlmodel import col

    job_device = session.exec(
        select(JobDevice).where(col(JobDevice.id) == update.job_device_id)
    ).first()

    if not job_device:
        raise HTTPException(status_code=404, detail="JobDevice not found")

    job_device.status = update.status
    session.add(job_device)
    session.commit()
    return {"status": "success"}


@router.post("/storage/upload")
async def upload_file(
    bucket: str,
    object_name: str,
    request: Request,
    authenticated: bool = Depends(verify_worker_token),
    minio_helper: MinioHelper = Depends(get_minio_client),
):
    """Upload a file to MinIO storage.

    The file bytes should be sent as the raw request body.
    Query params: bucket, object_name
    """
    try:
        if minio_helper is None:
            raise HTTPException(status_code=500, detail="MinIO helper not available")

        # Read the raw body bytes
        file_bytes = await request.body()

        if not file_bytes:
            raise HTTPException(status_code=400, detail="No file data provided")

        # Upload to MinIO
        minio_helper.upload_bytes(bucket, object_name, file_bytes)

        return {
            "status": "success",
            "bucket": bucket,
            "object_name": object_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
