import uuid

from fastapi import APIRouter, Depends, Request, Form, Body
from fastapi.responses import JSONResponse
from sqlmodel import select
from starlette.responses import HTMLResponse, RedirectResponse

from src.common.db import get_session, Query
from src.common.templates import templates

app = APIRouter()


@app.get("/queries", response_class=HTMLResponse)
def read_queries(request: Request, session=Depends(get_session)):
    queries = session.exec(select(Query).order_by(Query.query_name)).all()
    return templates.TemplateResponse(
        "queries/browse.html",
        context={
            "request": request,
            "queries": queries,
        },
    )


@app.get("/queries/add", response_class=HTMLResponse)
def read_add_query(request: Request):
    return templates.TemplateResponse(
        "queries/add.html",
        context={"request": request},
    )


@app.post("/queries/add", response_class=HTMLResponse)
async def add_query(request: Request, query_name: str = Form(...), query_text: str = Form(...),
                    redirect_to: str = Form(None), session=Depends(get_session)):
    try:
        new_query = Query(
            query_id=str(uuid.uuid4()),
            query_name=query_name,
            query_text=query_text
        )
        session.add(new_query)
        session.commit()
        session.refresh(new_query)

        # Use redirect_to if provided, otherwise default to /queries
        redirect_url = redirect_to if redirect_to else "/queries"
        return RedirectResponse(redirect_url, status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )


@app.get("/queries/{query_id}/edit", response_class=HTMLResponse)
def read_edit_query(request: Request, query_id: str, session=Depends(get_session)):
    query = session.exec(select(Query).where(Query.query_id == query_id)).first()
    if not query:
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": "No query found",
            }
        )
    return templates.TemplateResponse(
        "queries/edit.html",
        context={
            "request": request,
            "query": query,
        }
    )


@app.post("/queries/{query_id}/edit", response_class=HTMLResponse)
async def edit_query(request: Request, query_id: str, query_name: str = Form(...),
                     query_text: str = Form(...),
                     session=Depends(get_session)):
    try:
        query = session.exec(select(Query).where(Query.query_id == query_id)).first()
        query.query_name = query_name
        query.query_text = query_text
        session.commit()
        session.refresh(query)
        return RedirectResponse("/queries", status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )


@app.post("/queries/{query_id}/delete", response_class=HTMLResponse)
async def delete_query(request: Request, query_id: str, redirect_to: str = Form(None), session=Depends(get_session)):
    try:
        query = session.exec(select(Query).where(Query.query_id == query_id)).first()
        session.delete(query)
        session.commit()

        # Use redirect_to if provided, otherwise default to /queries
        redirect_url = redirect_to if redirect_to else "/queries"
        return RedirectResponse(redirect_url, status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )


@app.get("/queries/search")
def search_queries(term: str = "", session=Depends(get_session)):
    stmt = select(Query)
    if term:
        stmt = stmt.where(Query.query_name.contains(term) | Query.query_text.contains(term))
    queries = session.exec(stmt.order_by(Query.query_name)).all()
    return JSONResponse({
        "queries": [
            {
                "query_id": q.query_id,
                "query_name": q.query_name,
                "query_text": q.query_text
            } for q in queries
        ]
    })


@app.post("/queries/{query_id}/edit_ajax")
async def edit_query_ajax(query_id: str, data: dict = Body(...), session=Depends(get_session)):
    query = session.exec(select(Query).where(Query.query_id == query_id)).first()
    if not query:
        return JSONResponse({"error": "Query not found"}, status_code=404)
    query.query_name = data.get("query_name", query.query_name)
    query.query_text = data.get("query_text", query.query_text)
    session.add(query)
    session.commit()
    session.refresh(query)
    return JSONResponse({
        "query_id": query.query_id,
        "query_name": query.query_name,
        "query_text": query.query_text
    })
