"""Graph renderer for displaying sensor data visualizations."""

import tkinter as tk
from typing import List, Optional, Tuple
from robot_data_parser import SensorData


class GraphRenderer:
    """Handles rendering of sensor data graphs."""
    
    def __init__(self, canvas: tk.Canvas, width: int = 800, height: int = 300):
        self.canvas = canvas
        self.canvas_width = width
        self.canvas_height = height
        self.line_position: Optional[float] = None
        self.line_position_raw: Optional[int] = None
        self.max_value_seen: int = 1
    
    def update_line_position(self, normalized_position: float, raw_position: int) -> None:
        """Update line position information for rendering."""
        self.line_position = normalized_position
        self.line_position_raw = raw_position
    
    def update_sensor_data(self, sensor_data: SensorData) -> None:
        """Update sensor data for rendering."""
        self.line_position = sensor_data.line_position
        self.line_position_raw = sensor_data.line_position_raw
        self.max_value_seen = sensor_data.max_value_seen
    
    def draw_graph(self, sensor_values: List[int]) -> None:
        """Draw the sensor graph with current data."""
        self.canvas.delete("all")

        values = sensor_values
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
                                values: List[int], max_value: int) -> List[Tuple[float, float, float]]:
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
    
    def _draw_spline_curve(self, spline_points: List[Tuple[float, float, float]]) -> None:
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
    
    def _draw_placeholder(self) -> None:
        """Draw placeholder text when no data is available."""
        width = self.canvas.winfo_width() or self.canvas_width
        height = self.canvas.winfo_height() or self.canvas_height
        self.canvas.create_text(
            width / 2,
            height / 2,
            text="Waiting for sensor data (S...) or line position (L...)...",
            fill="#888",
            font=("Segoe UI", 14),
        )
    
    def _value_to_color(self, normalized: float) -> str:
        """Map 0..1 to a blue→green→red gradient."""
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