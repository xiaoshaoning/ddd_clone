"""
Main application window for DDD Clone.
"""

import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItem, QToolBar,
    QAction, QStatusBar, QLabel, QMessageBox, QMenuBar, QMenu, QFileDialog,
    QLineEdit, QPushButton, QHBoxLayout, QToolTip
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

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the main user interface."""
        self.setWindowTitle("DDD Clone - Graphical Debugger")
        # Position window above command window with larger size
        self.setGeometry(100, 50, 1400, 900)

        # Create central widget and main layout
        central_widget = QWidget()
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

    def create_left_panel(self):
        """Create the left panel with source code and execution controls."""
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)

        # Source code viewer
        self.source_viewer = SourceViewer()
        layout.addWidget(self.source_viewer)

        return left_widget

    def create_right_panel(self):
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

    def create_toolbar(self):
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

    def create_menu_bar(self):
        """Create the menu bar."""
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # File menu
        file_menu = QMenu("File", self)
        menu_bar.addMenu(file_menu)

        # Open program action
        open_action = QAction("Open Program...", self)
        open_action.triggered.connect(self.open_program)
        file_menu.addAction(open_action)

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def create_status_bar(self):
        """Create the status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        # Status labels
        self.status_label = QLabel("Ready")
        status_bar.addWidget(self.status_label)

        self.current_file_label = QLabel("No file loaded")
        status_bar.addPermanentWidget(self.current_file_label)

    def connect_signals(self):
        """Connect signals from GDB controller to UI updates."""
        self.gdb_controller.state_changed.connect(self.update_ui_state)
        self.gdb_controller.output_received.connect(self.handle_gdb_output)

        # Connect source viewer signals
        self.source_viewer.breakpoint_toggled.connect(self.handle_breakpoint_toggle)
        self.source_viewer.variable_hovered.connect(self.handle_variable_hover)

    def run_or_continue(self):
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

    def run_program(self):
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

    def pause_program(self):
        """Pause program execution."""
        try:
            self.gdb_controller.pause()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to pause program: {e}")

    def step_over(self):
        """Step over current line."""
        try:
            self.gdb_controller.step_over()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to step over: {e}")

    def step_into(self):
        """Step into function call."""
        try:
            self.gdb_controller.step_into()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to step into: {e}")

    def step_out(self):
        """Step out of current function."""
        try:
            self.gdb_controller.step_out()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to step out: {e}")

    def continue_execution(self):
        """Continue program execution."""
        try:
            self.gdb_controller.continue_execution()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to continue: {e}")

    def update_ui_state(self, state_info):
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

    def handle_gdb_output(self, output):
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
        # Remove GDB/MI prefixes like ~, =, ^, &, etc.
        if output.startswith('~'):
            # Remove ~" and trailing quote
            cleaned = output[2:-1] if output.endswith('"') else output[2:]
            # Remove escaped newlines
            cleaned = cleaned.replace('\\n', '\n')
            # Remove single quotes if they wrap the entire output
            if cleaned.startswith("'") and cleaned.endswith("'"):
                cleaned = cleaned[1:-1]
            # Remove escaped quotes and backslashes
            cleaned = cleaned.replace('\\"', '"').replace('\\\\', '\\')
            # Filter out common noise messages
            if self._should_filter_output(cleaned):
                return ""
            # Remove ANSI escape codes
            cleaned = self._remove_ansi_escape_codes(cleaned)
            # Remove quotes around source code lines (e.g., "12\t    return n * factorial(n - 1);")
            cleaned = re.sub(r'"(\d+\\t.*?)"', r'\1', cleaned)
            return cleaned
        elif output.startswith('&'):
            # Remove &" and trailing quote
            cleaned = output[2:-1] if output.endswith('"') else output[2:]
            # Remove escaped newlines
            cleaned = cleaned.replace('\\n', '\n')
            # Remove single quotes if they wrap the entire output
            if cleaned.startswith("'") and cleaned.endswith("'"):
                cleaned = cleaned[1:-1]
            # Remove escaped quotes and backslashes
            cleaned = cleaned.replace('\\"', '"').replace('\\\\', '\\')
            # Filter out common noise messages
            if self._should_filter_output(cleaned):
                return ""
            # Remove ANSI escape codes
            cleaned = self._remove_ansi_escape_codes(cleaned)
            # Remove quotes around source code lines (e.g., "12\t    return n * factorial(n - 1);")
            cleaned = re.sub(r'"(\d+\\t.*?)"', r'\1', cleaned)
            return cleaned
        elif output.startswith('='):
            # Skip MI result records for now
            return ""
        elif output.startswith('^'):
            # Skip MI result records
            return ""
        elif output.strip() == '(gdb)':
            # Skip prompt
            return ""
        elif output.startswith('*'):
            # Handle async output like *running
            cleaned = output[1:].strip()
            # Remove escaped quotes and backslashes
            cleaned = cleaned.replace('\\"', '"').replace('\\\\', '\\')
            # Filter out common noise messages
            if self._should_filter_output(cleaned):
                return ""
            # Remove ANSI escape codes
            cleaned = self._remove_ansi_escape_codes(cleaned)
            # Remove quotes around source code lines (e.g., "12\t    return n * factorial(n - 1);")
            cleaned = re.sub(r'"(\d+\\t.*?)"', r'\1', cleaned)
            return cleaned
        else:
            # Return other output as-is
            cleaned = output.strip()
            # Remove single quotes if they wrap the entire output
            if cleaned.startswith("'") and cleaned.endswith("'"):
                cleaned = cleaned[1:-1]
            # Remove double quotes if they wrap the entire output
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1]
            # Remove escaped quotes and backslashes
            cleaned = cleaned.replace('\\"', '"').replace('\\\\', '\\')
            # Filter out common noise messages
            if self._should_filter_output(cleaned):
                return ""
            # Remove ANSI escape codes
            cleaned = self._remove_ansi_escape_codes(cleaned)
            # Remove quotes around source code lines (e.g., "12\t    return n * factorial(n - 1);")
            cleaned = re.sub(r'"(\d+\\t.*?)"', r'\1', cleaned)
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

    def _handle_breakpoint_output(self, output: str):
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

    def _add_breakpoint_visual_marker(self, file_path: str, line_number: int):
        """Add visual breakpoint marker if the file matches current source."""
        if (hasattr(self.source_viewer, 'current_file') and
            self.source_viewer.current_file and
            file_path in self.source_viewer.current_file):

            # Add visual marker
            self.source_viewer.add_breakpoint_marker(line_number)

    def _handle_variable_output(self, output: str):
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

    def _update_variable_tooltip(self, variable_name: str, value: str):
        """Update the tooltip with the actual variable value."""
        # Update the source viewer with the variable value and update tooltip
        self.source_viewer.update_variable_tooltip(variable_name, value)

    def load_initial_source(self, program_path):
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

    def open_program(self):
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

    def set_breakpoint_at_line(self, line_number):
        """Set breakpoint at specific line in current file."""
        if hasattr(self.source_viewer, 'current_file'):
            current_file = self.source_viewer.current_file
            if current_file:
                self.breakpoint_manager.add_breakpoint(current_file, line_number)

    def remove_breakpoint_at_line(self, line_number):
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

    def execute_gdb_command(self):
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

    def handle_breakpoint_toggle(self, line_number: int):
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

    def handle_variable_hover(self, variable_name: str):
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

    def _show_gdb_output_context_menu(self, position):
        """Show context menu for GDB output text area."""
        menu = QMenu(self.gdb_output_text)

        # Add Clear action
        clear_action = QAction("Clear", self.gdb_output_text)
        clear_action.triggered.connect(self._clear_gdb_output)
        menu.addAction(clear_action)

        # Show the menu at the cursor position
        menu.exec_(self.gdb_output_text.viewport().mapToGlobal(position))

    def _clear_gdb_output(self):
        """Clear the GDB output text area."""
        self.gdb_output_text.clear()