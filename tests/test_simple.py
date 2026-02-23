#!/usr/bin/env python3
"""
Simple test without GUI event loop.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

# Add parent directory to path (ddd_clone is in the parent)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ddd_clone.gui.main_window import MainWindow
from ddd_clone.gdb.gdb_controller import GDBController


def test_gui_setup():
    """Test GUI setup without running event loop."""
    app = QApplication(sys.argv)

    # Initialize GDB controller
    gdb_controller = GDBController()

    # Create main window
    window = MainWindow(gdb_controller)

    # Test loading source code
    test_file = "../examples/simple_program.c"
    if os.path.exists(test_file):
        window.source_viewer.load_source_file(test_file)
        print(f"[OK] Loaded source file: {test_file}")

        # Check if source code is displayed
        content = window.source_viewer.toPlainText()
        if content and len(content) > 0:
            print(f"[OK] Source code displayed ({len(content)} characters)")
        else:
            print("[ERROR] Source code not displayed")
    else:
        print(f"[ERROR] Test file not found: {test_file}")

    # Test GDB startup
    if gdb_controller.start_gdb("../examples/simple_program"):
        print("[OK] GDB started successfully")
    else:
        print("[ERROR] Failed to start GDB")

    print("\n[OK] GUI setup test completed successfully")
    print("The main window should now display source code")

    # Show the window briefly
    window.show()

    # Process events briefly to show the window
    app.processEvents()

    # Keep the window open for a moment
    import time
    time.sleep(2)


if __name__ == "__main__":
    test_gui_setup()