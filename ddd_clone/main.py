"""
Main entry point for the DDD Clone application.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication

from ddd_clone.gui.main_window import MainWindow
from ddd_clone.gdb.gdb_controller import GDBController


def main():
    """
    Main function to start the DDD Clone application.
    """
    app = QApplication(sys.argv)

    # Get program path from command line arguments
    program_path = None
    if len(sys.argv) > 1:
        program_path = sys.argv[1]

    # Initialize GDB controller
    gdb_controller = GDBController()

    # Create and show main window
    window = MainWindow(gdb_controller)
    window.show()

    # Start GDB and load program if provided
    if program_path:
        if not gdb_controller.start_gdb(program_path):
            print(f"Failed to start GDB with program: {program_path}")
            return 1
        # Load initial source code
        window.load_initial_source(program_path)

    # Start the application event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()