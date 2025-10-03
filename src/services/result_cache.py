import json
from pathlib import Path
from typing import Dict, Any, Optional

# Define the path for the cache file
CACHE_DIR = Path(".cache")
CACHE_FILE = CACHE_DIR / "results.json"


def _load_cache() -> Dict[str, Any]:
    """Loads the entire cache from the JSON file."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Return an empty dict if the file is empty or corrupt
        return {}


def _save_cache(cache_data: Dict[str, Any]):
    """Saves the entire cache to the JSON file."""
    # Ensure the .cache directory exists
    CACHE_DIR.mkdir(exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f, indent=4)


def get_cached_result(key: str) -> Optional[Any]:
    """Reads the cache from disk and returns the value for a specific key."""
    cache = _load_cache()
    return cache.get(key)


def set_cached_result(key: str, value: Any):
    """Reads the cache, updates it with a new key-value pair, and saves it back to disk."""
    cache = _load_cache()
    cache[key] = value
    _save_cache(cache)


def get_result_for_datatables(key: str, draw: int) -> Optional[Dict[str, Any]]:
    """
    Gets a cached result and formats it for a DataTables.net server-side response.

    Note: This implementation does not handle server-side filtering, sorting, or pagination.
    It returns the entire cached dataset.
    """
    result = get_cached_result(key)
    if not result or not isinstance(result, list):
        return None

    return {
        "draw": draw,
        "data": result,
        "recordsTotal": len(result),
        "recordsFiltered": len(result),
    }
