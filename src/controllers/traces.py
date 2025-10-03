import datetime
import uuid

from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from sqlmodel import select
from starlette.responses import HTMLResponse, RedirectResponse

from src.common.db import get_session, Trace, Device, Query
from src.common.hostname import get_hostname
from src.common.minio import MinioHelper, get_minio_client
from src.common.perfetto_analysis import run_perfetto_query
from src.common.templates import templates
from src.services.datatables_filter import process_inmemory_datatable
from src.services.result_cache import get_cached_result, set_cached_result

app = APIRouter()


@app.get("/traces", response_class=HTMLResponse)
def read_traces(request: Request, session=Depends(get_session)):
    traces = session.exec(select(Trace, Device).join(Device).order_by(Trace.trace_timestamp.desc())).all()

    return templates.TemplateResponse(
        "traces/browse.html",
        context={
            "request": request,
            "traces": traces,
        },
    )


@app.get("/traces/add", response_class=HTMLResponse)
def read_add_trace(request: Request, session=Depends(get_session)):
    devices = session.exec(select(Device).order_by(Device.device_name)).all()
    return templates.TemplateResponse(
        "traces/add.html",
        context={
            "request": request,
            "devices": devices,
        },
    )


@app.post("/traces/add", response_class=HTMLResponse)
async def add_trace(request: Request, trace_name: str = Form(...), device_id: str = Form(...),
                    trace_timestamp: datetime.datetime = Form(...), trace_file: UploadFile = File(...),
                    session=Depends(get_session), minio_helper: MinioHelper = Depends(get_minio_client)):
    try:
        file_content = await trace_file.read()
        file_uuid = str(uuid.uuid4())
        file_name = f"{file_uuid}-{trace_file.filename}"

        minio_helper.upload_bytes("traces", file_name, file_content)

        new_trace = Trace(
            trace_id=str(uuid.uuid4()),
            trace_name=trace_name,
            device_id=device_id,
            trace_timestamp=trace_timestamp,
            trace_filename=file_name,
            host_name=get_hostname(),
        )
        session.add(new_trace)
        session.commit()
        session.refresh(new_trace)

        return RedirectResponse("/traces", status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )


@app.get("/traces/{trace_id}", response_class=HTMLResponse)
def read_trace(request: Request, trace_id: str, session=Depends(get_session)):
    trace = session.exec(select(Trace, Device).join(Device).where(Trace.trace_id == trace_id)).first()
    queries_raw = session.exec(select(Query).order_by(Query.updated_at)).all()
    queries = [
        {
            "query_id": q.query_id,
            "query_name": q.query_name,
            "query_text": q.query_text
        }
        for q in queries_raw
    ]
    if not trace:
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": "No trace found",
            }
        )
    return templates.TemplateResponse(
        "traces/read.html",
        context={
            "request": request,
            "trace": trace,
            "queries": queries,
            "result": None,
        }
    )


@app.get("/traces/{trace_id}/download", response_class=HTMLResponse)
def download_trace(request: Request, trace_id: str, session=Depends(get_session),
                   minio_helper: MinioHelper = Depends(get_minio_client)):
    trace = session.exec(select(Trace).where(Trace.trace_id == trace_id)).first()
    if not trace:
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": "No trace found",
            }
        )
    try:
        presigned_url = minio_helper.get_presigned_url(minio_helper.DEFAULT_BUCKET, trace.trace_filename)
        return RedirectResponse(presigned_url, status_code=303)
    except Exception as e:
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )


@app.get("/traces/{trace_id}/query/{query_id}", response_class=HTMLResponse)
def execute_query(request: Request, trace_id: str, query_id: str, session=Depends(get_session),
                  minio_helper: MinioHelper = Depends(get_minio_client)):
    try:
        trace = session.exec(select(Trace, Device).join(Device).where(Trace.trace_id == trace_id)).first()
        query = session.exec(select(Query).where(Query.query_id == query_id)).first()
        queries_raw = session.exec(select(Query).order_by(Query.updated_at)).all()
        queries = [
            {
                "query_id": q.query_id,
                "query_name": q.query_name,
                "query_text": q.query_text
            } for q in queries_raw
        ]

        if trace and query:
            key = f"{trace_id}_{query_id}"
            print(f"Query for trace {trace[0].trace_id}: {query.query_name}")

            query_result = run_perfetto_query(trace_id=trace[0].trace_id, query_id=query.query_id, session=session,
                                              minio=minio_helper)

            res = {
                "columns": query_result['columns'],
                "endpoint": f"/traces/{trace_id}/query/{query_id}/data",
            }

            full_data = {
                "columns": res['columns'],
                "rows": query_result['rows'],
            }

            set_cached_result(key, full_data)

            return templates.TemplateResponse(
                "traces/read.html",
                context={
                    "request": request,
                    "trace": trace,
                    "queries": queries,
                    "result": res,
                }
            )
        else:
            return templates.TemplateResponse(
                "error.html",
                context={
                    "request": request,
                    "error": "Trace or Query not found",
                }
            )

    except Exception as e:
        raise e
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )


@app.post("/traces/{trace_id}/query/{query_id}/data")
async def get_query_data(
        request: Request,
        trace_id: str,
        query_id: str
):
    try:
        key = f"{trace_id}_{query_id}"
        # get_cached_result should return a dict like {'columns': [...], 'rows': [[...], ...]}
        result_data = get_cached_result(key)

        if result_data and result_data['rows']:
            # Convert the Starlette form data to a simple dictionary
            request_dict = {key: val for key, val in (await request.form()).items()}

            # Call the new robust processing function
            return process_inmemory_datatable(
                request_dict=request_dict,
                columns=result_data['columns'],
                source_data=result_data['rows']
            )
        else:
            # Return an empty response if there's no data
            return {
                "draw": int((await request.form()).get("draw", 0)),
                "recordsTotal": 0,
                "recordsFiltered": 0,
                "data": []
            }

    except Exception as e:
        return {
            "data": [],
            "error": str(e)
        }


@app.post("/traces/{trace_id}/delete", response_class=HTMLResponse)
async def delete_trace(request: Request, trace_id: str, session=Depends(get_session),
                       minio_helper: MinioHelper = Depends(get_minio_client)):
    try:
        trace = session.exec(select(Trace).where(Trace.trace_id == trace_id)).first()
        if trace:
            # Delete the file from Minio
            minio_helper.client.remove_object(minio_helper.DEFAULT_BUCKET, trace.trace_filename)

            session.delete(trace)
            session.commit()
        return RedirectResponse("/traces", status_code=303)
    except Exception as e:
        session.rollback()
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": str(e),
            }
        )
