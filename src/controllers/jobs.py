import json

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlmodel import select

from src.common.db import get_session, Config
from src.common.templates import templates
from src.services.job_requests import JobRequestService

app = APIRouter()


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
def view_job_result(request: Request, job_id: str, session=Depends(get_session)):
    """View job result page with SSE updates"""
    job_service = JobRequestService(session)
    job_request = job_service.get_job_request(job_id)

    if not job_request:
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": "Job request not found",
            }
        )

    # Get config details
    config = session.exec(select(Config).where(Config.config_id == job_request.config_id)).first()

    # Get devices involved
    devices = job_service.get_all_devices_for_job(job_request)
    device_serials = json.loads(job_request.device_serials)

    return templates.TemplateResponse(
        "jobs/result.html",
        context={
            "request": request,
            "job_request": job_request,
            "config": config,
            "devices": devices,
            "device_serials": device_serials,
        }
    )


@app.get("/jobs/{job_id}/stream")
def job_updates_stream(job_id: str, session=Depends(get_session)):
    """Server-Sent Events endpoint for job updates"""
    job_service = JobRequestService(session)

    def event_stream():
        yield "data: {\"type\": \"connected\"}\n\n"

        for update in job_service.get_job_updates_stream(job_id):
            yield update

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/jobs/run")
async def create_job_request(
        request: Request,
        config_id: str = Form(...),
        device_serials: str = Form(...),  # JSON string or comma-separated
        redirect_url: str = Form(None),
        session=Depends(get_session)
):
    """Create a new job request"""
    try:
        # Parse device serials - handle various formats
        device_serials = device_serials.strip()

        if not device_serials:
            raise ValueError("No device serials provided")

        # Try to parse as JSON first
        try:
            if device_serials.startswith('['):
                serials_list = json.loads(device_serials)
            else:
                # Comma-separated format
                serials_list = [s.strip() for s in device_serials.split(',') if s.strip()]
        except json.JSONDecodeError as e:
            # If JSON parsing fails, treat as comma-separated
            serials_list = [s.strip() for s in device_serials.split(',') if s.strip()]

        if not serials_list:
            raise ValueError("No valid device serials after parsing")

        print(f"Creating job request for config {config_id} with devices: {serials_list}")

        job_service = JobRequestService(session)
        job_request = job_service.create_job_request(config_id, serials_list)

        # Always redirect to the job result page to see real-time updates
        return RedirectResponse(f"/jobs/{job_request.job_id}", status_code=303)

    except Exception as e:
        print(f"Error creating job request: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return templates.TemplateResponse(
            "error.html",
            context={
                "request": request,
                "error": f"Failed to create job request: {str(e)}",
            }
        )
