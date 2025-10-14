import os
import uuid
from typing import Optional

from src.common.adb import adb_shell, adb_pull, adb_push
from src.common.db import Config


def run_perfetto_trace(device_serial: str, config: Config, duration_seconds: int = 10) -> Optional[str]:
    """
    Run a perfetto trace on the specified device using the provided config.

    Args:
        device_serial: The serial number of the device
        config: The Config object containing the trace configuration
        duration_seconds: How long to run the trace (default: 10 seconds)

    Returns:
        Optional[str]: Local path to the trace file if successful, None otherwise
    """

    local_cache_dir = ".cache/pbconfigs"
    os.makedirs(local_cache_dir, exist_ok=True)

    config_uuid = uuid.uuid4().hex[:8]
    local_config_filename = f"perfetto_config_{config_uuid}.pbtxt"
    local_config_path = os.path.join(local_cache_dir, local_config_filename)

    # --- FIX: Use the correct SELinux-labeled directories ---
    # The config MUST go in /data/misc/perfetto-configs
    # The trace output SHOULD go in /data/misc/perfetto-traces
    temp_config_path = f"/data/misc/perfetto-configs/perfetto_config_{config_uuid}.pbtxt"
    temp_trace_path = f"/data/misc/perfetto-traces/trace_{config_uuid}.perfetto-trace"

    # Add duration_ms to the config text
    # NOTE: Team should NOT include duration_ms in their configs - we add it here
    config_text = f"duration_ms: {duration_seconds * 1000}\n{config.config_text}"

    try:
        with open(local_config_path, 'w') as f:
            f.write(config_text)

        print(f"Config written to local cache: {local_config_path}")

        # Push config file to the correct directory
        if not adb_push(local_config_path, temp_config_path, serial=device_serial):
            print(f"Failed to push config to device. Ensure the target directory exists or you have root.")
            return None

        print(f"Config pushed to device: {temp_config_path}")

        # --- IMPROVEMENT: Add --txt flag for text-based config ---
        # The command will be blocking (waits for trace to complete)
        perfetto_cmd = f"perfetto -c {temp_config_path} -o {temp_trace_path} --txt"

        print(f"Starting Perfetto trace for {duration_seconds} seconds...")
        success, stdout, stderr = adb_shell(perfetto_cmd, serial=device_serial)

        if not success:
            print(f"Failed to run perfetto: {stderr}")
            # The command may have failed. As a cleanup attempt, try to remove the config file.
            adb_shell(f"rm {temp_config_path}", serial=device_serial)
            return None

        print("Stdout:", stdout)
        print("Success:", success)
        print(f"Stderr: {stderr}")

        print(f"Trace completed. Pulling file from device...")

        local_trace_path = adb_pull(temp_trace_path, serial=device_serial)

        # Clean up temporary files on device
        print("Cleaning up device files...")
        adb_shell(f"rm {temp_config_path}", serial=device_serial)
        adb_shell(f"rm {temp_trace_path}", serial=device_serial)

        # Clean up local config file
        os.unlink(local_config_path)

        if not local_trace_path or not os.path.exists(local_trace_path):
            print(f"Failed to pull trace file from device.")
            return None

        print(f"Successfully retrieved trace: {local_trace_path}")
        return local_trace_path

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        # Ensure cleanup on error
        adb_shell(f"rm {temp_config_path}", serial=device_serial)
        adb_shell(f"rm {temp_trace_path}", serial=device_serial)
        return None
