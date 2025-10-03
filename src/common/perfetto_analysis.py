import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig
from sqlmodel import Session, select

from src.common.db import Trace, Query
from src.common.minio import MinioHelper

CACHE_DIR = Path(".cache")
QUERY_CACHE_FILE = CACHE_DIR / "queries.json"


def _load_query_cache() -> Dict[str, Any]:
    """Loads the query cache from the JSON file."""
    if not QUERY_CACHE_FILE.exists():
        return {}
    try:
        with open(QUERY_CACHE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_query_cache(cache_data: Dict[str, Any]):
    """Saves the given dictionary to the query cache JSON file."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(QUERY_CACHE_FILE, "w") as f:
        json.dump(cache_data, f, indent=2)


def _get_actual_binary_path() -> str:
    """
    Finds the path to the trace_processor_shell binary by mimicking the
    perfetto library's internal logic. This is robust and avoids hallucinations.
    """
    try:
        home_dir = Path.home()
    except RuntimeError:
        home_dir = None

    print("\n--- PERFETTO BINARY DIAGNOSTICS ---")
    print(f"Python Executable: {sys.executable}")
    print(f"HOME Environment Var: {os.getenv('HOME')}")
    print(f"Path.home() resolved to: {home_dir}")

    if not home_dir:
        print("CRITICAL: Could not determine home directory. Perfetto cannot find its binary.")
        print("--- END DIAGNOSTICS ---\n")
        raise FileNotFoundError("Perfetto binary could not be found because the home directory is not set.")

    binary_path = home_dir / ".local" / "share" / "perfetto" / "prebuilts" / "trace_processor_shell"

    print(f"Constructed binary path: {binary_path}")
    print(f"Does the binary exist at this path? -> {binary_path.exists()}")
    print("--- END DIAGNOSTICS ---\n")

    if not binary_path.exists():
        raise FileNotFoundError(f"Perfetto binary not found at the expected path: {binary_path}")

    return str(binary_path)


def run_query_on_file(filepath: str, query: str) -> Dict[str, List[Any]]:
    """
    Runs a SQL query on a Perfetto trace file by explicitly finding and using
    the library's managed binary, making it immune to environment issues.
    """
    try:
        correct_shell_path = _get_actual_binary_path()
        config = TraceProcessorConfig(bin_path=correct_shell_path)
        tp = TraceProcessor(trace=filepath, config=config)

        query_iterator = tp.query(query)
        columns: List[str] = []
        rows: List[List[Any]] = []
        is_first_row = True

        for row in query_iterator:
            if is_first_row:
                columns = list(vars(row).keys())
                is_first_row = False
            rows.append([getattr(row, col) for col in columns])

        return {"columns": columns, "rows": rows}
    except Exception as e:
        print(f"An error occurred during trace processing: {e}")
        raise


def run_perfetto_query(trace_id: str, query_id: str, session: Session, minio: MinioHelper) -> Dict[str, List[Any]]:
    trace_db_rec = session.exec(select(Trace).where(Trace.trace_id == trace_id)).first()
    query_db_rec = session.exec(select(Query).where(Query.query_id == query_id)).first()

    if not (trace_db_rec and query_db_rec):
        raise ValueError("Trace or Query not found in the database.")

    # --- Caching Logic ---
    filename = trace_db_rec.trace_filename
    query_text = query_db_rec.query_text
    cache_key = hashlib.sha256((filename + query_text).encode()).hexdigest()

    query_cache = _load_query_cache()

    if cache_key in query_cache:
        return query_cache[cache_key]

    # --- Cache Miss: Execute Query ---
    local_path = minio.download_cached(minio.DEFAULT_BUCKET, filename)
    if not local_path:
        raise FileNotFoundError(f"Trace file '{filename}' could not be downloaded.")

    result = run_query_on_file(local_path, query_text)

    # --- Update and save cache ---
    query_cache[cache_key] = result
    _save_query_cache(query_cache)

    return result
