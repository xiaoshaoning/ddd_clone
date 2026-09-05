#!/usr/bin/env python3
"""
Simple pytest smoke test for GUI functionality.

As a pytest test this sets up the window without blocking. Running it as a
script (python tests/test_gui.py) additionally enters the Qt event loop.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

# Add parent directory to path (ddd_clone is in the parent)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ddd_clone.gui.main_window import MainWindow
from ddd_clone.gdb.gdb_controller import GDBController


def test_gui():
    """Test the GUI functionality."""
    app = QApplication.instance() or QApplication(sys.argv)

    # Initialize GDB controller
    gdb_controller = GDBController()

    # Create main window
    window = MainWindow(gdb_controller)
    window.show()

    # Test loading source code
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'simple_program.c')
    if os.path.exists(test_file):
        window.source_viewer.load_source_file(test_file)
        print(f"Loaded source file: {test_file}")
    else:
        print(f"Test file not found: {test_file}")

    print("GUI test completed successfully")
    print("Window should be visible with source code")


if __name__ == "__main__":
    test_gui()
    app = QApplication.instance() or QApplication(sys.argv)
    sys.exit(app.exec_())
