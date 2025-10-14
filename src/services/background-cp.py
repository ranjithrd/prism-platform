import json
import logging
import os
import sys
import threading
import time
import uuid
from datetime import datetime, timezone

from redis import Redis
from sqlmodel import create_engine, Session, select

from src.common.db import Config, Device, Trace, JobRequest
from src.common.hostname import get_hostname
from src.common.minio import MinioHelper
from src.services.run_perfetto import run_perfetto_trace

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - PID:%(process)d - %(thread)d - %(levelname)s - %(message)s',
    stream=sys.stdout,  # Explicitly send logs to standard output
    force=True  # **This is the most important part.** It removes any old handlers and forces this config.
)

logging.info("Logging configured successfully for this worker process.")

# --- Configuration ---
JOB_REQUEST_STREAM_NAME = "job_requests"
JOB_PROCESSOR_POSITION_KEY = "job_processor_position"  # Shared position key in Redis
JOB_LOCK_PREFIX = "job_lock:"  # Prefix for job-specific locks in Redis
JOB_LOCK_EXPIRY_SECONDS = 120  # Safety timeout for locks to prevent deadlocks

# --- Process-Safe Resource Initialization ---
# These globals will hold the connection objects, but only ONCE per forked process.
_engine = None
_redis_client = None


def get_engine():
    """Lazily creates a single, process-safe SQLAlchemy engine."""
    global _engine
    if _engine is None:
        logging.info("Initializing new database engine for this process...")
        db_url = os.getenv("DATABASE_URL", "sqlite:///./database.db")  # Example fallback
        _engine = create_engine(db_url)
    return _engine


def get_redis_client():
    """Lazily creates a single, process-safe Redis client."""
    global _redis_client
    if _redis_client is None:
        logging.info("Initializing new Redis client for this process...")
        _redis_client = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    return _redis_client


def process_job_request(job_id: str, config_id: str, device_serials: list):
    """
    Process a single job request. This function contains the core business logic.
    It's designed to be called within a thread by a wrapper that handles locking.
    """
    engine = get_engine()
    session = Session(engine)
    redis_client = get_redis_client()

    try:
        config = session.exec(select(Config).where(Config.config_id == config_id)).first()
        if not config:
            logging.error(f"Config {config_id} not found for job {job_id}")
            update_job_status(session, job_id, "failed", "Configuration not found")
            send_job_update(redis_client, job_id, "all", "failed", "Configuration not found")
            return

        perfetto_config_data = getattr(config, 'config_text', None)
        if not perfetto_config_data:
            logging.error(f"Config {config_id} is empty for job {job_id}")
            update_job_status(session, job_id, "failed", "Configuration data is empty")
            send_job_update(redis_client, job_id, "all", "failed", "Configuration data is empty")
            return

        update_job_status(session, job_id, "running")

        success_count, failure_count = 0, 0
        for device_serial in device_serials:
            # CHANGED: The entire device processing logic is now in a try...except block.
            try:
                logging.info(f"Processing device {device_serial} for job {job_id}")
                send_job_update(redis_client, job_id, device_serial, "starting", f"Starting trace on {device_serial}")

                device = session.exec(select(Device).where(
                    (Device.device_uuid == device_serial) | (Device.device_id == device_serial))).first()
                if not device:
                    logging.warning(f"Device {device_serial} not found in DB for job {job_id}")
                    send_job_update(redis_client, job_id, device_serial, "failed", "Device not found")
                    failure_count += 1
                    continue

                send_job_update(redis_client, job_id, device_serial, "running", "Collecting trace...")

                # CHANGED: We now pass the specific config data, not the whole object.
                # This makes the dependency explicit and the code easier to understand.
                local_trace_path = run_perfetto_trace(device_serial, config=perfetto_config_data, duration_seconds=5)

                # This check remains as a fallback in case run_perfetto_trace returns None without an exception.
                if not local_trace_path:
                    raise RuntimeError("Trace collection returned no path without raising an exception.")

                # Upload to MinIO
                send_job_update(redis_client, job_id, device_serial, "uploading", "Uploading trace...")
                minio_helper = MinioHelper(
                    host=os.getenv("MINIO_HOST"),
                    access_key=os.getenv("MINIO_ACCESS_KEY"),
                    secret_key=os.getenv("MINIO_SECRET_KEY")
                )
                file_uuid = str(uuid.uuid4())
                minio_filename = f"{file_uuid}-{getattr(config, 'config_name', 'trace')}.perfetto-trace"
                with open(local_trace_path, 'rb') as f:
                    minio_helper.upload_bytes("traces", minio_filename, f.read())

                os.unlink(local_trace_path)  # Clean up local file immediately after use

                # Create trace record in database
                trace = Trace(
                    trace_id=str(uuid.uuid4()),
                    trace_name=f"{getattr(config, 'config_name', 'trace')} - {device.device_name}",
                    device_id=device.device_id,
                    trace_timestamp=datetime.now(timezone.utc),
                    trace_filename=minio_filename,
                    host_name=get_hostname()
                )
                session.add(trace)
                session.commit()
                session.refresh(trace)

                logging.info(f"Successfully created trace {trace.trace_id} for device {device_serial}")
                send_job_update(redis_client, job_id, device_serial, "completed", "Trace collected successfully",
                                trace_id=trace.trace_id)
                success_count += 1

            # CHANGED: This is the most important part. We now catch the exception.
            except Exception as e:
                # This log will now print the FULL traceback to your console/log file.
                logging.error(f"Failure on device {device_serial} for job {job_id}: {e}", exc_info=True)

                # The status update now contains the actual error message.
                send_job_update(redis_client, job_id, device_serial, "failed", f"Error: {str(e)}")
                failure_count += 1

        total = len(device_serials)
        summary = f"Completed: {success_count}/{total} successful, {failure_count}/{total} failed"
        if failure_count == total:
            update_job_status(session, job_id, "failed", summary)
        elif failure_count > 0:
            update_job_status(session, job_id, "partial", summary)
        else:
            update_job_status(session, job_id, "completed", summary)

    except Exception as e:
        logging.error(f"Critical error processing job {job_id}: {e}", exc_info=True)
        update_job_status(session, job_id, "failed", str(e))
    finally:
        session.close()


