from datetime import datetime, timezone

import dotenv
from sqlmodel import select

from src.common.db import Host, Session, create_tables, engine
from src.common.hostname import get_hostname
from src.common.minio import initialize_minio_client

dotenv.load_dotenv()


def update_host_status():
    print("Updating host status...")
    with Session(engine) as session:
        hostname = get_hostname()

        existing_host = session.exec(
            select(Host).where(Host.host_name == hostname)
        ).first()
        if existing_host:
            existing_host.last_seen = datetime.now(timezone.utc)
            session.add(existing_host)
            session.commit()
            print(f"Updated host last seen: {existing_host.host_name}")
        else:
            new_host = Host(host_name=hostname, last_seen=datetime.now(timezone.utc))
            session.add(new_host)
            session.commit()
            print(f"Added host: {new_host.host_name}")


async def update_host_status_service():
    import asyncio

    while True:
        update_host_status()
        await asyncio.sleep(15)


def update_host_status_service_sync():
    import time

    while True:
        update_host_status()
        time.sleep(15)
        time.sleep(15)


def handle_on_startup():
    create_tables()
    initialize_minio_client()
    update_host_status()
