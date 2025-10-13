import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from sqlmodel import select, desc
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

from src.common.db import Trace, get_session
from src.controllers import devices_router, traces_router, queries_router, configs_router
from src.controllers.jobs import app as jobs_router
from src.services.background import background_task
from src.services.startup import handle_on_startup


# This async wrapper will call your existing synchronous background_task
async def run_background_task():
    """
    A wrapper that runs the imported background task every 5 seconds.
    """
    while True:
        try:
            print(f"[{time.strftime('%X')}] Running periodic task...")
            background_task()  # Calling your synchronous function
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            print("Periodic task was cancelled.")
            break
        except Exception as e:
            print(f"An error occurred in the periodic task: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    """
    print("Application starting up...")
    # Run your original startup logic
    handle_on_startup()

    # Start the background task
    task = asyncio.create_task(run_background_task())

    yield

    # --- Code after yield runs on shutdown ---
    print("Application shutting down...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("Background task has been successfully cancelled.")


# --- 4. Pass the lifespan manager to the FastAPI app ---
app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 5. The old on_startup event is no longer needed ---
# @app.on_event("startup")
# async def on_startup():
#     handle_on_startup()


app.include_router(devices_router)
app.include_router(traces_router)
app.include_router(queries_router)
app.include_router(configs_router)
app.include_router(jobs_router)


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request, session=Depends(get_session)):
    traces = session.exec(select(Trace).order_by(desc(Trace.trace_timestamp))).all()

    return RedirectResponse("/traces", status_code=303)
