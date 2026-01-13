#!/usr/bin/env python3
"""
Install bpftrace inside eadb Debian environment on a specific device.
Called from GUI "Setup eadb on device" button.
"""

import os
import subprocess
import sys
from time import sleep

# Add parent directory to path to import run_eadb_command
sys.path.insert(0, os.path.dirname(__file__))
from run_eadb_command import run_eadb_script


def main():
    if len(sys.argv) < 2:
        print("Error: Device serial number required")
        print("Usage: python3 bpftrace_install.py <device_serial>")
        sys.exit(1)

    device_serial = sys.argv[1]
    print(f"Installing bpftrace on device: {device_serial}")
    print("")

    # Ensure adb is running as root
    print("Ensuring adb root access...")
    try:
        root_result = subprocess.run(
            ["adb", "-s", device_serial, "root"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if root_result.stdout:
            print(root_result.stdout.strip())
        if root_result.stderr:
            print(root_result.stderr.strip())

        # Wait a moment for adb to restart as root
        sleep(2)
        print("")
    except Exception as e:
        print(f"⚠ Warning: Could not ensure root access: {e}")
        print("")

    # Get the installation script path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    install_script = os.path.join(script_dir, "eadbshell_install_bpftrace.sh")

    if not os.path.exists(install_script):
        print(f"Error: Installation script not found: {install_script}")
        sys.exit(1)

    print("Pushing and executing installation script...")
    print("")

    # Try to run the installation script inside eadb
    success, output = run_eadb_script(device_serial, install_script, timeout=600)

    # If failed, eadb might not be set up on this device yet
    if not success:
        print(output)
        print("")
        print("⚠ eadb may not be set up on this device yet.")
        print("Running 'eadb prepare' to set up eadb...")
        print("")

        try:
            # Run eadb prepare to set up eadb on the device
            prepare_result = subprocess.run(
                ["eadb", "prepare"],
                capture_output=True,
                text=True,
                timeout=300,
            )

            print(prepare_result.stdout)
            if prepare_result.stderr:
                print(prepare_result.stderr)

            if prepare_result.returncode != 0:
                print("")
                print(
                    "✗ eadb prepare failed. Cannot proceed with bpftrace installation."
                )
                sys.exit(1)

            print("")
            print("✓ eadb prepare completed. Retrying bpftrace installation...")
            print("")

            # eadb prepare causes the device to disconnect/reconnect
            # Wait for device to come back online
            print("Waiting for device to come back online...")
            wait_result = subprocess.run(
                ["adb", "-s", device_serial, "wait-for-device"],
                timeout=30,
                capture_output=True,
            )

            if wait_result.returncode != 0:
                print("✗ Device did not come back online")
                sys.exit(1)

            # Give it a few more seconds for eadb to fully initialize
            sleep(5)
            print("Device ready. Initializing eadb environment...")
            print("")

            # Run eadb shell once to trigger initialization and create necessary scripts
            # This creates /data/eadb/run-command and other required files
            # try:
            #     init_result = subprocess.run(
            #         ["eadb", "--serial", device_serial, "shell", "exit"],
            #         timeout=10,
            #         capture_output=True,
            #         text=True,
            #     )
            #     # Don't care about exit code, just that it ran
            #     print("eadb environment initialized.")
            #     print("")
            # except subprocess.TimeoutExpired:
            #     print("⚠ eadb shell initialization timed out, continuing anyway...")
            #     print("")
            # except Exception as e:
            #     print(f"⚠ eadb shell initialization error (continuing): {e}")
            #     print("")

            print("Retrying bpftrace installation...")
            print("")

            # Retry the installation
            success, output = run_eadb_script(
                device_serial, install_script, timeout=600
            )

        except subprocess.TimeoutExpired:
            print("")
            print("✗ eadb prepare timed out after 300 seconds")
            sys.exit(1)
        except FileNotFoundError:
            print("")
            print("✗ eadb command not found. Please install eadb globally first.")
            sys.exit(1)
        except Exception as e:
            print("")
            print(f"✗ Error running eadb prepare: {e}")
            sys.exit(1)

    print(output)

    if success:
        print("")
        print("✓ bpftrace installation completed successfully!")
        sys.exit(0)
    else:
        print("")
        print("✗ bpftrace installation failed. Check output above for errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()
