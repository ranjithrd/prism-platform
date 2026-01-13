import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Optional

# Import eadb command helper
script_dir = os.path.join(os.path.dirname(__file__), "scripts")
sys.path.insert(0, script_dir)


@dataclass
class BpftraceConfig:
    """Configuration for bpftrace profiling"""

    config_text: str  # The content of the .bt script
    btf_path: str = "/sys/kernel/btf/vmlinux"
    # Include paths: arch-specific headers and kernel headers
    # Note: We dynamically construct kernel headers path at runtime
    cflags: str = "-I/usr/include/aarch64-linux-gnu -I/usr/include"
    # Environment variables to set before running bpftrace
    env_vars: Optional[dict[str, str]] = None


# Cache to track which devices have bpftrace installed (per session)
_bpftrace_checked_devices = set()


def _check_and_install_dependencies(device_serial: str):
    """
    Ensures eadb and bpftrace are installed and ready.
    Uses /data/eadb/run-command for non-interactive execution.
    """
    # 1. Ensure adb root (mandatory for eadb/bpftrace)
    subprocess.run(["adb", "-s", device_serial, "root"], check=False)
    time.sleep(2)  # Allow adbd to restart

    # 2. Check if bpftrace is installed inside the eadb environment
    # Skip check if we already verified it for this device in this session
    if device_serial in _bpftrace_checked_devices:
        print(f"bpftrace already verified for device {device_serial}")
        return

    # Check via adb shell /data/eadb/run-command (non-interactive)
    try:
        proc = subprocess.run(
            [
                "adb",
                "-s",
                device_serial,
                "shell",
                "/data/eadb/run-command which bpftrace",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # If bpftrace is found, output will contain the path
        if "bpftrace" in proc.stdout:
            print(f"bpftrace found in eadb environment: {proc.stdout.strip()}")
            _bpftrace_checked_devices.add(device_serial)
        else:
            print("bpftrace not found in eadb environment. Please install it manually.")
            print(
                "Run the 'Setup eadb on device' button to install bpftrace inside eadb."
            )
            print(f"Output: {proc.stdout}")
            print(f"Errors: {proc.stderr}")
    except Exception as e:
        print(f"Failed to check bpftrace status: {e}")
        print(
            "Assuming bpftrace is not installed. Please run 'Setup eadb on device' button."
        )


def _validate_bpftrace_script(script: str) -> tuple[bool, Optional[str]]:
    """
    Validates bpftrace script for dangerous patterns that could cause kernel panics on Android.

    Returns:
        (is_valid, error_message) tuple
    """
    dangerous_patterns = [
        (
            "kprobe:*",
            "Wildcard kprobes can be extremely dangerous and cause kernel panics",
        ),
        (
            "kretprobe:*",
            "Wildcard kretprobes can be extremely dangerous and cause kernel panics",
        ),
        (
            "profile:",
            "Profile probes are UNSTABLE on Android and frequently cause kernel panics. Use tracepoints instead.",
        ),
        (
            "hardware:",
            "Hardware probes are unsupported on most Android devices and cause kernel panics",
        ),
        ("interval:ms:1", "1ms intervals are too aggressive and can crash the kernel"),
        (
            "interval:us:",
            "Microsecond intervals are too aggressive and can crash the kernel",
        ),
    ]

    script_lower = script.lower()
    for pattern, reason in dangerous_patterns:
        if pattern.lower() in script_lower:
            return False, f"Dangerous pattern detected: {reason}"

    # Check for empty script
    if not script.strip():
        return False, "Script cannot be empty"

    return True, None


def run_bpftrace_trace(
    device_serial: str, config, duration_seconds: int = 10
) -> tuple[Optional[str], None]:
    """
    Runs a bpftrace script on an Android device using eadb.

    Args:
        device_serial: Android device serial number
        config: Config object or dict containing config_text (the .bt script)
        duration_seconds: Duration to run the trace

    Returns:
        tuple of (trace_file_path, error_message) on success/failure
        - (trace_path, None) on success
        - (None, error_message) on failure with meaningful error
    """
    # Handle both Config object and dict
    if isinstance(config, dict):
        config_text = config.get("config_text", "")
    else:
        config_text = config.config_text

    # CRITICAL: Validate script before running to prevent kernel panics
    is_valid, error_msg = _validate_bpftrace_script(config_text)
    if not is_valid:
        print(f"ERROR: Script validation failed: {error_msg}")
        print("Script rejected to prevent potential kernel panic.")
        return None, None

    # Parse config into object for easier handling of defaults
    # If the input was just raw text wrapped in the object, we use defaults for paths
    bpftrace_config = BpftraceConfig(config_text=config_text)

    # Verify dependencies
    _check_and_install_dependencies(device_serial)

    local_cache_dir = ".cache/traces"
    os.makedirs(local_cache_dir, exist_ok=True)

    trace_uuid = uuid.uuid4().hex[:8]
    local_script_path = os.path.join(local_cache_dir, f"script_{trace_uuid}.bt")
    local_trace_path = os.path.join(local_cache_dir, f"bpftrace_{trace_uuid}.txt")

    # Push script inside eadb chroot using eadb push
    # This puts it in /tmp/ inside the Debian chroot, not Android's /data/local/tmp
    device_script_path = f"/tmp/script_{trace_uuid}.bt"

    # 1. Write config (.bt script) to local file
    with open(local_script_path, "w") as f:
        f.write(bpftrace_config.config_text)

    # 2. Push .bt script to eadb chroot filesystem
    print(f"Pushing bpftrace script to eadb chroot: {device_script_path}...")
    push_cmd = [
        "eadb",
        "--serial",
        device_serial,
        "push",
        local_script_path,
        device_script_path,
    ]
    if subprocess.run(push_cmd).returncode != 0:
        print("Failed to push bpftrace script to eadb chroot.")
        return None, None

    # 3. Execute bpftrace using /data/eadb/run-command for non-interactive execution
    print(f"Starting bpftrace for {duration_seconds}s...")

    # IMPORTANT: Cap duration to prevent runaway processes
    max_duration = min(duration_seconds, 300)  # Max 5 minutes
    if duration_seconds > max_duration:
        print(
            f"WARNING: Duration capped from {duration_seconds}s to {max_duration}s for safety"
        )

    # Build the command to execute inside eadb
    # CRITICAL: Use inline env vars (VAR=value command) instead of export to ensure they take effect
    # Use full path to bpftrace because PATH is not set in non-interactive shells
    # Use BPFTRACE_CFLAGS (not BPFTRACE_INCLUDE) to specify include directories
    # NOTE: Use double quotes for BPFTRACE_CFLAGS to avoid quote escaping issues
    # NOTE: Do NOT use BPFTRACE_BTF - /sys/kernel/btf/vmlinux is not accessible inside eadb chroot
    #       bpftrace will use kernel headers instead
    bpftrace_cmd = (
        f"PATH=/usr/local/bin:/usr/bin:/bin "
        f'BPFTRACE_CFLAGS="{bpftrace_config.cflags}" '
        f"timeout {max_duration} /usr/bin/bpftrace {device_script_path}"
    )

    print(bpftrace_cmd)

    # Use /data/eadb/run-command for non-interactive execution with stdout capture
    try:
        result = subprocess.run(
            [
                "adb",
                "-s",
                device_serial,
                "shell",
                f"/data/eadb/run-command '{bpftrace_cmd}'",
            ],
            capture_output=True,
            text=True,
            timeout=duration_seconds + 30,
        )

        stdout = result.stdout
        stderr = result.stderr

        print("bpftrace finished.")
        if result.returncode != 0:
            print(f"bpftrace exited with code: {result.returncode}")

        # Filter out bash warnings that aren't useful
        error_lines = []
        if stderr:
            print(f"Stderr: {stderr}")
            for line in stderr.split("\n"):
                line = line.strip()
                # Skip bash terminal warnings
                if "cannot set terminal process group" in line:
                    continue
                if "no job control" in line:
                    continue
                # Keep actual errors
                if line and (
                    "ERROR" in line
                    or "error:" in line
                    or "fatal" in line
                    or "not found" in line
                    or "failed" in line
                ):
                    error_lines.append(line)

        # Save output to file
        if stdout and stdout.strip():
            with open(local_trace_path, "w") as f:
                f.write(stdout)
        else:
            print("No output captured from bpftrace")
            print(f"stdout was: '{stdout}'")
            print(f"stderr was: '{stderr}'")

            # Return meaningful error message
            if error_lines:
                error_msg = "\n".join(error_lines[:3])  # First 3 error lines
                return None, f"bpftrace error: {error_msg}"
            return None, "bpftrace produced no output"

    except subprocess.TimeoutExpired as e:
        print(f"bpftrace execution timed out after {duration_seconds + 30}s")
        # Try to get any partial output
        stdout = e.stdout if e.stdout else ""
        stderr = e.stderr if e.stderr else ""
        if stdout:
            with open(local_trace_path, "w") as f:
                f.write(stdout)
        if stderr:
            print(f"Stderr: {stderr}")
        return None, "bpftrace execution timed out"

    # Cleanup: Remove local temp script and device script
    if os.path.exists(local_script_path):
        os.unlink(local_script_path)

    # Remove script from eadb chroot
    subprocess.run(
        [
            "adb",
            "-s",
            device_serial,
            "shell",
            f"/data/eadb/run-command 'rm -f {device_script_path}'",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if os.path.exists(local_trace_path) and os.path.getsize(local_trace_path) > 0:
        print(f"Successfully retrieved bpftrace output: {local_trace_path}")
        return local_trace_path, None
    else:
        print("Trace file was not created or is empty. Check logs for errors.")
        return None, None
