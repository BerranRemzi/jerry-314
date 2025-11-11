"""Time-series plotter renderer for L and O values."""

import time
import threading
import tkinter as tk
from typing import List, Optional, Tuple
from collections import deque


class PlotterRenderer:
    """Handles rendering of time-series plot for L and O values."""
    
    def __init__(self, canvas: tk.Canvas, width: int = 800, height: int = 200):
        self.canvas = canvas
        self.plotter_canvas_width = width
        self.plotter_canvas_height = height
        self.plotter_data_lock = threading.Lock()
        self.plotter_data: deque = deque(maxlen=10000)  # Limit to prevent memory issues
        self.plotter_start_time: Optional[float] = None
        self.plotter_time_window = tk.DoubleVar(value=10.0)  # Time window in seconds
        self.plotter_time_window_max = tk.DoubleVar(value=60.0)  # Max time window in seconds
    
    def set_time_window(self, time_window: float) -> None:
        """Set the time window for plotting."""
        if time_window > 0:
            self.plotter_time_window.set(time_window)
    
    def set_time_window_max(self, max_time: float) -> None:
        """Set the maximum time window."""
        if max_time > 0:
            self.plotter_time_window_max.set(max_time)
    
    def get_time_window(self) -> float:
        """Get current time window."""
        return self.plotter_time_window.get()
    
    def get_time_window_max(self) -> float:
        """Get maximum time window."""
        return self.plotter_time_window_max.get()
    
    def add_data_point(self, l_value: Optional[int], o_value: Optional[int]) -> None:
        """Add L or O value to plotter time-series data."""
        current_time = time.time()
        if self.plotter_start_time is None:
            self.plotter_start_time = current_time
        
        with self.plotter_data_lock:
            relative_time = current_time - self.plotter_start_time
            self.plotter_data.append((relative_time, l_value, o_value))
    
    def draw_plotter(self) -> None:
        """Draw time-series plotter for L (line position) and O (PID output) values."""
        self.canvas.delete("all")
        
        with self.plotter_data_lock:
            data = list(self.plotter_data)
        
        if not data:
            width = self.canvas.winfo_width() or self.plotter_canvas_width
            height = self.canvas.winfo_height() or self.plotter_canvas_height
            self.canvas.create_text(
                width / 2,
                height / 2,
                text="Waiting for L (line position) and O (PID output) data...",
                fill="#888",
                font=("Segoe UI", 12),
            )
            return
        
        width = self.canvas.winfo_width() or self.plotter_canvas_width
        height = self.canvas.winfo_height() or self.plotter_canvas_height
        
        margin = 50
        usable_width = max(width - margin * 2, 10)
        usable_height = max(height - margin * 2, 10)
        
        # Filter data based on time window - show only the most recent time_window seconds
        time_window = self.plotter_time_window.get()
        filtered_data = []
        times = []
        l_values = []
        o_values = []
        
        if time_window > 0 and data:
            # Find max time first (most recent data point)
            max_time = None
            for d in data:
                if d[0] is not None:
                    if max_time is None or d[0] > max_time:
                        max_time = d[0]
            
            if max_time is not None:
                # Define the visible time range: from (max_time - time_window) to max_time
                time_min_visible = max_time - time_window
                time_max_visible = max_time
                
                # Filter data to show only points within the visible time window
                for d in data:
                    t, l_val, o_val = d
                    if t is not None and time_min_visible <= t <= time_max_visible:
                        filtered_data.append(d)
                        times.append(t)
                        if l_val is not None:
                            l_values.append(l_val)
                        if o_val is not None:
                            o_values.append(o_val)
                
                # Use the defined time window for X-axis scaling
                time_min = time_min_visible
                time_max = time_max_visible
                time_range = time_window
            else:
                # No valid time data
                return
        else:
            # No time window filtering - show all data
            for d in data:
                t, l_val, o_val = d
                if t is not None:
                    filtered_data.append(d)
                    times.append(t)
                    if l_val is not None:
                        l_values.append(l_val)
                    if o_val is not None:
                        o_values.append(o_val)
            
            if not times:
                return
            
            time_min = min(times)
            time_max = max(times)
            time_range = max(time_max - time_min, 0.1)  # Avoid division by zero
        
        data = filtered_data
        
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
        
        self.canvas.create_line(graph_left, graph_bottom, graph_right, graph_bottom, fill="#444", width=1)
        self.canvas.create_line(graph_left, graph_top, graph_left, graph_bottom, fill="#444", width=1)
        
        # Draw grid lines and labels
        # Y-axis labels
        for i in range(5):
            y_val = combined_min + (combined_range * i / 4)
            y_pos = graph_bottom - (i / 4) * usable_height
            self.canvas.create_line(graph_left - 5, y_pos, graph_left, y_pos, fill="#555", width=1)
            self.canvas.create_text(
                graph_left - 8, y_pos,
                text=f"{int(y_val)}",
                fill="#aaa", font=("Segoe UI", 8),
                anchor="e"
            )
        
        # X-axis labels (time range)
        if time_range > 0:
            # Show time range on X-axis
            self.canvas.create_text(
                graph_left, graph_bottom + 20,
                text=f"{time_min:.1f}s",
                fill="#aaa", font=("Segoe UI", 8),
                anchor="w"
            )
            self.canvas.create_text(
                graph_right, graph_bottom + 20,
                text=f"{time_max:.1f}s",
                fill="#aaa", font=("Segoe UI", 8),
                anchor="e"
            )
            # Show time window in center
            self.canvas.create_text(
                (graph_left + graph_right) / 2, graph_bottom + 20,
                text=f"Window: {time_window:.1f}s",
                fill="#aaa", font=("Segoe UI", 8),
                anchor="center"
            )
        
        # Draw L values (line position) in yellow - draw all points, no sampling
        l_points = []
        o_points = []
        
        # Draw all data points - no filtering or sampling
        for t, l_val, o_val in data:
            if t is not None:
                x = graph_left + ((t - time_min) / time_range) * usable_width
                if l_val is not None:
                    y = graph_bottom - ((l_val - combined_min) / combined_range) * usable_height
                    l_points.append((x, y))
                if o_val is not None:
                    y = graph_bottom - ((o_val - combined_min) / combined_range) * usable_height
                    o_points.append((x, y))
        
        # Draw lines more efficiently - use polyline for better performance
        if len(l_points) > 1:
            # Draw L line (yellow) - use polyline
            coords = []
            for x, y in l_points:
                coords.extend([x, y])
            if len(coords) >= 4:  # At least 2 points
                self.canvas.create_line(*coords, fill="#ffff00", width=2, smooth=False)
        
        if len(o_points) > 1:
            # Draw O line (cyan) - use polyline
            coords = []
            for x, y in o_points:
                coords.extend([x, y])
            if len(coords) >= 4:  # At least 2 points
                self.canvas.create_line(*coords, fill="#00ffff", width=2, smooth=False)
        
        # Draw legend
        legend_y = graph_top + 15
        if l_values:
            self.canvas.create_line(
                graph_left + 10, legend_y,
                graph_left + 30, legend_y,
                fill="#ffff00", width=2
            )
            self.canvas.create_text(
                graph_left + 35, legend_y,
                text="L (Line Position)",
                fill="#ffff00", font=("Segoe UI", 9),
                anchor="w"
            )
        
        if o_values:
            legend_offset = 150 if l_values else 10
            self.canvas.create_line(
                graph_left + legend_offset, legend_y,
                graph_left + legend_offset + 20, legend_y,
                fill="#00ffff", width=2
            )
            self.canvas.create_text(
                graph_left + legend_offset + 25, legend_y,
                text="O (PID Output)",
                fill="#00ffff", font=("Segoe UI", 9),
                anchor="w"
            )
    
    def clear_data(self) -> None:
        """Clear all plotter data."""
        with self.plotter_data_lock:
            self.plotter_data.clear()
            self.plotter_start_time = None