"""
Main application window for DDD Clone.
"""

import os
from typing import Any, Optional
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QTextEdit, QTreeWidget, QTreeWidgetItem, QToolBar,
    QAction, QStatusBar, QLabel, QMessageBox, QMenu, QFileDialog,
    QLineEdit, QPushButton, QDialog, QComboBox,
    QSizePolicy, QToolButton, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ..gdb.gdb_controller import GDBController
from .source_viewer import SourceViewer
from .breakpoint_manager import BreakpointManager, Breakpoint
from .variable_inspector import VariableInspector
from .memory_viewer import MemoryViewer


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
        self.tab_widget = tab_widget
        splitter.addWidget(tab_widget)

        # Variables tab
        self.variables_tree = QTreeWidget()
        self.variables_tree.setHeaderLabels(["Name", "Value", "Type"])
        self.variables_tree.setFont(QFont("Arial", 18))  # Larger font
        self.variables_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.variables_tree.customContextMenuRequested.connect(self._show_variables_context_menu)
        tab_widget.addTab(self.variables_tree, "Variables")

        # Watch expressions tab
        self.watch_tree = QTreeWidget()
        self.watch_tree.setHeaderLabels(["Expression", "Value"])
        self.watch_tree.setFont(QFont("Arial", 18))  # Larger font
        self.watch_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.watch_tree.customContextMenuRequested.connect(self._show_watch_tree_context_menu)
        tab_widget.addTab(self.watch_tree, "Watch")

        # Breakpoints tab
        self.breakpoints_tree = QTreeWidget()
        self.breakpoints_tree.setHeaderLabels(["File", "Line", "Condition", "Enabled"])
        self.breakpoints_tree.setFont(QFont("Arial", 18))  # Larger font
        self.breakpoints_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.breakpoints_tree.customContextMenuRequested.connect(self._show_breakpoints_context_menu)
        tab_widget.addTab(self.breakpoints_tree, "Breakpoints")

        # Watchpoints tab
        self.watchpoints_tree = QTreeWidget()
        self.watchpoints_tree.setHeaderLabels(["Expression", "Type", "Enabled", "Value"])
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

        # Memory tab
        self.memory_viewer = MemoryViewer(self.gdb_controller)
        tab_widget.addTab(self.memory_viewer, "Memory")

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

        # Add spacer to push preference button to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)

        # Dropdown button for syntax highlighting preferences
        self.syntax_highlight_button = QToolButton(self)
        self.syntax_highlight_button.setFont(toolbar_font)
        self.syntax_highlight_button.setText(f"Syntax: {self.source_viewer.highlight_style}")
        self.syntax_highlight_button.setPopupMode(QToolButton.InstantPopup)

        # Create menu with available styles
        syntax_menu = QMenu(self.syntax_highlight_button)

        # Available pygments styles (selected for light backgrounds)
        available_styles = [
            "pastie",        # Good contrast
            "friendly",      # Clean and readable
            "tango",         # Based on Tango desktop palette
            "perldoc",       # Like perldoc, good for light backgrounds
            "vs",            # Visual Studio-like
            "xcode",         # Xcode-like (SourceViewer default)
            "solarized-light", # Solarized light theme
            "default",       # Pygments default style
            "colorful",      # Colorful style
            "autumn",        # Autumn colors
            "borland",       # Borland style
            "vim",           # Vim style
            "rrt",           # Pygments style
            "native",        # Native style
        ]

        for style in available_styles:
            action = QAction(style, self)
            action.triggered.connect(lambda checked, s=style: self._on_syntax_style_selected(s))
            syntax_menu.addAction(action)

        self.syntax_highlight_button.setMenu(syntax_menu)
        toolbar.addWidget(self.syntax_highlight_button)

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

    def _on_syntax_style_selected(self, style: str) -> None:
        """Handle syntax highlighting style selection from dropdown menu."""
        # The source viewer owns the style; we only mirror it in the button.
        if style != self.source_viewer.highlight_style and \
                self.source_viewer.set_syntax_highlight_style(style):
            self.syntax_highlight_button.setText(f"Syntax: {style}")

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
        self.gdb_controller.console_output.connect(self._append_console_output)
        self.gdb_controller.breakpoint_created.connect(self._add_breakpoint_visual_marker)

        # Connect source viewer signals
        self.source_viewer.breakpoint_toggled.connect(self.handle_breakpoint_toggle)
        self.source_viewer.variable_hovered.connect(self.handle_variable_hover)

        # Connect breakpoint manager signals
        self.breakpoint_manager.breakpoints_changed.connect(self._update_breakpoints_tree)
        self.breakpoint_manager.watchpoints_changed.connect(self._update_watchpoints_tree)
        # GDB creates breakpoints we did not ask for too (a `break` typed at the
        # console), so re-read its list whenever it reports a new one.
        self.gdb_controller.breakpoint_created.connect(self.breakpoint_manager.refresh)

        # Connect variable inspector signals
        self.variable_inspector.watch_expression_added.connect(self._update_watch_tree)
        self.variable_inspector.watch_expression_removed.connect(self._update_watch_tree)

        # Connect call stack navigation
        self.call_stack_tree.itemDoubleClicked.connect(self._on_call_stack_frame_activated)

        # A view only refreshes when it is on screen, so it needs refreshing
        # when it becomes the one on screen
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # Connect variable tree expansion for composite types
        self.variables_tree.itemExpanded.connect(self._on_variable_expanded)
        self.variables_tree.itemCollapsed.connect(self._on_variable_collapsed)

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

    def update_ui_state(self, state_info: dict) -> None:
        """Update UI based on current debugger state."""
        # Update status label
        state = state_info.get('state', 'unknown')
        self.status_label.setText(f"State: {state}")

        # Check if we have valid line information to highlight
        has_valid_line = ('file' in state_info and 'line' in state_info and
                         state_info['line'] is not None and state_info['line'] > 0)

        if has_valid_line and state == 'stopped':
            # Follow the program into whichever file it stopped in
            self._show_source_location(state_info, state_info['line'])
        else:
            # Clear highlight when program exits or no valid line info
            self.source_viewer.clear_all_highlights()
            self.call_stack_tree.clear()
            if 'file' in state_info and state_info['file']:
                self.current_file_label.setText(f"{state_info['file']}:??")
            else:
                self.current_file_label.setText("No file loaded")

        # Refreshing every view on every stop costs ~47ms against a local GDB,
        # most of it re-reading 207 registers for a tab that is usually not on
        # screen, so only the visible view is refreshed here; the others are
        # refreshed by _on_tab_changed when they are brought forward.
        if state == 'stopped':
            self._refresh_current_tab()

    def _refresh_current_tab(self) -> None:
        """Refresh the debug view currently on screen."""
        current = self.tab_widget.currentWidget()

        if current is self.variables_tree:
            self._update_variables_tree()
        elif current is self.watch_tree:
            self.variable_inspector.update_watch_expressions()
            self._update_watch_tree()
        elif current in (self.breakpoints_tree, self.watchpoints_tree):
            # Rebuilds both trees through the manager's signals
            self.breakpoint_manager.refresh()
        elif current is self.registers_tree:
            self._update_registers_tree()
        elif current is self.call_stack_tree:
            self._update_call_stack_tree()
        elif current is self.memory_viewer:
            self.memory_viewer.refresh()

    def _on_tab_changed(self, index: int) -> None:
        """Show fresh data for a view the moment it is brought forward."""
        if self.gdb_controller.current_state.get('state') == 'stopped':
            self._refresh_current_tab()

    def _resolve_source_path(self, state_info: dict) -> Optional[str]:
        """Find a path on disk for the file the program stopped in, or None."""
        # fullname is the absolute path when GDB can provide it
        fullname = state_info.get('fullname')
        if fullname and os.path.exists(fullname):
            return fullname

        # file is often only a basename; look next to the source already open
        file_name = state_info.get('file')
        if not file_name:
            return None
        current_file = getattr(self.source_viewer, 'current_file', None)
        if current_file:
            candidate = os.path.join(os.path.dirname(current_file),
                                     os.path.basename(file_name))
            if os.path.exists(candidate):
                return candidate
        return file_name if os.path.exists(file_name) else None

    def _show_source_location(self, state_info: dict, line_number: int) -> None:
        """Show the stopped file, loading it if it is not the one on screen."""
        path = self._resolve_source_path(state_info)
        if path and not self._is_current_source(path):
            self.source_viewer.load_source_file(path, line_number)
        else:
            self.source_viewer.highlight_current_line(line_number)
        self.current_file_label.setText(f"{path or state_info.get('file', '')}:{line_number}")

    def _append_console_output(self, text: str) -> None:
        """Append decoded GDB console text to the output area."""
        if not text.strip():
            return
        self.gdb_output_text.append(text.rstrip("\n"))
        # Auto-scroll to bottom
        cursor = self.gdb_output_text.textCursor()
        cursor.movePosition(cursor.End)
        self.gdb_output_text.setTextCursor(cursor)

    def _is_current_source(self, file_path: str) -> bool:
        """True if file_path names the source file currently on screen."""
        current_file = getattr(self.source_viewer, 'current_file', None)
        if not current_file:
            return False
        # GDB may report an absolute path with either slash direction; compare
        # basenames so paths resolve regardless of how GDB rendered them.
        return os.path.basename(file_path.replace('\\', '/')) == \
            os.path.basename(current_file.replace('\\', '/'))

    def _add_breakpoint_visual_marker(self, file_path: str, line_number: int) -> None:
        """Add a visual marker if GDB reports the loaded source file."""
        if self._is_current_source(file_path):
            self.source_viewer.add_breakpoint_marker(line_number)

    def _update_breakpoints_tree(self) -> None:
        """Update the breakpoints tree with current breakpoints."""
        self.breakpoints_tree.clear()
        for bp in self.breakpoint_manager.get_breakpoints():
            item = QTreeWidgetItem(self.breakpoints_tree)
            item.setText(0, os.path.basename(bp.file))
            item.setText(1, str(bp.line))
            item.setText(2, bp.condition or "")
            item.setText(3, "Yes" if bp.enabled else "No")
            # Store GDB's breakpoint number in the item
            item.setData(0, Qt.UserRole, bp.gdb_number)

    def _update_call_stack_tree(self) -> None:
        """Update the call stack tree with the frames GDB reports."""
        self.call_stack_tree.clear()
        for frame in self.gdb_controller.get_call_stack():
            item = QTreeWidgetItem(self.call_stack_tree)
            file_path = frame.get('file', '')
            item.setText(0, frame.get('func', '??'))
            item.setText(1, os.path.basename(file_path.replace('\\', '/')))
            item.setText(2, frame.get('level', ''))
            # fullname is absolute when GDB can provide it; file may be relative
            item.setData(0, Qt.UserRole, {
                'level': int(frame.get('level') or 0),
                'file': frame.get('fullname') or file_path,
                'line': int(frame.get('line') or 0),
            })

    def _on_call_stack_frame_activated(self, item: QTreeWidgetItem, column: int = 0) -> None:
        """Select the double-clicked stack frame and show its source line."""
        info = item.data(0, Qt.UserRole)
        if not info or not self.gdb_controller.select_frame(info['level']):
            return

        file_path = info['file']
        if file_path and os.path.exists(file_path):
            self.source_viewer.load_source_file(file_path, info['line'])
            self.current_file_label.setText(f"{file_path}:{info['line']}")
        elif info['line'] > 0:
            self.source_viewer.highlight_current_line(info['line'])

    def _show_breakpoints_context_menu(self, position: Any) -> None:
        """Show context menu for the breakpoints tree."""
        item = self.breakpoints_tree.itemAt(position)
        if not item:
            return

        breakpoint = self.breakpoint_manager.get_breakpoint(item.data(0, Qt.UserRole))
        if not breakpoint:
            return

        menu = QMenu(self.breakpoints_tree)

        condition_action = QAction("Edit Condition...", self.breakpoints_tree)
        condition_action.triggered.connect(
            lambda: self._edit_breakpoint_condition(breakpoint.gdb_number))
        menu.addAction(condition_action)

        toggle_text = "Disable" if breakpoint.enabled else "Enable"
        toggle_action = QAction(toggle_text, self.breakpoints_tree)
        toggle_action.triggered.connect(
            lambda: self.breakpoint_manager.toggle_breakpoint(breakpoint.gdb_number))
        menu.addAction(toggle_action)

        delete_action = QAction("Delete", self.breakpoints_tree)
        delete_action.triggered.connect(
            lambda: self._delete_breakpoint(breakpoint.gdb_number))
        menu.addAction(delete_action)

        menu.exec_(self.breakpoints_tree.viewport().mapToGlobal(position))

    def _edit_breakpoint_condition(self, gdb_number: int) -> None:
        """Ask for a new condition and apply it to the breakpoint."""
        breakpoint = self.breakpoint_manager.get_breakpoint(gdb_number)
        if not breakpoint:
            return

        dialog = self._create_condition_dialog(breakpoint)
        if dialog.exec_() == QDialog.Accepted:
            self.breakpoint_manager.update_breakpoint_condition(
                gdb_number, getattr(dialog, 'condition', None))

    def _create_condition_dialog(self, breakpoint) -> QDialog:
        """Build the breakpoint-condition dialog (does not exec, so it is testable)."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Breakpoint Condition")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(
            f"Condition for {os.path.basename(breakpoint.file)}:{breakpoint.line}"))

        condition_input = QLineEdit(dialog)
        condition_input.setText(breakpoint.condition or "")
        condition_input.setPlaceholderText("e.g. i == 5 (empty removes the condition)")
        layout.addWidget(condition_input)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK", dialog)
        cancel_button = QPushButton("Cancel", dialog)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def on_ok():
            dialog.condition = condition_input.text().strip()
            dialog.accept()

        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(dialog.reject)
        return dialog

    def _delete_breakpoint(self, gdb_number: int) -> None:
        """Delete a breakpoint and its visual marker."""
        breakpoint = self.breakpoint_manager.get_breakpoint(gdb_number)
        if breakpoint and self.breakpoint_manager.remove_breakpoint(gdb_number):
            if self._is_current_source(breakpoint.file):
                self.source_viewer.remove_breakpoint_marker(breakpoint.line)

    def _update_watchpoints_tree(self) -> None:
        """Update the watchpoints tree with current watchpoints and values."""
        self.watchpoints_tree.clear()
        # Only ask GDB for a value while the program is stopped; evaluating a
        # running program would block or fail.
        stopped = self.gdb_controller.current_state.get('state') == 'stopped'
        for wp in self.breakpoint_manager.get_watchpoints():
            item = QTreeWidgetItem(self.watchpoints_tree)
            item.setText(0, wp.expression)
            item.setText(1, wp.watch_type)
            item.setText(2, "Yes" if wp.enabled else "No")
            if stopped:
                value = self.gdb_controller.evaluate_expression(wp.expression)
                item.setText(3, value if value is not None else "N/A")
            # Store watchpoint ID in the item
            item.setData(0, Qt.UserRole, wp.gdb_number)

    def _update_watch_tree(self) -> None:
        """Update the Watch tab with the current watch expressions."""
        self.watch_tree.clear()
        for expression, value in self.variable_inspector.get_watch_expressions().items():
            item = QTreeWidgetItem(self.watch_tree)
            item.setText(0, expression)
            item.setText(1, value)
            item.setData(0, Qt.UserRole, expression)

    def _show_variables_context_menu(self, position: Any) -> None:
        """Show context menu for the variables tree."""
        item = self.variables_tree.itemAt(position)
        if not item:
            return

        name = item.data(0, Qt.UserRole)
        if not name:
            return

        menu = QMenu(self.variables_tree)
        watch_action = QAction("Add to Watch", self.variables_tree)
        watch_action.triggered.connect(
            lambda: self.variable_inspector.add_watch_expression(name))
        menu.addAction(watch_action)
        menu.exec_(self.variables_tree.viewport().mapToGlobal(position))

    def _show_watch_tree_context_menu(self, position: Any) -> None:
        """Show context menu for the Watch tab."""
        item = self.watch_tree.itemAt(position)
        if not item:
            return

        expression = item.data(0, Qt.UserRole)
        menu = QMenu(self.watch_tree)
        remove_action = QAction("Remove", self.watch_tree)
        remove_action.triggered.connect(
            lambda: self.variable_inspector.remove_watch_expression(expression))
        menu.addAction(remove_action)
        menu.exec_(self.watch_tree.viewport().mapToGlobal(position))

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
        self.variable_inspector.update_variables()

        for variable in self.variable_inspector.get_local_variables():
            self._add_variable_item(self.variables_tree, variable)

    def _add_variable_item(self, parent, variable) -> QTreeWidgetItem:
        """
        Add a row for a variable, expandable when it has children to load.

        Args:
            parent: QTreeWidget or QTreeWidgetItem to add the row to
            variable: Variable to display

        Returns:
            The row that was added
        """
        item = QTreeWidgetItem(parent)
        value = variable.value or ''
        var_type = variable.type or 'N/A'

        item.setText(0, variable.name or 'N/A')
        if value:
            item.setText(1, value)
        elif VariableInspector._is_array_type(var_type):
            # A composite GDB did not expand is shown by its type instead
            item.setText(1, "array")
        else:
            item.setText(1, var_type)
        item.setText(2, var_type)

        # The path is the expression that reaches this row, not its label:
        # children are asked for by path, and so is "Add to Watch".
        item.setData(0, Qt.UserRole, variable.path)
        if VariableInspector._is_expandable(var_type):
            item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        return item

    def _on_variable_expanded(self, item: QTreeWidgetItem) -> None:
        """Load and display children of an expanded variable."""
        path = item.data(0, Qt.UserRole)
        if not path:
            return

        item.takeChildren()  # clear stale children on re-expand
        for child in self.variable_inspector.expand_variable(path):
            self._add_variable_item(item, child)

    def _on_variable_collapsed(self, item: QTreeWidgetItem) -> None:
        """Collapse a variable and remove its displayed children."""
        path = item.data(0, Qt.UserRole)
        if path:
            self.variable_inspector.collapse_variable(path)
            item.takeChildren()

    def add_watchpoint_dialog(self) -> None:
        """Show modal dialog to add a new watchpoint."""
        dialog = self._create_watchpoint_dialog()
        dialog.exec_()

    def _create_watchpoint_dialog(self) -> QDialog:
        """Build the add-watchpoint dialog (does not exec, so it is testable)."""
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

        return dialog

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
        breakpoint = self._find_breakpoint_at(line_number)
        if breakpoint:
            self.breakpoint_manager.remove_breakpoint(breakpoint.gdb_number)

    def _find_breakpoint_at(self, line_number: int) -> Optional[Breakpoint]:
        """The breakpoint on this line of the file on screen, if there is one."""
        for breakpoint in self.breakpoint_manager.get_breakpoints():
            if breakpoint.line == line_number and self._is_current_source(breakpoint.file):
                return breakpoint
        return None

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
            existing_bp = self._find_breakpoint_at(line_number)

            if existing_bp:
                # Remove existing breakpoint
                if self.breakpoint_manager.remove_breakpoint(existing_bp.gdb_number):
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
        """Handle variable hover by asking the controller for the value."""
        # Only query variable values when program is stopped
        if self.gdb_controller.current_state['state'] != 'stopped':
            return

        value = self.gdb_controller.evaluate_expression(variable_name)
        if value is not None:
            self.source_viewer.update_variable_tooltip(variable_name, value)

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

        watchpoint = self.breakpoint_manager.get_watchpoint(item.data(0, Qt.UserRole))
        if not watchpoint:
            return

        menu = QMenu(self.watchpoints_tree)

        # Edit action
        edit_action = QAction("Edit", self.watchpoints_tree)
        edit_action.triggered.connect(lambda: self._edit_watchpoint(watchpoint.gdb_number))
        menu.addAction(edit_action)

        # Delete action
        delete_action = QAction("Delete", self.watchpoints_tree)
        delete_action.triggered.connect(lambda: self._delete_watchpoint(watchpoint.gdb_number))
        menu.addAction(delete_action)

        # Toggle action
        toggle_text = "Disable" if watchpoint.enabled else "Enable"
        toggle_action = QAction(toggle_text, self.watchpoints_tree)
        toggle_action.triggered.connect(lambda: self._toggle_watchpoint(watchpoint.gdb_number))
        menu.addAction(toggle_action)

        # Show the menu at the cursor position
        menu.exec_(self.watchpoints_tree.viewport().mapToGlobal(position))

    def _edit_watchpoint(self, gdb_number: int) -> None:
        """Edit a watchpoint."""
        watchpoint = self.breakpoint_manager.get_watchpoint(gdb_number)
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
                    gdb_number, new_expr, new_type
                )
            dialog.accept()

        def on_cancel():
            dialog.reject()

        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(on_cancel)

        dialog.exec_()

    def _delete_watchpoint(self, gdb_number: int) -> None:
        """Delete a watchpoint."""
        self.breakpoint_manager.remove_watchpoint(gdb_number)

    def _toggle_watchpoint(self, gdb_number: int) -> None:
        """Toggle a watchpoint enabled state."""
        self.breakpoint_manager.toggle_watchpoint(gdb_number)

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
        copy_value_action.triggered.connect(lambda: self._copy_to_clipboard(item.text(2)))
        menu.addAction(copy_value_action)

        # Copy name action
        copy_name_action = QAction("Copy Name", self.registers_tree)
        copy_name_action.triggered.connect(lambda: self._copy_to_clipboard(register_name))
        menu.addAction(copy_name_action)

        # Copy number action
        copy_number_action = QAction("Copy Number", self.registers_tree)
        copy_number_action.triggered.connect(lambda: self._copy_to_clipboard(item.text(1)))
        menu.addAction(copy_number_action)

        # Display memory action
        display_memory_action = QAction("Display Memory", self.registers_tree)
        display_memory_action.triggered.connect(lambda: self._display_memory(item.text(2)))
        menu.addAction(display_memory_action)

        # Show the menu at the cursor position
        menu.exec_(self.registers_tree.viewport().mapToGlobal(position))

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to the clipboard."""
        QApplication.clipboard().setText(text)

    def _display_memory(self, address: str) -> None:
        """Show memory at an address, e.g. from the registers tree."""
        if not address or address == "N/A":
            return
        self.tab_widget.setCurrentWidget(self.memory_viewer)
        self.memory_viewer.set_address(address)

    def save_breakpoints(self) -> None:
        """Save breakpoints and watchpoints to a file."""
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