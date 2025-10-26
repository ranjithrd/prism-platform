import json
import os
import threading
import uuid
from datetime import datetime, timezone
from time import sleep

from sqlmodel import Session, select

from src.common.adb import is_device_connected
from src.common.db import Config, Device, JobRequest, Trace, engine
from src.common.hostname import get_hostname
from src.common.minio import MinioHelper
from src.common.redis_client import get_redis_client
from src.services.run_perfetto import run_perfetto_trace
from src.services.startup import update_devices_in_redis

JOB_REQUEST_STREAM_NAME = "job_requests"


def process_job_request(
    job_id: str, config_id: str, device_serials: list, duration: int
):
    """
    Process a single job request by running perfetto traces on specified devices.

    Args:
        job_id: The job request ID
        config_id: The configuration ID to use
        device_serials: List of device serial numbers
    """
    session = Session(engine)
    redis_client = get_redis_client()

    try:
        # Get the config
        config = session.exec(
            select(Config).where(Config.config_id == config_id)
        ).first()
        if not config:
            print(f"Config {config_id} not found")
            update_job_status(session, job_id, "failed", "Configuration not found")
            if redis_client:
                send_job_update(
                    redis_client, job_id, "all", "failed", "Configuration not found"
                )
            return

        # Track success/failure counts
        success_count = 0
        failure_count = 0

        # Process each device independently - don't let one failure stop others
        for device_serial in device_serials:
            try:
                print(
                    f"Received request for {device_serial} with config {config.config_name}"
                )

                device_connected_to_this_host = is_device_connected(device_serial)
                print(
                    f"Device {device_serial} connected to this host: {device_connected_to_this_host}"
                )

                if device_connected_to_this_host is False:
                    print(
                        f"Device {device_serial} is not connected to this host. Exiting for this device ID"
                    )
                    continue

                # Send status update
                if redis_client:
                    send_job_update(
                        redis_client,
                        job_id,
                        device_serial,
                        "starting",
                        f"Starting trace collection on {device_serial}",
                    )

                # Update job status to running
                update_job_status(session, job_id, "running")

                # Check if device exists in database
                device = session.exec(
                    select(Device).where(
                        (Device.device_uuid == device_serial)
                        | (Device.device_id == device_serial)
                    )
                ).first()

                # check if device is connected to host
                if device and redis_client:
                    device_status = redis_client.get_device_status(device_serial)
                    if (
                        not device_status
                        or device_status.get("status") != "online"
                        or device_status.get("current_host") != get_hostname()
                    ):
                        print(
                            f"Device {device_serial} is not online or not connected to this host"
                        )
                        send_job_update(
                            redis_client,
                            job_id,
                            device_serial,
                            "failed",
                            "Device is not online or not connected to this host",
                        )
                        failure_count += 1
                        continue

                if not device:
                    print(f"Device {device_serial} not found in database")
                    if redis_client:
                        send_job_update(
                            redis_client,
                            job_id,
                            device_serial,
                            "failed",
                            "Device not found in database",
                        )
                    failure_count += 1
                    continue

                # Run perfetto trace
                if redis_client:
                    send_job_update(
                        redis_client,
                        job_id,
                        device_serial,
                        "running",
                        "Collecting trace...",
                    )

                local_trace_path = run_perfetto_trace(
                    device_serial, config, duration_seconds=duration
                )

                if not local_trace_path:
                    print(f"Failed to collect trace from {device_serial}")
                    if redis_client:
                        send_job_update(
                            redis_client,
                            job_id,
                            device_serial,
                            "failed",
                            "Failed to collect trace",
                        )
                    failure_count += 1
                    continue

                # Upload to MinIO
                if redis_client:
                    send_job_update(
                        redis_client,
                        job_id,
                        device_serial,
                        "uploading",
                        "Uploading trace to storage...",
                    )

                minio_helper = MinioHelper(
                    host=os.getenv("MINIO_HOST"),
                    access_key=os.getenv("MINIO_ACCESS_KEY"),
                    secret_key=os.getenv("MINIO_SECRET_KEY"),
                )
                file_uuid = str(uuid.uuid4())
                minio_filename = f"{file_uuid}-{config.config_name}.perfetto-trace"

                with open(local_trace_path, "rb") as f:
                    minio_helper.upload_bytes("traces", minio_filename, f.read())

                # Create trace record in database
                trace = Trace(
                    trace_id=str(uuid.uuid4()),
                    trace_name=f"{config.config_name} - {device.device_name}",
                    device_id=device.device_id,
                    trace_timestamp=datetime.now(timezone.utc),
                    trace_filename=minio_filename,
                    host_name=get_hostname(),
                    configuration_id=config.config_id,
                )
                session.add(trace)
                session.commit()
                session.refresh(trace)

                # Clean up local file
                try:
                    os.unlink(local_trace_path)
                except:
                    pass

                print(
                    f"Successfully created trace {trace.trace_id} for device {device_serial}"
                )

                if redis_client:
                    send_job_update(
                        redis_client,
                        job_id,
                        device_serial,
                        "completed",
                        "Trace collected successfully",
                        trace_id=trace.trace_id,
                    )

                success_count += 1

            except Exception as e:
                print(f"Error processing device {device_serial}: {e}")
                import traceback

                traceback.print_exc()
                if redis_client:
                    send_job_update(
                        redis_client,
                        job_id,
                        device_serial,
                        "failed",
                        f"Error: {str(e)}",
                    )
                failure_count += 1
                # Continue to next device instead of breaking

        # Mark job as completed with summary
        total = len(device_serials)
        result_summary = f"Completed: {success_count}/{total} devices successful, {failure_count}/{total} failed"

        if failure_count == total:
            # All failed
            update_job_status(session, job_id, "failed", result_summary)
        elif failure_count > 0:
            # Some failed
            update_job_status(session, job_id, "partial", result_summary)
        else:
            # All succeeded
            update_job_status(session, job_id, "completed", result_summary)

    except Exception as e:
        print(f"Error processing job {job_id}: {e}")
        import traceback

        traceback.print_exc()
        update_job_status(session, job_id, "failed", str(e))
    finally:
        session.close()


