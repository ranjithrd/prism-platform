import json
import os
import uuid
from datetime import datetime, timezone

from sqlmodel import Session, select

from src.common.adb import is_device_connected
from src.common.db import Config, Device, JobRequest, Trace, engine
from src.common.hostname import get_hostname
from src.common.minio import MinioHelper
from src.common.redis_client import get_redis_client
from src.services.run_perfetto import run_perfetto_trace

JOB_REQUEST_STREAM_NAME = "job_requests"
LOCK_FILE_PATH = ".cache/background_worker.lock"
LAST_MESSAGE_ID_FILE = ".cache/last_message_id.txt"

# Track last message ID - loaded ONCE on module import
os.makedirs(".cache", exist_ok=True)
if os.path.exists(LAST_MESSAGE_ID_FILE):
    try:
        with open(LAST_MESSAGE_ID_FILE, "r") as f:
            LAST_MESSAGE_ID = f.read().strip() or "0"
            print(f"[BACKGROUND] Resuming from message ID: {LAST_MESSAGE_ID}")
    except:
        LAST_MESSAGE_ID = "0"
        print("[BACKGROUND] Starting fresh with 0 (will read all messages)")
else:
    LAST_MESSAGE_ID = "0"
    print("[BACKGROUND] First run, using 0 to read all messages")


def process_job_request(job_id: str, config_id: str, device_serials: list):
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
                    device_serial, config, duration_seconds=10
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
        # Read new messages from the job request stream
        # Get the current position from Redis (shared across all workers)
        try:
            saved_position = redis_client.client.get("job_processor_position")
            if saved_position:
                current_position = (
                    saved_position.decode("utf-8")
                    if isinstance(saved_position, bytes)
                    else saved_position
                )
            else:
                current_position = "0"
        except:
            current_position = "0"

        # Read new messages from the job request stream
        try:
            streams = redis_client.client.xread(
                {JOB_REQUEST_STREAM_NAME: current_position},
                count=1,  # Only read ONE message at a time
                block=1000,  # Block for 1 second
            )
        except Exception as e:
            print(f"[BACKGROUND] Error reading from Redis: {e}")
            return

        if not streams:
            return

        for stream_name, messages in streams:
            for message_id, fields in messages:
                try:
                    # Try to acquire a lock for THIS specific message using Redis SETNX
                    lock_key = f"job_lock:{message_id}"

                    # Try to set the lock (expires in 60 seconds as safety)
                    # SETNX returns 1 if lock acquired, 0 if already exists
                    lock_acquired = redis_client.client.set(
                        lock_key, os.getpid(), nx=True, ex=60
                    )

                    if not lock_acquired:
                        print(
                            f"[BACKGROUND] Worker {os.getpid()} - job {message_id} already being processed by another worker"
                        )
                        continue

                    print(
                        f"[BACKGROUND] Worker {os.getpid()} acquired lock for message {message_id}"
                    )

                    # Decode bytes to strings if needed
                    decoded_fields = {}
                    for key, value in fields.items():
                        if isinstance(key, bytes):
                            key = key.decode("utf-8")
                        if isinstance(value, bytes):
                            value = value.decode("utf-8")
                        decoded_fields[key] = value

                    job_id = decoded_fields.get("job_id")
                    config_id = decoded_fields.get("config_id")
                    devices = decoded_fields.get("devices")

                    if not all([job_id, config_id, devices]):
                        print(
                            f"[BACKGROUND] Invalid job request message: {decoded_fields}"
                        )
                        # Release lock and update position
                        redis_client.client.delete(lock_key)
                        redis_client.client.set("job_processor_position", message_id)
                        continue

                    # Parse device list
                    if isinstance(devices, str):
                        device_serials = json.loads(devices)
                    else:
                        device_serials = devices

                    print(
                        f"[BACKGROUND] Worker {os.getpid()} processing job {job_id} with config {config_id} for devices {device_serials}"
                    )

                    # Process the job request IN A SEPARATE THREAD to avoid worker timeout
                    import threading

                    def process_in_thread():
                        try:
                            process_job_request(job_id, config_id, device_serials)
                        except Exception as e:
                            print(
                                f"[BACKGROUND] Error in thread processing job {job_id}: {e}"
                            )
                            import traceback

                            traceback.print_exc()
                        finally:
                            # Release the lock after processing
                            try:
                                redis_client.client.delete(lock_key)
                                print(
                                    f"[BACKGROUND] Worker {os.getpid()} released lock for job {job_id}"
                                )
                            except:
                                pass

                    thread = threading.Thread(target=process_in_thread, daemon=True)
                    thread.start()
                    print(
                        f"[BACKGROUND] Worker {os.getpid()} started thread for job {job_id}"
                    )

                    # Update position in Redis IMMEDIATELY so other workers skip this message
                    redis_client.client.set("job_processor_position", message_id)
                    print(
                        f"[BACKGROUND] Worker {os.getpid()} updated position to {message_id}"
                    )

                except Exception as e:
                    print(f"[BACKGROUND] Error processing message {message_id}: {e}")
                    import traceback

                    traceback.print_exc()

    except Exception as e:
        print(f"[BACKGROUND] Error in background task for worker {os.getpid()}: {e}")
        import traceback

        traceback.print_exc()
