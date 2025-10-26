import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.services.background import run_listen_pubsub, run_update_devices
from src.services.startup import handle_on_startup, update_host_status_service_sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Code before yield runs on startup ---
    print("--- Worker application starting up... ---")

    # Call the startup handler
    handle_on_startup()

    # Start the background task
    devices_thread = threading.Thread(target=run_update_devices)
    devices_thread.daemon = True

    pubsub_thread = threading.Thread(target=run_listen_pubsub)
    pubsub_thread.daemon = True

    status_update_thread = threading.Thread(target=update_host_status_service_sync)
    status_update_thread.daemon = True

    print("Starting devices thread...")
    devices_thread.start()

    print("Starting pubsub listener thread...")
    pubsub_thread.start()

    print("Starting status update thread...")
    status_update_thread.start()

    yield

    # --- Code after yield runs on shutdown ---
    print("--- Worker application shutting down... ---")
    devices_thread.join(timeout=3)
    pubsub_thread.join(timeout=5)
    status_update_thread.join(timeout=3)

    print("--- Shutdown complete. ---")


# --- Create the FastAPI App ---
app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    """A simple health check endpoint."""
    return "PRISM Worker running"
