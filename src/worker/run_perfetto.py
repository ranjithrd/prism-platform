import os
import signal
import subprocess
import time
import uuid
from typing import Optional

PERFETTO_SCRIPT_PATH = "src/tools/record_android_trace.py"


def run_perfetto_trace(
    device_serial: str, config, duration_seconds: int = 10
) -> Optional[str]:
    """
    Runs a Perfetto trace using the official helper script and manages its
    interactive lifecycle automatically.
    """
    if not os.path.exists(PERFETTO_SCRIPT_PATH):
        print(f"Error: Perfetto script not found at '{PERFETTO_SCRIPT_PATH}'")
        return None

    # Handle both Config object and dict
    if isinstance(config, dict):
        config_text = config.get("config_text", "")
    else:
        config_text = config.config_text

    local_cache_dir = ".cache/traces"
    os.makedirs(local_cache_dir, exist_ok=True)

    trace_uuid = uuid.uuid4().hex[:8]
    local_trace_path = os.path.join(
        local_cache_dir, f"trace_{trace_uuid}.perfetto-trace"
    )
    temp_config_path = os.path.join(local_cache_dir, f"config_{trace_uuid}.pbtxt")

    with open(temp_config_path, "w") as f:
        f.write(config_text)

    command = [
        "python3",
        PERFETTO_SCRIPT_PATH,
        "-c",
        temp_config_path,
        "-o",
        local_trace_path,
        "--serial",
        device_serial,
        "-t",
        f"{duration_seconds}s",
        "-n",
    ]

    print(f"Starting background Perfetto trace for {duration_seconds}s...")
    print(f"Command: {' '.join(command)}")

    # Use Popen to run the script as a non-blocking background process
    proc = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    try:
        # Wait for the specified duration while the trace runs
        time.sleep(duration_seconds)

    finally:
        # Send the CTRL+C signal (SIGINT) to gracefully stop the trace
        print("Stopping trace...")
        proc.send_signal(signal.SIGINT)

        # Wait for the process to terminate and get the output
        try:
            stdout, stderr = proc.communicate(timeout=30)  # Add a timeout for safety
            print("Trace script finished.")
            if proc.returncode != 0:
                print(f"Perfetto script exited with error code: {proc.returncode}")
                print("Stdout:", stdout)
                print("Stderr:", stderr)
                return None
        except subprocess.TimeoutExpired:
            print("Perfetto script did not terminate, killing.")
            proc.kill()
            stdout, stderr = proc.communicate()
            print("Stderr:", stderr)
            return None

    os.unlink(temp_config_path)

    if os.path.exists(local_trace_path) and os.path.getsize(local_trace_path) > 1024:
        print(f"Successfully retrieved trace: {local_trace_path}")
        return local_trace_path
    else:
        print("Trace file was not created or is empty. Check logs for errors.")
        return None
