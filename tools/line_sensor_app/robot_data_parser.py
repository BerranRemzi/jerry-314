"""Data parser for processing sensor and robot messages."""

from typing import List, Optional, Callable, Any
from robot_data_regex import SENSOR_LINE_REGEX, LINE_POS_REGEX, PID_OUTPUT_REGEX


class SensorData:
    """Container for sensor data and line position information."""
    
    def __init__(self):
        self.sensor_values: List[int] = []
        self.line_position: Optional[float] = None  # Position as fraction (0.0 to 1.0)
        self.line_position_raw: Optional[int] = None  # Raw line position (-127 to +127)
        self.max_value_seen: int = 1


class DataParser:
    """Parses incoming data from the robot and triggers appropriate callbacks."""
    
    def __init__(self):
        self.sensor_data = SensorData()
        
        # Callback functions for different data types
        self.sensor_callback: Optional[Callable[[List[int]], None]] = None
        self.line_position_callback: Optional[Callable[[float, int], None]] = None  # (normalized, raw)
        self.pid_output_callback: Optional[Callable[[int], None]] = None
        self.parameter_callback: Optional[Callable[[str, str], None]] = None  # (param_name, param_value)
        self.data_added_callback: Optional[Callable[[Optional[int], Optional[int]], None]] = None  # (l_value, o_value)
    
    def set_callbacks(self, 
                     sensor_callback: Optional[Callable[[List[int]], None]] = None,
                     line_position_callback: Optional[Callable[[float, int], None]] = None,
                     pid_output_callback: Optional[Callable[[int], None]] = None,
                     parameter_callback: Optional[Callable[[str, str], None]] = None,
                     data_added_callback: Optional[Callable[[Optional[int], Optional[int]], None]] = None) -> None:
        """Set callback functions for different data types."""
        self.sensor_callback = sensor_callback
        self.line_position_callback = line_position_callback
        self.pid_output_callback = pid_output_callback
        self.parameter_callback = parameter_callback
        self.data_added_callback = data_added_callback
    
    def parse_line(self, line: str) -> bool:
        """Parse a single line of data and trigger appropriate callbacks.
        
        Returns True if the line was successfully parsed, False otherwise.
        """
        line_stripped = line.strip()
        
        # Parse sensor values (S prefix)
        # Format: S,968,973,853,894,962,980
        if SENSOR_LINE_REGEX.match(line_stripped):
            self._parse_sensor_data(line_stripped)
            return True
        
        # Parse line position (L prefix)
        # Format: L,3 (value from -127 to +127)
        elif LINE_POS_REGEX.match(line_stripped):
            self._parse_line_position(line_stripped)
            return True
        
        # Parse PID output (O prefix)
        # Format: O,123 (PID output value)
        elif PID_OUTPUT_REGEX.match(line_stripped):
            self._parse_pid_output(line_stripped)
            return True
        
        # Parse parameter responses (e.g., "pid p 10.5", "motor speed 100")
        elif self._parse_parameter_response(line_stripped):
            # Parameter response was handled
            return True
        
        return False
    
    def _parse_sensor_data(self, line: str) -> None:
        """Parse sensor data from line."""
        try:
            text = line[2:].strip()  # Remove 'S,' prefix
            numbers = [int(part.strip()) for part in text.split(',') if part.strip()]
            if numbers:
                self.sensor_data.sensor_values = numbers
                current_max = max(numbers)
                if current_max > self.sensor_data.max_value_seen:
                    self.sensor_data.max_value_seen = current_max
                
                # Trigger sensor callback
                if self.sensor_callback:
                    self.sensor_callback(numbers)
        except Exception:
            pass
    
    def _parse_line_position(self, line: str) -> None:
        """Parse line position from line."""
        try:
            text = line[2:].strip()  # Remove 'L,' prefix
            line_pos = int(text)
            # Clamp to -127 to +127 range
            self.sensor_data.line_position_raw = max(-127, min(127, line_pos))
            
            # Normalize to 0.0-1.0 range based on number of sensors
            if self.sensor_data.sensor_values:
                num_sensors = len(self.sensor_data.sensor_values)
                # Line position is typically the index (0 to num_sensors-1)
                self.sensor_data.line_position = line_pos / max(num_sensors - 1, 1)
            else:
                # Fallback: assume line_pos is already normalized or use as-is
                self.sensor_data.line_position = min(max(line_pos / 100.0, 0.0), 1.0)
            
            # Trigger line position callback
            if self.line_position_callback:
                self.line_position_callback(self.sensor_data.line_position, self.sensor_data.line_position_raw)
            
            # Add to plotter data
            if self.data_added_callback:
                self.data_added_callback(line_pos, None)
                
        except Exception:
            pass
    
    def _parse_pid_output(self, line: str) -> None:
        """Parse PID output from line."""
        try:
            text = line[2:].strip()  # Remove 'O,' prefix
            pid_output = int(text)
            
            # Trigger PID output callback
            if self.pid_output_callback:
                self.pid_output_callback(pid_output)
            
            # Add to plotter data
            if self.data_added_callback:
                self.data_added_callback(None, pid_output)
                
        except Exception:
            pass
    
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
                value = parts[2]
                
                if self.parameter_callback:
                    self.parameter_callback(f"pid_{param_type}", value)
                return True
            
            # Parse "motor speed 100" format
            elif parts[0] == "motor" and parts[1] == "speed" and len(parts) == 3:
                if self.parameter_callback:
                    self.parameter_callback("motor_speed", parts[2])
                return True
        except (ValueError, IndexError):
            pass
        return False
    
    def get_sensor_data(self) -> SensorData:
        """Get the current sensor data."""
        return self.sensor_data
    
    def reset(self) -> None:
        """Reset all sensor data."""
        self.sensor_data = SensorData()