def update_job_status(
    session: Session, job_id: str, status: str, result_summary: str = None
):
    """Update the job request status in the database."""
    job = session.exec(select(JobRequest).where(JobRequest.job_id == job_id)).first()
    if job:
        job.status = status
        job.updated_at = datetime.now(timezone.utc)
        if result_summary:
            job.result_summary = result_summary
        session.add(job)
        session.commit()


def send_job_update(
    redis_client,
    job_id: str,
    device_serial: str,
    status: str,
    message: str = "",
    trace_id: str = None,
):
    """Send a job update to Redis stream."""
    if not redis_client or not redis_client.client:
        return

    stream_key = f"{JOB_REQUEST_STREAM_NAME}:{job_id}"
    update_data = {
        "device_serial": device_serial,
        "status": status,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if trace_id:
        update_data["trace_id"] = trace_id

    try:
        redis_client.client.xadd(stream_key, update_data)
    except Exception as e:
        print(f"Failed to send job update to Redis: {e}")


def background_task():
    """
    Background task that polls Redis stream for new job requests.
    Only ONE worker will process each job using Redis-based locking.
    """
    global LAST_MESSAGE_ID

    redis_client = get_redis_client()

    if not redis_client or not redis_client.client:
        return

    try:
        try:
            # Read new messages from the job request stream
            redis_client = get_redis_client()

            if not redis_client or not redis_client.client:
                print("[BACKGROUND] Redis client not available")
                return

            pubsub = redis_client.client.pubsub()
            pubsub.subscribe(JOB_REQUEST_STREAM_NAME)
            for i in pubsub.listen():
                print("Received message from pubsub:", i)
                data = i["data"]
                try:
                    decoded_fields = json.loads(data)
                    print("Decoded message data as JSON:", decoded_fields)

                    is_job = decoded_fields.get("job_id") is not None
                    if is_job:
                        print(
                            "Received job request with id: ",
                            decoded_fields.get("job_id"),
                        )

                    job_id = decoded_fields.get("job_id")
                    config_id = decoded_fields.get("config_id")
                    devices = decoded_fields.get("devices")
                    duration = decoded_fields.get("duration", 10)

                    print("Job duration: ", duration)

                    if isinstance(duration, str):
                        try:
                            duration = int(duration)
                        except ValueError:
                            duration = 10

                    print("Parsed duration: ", duration)

                    if not all([job_id, config_id, devices]):
                        print(
                            f"[BACKGROUND] Invalid job request message: {decoded_fields}"
                        )
                        continue

                    # Parse device list
                    if isinstance(devices, str):
                        device_serials = json.loads(devices)
                    else:
                        device_serials = devices

                    print(
                        f"[BACKGROUND] Worker {os.getpid()} processing job {job_id} with config {config_id} for devices {device_serials}"
                    )

                    def process_in_thread():
                        try:
                            process_job_request(
                                job_id, config_id, device_serials, duration
                            )
                        except Exception as e:
                            print(
                                f"[BACKGROUND] Error in thread processing job {job_id}: {e}"
                            )
                            import traceback

                            traceback.print_exc()

                    thread = threading.Thread(target=process_in_thread, daemon=True)
                    thread.start()
                    print(
                        f"[BACKGROUND] Worker {os.getpid()} started thread for job {job_id}"
                    )

                except Exception:
                    print("[BACKGROUND] Failed to read or process message:", data)
                    continue

            print("[BACKGROUND] Exiting pubsub listener loop...")

        except Exception as e:
            print(f"[BACKGROUND] Error reading from Redis: {e}")

        print("[BACKGROUND] Completed Redis pubsub listener...")
        return

    except Exception as e:
        print(f"[BACKGROUND] Error in background task for worker {os.getpid()}: {e}")
        import traceback

        traceback.print_exc()


def run_update_devices():
    """
    A wrapper that runs the imported background task every 5 seconds.
    """
    while True:
        try:
            print(f"[{datetime.now().strftime('%X')}] Updating devices...")
            update_devices_in_redis()
            sleep(5)
        except Exception as e:
            print(f"An error occurred in the periodic task: {e}")
            sleep(5)


def run_listen_pubsub():
    """
    A wrapper that runs the imported background task to listen to Redis pubsub.
    """
    print("Running Redis pubsub listener...")
    background_task()
