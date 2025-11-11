# Line Sensor App - Robot Line Following Monitoring & Control

A comprehensive Python GUI application for monitoring sensor data, visualizing line detection, and controlling PID parameters of a line-following robot in real-time.

## Overview

This application provides a complete interface for robot line-following systems, featuring real-time sensor visualization, line position tracking, time-series analysis, and interactive PID parameter tuning. It connects to robots via serial communication and displays live data in an intuitive tkinter-based GUI.

## Features

### 🔍 Real-Time Monitoring
- **Live Sensor Graph**: Visualizes sensor values using smooth spline curves with color-coded values
- **Line Position Tracking**: Displays detected line position with visual indicators
- **Line Position Bar**: Horizontal indicator showing line position from -127 to +127
- **PID Output Monitoring**: Real-time tracking of PID controller output values

### 📊 Time-Series Analysis
- **L/O Plotter**: Time-series visualization of Line position (L) and PID output (O)
- **Configurable Time Window**: Adjustable display window (1-60 seconds)
- **Dual Data Streams**: Separate yellow (L) and cyan (O) trend lines
- **Real-Time Updates**: Continuous plotting as new data arrives

### ⚙️ Interactive Control Panel
- **PID Tuning**: Proportional, Integral, and Derivative controls with sliders and text inputs
- **Motor Control**: Speed adjustment (0-255) with start/stop buttons
- **Parameter Management**: Dynamic value ranges and real-time updates
- **Logging Controls**: Selective logging for P, I, D, S, L, O data streams

### 💾 File Operations
- **Parameter Saving**: Export PID and motor settings to JSON files
- **Parameter Loading**: Import saved configurations
- **Example Configuration**: Sample parameter file included (`example.json`)

### 🤖 Robot Communication
- **Serial Connection**: Automatic port scanning and connection
- **Parameter Reading**: Fetch current settings from robot
- **Parameter Writing**: Send new settings to robot in real-time
- **Auto-Reconnection**: Handles connection drops and port changes

## Architecture

### Core Components

1. **SerialLineGraphApp** - Main application orchestrator
2. **SerialManager** - Serial communication handler with auto-detection
3. **DataParser** - Message parsing and callback management
4. **GraphRenderer** - Real-time sensor graph visualization
5. **PlotterRenderer** - Time-series data plotting
6. **ControlPanel** - Interactive GUI controls and event handling
7. **FileManager** - JSON parameter file operations
8. **RobotCommunication** - Robot parameter exchange
9. **Data Regex** - Message format validation patterns

### Message Protocol

The application expects specific message formats from the robot:

```
# Sensor data (multiple comma-separated values)
S,968,973,853,894,962,980

# Line position (-127 to +127)
L,3
L,-15

# PID output (any integer value)
O,123
O,-45

# Parameter responses from robot
pid p 1.1
pid i 0.0
pid d 5.1
motor speed 58
```

## Installation

### Requirements
```bash
pip install pyserial
```

### Dependencies
- Python 3.6+
- tkinter (usually included with Python)
- pyserial for serial communication
- Standard library modules: threading, time, json, re

## Usage

### Basic Startup
```bash
cd tools/line_sensor_app
python line_sensor_app.py
```

### Advanced Startup Options
```bash
# Custom baudrate
python line_sensor_app.py 57600

# Specify preferred port
python line_sensor_app.py 115200 COM3

# Custom baudrate and port
python line_sensor_app.py 57600 COM5
```

### GUI Controls

#### Plotter Section
- **Time Window (s)**: Adjust display duration (1.0-60.0 seconds)
- **Max (s)**: Set maximum allowable time window

#### PID Controls
- **P**: Proportional gain adjustment
- **I**: Integral gain adjustment  
- **D**: Derivative gain adjustment
- Each parameter includes:
  - Text input for precise values
  - Slider for coarse adjustment
  - Maximum value configuration

#### Motor Control
- **Speed**: Motor speed setting (0-255)
- **Start/Stop**: Motor control buttons

