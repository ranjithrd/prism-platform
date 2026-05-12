import argparse
import subprocess
import sys
import uuid
from pathlib import Path

# --- CONFIGURATION FOR ALPHA ---
REMOTE_USER = "<USERNAME>"
REMOTE_HOST = "<VPN IP ADDRESS>"
# Path on REMOTE SYSTEM where the REAL report_html.py lives
REMOTE_REAL_SCRIPT = "/var/lib/android/ndk/27.0.12077973/simpleperf/report_html.py"


def main():
    # 1. Parse the arguments passed by your immutable app
    # The app passes: -i <input> -o <output> [flags]
    parser = argparse.ArgumentParser(description="Proxy for remote SimplePerf")
    parser.add_argument(
        "-i", "--record_file", required=True, help="Path to input .data file"
    )
    parser.add_argument(
        "-o", "--report_path", required=True, help="Path to output .html file"
    )

    # Capture known args, leave the rest (flags) to pass through
    args, unknown_args = parser.parse_known_args()

    local_input_path = Path(args.record_file).resolve()
    local_output_path = Path(args.report_path).resolve()

    # 2. Generate safe remote filenames
    # We use a UUID to prevent collisions if multiple jobs run at once
    job_id = uuid.uuid4().hex
    remote_input = f"/tmp/{job_id}.data"
    remote_output = f"/tmp/{job_id}.html"
    connection = f"{REMOTE_USER}@{REMOTE_HOST}"

    print(f"[Proxy] Intercepted job. Offloading to {REMOTE_HOST}...")

    try:
        # 3. SCP Input to Remote
        print(f"[Proxy] Uploading {local_input_path.name} -> {remote_input}")
        subprocess.run(
            ["scp", str(local_input_path), f"{connection}:{remote_input}"], check=True
        )

        # 4. SSH to run the REAL script on x86
        # We reconstruct the command using the unknown_args (flags)
        extra_flags = " ".join(unknown_args)

        # Note: We execute python3 on the remote machine
        remote_cmd = (
            f"python3 {REMOTE_REAL_SCRIPT} "
            f"-i {remote_input} "
            f"-o {remote_output} "
            f"{extra_flags}"
        )

        print("[Proxy] Executing on x86...")
        subprocess.run(["ssh", connection, remote_cmd], check=True)

        # 5. SCP Output back to Local
        print(f"[Proxy] Downloading result -> {local_output_path}")
        subprocess.run(
            ["scp", f"{connection}:{remote_output}", str(local_output_path)], check=True
        )

        # 6. Cleanup Remote (Optional but polite)
        subprocess.run(
            ["ssh", connection, f"rm -f {remote_input} {remote_output}"],
            stderr=subprocess.DEVNULL,
        )

        print("[Proxy] Success.")

    except subprocess.CalledProcessError as e:
        print(f"[Proxy] Remote execution failed with code {e.returncode}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"[Proxy] Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
