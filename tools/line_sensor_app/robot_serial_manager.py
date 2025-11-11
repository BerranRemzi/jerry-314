"""Serial communication manager for the line sensor application."""

import time
import threading
import serial
from serial.tools import list_ports
from typing import Optional, Callable, Dict, Any
import sys


class SerialManager:
    """Manages serial communication with the robot."""
    
    def __init__(self, baudrate: int = 115200, read_timeout_s: float = 0.1):
        self.baudrate = baudrate
        self.read_timeout_s = read_timeout_s
        self.serial_lock = threading.Lock()
        self.serial_connection: Optional[serial.Serial] = None
        self.stop_event = threading.Event()
        self.pending_reads: Dict[str, Any] = {}  # Track pending read commands
        self.read_lock = threading.Lock()
        self.status_callback: Optional[Callable[[str], None]] = None
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback function for status updates."""
        self.status_callback = callback
    
    def set_status_text(self, text: str) -> None:
        """Update status text through callback."""
        if self.status_callback:
            self.status_callback(text)
    
    def _readline(self) -> Optional[str]:
        """Read a line from serial connection with error handling."""
        try:
            with self.serial_lock:
                if self.serial_connection is None:
                    return None
                # Use a shorter timeout to avoid long blocks
                raw = self.serial_connection.readline()
            if not raw:
                return None
            return raw.decode(errors="ignore").strip()
        except Exception:
            # Likely a disconnect; drop the connection to trigger rescan
            try:
                with self.serial_lock:
                    if self.serial_connection is not None:
                        self.serial_connection.close()
                    self.serial_connection = None
            except Exception:
                pass
            return None
    
    def _ensure_open_port(self) -> bool:
        """Scan and open available serial port with valid data."""
        # If we already have an open port, validate it's alive
        with self.serial_lock:
            if self.serial_connection is not None and self.serial_connection.is_open:
                return True

        # Import regex patterns here to avoid circular imports
        from robot_data_regex import SENSOR_LINE_REGEX, LINE_POS_REGEX, PID_OUTPUT_REGEX
        
        # Scan available ports
        candidate_ports = [p.device for p in list_ports.comports()]
        if not candidate_ports:
            self.set_status_text("No serial ports found. Retrying…")
            return False

        for device in candidate_ports:
            if self.stop_event.is_set():
                return False

            try:
                candidate = serial.Serial(
                    port=device,
                    baudrate=self.baudrate,
                    timeout=self.read_timeout_s,
                )
                # Set DTR active when connecting
                candidate.dtr = False
            except Exception:
                continue

            # Give the device 500 ms, then try to read and validate data
            self.set_status_text(f"Opened {device}, waiting for data…")
            time.sleep(0.5)
            try:
                # Flush any stale data first
                candidate.reset_input_buffer()
                # Attempt a few reads quickly to find a valid frame
                valid = False
                for _ in range(8):
                    raw = candidate.readline()
                    if not raw:
                        continue
                    text = raw.decode(errors="ignore").strip()
                    if (SENSOR_LINE_REGEX.match(text) or 
                        LINE_POS_REGEX.match(text) or 
                        PID_OUTPUT_REGEX.match(text)):
                        valid = True
                        break
                if valid:
                    with self.serial_lock:
                        # Close previous connection if any
                        if self.serial_connection is not None:
                            try:
                                self.serial_connection.close()
                            except Exception:
                                pass
                        self.serial_connection = candidate
                    self.set_status_text(f"Connected: {device} @ {self.baudrate} bps")
                    return True
                else:
                    # Brief hint for debugging mismatched baud/data format
                    try:
                        sample = candidate.readline().decode(errors="ignore").strip()
                        sys.stderr.write(f"Probed {device}: no valid frame yet, sample='" + sample + "'\n")
                    except Exception:
                        pass
            except Exception:
                pass

            # Not valid; close and try next
            try:
                candidate.close()
            except Exception:
                pass

        self.set_status_text("No ports with valid data found. Retrying…")
        return False
    
    def send_command(self, command: str) -> None:
        """Send a command string over serial connection."""
        try:
            with self.serial_lock:
                if self.serial_connection is not None and self.serial_connection.is_open:
                    command_bytes = (command + "\n").encode('utf-8')
                    self.serial_connection.write(command_bytes)
        except Exception:
            pass  # Silently fail if serial is not available
    
    def close(self) -> None:
        """Close the serial connection."""
        self.stop_event.set()
        try:
            with self.serial_lock:
                if self.serial_connection is not None:
                    self.serial_connection.close()
        except Exception:
            pass