import uuid

import dotenv
from sqlmodel import select

from src.common.hostname import get_hostname

dotenv.load_dotenv()

from src.common.db import create_tables, Session, engine, Host, Device
from src.common.redis_client import initialize_redis_client, get_redis_client
from src.common.adb import adb_devices
from src.common.minio import initialize_minio_client


def update_devices_in_redis():
    devices = adb_devices()
    redis_client = get_redis_client()
    online_devices = []
    hostname = get_hostname()
    for device in devices:
        serial = device.get("serial")
        state = device.get("state")
        if serial and state:
            online_devices.append(serial)
            if redis_client:
                redis_client.update_device_status(serial, "online" if state == "device" else "offline", hostname)
                print(f"Updated device status in Redis: {serial} is {state}")

            with Session(engine) as session:
                existing_device = session.exec(select(Device).where(Device.device_uuid == serial)).first()
                if not existing_device:
                    new_device = Device(device_id=str(uuid.uuid4()), device_name=serial, device_uuid=serial)
                    session.add(new_device)
                    session.commit()
                    print(f"Added device to DB: {new_device.device_name}")

    # Mark devices not currently online as offline
    if redis_client:
        all_device_statuses = redis_client.get_all_device_statuses()
        for device_id, status_info in all_device_statuses.items():
            if device_id not in online_devices and status_info["current_host"] == hostname:
                redis_client.update_device_status(device_id, "offline", None)
                print(f"Marked device as offline in Redis: {device_id}")


def handle_on_startup():
    create_tables()
    initialize_minio_client()
    initialize_redis_client()

    with Session(engine) as session:
        hostname = get_hostname()

        existing_host = session.exec(select(Host).where(Host.host_name == hostname)).first()
        if not existing_host:
            new_host = Host(host_name=hostname)
            session.add(new_host)
            session.commit()
            print(f"Added host: {new_host.host_name}")

    # update in redis
    redis_client = get_redis_client()
    if redis_client:
        redis_client.update_host_status(hostname, "online")
        print(f"Updated host status in Redis: {hostname} is online")

        update_devices_in_redis()
