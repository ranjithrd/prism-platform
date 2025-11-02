from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from src.common.db import Host, SessionDepType, get_session
from src.common.device import calculate_status

router = APIRouter(prefix="/v1/api/hosts", tags=["hosts"])


class HostWithStatus(Host):
    status: str


@router.get("", response_model=List[HostWithStatus])
def get_hosts(
    session: SessionDepType = Depends(get_session),
):
    """Get all hosts"""
    hosts = session.exec(select(Host).order_by(Host.host_name)).all()
    hosts_with_status = []
    for host in hosts:
        host_with_status = HostWithStatus(
            host_name=host.host_name,
            last_seen=host.last_seen,
            status=calculate_status(host.last_seen, 60 * 2),
        )
        hosts_with_status.append(host_with_status)
    return hosts_with_status


@router.post("/{host_id}/delete")
def delete_host(host_id: str, session: SessionDepType = Depends(get_session)):
    """Delete a host by ID"""
    host = session.exec(select(Host).where(Host.host_name == host_id)).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    session.delete(host)
    session.commit()
    return {"status": "success", "message": f"Host {host_id} deleted"}
