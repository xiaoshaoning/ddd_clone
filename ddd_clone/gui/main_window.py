"""
Main application window for DDD Clone.
"""

import os
from typing import Any
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItem, QToolBar,
    QAction, QStatusBar, QLabel, QMessageBox, QMenuBar, QMenu, QFileDialog,
    QLineEdit, QPushButton, QHBoxLayout, QToolTip, QDialog, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

from ..gdb.gdb_controller import GDBController
from .source_viewer import SourceViewer
from .breakpoint_manager import BreakpointManager
from .variable_inspector import VariableInspector


class MainWindow(QMainWindow):
    """
    Main window that contains all debugger components.
    """

    def __init__(self, gdb_controller: GDBController):
        super().__init__()
        self.gdb_controller = gdb_controller

        # Initialize managers
        self.breakpoint_manager = BreakpointManager(gdb_controller)
        self.variable_inspector = VariableInspector(gdb_controller)

        # Variable hover tracking
        self.pending_variable_queries = {}
        self.current_hover_variable = None

        # Register display settings
        self.register_format = "x"  # Default: hexadecimal
        self.previous_register_values = {}  # For change detection

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self) -> None:
        """Set up the main user interface."""
        self.setWindowTitle("DDD Clone - Graphical Debugger")
        # Position window above command window with larger size
        self.setGeometry(100, 50, 1400, 900)

        # Create central widget and main layout
        central_widget = QWidget()
        # Set background color to bean green (RGB: 202, 234, 206)
        central_widget.setStyleSheet("background-color: rgb(202, 234, 206);")
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel: Source code and execution control
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # Right panel: Debug information
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # Set initial splitter proportions
        splitter.setSizes([800, 400])

        # Create menu bar
        self.create_menu_bar()

        # Create toolbar
        self.create_toolbar()

        # Create status bar
        self.create_status_bar()

    def create_left_panel(self) -> None:
        """Create the left panel with source code and execution controls."""
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)

        # Source code viewer
        self.source_viewer = SourceViewer()
        layout.addWidget(self.source_viewer)

        return left_widget

    def create_right_panel(self) -> None:
        """Create the right panel with debug information."""
        right_widget = QWidget()
        layout = QVBoxLayout(right_widget)

        # Create vertical splitter for resizable panels
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)

        # Tab widget for different debug views
        tab_widget = QTabWidget()
        splitter.addWidget(tab_widget)

        # Variables tab
        self.variables_tree = QTreeWidget()
        self.variables_tree.setHeaderLabels(["Name", "Value", "Type"])
        self.variables_tree.setFont(QFont("Arial", 18))  # Larger font
        tab_widget.addTab(self.variables_tree, "Variables")

        # Watch expressions tab
        self.watch_tree = QTreeWidget()
        self.watch_tree.setHeaderLabels(["Expression", "Value"])
        self.watch_tree.setFont(QFont("Arial", 18))  # Larger font
        tab_widget.addTab(self.watch_tree, "Watch")

        # Breakpoints tab
        self.breakpoints_tree = QTreeWidget()
        self.breakpoints_tree.setHeaderLabels(["File", "Line", "Condition"])
        self.breakpoints_tree.setFont(QFont("Arial", 18))  # Larger font
        tab_widget.addTab(self.breakpoints_tree, "Breakpoints")

        # Watchpoints tab
        self.watchpoints_tree = QTreeWidget()
        self.watchpoints_tree.setHeaderLabels(["Expression", "Type", "Enabled"])
        self.watchpoints_tree.setFont(QFont("Arial", 18))  # Larger font
        self.watchpoints_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.watchpoints_tree.customContextMenuRequested.connect(self._show_watchpoints_context_menu)
        tab_widget.addTab(self.watchpoints_tree, "Watchpoints")

        # Registers tab
        self.registers_tree = QTreeWidget()
        self.registers_tree.setHeaderLabels(["Name", "Number", "Value"])
        self.registers_tree.setFont(QFont("Arial", 18))  # Larger font
        self.registers_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.registers_tree.customContextMenuRequested.connect(self._show_registers_context_menu)
        tab_widget.addTab(self.registers_tree, "Registers")

        # Call stack tab
        self.call_stack_tree = QTreeWidget()
        self.call_stack_tree.setHeaderLabels(["Function", "File", "Line"])
        self.call_stack_tree.setFont(QFont("Arial", 18))  # Larger font
        tab_widget.addTab(self.call_stack_tree, "Call Stack")

        # GDB output area
        gdb_output_widget = QWidget()
        gdb_output_layout = QVBoxLayout(gdb_output_widget)

        # GDB Command area
        gdb_command_layout = QHBoxLayout()
        gdb_output_layout.addLayout(gdb_command_layout)

        # GDB command input
        self.gdb_command_input = QLineEdit()
        self.gdb_command_input.setPlaceholderText("Enter GDB command...")
        self.gdb_command_input.setFont(QFont("Arial", 18))  # Larger font
        self.gdb_command_input.returnPressed.connect(self.execute_gdb_command)
        gdb_command_layout.addWidget(self.gdb_command_input)

        # Execute button
        self.gdb_execute_button = QPushButton("Execute")
        self.gdb_execute_button.setFont(QFont("Arial", 18))  # Larger font
        self.gdb_execute_button.clicked.connect(self.execute_gdb_command)
        gdb_command_layout.addWidget(self.gdb_execute_button)

        # GDB output text area
        self.gdb_output_text = QTextEdit()
        self.gdb_output_text.setReadOnly(True)
        self.gdb_output_text.setPlaceholderText("GDB output will appear here...")
        self.gdb_output_text.setFont(QFont("Courier New", 18))  # Larger font

        # Enable context menu for GDB output text area
        self.gdb_output_text.setContextMenuPolicy(Qt.CustomContextMenu)
        self.gdb_output_text.customContextMenuRequested.connect(self._show_gdb_output_context_menu)

        gdb_output_layout.addWidget(self.gdb_output_text)

        # Add GDB output area to splitter
        splitter.addWidget(gdb_output_widget)

        # Set initial splitter proportions (70% for tabs, 30% for GDB output)
        splitter.setSizes([700, 300])

        return right_widget

    def create_toolbar(self) -> None:
        """Create the main toolbar with debug controls."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        # Create font for toolbar actions
        toolbar_font = QFont("Arial", 18)

        # Load program action
        load_action = QAction("Load", self)
        load_action.setFont(toolbar_font)
        load_action.triggered.connect(self.open_program)
        toolbar.addAction(load_action)

        # Debug actions
        run_action = QAction("Run/Continue", self)
        run_action.setFont(toolbar_font)
        run_action.triggered.connect(self.run_or_continue)
        toolbar.addAction(run_action)

        pause_action = QAction("Pause", self)
        pause_action.setFont(toolbar_font)
        pause_action.triggered.connect(self.pause_program)
        toolbar.addAction(pause_action)

        step_over_action = QAction("Step Over", self)
        step_over_action.setFont(toolbar_font)
        step_over_action.triggered.connect(self.step_over)
        toolbar.addAction(step_over_action)

        step_into_action = QAction("Step Into", self)
        step_into_action.setFont(toolbar_font)
        step_into_action.triggered.connect(self.step_into)
        toolbar.addAction(step_into_action)

        step_out_action = QAction("Step Out", self)
        step_out_action.setFont(toolbar_font)
        step_out_action.triggered.connect(self.step_out)
        toolbar.addAction(step_out_action)

        # Add separator
        toolbar.addSeparator()

        # Watchpoint actions
        add_watchpoint_action = QAction("Add Watchpoint", self)
        add_watchpoint_action.setFont(toolbar_font)
        add_watchpoint_action.triggered.connect(self.add_watchpoint_dialog)
        toolbar.addAction(add_watchpoint_action)

        # Add separator
        toolbar.addSeparator()

        # Register format selection
        format_label = QLabel("Registers:")
        format_label.setFont(toolbar_font)
        toolbar.addWidget(format_label)

        self.register_format_combo = QComboBox()
        self.register_format_combo.setFont(toolbar_font)
        self.register_format_combo.addItems(["Hex", "Decimal", "Octal", "Binary"])
        self.register_format_combo.setCurrentText("Hex")
        self.register_format_combo.currentTextChanged.connect(self._on_register_format_changed)
        toolbar.addWidget(self.register_format_combo)

        # Add separator
        toolbar.addSeparator()

        # Quit and Exit buttons
        quit_action = QAction("Quit", self)
        quit_action.setFont(toolbar_font)
        quit_action.triggered.connect(self.quit_gdb_session)
        toolbar.addAction(quit_action)

        exit_action = QAction("Exit", self)
        exit_action.setFont(toolbar_font)
        exit_action.triggered.connect(self.close)
        toolbar.addAction(exit_action)

    def _on_register_format_changed(self, format_text: str) -> None:
        """Handle register format selection change."""
        format_map = {
            "Hex": "x",
            "Decimal": "d",
            "Octal": "o",
            "Binary": "b"
        }
        self.register_format = format_map.get(format_text, "x")
        # Update register display if program is stopped
        if self.gdb_controller.current_state['state'] == 'stopped':
            self._update_registers_tree()

    def create_menu_bar(self) -> None:
        """Create the menu bar."""
        # No menu bar needed - all functionality is in toolbar
        # Set menu bar to None to completely hide it
        self.setMenuBar(None)

    def create_status_bar(self) -> None:
        """Create the status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        # Status labels
        self.status_label = QLabel("Ready")
        status_bar.addWidget(self.status_label)

        self.current_file_label = QLabel("No file loaded")
        status_bar.addPermanentWidget(self.current_file_label)

    def connect_signals(self) -> None:
        """Connect signals from GDB controller to UI updates."""
        self.gdb_controller.state_changed.connect(self.update_ui_state)
        self.gdb_controller.output_received.connect(self.handle_gdb_output)

        # Connect source viewer signals
        self.source_viewer.breakpoint_toggled.connect(self.handle_breakpoint_toggle)
        self.source_viewer.variable_hovered.connect(self.handle_variable_hover)

        # Connect breakpoint manager signals
        self.breakpoint_manager.watchpoint_added.connect(self._update_watchpoints_tree)
        self.breakpoint_manager.watchpoint_removed.connect(self._update_watchpoints_tree)
        self.breakpoint_manager.watchpoint_updated.connect(self._update_watchpoints_tree)

    def run_or_continue(self) -> None:
        """Run program (if not started) or continue execution (if paused)."""
        try:
            # Check if GDB is running
            if not self.gdb_controller.gdb_process or self.gdb_controller.gdb_process.poll() is not None:
                QMessageBox.warning(self, "Warning", "GDB is not running. Please load a program first.")
                return

            # Check current state to decide whether to run or continue
            current_state = self.gdb_controller.current_state['state']

            if current_state == 'disconnected' or current_state == 'connected' or current_state == 'exited':
                # Program not started yet or has exited - run it
                if self.gdb_controller.run():
                    self.status_label.setText("Running program...")
                else:
                    QMessageBox.critical(self, "Error", "Failed to start program execution")
            elif current_state == 'stopped':
                # Program is paused - continue execution
                if self.gdb_controller.continue_execution():
                    self.status_label.setText("Continuing execution...")
                else:
                    QMessageBox.critical(self, "Error", "Failed to continue execution")
            elif current_state == 'running':
                # Program is already running
                pass
            else:
                # Unknown state
                QMessageBox.warning(self, "Warning", f"Cannot run/continue in state: {current_state}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run/continue program: {e}")

    def run_program(self) -> None:
        """Start program execution."""
        try:
            # Check if GDB is running
            if not self.gdb_controller.gdb_process or self.gdb_controller.gdb_process.poll() is not None:
                QMessageBox.warning(self, "Warning", "GDB is not running. Please load a program first.")
                return

            if self.gdb_controller.run():
                self.status_label.setText("Running program...")
            else:
                QMessageBox.critical(self, "Error", "Failed to start program execution")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run program: {e}")

    def pause_program(self) -> None:
        """Pause program execution."""
        try:
            self.gdb_controller.pause()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to pause program: {e}")

    def step_over(self) -> None:
        """Step over current line."""
        try:
            self.gdb_controller.step_over()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to step over: {e}")

    def step_into(self) -> None:
        """Step into function call."""
        try:
            self.gdb_controller.step_into()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to step into: {e}")

    def step_out(self) -> None:
        """Step out of current function."""
        try:
            self.gdb_controller.step_out()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to step out: {e}")

    def continue_execution(self) -> None:
        """Continue program execution."""
        try:
            self.gdb_controller.continue_execution()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to continue: {e}")

    def update_ui_state(self, state_info: dict) -> None:
        """Update UI based on current debugger state."""
        # Update status label
        state = state_info.get('state', 'unknown')
        self.status_label.setText(f"State: {state}")

        # Check if we have valid line information to highlight
        has_valid_line = ('file' in state_info and 'line' in state_info and
                         state_info['line'] is not None and state_info['line'] > 0)

        if has_valid_line and state == 'stopped':
            # Highlight current execution line in source viewer
            current_line = state_info['line']
            self.current_file_label.setText(f"{state_info['file']}:{current_line}")
            self.source_viewer.highlight_current_line(current_line)
        else:
            # Clear highlight when program exits or no valid line info
            self.source_viewer.clear_all_highlights()
            if 'file' in state_info and state_info['file']:
                self.current_file_label.setText(f"{state_info['file']}:??")
            else:
                self.current_file_label.setText("No file loaded")

        # Update registers and variables when program is stopped
        if state == 'stopped':
            self._update_registers_tree()
            self._update_variables_tree()

    def handle_gdb_output(self, output: str) -> None:
        """Handle output received from GDB."""
        # Process GDB output and update relevant UI components

        # Handle breakpoint creation from GDB commands
        self._handle_breakpoint_output(output)

        # Handle variable value extraction for tooltips
        self._handle_variable_output(output)

        # Display output in the GDB output area
        if hasattr(self, 'gdb_output_text'):
            # Clean up the output by removing GDB/MI prefixes
            clean_output = self._clean_gdb_output(output)
            if clean_output:
                self.gdb_output_text.append(clean_output)
                # Auto-scroll to bottom
                cursor = self.gdb_output_text.textCursor()
                cursor.movePosition(cursor.End)
                self.gdb_output_text.setTextCursor(cursor)

    def _clean_gdb_output(self, output: str) -> str:
        """Clean GDB/MI output by removing prefixes and formatting."""
        import re

        # First check if this is a variable print output or error message
        # Variable print output typically looks like: ~"$1 = 5"
        # Error messages typically start with ^error or &"Error

        # Extract the actual content regardless of prefix
        cleaned = ""
        if output.startswith('~') or output.startswith('&'):
            # Remove prefix and quotes for console output
            cleaned = output[2:-1] if output.endswith('"') else output[2:]
            # Remove escaped newlines
            cleaned = cleaned.replace('\\n', '\n')
            # Remove single quotes if they wrap the entire output
            if cleaned.startswith("'") and cleaned.endswith("'"):
                cleaned = cleaned[1:-1]
            # Remove escaped quotes and backslashes
            cleaned = cleaned.replace('\\"', '"').replace('\\\\', '\\')
        elif output.startswith('='):
            # MI result records - check if they contain variable values
            # Look for patterns like =thread-group-started or =breakpoint-created
            # We'll skip most of these unless they contain error information
            if 'error' in output.lower():
                # Extract error message from MI output
                cleaned = output
            else:
                return ""
        elif output.startswith('^'):
            # MI result records - check for errors
            if output.startswith('^error'):
                # This is an error message, extract it
                # Pattern: ^error,msg="Error message here"
                match = re.search(r'msg="([^"]+)"', output)
                if match:
                    error_msg = match.group(1)
                    # Filter out "Undefined MI command: exec-abort" error
                    if "Undefined MI command: exec-abort" in error_msg:
                        return ""
                    cleaned = f"Error: {error_msg}"
                else:
                    cleaned = "Error (no message)"
            else:
                # Skip other ^ records
                return ""
        elif output.strip() == '(gdb)':
            # Skip prompt
            return ""
        elif output.startswith('*'):
            # Async output like *running, *stopped
            # Skip these as they are not user-requested variable prints
            return ""
        else:
            # Other output - keep as-is but check if it's variable or error
            cleaned = output.strip()
            # Remove quotes
            if cleaned.startswith("'") and cleaned.endswith("'"):
                cleaned = cleaned[1:-1]
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            cleaned = cleaned.replace('\\"', '"').replace('\\\\', '\\')

        # Remove ANSI escape codes
        cleaned = self._remove_ansi_escape_codes(cleaned)

        # Check if this should be displayed (not filtered as noise)
        if self._should_filter_output(cleaned):
            return ""

        # Clean up quotes around source code lines if present
        cleaned = re.sub(r'"(\d+\\t.*?)"', r'\1', cleaned)

        # Process variable output (keep $number = prefix, remove quotes from value)
        variable_pattern = r'^\$\d+\s*='
        if re.search(variable_pattern, cleaned) is not None:
            # Strip whitespace (including newlines) from start and end
            cleaned = cleaned.strip()
            # Remove quotes from value part only (e.g., $1 = "value" -> $1 = value)
            # Match pattern: $number = "value" or $number = 'value'
            match = re.match(r'^(\$\d+\s*=\s*)([\'"]?)(.*?)\2$', cleaned)
            if match:
                # Reconstruct without quotes around value
                cleaned = match.group(1) + match.group(3)
            # Also handle cases where quotes might be around the whole output
            elif cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            elif cleaned.startswith("'") and cleaned.endswith("'"):
                cleaned = cleaned[1:-1]

        # For other outputs, just strip whitespace
        else:
            cleaned = cleaned.strip()
            # Remove surrounding quotes if present
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            elif cleaned.startswith("'") and cleaned.endswith("'"):
                cleaned = cleaned[1:-1]

        return cleaned

    def _should_filter_output(self, output: str) -> bool:
        """Check if output should be filtered out as noise."""
        if not output:
            return True

        # Common noise patterns (case-insensitive)
        noise_patterns = [
            r'^GNU gdb.*',
            r'^Copyright.*',
            r'^License GPL.*',
            r'^This is free software.*',
            r'^There is NO WARRANTY.*',
            r'^Type.*show copying.*',
            r'^Type.*show warranty.*',
            r'^This GDB was configured as.*',
            r'^Type.*show configuration.*',
            r'^For bug reporting instructions.*',
            r'^Find the GDB manual.*',
            r'^For help, type.*',
            r'^Type.*apropos word.*',
            r'^\s*$',  # Empty or whitespace-only lines
            # URLs related to GDB documentation and bug reporting
            r'^<https?://.*gnu\.org/software/gdb.*>.*',
            r'^<https?://www\.gnu\.org/software/gdb.*>.*',
            # General GDB info URLs
            r'^<https?://.*gnu\.org/licenses/.*>.*',
            # Lines that are just URLs in angle brackets
            r'^<[^>]*>\s*\.?$',
            # Incomplete lines from split output
            r'^Type\s*".*',
            r'^show copying.*',
            r'^<".*',
            r'.*gnu\.org/software/gdb.*',
            r'^".*',  # Lines that start with a quote
            # GDB/MI asynchronous notifications (technical details)
            r'^\*?running,thread-id=.*',
            r'^\*?stopped,reason=.*',
            r'^\*?breakpoint-hit,.*',
            r'^\*?thread-created,.*',
            r'^\*?thread-exited,.*',
            r'^\*?library-loaded,.*',
            r'^\*?library-unloaded,.*',
            # GDB/MI status messages with technical parameters
            r'.*thread-id="\d+".*',
            r'.*frame=\{.*',
            r'.*stopped-threads=.*',
            r'.*arch=".*".*',
        ]

        import re
        for pattern in noise_patterns:
            if re.match(pattern, output, re.IGNORECASE):
                return True

        # Also filter lines that are just punctuation or very short noise
        if re.match(r'^[\s\"\'\\]*$', output):
            return True

        # Filter GDB command echo (e.g., "p sum", "print fib_result")
        if re.match(r'^(p|print|break|watch|display|info|run|continue|next|step|finish|kill|quit)\s+', output, re.IGNORECASE):
            return True

        # Filter lines that contain command prompts but no actual output
        if re.match(r'^\(\w+\)\s*$', output):
            return True

        # Filter GDB help and info lines that may be split across multiple lines
        if re.match(r'^Type\s*".*', output, re.IGNORECASE):
            return True
        if re.match(r'^show\s+\w+.*', output, re.IGNORECASE):
            return True
        if re.match(r'.*for details.*', output, re.IGNORECASE):
            return True
        if re.match(r'.*for configuration details.*', output, re.IGNORECASE):
            return True
        if re.match(r'.*to search for commands.*', output, re.IGNORECASE):
            return True

        # Filter MI command responses (e.g., "1^done,register-names=...", "2^done,register-values=...")
        if re.match(r'^\d+\^done,.*', output):
            return True
        if re.match(r'^\d+\^error,.*', output):
            return True

        # Filter GDB status messages (but keep breakpoint hits and source lines per user request)
        if re.match(r'^Reading symbols from.*', output):
            return True
        if re.match(r'^\[New Thread.*\]', output):
            return True
        # Note: Thread hit Breakpoint and source code lines are kept - DO NOT filter them
        # if re.match(r'^Thread \d+ hit Breakpoint.*', output):
        #     return True
        # if re.match(r'^\d+\s+.*at .*:\d+', output):  # Source code lines like "33    fib_result = fibonacci(number);"
        #     return True
        # if re.match(r'.* at .*:\d+', output):  # Function at file:line
        #     return True

        # Filter empty or mostly empty Type messages
        if output.strip() == 'Type ""':
            return True
        if output.strip() == 'Type':
            return True
        if re.match(r'^Type\s*"?"?$', output):  # Type "" or Type "?"
            return True

        # Filter lines that are just punctuation, quotes, or very short
        if len(output.strip()) <= 3 and re.match(r'^[\s\"\'\\\.\?]*$', output):
            return True

        return False

    def _remove_ansi_escape_codes(self, text: str) -> str:
        """Remove ANSI escape sequences from text."""
        import re
        # 7-bit C1 ANSI sequences
        ansi_escape = re.compile(r'''
            \x1B  # ESC
            (?:   # 7-bit C1 Fe (except CSI)
                [@-Z\\-_]
            |     # or [ for CSI, followed by a control sequence
                \[
                [0-?]*  # Parameter bytes
                [ -/]*  # Intermediate bytes
                [@-~]   # Final byte
            )
        ''', re.VERBOSE)
        return ansi_escape.sub('', text)

    def _handle_breakpoint_output(self, output: str) -> None:
        """Handle GDB output related to breakpoint creation."""
        import re

        # Look for breakpoint creation messages
        # Examples: "Breakpoint 1 at 0x401530: file simple_program.c, line 5."
        # Or: "Breakpoint 1, main () at simple_program.c:5"

        # Pattern for breakpoint creation
        bp_pattern1 = r'Breakpoint (\d+) at .* file ([^,]+), line (\d+)'
        bp_pattern2 = r'Breakpoint (\d+), .* at ([^:]+):(\d+)'

        match1 = re.search(bp_pattern1, output)
        match2 = re.search(bp_pattern2, output)

        if match1:
            bp_id = int(match1.group(1))
            file_path = match1.group(2)
            line_number = int(match1.group(3))
            self._add_breakpoint_visual_marker(file_path, line_number)
        elif match2:
            bp_id = int(match2.group(1))
            file_path = match2.group(2)
            line_number = int(match2.group(3))
            self._add_breakpoint_visual_marker(file_path, line_number)

    def _add_breakpoint_visual_marker(self, file_path: str, line_number: int) -> None:
        """Add visual breakpoint marker if the file matches current source."""
        if (hasattr(self.source_viewer, 'current_file') and
            self.source_viewer.current_file and
            file_path in self.source_viewer.current_file):

            # Add visual marker
            self.source_viewer.add_breakpoint_marker(line_number)

    def _handle_variable_output(self, output: str) -> None:
        """Extract variable values from GDB output for tooltips."""
        import re

        # Check if this output contains a variable value from a pending query
        if not self.pending_variable_queries or not self.current_hover_variable:
            return

        # Skip error messages
        if output.startswith('^error'):
            # Remove from pending queries without updating tooltip
            if self.current_hover_variable in self.pending_variable_queries:
                del self.pending_variable_queries[self.current_hover_variable]
                # Hide tooltip for errors
                QToolTip.hideText()
            return

        # Pattern to match GDB print output like "$1 = 5" or "$272 = 5"
        # Also handles arrays and structures
        value_pattern = r'=\s*(.+)'

        match = re.search(value_pattern, output)
        if match:
            variable_value = match.group(1).strip()
            # Clean up the value: remove quotes and escape sequences
            # Remove all double quotes (not just surrounding)
            variable_value = variable_value.replace('"', '')
            # Remove any remaining "= " prefix just in case
            if variable_value.startswith('= '):
                variable_value = variable_value[2:]
            elif variable_value.startswith('='):
                variable_value = variable_value[1:]
            # Handle escape sequences - both literal backslash-n and actual newlines
            variable_value = variable_value.replace('\\n', '').replace('\\r', '').replace('\\t', ' ')
            variable_value = variable_value.replace('\n', '').replace('\r', '')
            # Also handle escaped backslashes and quotes
            variable_value = variable_value.replace('\\\\', '').replace('\\"', '')
            # Collapse multiple spaces and trim
            variable_value = ' '.join(variable_value.split())
            # Final trim
            variable_value = variable_value.strip()

            # Skip function addresses (e.g., "{int (void)} 0x7ff7625314fd <main>")
            # This pattern matches function type signatures
            if re.match(r'^\{.*\}.*<.*>$', variable_value):
                # Remove from pending queries without updating tooltip
                if self.current_hover_variable in self.pending_variable_queries:
                    del self.pending_variable_queries[self.current_hover_variable]
                    # Hide tooltip for function addresses
                    QToolTip.hideText()
                return

            # Check if this is for our current hover variable
            if self.current_hover_variable in self.pending_variable_queries:
                # Update the tooltip with the actual value
                self._update_variable_tooltip(self.current_hover_variable, variable_value)

                # Remove from pending queries
                del self.pending_variable_queries[self.current_hover_variable]
                print(f"{variable_value}")

    def _update_variable_tooltip(self, variable_name: str, value: str) -> None:
        """Update the tooltip with the actual variable value."""
        # Update the source viewer with the variable value and update tooltip
        self.source_viewer.update_variable_tooltip(variable_name, value)

    def _update_watchpoints_tree(self) -> None:
        """Update the watchpoints tree with current watchpoints."""
        self.watchpoints_tree.clear()
        watchpoints = self.breakpoint_manager.get_watchpoints()
        for wp in watchpoints:
            item = QTreeWidgetItem(self.watchpoints_tree)
            item.setText(0, wp.expression)
            item.setText(1, wp.watch_type)
            item.setText(2, "Yes" if wp.enabled else "No")
            # Store watchpoint ID in the item
            item.setData(0, Qt.UserRole, wp.watchpoint_id)

    def _update_registers_tree(self) -> None:
        """Update the registers tree with current register values."""
        self.registers_tree.clear()
        # Get register names
        registers = self.gdb_controller.get_registers()
        # Get register values in selected format
        values = self.gdb_controller.get_register_values(self.register_format)

        # Create a mapping of register number to value for quick lookup
        value_map = {v.get('number', ''): v.get('value', '') for v in values}

        # Track current values for change detection
        current_values = {}

        for reg in registers:
            item = QTreeWidgetItem(self.registers_tree)
            register_name = reg.get('name', '')
            register_number = reg.get('number', '')
            register_value = value_map.get(register_number, 'N/A')

            item.setText(0, register_name)
            item.setText(1, register_number)
            item.setText(2, register_value)

            # Store current value for change detection
            current_values[register_name] = register_value

            # Apply color highlighting for changed registers
            if register_name in self.previous_register_values:
                previous_value = self.previous_register_values[register_name]
                if previous_value != register_value:
                    # Register changed - highlight in yellow
                    item.setBackground(2, Qt.yellow)
                else:
                    # Register unchanged - clear highlighting
                    item.setBackground(2, Qt.transparent)
            else:
                # First time seeing this register
                item.setBackground(2, Qt.transparent)

        # Update previous values for next comparison
        self.previous_register_values = current_values

    def _update_variables_tree(self) -> None:
        """Update the variables tree with current variable values."""
        self.variables_tree.clear()
        # Get variables from GDB
        variables = self.gdb_controller.get_variables()

        for var in variables:
            # Debug: print raw variable data
            print(f"[DEBUG] var raw: {var}")

            item = QTreeWidgetItem(self.variables_tree)
            name = var.get('name', 'N/A')
            value = var.get('value', '')
            var_type = var.get('type', 'N/A')

            # Debug: print extracted fields
            print(f"[DEBUG] var extracted: name='{name}', value='{value}', type='{var_type}'")

            item.setText(0, name)

            # Handle empty values (e.g., arrays, structures)
            if not value:
                # Check if it's an array type
                if '[' in var_type or 'array' in var_type.lower():
                    # For arrays, show address if available, otherwise just "array"
                    addr = var.get('addr', '')
                    if addr:
                        item.setText(1, f"array @ {addr}")
                    else:
                        item.setText(1, "array")
                else:
                    # For other types with no value, show type
                    item.setText(1, var_type)
            else:
                item.setText(1, value)

            item.setText(2, var_type)

    def add_watchpoint_dialog(self) -> None:
        """Show dialog to add a new watchpoint."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton, QMessageBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Watchpoint")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        # Expression input
        expression_layout = QHBoxLayout()
        expression_label = QLabel("Expression:")
        expression_label.setFont(QFont("Arial", 14))
        expression_input = QLineEdit()
        expression_input.setFont(QFont("Arial", 14))
        expression_input.setPlaceholderText("e.g., variable_name, *0x1234")
        expression_layout.addWidget(expression_label)
        expression_layout.addWidget(expression_input)
        layout.addLayout(expression_layout)

        # Type selection
        type_layout = QHBoxLayout()
        type_label = QLabel("Type:")
        type_label.setFont(QFont("Arial", 14))
        type_combo = QComboBox()
        type_combo.setFont(QFont("Arial", 14))
        type_combo.addItems(["write", "read", "access"])
        type_layout.addWidget(type_label)
        type_layout.addWidget(type_combo)
        layout.addLayout(type_layout)

        # Buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add")
        add_button.setFont(QFont("Arial", 14))
        cancel_button = QPushButton("Cancel")
        cancel_button.setFont(QFont("Arial", 14))

        add_button.clicked.connect(lambda: self._add_watchpoint_from_dialog(
            expression_input.text(), type_combo.currentText(), dialog))
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addWidget(add_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        dialog.exec_()

    def _add_watchpoint_from_dialog(self, expression: str, watch_type: str, dialog: QDialog) -> None:
        """Add watchpoint from dialog input."""
        if not expression.strip():
            QMessageBox.warning(self, "Warning", "Expression cannot be empty")
            return

        watchpoint = self.breakpoint_manager.add_watchpoint(expression.strip(), watch_type)
        if watchpoint:
            dialog.accept()
        else:
            QMessageBox.critical(self, "Error", f"Failed to set watchpoint on '{expression}'")

    def load_initial_source(self, program_path: str) -> None:
        # For now, try to load the corresponding C file
        # In a real implementation, we would query GDB for the main file
        c_file = program_path.replace('.exe', '.c')
        if os.path.exists(c_file):
            self.source_viewer.load_source_file(c_file)
            self.current_file_label.setText(f"Loaded: {c_file}")
        else:
            # Try to find any .c file in the same directory
            directory = os.path.dirname(program_path)
            for file in os.listdir(directory):
                if file.endswith('.c'):
                    c_file = os.path.join(directory, file)
                    self.source_viewer.load_source_file(c_file)
                    self.current_file_label.setText(f"Loaded: {c_file}")
                    break

    def open_program(self) -> None:
        """Open a program for debugging."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Program", "", "Executable Files (*.exe);;All Files (*)"
        )
        if file_path:
            if self.gdb_controller.start_gdb(file_path):
                self.load_initial_source(file_path)
                self.status_label.setText("Program loaded")
            else:
                QMessageBox.critical(self, "Error", "Failed to start GDB with selected program")

    def set_breakpoint_at_line(self, line_number: int) -> None:
        """Set breakpoint at specific line in current file."""
        if hasattr(self.source_viewer, 'current_file'):
            current_file = self.source_viewer.current_file
            if current_file:
                self.breakpoint_manager.add_breakpoint(current_file, line_number)

    def remove_breakpoint_at_line(self, line_number: int) -> None:
        """Remove breakpoint at specific line in current file."""
        if hasattr(self.source_viewer, 'current_file'):
            current_file = self.source_viewer.current_file
            if current_file:
                # Find breakpoint at this location
                breakpoints = self.breakpoint_manager.get_breakpoints_in_file(current_file)
                for bp in breakpoints:
                    if bp.line == line_number:
                        self.breakpoint_manager.remove_breakpoint(bp.breakpoint_id)
                        break

    def execute_gdb_command(self) -> None:
        """Execute a GDB command from the input field."""
        command = self.gdb_command_input.text().strip()
        if not command:
            return

        # Clear the input field
        self.gdb_command_input.clear()

        # Execute the command
        if self.gdb_controller.send_command(command):
            pass  # Command executed successfully
        else:
            QMessageBox.warning(self, "Error", "Failed to execute GDB command")

    def handle_breakpoint_toggle(self, line_number: int) -> None:
        """Handle breakpoint toggle from source viewer."""

        if hasattr(self.source_viewer, 'current_file') and self.source_viewer.current_file:
            current_file = self.source_viewer.current_file

            # Check if breakpoint already exists at this location
            existing_bp = None
            breakpoints = self.breakpoint_manager.get_breakpoints_in_file(current_file)
            for bp in breakpoints:
                if bp.line == line_number:
                    existing_bp = bp
                    break

            if existing_bp:
                # Remove existing breakpoint
                if self.breakpoint_manager.remove_breakpoint(existing_bp.breakpoint_id):
                    # Only remove visual marker if GDB successfully removed the breakpoint
                    self.source_viewer.remove_breakpoint_marker(line_number)
                else:
                    pass  # Failed to remove breakpoint
            else:
                # Add new breakpoint
                bp = self.breakpoint_manager.add_breakpoint(current_file, line_number)
                if bp:
                    # Only add visual marker if GDB successfully set the breakpoint
                    self.source_viewer.add_breakpoint_marker(line_number)
                else:
                    pass  # Failed to set breakpoint - no executable code at this location
        else:
            pass  # Cannot set breakpoint: no source file loaded

    def handle_variable_hover(self, variable_name: str) -> None:
        """Handle variable hover and query GDB for variable value."""
        # Only query variable values when program is stopped
        if self.gdb_controller.current_state['state'] != 'stopped':
            return

        # Store the current hover variable
        self.current_hover_variable = variable_name

        # Query GDB for variable value
        try:
            # Send command to get variable value
            command = f"print {variable_name}"
            if self.gdb_controller.send_command(command):
                # Track this query so we can extract the value from the output
                self.pending_variable_queries[variable_name] = True
        except Exception as e:
            pass  # Silent error handling

    def _show_gdb_output_context_menu(self, position: Any) -> None:
        """Show context menu for GDB output text area."""
        menu = QMenu(self.gdb_output_text)

        # Add Clear action
        clear_action = QAction("Clear", self.gdb_output_text)
        clear_action.triggered.connect(self._clear_gdb_output)
        menu.addAction(clear_action)

        # Show the menu at the cursor position
        menu.exec_(self.gdb_output_text.viewport().mapToGlobal(position))

    def _clear_gdb_output(self) -> None:
        """Clear the GDB output text area."""
        self.gdb_output_text.clear()

    def _show_watchpoints_context_menu(self, position: Any) -> None:
        """Show context menu for watchpoints tree."""
        item = self.watchpoints_tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self.watchpoints_tree)

        # Get watchpoint ID from item data (stored in first column)
        expression = item.text(0)
        watchpoint_type = item.text(1)

        # Find the watchpoint by expression and type
        watchpoint_id = None
        for wp_id, wp in self.breakpoint_manager.get_watchpoints().items():
            if wp.expression == expression and wp.watch_type == watchpoint_type:
                watchpoint_id = wp_id
                break

        if watchpoint_id is None:
            return

        # Edit action
        edit_action = QAction("Edit", self.watchpoints_tree)
        edit_action.triggered.connect(lambda: self._edit_watchpoint(watchpoint_id))
        menu.addAction(edit_action)

        # Delete action
        delete_action = QAction("Delete", self.watchpoints_tree)
        delete_action.triggered.connect(lambda: self._delete_watchpoint(watchpoint_id))
        menu.addAction(delete_action)

        # Toggle action
        enabled = item.text(2) == "True"
        toggle_text = "Disable" if enabled else "Enable"
        toggle_action = QAction(toggle_text, self.watchpoints_tree)
        toggle_action.triggered.connect(lambda: self._toggle_watchpoint(watchpoint_id))
        menu.addAction(toggle_action)

        # Show the menu at the cursor position
        menu.exec_(self.watchpoints_tree.viewport().mapToGlobal(position))

    def _edit_watchpoint(self, watchpoint_id: int) -> None:
        """Edit a watchpoint."""
        watchpoint = self.breakpoint_manager.get_watchpoint(watchpoint_id)
        if not watchpoint:
            return

        # Create dialog for editing
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Watchpoint")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        # Expression input
        expr_label = QLabel("Expression:")
        layout.addWidget(expr_label)
        expr_input = QLineEdit(dialog)
        expr_input.setText(watchpoint.expression)
        layout.addWidget(expr_input)

        # Type selection
        type_label = QLabel("Type:")
        layout.addWidget(type_label)
        type_combo = QComboBox(dialog)
        type_combo.addItems(["write", "read", "access"])
        type_combo.setCurrentText(watchpoint.watch_type)
        layout.addWidget(type_combo)

        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK", dialog)
        cancel_button = QPushButton("Cancel", dialog)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def on_ok():
            new_expr = expr_input.text().strip()
            new_type = type_combo.currentText()
            if new_expr and new_type:
                self.breakpoint_manager.update_watchpoint_expression(
                    watchpoint_id, new_expr, new_type
                )
            dialog.accept()

        def on_cancel():
            dialog.reject()

        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(on_cancel)

        dialog.exec_()

    def _delete_watchpoint(self, watchpoint_id: int) -> None:
        """Delete a watchpoint."""
        self.breakpoint_manager.remove_watchpoint(watchpoint_id)

    def _toggle_watchpoint(self, watchpoint_id: int) -> None:
        """Toggle a watchpoint enabled state."""
        self.breakpoint_manager.toggle_watchpoint(watchpoint_id)

    def _show_registers_context_menu(self, position: Any) -> None:
        """Show context menu for registers tree."""
        item = self.registers_tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self.registers_tree)

        # Get register name from item
        register_name = item.text(0)

        # Copy value action
        copy_value_action = QAction("Copy Value", self.registers_tree)
        copy_value_action.triggered.connect(lambda: self._copy_register_value(register_name))
        menu.addAction(copy_value_action)

        # Copy name action
        copy_name_action = QAction("Copy Name", self.registers_tree)
        copy_name_action.triggered.connect(lambda: self._copy_register_name(register_name))
        menu.addAction(copy_name_action)

        # Copy number action
        copy_number_action = QAction("Copy Number", self.registers_tree)
        copy_number_action.triggered.connect(lambda: self._copy_register_number(item.text(1)))
        menu.addAction(copy_number_action)

        # Show the menu at the cursor position
        menu.exec_(self.registers_tree.viewport().mapToGlobal(position))

    def _copy_register_value(self, register_name: str) -> None:
        """Copy register value to clipboard."""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(register_name)

    def _copy_register_name(self, register_name: str) -> None:
        """Copy register name to clipboard."""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(register_name)

    def _copy_register_number(self, register_number: str) -> None:
        """Copy register number to clipboard."""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(register_number)

    def save_breakpoints(self) -> None:
        """Save breakpoints and watchpoints to a file."""
        from PyQt5.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Breakpoints",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            if self.breakpoint_manager.save_breakpoints_to_file(file_path):
                self.status_label.setText(f"Breakpoints saved to {file_path}")
            else:
                self.status_label.setText("Failed to save breakpoints")

    def load_breakpoints(self) -> None:
        """Load breakpoints and watchpoints from a file."""
        from PyQt5.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Breakpoints",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            if self.breakpoint_manager.load_breakpoints_from_file(file_path):
                self.status_label.setText(f"Breakpoints loaded from {file_path}")
                # Update UI
                self._update_watchpoints_tree()
                # Note: Breakpoints tree update is handled via signals
            else:
                self.status_label.setText("Failed to load breakpoints")

    def quit_gdb_session(self) -> None:
        """Stop current debugging session (kill program but keep GDB running)."""
        if not self.gdb_controller:
            self.status_label.setText("No GDB controller")
            return

        state = self.gdb_controller.current_state['state']

        # Only react if program is running or stopped (being debugged)
        if state in ['running', 'stopped']:
            if self.gdb_controller.kill():
                self.status_label.setText("Program killed")
                # Update state to exited
                self.gdb_controller.current_state['state'] = 'exited'
                self.gdb_controller.current_state['line'] = None
                self.gdb_controller.current_state['file'] = None
                self.gdb_controller.current_state['function'] = None
                self.gdb_controller.state_changed.emit(self.gdb_controller.current_state.copy())
            else:
                self.status_label.setText("Failed to kill program")
        elif state == 'exited':
            self.status_label.setText("Program already exited")
        elif state == 'disconnected':
            self.status_label.setText("No active debugging session")
        else:
            self.status_label.setText(f"No program running (state: {state})")