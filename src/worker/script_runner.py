available_scripts = {
    "eadb_install": "src/worker/scripts/eadb_install.sh",
    "bpftrace_install": "src/worker/scripts/bpftrace_install.sh",
}

def _run_script(script_path: str) -> None:
    import subprocess

    try:
        subprocess.run(["bash", script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running the script: {e}")

def run_script_in_worker(script_name: str) -> None:
    script_path = available_scripts.get(script_name)
    if script_path:
        _run_script(script_path)
    else:
        print(f"Script '{script_name}' not found in available scripts.")
    