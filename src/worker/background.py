import os
import threading
import uuid
from datetime import datetime, timezone

from src.common.adb import adb_devices, is_device_connected
from src.common.hostname import get_hostname

from .api import get_worker_client
from .run_perfetto import run_perfetto_trace

JOB_REQUEST_STREAM_NAME = "job_requests"

# Global shutdown event to signal threads to stop
_shutdown_event = threading.Event()

# Global GUI callback for device updates
_gui_device_callback = None

# Global GUI callback for error notifications
_gui_error_callback = None

# Track devices currently tracing - set of device UUIDs
_tracing_devices = set()


def register_gui_callback(callback):
    """Register a callback function for GUI device updates.

    Args:
        callback: Function that takes a list of tuples (serial, status, extra_info)
    """
    global _gui_device_callback
    _gui_device_callback = callback
    print("[GUI] Device update callback registered")


def register_error_callback(callback):
    """Register a callback function for error notifications.

    Args:
        callback: Function that takes an error message string
    """
    global _gui_error_callback
    _gui_error_callback = callback
    print("[GUI] Error callback registered")


def update_device_statuses():
    """Update device statuses in the database based on ADB connections.
    Also notifies GUI if callback is registered.
    """
    devices = adb_devices()
    online_devices = []
    hostname = get_hostname()
    client = get_worker_client()

    print("Logging connected devices:")
    print(devices)
    db_devices = client.get_existing_devices()
    print(db_devices)

    # Prepare GUI update list
    gui_device_list = []

    for device in devices:
        serial = device.get("serial")
        state = device.get("state")
        if serial and state:
            # Skip devices that are currently tracing - don't overwrite their status
            if serial in _tracing_devices:
                continue

            # Add to GUI list
            gui_device_list.append((serial, state, None))

            existing_device = next(
                (
                    d
                    for d in db_devices
                    if d["device_uuid"] == serial or d["device_id"] == serial
                ),
                None,
            )

            if not existing_device:
                new_id = str(uuid.uuid4())
                online_devices.append(new_id)
                client.add_new_device(
                    {
                        "device_id": new_id,
                        "device_name": serial,
                        "device_uuid": serial,
                        "last_seen": datetime.now(timezone.utc).isoformat(),
                        "last_status": "online",
                        "host": hostname,
                    }
                )
                print(f"Added device to DB: {serial}")
            else:
                existing_device["last_seen"] = datetime.now(timezone.utc).isoformat()
                existing_device["host"] = hostname
                existing_device["last_status"] = "online"
                online_devices.append(existing_device["device_id"])
                client.update_device(existing_device["device_id"], existing_device)
                print(f"Updated device in DB: {existing_device['device_name']}")

    for db_device in db_devices:
        if (db_device["device_id"] not in online_devices) and (
            db_device["last_status"] != "offline"
        ):
            db_device["last_status"] = "offline"
            client.update_device(db_device["device_id"], db_device)
            print(f"Marked device as offline in DB: {db_device['device_name']}")

    # Check for authentication errors and notify GUI
    if _gui_error_callback and client.last_auth_error:
        try:
            _gui_error_callback(client.last_auth_error)
        except Exception as e:
            print(f"[GUI] Error calling error callback: {e}")

    # Notify GUI if callback is registered
    if _gui_device_callback:
        try:
            _gui_device_callback(gui_device_list)
        except Exception as e:
            print(f"[GUI] Error calling device callback: {e}")


