import datetime
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException
from fastapi import Query as QueryParam
from fastapi import UploadFile
from pydantic import BaseModel
from sqlmodel import desc, or_, select

from src.common.db import Config, Device, SessionDepType, Trace, get_session
from src.common.hostname import get_hostname
from src.common.minio import MinioHelper, get_minio_client

router = APIRouter(prefix="/v1/api/traces", tags=["traces"])


class TraceWithDevice(BaseModel):
    trace_id: str
    trace_name: str
    trace_timestamp: str
    trace_filename: str
    device_id: str
    device_name: str
    host_name: Optional[str] = None
    configuration_id: Optional[str] = None

    class Config:
        from_attributes = True


class TraceDetail(BaseModel):
    trace_id: str
    trace_name: str
    trace_timestamp: str
    trace_filename: str
    device_id: str
    device_name: str
    host_name: Optional[str] = None
    configuration_id: Optional[str] = None
    configuration_name: Optional[str] = None
    configuration_type: Optional[str] = None

    class Config:
        from_attributes = True


class TraceUpdate(BaseModel):
    trace_name: str
    device_id: Optional[str] = None


@router.get("", response_model=List[TraceWithDevice])
def get_traces(
    session: SessionDepType = Depends(get_session),
    sort_by: Optional[str] = QueryParam(None, description="Field to sort by"),
    device_id: Optional[str] = QueryParam(None, description="Filter by device ID"),
    limit: Optional[int] = QueryParam(None, description="Limit number of results"),
):
    """Get all traces with filtering and sorting"""
    query = select(Trace, Device).join(Device)

    if device_id:
        query = query.where(
            or_(Trace.device_id == device_id, Device.device_uuid == device_id)
        )

    if sort_by == "name":
        query = query.order_by(Trace.trace_name)
    else:
        query = query.order_by(desc(Trace.trace_timestamp))

    if limit:
        query = query.limit(limit)

    results = session.exec(query).all()

    traces_with_devices = []
    for trace, device in results:
        traces_with_devices.append(
            TraceWithDevice(
                trace_id=trace.trace_id,
                trace_name=trace.trace_name,
                trace_timestamp=trace.trace_timestamp.isoformat(),
                trace_filename=trace.trace_filename,
                device_id=trace.device_id,
                device_name=device.device_name,
                host_name=trace.host_name,
                configuration_id=trace.configuration_id,
            )
        )

    return traces_with_devices


@router.get("/{trace_id}", response_model=TraceDetail)
def get_trace(trace_id: str, session: SessionDepType = Depends(get_session)):
    """Get a specific trace"""
    result = session.exec(
        select(Trace, Device).join(Device).where(Trace.trace_id == trace_id)
    ).first()

    if not result:
        raise HTTPException(status_code=404, detail="Trace not found")

    trace, device = result

    config = None
    if trace.configuration_id is not None:
        config = session.exec(
            select(Config).where(Config.config_id == trace.configuration_id)
        ).first()

    data = TraceDetail(
        trace_id=trace.trace_id,
        trace_name=trace.trace_name,
        trace_timestamp=trace.trace_timestamp.isoformat(),
        trace_filename=trace.trace_filename,
        device_id=trace.device_id,
        device_name=device.device_name,
        host_name=trace.host_name,
        configuration_id=trace.configuration_id,
    )

    if config:
        data.configuration_name = config.config_name
        data.configuration_type = config.tracing_tool

    return data


@router.post("/{trace_id}/edit", response_model=TraceDetail)
def edit_trace(
    trace_id: str,
    trace_update: TraceUpdate,
    session: SessionDepType = Depends(get_session),
):
    """Edit trace metadata"""
    result = session.exec(
        select(Trace, Device).join(Device).where(Trace.trace_id == trace_id)
    ).first()

    if not result:
        raise HTTPException(status_code=404, detail="Trace not found")

    trace, device = result
    trace.trace_name = trace_update.trace_name
    if trace_update.device_id:
        trace.device_id = trace_update.device_id
        device = session.exec(
            select(Device).where(Device.device_id == trace_update.device_id)
        ).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

    session.add(trace)
    session.commit()
    session.refresh(trace)

    return TraceDetail(
        trace_id=trace.trace_id,
        trace_name=trace.trace_name,
        trace_timestamp=trace.trace_timestamp.isoformat(),
        trace_filename=trace.trace_filename,
        device_id=trace.device_id,
        device_name=device.device_name,
        host_name=trace.host_name,
        configuration_id=trace.configuration_id,
    )


