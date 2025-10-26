from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from src.common.db import Host, SessionDepType, get_session
from src.common.redis_client import RedisHelper, get_redis_client

router = APIRouter(prefix="/v1/api/hosts", tags=["hosts"])


class HostWithStatus(Host):
    status: str
    last_seen: str


@router.get("", response_model=List[HostWithStatus])
def get_hosts(
    session: SessionDepType = Depends(get_session),
    redis_client: RedisHelper = Depends(get_redis_client),
):
    """Get all hosts"""
    hosts = session.exec(select(Host).order_by(Host.host_name)).all()
    # merge with redis info
    hosts_with_status = []
    for host in hosts:
        host_with_status = HostWithStatus(
            host_name=host.host_name,
            status="",
            last_seen="",
        )
        redis_status = redis_client.get_host_status(host.host_name)
        if redis_status:
            host_with_status.status = redis_status.get("status", "offline")
            host_with_status.last_seen = redis_status.get("last_seen", "")
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