def process_job_device(
    job_device_id: str,
    job_id: str,
    config_id: str,
    device_id: str,
    device_uuid: str,
    duration: int,
):
    """
    Process a single job-device pair by running perfetto trace.

    Args:
        job_device_id: The JobDevice.id
        job_id: The job request ID
        config_id: The configuration ID to use
        device_id: The device_id (DB primary key)
        device_uuid: The device serial for ADB connection
        duration: Duration in seconds
    """
    try:
        # Get the worker API client
        client = get_worker_client()

        # Mark JobDevice as running
        client.update_job_device_status(job_device_id, "running")

        # Check if device is connected to this host
        device_connected = is_device_connected(device_uuid)
        print(f"Device {device_uuid} connected to this host: {device_connected}")

        if not device_connected:
            print(
                f"Device {device_uuid} is not connected to this host. Ignoring - another worker may handle it."
            )
            # Don't mark as failed - just silently ignore
            # Another worker with this device connected may pick it up
            return

        # Get config via API
        config = client.get_config(config_id)
        if not config:
            print(f"Config {config_id} not found")
            client.update_job_device_status(job_device_id, "failed")
            client.send_job_update(
                job_id, device_id, "failed", "Configuration not found"
            )
            return

        print(
            f"Processing job {job_id} for device {device_uuid} with config {config.get('config_name', 'config')}"
        )

        # Mark device as tracing to prevent regular poll from overwriting status
        _tracing_devices.add(device_uuid)

        # Notify GUI that device is tracing - instant update
        if _gui_device_callback:
            try:
                _gui_device_callback(
                    [
                        (
                            device_uuid,
                            "tracing",
                            f"Tracing: {config.get('config_name', 'config')}",
                        )
                    ]
                )
            except Exception as e:
                print(f"[GUI] Error calling tracing callback: {e}")

        # Send status updates
        client.send_job_update(
            job_id,
            device_id,
            "starting",
            f"Starting trace collection on {device_uuid}",
        )

        # Run perfetto trace
        client.send_job_update(
            job_id,
            device_id,
            "running",
            "Collecting trace...",
        )

        local_trace_path = run_perfetto_trace(
            device_uuid, config, duration_seconds=duration
        )

        if not local_trace_path:
            print(f"Failed to collect trace from {device_uuid}")
            client.update_job_device_status(job_device_id, "failed")
            client.send_job_update(
                job_id,
                device_id,
                "failed",
                "Failed to collect trace",
            )
            return

        client.send_job_update(
            job_id,
            device_id,
            "uploading",
            "Uploading trace to storage...",
        )

        # Upload trace file
        file_uuid = str(uuid.uuid4())
        minio_filename = (
            f"{file_uuid}-{config.get('config_name', 'config')}.perfetto-trace"
        )

        with open(local_trace_path, "rb") as f:
            client.upload_trace_file("traces", minio_filename, f.read())

        # Create trace record
        trace_payload = {
            "trace_id": str(uuid.uuid4()),
            "trace_name": f"{config.get('config_name', 'config')} - {device_uuid}",
            "device_id": device_id,
            "trace_timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_filename": minio_filename,
            "host_name": get_hostname(),
            "configuration_id": config.get("config_id"),
        }

        trace = client.create_trace_record(trace_payload)

        # Clean up local file
        try:
            os.unlink(local_trace_path)
        except Exception:
            pass

        trace_id = trace.get("trace_id") if isinstance(trace, dict) else None
        print(f"Successfully created trace {trace_id} for device {device_uuid}")

        # Mark as completed
        client.update_job_device_status(job_device_id, "completed")
        client.send_job_update(
            job_id,
            device_id,
            "completed",
            "Trace collected successfully",
            trace_id=trace_id,
        )

        # Remove from tracing set
        _tracing_devices.discard(device_uuid)

        # Notify GUI immediately that device is back to available - instant update
        if _gui_device_callback:
            try:
                _gui_device_callback([(device_uuid, "available", None)])
                print(f"[GUI] Notified device {device_uuid} back to available")
            except Exception as e:
                print(f"[GUI] Error calling available callback: {e}")

    except Exception as e:
        print(f"Error processing job_device {job_device_id}: {e}")
        import traceback

        traceback.print_exc()

        # Remove from tracing set on error
        _tracing_devices.discard(device_uuid)

        client = get_worker_client()
        client.update_job_device_status(job_device_id, "failed")
        client.send_job_update(
            job_id,
            device_id,
            "failed",
            f"Error: {str(e)}",
        )

        # Notify GUI immediately that device is back to available after error - instant update
        if _gui_device_callback:
            try:
                _gui_device_callback([(device_uuid, "available", None)])
                print(
                    f"[GUI] Notified device {device_uuid} back to available after error"
                )
            except Exception as callback_err:
                print(f"[GUI] Error calling available callback: {callback_err}")


def background_task():
    """Poll for pending job-device pairs and process them."""
    try:
        client = get_worker_client()
        pending = client.fetch_pending_jobs()
        if not pending:
            # Nothing to do right now
            return

        for job_item in pending:
            try:
                job_device_id = job_item.get("job_device_id")
                job_id = job_item.get("job_id")
                config_id = job_item.get("config_id")
                device_id = job_item.get("device_id")
                device_uuid = job_item.get("device_uuid")
                duration = job_item.get("duration", 10)

                if isinstance(duration, str):
                    try:
                        duration = int(duration)
                    except ValueError:
                        duration = 10

                if not all([job_device_id, job_id, config_id, device_id, device_uuid]):
                    print(f"[BACKGROUND] Invalid job structure: {job_item}")
                    continue

                print(
                    f"[BACKGROUND] Worker {os.getpid()} processing job_device {job_device_id} "
                    f"(job={job_id}, device={device_uuid})"
                )

                def process_in_thread():
                    try:
                        process_job_device(
                            job_device_id,
                            job_id,
                            config_id,
                            device_id,
                            device_uuid,
                            duration,
                        )
                    except Exception as e:
                        print(
                            f"[BACKGROUND] Error in thread for job_device {job_device_id}: {e}"
                        )
                        import traceback

                        traceback.print_exc()

                thread = threading.Thread(target=process_in_thread, daemon=True)
                thread.start()
                print(
                    f"[BACKGROUND] Worker {os.getpid()} started thread for job_device {job_device_id}"
                )

            except Exception as e:
                print(f"[BACKGROUND] Skipping invalid job entry: {e}")

        return

    except Exception as e:
        print(f"[BACKGROUND] Error in background polling task: {e}")
        import traceback

        traceback.print_exc()


def run_update_devices():
    """
    A wrapper that runs the imported background task every 5 seconds.
    Uses threading.Event for faster, interruptible shutdown.
    """
    while not _shutdown_event.is_set():
        try:
            print(f"[{datetime.now().strftime('%X')}] Updating devices...")
            update_device_statuses()
        except Exception as e:
            print(f"An error occurred in the periodic task: {e}")

        # Wait 5 seconds or until shutdown is signaled (whichever comes first)
        _shutdown_event.wait(timeout=5)

    print("Device update thread stopped.")


def run_listen_pubsub():
    """
    Polls for pending jobs every 5 seconds.
    Uses threading.Event for faster, interruptible shutdown.
    """
    print("Running pubsub listener...")
    while not _shutdown_event.is_set():
        try:
            background_task()
        except Exception as e:
            print(f"An error occurred in the pubsub listener: {e}")

        # Wait 5 seconds or until shutdown is signaled (whichever comes first)
        _shutdown_event.wait(timeout=5)

    print("Pubsub listener thread stopped.")


def signal_shutdown():
    """Signal all background threads to stop."""
    print("Signaling background threads to shutdown...")
    _shutdown_event.set()
