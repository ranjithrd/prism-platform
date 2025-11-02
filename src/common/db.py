import datetime
import os
import uuid
from typing import Annotated

from dotenv import load_dotenv
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine

load_dotenv()

db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)


class Host(SQLModel, table=True):
    __tablename__ = "hosts"

    host_name: str = Field(str, primary_key=True)
    host_type: str = Field(str, nullable=True)
    host_key: str | None = Field(str, nullable=True)
    last_seen: datetime.datetime | None = Field(datetime.datetime, nullable=True)


class Device(SQLModel, table=True):
    __tablename__ = "devices"

    device_id: str = Field(str, primary_key=True)
    device_name: str = Field(str, nullable=False)
    device_uuid: str = Field(str, nullable=True)
    last_status: str | None = Field(default=None, nullable=True)
    last_seen: datetime.datetime | None = Field(default=None, nullable=True)
    host: str | None = Field(default=None, nullable=True)


class Trace(SQLModel, table=True):
    __tablename__ = "traces"

    trace_id: str = Field(str, primary_key=True)
    trace_timestamp: datetime.datetime = Field(datetime.datetime, nullable=False)
    trace_filename: str = Field(str, nullable=False)
    trace_name: str = Field(str, nullable=False)
    device_id: str = Field(default=None, foreign_key="devices.device_id")
    host_name: str = Field(default=None, foreign_key="hosts.host_name")
    configuration_id: str = Field(
        default=None,
        nullable=True,
        foreign_key="configs.config_id",
        sa_column_kwargs={"index": True},
    )


class Query(SQLModel, table=True):
    __tablename__ = "queries"

    query_id: str = Field(str, primary_key=True)
    query_name: str = Field(str, nullable=False)
    query_text: str = Field(str, nullable=False)

    configuration_id: str = Field(
        default=None, nullable=True, foreign_key="configs.config_id"
    )

    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.datetime.utcnow},
    )


class Config(SQLModel, table=True):
    __tablename__ = "configs"

    config_id: str = Field(str, primary_key=True)
    config_name: str = Field(str, nullable=False)
    config_text: str = Field(str, nullable=False)
    tracing_tool: str = Field(str, nullable=True)
    default_duration: int = Field(int, nullable=True)

    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.datetime.utcnow},
    )


class JobDevice(SQLModel, table=True):
    __tablename__ = "job_devices"

    id: str = Field(primary_key=True, default_factory=lambda: str(uuid.uuid4()))
    job_id: str = Field(foreign_key="job_requests.job_id")
    device_id: str = Field(foreign_key="devices.device_id")
    status: str = Field(default="pending")  # pending, running, completed, failed

    # Relationship - will be set up after JobRequest is defined
    job_request: "JobRequest" = Relationship(back_populates="job_devices")


class JobRequest(SQLModel, table=True):
    __tablename__ = "job_requests"

    job_id: str = Field(primary_key=True)
    config_id: str = Field(foreign_key="configs.config_id")
    status: str = Field()
    duration: int = Field(nullable=True)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    # join table with job device as part of preload
    job_devices: list[JobDevice] = Relationship(back_populates="job_request")

    result_summary: str | None = Field(default=None, nullable=True)


class JobUpdate(SQLModel, table=True):
    __tablename__ = "job_updates"

    update_id: str = Field(primary_key=True, default_factory=lambda: str(uuid.uuid4()))
    job_id: str = Field(foreign_key="job_requests.job_id")
    device_id: str = Field(
        foreign_key="devices.device_id"
    )  # Changed from device_serial
    status: str = Field()
    message: str | None = Field(default=None, nullable=True)
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    trace_id: str | None = Field(
        default=None, foreign_key="traces.trace_id", nullable=True
    )


def create_tables():
    """Create all tables. Handles existing tables gracefully."""
    try:
        SQLModel.metadata.create_all(engine, checkfirst=True)
    except Exception as e:
        # Log but don't fail if tables already exist
        print(f"Warning during table creation (may be harmless): {e}")


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, SQLModel]
SessionDepType = Session
