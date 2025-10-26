import csv
import io
import json
from typing import Literal, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Query as QueryParam
from fastapi.responses import StreamingResponse, JSONResponse
from sqlmodel import select

from src.common.db import Trace, Query, get_session, SessionDepType
from src.common.minio import MinioHelper, get_minio_client
from src.common.perfetto_analysis import run_perfetto_query
from src.services.datatables_filter import process_inmemory_datatable
from src.services.result_cache import get_cached_result, set_cached_result

router = APIRouter(prefix="/v1/api/results", tags=["results"])


def get_or_compute_result(trace_id: str, query_id: str, minio: MinioHelper,
                          session: SessionDepType = Depends(get_session)) -> Dict[str, Any]:
    """Get cached result or compute it"""
    cache_key = f"{trace_id}_{query_id}"
    cached = get_cached_result(cache_key)

    if cached:
        return cached

    result = run_perfetto_query(trace_id=trace_id, query_id=query_id, session=session, minio=minio)

    full_data = {
        "columns": result['columns'],
        "rows": result['rows'],
    }

    set_cached_result(cache_key, full_data)
    return full_data


@router.get("/{trace_id}/{query_id}/export")
def export_result(
        trace_id: str,
        query_id: str,
        file_format: Literal["csv", "tsv", "json"] = QueryParam(..., description="Export format"),
        session: SessionDepType = Depends(get_session),
        minio: MinioHelper = Depends(get_minio_client)
):
    """Export query results in various formats"""
    trace = session.exec(select(Trace).where(Trace.trace_id == trace_id)).first()
    query = session.exec(select(Query).where(Query.query_id == query_id)).first()

    if not trace or not query:
        raise HTTPException(status_code=404, detail="Trace or query not found")

    try:
        result = get_or_compute_result(trace_id, query_id, minio, session)
        columns = result['columns']
        rows = result['rows']

        if file_format == "json":
            output = io.StringIO()
            data = [dict(zip(columns, row)) for row in rows]
            json.dump(data, output, indent=2)
            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={trace_id}_{query_id}.json"}
            )

        elif file_format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(columns)
            writer.writerows(rows)
            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={trace_id}_{query_id}.csv"}
            )

        elif file_format == "tsv":
            output = io.StringIO()
            writer = csv.writer(output, delimiter='\t')
            writer.writerow(columns)
            writer.writerows(rows)
            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/tab-separated-values",
                headers={"Content-Disposition": f"attachment; filename={trace_id}_{query_id}.tsv"}
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting result: {str(e)}")


@router.get("/{trace_id}/{query_id}/datatables")
async def get_datatables_result(
        request: Request,
        trace_id: str,
        query_id: str,
        session: SessionDepType = Depends(get_session),
        minio: MinioHelper = Depends(get_minio_client)
):
    """Get query results formatted for DataTables"""
    trace = session.exec(select(Trace).where(Trace.trace_id == trace_id)).first()
    query = session.exec(select(Query).where(Query.query_id == query_id)).first()

    if not trace or not query:
        raise HTTPException(status_code=404, detail="Trace or query not found")

    try:
        result = get_or_compute_result(trace_id, query_id, minio, session)
        columns = result['columns']
        rows = result['rows']

        query_params = dict(request.query_params)
        dt_result = process_inmemory_datatable(query_params, columns, rows)

        return JSONResponse(content=dt_result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing datatables: {str(e)}")


@router.get("/{trace_id}/{query_id}/json")
def get_json_result(
        trace_id: str,
        query_id: str,
        session: SessionDepType = Depends(get_session),
        minio: MinioHelper = Depends(get_minio_client)
):
    """Get query results as JSON"""
    trace = session.exec(select(Trace).where(Trace.trace_id == trace_id)).first()
    query = session.exec(select(Query).where(Query.query_id == query_id)).first()

    if not trace or not query:
        raise HTTPException(status_code=404, detail="Trace or query not found")

    try:
        result = get_or_compute_result(trace_id, query_id, minio, session)
        columns = result['columns']
        rows = result['rows']

        data = [dict(zip(columns, row)) for row in rows]

        return JSONResponse(content={
            "columns": columns,
            "data": data,
            "count": len(data)
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting result: {str(e)}")
