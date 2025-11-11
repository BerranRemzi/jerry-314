"""File manager for handling parameter file operations."""

import json
import tkinter as tk
from tkinter import filedialog
from typing import Dict, Any, Optional, Callable


class FileManager:
    """Handles file operations for parameter saving and loading."""
    
    def __init__(self, status_callback: Optional[Callable[[str], None]] = None):
        self.current_file_path: Optional[str] = None
        self.status_callback = status_callback
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback function for status updates."""
        self.status_callback = callback
    
    def _set_status_text(self, text: str) -> None:
        """Update status text through callback."""
        if self.status_callback:
            self.status_callback(text)
    
    def open_parameters_file(self) -> Dict[str, Any]:
        """Open a parameters JSON file.
        
        Returns:
            Dictionary with parameters, or empty dict if cancelled
        """
        file_path = filedialog.askopenfilename(
            title="Open Parameters",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    params = json.load(f)
                self.current_file_path = file_path
                self._set_status_text(f"Loaded parameters from {file_path}")
                return params
            except Exception as e:
                self._set_status_text(f"Error loading file: {str(e)}")
                return {}
        
        return {}
    
    def save_parameters_file(self, params: Dict[str, Any]) -> bool:
        """Save parameters to current file path.
        
        Args:
            params: Dictionary of parameters to save
            
        Returns:
            True if successful, False otherwise
        """
        if self.current_file_path:
            return self._save_to_file(self.current_file_path, params)
        else:
            return self.save_parameters_file_as(params)
    
    def save_parameters_file_as(self, params: Dict[str, Any]) -> bool:
        """Save parameters to a new file.
        
        Args:
            params: Dictionary of parameters to save
            
        Returns:
            True if successful, False otherwise
        """
        file_path = filedialog.asksaveasfilename(
            title="Save Parameters As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            return self._save_to_file(file_path, params)
        
        return False
    
    def _save_to_file(self, file_path: str, params: Dict[str, Any]) -> bool:
        """Save parameters to a specific file path.
        
        Args:
            file_path: Path to save the file
            params: Dictionary of parameters to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(params, f, indent=2)
            self.current_file_path = file_path
            self._set_status_text(f"Saved parameters to {file_path}")
            return True
        except Exception as e:
            self._set_status_text(f"Error saving file: {str(e)}")
            return False
    
    def get_current_file_path(self) -> Optional[str]:
        """Get the current file path."""
        return self.current_file_path
    
    def set_current_file_path(self, file_path: Optional[str]) -> None:
        """Set the current file path."""
        self.current_file_path = file_path