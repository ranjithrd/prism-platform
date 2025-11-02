import os
import threading
import uuid
from datetime import datetime, timezone
from time import sleep

from src.common.adb import adb_devices, is_device_connected
from src.common.hostname import get_hostname

from .api import get_worker_client
from .run_perfetto import run_perfetto_trace

JOB_REQUEST_STREAM_NAME = "job_requests"


def update_device_statuses():
    """Update device statuses in the database based on ADB connections.

    Note: Device management is currently a stub in worker_api.py.
    This function is kept for future implementation when device
    management is fully integrated with the API.
    """
    devices = adb_devices()
    online_devices = []
    hostname = get_hostname()
    client = get_worker_client()

    print("Logging connected devices:")
    print(devices)
    db_devices = client.get_existing_devices()
    print(db_devices)

    for device in devices:
        serial = device.get("serial")
        state = device.get("state")
        if serial and state:
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
            print(f"Device {device_uuid} is not connected to this host. Skipping.")
            client.update_job_device_status(job_device_id, "failed")
            client.send_job_update(
                job_id,
                device_id,
                "failed",
                f"Device {device_uuid} not connected to this host",
            )
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

    except Exception as e:
        print(f"Error processing job_device {job_device_id}: {e}")
        import traceback

        traceback.print_exc()

        client = get_worker_client()
        client.update_job_device_status(job_device_id, "failed")
        client.send_job_update(
            job_id,
            device_id,
            "failed",
            f"Error: {str(e)}",
        )


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
    """
    while True:
        try:
            print(f"[{datetime.now().strftime('%X')}] Updating devices...")
            update_device_statuses()
            sleep(5)
        except Exception as e:
            print(f"An error occurred in the periodic task: {e}")
            sleep(5)


def run_listen_pubsub():
    print("Running pubsub listener...")
    while True:
        try:
            background_task()
            sleep(5)
        except Exception as e:
            print(f"An error occurred in the pubsub listener: {e}")
            sleep(5)
