from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import desc, select

from src.common.db import Host, SessionDepType, get_session
from src.common.device import calculate_status
from src.common.host_token import HostTokenPayload, create_host_token

router = APIRouter(prefix="/v1/api/hosts", tags=["hosts"])


class HostWithStatus(Host):
    status: str


class AddHostRequest(BaseModel):
    host_name: str


class GenerateHostKeyResponse(BaseModel):
    status: str
    host_name: str
    host_key: str


@router.get("", response_model=List[HostWithStatus])
def get_hosts(
    session: SessionDepType = Depends(get_session),
):
    """Get all hosts"""
    hosts = session.exec(
        select(Host).order_by(
            Host.last_seen.is_(None), desc(Host.last_seen), Host.host_name
        )
    ).all()
    hosts_with_status = []
    for host in hosts:
        host_with_status = HostWithStatus(
            host_name=host.host_name,
            last_seen=host.last_seen,
            host_type=host.host_type,
            host_key="",
            status=calculate_status(host.last_seen, 60),
        )
        hosts_with_status.append(host_with_status)
    return hosts_with_status


@router.post("/")
def add_host(
    host_request: AddHostRequest,
    session: SessionDepType = Depends(get_session),
):
    """Add a new host"""
    existing_host = session.exec(
        select(Host).where(Host.host_name == host_request.host_name)
    ).first()
    if existing_host:
        raise HTTPException(status_code=400, detail="Host already exists")

    new_host = Host(
        host_name=host_request.host_name,
        host_type="worker",
        host_key=None,
        last_seen=datetime.now(timezone.utc),
    )
    session.add(new_host)
    session.commit()
    session.refresh(new_host)
    return {"status": "success", "host_name": new_host.host_name}


@router.post("/{host_id}/key", response_model=GenerateHostKeyResponse)
def generate_key(
    request: Request,
    host_id: str,
    session: SessionDepType = Depends(get_session),
):
    """Generate and set a new key for the host"""
    host = session.exec(select(Host).where(Host.host_name == host_id)).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    base_url = request.base_url._url.rstrip("/")

    new_key = create_host_token(
        HostTokenPayload(hostname=host.host_name, api_url=base_url)
    )
    host.host_key = new_key
    session.add(host)
    session.commit()
    session.refresh(host)
    return {
        "status": "success",
        "host_name": host.host_name,
        "host_key": new_key,
    }


@router.post("/{host_id}/delete")
def delete_host(host_id: str, session: SessionDepType = Depends(get_session)):
    """Delete a host by ID"""
    host = session.exec(select(Host).where(Host.host_name == host_id)).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    session.delete(host)
    session.commit()
    return {"status": "success", "message": f"Host {host_id} deleted"}
