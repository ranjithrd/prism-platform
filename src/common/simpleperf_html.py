import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from src.common.minio import MinioHelper

load_dotenv()

logging.basicConfig(level=logging.INFO)

SIMPLEPERF_FLAGS = ["--no_browser"]

DEFAULT_SEARCH_PATHS = [
    Path.home() / "Android" / "Sdk",
    Path.home() / "android-sdk",
    Path("/opt/android-sdk"),
    Path("/usr/lib/android-sdk"),
    Path("/usr/local/lib/android-sdk"),
]


def _find_report_script() -> Path:
    """Locates the report_html.py script by checking environment variables and standard installation directories."""
    env_script_path = os.getenv("SIMPLEPERF_SCRIPT_PATH")
    if env_script_path:
        path = Path(env_script_path)
        if path.exists() and path.is_file():
            return path
        logging.warning(
            f"SIMPLEPERF_SCRIPT_PATH set to {env_script_path} but file not found."
        )

    potential_ndk_roots = []

    android_ndk_home = os.getenv("ANDROID_NDK_HOME")
    if android_ndk_home:
        potential_ndk_roots.append(Path(android_ndk_home))

    android_home = os.getenv("ANDROID_HOME")
    if android_home:
        potential_ndk_roots.append(Path(android_home) / "ndk")

    android_sdk_root = os.getenv("ANDROID_SDK_ROOT")
    if android_sdk_root:
        potential_ndk_roots.append(Path(android_sdk_root) / "ndk")

    for p in DEFAULT_SEARCH_PATHS:
        potential_ndk_roots.append(p / "ndk")

    for ndk_root in potential_ndk_roots:
        if not ndk_root.exists():
            continue

        versions = sorted([d for d in ndk_root.iterdir() if d.is_dir()], reverse=True)

        for version_dir in versions:
            script = version_dir / "simpleperf" / "report_html.py"
            if script.exists():
                return script

            script_legacy = version_dir / "simpleperf" / "report.py"
            if script_legacy.exists():
                return script_legacy

    local_check = Path("simpleperf") / "report_html.py"
    if local_check.exists():
        return local_check.resolve()

    raise FileNotFoundError(
        "Could not locate 'report_html.py'. Please ensure the Android NDK is installed "
        "or set ANDROID_NDK_HOME in your .env file."
    )


def _generate_simpleperf_html(local_trace_filepath: str) -> str:
    """Generates an HTML report from a simpleperf .data file.

    Args:
        local_trace_filepath: Path to the .data file

    Returns:
        The filepath to the generated HTML file in .cache/html_files/
    """
    input_path = Path(local_trace_filepath).resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Trace file not found: {input_path}")

    html_output_dir = Path(".cache/html_files").resolve()
    html_output_dir.mkdir(parents=True, exist_ok=True)

    output_filename = input_path.stem + ".html"
    output_path = html_output_dir / output_filename

    script_path = _find_report_script()
    logging.info(f"Using Simpleperf script: {script_path}")

    cmd = [
        sys.executable,
        str(script_path),
        "-i",
        str(input_path),
        "-o",
        str(output_path.resolve()),
    ]

    cmd.extend(SIMPLEPERF_FLAGS)

    try:
        logging.info(f"Executing: {' '.join(cmd)}")
        subprocess.run(
            cmd, check=True, cwd=script_path.parent, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        logging.error(f"Simpleperf generation failed with exit code {e.returncode}")
        raise

    return str(output_path)


def generate_simpleperf_html(minio_filename: str, minio: MinioHelper) -> Optional[str]:
    """Download simpleperf .data file from MinIO, generate HTML report, and upload back to MinIO.

    Args:
        minio_filename: The object name in MinIO (e.g., "simpleperf_abc123.data")
        minio: MinioHelper instance for downloading/uploading

    Returns:
        The MinIO object name of the uploaded HTML file, or None if generation fails
    """
    try:
        local_data_path = minio.download_cached(minio.DEFAULT_BUCKET, minio_filename)
        if not local_data_path:
            logging.error(f"Failed to download simpleperf data file: {minio_filename}")
            return None

        logging.info(f"Downloaded simpleperf data to: {local_data_path}")

        local_html_path = _generate_simpleperf_html(local_data_path)

        logging.info(f"Generated simpleperf HTML at: {local_html_path}")

        with open(local_html_path, "rb") as f:
            html_bytes = f.read()

        html_filename = Path(minio_filename).stem + ".html"

        minio.upload_bytes(minio.DEFAULT_BUCKET, html_filename, html_bytes)
        logging.info(f"Successfully uploaded HTML report: {html_filename}")

        return html_filename

    except Exception as e:
        logging.error(f"Failed to generate simpleperf HTML: {e}")
        return None
