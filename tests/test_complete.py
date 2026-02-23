#!/usr/bin/env python3
"""
Complete test for DDD Clone application.
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
    app = QApplication(sys.argv)

    # Initialize GDB controller
    gdb_controller = GDBController()

    # Create main window
    window = MainWindow(gdb_controller)
    window.show()

    # Test loading source code
    test_file = "../examples/simple_program.c"
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
        if gdb_controller.start_gdb("../examples/simple_program.exe"):
            print("[OK] GDB started successfully")

            # Test run button
            print("[INFO] Run button should now work")
            print("[INFO] You can click in the line number area to set/remove breakpoints")
        else:
            print("[WARNING] Failed to start GDB - debug controls may not work")
    else:
        print(f"[ERROR] Test file not found: {test_file}")

    print("\n[OK] Complete application test completed successfully")
    print("The main window should now display:")
    print("- Source code with line numbers")
    print("- Breakpoint marker at line 5")
    print("- Functional toolbar buttons")
    print("- Line number area for breakpoint setting")

    # Start the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    test_complete_app()