from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import select

from src.common.db import Config, Device, SessionDepType, get_session
from src.services.job_requests import JobRequestService

router = APIRouter(prefix="/v1/api/requests", tags=["requests"])


class JobRequestCreate(BaseModel):
    config_id: str
    devices: List[str]
    duration: int


class JobRequestResponse(BaseModel):
    job_id: str
    config_id: str
    device_serials: List[str]
    status: str
    created_at: str
    updated_at: str
    duration: int | None = None
    result_summary: str | None = None

    class Config:
        from_attributes = True


@router.post("", response_model=JobRequestResponse)
def create_job_request(
    request: JobRequestCreate, session: SessionDepType = Depends(get_session)
):
    """Create a new job request"""
    config = session.exec(
        select(Config).where(Config.config_id == request.config_id)
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    if not request.devices:
        raise HTTPException(status_code=400, detail="No devices provided")

    job_service = JobRequestService(session)
    job_request = job_service.create_job_request(
        request.config_id, request.devices, request.duration
    )
    device_serials = session.exec(
        select(Device.device_uuid).where(Device.device_id.in_(request.devices))
    ).all()

    return JobRequestResponse(
        job_id=job_request.job_id,
        config_id=job_request.config_id,
        device_serials=device_serials,
        status=job_request.status,
        duration=job_request.duration,
        created_at=job_request.created_at.isoformat(),
        updated_at=job_request.updated_at.isoformat(),
        result_summary=job_request.result_summary,
    )


@router.get("/{job_id}", response_model=JobRequestResponse)
def get_job_request(job_id: str, session: SessionDepType = Depends(get_session)):
    """Get job request details"""
    job_service = JobRequestService(session)
    job_request = job_service.get_job_request(job_id)

    if not job_request:
        raise HTTPException(status_code=404, detail="Job request not found")

    device_serials = list(
        session.exec(
            select(Device.device_uuid).where(
                Device.device_id.in_([jd.device_id for jd in job_request.job_devices])
            )
        ).all()
    )

    return JobRequestResponse(
        job_id=job_request.job_id,
        config_id=job_request.config_id,
        device_serials=device_serials,
        status=job_request.status,
        duration=job_request.duration,
        created_at=job_request.created_at.isoformat(),
        updated_at=job_request.updated_at.isoformat(),
        result_summary=job_request.result_summary,
    )


@router.get("/{job_id}/stream")
def stream_job_updates(job_id: str, session: SessionDepType = Depends(get_session)):
    """Server-Sent Events stream for job updates"""
    job_service = JobRequestService(session)
    job_request = job_service.get_job_request(job_id)

    if not job_request:
        raise HTTPException(status_code=404, detail="Job request not found")

    def event_stream():
        yield 'data: {"type": "connected"}\n\n'
        for update in job_service.get_job_updates_stream(job_id):
            yield update

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
