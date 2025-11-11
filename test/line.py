import re
import sys
import time
import threading
import json
from typing import List, Optional
from tkinter import filedialog

try:
    import serial  # pyserial
    from serial.tools import list_ports
except Exception as import_error:
    print("pyserial is required. Install with: pip install pyserial", file=sys.stderr)
    raise import_error

try:
    import tkinter as tk
except Exception as import_error:
    print("tkinter is required (usually included with Python on Windows).", file=sys.stderr)
    raise import_error

# Regex patterns for sensor data (S prefix), line position (L prefix), and PID output (O prefix)
# Format: S,968,973,... or L,3 or L,-3 (for negative values) or O,123 (PID output)
SENSOR_LINE_REGEX = re.compile(r"^S\s*,?\s*\d+(?:\s*,\s*\d+)*\s*$")
LINE_POS_REGEX = re.compile(r"^L\s*,?\s*-?\d+\s*$")
PID_OUTPUT_REGEX = re.compile(r"^O\s*,?\s*-?\d+\s*$")


class SerialLineGraphApp:
    def __init__(self, baudrate: int = 115200, read_timeout_s: float = 0.1):
        self.root = tk.Tk()
        self.root.title("Line Sensor Graph")
        self.root.geometry("1200x700")  # Initial window size: width x height

        self.status_text_var = tk.StringVar(value="Scanning serial ports…")
        self.port_label = tk.Label(self.root, textvariable=self.status_text_var, anchor="w")
        self.port_label.pack(fill="x", padx=8, pady=4)

        # Main container with left (graphs) and right (controls) frames
        main_container = tk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=4, pady=4)

        # Left frame for graphs
        left_frame = tk.Frame(main_container)
        left_frame.pack(side="left", fill="both", expand=True, padx=4)

        self.canvas_width = 800
        self.canvas_height = 300
        self.canvas = tk.Canvas(left_frame, width=self.canvas_width, height=self.canvas_height, bg="#111")
        self.canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # Plotter canvas for L and O values over time
        self.plotter_canvas_width = 800
        self.plotter_canvas_height = 200
        self.plotter_canvas = tk.Canvas(left_frame, width=self.plotter_canvas_width, height=self.plotter_canvas_height, bg="#111")
        self.plotter_canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # Right frame for controls
        self.control_frame = tk.Frame(main_container, width=300)
        self.control_frame.pack(side="right", fill="y", padx=4, pady=4)
        self.control_frame.pack_propagate(False)  # Maintain fixed width

        self.baudrate = baudrate
        self.read_timeout_s = read_timeout_s
        self.serial_lock = threading.Lock()
        self.serial_connection: Optional[serial.Serial] = None

        self.sensor_values: List[int] = []
        self.line_position: Optional[float] = None  # Position as fraction (0.0 to 1.0)
        self.line_position_raw: Optional[int] = None  # Raw line position (-127 to +127)
        self.max_value_seen: int = 1
        self.stop_event = threading.Event()

        # Time-series data for plotter (L and O values)
        self.plotter_data_lock = threading.Lock()
        self.plotter_data: List[tuple] = []  # List of (timestamp, L_value, O_value) tuples
        self.plotter_max_points = 500  # Maximum number of points to keep
        self.plotter_start_time: Optional[float] = None
        self.plotter_time_window = tk.DoubleVar(value=10.0)  # Time window in seconds
        self.plotter_time_window_max = tk.DoubleVar(value=60.0)  # Max time window in seconds
        
        # File management
        self.current_file_path: Optional[str] = None
        
        # Robot communication
        self.pending_reads: dict = {}  # Track pending read commands
        self.read_lock = threading.Lock()

        # PID and motor speed values
        self.pid_p_value = tk.DoubleVar(value=0.0)
        self.pid_i_value = tk.DoubleVar(value=0.0)
        self.pid_d_value = tk.DoubleVar(value=0.0)
        self.motor_speed_value = tk.DoubleVar(value=0.0)
        
        # Slider maximum values
        self.pid_p_max = tk.DoubleVar(value=100.0)
        self.pid_i_max = tk.DoubleVar(value=100.0)
        self.pid_d_max = tk.DoubleVar(value=100.0)
        self.motor_speed_max = tk.DoubleVar(value=255.0)
        
        # Logging checkboxes
        self.log_p_enabled = tk.BooleanVar(value=False)
        self.log_i_enabled = tk.BooleanVar(value=False)
        self.log_d_enabled = tk.BooleanVar(value=False)
        self.log_s_enabled = tk.BooleanVar(value=False)
        self.log_l_enabled = tk.BooleanVar(value=False)
        self.log_o_enabled = tk.BooleanVar(value=False)
        
        # Flag to prevent circular updates
        self._updating_control = False
        
        # Initialize control panel
        self._create_control_panel()

        self.reader_thread = threading.Thread(target=self._reader_loop, name="SerialReader", daemon=True)
        self.reader_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._schedule_gui_update()

    def _on_close(self) -> None:
        self.stop_event.set()
        try:
            with self.serial_lock:
                if self.serial_connection is not None:
                    self.serial_connection.close()
        except Exception:
            pass
        self.root.destroy()

    def _reader_loop(self) -> None:
        while not self.stop_event.is_set():
            if not self._ensure_open_port():
                # No valid port yet; wait a bit before rescanning
                time.sleep(0.5)
                continue

            line = self._readline()
            if line is None:
                # Possible disconnect or timeout; retry
                continue

            line_stripped = line.strip()
            
            # Parse sensor values (S prefix)
            # Format: S,968,973,853,894,962,980
            if SENSOR_LINE_REGEX.match(line_stripped):
                try:
                    text = line_stripped[2:].strip()  # Remove 'S,' prefix
                    numbers = [int(part.strip()) for part in text.split(',') if part.strip()]
                    if numbers:
                        self.sensor_values = numbers
                        current_max = max(numbers)
                        if current_max > self.max_value_seen:
                            self.max_value_seen = current_max
                except Exception:
                    continue
            
            # Parse line position (L prefix)
            # Format: L,3 (value from -127 to +127)
            elif LINE_POS_REGEX.match(line_stripped):
                try:
                    text = line_stripped[2:].strip()  # Remove 'L,' prefix
                    line_pos = int(text)
                    # Clamp to -127 to +127 range
                    self.line_position_raw = max(-127, min(127, line_pos))
                    # Normalize to 0.0-1.0 range based on number of sensors
                    if self.sensor_values:
                        num_sensors = len(self.sensor_values)
                        # Line position is typically the index (0 to num_sensors-1)
                        self.line_position = line_pos / max(num_sensors - 1, 1)
                    else:
                        # Fallback: assume line_pos is already normalized or use as-is
                        self.line_position = min(max(line_pos / 100.0, 0.0), 1.0)
                    
                    # Add to plotter data
                    self._add_plotter_data(l_value=line_pos, o_value=None)
                except Exception:
                    continue
            
            # Parse PID output (O prefix)
            # Format: O,123 (PID output value)
            elif PID_OUTPUT_REGEX.match(line_stripped):
                try:
                    text = line_stripped[2:].strip()  # Remove 'O,' prefix
                    pid_output = int(text)
                    # Add to plotter data
                    self._add_plotter_data(l_value=None, o_value=pid_output)
                except Exception:
                    continue
            
            # Parse parameter responses (e.g., "pid p 10.5", "motor speed 100")
            elif self._parse_parameter_response(line_stripped):
                # Parameter response was handled
                continue

    def _readline(self) -> Optional[str]:
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
        # If we already have an open port, validate it's alive
        with self.serial_lock:
            if self.serial_connection is not None and self.serial_connection.is_open:
                return True

        # Scan available ports
        candidate_ports = [p.device for p in list_ports.comports()]
        if not candidate_ports:
            self._set_status_text("No serial ports found. Retrying…")
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
            self._set_status_text(f"Opened {device}, waiting for data…")
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
                    self._set_status_text(f"Connected: {device} @ {self.baudrate} bps")
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

        self._set_status_text("No ports with valid data found. Retrying…")
        return False

    def _create_control_panel(self) -> None:
        """Create control panel with PID sliders/textboxes, max values, logging checkboxes, and motor controls"""
        # Create a scrollable container (using pack for simplicity)
        main_container = tk.Frame(self.control_frame)
        main_container.pack(fill="both", expand=True, padx=4, pady=4)
        
        # Section: Plotter Time Window
        plotter_section = tk.LabelFrame(main_container, text="Plotter", font=("Segoe UI", 9, "bold"))
        plotter_section.pack(fill="x", pady=4, padx=2)
        
        # Use grid layout for better alignment
        plotter_grid = tk.Frame(plotter_section)
        plotter_grid.pack(fill="x", padx=4, pady=4)
        
        # Row 0: Time Window value
        tk.Label(plotter_grid, text="Time Window (s):", font=("Segoe UI", 9), anchor="w").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        time_window_text = tk.Entry(plotter_grid, width=10)
        time_window_text.grid(row=0, column=1, padx=2, pady=2, sticky="w")
        time_window_text.insert(0, "10.0")
        time_window_text.bind("<Return>", lambda e: self._on_time_window_changed())
        time_window_text.bind("<FocusOut>", lambda e: self._on_time_window_changed())
        time_window_slider = tk.Scale(plotter_grid, from_=1.0, to=60.0, resolution=0.5, 
                                      orient="horizontal", variable=self.plotter_time_window, 
                                      command=lambda v: self._on_time_window_slider_changed(v), length=120)
        # Update slider to use max variable
        time_window_slider.config(to=self.plotter_time_window_max.get())
        time_window_slider.grid(row=0, column=2, padx=2, pady=2, sticky="ew")
        
        # Row 1: Max value
        tk.Label(plotter_grid, text="Max (s):", font=("Segoe UI", 9), anchor="w").grid(row=1, column=0, padx=2, pady=2, sticky="w")
        time_window_max_text = tk.Entry(plotter_grid, width=10)
        time_window_max_text.grid(row=1, column=1, padx=2, pady=2, sticky="w")
        time_window_max_text.insert(0, "60.0")
        time_window_max_text.bind("<Return>", lambda e: self._on_time_window_max_changed())
        time_window_max_text.bind("<FocusOut>", lambda e: self._on_time_window_max_changed())
        
        # Configure grid column weights
        plotter_grid.columnconfigure(0, weight=0)  # Labels - fixed width
        plotter_grid.columnconfigure(1, weight=0)  # Textboxes - fixed width
        plotter_grid.columnconfigure(2, weight=1)  # Slider - expandable
        
        # Section: PID Controls
        pid_section = tk.LabelFrame(main_container, text="PID Controls", font=("Segoe UI", 9, "bold"))
        pid_section.pack(fill="x", pady=4, padx=2)
        
        # Use grid layout for PID controls
        pid_grid = tk.Frame(pid_section)
        pid_grid.pack(fill="x", padx=4, pady=4)
        
        # Row 0: PID P
        tk.Label(pid_grid, text="P:", font=("Segoe UI", 9), anchor="w").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        pid_p_text = tk.Entry(pid_grid, width=10)
        pid_p_text.grid(row=0, column=1, padx=2, pady=2, sticky="w")
        pid_p_text.bind("<Return>", lambda e: self._on_pid_p_changed())
        pid_p_text.bind("<FocusOut>", lambda e: self._on_pid_p_changed())
        pid_p_slider = tk.Scale(pid_grid, from_=0.0, to=100.0, resolution=0.1, 
                                orient="horizontal", variable=self.pid_p_value, 
                                command=lambda v: self._on_pid_p_slider_changed(v), length=100)
        pid_p_slider.grid(row=0, column=2, padx=2, pady=2, sticky="ew")
        tk.Label(pid_grid, text="Max:", font=("Segoe UI", 8)).grid(row=0, column=3, padx=2, pady=2, sticky="w")
        pid_p_max_text = tk.Entry(pid_grid, width=10)
        pid_p_max_text.grid(row=0, column=4, padx=2, pady=2, sticky="w")
        pid_p_max_text.insert(0, "100.0")
        pid_p_max_text.bind("<Return>", lambda e: self._on_pid_p_max_changed())
        pid_p_max_text.bind("<FocusOut>", lambda e: self._on_pid_p_max_changed())
        
        # Row 1: PID I
        tk.Label(pid_grid, text="I:", font=("Segoe UI", 9), anchor="w").grid(row=1, column=0, padx=2, pady=2, sticky="w")
        pid_i_text = tk.Entry(pid_grid, width=10)
        pid_i_text.grid(row=1, column=1, padx=2, pady=2, sticky="w")
        pid_i_text.bind("<Return>", lambda e: self._on_pid_i_changed())
        pid_i_text.bind("<FocusOut>", lambda e: self._on_pid_i_changed())
        pid_i_slider = tk.Scale(pid_grid, from_=0.0, to=100.0, resolution=0.1, 
                                orient="horizontal", variable=self.pid_i_value, 
                                command=lambda v: self._on_pid_i_slider_changed(v), length=100)
        pid_i_slider.grid(row=1, column=2, padx=2, pady=2, sticky="ew")
        tk.Label(pid_grid, text="Max:", font=("Segoe UI", 8)).grid(row=1, column=3, padx=2, pady=2, sticky="w")
        pid_i_max_text = tk.Entry(pid_grid, width=10)
        pid_i_max_text.grid(row=1, column=4, padx=2, pady=2, sticky="w")
        pid_i_max_text.insert(0, "100.0")
        pid_i_max_text.bind("<Return>", lambda e: self._on_pid_i_max_changed())
        pid_i_max_text.bind("<FocusOut>", lambda e: self._on_pid_i_max_changed())
        
        # Row 2: PID D
        tk.Label(pid_grid, text="D:", font=("Segoe UI", 9), anchor="w").grid(row=2, column=0, padx=2, pady=2, sticky="w")
        pid_d_text = tk.Entry(pid_grid, width=10)
        pid_d_text.grid(row=2, column=1, padx=2, pady=2, sticky="w")
        pid_d_text.bind("<Return>", lambda e: self._on_pid_d_changed())
        pid_d_text.bind("<FocusOut>", lambda e: self._on_pid_d_changed())
        pid_d_slider = tk.Scale(pid_grid, from_=0.0, to=100.0, resolution=0.1, 
                                orient="horizontal", variable=self.pid_d_value, 
                                command=lambda v: self._on_pid_d_slider_changed(v), length=100)
        pid_d_slider.grid(row=2, column=2, padx=2, pady=2, sticky="ew")
        tk.Label(pid_grid, text="Max:", font=("Segoe UI", 8)).grid(row=2, column=3, padx=2, pady=2, sticky="w")
        pid_d_max_text = tk.Entry(pid_grid, width=10)
        pid_d_max_text.grid(row=2, column=4, padx=2, pady=2, sticky="w")
        pid_d_max_text.insert(0, "100.0")
        pid_d_max_text.bind("<Return>", lambda e: self._on_pid_d_max_changed())
        pid_d_max_text.bind("<FocusOut>", lambda e: self._on_pid_d_max_changed())
        
        # Configure PID grid column weights
        pid_grid.columnconfigure(0, weight=0)  # Labels - fixed width
        pid_grid.columnconfigure(1, weight=0)  # Textboxes - fixed width
        pid_grid.columnconfigure(2, weight=1)   # Sliders - expandable
        pid_grid.columnconfigure(3, weight=0)  # Max labels - fixed width
        pid_grid.columnconfigure(4, weight=0)  # Max textboxes - fixed width
        
        # Section: Motor Control
        motor_section = tk.LabelFrame(main_container, text="Motor Control", font=("Segoe UI", 9, "bold"))
        motor_section.pack(fill="x", pady=4, padx=2)
        
        # Use grid layout for motor controls
        motor_grid = tk.Frame(motor_section)
        motor_grid.pack(fill="x", padx=4, pady=4)
        
        # Row 0: Motor speed
        tk.Label(motor_grid, text="Speed:", font=("Segoe UI", 9), anchor="w").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        motor_text = tk.Entry(motor_grid, width=10)
        motor_text.grid(row=0, column=1, padx=2, pady=2, sticky="w")
        motor_text.bind("<Return>", lambda e: self._on_motor_speed_changed())
        motor_text.bind("<FocusOut>", lambda e: self._on_motor_speed_changed())
        motor_slider = tk.Scale(motor_grid, from_=0.0, to=255.0, resolution=1.0, 
                                orient="horizontal", variable=self.motor_speed_value, 
                                command=lambda v: self._on_motor_speed_slider_changed(v), length=100)
        motor_slider.grid(row=0, column=2, padx=2, pady=2, sticky="ew")
        tk.Label(motor_grid, text="Max:", font=("Segoe UI", 8)).grid(row=0, column=3, padx=2, pady=2, sticky="w")
        motor_max_text = tk.Entry(motor_grid, width=10)
        motor_max_text.grid(row=0, column=4, padx=2, pady=2, sticky="w")
        motor_max_text.insert(0, "255.0")
        motor_max_text.bind("<Return>", lambda e: self._on_motor_speed_max_changed())
        motor_max_text.bind("<FocusOut>", lambda e: self._on_motor_speed_max_changed())
        
        # Row 1: Motor buttons
        motor_start_btn = tk.Button(motor_grid, text="Start", command=self._on_motor_start, 
                                    font=("Segoe UI", 9))
        motor_start_btn.grid(row=1, column=0, columnspan=2, padx=2, pady=2, sticky="ew")
        motor_stop_btn = tk.Button(motor_grid, text="Stop", command=self._on_motor_stop, 
                                   font=("Segoe UI", 9))
        motor_stop_btn.grid(row=1, column=2, columnspan=3, padx=2, pady=2, sticky="ew")
        
        # Configure motor grid column weights
        motor_grid.columnconfigure(0, weight=0)  # Labels - fixed width
        motor_grid.columnconfigure(1, weight=0)  # Textboxes - fixed width
        motor_grid.columnconfigure(2, weight=1)  # Sliders - expandable
        motor_grid.columnconfigure(3, weight=0)  # Max labels - fixed width
        motor_grid.columnconfigure(4, weight=0)  # Max textboxes - fixed width
        
        # Section: Logging
        logging_section = tk.LabelFrame(main_container, text="Logging", font=("Segoe UI", 9, "bold"))
        logging_section.pack(fill="x", pady=4, padx=2)
        
        # Use grid layout for logging checkboxes
        logging_grid = tk.Frame(logging_section)
        logging_grid.pack(fill="x", padx=4, pady=4)
        
        # Row 0: First row of checkboxes
        log_p_check = tk.Checkbutton(logging_grid, text="P", variable=self.log_p_enabled, 
                                     command=lambda: self._on_log_changed("p"), font=("Segoe UI", 9))
        log_p_check.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        log_i_check = tk.Checkbutton(logging_grid, text="I", variable=self.log_i_enabled, 
                                     command=lambda: self._on_log_changed("i"), font=("Segoe UI", 9))
        log_i_check.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        log_d_check = tk.Checkbutton(logging_grid, text="D", variable=self.log_d_enabled, 
                                     command=lambda: self._on_log_changed("d"), font=("Segoe UI", 9))
        log_d_check.grid(row=0, column=2, padx=2, pady=2, sticky="ew")
        
        # Row 1: Second row of checkboxes
        log_s_check = tk.Checkbutton(logging_grid, text="S", variable=self.log_s_enabled, 
                                     command=lambda: self._on_log_changed("s"), font=("Segoe UI", 9))
        log_s_check.grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        log_l_check = tk.Checkbutton(logging_grid, text="L", variable=self.log_l_enabled, 
                                     command=lambda: self._on_log_changed("l"), font=("Segoe UI", 9))
        log_l_check.grid(row=1, column=1, padx=2, pady=2, sticky="ew")
        log_o_check = tk.Checkbutton(logging_grid, text="O", variable=self.log_o_enabled, 
                                     command=lambda: self._on_log_changed("o"), font=("Segoe UI", 9))
        log_o_check.grid(row=1, column=2, padx=2, pady=2, sticky="ew")
        
        # Configure logging grid column weights
        logging_grid.columnconfigure(0, weight=1)  # Equal width columns
        logging_grid.columnconfigure(1, weight=1)
        logging_grid.columnconfigure(2, weight=1)
        
        # Section: File Operations
        file_section = tk.LabelFrame(main_container, text="File Operations", font=("Segoe UI", 9, "bold"))
        file_section.pack(fill="x", pady=4, padx=2)
        
        # Use grid layout for file buttons
        file_grid = tk.Frame(file_section)
        file_grid.pack(fill="x", padx=4, pady=4)
        
        open_btn = tk.Button(file_grid, text="Open", command=self._on_file_open, 
                            font=("Segoe UI", 9))
        open_btn.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        
        save_btn = tk.Button(file_grid, text="Save", command=self._on_file_save, 
                             font=("Segoe UI", 9))
        save_btn.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        
        save_as_btn = tk.Button(file_grid, text="Save As", command=self._on_file_save_as, 
                                font=("Segoe UI", 9))
        save_as_btn.grid(row=0, column=2, padx=2, pady=2, sticky="ew")
        
        # Configure file grid column weights
        file_grid.columnconfigure(0, weight=1)  # Equal width columns
        file_grid.columnconfigure(1, weight=1)
        file_grid.columnconfigure(2, weight=1)
        
        # Section: Robot Communication
        robot_section = tk.LabelFrame(main_container, text="Robot Communication", font=("Segoe UI", 9, "bold"))
        robot_section.pack(fill="x", pady=4, padx=2)
        
        # Use grid layout for robot buttons
        robot_grid = tk.Frame(robot_section)
        robot_grid.pack(fill="x", padx=4, pady=4)
        
        read_btn = tk.Button(robot_grid, text="Read", command=self._on_robot_read, 
                            font=("Segoe UI", 9))
        read_btn.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        
        write_btn = tk.Button(robot_grid, text="Write", command=self._on_robot_write, 
                             font=("Segoe UI", 9))
        write_btn.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        
        # Configure robot grid column weights
        robot_grid.columnconfigure(0, weight=1)  # Equal width columns
        robot_grid.columnconfigure(1, weight=1)
        
        # Store references for later use
        self.pid_p_text = pid_p_text
        self.pid_i_text = pid_i_text
        self.pid_d_text = pid_d_text
        self.motor_text = motor_text
        self.pid_p_slider = pid_p_slider
        self.pid_i_slider = pid_i_slider
        self.pid_d_slider = pid_d_slider
        self.motor_slider = motor_slider
        self.pid_p_max_text = pid_p_max_text
        self.pid_i_max_text = pid_i_max_text
        self.pid_d_max_text = pid_d_max_text
        self.motor_max_text = motor_max_text
        self.time_window_text = time_window_text
        self.time_window_slider = time_window_slider
        self.time_window_max_text = time_window_max_text
        
        # Initialize textboxes with current values
        self._sync_textboxes()

    def _sync_textboxes(self) -> None:
        """Sync textboxes with current variable values"""
        if not self._updating_control:
            self._updating_control = True
            self.pid_p_text.delete(0, tk.END)
            self.pid_p_text.insert(0, str(self.pid_p_value.get()))
            self.pid_i_text.delete(0, tk.END)
            self.pid_i_text.insert(0, str(self.pid_i_value.get()))
            self.pid_d_text.delete(0, tk.END)
            self.pid_d_text.insert(0, str(self.pid_d_value.get()))
            self.motor_text.delete(0, tk.END)
            self.motor_text.insert(0, str(int(self.motor_speed_value.get())))
            self._updating_control = False

    def _send_serial_command(self, command: str) -> None:
        """Send a command string over serial connection"""
        try:
            with self.serial_lock:
                if self.serial_connection is not None and self.serial_connection.is_open:
                    command_bytes = (command + "\n").encode('utf-8')
                    self.serial_connection.write(command_bytes)
        except Exception:
            pass  # Silently fail if serial is not available

    def _on_pid_p_changed(self) -> None:
        """Handle PID P value change from textbox"""
        if self._updating_control:
            return
        try:
            value = float(self.pid_p_text.get())
            self._updating_control = True
            self.pid_p_value.set(value)
            self._updating_control = False
            self._send_serial_command(f"pid p {value}")
        except ValueError:
            # Invalid value, restore from variable
            self._updating_control = True
            self.pid_p_text.delete(0, tk.END)
            self.pid_p_text.insert(0, str(self.pid_p_value.get()))
            self._updating_control = False

    def _on_pid_p_slider_changed(self, value: str) -> None:
        """Handle PID P value change from slider"""
        if self._updating_control:
            return
        try:
            float_value = float(value)
            self._updating_control = True
            self.pid_p_text.delete(0, tk.END)
            self.pid_p_text.insert(0, value)
            self._updating_control = False
            self._send_serial_command(f"pid p {float_value}")
        except ValueError:
            pass

    def _on_pid_i_changed(self) -> None:
        """Handle PID I value change from textbox"""
        if self._updating_control:
            return
        try:
            value = float(self.pid_i_text.get())
            self._updating_control = True
            self.pid_i_value.set(value)
            self._updating_control = False
            self._send_serial_command(f"pid i {value}")
        except ValueError:
            # Invalid value, restore from variable
            self._updating_control = True
            self.pid_i_text.delete(0, tk.END)
            self.pid_i_text.insert(0, str(self.pid_i_value.get()))
            self._updating_control = False

    def _on_pid_i_slider_changed(self, value: str) -> None:
        """Handle PID I value change from slider"""
        if self._updating_control:
            return
        try:
            float_value = float(value)
            self._updating_control = True
            self.pid_i_text.delete(0, tk.END)
            self.pid_i_text.insert(0, value)
            self._updating_control = False
            self._send_serial_command(f"pid i {float_value}")
        except ValueError:
            pass

    def _on_pid_d_changed(self) -> None:
        """Handle PID D value change from textbox"""
        if self._updating_control:
            return
        try:
            value = float(self.pid_d_text.get())
            self._updating_control = True
            self.pid_d_value.set(value)
            self._updating_control = False
            self._send_serial_command(f"pid d {value}")
        except ValueError:
            # Invalid value, restore from variable
            self._updating_control = True
            self.pid_d_text.delete(0, tk.END)
            self.pid_d_text.insert(0, str(self.pid_d_value.get()))
            self._updating_control = False

    def _on_pid_d_slider_changed(self, value: str) -> None:
        """Handle PID D value change from slider"""
        if self._updating_control:
            return
        try:
            float_value = float(value)
            self._updating_control = True
            self.pid_d_text.delete(0, tk.END)
            self.pid_d_text.insert(0, value)
            self._updating_control = False
            self._send_serial_command(f"pid d {float_value}")
        except ValueError:
            pass

    def _on_motor_speed_changed(self) -> None:
        """Handle motor speed value change from textbox"""
        if self._updating_control:
            return
        try:
            value = float(self.motor_text.get())
            self._updating_control = True
            self.motor_speed_value.set(value)
            self._updating_control = False
            self._send_serial_command(f"motor speed {value}")
        except ValueError:
            # Invalid value, restore from variable
            self._updating_control = True
            self.motor_text.delete(0, tk.END)
            self.motor_text.insert(0, str(self.motor_speed_value.get()))
            self._updating_control = False

    def _on_motor_speed_slider_changed(self, value: str) -> None:
        """Handle motor speed value change from slider"""
        if self._updating_control:
            return
        try:
            int_value = int(float(value))
            self._updating_control = True
            self.motor_text.delete(0, tk.END)
            self.motor_text.insert(0, str(int_value))
            self._updating_control = False
            self._send_serial_command(f"motor speed {int_value}")
        except ValueError:
            pass

    def _on_pid_p_max_changed(self) -> None:
        """Handle PID P max value change"""
        try:
            max_val = float(self.pid_p_max_text.get())
            if max_val > 0:
                self.pid_p_max.set(max_val)
                self.pid_p_slider.config(to=max_val)
                # Clamp current value if needed
                if self.pid_p_value.get() > max_val:
                    self.pid_p_value.set(max_val)
                    self.pid_p_text.delete(0, tk.END)
                    self.pid_p_text.insert(0, str(max_val))
        except ValueError:
            # Invalid value, restore
            self.pid_p_max_text.delete(0, tk.END)
            self.pid_p_max_text.insert(0, str(self.pid_p_max.get()))

    def _on_pid_i_max_changed(self) -> None:
        """Handle PID I max value change"""
        try:
            max_val = float(self.pid_i_max_text.get())
            if max_val > 0:
                self.pid_i_max.set(max_val)
                self.pid_i_slider.config(to=max_val)
                # Clamp current value if needed
                if self.pid_i_value.get() > max_val:
                    self.pid_i_value.set(max_val)
                    self.pid_i_text.delete(0, tk.END)
                    self.pid_i_text.insert(0, str(max_val))
        except ValueError:
            # Invalid value, restore
            self.pid_i_max_text.delete(0, tk.END)
            self.pid_i_max_text.insert(0, str(self.pid_i_max.get()))

    def _on_pid_d_max_changed(self) -> None:
        """Handle PID D max value change"""
        try:
            max_val = float(self.pid_d_max_text.get())
            if max_val > 0:
                self.pid_d_max.set(max_val)
                self.pid_d_slider.config(to=max_val)
                # Clamp current value if needed
                if self.pid_d_value.get() > max_val:
                    self.pid_d_value.set(max_val)
                    self.pid_d_text.delete(0, tk.END)
                    self.pid_d_text.insert(0, str(max_val))
        except ValueError:
            # Invalid value, restore
            self.pid_d_max_text.delete(0, tk.END)
            self.pid_d_max_text.insert(0, str(self.pid_d_max.get()))

    def _on_motor_speed_max_changed(self) -> None:
        """Handle motor speed max value change"""
        try:
            max_val = float(self.motor_max_text.get())
            if max_val > 0:
                self.motor_speed_max.set(max_val)
                self.motor_slider.config(to=max_val)
                # Clamp current value if needed
                if self.motor_speed_value.get() > max_val:
                    self.motor_speed_value.set(max_val)
                    self.motor_text.delete(0, tk.END)
                    self.motor_text.insert(0, str(int(max_val)))
        except ValueError:
            # Invalid value, restore
            self.motor_max_text.delete(0, tk.END)
            self.motor_max_text.insert(0, str(self.motor_speed_max.get()))

    def _on_log_changed(self, log_type: str) -> None:
        """Handle logging checkbox change"""
        enabled = False
        if log_type == "p":
            enabled = self.log_p_enabled.get()
        elif log_type == "i":
            enabled = self.log_i_enabled.get()
        elif log_type == "d":
            enabled = self.log_d_enabled.get()
        elif log_type == "s":
            enabled = self.log_s_enabled.get()
        elif log_type == "l":
            enabled = self.log_l_enabled.get()
        elif log_type == "o":
            enabled = self.log_o_enabled.get()
        
        state = "on" if enabled else "off"
        self._send_serial_command(f"log {log_type} {state}")

    def _on_motor_start(self) -> None:
        """Handle motor start button click"""
        self._send_serial_command("motor start")

    def _on_motor_stop(self) -> None:
        """Handle motor stop button click"""
        self._send_serial_command("motor stop")

    def _on_time_window_changed(self) -> None:
        """Handle time window value change from textbox"""
        try:
            value = float(self.time_window_text.get())
            if value > 0:
                self._updating_control = True
                self.plotter_time_window.set(value)
                self._updating_control = False
        except ValueError:
            # Invalid value, restore from variable
            self._updating_control = True
            self.time_window_text.delete(0, tk.END)
            self.time_window_text.insert(0, str(self.plotter_time_window.get()))
            self._updating_control = False

    def _on_time_window_slider_changed(self, value: str) -> None:
        """Handle time window value change from slider"""
        if self._updating_control:
            return
        try:
            float_value = float(value)
            self._updating_control = True
            self.time_window_text.delete(0, tk.END)
            self.time_window_text.insert(0, value)
            self._updating_control = False
        except ValueError:
            pass

    def _on_time_window_max_changed(self) -> None:
        """Handle time window max value change"""
        try:
            max_val = float(self.time_window_max_text.get())
            if max_val > 0:
                self.plotter_time_window_max.set(max_val)
                self.time_window_slider.config(to=max_val)
                # Clamp current value if needed
                if self.plotter_time_window.get() > max_val:
                    self.plotter_time_window.set(max_val)
                    self.time_window_text.delete(0, tk.END)
                    self.time_window_text.insert(0, str(max_val))
        except ValueError:
            # Invalid value, restore
            self.time_window_max_text.delete(0, tk.END)
            self.time_window_max_text.insert(0, str(self.plotter_time_window_max.get()))

    def _get_all_parameters(self) -> dict:
        """Get all current parameters as a dictionary"""
        return {
            "pid_p": self.pid_p_value.get(),
            "pid_i": self.pid_i_value.get(),
            "pid_d": self.pid_d_value.get(),
            "motor_speed": self.motor_speed_value.get(),
            "pid_p_max": self.pid_p_max.get(),
            "pid_i_max": self.pid_i_max.get(),
            "pid_d_max": self.pid_d_max.get(),
            "motor_speed_max": self.motor_speed_max.get(),
            "time_window": self.plotter_time_window.get(),
            "time_window_max": self.plotter_time_window_max.get(),
            "log_p": self.log_p_enabled.get(),
            "log_i": self.log_i_enabled.get(),
            "log_d": self.log_d_enabled.get(),
            "log_s": self.log_s_enabled.get(),
            "log_l": self.log_l_enabled.get(),
            "log_o": self.log_o_enabled.get(),
        }

    def _set_all_parameters(self, params: dict) -> None:
        """Set all parameters from a dictionary"""
        self._updating_control = True
        try:
            if "pid_p" in params:
                self.pid_p_value.set(params["pid_p"])
                self.pid_p_text.delete(0, tk.END)
                self.pid_p_text.insert(0, str(params["pid_p"]))
            if "pid_i" in params:
                self.pid_i_value.set(params["pid_i"])
                self.pid_i_text.delete(0, tk.END)
                self.pid_i_text.insert(0, str(params["pid_i"]))
            if "pid_d" in params:
                self.pid_d_value.set(params["pid_d"])
                self.pid_d_text.delete(0, tk.END)
                self.pid_d_text.insert(0, str(params["pid_d"]))
            if "motor_speed" in params:
                self.motor_speed_value.set(params["motor_speed"])
                self.motor_text.delete(0, tk.END)
                self.motor_text.insert(0, str(int(params["motor_speed"])))
            
            if "pid_p_max" in params:
                self.pid_p_max.set(params["pid_p_max"])
                self.pid_p_max_text.delete(0, tk.END)
                self.pid_p_max_text.insert(0, str(params["pid_p_max"]))
                self.pid_p_slider.config(to=params["pid_p_max"])
            if "pid_i_max" in params:
                self.pid_i_max.set(params["pid_i_max"])
                self.pid_i_max_text.delete(0, tk.END)
                self.pid_i_max_text.insert(0, str(params["pid_i_max"]))
                self.pid_i_slider.config(to=params["pid_i_max"])
            if "pid_d_max" in params:
                self.pid_d_max.set(params["pid_d_max"])
                self.pid_d_max_text.delete(0, tk.END)
                self.pid_d_max_text.insert(0, str(params["pid_d_max"]))
                self.pid_d_slider.config(to=params["pid_d_max"])
            if "motor_speed_max" in params:
                self.motor_speed_max.set(params["motor_speed_max"])
                self.motor_max_text.delete(0, tk.END)
                self.motor_max_text.insert(0, str(params["motor_speed_max"]))
                self.motor_slider.config(to=params["motor_speed_max"])
            
            if "time_window" in params:
                self.plotter_time_window.set(params["time_window"])
                self.time_window_text.delete(0, tk.END)
                self.time_window_text.insert(0, str(params["time_window"]))
            if "time_window_max" in params:
                self.plotter_time_window_max.set(params["time_window_max"])
                self.time_window_max_text.delete(0, tk.END)
                self.time_window_max_text.insert(0, str(params["time_window_max"]))
                self.time_window_slider.config(to=params["time_window_max"])
            
            if "log_p" in params:
                self.log_p_enabled.set(params["log_p"])
            if "log_i" in params:
                self.log_i_enabled.set(params["log_i"])
            if "log_d" in params:
                self.log_d_enabled.set(params["log_d"])
            if "log_s" in params:
                self.log_s_enabled.set(params["log_s"])
            if "log_l" in params:
                self.log_l_enabled.set(params["log_l"])
            if "log_o" in params:
                self.log_o_enabled.set(params["log_o"])
        finally:
            self._updating_control = False

    def _on_file_open(self) -> None:
        """Handle file open button click"""
        file_path = filedialog.askopenfilename(
            title="Open Parameters",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    params = json.load(f)
                self._set_all_parameters(params)
                self.current_file_path = file_path
                self._set_status_text(f"Loaded parameters from {file_path}")
            except Exception as e:
                self._set_status_text(f"Error loading file: {str(e)}")

    def _on_file_save(self) -> None:
        """Handle file save button click"""
        if self.current_file_path:
            try:
                params = self._get_all_parameters()
                with open(self.current_file_path, 'w') as f:
                    json.dump(params, f, indent=2)
                self._set_status_text(f"Saved parameters to {self.current_file_path}")
            except Exception as e:
                self._set_status_text(f"Error saving file: {str(e)}")
        else:
            # No current file, use Save As
            self._on_file_save_as()

    def _on_file_save_as(self) -> None:
        """Handle file save as button click"""
        file_path = filedialog.asksaveasfilename(
            title="Save Parameters As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            try:
                params = self._get_all_parameters()
                with open(file_path, 'w') as f:
                    json.dump(params, f, indent=2)
                self.current_file_path = file_path
                self._set_status_text(f"Saved parameters to {file_path}")
            except Exception as e:
                self._set_status_text(f"Error saving file: {str(e)}")

    def _parse_parameter_response(self, line: str) -> bool:
        """Parse parameter response from robot (e.g., 'pid p 10.5', 'motor speed 100')
        Returns True if the line was a parameter response"""
        try:
            parts = line.strip().split()
            if len(parts) < 3:
                return False
            
            # Parse "pid p 10.5" format
            if parts[0] == "pid" and len(parts) == 3:
                param_type = parts[1].lower()
                value = float(parts[2])
                
                self._updating_control = True
                if param_type == "p":
                    self.pid_p_value.set(value)
                    self.pid_p_text.delete(0, tk.END)
                    self.pid_p_text.insert(0, str(value))
                elif param_type == "i":
                    self.pid_i_value.set(value)
                    self.pid_i_text.delete(0, tk.END)
                    self.pid_i_text.insert(0, str(value))
                elif param_type == "d":
                    self.pid_d_value.set(value)
                    self.pid_d_text.delete(0, tk.END)
                    self.pid_d_text.insert(0, str(value))
                self._updating_control = False
                return True
            
            # Parse "motor speed 100" format
            elif parts[0] == "motor" and parts[1] == "speed" and len(parts) == 3:
                value = float(parts[2])
                self._updating_control = True
                self.motor_speed_value.set(value)
                self.motor_text.delete(0, tk.END)
                self.motor_text.insert(0, str(int(value)))
                self._updating_control = False
                return True
        except (ValueError, IndexError):
            pass
        return False

    def _on_robot_read(self) -> None:
        """Read all parameters from robot (non-blocking)"""
        def read_thread():
            self._set_status_text("Reading parameters from robot...")
            
            # Read PID parameters
            self._send_serial_command("pid p ?")
            time.sleep(0.1)
            self._send_serial_command("pid i ?")
            time.sleep(0.1)
            self._send_serial_command("pid d ?")
            time.sleep(0.1)
            
            # Read motor speed
            self._send_serial_command("motor speed ?")
            time.sleep(0.1)
            
            self._set_status_text("Reading parameters... (check responses)")
        
        thread = threading.Thread(target=read_thread, daemon=True)
        thread.start()

    def _on_robot_write(self) -> None:
        """Write all current parameters to robot (non-blocking)"""
        def write_thread():
            self._set_status_text("Writing parameters to robot...")
            
            # Write PID parameters
            self._send_serial_command(f"pid p {self.pid_p_value.get()}")
            time.sleep(0.1)
            self._send_serial_command(f"pid i {self.pid_i_value.get()}")
            time.sleep(0.1)
            self._send_serial_command(f"pid d {self.pid_d_value.get()}")
            time.sleep(0.1)
            
            # Write motor speed
            self._send_serial_command(f"motor speed {int(self.motor_speed_value.get())}")
            time.sleep(0.1)
            
            # Write logging states
            if self.log_p_enabled.get():
                self._send_serial_command("log p on")
            else:
                self._send_serial_command("log p off")
            time.sleep(0.05)
            
            if self.log_i_enabled.get():
                self._send_serial_command("log i on")
            else:
                self._send_serial_command("log i off")
            time.sleep(0.05)
            
            if self.log_d_enabled.get():
                self._send_serial_command("log d on")
            else:
                self._send_serial_command("log d off")
            time.sleep(0.05)
            
            if self.log_s_enabled.get():
                self._send_serial_command("log s on")
            else:
                self._send_serial_command("log s off")
            time.sleep(0.05)
            
            if self.log_l_enabled.get():
                self._send_serial_command("log l on")
            else:
                self._send_serial_command("log l off")
            time.sleep(0.05)
            
            if self.log_o_enabled.get():
                self._send_serial_command("log o on")
            else:
                self._send_serial_command("log o off")
            
            self._set_status_text("Parameters written to robot")
        
        thread = threading.Thread(target=write_thread, daemon=True)
        thread.start()

    def _set_status_text(self, text: str) -> None:
        def update() -> None:
            self.status_text_var.set(text)
        try:
            self.root.after(0, update)
        except Exception:
            # In case the window is already closing
            pass

    def _add_plotter_data(self, l_value: Optional[int], o_value: Optional[int]) -> None:
        """Add L or O value to plotter time-series data"""
        current_time = time.time()
        if self.plotter_start_time is None:
            self.plotter_start_time = current_time
        
        with self.plotter_data_lock:
            relative_time = current_time - self.plotter_start_time
            
            # If we have recent data (within 10ms), update the last entry
            # Otherwise, create a new entry
            if (self.plotter_data and 
                relative_time - self.plotter_data[-1][0] < 0.01):
                # Update last entry (very recent, likely same sample)
                last_entry = list(self.plotter_data[-1])
                if l_value is not None:
                    last_entry[1] = l_value
                if o_value is not None:
                    last_entry[2] = o_value
                self.plotter_data[-1] = tuple(last_entry)
            else:
                # Add new entry
                self.plotter_data.append((relative_time, l_value, o_value))
                
                # Limit the number of points (rolling window) - more efficient than time-based filtering
                # Time-based filtering will be done in the drawing function
                if len(self.plotter_data) > self.plotter_max_points:
                    removed_time = self.plotter_data[0][0]
                    self.plotter_data.pop(0)
                    # Adjust start time to keep relative times correct
                    if len(self.plotter_data) > 0:
                        self.plotter_start_time = current_time - (relative_time - removed_time)

    def _schedule_gui_update(self) -> None:
        try:
            self._draw_graph()
            self._draw_plotter()
        except Exception:
            # Prevent crashes from breaking the update loop
            pass
        # Update ~15 FPS (slightly slower to reduce CPU usage)
        self.root.after(66, self._schedule_gui_update)

    def _draw_graph(self) -> None:
        self.canvas.delete("all")

        values = self.sensor_values
        if not values:
            self._draw_placeholder()
            return

        width = self.canvas.winfo_width() or self.canvas_width
        height = self.canvas.winfo_height() or self.canvas_height

        num_points = len(values)
        max_value = max(self.max_value_seen, 1)

        margin = 40
        bar_area_height = 50  # Space for horizontal position bar
        usable_width = max(width - margin * 2, 10)
        usable_height = max(height - margin * 2 - bar_area_height, 10)
        graph_bottom_y = height - margin - bar_area_height

        # Calculate x positions (evenly spaced across width)
        x_coords = []
        y_coords = []
        for index in range(num_points):
            x = margin + (index / max(num_points - 1, 1)) * usable_width
            x_coords.append(x)
            
            normalized = min(max(values[index] / max_value, 0.0), 1.0)
            # Invert Y (higher values at top, lower at bottom)
            y = graph_bottom_y - (normalized * usable_height)
            y_coords.append(y)

        # Draw axes (adjusted for bar area)
        self.canvas.create_line(margin, graph_bottom_y, width - margin, graph_bottom_y, fill="#444", width=1)
        self.canvas.create_line(margin, margin, margin, graph_bottom_y, fill="#444", width=1)

        # Draw spline curve connecting all points
        if len(x_coords) > 1:
            spline_points = self._generate_spline_points(x_coords, y_coords, values, max_value)
            self._draw_spline_curve(spline_points)

        # Draw data points as circles
        for i, (x, y, value) in enumerate(zip(x_coords, y_coords, values)):
            normalized = min(max(value / max_value, 0.0), 1.0)
            color = self._value_to_color(normalized)
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline="")
            
            # Value labels above points
            label_y = max(y - 12, margin + 8)
            self.canvas.create_text(
                x,
                label_y,
                text=str(value),
                fill="#ddd",
                font=("Segoe UI", 8),
            )

        # Draw vertical line for detected line position
        if self.line_position is not None:
            line_x = margin + (self.line_position * usable_width)
            # Draw vertical line from top to bottom of graph (not including bar area)
            self.canvas.create_line(
                line_x, margin, 
                line_x, graph_bottom_y,
                fill="#ffff00",  # Yellow for visibility
                width=2,
                dash=(4, 4)  # Dashed line
            )
            # Label for line position
            self.canvas.create_text(
                line_x,
                margin - 12,
                text="Line",
                fill="#ffff00",
                font=("Segoe UI", 9, "bold"),
                anchor="s"
            )

        # Draw horizontal bar indicator for line position (-127 to +127)
        self._draw_line_position_bar(width, height, margin)

    def _draw_line_position_bar(self, width: int, height: int, margin: int) -> None:
        """Draw horizontal bar indicator showing line position from -127 to +127"""
        bar_height = 30
        bar_y = height - margin - bar_height - 5
        
        # Bar area
        bar_x_left = margin
        bar_x_right = width - margin
        bar_center_x = (bar_x_left + bar_x_right) / 2
        bar_width = bar_x_right - bar_x_left
        
        # Draw background bar
        self.canvas.create_rectangle(
            bar_x_left, bar_y,
            bar_x_right, bar_y + bar_height,
            fill="#222", outline="#555", width=1
        )
        
        # Draw center line (0 position)
        self.canvas.create_line(
            bar_center_x, bar_y,
            bar_center_x, bar_y + bar_height,
            fill="#666", width=1
        )
        
        # Draw scale labels
        self.canvas.create_text(
            bar_x_left, bar_y + bar_height / 2,
            text="-127", fill="#aaa", font=("Segoe UI", 9), anchor="e"
        )
        self.canvas.create_text(
            bar_center_x, bar_y - 5,
            text="0", fill="#aaa", font=("Segoe UI", 9), anchor="s"
        )
        self.canvas.create_text(
            bar_x_right, bar_y + bar_height / 2,
            text="+127", fill="#aaa", font=("Segoe UI", 9), anchor="w"
        )
        
        # Draw position indicator if we have a value
        if self.line_position_raw is not None:
            # Calculate position: -127 is left, 0 is center, +127 is right
            pos_normalized = (self.line_position_raw + 127) / 254.0  # 0.0 to 1.0
            indicator_x = bar_x_left + (pos_normalized * bar_width)
            
            # Draw indicator bar (filled portion from center to position)
            if self.line_position_raw < 0:
                # Left of center - fill from position to center
                fill_left = indicator_x
                fill_right = bar_center_x
                fill_color = "#ff6666"  # Red for left
            elif self.line_position_raw > 0:
                # Right of center - fill from center to position
                fill_left = bar_center_x
                fill_right = indicator_x
                fill_color = "#66ff66"  # Green for right
            else:
                # At center
                fill_left = bar_center_x - 1
                fill_right = bar_center_x + 1
                fill_color = "#ffff66"  # Yellow for center
            
            self.canvas.create_rectangle(
                fill_left, bar_y + 5,
                fill_right, bar_y + bar_height - 5,
                fill=fill_color, outline=""
            )
            
            # Draw position marker line
            self.canvas.create_line(
                indicator_x, bar_y,
                indicator_x, bar_y + bar_height,
                fill="#ffff00", width=2
            )
            
            # Draw value label
            self.canvas.create_text(
                indicator_x, bar_y + bar_height + 12,
                text=str(self.line_position_raw),
                fill="#ffff00", font=("Segoe UI", 10, "bold"),
                anchor="n"
            )
        else:
            # Show "No line" when no position data
            self.canvas.create_text(
                bar_center_x, bar_y + bar_height / 2,
                text="No line", fill="#888", font=("Segoe UI", 9),
                anchor="center"
            )

    def _generate_spline_points(self, x_coords: List[float], y_coords: List[float], 
                                values: List[int], max_value: int) -> List[tuple]:
        """Generate smooth spline points using Catmull-Rom spline interpolation"""
        if len(x_coords) < 2:
            return []
        
        spline_points = []
        num_segments = len(x_coords) - 1
        
        for seg in range(num_segments):
            # Get control points for this segment
            p0_idx = max(0, seg - 1)
            p1_idx = seg
            p2_idx = seg + 1
            p3_idx = min(len(x_coords) - 1, seg + 2)
            
            p0 = (x_coords[p0_idx], y_coords[p0_idx])
            p1 = (x_coords[p1_idx], y_coords[p1_idx])
            p2 = (x_coords[p2_idx], y_coords[p2_idx])
            p3 = (x_coords[p3_idx], y_coords[p3_idx])
            
            # Generate points along the spline curve
            steps = 20  # Number of interpolated points per segment
            for i in range(steps + 1):
                t = i / steps
                # Catmull-Rom spline formula
                t2 = t * t
                t3 = t2 * t
                
                x = 0.5 * (
                    (2 * p1[0]) +
                    (-p0[0] + p2[0]) * t +
                    (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                    (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
                )
                
                y = 0.5 * (
                    (2 * p1[1]) +
                    (-p0[1] + p2[1]) * t +
                    (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                    (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
                )
                
                # Calculate normalized value for coloring
                if seg < len(values) - 1:
                    # Interpolate value between segment endpoints
                    normalized_val = (values[seg] * (1 - t) + values[seg + 1] * t) / max_value
                else:
                    normalized_val = values[-1] / max_value
                
                spline_points.append((x, y, normalized_val))
        
        return spline_points
    
    def _draw_spline_curve(self, spline_points: List[tuple]) -> None:
        """Draw the spline curve with color-coded segments"""
        if len(spline_points) < 2:
            return
        
        # Draw the spline as connected line segments with color gradients
        for i in range(len(spline_points) - 1):
            x0, y0, norm_val0 = spline_points[i]
            x1, y1, norm_val1 = spline_points[i + 1]
            
            # Use average normalized value for this segment's color
            avg_norm = (norm_val0 + norm_val1) / 2.0
            color = self._value_to_color(avg_norm)
            
            self.canvas.create_line(x0, y0, x1, y1, fill=color, width=2, smooth=False)

    # Tone generation removed

    def _draw_placeholder(self) -> None:
        width = self.canvas.winfo_width() or self.canvas_width
        height = self.canvas.winfo_height() or self.canvas_height
        self.canvas.create_text(
            width / 2,
            height / 2,
            text="Waiting for sensor data (S...) or line position (L...)...",
            fill="#888",
            font=("Segoe UI", 14),
        )

    def _draw_plotter(self) -> None:
        """Draw time-series plotter for L (line position) and O (PID output) values"""
        self.plotter_canvas.delete("all")
        
        with self.plotter_data_lock:
            data = list(self.plotter_data)
        
        if not data:
            width = self.plotter_canvas.winfo_width() or self.plotter_canvas_width
            height = self.plotter_canvas.winfo_height() or self.plotter_canvas_height
            self.plotter_canvas.create_text(
                width / 2,
                height / 2,
                text="Waiting for L (line position) and O (PID output) data...",
                fill="#888",
                font=("Segoe UI", 12),
            )
            return
        
        width = self.plotter_canvas.winfo_width() or self.plotter_canvas_width
        height = self.plotter_canvas.winfo_height() or self.plotter_canvas_height
        
        margin = 50
        usable_width = max(width - margin * 2, 10)
        usable_height = max(height - margin * 2, 10)
        
        # Filter data based on time window (more efficient: iterate once)
        time_window = self.plotter_time_window.get()
        filtered_data = []
        times = []
        l_values = []
        o_values = []
        
        if time_window > 0 and data:
            # Find max time first (only if we have data)
            max_time = max(d[0] for d in data if d[0] is not None)
            time_cutoff = max_time - time_window
            
            # Single pass: filter and extract values
            for d in data:
                t, l_val, o_val = d
                if t is not None and t >= time_cutoff:
                    filtered_data.append(d)
                    times.append(t)
                    if l_val is not None:
                        l_values.append(l_val)
                    if o_val is not None:
                        o_values.append(o_val)
        else:
            # No time window filtering - extract all data
            for d in data:
                t, l_val, o_val = d
                if t is not None:
                    filtered_data.append(d)
                    times.append(t)
                    if l_val is not None:
                        l_values.append(l_val)
                    if o_val is not None:
                        o_values.append(o_val)
        
        data = filtered_data
        
        if not times:
            return
        
        time_min = min(times)
        time_max = max(times)
        time_range = max(time_max - time_min, 0.1)  # Avoid division by zero
        
        # Find value ranges for scaling
        l_min = min(l_values) if l_values else -127
        l_max = max(l_values) if l_values else 127
        l_range = max(l_max - l_min, 1)
        
        o_min = min(o_values) if o_values else -255
        o_max = max(o_values) if o_values else 255
        o_range = max(o_max - o_min, 1)
        
        # Use a combined range that fits both L and O
        combined_min = min(l_min, o_min) if (l_values and o_values) else (l_min if l_values else o_min)
        combined_max = max(l_max, o_max) if (l_values and o_values) else (l_max if l_values else o_max)
        combined_range = max(combined_max - combined_min, 1)
        
        # Draw axes
        graph_bottom = height - margin
        graph_left = margin
        graph_right = width - margin
        graph_top = margin
        
        self.plotter_canvas.create_line(graph_left, graph_bottom, graph_right, graph_bottom, fill="#444", width=1)
        self.plotter_canvas.create_line(graph_left, graph_top, graph_left, graph_bottom, fill="#444", width=1)
        
        # Draw grid lines and labels
        # Y-axis labels
        for i in range(5):
            y_val = combined_min + (combined_range * i / 4)
            y_pos = graph_bottom - (i / 4) * usable_height
            self.plotter_canvas.create_line(graph_left - 5, y_pos, graph_left, y_pos, fill="#555", width=1)
            self.plotter_canvas.create_text(
                graph_left - 8, y_pos,
                text=f"{int(y_val)}",
                fill="#aaa", font=("Segoe UI", 8),
                anchor="e"
            )
        
        # X-axis label (time)
        if time_range > 0:
            self.plotter_canvas.create_text(
                graph_right, graph_bottom + 20,
                text=f"Time: {time_max:.1f}s",
                fill="#aaa", font=("Segoe UI", 8),
                anchor="e"
            )
        
        # Draw L values (line position) in yellow - single pass
        l_points = []
        o_points = []
        for t, l_val, o_val in data:
            if t is not None:
                x = graph_left + ((t - time_min) / time_range) * usable_width
                if l_val is not None:
                    y = graph_bottom - ((l_val - combined_min) / combined_range) * usable_height
                    l_points.append((x, y))
                if o_val is not None:
                    y = graph_bottom - ((o_val - combined_min) / combined_range) * usable_height
                    o_points.append((x, y))
        
        # Draw lines more efficiently
        if len(l_points) > 1:
            # Use create_line with multiple points for better performance
            for i in range(len(l_points) - 1):
                self.plotter_canvas.create_line(
                    l_points[i][0], l_points[i][1],
                    l_points[i + 1][0], l_points[i + 1][1],
                    fill="#ffff00", width=2, smooth=False
                )
        
        if len(o_points) > 1:
            for i in range(len(o_points) - 1):
                self.plotter_canvas.create_line(
                    o_points[i][0], o_points[i][1],
                    o_points[i + 1][0], o_points[i + 1][1],
                    fill="#00ffff", width=2, smooth=False
                )
        
        # Draw legend
        legend_y = graph_top + 15
        if l_values:
            self.plotter_canvas.create_line(
                graph_left + 10, legend_y,
                graph_left + 30, legend_y,
                fill="#ffff00", width=2
            )
            self.plotter_canvas.create_text(
                graph_left + 35, legend_y,
                text="L (Line Position)",
                fill="#ffff00", font=("Segoe UI", 9),
                anchor="w"
            )
        
        if o_values:
            legend_offset = 150 if l_values else 10
            self.plotter_canvas.create_line(
                graph_left + legend_offset, legend_y,
                graph_left + legend_offset + 20, legend_y,
                fill="#00ffff", width=2
            )
            self.plotter_canvas.create_text(
                graph_left + legend_offset + 25, legend_y,
                text="O (PID Output)",
                fill="#00ffff", font=("Segoe UI", 9),
                anchor="w"
            )

    def _value_to_color(self, normalized: float) -> str:
        # Map 0..1 to a blue→green→red gradient
        if normalized < 0.5:
            t = normalized / 0.5
            r = int(0)
            g = int(255 * t)
            b = int(255 * (1 - t))
        else:
            t = (normalized - 0.5) / 0.5
            r = int(255 * t)
            g = int(255 * (1 - t))
            b = int(0)
        return f"#{r:02x}{g:02x}{b:02x}"

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    # Usage: python test/line.py [baudrate] [COMx]
    baudrate = 115200
    preferred_port: Optional[str] = None
    if len(sys.argv) >= 2:
        try:
            baudrate = int(sys.argv[1])
        except Exception:
            preferred_port = sys.argv[1]
    if len(sys.argv) >= 3:
        preferred_port = sys.argv[2]

    # If a port is specified, preselect it by reordering the list later
    if preferred_port:
        # Monkey-patch a small hook to try preferred port first
        original_comports = list_ports.comports
        def _preferred_first():
            ports = list(original_comports())
            ports.sort(key=lambda p: (0 if p.device == preferred_port else 1, p.device))
            return ports
        list_ports.comports = _preferred_first  # type: ignore

    app = SerialLineGraphApp(baudrate=baudrate)
    app.run()


if __name__ == "__main__":
    main()


