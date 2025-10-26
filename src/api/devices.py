import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from src.common.db import SessionDepType, get_session, Device, DeviceWithRedisInfo
from src.common.redis_client import get_redis_client

router = APIRouter(prefix="/v1/api/devices", tags=["devices"])


class DeviceCreate(BaseModel):
    device_name: str
    device_uuid: Optional[str] = None


class DeviceUpdate(BaseModel):
    device_name: str
    device_uuid: Optional[str] = None


@router.get("", response_model=List[DeviceWithRedisInfo])
def get_devices(session: SessionDepType = Depends(get_session), redis_client=Depends(get_redis_client)):
    """Get all devices with status information"""
    devices = session.exec(select(Device).order_by(Device.device_name)).all()

    devices_with_status: List[DeviceWithRedisInfo] = []
    for device in devices:
        device_info = DeviceWithRedisInfo.from_orm(device)
        if redis_client and device.device_uuid:
            status_info = redis_client.get_device_status(device.device_uuid)
            if status_info:
                device_info.status = status_info.get("status")
                device_info.host = status_info.get("current_host")
        devices_with_status.append(device_info)

    return devices_with_status


@router.post("", response_model=Device)
def create_device(device: DeviceCreate, session: SessionDepType = Depends(get_session)):
    """Create a new device"""
    new_device = Device(
        device_id=str(uuid.uuid4()),
        device_name=device.device_name,
        device_uuid=device.device_uuid
    )
    session.add(new_device)
    session.commit()
    session.refresh(new_device)
    return new_device


@router.post("/{device_id}/edit", response_model=Device)
def edit_device(device_id: str, device: DeviceUpdate, session: SessionDepType = Depends(get_session)):
    """Edit an existing device"""
    db_device = session.exec(select(Device).where(Device.device_id == device_id)).first()
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")

    db_device.device_name = device.device_name
    db_device.device_uuid = device.device_uuid
    session.add(db_device)
    session.commit()
    session.refresh(db_device)
    return db_device


@router.post("/{device_id}/delete")
def delete_device(device_id: str, session: SessionDepType = Depends(get_session)):
    """Delete a device"""
    device = session.exec(select(Device).where(Device.device_id == device_id)).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    session.delete(device)
    session.commit()
    return {"status": "success", "message": f"Device {device_id} deleted"}
