"""Main application module that orchestrates all components."""

import threading
import time
import tkinter as tk
from typing import List, Optional
import sys

# Import all modules
from robot_serial_manager import SerialManager
from robot_data_parser import DataParser
from sensor_graph_renderer import GraphRenderer
from time_series_plotter import PlotterRenderer
from robot_control_panel import ControlPanel
from parameter_file_manager import FileManager
from robot_parameter_communicator import RobotCommunication


class SerialLineGraphApp:
    """Main application that coordinates all components."""
    
    def __init__(self, baudrate: int = 115200, read_timeout_s: float = 0.1):
        # Initialize main window
        self.root = tk.Tk()
        self.root.title("Line Sensor Graph")
        self.root.geometry("1200x700")  # Initial window size: width x height
        
        # Initialize all components
        self._initialize_components(baudrate, read_timeout_s)
        
        # Create UI layout
        self._create_layout()
        
        # Initialize data
        self._setup_data_handling()
        
        # Start background threads
        self._start_background_processes()
        
        # Setup window closing
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _initialize_components(self, baudrate: int, read_timeout_s: float) -> None:
        """Initialize all application components."""
        # Serial manager
        self.serial_manager = SerialManager(baudrate=baudrate, read_timeout_s=read_timeout_s)
        
        # Data parser
        self.data_parser = DataParser()
        
        # Graph renderer
        self.canvas = None
        self.graph_renderer = None
        
        # Plotter renderer
        self.plotter_canvas = None
        self.plotter_renderer = None
        
        # Control panel
        self.control_frame = None
        self.control_panel = None
        
        # File manager
        self.file_manager = FileManager()
        
        # Robot communication
        self.robot_communication = RobotCommunication(
            serial_sender=self.serial_manager.send_command,
            status_callback=None  # Will be set later
        )
        
        # Current sensor values for graph rendering
        self.current_sensor_values: List[int] = []
        
        # Stop event
        self.stop_event = threading.Event()
    
    def _create_layout(self) -> None:
        """Create the main application layout."""
        # Main container with left (graphs) and right (controls) frames
        main_container = tk.Frame(self.root)
        main_container.pack(fill="both", expand=True, padx=4, pady=4)

        # Left frame for graphs
        left_frame = tk.Frame(main_container)
        left_frame.pack(side="left", fill="both", expand=True, padx=4)

        # Graph canvas
        self.canvas_width = 800
        self.canvas_height = 300
        self.canvas = tk.Canvas(left_frame, width=self.canvas_width, height=self.canvas_height, bg="#111")
        self.canvas.pack(fill="both", expand=True, padx=4, pady=4)
        
        # Initialize graph renderer
        self.graph_renderer = GraphRenderer(self.canvas, self.canvas_width, self.canvas_height)

        # Plotter canvas for L and O values over time
        self.plotter_canvas_width = 800
        self.plotter_canvas_height = 200
        self.plotter_canvas = tk.Canvas(left_frame, width=self.plotter_canvas_width, height=self.plotter_canvas_height, bg="#111")
        self.plotter_canvas.pack(fill="both", expand=True, padx=4, pady=4)
        
        # Initialize plotter renderer
        self.plotter_renderer = PlotterRenderer(self.plotter_canvas, self.plotter_canvas_width, self.plotter_canvas_height)

        # Right frame for controls
        self.control_frame = tk.Frame(main_container, width=300)
        self.control_frame.pack(side="right", fill="y", padx=4, pady=4)
        self.control_frame.pack_propagate(False)  # Maintain fixed width
        
        # Initialize control panel
        self.control_panel = ControlPanel(self.control_frame)
        
        # Connect callbacks
        self._setup_callbacks()
    
    def _setup_callbacks(self) -> None:
        """Setup all component callbacks."""
        # Serial manager status callback
        self.serial_manager.set_status_callback(self.control_panel.set_status_text)
        
        # File manager status callback
        self.file_manager.set_status_callback(self.control_panel.set_status_text)
        
        # Robot communication status callback
        self.robot_communication.set_status_callback(self.control_panel.set_status_text)
        
        # Control panel callbacks
        self.control_panel.set_serial_command_callback(self.serial_manager.send_command)
        self.control_panel.set_file_callbacks(
            open_callback=self._on_file_open,
            save_callback=self._on_file_save,
            save_as_callback=self._on_file_save_as
        )
        self.control_panel.set_robot_callbacks(
            read_callback=self._on_robot_read,
            write_callback=self._on_robot_write
        )
        
        # Data parser callbacks
        self.data_parser.set_callbacks(
            sensor_callback=self._on_sensor_data,
            line_position_callback=self._on_line_position,
            pid_output_callback=self._on_pid_output,
            parameter_callback=self._on_parameter_response,
            data_added_callback=self.plotter_renderer.add_data_point
        )
        
        # Connect plotter time window changes
        self.control_panel.plotter_time_window.trace_add('write', self._on_time_window_changed)
        self.control_panel.plotter_time_window_max.trace_add('write', self._on_time_window_max_changed)
    
    def _setup_data_handling(self) -> None:
        """Setup data handling connections."""
        # Sync file paths
        self.file_manager.set_current_file_path(self.control_panel.get_current_file_path())
    
    def _start_background_processes(self) -> None:
        """Start background threads and processes."""
        # Start serial reader thread
        self.reader_thread = threading.Thread(target=self._reader_loop, name="SerialReader", daemon=True)
        self.reader_thread.start()
        
        # Start GUI update loop
        self._schedule_gui_update()
    
    def _reader_loop(self) -> None:
        """Background thread for reading serial data."""
        while not self.stop_event.is_set():
            if not self.serial_manager._ensure_open_port():
                # No valid port yet; wait a bit before rescanning
                time.sleep(0.5)
                continue

            line = self.serial_manager._readline()
            if line is None:
                # Possible disconnect or timeout; retry
                continue

            # Parse the line
            self.data_parser.parse_line(line)
    
    def _schedule_gui_update(self) -> None:
        """Schedule periodic GUI updates."""
        try:
            self._draw_graph()
            self.plotter_renderer.draw_plotter()
        except Exception:
            # Prevent crashes from breaking the update loop
            pass
        # Update ~30 FPS for better responsiveness
        self.root.after(33, self._schedule_gui_update)
    
    def _draw_graph(self) -> None:
        """Draw the sensor graph."""
        if self.graph_renderer and self.current_sensor_values:
            self.graph_renderer.update_sensor_data(self.data_parser.get_sensor_data())
            self.graph_renderer.draw_graph(self.current_sensor_values)
    
    # Event handlers for data callbacks
    def _on_sensor_data(self, sensor_values: List[int]) -> None:
        """Handle new sensor data."""
        self.current_sensor_values = sensor_values
    
    def _on_line_position(self, normalized_position: float, raw_position: int) -> None:
        """Handle line position data."""
        if self.graph_renderer:
            self.graph_renderer.update_line_position(normalized_position, raw_position)
    
    def _on_pid_output(self, pid_output: int) -> None:
        """Handle PID output data."""
        # Additional handling can be added here if needed
        pass
    
    def _on_parameter_response(self, param_name: str, param_value: str) -> None:
        """Handle parameter response from robot."""
        # Update control panel if parameter matches known parameters
        if param_name.startswith("pid_"):
            param_type = param_name.split("_")[1]
            try:
                value = float(param_value)
                self.control_panel._updating_control = True
                if param_type == "p":
                    self.control_panel.pid_p_value.set(value)
                    self.control_panel.controls['pid_p_text'].delete(0, tk.END)
                    self.control_panel.controls['pid_p_text'].insert(0, str(value))
                elif param_type == "i":
                    self.control_panel.pid_i_value.set(value)
                    self.control_panel.controls['pid_i_text'].delete(0, tk.END)
                    self.control_panel.controls['pid_i_text'].insert(0, str(value))
                elif param_type == "d":
                    self.control_panel.pid_d_value.set(value)
                    self.control_panel.controls['pid_d_text'].delete(0, tk.END)
                    self.control_panel.controls['pid_d_text'].insert(0, str(value))
                self.control_panel._updating_control = False
            except ValueError:
                pass
        elif param_name == "motor_speed":
            try:
                value = float(param_value)
                self.control_panel._updating_control = True
                self.control_panel.motor_speed_value.set(value)
                self.control_panel.controls['motor_text'].delete(0, tk.END)
                self.control_panel.controls['motor_text'].insert(0, str(int(value)))
                self.control_panel._updating_control = False
            except ValueError:
                pass
    
    # Time window change handlers
    def _on_time_window_changed(self, *args) -> None:
        """Handle time window change."""
        new_value = self.control_panel.plotter_time_window.get()
        self.plotter_renderer.set_time_window(new_value)
    
    def _on_time_window_max_changed(self, *args) -> None:
        """Handle time window max change."""
        new_value = self.control_panel.plotter_time_window_max.get()
        self.plotter_renderer.set_time_window_max(new_value)
        self.control_panel.controls['time_window_slider'].config(to=new_value)
    
    # File operation handlers
    def _on_file_open(self) -> None:
        """Handle file open operation."""
        params = self.file_manager.open_parameters_file()
        if params:
            self.control_panel.set_all_parameters(params)
    
    def _on_file_save(self) -> None:
        """Handle file save operation."""
        params = self.control_panel.get_all_parameters()
        self.file_manager.save_parameters_file(params)
    
    def _on_file_save_as(self) -> None:
        """Handle file save as operation."""
        params = self.control_panel.get_all_parameters()
        self.file_manager.save_parameters_file_as(params)
    
    # Robot communication handlers
    def _on_robot_read(self) -> None:
        """Handle robot read operation."""
        self.robot_communication.read_all_parameters()
    
    def _on_robot_write(self) -> None:
        """Handle robot write operation."""
        params = self.control_panel.get_all_parameters()
        self.robot_communication.write_all_parameters(params)
    
    def _on_close(self) -> None:
        """Handle application closing."""
        # Stop all background processes
        self.stop_event.set()
        
        # Close serial connection
        self.serial_manager.close()
        
        # Shutdown robot communication
        self.robot_communication.shutdown()
        
        # Destroy window
        self.root.destroy()
    
    def run(self) -> None:
        """Start the application main loop."""
        self.root.mainloop()


def main() -> None:
    """Main entry point for the application."""
    # Usage: python test/line_sensor_app.py [baudrate] [COMx]
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
        from serial.tools import list_ports
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