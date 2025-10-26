import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import desc, select

from src.common.db import Config, Device, SessionDepType, Trace, get_session

router = APIRouter(prefix="/v1/api/configurations", tags=["configurations"])


class ConfigCreate(BaseModel):
    config_name: str
    config_text: str
    tracing_tool: Optional[str] = None
    default_duration: Optional[int] = 10


class ConfigUpdate(BaseModel):
    config_name: str
    config_text: str
    tracing_tool: Optional[str] = None
    default_duration: Optional[int] = 10


class TraceWithDevice(BaseModel):
    trace_id: str
    trace_name: str
    trace_timestamp: str
    trace_filename: str
    device_id: str
    device_name: str
    host_name: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("", response_model=List[Config])
def get_configurations(session: SessionDepType = Depends(get_session)):
    """Get all configurations"""
    configs = session.exec(select(Config).order_by(Config.config_name)).all()
    return configs


@router.post("", response_model=Config)
def create_configuration(
    config: ConfigCreate, session: SessionDepType = Depends(get_session)
):
    """Create a new configuration"""
    new_config = Config(
        config_id=str(uuid.uuid4()),
        config_name=config.config_name,
        config_text=config.config_text,
        tracing_tool=config.tracing_tool,
        default_duration=config.default_duration,
    )
    session.add(new_config)
    session.commit()
    session.refresh(new_config)
    return new_config


@router.get("/{config_id}", response_model=Config)
def get_configuration(config_id: str, session: SessionDepType = Depends(get_session)):
    """Get a specific configuration"""
    config = session.exec(select(Config).where(Config.config_id == config_id)).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config


@router.post("/{config_id}/edit", response_model=Config)
def edit_configuration(
    config_id: str, config: ConfigUpdate, session: SessionDepType = Depends(get_session)
):
    """Edit an existing configuration"""
    db_config = session.exec(
        select(Config).where(Config.config_id == config_id)
    ).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    db_config.config_name = config.config_name
    db_config.config_text = config.config_text
    db_config.tracing_tool = config.tracing_tool
    db_config.default_duration = config.default_duration
    session.add(db_config)
    session.commit()
    session.refresh(db_config)
    return db_config


@router.post("/{config_id}/delete")
def delete_configuration(
    config_id: str, session: SessionDepType = Depends(get_session)
):
    """Delete a configuration"""
    config = session.exec(select(Config).where(Config.config_id == config_id)).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    session.delete(config)
    session.commit()
    return {"status": "success", "message": f"Configuration {config_id} deleted"}


@router.get("/{config_id}/traces", response_model=List[TraceWithDevice])
def get_configuration_traces(
    config_id: str,
    session: SessionDepType = Depends(get_session),
    n: Optional[int] = Query(None, description="Number of traces to return"),
    devices: Optional[str] = Query(None, description="Comma-separated device IDs"),
):
    if not n:
        n = 1

    """Get traces for a configuration, optionally filtered by devices and limited by count"""
    config = session.exec(select(Config).where(Config.config_id == config_id)).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    subquery = (
        select(
            Trace.trace_id,
            Device.device_id,
            func.row_number()
            .over(partition_by=Device.device_id, order_by=desc(Trace.trace_timestamp))
            .label("row_num"),
        )
        .join(
            Device,
        )
        .where(Trace.configuration_id == config_id, Trace.device_id == Device.device_id)
    )

    if devices:
        subquery = subquery.where(
            Device.device_id.in_([d.strip() for d in devices.split(",")])
        )
    subquery = subquery.subquery("ranked_traces")

    final_query = (
        select(Trace, Device)
        .join(subquery, Trace.trace_id == subquery.c.trace_id)
        .join(Device, Device.device_id == subquery.c.device_id)
        .where(
            subquery.c.row_num <= n,
        )
        .order_by(Device.device_id, subquery.c.row_num)
    )

    results = session.exec(final_query).all()

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
            )
        )

    return traces_with_devices
