import json
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SimpleperfConfigJson:
    """Configuration for simpleperf profiling"""

    debug_app_id: (
        str  # Package name like com.example.app, or "system" for system-wide trace
    )
    events: list[str] = field(default_factory=lambda: ["cpu-cycles"])  # Events to trace
    frequency: int = 4000  # Sampling frequency in Hz
    call_graph: str = "dwarf"  # Call graph method: "fp" or "dwarf"
    record_command: str = "record"  # Simpleperf command to run
    extra_args: list[str] = field(default_factory=list)  # Additional arguments
    root_mode: bool = False  # Whether to run adb root before tracing


def run_simpleperf_trace(
    device_serial: str, config, duration_seconds: int = 10
) -> tuple[Optional[str], None]:
    """
    Runs a simpleperf trace on an Android device to profile app performance.

    Args:
        device_serial: Android device serial number
        config: Config object or dict containing config_text with JSON configuration
        duration_seconds: Duration to run the trace

    Returns:
        tuple of (trace_file_path, None) on success, (None, None) on failure
    """
    # Handle both Config object and dict
    if isinstance(config, dict):
        config_text = config.get("config_text", "")
    else:
        config_text = config.config_text

    try:
        config_dict = json.loads(config_text)
        simpleperf_config = SimpleperfConfigJson(**config_dict)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Error parsing simpleperf config JSON: {e}")
        return None, None

    local_cache_dir = ".cache/traces"
    os.makedirs(local_cache_dir, exist_ok=True)

    trace_uuid = uuid.uuid4().hex[:8]
    device_trace_path = f"/data/local/tmp/perf_{trace_uuid}.data"
    local_trace_path = os.path.join(local_cache_dir, f"simpleperf_{trace_uuid}.data")

    # Run adb root if root_mode is enabled
    if simpleperf_config.root_mode:
        print("Enabling root mode...")
        root_command = ["adb", "-s", device_serial, "root"]
        try:
            root_result = subprocess.run(
                root_command, capture_output=True, text=True, timeout=10
            )
            if root_result.returncode != 0:
                print(f"Warning: adb root failed: {root_result.stderr}")
            else:
                print("Root mode enabled successfully")
                # Give device a moment to restart adbd
                import time

                time.sleep(2)
        except subprocess.TimeoutExpired:
            print("Warning: adb root command timed out")

    # Build simpleperf command
    # If debug_app_id is "system", do system-wide tracing (no --app argument)
    # Otherwise use --app <package>
    is_system_trace = simpleperf_config.debug_app_id.lower() == "system"

    simpleperf_args = [
        "adb",
        "-s",
        device_serial,
        "shell",
        "simpleperf",
        simpleperf_config.record_command,
    ]

    # Add --app argument only if not doing system-wide trace
    if not is_system_trace:
        simpleperf_args.extend(["--app", simpleperf_config.debug_app_id])
    else:
        # For system-wide traces, use -a (all processes)
        simpleperf_args.append("-a")

    simpleperf_args.extend(
        [
            "-o",
            device_trace_path,
            "--duration",
            str(duration_seconds),
        ]
    )

    # Only add call graph recording for non-system-wide traces
    # if not is_system_trace:
    if simpleperf_config.call_graph and simpleperf_config.call_graph.lower() != "none":
        simpleperf_args.extend(
            [
                "-g",  # Enable call graph recording
                "--call-graph",
                simpleperf_config.call_graph,
            ]
        )

    simpleperf_args.extend(
        [
            "-f",
            str(simpleperf_config.frequency),
        ]
    )

    # Add events
    for event in simpleperf_config.events:
        simpleperf_args.extend(["-e", event])

    # Add any extra arguments
    simpleperf_args.extend(simpleperf_config.extra_args)

    print(f"Starting simpleperf trace for {duration_seconds}s...")
    print(f"Command: {' '.join(simpleperf_args)}")

    try:
        # Run simpleperf record
        proc = subprocess.run(
            simpleperf_args,
            capture_output=True,
            text=True,
            timeout=duration_seconds + 30,  # Add buffer time
        )

        if proc.returncode != 0:
            print(f"Simpleperf record failed with code: {proc.returncode}")
            print(f"Stdout: {proc.stdout}")
            print(f"Stderr: {proc.stderr}")
            return None, None

        print("Simpleperf recording completed successfully")

    except subprocess.TimeoutExpired:
        print("Simpleperf recording timed out")
        return None, None

    # Pull the trace file from device
    print("Pulling trace file from device...")
    pull_command = [
        "adb",
        "-s",
        device_serial,
        "pull",
        device_trace_path,
        local_trace_path,
    ]

    try:
        pull_result = subprocess.run(
            pull_command, capture_output=True, text=True, timeout=60
        )

        if pull_result.returncode != 0:
            print(f"Failed to pull trace file: {pull_result.stderr}")
            return None, None

    except subprocess.TimeoutExpired:
        print("Timeout while pulling trace file")
        return None, None

    # Clean up device trace file
    cleanup_command = ["adb", "-s", device_serial, "shell", "rm", device_trace_path]
    subprocess.run(cleanup_command, capture_output=True)

    if os.path.exists(local_trace_path) and os.path.getsize(local_trace_path) > 0:
        print(f"Successfully retrieved simpleperf trace: {local_trace_path}")
        return local_trace_path, None
    else:
        print("Trace file was not created or is empty. Check logs for errors.")
        return None, None