def update_job_status(session: Session, job_id: str, status: str, result_summary: str = None):
    """Update the job request status in the database."""
    job = session.exec(select(JobRequest).where(JobRequest.job_id == job_id)).first()
    if job:
        job.status = status
        job.updated_at = datetime.now(timezone.utc)
        if result_summary:
            job.result_summary = result_summary
        session.add(job)
        session.commit()


def send_job_update(redis_client, job_id: str, device_serial: str, status: str, message: str = "",
                    trace_id: str = None):
    """Send a job update to a dedicated Redis stream for that job."""
    if not redis_client:
        return
    try:
        stream_key = f"{JOB_REQUEST_STREAM_NAME}:{job_id}"
        update_data = {
            "device_serial": device_serial, "status": status, "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if trace_id:
            update_data["trace_id"] = trace_id
        redis_client.xadd(stream_key, update_data)
    except Exception as e:
        logging.error(f"Failed to send job update to Redis for job {job_id}: {e}")


def process_job_request_with_lock_release(lock_key: str, job_id: str, config_id: str, device_serials: list):
    """
    A wrapper function that runs the job and guarantees the Redis lock is released,
    whether the job succeeds or fails. This is the target for our thread.
    """
    redis_client = get_redis_client()
    try:
        process_job_request(job_id, config_id, device_serials)
    except Exception as e:
        logging.error(f"Thread for job {job_id} caught an unhandled exception: {e}", exc_info=True)
    finally:
        logging.info(f"Releasing lock for job {job_id} ({lock_key})")
        redis_client.delete(lock_key)


def background_task():
    """
    Polls Redis stream and dispatches jobs, ensuring only one worker processes each job.
    This is the main entry point for each worker's loop.
    """
    logging.debug("Background worker cycle starting.")
    redis_client = get_redis_client()

    try:
        last_id = redis_client.get(JOB_PROCESSOR_POSITION_KEY)
        start_id = last_id.decode('utf-8') if last_id else '0'

        streams = redis_client.xread(
            {JOB_REQUEST_STREAM_NAME: start_id},
            count=1,
            block=2000
        )

        if not streams:
            logging.debug("No new jobs in stream.")
            return

        message_id_bytes, fields = streams[0][1][0]
        message_id = message_id_bytes.decode('utf-8')
        lock_key = f"{JOB_LOCK_PREFIX}{message_id}"

        lock_acquired = redis_client.set(lock_key, os.getpid(), nx=True, ex=JOB_LOCK_EXPIRY_SECONDS)

        if not lock_acquired:
            logging.info(f"Job {message_id} is locked by another worker. Skipping.")
            redis_client.set(JOB_PROCESSOR_POSITION_KEY, message_id)
            return

        logging.info(f"Acquired lock for job {message_id}. Processing.")
        try:
            decoded_fields = {k.decode('utf-8'): v.decode('utf-8') for k, v in fields.items()}
            job_id, config_id, devices_json = (
                decoded_fields.get('job_id'),
                decoded_fields.get('config_id'),
                decoded_fields.get('devices')
            )

            if not all([job_id, config_id, devices_json]):
                logging.error(f"Invalid job message {message_id}: {decoded_fields}. Discarding.")
                redis_client.set(JOB_PROCESSOR_POSITION_KEY, message_id)
                redis_client.delete(lock_key)
                return

            device_serials = json.loads(devices_json)

            thread = threading.Thread(
                target=process_job_request_with_lock_release,
                args=(lock_key, job_id, config_id, device_serials),
                daemon=True
            )
            thread.start()

            redis_client.set(JOB_PROCESSOR_POSITION_KEY, message_id)

        except Exception as e:
            logging.error(f"Error dispatching job {message_id}: {e}", exc_info=True)
            redis_client.delete(lock_key)

    except Exception as e:
        logging.error(f"Error in background task main loop: {e}", exc_info=True)
        time.sleep(5)


if __name__ == '__main__':
    logging.info("Starting background worker simulator. Press Ctrl+C to exit.")
    try:
        while True:
            background_task()
            time.sleep(0.1)
    except KeyboardInterrupt:
        logging.info("Simulator shutting down.")
