import datetime
import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends
from sqlmodel import SQLModel, Field, create_engine, Session

load_dotenv()

db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url)


class Device(SQLModel, table=True):
    __tablename__ = "devices"

    device_id: str = Field(str, primary_key=True)
    device_name: str = Field(str, nullable=False)
    device_uuid: str = Field(str, nullable=True)


class Host(SQLModel, table=True):
    __tablename__ = "hosts"

    host_name: str = Field(str, primary_key=True)


class Trace(SQLModel, table=True):
    __tablename__ = "traces"

    trace_id: str = Field(str, primary_key=True)
    trace_timestamp: datetime.datetime = Field(datetime.datetime, nullable=False)
    trace_filename: str = Field(str, nullable=False)
    trace_name: str = Field(str, nullable=False)
    device_id: str = Field(default=None, foreign_key="devices.device_id")
    host_name: str = Field(default=None, foreign_key="hosts.host_name")


class Query(SQLModel, table=True):
    __tablename__ = "queries"

    query_id: str = Field(str, primary_key=True)
    query_name: str = Field(str, nullable=False)
    query_text: str = Field(str, nullable=False)

    updated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"onupdate": datetime.datetime.utcnow}
    )


def create_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
