import dotenv
from sqlmodel import select

from src.common.hostname import get_hostname

dotenv.load_dotenv()

from src.common.db import create_tables, Session, engine, Host
from src.common.minio import initialize_minio_client


def handle_on_startup():
    create_tables()
    initialize_minio_client()

    with Session(engine) as session:
        hostname = get_hostname()

        existing_host = session.exec(select(Host).where(Host.host_name == hostname)).first()
        if not existing_host:
            new_host = Host(host_name=hostname)
            session.add(new_host)
            session.commit()
            print(f"Added host: {new_host.host_name}")
