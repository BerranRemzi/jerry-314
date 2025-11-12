"""Control panel for GUI widgets and event handling."""

import tkinter as tk
from tkinter import filedialog
from typing import Optional, Callable, Dict, Any
import json


class ControlPanel:
    """Handles GUI controls and event management."""
    
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.root = parent.winfo_toplevel()
        
        # Variable references for all controls
        self.status_text_var = tk.StringVar(value="Scanning serial ports…")
        
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
        
        # Time window variables
        self.plotter_time_window = tk.DoubleVar(value=10.0)
        self.plotter_time_window_max = tk.DoubleVar(value=60.0)
        
        # File management
        self.current_file_path: Optional[str] = None
        
        # Callback functions
        self.serial_command_callback: Optional[Callable[[str], None]] = None
        self.file_open_callback: Optional[Callable[[], None]] = None
        self.file_save_callback: Optional[Callable[[], None]] = None
        self.file_save_as_callback: Optional[Callable[[], None]] = None
        self.robot_read_callback: Optional[Callable[[], None]] = None
        self.robot_write_callback: Optional[Callable[[], None]] = None
        
        # Control reference dictionary for external access
        self.controls: Dict[str, tk.Widget] = {}
        
        # Flag to prevent circular updates
        self._updating_control = False
        
        # Create the control panel
        self.create_control_panel()
    
    def set_serial_command_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for sending serial commands."""
        self.serial_command_callback = callback
    
    def set_file_callbacks(self, open_callback: Callable[[], None], 
                          save_callback: Callable[[], None],
                          save_as_callback: Callable[[], None]) -> None:
        """Set callbacks for file operations."""
        self.file_open_callback = open_callback
        self.file_save_callback = save_callback
        self.file_save_as_callback = save_as_callback
    
    def set_robot_callbacks(self, read_callback: Callable[[], None], 
                           write_callback: Callable[[], None]) -> None:
        """Set callbacks for robot communication."""
        self.robot_read_callback = read_callback
        self.robot_write_callback = write_callback
    
    def create_control_panel(self) -> None:
        """Create the complete control panel."""
        # Create status label
        self.port_label = tk.Label(self.parent, textvariable=self.status_text_var, anchor="w")
        self.port_label.pack(fill="x", padx=8, pady=4)
        
        # Create a scrollable container (using pack for simplicity)
        main_container = tk.Frame(self.parent)
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
        time_window_slider = tk.Scale(plotter_grid, from_=1.0, to=self.plotter_time_window_max.get(), 
                                      resolution=0.5, orient="horizontal", variable=self.plotter_time_window, 
                                      command=lambda v: self._on_time_window_slider_changed(v), length=120)
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
        pid_p_text.bind("<MouseWheel>", lambda e: self._on_pid_p_scroll(e))
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
        pid_i_text.bind("<MouseWheel>", lambda e: self._on_pid_i_scroll(e))
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
        pid_d_text.bind("<MouseWheel>", lambda e: self._on_pid_d_scroll(e))
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
        self.controls = {
            'pid_p_text': pid_p_text,
            'pid_i_text': pid_i_text,
            'pid_d_text': pid_d_text,
            'motor_text': motor_text,
            'pid_p_slider': pid_p_slider,
            'pid_i_slider': pid_i_slider,
            'pid_d_slider': pid_d_slider,
            'motor_slider': motor_slider,
            'pid_p_max_text': pid_p_max_text,
            'pid_i_max_text': pid_i_max_text,
            'pid_d_max_text': pid_d_max_text,
            'motor_max_text': motor_max_text,
            'time_window_text': time_window_text,
            'time_window_slider': time_window_slider,
            'time_window_max_text': time_window_max_text,
        }
        
        # Initialize textboxes with current values
        self._sync_textboxes()
    
    # PID Control Event Handlers
    def _on_pid_p_changed(self) -> None:
        """Handle PID P value change from textbox"""
        if self._updating_control:
            return
        try:
            value = float(self.controls['pid_p_text'].get())
            self._updating_control = True
            self.pid_p_value.set(value)
            self._updating_control = False
            if self.serial_command_callback:
                self.serial_command_callback(f"pid p {value}")
        except ValueError:
            # Invalid value, restore from variable
            self._updating_control = True
            self.controls['pid_p_text'].delete(0, tk.END)
            self.controls['pid_p_text'].insert(0, str(self.pid_p_value.get()))
            self._updating_control = False

    def _on_pid_p_slider_changed(self, value: str) -> None:
        """Handle PID P value change from slider"""
        if self._updating_control:
            return
        try:
            float_value = float(value)
            self._updating_control = True
            self.controls['pid_p_text'].delete(0, tk.END)
            self.controls['pid_p_text'].insert(0, value)
            self._updating_control = False
            if self.serial_command_callback:
                self.serial_command_callback(f"pid p {float_value}")
        except ValueError:
            pass

    def _on_pid_i_changed(self) -> None:
        """Handle PID I value change from textbox"""
        if self._updating_control:
            return
        try:
            value = float(self.controls['pid_i_text'].get())
            self._updating_control = True
            self.pid_i_value.set(value)
            self._updating_control = False
            if self.serial_command_callback:
                self.serial_command_callback(f"pid i {value}")
        except ValueError:
            # Invalid value, restore from variable
            self._updating_control = True
            self.controls['pid_i_text'].delete(0, tk.END)
            self.controls['pid_i_text'].insert(0, str(self.pid_i_value.get()))
            self._updating_control = False

    def _on_pid_i_slider_changed(self, value: str) -> None:
        """Handle PID I value change from slider"""
        if self._updating_control:
            return
        try:
            float_value = float(value)
            self._updating_control = True
            self.controls['pid_i_text'].delete(0, tk.END)
            self.controls['pid_i_text'].insert(0, value)
            self._updating_control = False
            if self.serial_command_callback:
                self.serial_command_callback(f"pid i {float_value}")
        except ValueError:
            pass

    def _on_pid_d_changed(self) -> None:
        """Handle PID D value change from textbox"""
        if self._updating_control:
            return
        try:
            value = float(self.controls['pid_d_text'].get())
            self._updating_control = True
            self.pid_d_value.set(value)
            self._updating_control = False
            if self.serial_command_callback:
                self.serial_command_callback(f"pid d {value}")
        except ValueError:
            # Invalid value, restore from variable
            self._updating_control = True
            self.controls['pid_d_text'].delete(0, tk.END)
            self.controls['pid_d_text'].insert(0, str(self.pid_d_value.get()))
            self._updating_control = False

    def _on_pid_d_slider_changed(self, value: str) -> None:
        """Handle PID D value change from slider"""
        if self._updating_control:
            return
        try:
            float_value = float(value)
            self._updating_control = True
            self.controls['pid_d_text'].delete(0, tk.END)
            self.controls['pid_d_text'].insert(0, value)
            self._updating_control = False
            if self.serial_command_callback:
                self.serial_command_callback(f"pid d {float_value}")
        except ValueError:
            pass

    # PID Scroll Event Handlers
    def _on_pid_p_scroll(self, event) -> None:
        """Handle PID P value change from mouse wheel scroll"""
        if self._updating_control:
            return
        try:
            # Determine scroll direction (delta > 0 = scroll up, delta < 0 = scroll down)
            delta = 1 if event.delta > 0 else -1
            
            # Get current value and step size
            current_value = self.pid_p_value.get()
            max_value = self.pid_p_max.get()
            step_size = 0.1  # Small increment for precise control
            
            # Calculate new value
            new_value = round(current_value + (delta * step_size), 1)
            new_value = max(0.0, min(new_value, max_value))  # Clamp to valid range
            
            # Update values
            self._updating_control = True
            self.pid_p_value.set(new_value)
            self.controls['pid_p_text'].delete(0, tk.END)
            self.controls['pid_p_text'].insert(0, str(new_value))
            self._updating_control = False
            
            # Send serial command
            if self.serial_command_callback:
                self.serial_command_callback(f"pid p {new_value}")
                
        except ValueError:
            pass

    def _on_pid_i_scroll(self, event) -> None:
        """Handle PID I value change from mouse wheel scroll"""
        if self._updating_control:
            return
        try:
            # Determine scroll direction (delta > 0 = scroll up, delta < 0 = scroll down)
            delta = 1 if event.delta > 0 else -1
            
            # Get current value and step size
            current_value = self.pid_i_value.get()
            max_value = self.pid_i_max.get()
            step_size = 0.1  # Small increment for precise control
            
            # Calculate new value
            new_value = current_value + (delta * step_size)
            new_value = max(0.0, min(new_value, max_value))  # Clamp to valid range
            
            # Update values
            self._updating_control = True
            self.pid_i_value.set(new_value)
            self.controls['pid_i_text'].delete(0, tk.END)
            self.controls['pid_i_text'].insert(0, str(new_value))
            self._updating_control = False
            
            # Send serial command
            if self.serial_command_callback:
                self.serial_command_callback(f"pid i {new_value}")
                
        except ValueError:
            pass

    def _on_pid_d_scroll(self, event) -> None:
        """Handle PID D value change from mouse wheel scroll"""
        if self._updating_control:
            return
        try:
            # Determine scroll direction (delta > 0 = scroll up, delta < 0 = scroll down)
            delta = 1 if event.delta > 0 else -1
            
            # Get current value and step size
            current_value = self.pid_d_value.get()
            max_value = self.pid_d_max.get()
            step_size = 0.1  # Small increment for precise control
            
            # Calculate new value
            new_value = current_value + (delta * step_size)
            new_value = max(0.0, min(new_value, max_value))  # Clamp to valid range
            
            # Update values
            self._updating_control = True
            self.pid_d_value.set(new_value)
            self.controls['pid_d_text'].delete(0, tk.END)
            self.controls['pid_d_text'].insert(0, str(new_value))
            self._updating_control = False
            
            # Send serial command
            if self.serial_command_callback:
                self.serial_command_callback(f"pid d {new_value}")
                
        except ValueError:
            pass

    # Motor Control Event Handlers
    def _on_motor_speed_changed(self) -> None:
        """Handle motor speed value change from textbox"""
        if self._updating_control:
            return
        try:
            value = float(self.controls['motor_text'].get())
            self._updating_control = True
            self.motor_speed_value.set(value)
            self._updating_control = False
            if self.serial_command_callback:
                self.serial_command_callback(f"motor speed {value}")
        except ValueError:
            # Invalid value, restore from variable
            self._updating_control = True
            self.controls['motor_text'].delete(0, tk.END)
            self.controls['motor_text'].insert(0, str(self.motor_speed_value.get()))
            self._updating_control = False

    def _on_motor_speed_slider_changed(self, value: str) -> None:
        """Handle motor speed value change from slider"""
        if self._updating_control:
            return
        try:
            int_value = int(float(value))
            self._updating_control = True
            self.controls['motor_text'].delete(0, tk.END)
            self.controls['motor_text'].insert(0, str(int_value))
            self._updating_control = False
            if self.serial_command_callback:
                self.serial_command_callback(f"motor speed {int_value}")
        except ValueError:
            pass

    def _on_motor_start(self) -> None:
        """Handle motor start button click"""
        if self.serial_command_callback:
            self.serial_command_callback("motor start")

    def _on_motor_stop(self) -> None:
        """Handle motor stop button click"""
        if self.serial_command_callback:
            self.serial_command_callback("motor stop")

    # Maximum Value Event Handlers
    def _on_pid_p_max_changed(self) -> None:
        """Handle PID P max value change"""
        try:
            max_val = float(self.controls['pid_p_max_text'].get())
            if max_val > 0:
                self.pid_p_max.set(max_val)
                self.controls['pid_p_slider'].config(to=max_val)
                # Clamp current value if needed
                if self.pid_p_value.get() > max_val:
                    self.pid_p_value.set(max_val)
                    self.controls['pid_p_text'].delete(0, tk.END)
                    self.controls['pid_p_text'].insert(0, str(max_val))
        except ValueError:
            # Invalid value, restore
            self.controls['pid_p_max_text'].delete(0, tk.END)
            self.controls['pid_p_max_text'].insert(0, str(self.pid_p_max.get()))

    def _on_pid_i_max_changed(self) -> None:
        """Handle PID I max value change"""
        try:
            max_val = float(self.controls['pid_i_max_text'].get())
            if max_val > 0:
                self.pid_i_max.set(max_val)
                self.controls['pid_i_slider'].config(to=max_val)
                # Clamp current value if needed
                if self.pid_i_value.get() > max_val:
                    self.pid_i_value.set(max_val)
                    self.controls['pid_i_text'].delete(0, tk.END)
                    self.controls['pid_i_text'].insert(0, str(max_val))
        except ValueError:
            # Invalid value, restore
            self.controls['pid_i_max_text'].delete(0, tk.END)
            self.controls['pid_i_max_text'].insert(0, str(self.pid_i_max.get()))

    def _on_pid_d_max_changed(self) -> None:
        """Handle PID D max value change"""
        try:
            max_val = float(self.controls['pid_d_max_text'].get())
            if max_val > 0:
                self.pid_d_max.set(max_val)
                self.controls['pid_d_slider'].config(to=max_val)
                # Clamp current value if needed
                if self.pid_d_value.get() > max_val:
                    self.pid_d_value.set(max_val)
                    self.controls['pid_d_text'].delete(0, tk.END)
                    self.controls['pid_d_text'].insert(0, str(max_val))
        except ValueError:
            # Invalid value, restore
            self.controls['pid_d_max_text'].delete(0, tk.END)
            self.controls['pid_d_max_text'].insert(0, str(self.pid_d_max.get()))

    def _on_motor_speed_max_changed(self) -> None:
        """Handle motor speed max value change"""
        try:
            max_val = float(self.controls['motor_max_text'].get())
            if max_val > 0:
                self.motor_speed_max.set(max_val)
                self.controls['motor_slider'].config(to=max_val)
                # Clamp current value if needed
                if self.motor_speed_value.get() > max_val:
                    self.motor_speed_value.set(max_val)
                    self.controls['motor_text'].delete(0, tk.END)
                    self.controls['motor_text'].insert(0, str(int(max_val)))
        except ValueError:
            # Invalid value, restore
            self.controls['motor_max_text'].delete(0, tk.END)
            self.controls['motor_max_text'].insert(0, str(self.motor_speed_max.get()))

    # Time Window Event Handlers
    def _on_time_window_changed(self) -> None:
        """Handle time window value change from textbox"""
        try:
            value = float(self.controls['time_window_text'].get())
            if value > 0:
                self._updating_control = True
                self.plotter_time_window.set(value)
                self._updating_control = False
        except ValueError:
            # Invalid value, restore from variable
            self._updating_control = True
            self.controls['time_window_text'].delete(0, tk.END)
            self.controls['time_window_text'].insert(0, str(self.plotter_time_window.get()))
            self._updating_control = False

    def _on_time_window_slider_changed(self, value: str) -> None:
        """Handle time window value change from slider"""
        if self._updating_control:
            return
        try:
            float_value = float(value)
            # Update the variable (this is already done by the Scale widget, but ensure it's set)
            self._updating_control = True
            self.plotter_time_window.set(float_value)
            self.controls['time_window_text'].delete(0, tk.END)
            self.controls['time_window_text'].insert(0, value)
            self._updating_control = False
        except ValueError:
            pass

    def _on_time_window_max_changed(self) -> None:
        """Handle time window max value change"""
        try:
            max_val = float(self.controls['time_window_max_text'].get())
            if max_val > 0:
                self.plotter_time_window_max.set(max_val)
                self.controls['time_window_slider'].config(to=max_val)
                # Clamp current value if needed
                if self.plotter_time_window.get() > max_val:
                    self.plotter_time_window.set(max_val)
                    self.controls['time_window_text'].delete(0, tk.END)
                    self.controls['time_window_text'].insert(0, str(max_val))
        except ValueError:
            # Invalid value, restore
            self.controls['time_window_max_text'].delete(0, tk.END)
            self.controls['time_window_max_text'].insert(0, str(self.plotter_time_window_max.get()))

    # Logging Event Handlers
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
        if self.serial_command_callback:
            self.serial_command_callback(f"log {log_type} {state}")

    # File Operation Event Handlers
    def _on_file_open(self) -> None:
        """Handle file open button click"""
        if self.file_open_callback:
            self.file_open_callback()

    def _on_file_save(self) -> None:
        """Handle file save button click"""
        if self.file_save_callback:
            self.file_save_callback()

    def _on_file_save_as(self) -> None:
        """Handle file save as button click"""
        if self.file_save_as_callback:
            self.file_save_as_callback()

    # Robot Communication Event Handlers
    def _on_robot_read(self) -> None:
        """Handle robot read button click"""
        if self.robot_read_callback:
            self.robot_read_callback()

    def _on_robot_write(self) -> None:
        """Handle robot write button click"""
        if self.robot_write_callback:
            self.robot_write_callback()

    # Utility Methods
    def _sync_textboxes(self) -> None:
        """Sync textboxes with current variable values"""
        if not self._updating_control:
            self._updating_control = True
            self.controls['pid_p_text'].delete(0, tk.END)
            self.controls['pid_p_text'].insert(0, str(self.pid_p_value.get()))
            self.controls['pid_i_text'].delete(0, tk.END)
            self.controls['pid_i_text'].insert(0, str(self.pid_i_value.get()))
            self.controls['pid_d_text'].delete(0, tk.END)
            self.controls['pid_d_text'].insert(0, str(self.pid_d_value.get()))
            self.controls['motor_text'].delete(0, tk.END)
            self.controls['motor_text'].insert(0, str(int(self.motor_speed_value.get())))
            self._updating_control = False

    def get_all_parameters(self) -> dict:
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

    def set_all_parameters(self, params: dict) -> None:
        """Set all parameters from a dictionary"""
        self._updating_control = True
        try:
            if "pid_p" in params:
                self.pid_p_value.set(params["pid_p"])
                self.controls['pid_p_text'].delete(0, tk.END)
                self.controls['pid_p_text'].insert(0, str(params["pid_p"]))
            if "pid_i" in params:
                self.pid_i_value.set(params["pid_i"])
                self.controls['pid_i_text'].delete(0, tk.END)
                self.controls['pid_i_text'].insert(0, str(params["pid_i"]))
            if "pid_d" in params:
                self.pid_d_value.set(params["pid_d"])
                self.controls['pid_d_text'].delete(0, tk.END)
                self.controls['pid_d_text'].insert(0, str(params["pid_d"]))
            if "motor_speed" in params:
                self.motor_speed_value.set(params["motor_speed"])
                self.controls['motor_text'].delete(0, tk.END)
                self.controls['motor_text'].insert(0, str(int(params["motor_speed"])))
            
            if "pid_p_max" in params:
                self.pid_p_max.set(params["pid_p_max"])
                self.controls['pid_p_max_text'].delete(0, tk.END)
                self.controls['pid_p_max_text'].insert(0, str(params["pid_p_max"]))
                self.controls['pid_p_slider'].config(to=params["pid_p_max"])
            if "pid_i_max" in params:
                self.pid_i_max.set(params["pid_i_max"])
                self.controls['pid_i_max_text'].delete(0, tk.END)
                self.controls['pid_i_max_text'].insert(0, str(params["pid_i_max"]))
                self.controls['pid_i_slider'].config(to=params["pid_i_max"])
            if "pid_d_max" in params:
                self.pid_d_max.set(params["pid_d_max"])
                self.controls['pid_d_max_text'].delete(0, tk.END)
                self.controls['pid_d_max_text'].insert(0, str(params["pid_d_max"]))
                self.controls['pid_d_slider'].config(to=params["pid_d_max"])
            if "motor_speed_max" in params:
                self.motor_speed_max.set(params["motor_speed_max"])
                self.controls['motor_max_text'].delete(0, tk.END)
                self.controls['motor_max_text'].insert(0, str(params["motor_speed_max"]))
                self.controls['motor_slider'].config(to=params["motor_speed_max"])
            
            if "time_window" in params:
                self.plotter_time_window.set(params["time_window"])
                self.controls['time_window_text'].delete(0, tk.END)
                self.controls['time_window_text'].insert(0, str(params["time_window"]))
            if "time_window_max" in params:
                self.plotter_time_window_max.set(params["time_window_max"])
                self.controls['time_window_max_text'].delete(0, tk.END)
                self.controls['time_window_max_text'].insert(0, str(params["time_window_max"]))
                self.controls['time_window_slider'].config(to=params["time_window_max"])
            
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

    def set_status_text(self, text: str) -> None:
        """Set the status text."""
        self.status_text_var.set(text)
    
    def get_current_file_path(self) -> Optional[str]:
        """Get the current file path."""
        return self.current_file_path
    
    def set_current_file_path(self, file_path: Optional[str]) -> None:
        """Set the current file path."""
        self.current_file_path = file_path