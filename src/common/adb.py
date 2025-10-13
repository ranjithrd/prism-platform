import logging
import os
import shutil
import subprocess
from typing import List, Optional, Tuple, Dict

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Pre-flight Check ---
if not shutil.which("adb"):
    logging.error("ADB command not found. Please ensure it is installed and in your system's PATH.")
    # This won't stop execution, but will log a clear error on import.
    # A hard exit might be desired in some applications.


# --- Internal Helper ---

def _run_command(command: List[str]) -> Tuple[bool, str, str]:
    """
    Internal helper to run a shell command and capture its output.

    Args:
        command (List[str]): The command to execute as a list of strings.

    Returns:
        Tuple[bool, str, str]: A tuple containing success (boolean), stdout (str), and stderr (str).
    """
    try:
        logging.info(f"Running command: {' '.join(command)}")
        process = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return True, process.stdout.strip(), process.stderr.strip()
    except FileNotFoundError:
        logging.error(f"Command not found: {command[0]}. Ensure it is installed and in PATH.")
        return False, "", "Command not found."
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed with exit code {e.returncode}: {' '.join(command)}")
        logging.error(f"STDOUT: {e.stdout.strip()}")
        logging.error(f"STDERR: {e.stderr.strip()}")
        return False, e.stdout.strip(), e.stderr.strip()


def _add_serial(base_command: List[str], serial: Optional[str]) -> List[str]:
    """Adds the -s <serial> flag to a command if a serial is provided."""
    if serial:
        return [base_command[0], "-s", serial] + base_command[1:]
    return base_command


# --- Public ADB Functions ---

def adb_devices() -> List[Dict[str, str]]:
    """
    Lists all connected devices and their states.

    Returns:
        List[Dict[str, str]]: A list of dictionaries, each representing a device.
        Example: [{'serial': 'emulator-5554', 'state': 'device'}]
    """
    success, stdout, _ = _run_command(["adb", "devices"])
    if not success or not stdout:
        return []

    lines = stdout.strip().split('\n')
    # Skip the "List of devices attached" header
    devices_lines = lines[1:]

    devices = []
    for line in devices_lines:
        if not line.strip():
            continue
        try:
            serial, state = line.split('\t')
            devices.append({"serial": serial.strip(), "state": state.strip()})
        except ValueError:
            logging.warning(f"Could not parse device line: '{line}'")

    return devices


def adb_shell(command: str, serial: Optional[str] = None) -> Tuple[bool, str, str]:
    """
    Executes an arbitrary shell command on a device.

    Args:
        command (str): The command to run in the device's shell.
        serial (Optional[str]): The specific device serial to target.

    Returns:
        Tuple[bool, str, str]: A tuple of success, stdout, and stderr.
    """
    base_cmd = ["adb", "shell", command]
    cmd = _add_serial(base_cmd, serial)
    return _run_command(cmd)


def adb_pull(remote_path: str, local_dir: str = ".cache/adb", serial: Optional[str] = None) -> Optional[str]:
    """
    Pulls a file from a device to a local cache directory.

    Args:
        remote_path (str): The full path of the file on the device.
        local_dir (str): The local directory to save the file to. Defaults to '.cache/adb'.
        serial (Optional[str]): The specific device serial to target.

    Returns:
        Optional[str]: The full local path to the saved file, or None on failure.
    """
    os.makedirs(local_dir, exist_ok=True)

    # Construct a safe local filepath
    filename = os.path.basename(remote_path)
    local_filepath = os.path.join(local_dir, filename)

    base_cmd = ["adb", "pull", remote_path, local_filepath]
    cmd = _add_serial(base_cmd, serial)

    success, _, _ = _run_command(cmd)

    return local_filepath if success else None


def adb_push(local_path: str, remote_path: str, serial: Optional[str] = None) -> bool:
    """
    Pushes a local file to a device.

    Args:
        local_path (str): The path to the local file to push.
        remote_path (str): The destination path on the device.
        serial (Optional[str]): The specific device serial to target.

    Returns:
        bool: True if the push was successful, False otherwise.
    """
    if not os.path.exists(local_path):
        logging.error(f"Local file not found: {local_path}")
        return False

    base_cmd = ["adb", "push", local_path, remote_path]
    cmd = _add_serial(base_cmd, serial)

    success, _, _ = _run_command(cmd)
    return success


# --- Common Utility Functions ---

def adb_install(apk_path: str, reinstall: bool = True, serial: Optional[str] = None) -> bool:
    """
    Installs an APK on a device.

    Args:
        apk_path (str): The path to the local .apk file.
        reinstall (bool): If True, allows updating an existing app (uses -r flag).
        serial (Optional[str]): The specific device serial to target.

    Returns:
        bool: True if installation was successful, False otherwise.
    """
    if not os.path.exists(apk_path):
        logging.error(f"APK file not found: {apk_path}")
        return False

    cmd_args = ["adb", "install"]
    if reinstall:
        cmd_args.append("-r")
    cmd_args.append(apk_path)

    cmd = _add_serial(cmd_args, serial)
    success, _, _ = _run_command(cmd)
    return success


def adb_uninstall(package_name: str, serial: Optional[str] = None) -> bool:
    """
    Uninstalls a package from a device.

    Args:
        package_name (str): The package name (e.g., com.example.app).
        serial (Optional[str]): The specific device serial to target.

    Returns:
        bool: True if uninstallation was successful, False otherwise.
    """
    base_cmd = ["adb", "uninstall", package_name]
    cmd = _add_serial(base_cmd, serial)
    success, _, _ = _run_command(cmd)
    return success


def adb_reboot(serial: Optional[str] = None) -> bool:
    """
    Reboots a device.

    Args:
        serial (Optional[str]): The specific device serial to target.

    Returns:
        bool: True if the command was sent successfully, False otherwise.
    """
    base_cmd = ["adb", "reboot"]
    cmd = _add_serial(base_cmd, serial)
    success, _, _ = _run_command(cmd)
    return success
