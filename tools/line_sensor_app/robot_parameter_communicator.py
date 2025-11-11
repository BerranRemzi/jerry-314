"""Robot communication handler for parameter reading and writing."""

import threading
import time
from typing import Callable, Optional, Dict, Any


class RobotCommunication:
    """Handles communication with robot for parameter reading/writing."""
    
    def __init__(self, serial_sender: Callable[[str], None], 
                 status_callback: Optional[Callable[[str], None]] = None):
        """Initialize robot communication handler.
        
        Args:
            serial_sender: Function to send commands over serial
            status_callback: Function to update status text
        """
        self.serial_sender = serial_sender
        self.status_callback = status_callback
        self._stop_event = threading.Event()
    
    def set_serial_sender(self, serial_sender: Callable[[str], None]) -> None:
        """Set the serial command sender function."""
        self.serial_sender = serial_sender
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set the status callback function."""
        self.status_callback = callback
    
    def _set_status_text(self, text: str) -> None:
        """Update status text through callback."""
        if self.status_callback:
            self.status_callback(text)
    
    def read_all_parameters(self) -> None:
        """Read all parameters from robot (non-blocking)."""
        def read_thread():
            self._set_status_text("Reading parameters from robot...")
            
            # Read PID parameters
            self._send_command("pid p ?")
            time.sleep(0.1)
            self._send_command("pid i ?")
            time.sleep(0.1)
            self._send_command("pid d ?")
            time.sleep(0.1)
            
            # Read motor speed
            self._send_command("motor speed ?")
            time.sleep(0.1)
            
            self._set_status_text("Reading parameters... (check responses)")
        
        thread = threading.Thread(target=read_thread, daemon=True)
        thread.start()
    
    def write_all_parameters(self, parameters: Dict[str, Any]) -> None:
        """Write all current parameters to robot (non-blocking)."""
        def write_thread():
            self._set_status_text("Writing parameters to robot...")
            
            # Write PID parameters
            if "pid_p" in parameters:
                self._send_command(f"pid p {parameters['pid_p']}")
                time.sleep(0.1)
            
            if "pid_i" in parameters:
                self._send_command(f"pid i {parameters['pid_i']}")
                time.sleep(0.1)
            
            if "pid_d" in parameters:
                self._send_command(f"pid d {parameters['pid_d']}")
                time.sleep(0.1)
            
            # Write motor speed
            if "motor_speed" in parameters:
                self._send_command(f"motor speed {int(parameters['motor_speed'])}")
                time.sleep(0.1)
            
            # Write logging states
            if "log_p" in parameters:
                self._send_command("log p on" if parameters["log_p"] else "log p off")
                time.sleep(0.05)
            
            if "log_i" in parameters:
                self._send_command("log i on" if parameters["log_i"] else "log i off")
                time.sleep(0.05)
            
            if "log_d" in parameters:
                self._send_command("log d on" if parameters["log_d"] else "log d off")
                time.sleep(0.05)
            
            if "log_s" in parameters:
                self._send_command("log s on" if parameters["log_s"] else "log s off")
                time.sleep(0.05)
            
            if "log_l" in parameters:
                self._send_command("log l on" if parameters["log_l"] else "log l off")
                time.sleep(0.05)
            
            if "log_o" in parameters:
                self._send_command("log o on" if parameters["log_o"] else "log o off")
            
            self._set_status_text("Parameters written to robot")
        
        thread = threading.Thread(target=write_thread, daemon=True)
        thread.start()
    
    def write_single_parameter(self, param_name: str, value: Any) -> None:
        """Write a single parameter to robot.
        
        Args:
            param_name: Name of the parameter (e.g., 'pid_p', 'motor_speed')
            value: Value to write
        """
        if param_name == "pid_p":
            self._send_command(f"pid p {value}")
        elif param_name == "pid_i":
            self._send_command(f"pid i {value}")
        elif param_name == "pid_d":
            self._send_command(f"pid d {value}")
        elif param_name == "motor_speed":
            self._send_command(f"motor speed {int(value)}")
        elif param_name == "log_p":
            self._send_command("log p on" if value else "log p off")
        elif param_name == "log_i":
            self._send_command("log i on" if value else "log i off")
        elif param_name == "log_d":
            self._send_command("log d on" if value else "log d off")
        elif param_name == "log_s":
            self._send_command("log s on" if value else "log s off")
        elif param_name == "log_l":
            self._send_command("log l on" if value else "log l off")
        elif param_name == "log_o":
            self._send_command("log o on" if value else "log o off")
        elif param_name == "motor_start":
            self._send_command("motor start")
        elif param_name == "motor_stop":
            self._send_command("motor stop")
    
    def _send_command(self, command: str) -> None:
        """Send a command to the robot."""
        if self.serial_sender:
            self.serial_sender(command)
    
    def shutdown(self) -> None:
        """Shutdown the robot communication handler."""
        self._stop_event.set()