#### Logging
- **Checkboxes**: Enable/disable logging for P, I, D, S, L, O data
- **State Control**: Send "log [type] on/off" commands to robot

#### File Operations
- **Open**: Load parameters from JSON file
- **Save**: Save current parameters to current file
- **Save As**: Save parameters to new JSON file

#### Robot Communication
- **Read**: Fetch current parameters from robot
- **Write**: Send current parameters to robot

## Configuration Files

### Parameter File Format (JSON)
```json
{
  "pid_p": 1.1,
  "pid_i": 0.0,
  "pid_d": 5.1,
  "motor_speed": 58.0,
  "pid_p_max": 2.0,
  "pid_i_max": 100.0,
  "pid_d_max": 10.0,
  "motor_speed_max": 255.0,
  "time_window": 10.0,
  "time_window_max": 60.0,
  "log_p": false,
  "log_i": false,
  "log_d": false,
  "log_s": false,
  "log_l": false,
  "log_o": false
}
```

## Visual Elements

### Sensor Graph
- **Color Coding**: Blue→Green→Red gradient for sensor values
- **Spline Curves**: Smooth interpolation between sensor readings
- **Value Labels**: Individual sensor values displayed above each point
- **Line Position Indicator**: Yellow dashed vertical line showing detected line
- **Position Bar**: Horizontal indicator with -127 to +127 scale

### Time-Series Plotter
- **L Values**: Yellow line showing line position over time
- **O Values**: Cyan line showing PID output over time
- **Grid Lines**: Horizontal grid with numeric labels
- **Time Scale**: X-axis showing relative time from start
- **Legend**: Clear identification of L and O data streams

## Serial Communication

### Auto-Detection
- Scans all available serial ports
- Validates data by checking for expected message patterns
- Automatically connects to ports sending valid sensor/line data
- Handles connection drops with automatic reconnection

### Port Selection
- Prioritizes specified port if provided via command line
- Fallback to automatic detection if no valid data found
- Status updates shown in control panel

### Error Handling
- Graceful handling of connection failures
- Automatic port rescan when no valid data detected
- Prevents application crashes from serial errors

## Development

### Adding New Message Types
1. Define regex pattern in `robot_data_regex.py`
2. Add parsing logic in `robot_data_parser.py`
3. Register callback in main application
4. Update UI components as needed

### Extending Visualizations
1. Add new rendering class (e.g., `CustomGraphRenderer`)
2. Integrate into main application layout
3. Connect to data parser callbacks

### Custom Parameter Types
1. Update `ControlPanel` with new controls
2. Add to parameter dictionary methods
3. Extend file manager for new parameter types
4. Update robot communication protocol

## Troubleshooting

### Connection Issues
- **No ports found**: Check USB connections and driver installation
- **No valid data**: Verify robot is sending correct message formats
- **Frequent disconnections**: Check cable connections and baudrate settings

### Display Issues
- **Graph not updating**: Verify serial data is being received
- **Out of range values**: Adjust slider maximum values in control panel
- **Performance issues**: Reduce time window or data sampling rate

### Parameter Synchronization
- **Robot not responding**: Check serial connection and command format
- **Values not updating**: Verify robot firmware supports parameter commands
- **File loading errors**: Check JSON file format and parameter names

## File Structure

```
tools/line_sensor_app/
├── line_sensor_app.py          # Main application entry point
├── robot_serial_manager.py     # Serial communication handler
├── robot_data_parser.py        # Message parsing and callbacks
├── sensor_graph_renderer.py    # Real-time sensor visualization
├── time_series_plotter.py      # Time-series data plotting
├── robot_control_panel.py      # Interactive GUI controls
├── parameter_file_manager.py   # JSON parameter file operations
├── robot_parameter_communicator.py  # Robot parameter exchange
├── robot_data_regex.py         # Message format validation
├── example.json                # Sample parameter configuration
└── README.md                   # This documentation
```

## License

This application is part of the Jerry robot line-following project. See main project license for details.

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit pull request

## Support

For issues and questions:
1. Check this README for common solutions
2. Review code comments for implementation details
3. Open issue with detailed problem description and logs