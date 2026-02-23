#!/usr/bin/env python3
"""
Simple test script to verify GUI functionality.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from ddd_clone.gui.main_window import MainWindow
from ddd_clone.gdb.gdb_controller import GDBController


def test_gui():
    """Test the GUI functionality."""
    app = QApplication(sys.argv)

    # Initialize GDB controller
    gdb_controller = GDBController()

    # Create main window
    window = MainWindow(gdb_controller)
    window.show()

    # Test loading source code
    test_file = "examples/simple_program.c"
    if os.path.exists(test_file):
        window.source_viewer.load_source_file(test_file)
        print(f"Loaded source file: {test_file}")
    else:
        print(f"Test file not found: {test_file}")

    print("GUI test completed successfully")
    print("Window should be visible with source code")

    # Start the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    test_gui()