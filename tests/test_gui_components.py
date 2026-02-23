"""
GUI component tests for DDD Clone Phase 4 features.
Tests watchpoint dialog and register tree updates.
"""

import sys
import os
from unittest.mock import Mock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# PyQt5 imports
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Import the modules to test
from ddd_clone.gui.main_window import MainWindow
from ddd_clone.gdb.gdb_controller import GDBController


def test_watchpoint_dialog(qtbot):
    """Test watchpoint dialog creation and interaction."""
    # Create mock GDB controller
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}

    # Create main window
    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    # Test that dialog can be created
    window.add_watchpoint_dialog()

    # Find dialog in application
    app = QApplication.instance()
    dialogs = [w for w in app.topLevelWidgets() if w.windowTitle() == "Add Watchpoint"]

    assert len(dialogs) == 1
    dialog = dialogs[0]

    # Test dialog widgets exist
    assert dialog is not None

    # Clean up
    dialog.close()


def test_register_format_change(qtbot):
    """Test register format switching via toolbar."""
    # Create mock GDB controller
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}
    mock_gdb.get_registers.return_value = [
        {'name': 'rax', 'number': '0'},
        {'name': 'rbx', 'number': '1'}
    ]
    mock_gdb.get_register_values.return_value = [
        {'number': '0', 'value': '0x7ffe'},
        {'number': '1', 'value': '0x1000'}
    ]

    # Create main window
    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    # Initially format should be hex
    assert window.register_format == "x"

    # Change format to decimal via combo box
    window.register_format_combo.setCurrentText("Decimal")

    # Check format changed
    assert window.register_format == "d"

    # Change format to binary
    window.register_format_combo.setCurrentText("Binary")

    # Check format changed
    assert window.register_format == "b"


def test_watchpoint_context_menu(qtbot):
    """Test watchpoint context menu creation."""
    # Create mock GDB controller
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}

    # Create main window
    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    # Add a watchpoint first
    mock_bp_manager = window.breakpoint_manager
    mock_bp_manager.add_watchpoint = Mock(return_value=Mock(
        expression="test_var",
        watchpoint_type="write",
        enabled=True
    ))

    # Trigger context menu request
    # Note: We can't easily test the actual menu display without complex setup,
    # but we can verify the method exists and doesn't crash
    try:
        # Call the context menu handler with a dummy position
        window._show_watchpoints_context_menu((0, 0))
        # If we get here, method executed without error
        assert True
    except Exception:
        assert False, "Context menu method raised exception"


def test_register_context_menu(qtbot):
    """Test register context menu creation."""
    # Create mock GDB controller
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}

    # Create main window
    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    # Trigger context menu request
    try:
        # Call the context menu handler with a dummy position
        window._show_registers_context_menu((0, 0))
        # If we get here, method executed without error
        assert True
    except Exception:
        assert False, "Context menu method raised exception"


def test_breakpoint_persistence(qtbot):
    """Test breakpoint save/load functionality."""
    # Create mock GDB controller
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}

    # Create main window
    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    # Mock the breakpoint manager methods
    mock_bp_manager = window.breakpoint_manager
    mock_bp_manager.save_breakpoints_to_file = Mock(return_value=True)
    mock_bp_manager.load_breakpoints_from_file = Mock(return_value=True)

    # Test save method exists
    try:
        window.save_breakpoints()
        assert True
    except Exception:
        assert False, "save_breakpoints method raised exception"

    # Test load method exists
    try:
        window.load_breakpoints()
        assert True
    except Exception:
        assert False, "load_breakpoints method raised exception"


def test_register_change_highlighting(qtbot):
    """Test register change highlighting logic."""
    # Create mock GDB controller
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}

    # Create main window
    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    # Set up mock register data
    mock_gdb.get_registers.return_value = [
        {'name': 'rax', 'number': '0'},
        {'name': 'rbx', 'number': '1'}
    ]

    # First call - all registers are new
    mock_gdb.get_register_values.return_value = [
        {'number': '0', 'value': '0x1000'},
        {'number': '1', 'value': '0x2000'}
    ]

    window._update_registers_tree()

    # Second call with changed value
    mock_gdb.get_register_values.return_value = [
        {'number': '0', 'value': '0x1001'},  # Changed
        {'number': '1', 'value': '0x2000'}   # Unchanged
    ]

    window._update_registers_tree()

    # Verify previous values were stored
    assert 'rax' in window.previous_register_values
    assert window.previous_register_values['rax'] == '0x1001'