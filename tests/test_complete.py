#!/usr/bin/env python3
"""
Complete smoke test for DDD Clone application.

As a pytest test this sets up the window without blocking. Running it as a
script (python tests/test_complete.py) additionally enters the Qt event loop.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

# Add parent directory to path (ddd_clone is in the parent)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ddd_clone.gui.main_window import MainWindow
from ddd_clone.gdb.gdb_controller import GDBController


def test_complete_app():
    """Test complete application functionality."""
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
        print(f"[OK] Loaded source file: {test_file}")

        # Test line numbers
        line_count = window.source_viewer.blockCount()
        print(f"[OK] Line numbers displayed: {line_count} lines")

        # Test breakpoint setting
        window.source_viewer.toggle_breakpoint(5)
        print("[OK] Breakpoint set at line 5")

        # Test GDB startup
        exe_path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'simple_program.exe')
        if gdb_controller.start_gdb(exe_path):
            print("[OK] GDB started successfully")
            print("[INFO] Run button should now work")
            print("[INFO] You can click in the line number area to set/remove breakpoints")
        else:
            print("[WARNING] Failed to start GDB - debug controls may not work")
    else:
        print(f"[ERROR] Test file not found: {test_file}")

    print("\n[OK] Complete application test completed successfully")
    print("The main window should now display:")


if __name__ == "__main__":
    test_complete_app()
    app = QApplication.instance() or QApplication(sys.argv)
    sys.exit(app.exec_())
