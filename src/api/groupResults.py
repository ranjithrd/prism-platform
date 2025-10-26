import csv
import datetime
import io
import json
import uuid
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as QueryParam
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import select

from src.common.db import Device, Query, SessionDepType, Trace, get_session
from src.common.minio import MinioHelper, get_minio_client
from src.common.perfetto_analysis import run_perfetto_query
from src.services.datatables_filter import process_inmemory_datatable
from src.services.result_cache import get_cached_result, set_cached_result

router = APIRouter(prefix="/v1/api/group_results", tags=["group_results"])


class TraceWithDevice(Trace):
    device_name: str
    device_serial: str


def get_or_compute_grouped_result(
    trace_ids: List[str],
    query_id: str,
    minio: MinioHelper,
    traces: List[TraceWithDevice],
    session: SessionDepType = Depends(get_session),
) -> Dict[str, Any]:
    """Get cached result or compute it"""
    cache_key = f"{','.join(trace_ids)}_{query_id}"
    cached = get_cached_result(cache_key)

    if cached:
        return cached

    trace_rows = []
    trace_cols = []

    for trace in traces:
        if trace.trace_id not in trace_ids:
            continue

        trace_id = trace.trace_id
        trace_device_id = trace.device_id
        print("Trace DB Timestamp:", trace.trace_timestamp)
        utc_timestamp = trace.trace_timestamp.replace(tzinfo=datetime.timezone.utc)
        print("UTC Timestamp:", utc_timestamp.isoformat())
        trace_timestamp = utc_timestamp.timestamp() * 1000
        print("Trace Timestamp (ms):", trace_timestamp)
        trace_device_serial = trace.device_serial

        perfetto_results = run_perfetto_query(
            trace_id=trace_id, query_id=query_id, session=session, minio=minio
        )
        for row in perfetto_results["rows"]:
            new_row = list(row) + [
                trace_id,
                trace_device_id,
                trace_device_serial,
                trace_timestamp,
            ]
            trace_rows.append(new_row)

        print("Trace ID:", trace_id)
        print("Number of rows returned:", len(perfetto_results["rows"]))

        for col in perfetto_results["columns"]:
            if col not in trace_cols:
                trace_cols.append(col)

    trace_cols.extend(
        ["prm_trace_id", "prm_device_id", "prm_device_serial", "prm_timestamp"]
    )

    full_data = {
        "columns": trace_cols,
        "rows": trace_rows,
    }

    set_cached_result(cache_key, full_data)
    return full_data


def get_traces(trace_ids: List[str], session: SessionDepType) -> List[TraceWithDevice]:
    traces = session.exec(
        select(Trace, Device).join(Device).where(Trace.trace_id.in_(trace_ids))
    ).all()

    trace_list = []
    for trace, device in traces:
        trace_with_device = TraceWithDevice(
            trace_id=trace.trace_id,
            trace_name=trace.trace_name,
            trace_timestamp=trace.trace_timestamp,
            trace_filename=trace.trace_filename,
            device_id=trace.device_id,
            host_name=trace.host_name,
            configuration_id=trace.configuration_id,
            device_name=device.device_name,
            device_serial=device.device_uuid,
        )
        trace_list.append(trace_with_device)

    return trace_list


@router.get("/{query_id}/export")
def export_result(
    query_id: str,
    trace_ids: str = QueryParam(..., description="Comma-separated Trace IDs"),
    file_format: Literal["csv", "tsv", "json"] = QueryParam(
        ..., description="Export format"
    ),
    session: SessionDepType = Depends(get_session),
    minio: MinioHelper = Depends(get_minio_client),
):
    """Export query results in various formats"""
    trace_ids_list = trace_ids.split(",")
    traces = get_traces(trace_ids_list, session)
    query = session.exec(select(Query).where(Query.query_id == query_id)).first()

    newfilename = f"{str(uuid.uuid4())}_{query_id}"

    if not traces or not query:
        raise HTTPException(status_code=404, detail="Trace or query not found")

    try:
        result = get_or_compute_grouped_result(
            trace_ids_list, query_id, minio, traces, session
        )
        columns = result["columns"]
        rows = result["rows"]

        print("Exporting result:")
        print("number of rows:", len(rows))
        print("filename: ", newfilename)

        if file_format == "json":
            output = io.StringIO()
            data = [dict(zip(columns, row)) for row in rows]
            json.dump(data, output, indent=2)
            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename={newfilename}.json"
                },
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
                headers={
                    "Content-Disposition": f"attachment; filename={newfilename}.csv"
                },
            )

        elif file_format == "tsv":
            output = io.StringIO()
            writer = csv.writer(output, delimiter="\t")
            writer.writerow(columns)
            writer.writerows(rows)
            output.seek(0)

            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/tab-separated-values",
                headers={
                    "Content-Disposition": f"attachment; filename={newfilename}.tsv"
                },
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting result: {str(e)}")


@router.get("/{query_id}/datatables")
async def get_datatables_result(
    request: Request,
    query_id: str,
    trace_ids: str = QueryParam(..., description="Comma-separated Trace IDs"),
    session: SessionDepType = Depends(get_session),
    minio: MinioHelper = Depends(get_minio_client),
):
    """Get query results formatted for DataTables"""
    trace_ids_list = trace_ids.split(",")
    traces = get_traces(trace_ids_list, session)
    query = session.exec(select(Query).where(Query.query_id == query_id)).first()

    if not traces or not query:
        raise HTTPException(status_code=404, detail="Trace or query not found")

    try:
        result = get_or_compute_grouped_result(
            trace_ids_list, query_id, minio, traces, session
        )
        columns = result["columns"]
        rows = result["rows"]

        query_params = dict(request.query_params)
        dt_result = process_inmemory_datatable(query_params, columns, rows)

        return JSONResponse(content=dt_result)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing datatables: {str(e)}"
        )


@router.get("/{query_id}/json")
def get_json_result(
    query_id: str,
    trace_ids: str = QueryParam(..., description="Comma-separated Trace IDs"),
    session: SessionDepType = Depends(get_session),
    minio: MinioHelper = Depends(get_minio_client),
):
    """Get query results as JSON"""
    trace_ids_list = trace_ids.split(",")
    traces = get_traces(trace_ids_list, session)
    query = session.exec(select(Query).where(Query.query_id == query_id)).first()

    if not traces or not query:
        raise HTTPException(status_code=404, detail="Trace or query not found")

    try:
        result = get_or_compute_grouped_result(
            trace_ids_list, query_id, minio, traces, session
        )
        columns = result["columns"]
        rows = result["rows"]

        data = [dict(zip(columns, row)) for row in rows]

        return JSONResponse(
            content={"columns": columns, "data": data, "count": len(data)}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting result: {str(e)}")
