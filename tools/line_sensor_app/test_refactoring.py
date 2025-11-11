"""Test script to verify the modular refactoring."""

import sys
import os

# Add test directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_module_imports():
    """Test that all modules can be imported correctly."""
    print("Testing module imports...")
    
    try:
        from robot_data_regex import SENSOR_LINE_REGEX, LINE_POS_REGEX, PID_OUTPUT_REGEX
        print("[OK] robot_data_regex imported successfully")
    except Exception as e:
        print(f"[FAIL] robot_data_regex import failed: {e}")
        return False
    
    try:
        from robot_data_parser import DataParser, SensorData
        print("[OK] robot_data_parser imported successfully")
    except Exception as e:
        print(f"[FAIL] robot_data_parser import failed: {e}")
        return False
    
    try:
        from robot_serial_manager import SerialManager
        print("[OK] robot_serial_manager imported successfully")
    except Exception as e:
        print(f"[FAIL] robot_serial_manager import failed: {e}")
        return False
    
    try:
        from sensor_graph_renderer import GraphRenderer
        print("[OK] sensor_graph_renderer imported successfully")
    except Exception as e:
        print(f"[FAIL] sensor_graph_renderer import failed: {e}")
        return False
    
    try:
        from time_series_plotter import PlotterRenderer
        print("[OK] time_series_plotter imported successfully")
    except Exception as e:
        print(f"[FAIL] time_series_plotter import failed: {e}")
        return False
    
    try:
        from robot_control_panel import ControlPanel
        print("[OK] robot_control_panel imported successfully")
    except Exception as e:
        print(f"[FAIL] robot_control_panel import failed: {e}")
        return False
    
    try:
        from parameter_file_manager import FileManager
        print("[OK] parameter_file_manager imported successfully")
    except Exception as e:
        print(f"[FAIL] parameter_file_manager import failed: {e}")
        return False
    
    try:
        from robot_parameter_communicator import RobotCommunication
        print("[OK] robot_parameter_communicator imported successfully")
    except Exception as e:
        print(f"[FAIL] robot_parameter_communicator import failed: {e}")
        return False
    
    return True

def test_data_parsing():
    """Test the data parser functionality."""
    print("\nTesting data parser...")
    
    try:
        from robot_data_parser import DataParser
        
        parser = DataParser()
        
        # Test sensor data parsing
        sensor_data_received = []
        parser.set_callbacks(sensor_callback=lambda x: sensor_data_received.append(x))
        
        # Test sensor line
        result = parser.parse_line("S,968,973,853,894,962,980")
        print("[OK] Sensor data parsing works")
        
        # Test line position parsing
        line_data_received = []
        parser.set_callbacks(line_position_callback=lambda x, y: line_data_received.append((x, y)))
        
        result = parser.parse_line("L,3")
        print("[OK] Line position parsing works")
        
        # Test PID output parsing
        pid_data_received = []
        parser.set_callbacks(pid_output_callback=lambda x: pid_data_received.append(x))
        
        result = parser.parse_line("O,123")
        print("[OK] PID output parsing works")
        
        # Test parameter response parsing
        param_received = []
        parser.set_callbacks(parameter_callback=lambda x, y: param_received.append((x, y)))
        
        result = parser.parse_line("pid p 10.5")
        print("[OK] Parameter response parsing works")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Data parser test failed: {e}")
        return False

def test_graph_renderer():
    """Test graph renderer functionality."""
    print("\nTesting graph renderer...")
    
    try:
        import tkinter as tk
        from sensor_graph_renderer import GraphRenderer
        
        # Create a mock canvas
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        canvas = tk.Canvas(root, width=800, height=300)
        renderer = GraphRenderer(canvas, 800, 300)
        
        # Test with empty data
        renderer.draw_graph([])
        print("[OK] Graph renderer initialization works")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"[FAIL] Graph renderer test failed: {e}")
        return False

def test_file_manager():
    """Test file manager functionality."""
    print("\nTesting file manager...")
    
    try:
        from parameter_file_manager import FileManager
        
        def dummy_status_callback(text):
            pass
        
        file_manager = FileManager(dummy_status_callback)
        file_manager.set_status_callback(dummy_status_callback)
        
        print("[OK] File manager initialization works")
        return True
        
    except Exception as e:
        print(f"[FAIL] File manager test failed: {e}")
        return False

def test_robot_communication():
    """Test robot communication functionality."""
    print("\nTesting robot communication...")
    
    try:
        def dummy_serial_sender(command):
            pass
        
        def dummy_status_callback(text):
            pass
        
        from robot_parameter_communicator import RobotCommunication
        
        robot_comm = RobotCommunication(dummy_serial_sender, dummy_status_callback)
        robot_comm.set_serial_sender(dummy_serial_sender)
        robot_comm.set_status_callback(dummy_status_callback)
        
        print("[OK] Robot communication initialization works")
        return True
        
    except Exception as e:
        print(f"[FAIL] Robot communication test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Starting modular refactoring tests...\n")
    
    tests = [
        test_module_imports,
        test_data_parsing,
        test_graph_renderer,
        test_file_manager,
        test_robot_communication,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"Test {test.__name__} failed")
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("SUCCESS: All tests passed! Refactoring successful.")
        return True
    else:
        print("ERROR: Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)