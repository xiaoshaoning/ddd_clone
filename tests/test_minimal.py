#!/usr/bin/env python3
"""
Minimal test for GUI functionality.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

# Add parent directory to path (ddd_clone is in the parent)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ddd_clone.gui.main_window import MainWindow
from ddd_clone.gdb.gdb_controller import GDBController


def test_minimal():
    """Minimal GUI test."""
    app = QApplication(sys.argv)

    # Initialize GDB controller
    gdb_controller = GDBController()

    # Create main window
    window = MainWindow(gdb_controller)

    # Test loading source code
    test_file = "../examples/simple_program.c"
    if os.path.exists(test_file):
        try:
            window.source_viewer.load_source_file(test_file)
            print(f"[OK] Loaded source file: {test_file}")
        except Exception as e:
            print(f"[ERROR] Failed to load source: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"[ERROR] Test file not found: {test_file}")

    print("[OK] GUI setup completed")


if __name__ == "__main__":
    test_minimal()