"""
Helper module to run commands inside eadb Debian environment.

Abstracts the complexity of /data/eadb/run-command execution.
"""

import os
import subprocess
import uuid
from typing import Optional, Tuple


def run_eadb_command(
    device_serial: str, command: str, timeout: Optional[int] = 30, check: bool = False
) -> subprocess.CompletedProcess:
    """
    Run a command inside the eadb Debian chroot environment.

    This function handles the complexity of executing commands via
    /data/eadb/run-command, which provides non-interactive access to
    the Debian environment on Android devices.

    Args:
        device_serial: Android device serial number
        command: Command to execute inside eadb (shell command as string)
        timeout: Command timeout in seconds (default: 30)
        check: If True, raise CalledProcessError on non-zero exit

    Returns:
        CompletedProcess object with stdout, stderr, and returncode

    Example:
        result = run_eadb_command("R3CWA04BBSZ", "ls /tmp")
        if result.returncode == 0:
            print(result.stdout)
    """
    # Build the adb shell command with /data/eadb/run-command
    # This chroots into /data/eadb/debian/ and executes the command
    adb_cmd = [
        "adb",
        "-s",
        device_serial,
        "shell",
        f"/data/eadb/run-command '{command}'",
    ]

    return subprocess.run(
        adb_cmd, capture_output=True, text=True, timeout=timeout, check=check
    )


def run_eadb_script(
    device_serial: str, script_path: str, timeout: Optional[int] = 300
) -> Tuple[bool, str]:
    """
    Push and execute a shell script inside the eadb environment.

    Args:
        device_serial: Android device serial number
        script_path: Local path to the shell script
        timeout: Script execution timeout in seconds

    Returns:
        (success: bool, output: str) tuple
    """
    script_name = os.path.basename(script_path)
    remote_path = f"/tmp/{script_name}.{uuid.uuid4().hex[:8]}"

    # Push script to eadb chroot /tmp/
    push_result = subprocess.run(
        ["eadb", "--serial", device_serial, "push", script_path, remote_path],
        capture_output=True,
        text=True,
    )

    if push_result.returncode != 0:
        return False, f"Failed to push script: {push_result.stderr}"

    # Make script executable and run it
    chmod_result = run_eadb_command(
        device_serial, f"chmod +x {remote_path}", timeout=10
    )
    if chmod_result.returncode != 0:
        return False, f"Failed to chmod script: {chmod_result.stderr}"

    # Execute the script
    exec_result = run_eadb_command(
        device_serial, f"/bin/bash {remote_path}", timeout=timeout
    )

    # Cleanup
    run_eadb_command(device_serial, f"rm -f {remote_path}", timeout=10)

    output = exec_result.stdout + "\n" + exec_result.stderr
    success = exec_result.returncode == 0

    return success, output
