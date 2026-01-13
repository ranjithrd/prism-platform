"""
PRISM Platform Worker GUI
Ultra-simple PySide6 (Qt) interface for managing worker configuration and viewing devices.
"""

import platform
import subprocess
import sys
import threading

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.worker.config import get_value_from_config, set_value_in_config, worker_config
from src.worker.script_runner import run_script_in_worker


class DeviceUpdateSignal(QObject):
    """Signal emitter for thread-safe device updates."""

    devices_updated = Signal(list)  # List of (serial, status, extra_info)
    error_occurred = Signal(str)  # Error message
    status_message = Signal(str, str)  # (message, color) for status updates


class PrismWorkerGUI(QMainWindow):
    def __init__(self, device_callback=None, job_callback=None):
        """
        Initialize the GUI.

        Args:
            device_callback: Optional callback function to register for device updates.
                             Will be called as: callback(device_list)
            job_callback: Optional callback for job status updates (future use)
        """
        super().__init__()

        # Shutdown event for background threads
        self.shutdown_event = threading.Event()

        # Track device states: serial -> (status, extra_info)
        self.device_states = {}

        # Signal for thread-safe updates
        self.signal_emitter = DeviceUpdateSignal()
        self.signal_emitter.devices_updated.connect(self.update_device_list)
        self.signal_emitter.error_occurred.connect(self.show_error_status)
        self.signal_emitter.status_message.connect(self.show_status_message)

        # Store callback for external registration
        if device_callback:
            device_callback(
                self.signal_emitter.devices_updated.emit,
                self.signal_emitter.error_occurred.emit,
            )

        # Setup window
        self.setWindowTitle("PRISM Worker")
        self.setFixedSize(500, 600)

        # Set app icon - create a simple colored square icon
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        from PySide6.QtGui import QColor, QPainter

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Draw a nice purple/blue gradient square
        painter.fillRect(0, 0, 64, 64, QColor("#6366f1"))
        painter.end()
        self.setWindowIcon(QIcon(pixmap))

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Setup UI components
        self.setup_ui(main_layout)

    def setup_ui(self, main_layout):
        """Create the GUI layout."""
        # --- Header Section ---

        # Header with title and quit button
        header_layout = QHBoxLayout()

        # Title (left-aligned)
        title = QLabel("PRISM Platform Worker")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(title)

        # Spacer
        header_layout.addStretch()

        # Quit button (right-aligned, subtle)
        quit_button = QPushButton("Quit")
        quit_button.setFont(QFont("Arial", 10))
        quit_button.setFixedSize(50, 24)
        quit_button.clicked.connect(self.close)
        quit_button.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: 1px solid #ef4444;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: white;
            }
            QPushButton:pressed {
                background-color: #dc2626;
            }
        """
        )
        header_layout.addWidget(quit_button)

        main_layout.addLayout(header_layout)
        main_layout.addSpacing(10)

        # API Key Label
        api_label = QLabel("API Key:")
        api_label.setFont(QFont("Arial", 14))
        main_layout.addWidget(api_label)

        # API Key Input
        self.api_key_input = QLineEdit()
        self.api_key_input.setFont(QFont("Arial", 12))
        self.api_key_input.setPlaceholderText("Enter your API key...")
        self.api_key_input.setMinimumHeight(32)

        # Load existing API key
        current_key = get_value_from_config("auth_token", "")
        if current_key:
            self.api_key_input.setText(current_key)

        main_layout.addWidget(self.api_key_input)

        # Save Button
        save_button = QPushButton("Save API Key")
        save_button.setFont(QFont("Arial", 12))
        save_button.setMinimumHeight(32)
        save_button.clicked.connect(self.save_api_key)
        save_button.setStyleSheet(
            """
            QPushButton {
                background-color: #3b8ed0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #2a7ab9;
            }
            QPushButton:pressed {
                background-color: #1f5c8a;
            }
        """
        )
        main_layout.addWidget(save_button)

        # Install eadb Button (subtle styling)
        install_eadb_button = QPushButton("Install eadb")
        install_eadb_button.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        install_eadb_button.setMinimumHeight(32)
        install_eadb_button.clicked.connect(self.install_eadb)
        install_eadb_button.setStyleSheet(
            """
            QPushButton {
                background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: palette(light);
            }
            QPushButton:pressed {
                background-color: palette(midlight);
            }
        """
        )
        main_layout.addWidget(install_eadb_button)
        main_layout.addSpacing(15)

        # API URL Display (left-aligned, bold)
        self.api_url_label = QLabel()
        self.api_url_label.setFont(QFont("Arial", 12))
        self.api_url_label.setTextFormat(Qt.TextFormat.RichText)
        self.api_url_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(self.api_url_label)

        # Hostname Display (left-aligned, bold)
        self.hostname_label = QLabel()
        self.hostname_label.setFont(QFont("Arial", 12))
        self.hostname_label.setTextFormat(Qt.TextFormat.RichText)
        self.hostname_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(self.hostname_label)

        # Refresh config display
        self.refresh_config_display()

        main_layout.addSpacing(10)

        # --- Devices Section (rest of space) ---

        # Devices Label
        devices_label = QLabel("Connected Devices:")
        devices_label.setFont(QFont("Arial", 14))
        main_layout.addWidget(devices_label)

        # Scroll Area for Devices
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Container for device list
        self.devices_container = QWidget()
        self.devices_layout = QVBoxLayout(self.devices_container)
        self.devices_layout.setContentsMargins(0, 0, 0, 0)
        self.devices_layout.setSpacing(5)
        self.devices_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll_area.setWidget(self.devices_container)
        main_layout.addWidget(scroll_area)

        # Status/Error message label (initially hidden) - moved above devices
        self.status_label = QLabel()
        self.status_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        # Insert above API URL (after save button, before API URL label)
        main_layout.insertWidget(
            main_layout.indexOf(self.api_url_label), self.status_label
        )

        # Initial empty device list
        self.update_device_list([])

    def refresh_config_display(self):
        """Refresh the API URL and Hostname display from config."""
        worker_config.refresh_config()

        # Update API URL label
        api_url = worker_config.api_url or "Not configured"
        self.api_url_label.setText(f"<b>API URL:</b> {api_url}")

        # Update Hostname label
        hostname = worker_config.hostname or "Not configured"
        self.hostname_label.setText(f"<b>Hostname:</b> {hostname}")

    def save_api_key(self):
        """Save the API key to config.json."""
        api_key = self.api_key_input.text().strip()
        if api_key:
            set_value_in_config("auth_token", api_key)
            self.refresh_config_display()  # Refresh after saving
            self.show_status_message("✓ API Key saved successfully!", "#22c55e")
        else:
            self.show_status_message("✗ API Key cannot be empty!", "#ef4444")

    def install_eadb(self):
        """Install eadb by opening a new terminal window."""
        try:
            self.show_status_message(
                "Opening terminal for eadb installation...", "#3b82f6"
            )

            # Get the script path
            import os

            script_dir = os.path.join(os.path.dirname(__file__), "scripts")
            script_path = os.path.join(script_dir, "eadb_install.sh")

            # Open new terminal based on OS
            if platform.system() == "Darwin":  # macOS
                # Use osascript to open Terminal.app with the script
                subprocess.Popen(
                    [
                        "osascript",
                        "-e",
                        f'tell app "Terminal" to do script "bash {script_path}"',
                    ]
                )
            elif platform.system() == "Linux":
                # Try common Linux terminals
                terminals = ["gnome-terminal", "konsole", "xterm"]
                for term in terminals:
                    if (
                        subprocess.run(["which", term], capture_output=True).returncode
                        == 0
                    ):
                        if term == "gnome-terminal":
                            subprocess.Popen([term, "--", "bash", script_path])
                        else:
                            subprocess.Popen([term, "-e", f"bash {script_path}"])
                        break
            elif platform.system() == "Windows":
                # Use Windows Terminal if available, fallback to cmd
                subprocess.Popen(
                    ["cmd", "/c", "start", "cmd", "/k", f"bash {script_path}"],
                    shell=True,
                )
            else:  # Fallback
                # Fallback to background execution with status update
                import threading

                def run_install():
                    try:
                        run_script_in_worker("eadb_install")
                        self.signal_emitter.status_message.emit(
                            "✓ eadb installed successfully!", "#22c55e"
                        )
                    except Exception as e:
                        self.signal_emitter.status_message.emit(
                            f"✗ Installation failed: {str(e)}", "#ef4444"
                        )

                threading.Thread(target=run_install, daemon=True).start()
                return

            self.show_status_message(
                "Terminal opened - check terminal window for progress", "#22c55e"
            )
        except Exception as e:
            self.show_status_message(f"✗ Error: {str(e)}", "#ef4444")

    def setup_eadb_for_device(self, device_serial):
        """Set up eadb and install bpftrace by opening a new terminal window."""
        try:
            self.show_status_message(
                f"Opening terminal for bpftrace installation on {device_serial}...",
                "#3b82f6",
            )

            # Get the Python script path
            import os

            script_dir = os.path.join(os.path.dirname(__file__), "scripts")
            script_path = os.path.join(script_dir, "bpftrace_install.py")

            # Open new terminal based on OS
            if platform.system() == "Darwin":  # macOS
                # Use osascript to open Terminal.app with the Python script
                commands = f"python3 {script_path} {device_serial}"
                subprocess.Popen(
                    [
                        "osascript",
                        "-e",
                        f'tell app "Terminal" to do script "{commands}"',
                    ]
                )
            elif platform.system() == "Linux":
                # Try common Linux terminals
                terminals = ["gnome-terminal", "konsole", "xterm"]
                commands = f"python3 {script_path} {device_serial}"
                for term in terminals:
                    if (
                        subprocess.run(["which", term], capture_output=True).returncode
                        == 0
                    ):
                        if term == "gnome-terminal":
                            subprocess.Popen([term, "--", "bash", "-c", commands])
                        else:
                            subprocess.Popen([term, "-e", f"bash -c '{commands}'"])
                        break
            elif platform.system() == "Windows":
                # Use Windows cmd to spawn new window with Python script
                subprocess.Popen(
                    [
                        "cmd",
                        "/c",
                        "start",
                        "cmd",
                        "/k",
                        f"python {script_path} {device_serial}",
                    ],
                    shell=True,
                )
            else:  # Fallback
                # Fallback to background execution
                import threading

                def run_setup():
                    try:
                        result = subprocess.run(
                            ["python3", script_path, device_serial],
                            capture_output=True,
                            text=True,
                            timeout=600,
                        )
                        if result.returncode == 0:
                            self.signal_emitter.status_message.emit(
                                f"✓ bpftrace installed for {device_serial}!", "#22c55e"
                            )
                        else:
                            self.signal_emitter.status_message.emit(
                                "✗ Installation failed", "#ef4444"
                            )
                    except subprocess.TimeoutExpired:
                        self.signal_emitter.status_message.emit(
                            "✗ Installation timed out", "#ef4444"
                        )
                    except Exception as e:
                        self.signal_emitter.status_message.emit(
                            f"✗ Installation failed: {str(e)}", "#ef4444"
                        )

                threading.Thread(target=run_setup, daemon=True).start()
                return

            self.show_status_message(
                "Terminal opened - check terminal window for progress", "#22c55e"
            )
        except Exception as e:
            self.show_status_message(f"✗ Error: {str(e)}", "#ef4444")

    def show_status_message(self, message, color):
        """Show a temporary status message."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")
        self.status_label.show()

        # Hide after 2 seconds
        QTimer.singleShot(2000, self.status_label.hide)

    def show_error_status(self, error_message):
        """Show error message persistently."""
        self.status_label.setText(f"⚠ {error_message}")
        self.status_label.setStyleSheet("color: #ef4444;")
        self.status_label.show()
        # Don't auto-hide error messages

    def update_device_list(self, devices):
        """Update the device list display.

        Args:
            devices: List of tuples (device_serial, status, extra_info)
        """
        # Update state for incoming devices
        for device_info in devices:
            if len(device_info) == 2:
                serial, status = device_info
                extra_info = None
            else:
                serial, status, extra_info = device_info
            self.device_states[serial] = (status, extra_info)

        # Clear existing widgets
        while self.devices_layout.count():
            item = self.devices_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Rebuild from state
        if not self.device_states:
            no_devices = QLabel("No devices connected")
            no_devices.setFont(QFont("Arial", 12))
            no_devices.setStyleSheet("color: gray;")
            no_devices.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_devices.setMinimumHeight(60)
            self.devices_layout.addWidget(no_devices)
        else:
            for serial, (status, extra_info) in self.device_states.items():
                device_card = self.create_device_card(serial, status, extra_info)
                self.devices_layout.addWidget(device_card)

    def create_device_card(self, serial, status, extra_info=None):
        """Create a device card widget with adaptive dark mode styling.

        Args:
            serial: Device serial number
            status: Device status (e.g., 'device', 'tracing', 'available')
            extra_info: Optional extra information to display
        """
        # Card frame
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)

        # Adaptive styling based on system theme - reduced padding
        card.setStyleSheet(
            """
            QFrame {
                background-color: palette(base);
                border: 1px solid palette(mid);
                border-radius: 6px;
                padding: 6px;
            }
        """
        )

        # Card layout - reduced margins
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(8, 6, 8, 6)

        # Device info (no emoji, no shadow)
        device_label = QLabel(serial)
        device_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        device_label.setStyleSheet("color: palette(text);")
        card_layout.addWidget(device_label)

        # Extra info if provided (no shadow)
        if extra_info:
            extra_label = QLabel(str(extra_info))
            extra_label.setFont(QFont("Arial", 10))
            extra_label.setStyleSheet("color: palette(mid);")
            card_layout.addWidget(extra_label)

        # Spacer
        card_layout.addStretch()

        # Set up eadb button (device-specific, subtle)
        setup_button = QPushButton("Set up BPFTrace")
        setup_button.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        setup_button.setFixedSize(90, 24)
        setup_button.clicked.connect(lambda: self.setup_eadb_for_device(serial))
        setup_button.setStyleSheet(
            """
            QPushButton {
                background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: palette(light);
            }
            QPushButton:pressed {
                background-color: palette(midlight);
            }
        """
        )
        card_layout.addWidget(setup_button)

        # Status indicator with adaptive colors (no shadow)
        if status == "device" or status == "available":
            status_color = "#22c55e"  # Green
            status_text = "AVAILABLE"
        elif status == "tracing":
            status_color = "#3b82f6"  # Blue
            status_text = "TRACING"
        else:
            status_color = "#f59e0b"  # Orange
            status_text = status.upper()

        status_label = QLabel(status_text)
        status_label.setFont(QFont("Arial", 10))
        status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        card_layout.addWidget(status_label)

        return card

    def closeEvent(self, event):
        """Handle window close event."""
        print("Shutting down GUI...")
        self.shutdown_event.set()
        event.accept()


def run_gui(device_update_callback=None):
    """Entry point to run the GUI application.

    Args:
        device_update_callback: Function to register the GUI's device update signal.
                               Will be called with the emit function.
    """
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("PRISM Worker")
    app.setOrganizationName("PRISM Platform")

    # Set application style
    app.setStyle("Fusion")  # Modern cross-platform style

    # Create and show window
    window = PrismWorkerGUI(device_callback=device_update_callback)
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
