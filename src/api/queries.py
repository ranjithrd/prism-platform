import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import select

from src.common.db import SessionDepType, get_session, Query

router = APIRouter(prefix="/v1/api/queries", tags=["queries"])


class QueryCreate(BaseModel):
    query_name: str
    query_text: str
    configuration_id: Optional[str] = None


class QueryUpdate(BaseModel):
    query_name: str
    query_text: str
    configuration_id: Optional[str] = None


@router.get("", response_model=List[Query])
def get_queries(session: SessionDepType = Depends(get_session)):
    """Get all queries"""
    queries = session.exec(select(Query).order_by(Query.query_name)).all()
    return queries


@router.get("/{query_id}", response_model=Query)
def get_query(query_id: str, session: SessionDepType = Depends(get_session)):
    """Get a specific query"""
    query = session.exec(select(Query).where(Query.query_id == query_id)).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    return query


@router.post("", response_model=Query)
def create_query(query: QueryCreate, session: SessionDepType = Depends(get_session)):
    """Create a new query"""
    new_query = Query(
        query_id=str(uuid.uuid4()),
        query_name=query.query_name,
        query_text=query.query_text,
        configuration_id=query.configuration_id
    )
    session.add(new_query)
    session.commit()
    session.refresh(new_query)
    return new_query


@router.post("/{query_id}/edit", response_model=Query)
def edit_query(query_id: str, query: QueryUpdate, session: SessionDepType = Depends(get_session)):
    """Edit an existing query"""
    db_query = session.exec(select(Query).where(Query.query_id == query_id)).first()
    if not db_query:
        raise HTTPException(status_code=404, detail="Query not found")

    db_query.query_name = query.query_name
    db_query.query_text = query.query_text
    db_query.configuration_id = query.configuration_id
    session.add(db_query)
    session.commit()
    session.refresh(db_query)
    return db_query


@router.post("/{query_id}/delete")
def delete_query(query_id: str, session: SessionDepType = Depends(get_session)):
    """Delete a query"""
    query = session.exec(select(Query).where(Query.query_id == query_id)).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    session.delete(query)
    session.commit()
    return {"status": "success", "message": f"Query {query_id} deleted"}
