"""Regex patterns for parsing sensor data from the robot."""

import re

# Regex patterns for sensor data (S prefix), line position (L prefix), and PID output (O prefix)
# Format: S,968,973,... or L,3 or L,-3 (for negative values) or O,123 (PID output)
SENSOR_LINE_REGEX = re.compile(r"^S\s*,?\s*\d+(?:\s*,\s*\d+)*\s*$")
LINE_POS_REGEX = re.compile(r"^L\s*,?\s*-?\d+\s*$")
PID_OUTPUT_REGEX = re.compile(r"^O\s*,?\s*-?\d+\s*$")