#!/usr/bin/env python3
"""
PRISM Worker GUI with integrated background threads.
Runs the device monitor and job listener threads alongside the GUI.
"""

import threading


def start_background_threads(device_callback, error_callback):
    """Start background worker threads.

    Args:
        device_callback: Function to register for device updates from background threads
        error_callback: Function to register for error notifications
    """
    from src.worker.background import (
        register_error_callback,
        register_gui_callback,
        run_listen_pubsub,
        run_update_devices,
    )

    # Register the GUI callbacks
    register_gui_callback(device_callback)
    register_error_callback(error_callback)

    # Start device monitoring thread
    devices_thread = threading.Thread(
        target=run_update_devices, daemon=True, name="DevicesThread"
    )
    devices_thread.start()
    print("[GUI] Started device monitoring thread")

    # Start job listener thread
    pubsub_thread = threading.Thread(
        target=run_listen_pubsub, daemon=True, name="PubSubThread"
    )
    pubsub_thread.start()
    print("[GUI] Started job listener thread")


if __name__ == "__main__":
    from src.worker.gui import run_gui

    # Run GUI with background threads
    run_gui(device_update_callback=start_background_threads)