@router.post("/{trace_id}/delete")
def delete_trace(
    trace_id: str,
    session: SessionDepType = Depends(get_session),
    minio_helper: MinioHelper = Depends(get_minio_client),
):
    """Delete a trace"""
    trace = session.exec(select(Trace).where(Trace.trace_id == trace_id)).first()
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    try:
        # MinioHelper exposes the raw client; remove the object from the bucket
        minio_helper.client.remove_object(
            minio_helper.DEFAULT_BUCKET, trace.trace_filename
        )
    except Exception as e:
        print(f"Failed to delete trace file from MinIO: {e}")

    session.delete(trace)
    session.commit()
    return {"status": "success", "message": f"Trace {trace_id} deleted"}
    return {"status": "success", "message": f"Trace {trace_id} deleted"}


@router.post("", response_model=TraceDetail, status_code=201)
async def create_trace(
    trace_name: str = Form(...),
    trace_file: UploadFile = File(...),
    trace_timestamp: datetime.datetime = Form(...),
    configuration_id: Optional[str] = Form(None),
    device_id: Optional[str] = Form(None),
    session: SessionDepType = Depends(get_session),
    minio_helper: MinioHelper = Depends(get_minio_client),
):
    """Create/upload a new trace. Accepts form-data with a file upload and metadata.

    This endpoint is intentionally implemented with Form and File parameters
    to ensure full OpenAPI compatibility for auto-generated clients on the frontend.
    """
    try:
        # Read file bytes
        file_bytes = await trace_file.read()
        file_uuid = str(uuid.uuid4())
        file_name = f"{file_uuid}-{trace_file.filename}"

        # Upload to Minio
        if minio_helper is None:
            raise ValueError("Minio client is not initialized")
        minio_helper.upload_bytes(minio_helper.DEFAULT_BUCKET, file_name, file_bytes)

        # Try to get hostname, but don't fail if not set
        try:
            host_name = get_hostname()
        except Exception:
            host_name = None

        trace_kwargs = {
            "trace_id": str(uuid.uuid4()),
            "trace_name": trace_name,
            "trace_timestamp": trace_timestamp,
            "trace_filename": file_name,
        }
        if device_id is not None:
            trace_kwargs["device_id"] = device_id
        if host_name is not None:
            trace_kwargs["host_name"] = host_name
        if configuration_id is not None:
            trace_kwargs["configuration_id"] = configuration_id

        new_trace = Trace(**trace_kwargs)

        session.add(new_trace)
        session.commit()
        session.refresh(new_trace)

        # Fetch device and config for richer response
        device = None
        if new_trace.device_id:
            device = session.exec(
                select(Device).where(Device.device_id == new_trace.device_id)
            ).first()

        config = None
        if new_trace.configuration_id:
            config = session.exec(
                select(Config).where(Config.config_id == new_trace.configuration_id)
            ).first()

        resp = TraceDetail(
            trace_id=new_trace.trace_id,
            trace_name=new_trace.trace_name,
            trace_timestamp=new_trace.trace_timestamp.isoformat(),
            trace_filename=new_trace.trace_filename,
            device_id=new_trace.device_id or "",
            device_name=device.device_name if device else "",
            host_name=new_trace.host_name,
            configuration_id=new_trace.configuration_id or "",
            configuration_name=config.config_name if config else None,
            configuration_type=config.tracing_tool if config else None,
        )

        return resp

    except Exception as e:
        # Surface a clear HTTP error for client
        raise HTTPException(status_code=500, detail=str(e))
