import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import desc, select
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from src.api import configurations_router
from src.api import devices_router as api_devices_router
from src.api import group_results_router as api_group_results_router
from src.api import hosts_router
from src.api import queries_router as api_queries_router
from src.api import requests_router, results_router
from src.api import traces_router as api_traces_router
from src.common.db import Trace, get_session
from src.controllers import (
    configs_router,
    devices_router,
    queries_router,
    traces_router,
)
from src.controllers.jobs import app as jobs_router
from src.services.startup import handle_on_startup, update_host_status_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    print("Application starting up...")
    # Run your original startup logic
    handle_on_startup()

    # # Start the background task
    task = asyncio.create_task(update_host_status_service())

    yield

    # # --- Code after yield runs on shutdown ---
    print("Application shutting down...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("Background task has been successfully cancelled.")


# --- 4. Pass the lifespan manager to the FastAPI app ---
app = FastAPI(
    lifespan=lifespan,
    title="Prism Platform API",
    description="API for managing traces, configurations, devices, and queries",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow Cross Origin requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Include HTML/template-based routers
app.include_router(devices_router)
app.include_router(traces_router)
app.include_router(queries_router)
app.include_router(configs_router)
app.include_router(jobs_router)

# Include REST API routers
app.include_router(hosts_router)
app.include_router(api_devices_router)
app.include_router(configurations_router)
app.include_router(api_traces_router)
app.include_router(api_queries_router)
app.include_router(results_router)
app.include_router(requests_router)
app.include_router(api_group_results_router)


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, session=Depends(get_session)):
    traces = session.exec(select(Trace).order_by(desc(Trace.trace_timestamp))).all()

    return RedirectResponse("/traces", status_code=303)
