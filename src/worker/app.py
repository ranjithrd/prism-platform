import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .background import run_listen_pubsub, run_update_devices, signal_shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Code before yield runs on startup ---
    print("--- Worker application starting up... ---")

    # Start the background task
    devices_thread = threading.Thread(target=run_update_devices, name="DevicesThread")
    devices_thread.daemon = True

    pubsub_thread = threading.Thread(target=run_listen_pubsub, name="PubSubThread")
    pubsub_thread.daemon = True

    print("Starting devices thread...")
    devices_thread.start()

    print("Starting pubsub listener thread...")
    pubsub_thread.start()

    yield

    # --- Code after yield runs on shutdown ---
    print("--- Worker application shutting down... ---")

    # Signal threads to stop
    signal_shutdown()

    # Wait for threads to finish (should be fast now with Event)
    devices_thread.join(timeout=1)
    pubsub_thread.join(timeout=1)

    print("--- Shutdown complete. ---")


# --- Create the FastAPI App ---
app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    """A simple health check endpoint."""
    return "PRISM Worker running"
