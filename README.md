# Line Sensor Graph - Serial Communication Protocol

This document describes all commands that can be sent to the robot and all data formats that can be received from the robot by `line_sensor_app.py`.

## Commands Sent to Robot

All commands are sent as text strings terminated with a newline character (`\n`).

### PID Control Commands

#### Set PID Parameters
- `pid p <value>` - Set PID P coefficient
  - Example: `pid p 10.5`
  - Value: Float number (typically 0.0 to 100.0, but max is configurable)

- `pid i <value>` - Set PID I coefficient
  - Example: `pid i 5.2`
  - Value: Float number (typically 0.0 to 100.0, but max is configurable)

- `pid d <value>` - Set PID D coefficient
  - Example: `pid d 2.1`
  - Value: Float number (typically 0.0 to 100.0, but max is configurable)

#### Read PID Parameters
- `pid p ?` - Read current PID P coefficient
- `pid i ?` - Read current PID I coefficient
- `pid d ?` - Read current PID D coefficient

The robot should respond with: `pid p <value>`, `pid i <value>`, or `pid d <value>` respectively.

### Motor Control Commands

#### Set Motor Speed
- `motor speed <value>` - Set base motor speed
  - Example: `motor speed 100`
  - Value: Integer (typically 0 to 255, but max is configurable)

#### Read Motor Speed
- `motor speed ?` - Read current motor speed

The robot should respond with: `motor speed <value>`

#### Motor Start/Stop
- `motor start` - Start the motor
- `motor stop` - Stop the motor

### Logging Control Commands

Enable or disable logging of specific data types:

- `log p on` - Enable logging of PID P values
- `log p off` - Disable logging of PID P values
- `log i on` - Enable logging of PID I values
- `log i off` - Disable logging of PID I values
- `log d on` - Enable logging of PID D values
- `log d off` - Disable logging of PID D values
- `log s on` - Enable logging of sensor values (S format)
- `log s off` - Disable logging of sensor values
- `log l on` - Enable logging of line position (L format)
- `log l off` - Disable logging of line position
- `log o on` - Enable logging of PID output (O format)
- `log o off` - Disable logging of PID output

**Default Logging States:**
- Sensor values (S): **Enabled** by default
- Line position (L): **Enabled** by default
- PID output (O): **Enabled** by default
- PID P/I/D values: **Disabled** by default

**Note:** When PID P/I/D logging is enabled, values are logged at a maximum rate of once every 100ms to avoid excessive serial traffic.

## Data Received from Robot

All data is received as text lines terminated with a newline character (`\n`).

### Sensor Data Format

- `S,<value1>,<value2>,<value3>,...`
  - Example: `S,968,973,853,894,962,980`
  - Format: Letter 'S' followed by comma-separated integer values
  - Whitespace around commas is allowed: `S, 968 , 973 , 853`
  - Used for: Sensor array readings (e.g., line sensor values)

### Line Position Format

- `L,<value>`
  - Example: `L,3` (positive position)
  - Example: `L,-3` (negative position)
  - Example: `L,0` (center)
  - Format: Letter 'L' followed by comma and integer value
  - Range: Typically -127 to +127 (clamped automatically)
  - Whitespace allowed: `L, 3` or `L , -5`
  - Used for: Detected line position relative to center

### PID Output Format

- `O,<value>`
  - Example: `O,123`
  - Example: `O,-50`
  - Format: Letter 'O' followed by comma and integer value
  - Whitespace allowed: `O, 123` or `O , -50`
  - Used for: PID regulator output value

### Parameter Response Format

When reading parameters (using `?`), the robot responds with:

- `pid p <value>` - Response to `pid p ?`
  - Example: `pid p 10.500`
  - Format: Three space-separated tokens: "pid", "p"/"i"/"d", and float value (3 decimal places)

- `pid i <value>` - Response to `pid i ?`
  - Example: `pid i 5.200`

- `pid d <value>` - Response to `pid d ?`
  - Example: `pid d 2.100`

- `motor speed <value>` - Response to `motor speed ?`
  - Example: `motor speed 100`
  - Format: Three space-separated tokens: "motor", "speed", and integer value

### System Commands

- `help` or `?` - Display available commands and usage
  - Example: `help`
  - The robot responds with a list of all available commands

- `bootloader` - Jump to bootloader mode
  - Example: `bootloader`
  - **Warning:** This command will restart the device in bootloader mode

## Communication Settings

- **Baudrate**: 115200 (default, configurable via command line)
- **Timeout**: 0.1 seconds (read timeout)
- **Line Ending**: `\n` (newline character)

## Usage Example

### Sending Commands
```
help
pid p 10.5
pid i 5.2
pid d 2.1
pid p ?
motor speed 100
motor speed ?
motor start
motor stop
log s on
log l on
log o on
log p on
```

### Receiving Data
```
S,968,973,853,894,962,980
L,3
O,123
S,970,975,860,900,965,985
L,-5
O,-50
```

## Error Handling

If a command is invalid or missing required arguments, the robot will respond with a usage message:
- `Usage: pid <p|i|d> <value> or pid <p|i|d> ?`
- `Usage: motor <speed|start|stop> [value|?]`
- `Usage: log <type> <on|off>`
- `Unknown command: <command>` - For unrecognized commands

## Notes

- All commands are case-sensitive
- Commands must end with a newline (`\n`)
- Commands are parsed using space-separated arguments (e.g., `pid p 10.5` has three tokens: "pid", "p", "10.5")
- Whitespace around commas in data formats is optional but recommended for consistency
- The Python GUI program automatically scans for valid serial ports and connects when it detects data matching the expected formats
- Parameter read responses update the GUI automatically when received
- Multiple data formats can be sent in any order and will be parsed accordingly
- Invalid parameter types (e.g., `pid x 10`) will result in an error message

