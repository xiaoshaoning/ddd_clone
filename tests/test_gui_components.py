"""
GUI component tests for DDD Clone Phase 4 features.
Tests watchpoint dialog and register tree updates.
"""

import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# PyQt5 imports
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QPoint

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

    # Test that the dialog can be created without blocking (no exec_)
    dialog = window._create_watchpoint_dialog()
    qtbot.addWidget(dialog)

    assert dialog is not None
    assert dialog.windowTitle() == "Add Watchpoint"

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
        window._show_watchpoints_context_menu(QPoint(0, 0))
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
        window._show_registers_context_menu(QPoint(0, 0))
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

    # Test save method exists (patch file dialog so it does not block)
    try:
        with patch('ddd_clone.gui.main_window.QFileDialog.getSaveFileName',
                   return_value=('bp.json', 'JSON Files (*.json)')):
            window.save_breakpoints()
        assert True
    except Exception:
        assert False, "save_breakpoints method raised exception"

    # Test load method exists (patch file dialog so it does not block)
    try:
        with patch('ddd_clone.gui.main_window.QFileDialog.getOpenFileName',
                   return_value=('bp.json', 'JSON Files (*.json)')):
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


def test_syntax_highlight_dropdown_button(qtbot):
    """Test syntax highlighting dropdown button creation and interaction."""
    # Create mock GDB controller
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}

    # Create main window
    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    # Verify syntax highlight button exists
    assert hasattr(window, 'syntax_highlight_button')
    assert window.syntax_highlight_button is not None

    # Verify button text contains current style
    assert "Syntax:" in window.syntax_highlight_button.text()

    # Verify menu exists
    assert window.syntax_highlight_button.menu() is not None

    # Verify menu has actions for each style
    menu = window.syntax_highlight_button.menu()
    assert len(menu.actions()) > 0

    # Test style selection: the source viewer owns the style, the button mirrors it
    original_style = window.source_viewer.highlight_style
    new_style = "friendly" if original_style != "friendly" else "tango"

    # Trigger style selection
    window._on_syntax_style_selected(new_style)

    # Verify the viewer applied the style and the button text followed
    assert window.source_viewer.highlight_style == new_style
    assert f"Syntax: {new_style}" in window.syntax_highlight_button.text()

def test_call_stack_tree_population(qtbot):
    """The call stack tree shows the frames GDB reports."""
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}
    mock_gdb.get_call_stack.return_value = [
        {'level': '0', 'func': 'factorial', 'file': 'simple_program.c',
         'fullname': 'D:\\build\\simple_program.c', 'line': '9'},
        {'level': '1', 'func': 'main', 'file': 'simple_program.c',
         'fullname': 'D:\\build\\simple_program.c', 'line': '29'},
    ]

    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)
    window._update_call_stack_tree()

    assert window.call_stack_tree.topLevelItemCount() == 2
    assert window.call_stack_tree.topLevelItem(0).text(0) == 'factorial'
    assert window.call_stack_tree.topLevelItem(1).text(0) == 'main'
    assert window.call_stack_tree.topLevelItem(1).text(2) == '1'
    info = window.call_stack_tree.topLevelItem(1).data(0, Qt.UserRole)
    assert info == {'level': 1, 'file': 'D:\\build\\simple_program.c', 'line': 29}


def test_call_stack_frame_activation(qtbot, tmp_path):
    """Activating a frame selects it in GDB and shows its source line."""
    source = tmp_path / 'frame.c'
    source.write_text('int main(void) { return 0; }\n')

    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}
    mock_gdb.select_frame = Mock(return_value=True)
    mock_gdb.get_call_stack.return_value = [
        {'level': '1', 'func': 'main', 'file': 'frame.c',
         'fullname': str(source), 'line': '1'},
    ]

    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)
    window._update_call_stack_tree()

    window._on_call_stack_frame_activated(window.call_stack_tree.topLevelItem(0), 0)

    mock_gdb.select_frame.assert_called_once_with(1)
    assert window.source_viewer.current_file == str(source)
    assert window.source_viewer.current_line == 1


def test_breakpoints_tree_and_delete(qtbot):
    """The breakpoints tree reflects the manager and supports deletion."""
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}
    mock_gdb.set_breakpoint = Mock(return_value=4)
    mock_gdb.delete_breakpoint = Mock(return_value=True)

    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)
    bp = window.breakpoint_manager.add_breakpoint('simple_program.c', 22)
    assert bp is not None

    # The breakpoint_added signal refreshes the tree
    assert window.breakpoints_tree.topLevelItemCount() == 1
    item = window.breakpoints_tree.topLevelItem(0)
    assert item.text(0) == 'simple_program.c'
    assert item.text(1) == '22'
    assert item.text(3) == 'Yes'

    window._delete_breakpoint(bp.breakpoint_id)
    mock_gdb.delete_breakpoint.assert_called_once_with(4)
    assert window.breakpoints_tree.topLevelItemCount() == 0


def test_watch_tree_population(qtbot):
    """The Watch tab lists expressions and their values."""
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}
    mock_gdb.evaluate_expression.return_value = '42'

    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    # Adding a watch expression refreshes the tree via the signal
    assert window.variable_inspector.add_watch_expression('my_var') is True

    assert window.watch_tree.topLevelItemCount() == 1
    item = window.watch_tree.topLevelItem(0)
    assert item.text(0) == 'my_var'
    assert item.text(1) == '42'

    # Removing it clears the row
    window.variable_inspector.remove_watch_expression('my_var')
    assert window.watch_tree.topLevelItemCount() == 0


def test_watchpoints_tree_shows_value(qtbot):
    """The Watchpoints tab shows a live value and records GDB's number."""
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}
    mock_gdb.set_watchpoint = Mock(return_value=2)
    mock_gdb.evaluate_expression = Mock(return_value='7')

    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    wp = window.breakpoint_manager.add_watchpoint('x', 'write')
    assert wp is not None
    assert wp.gdb_number == 2

    window._update_watchpoints_tree()
    item = window.watchpoints_tree.topLevelItem(0)
    assert item.text(0) == 'x'
    assert item.text(2) == 'Yes'
    assert item.text(3) == '7'


def test_update_ui_state_follows_source_file(qtbot, tmp_path):
    """Stopping in another file loads that file and highlights the line."""
    first = tmp_path / 'first.c'
    second = tmp_path / 'second.c'
    first.write_text('int main(void) { return 0; }\n')
    second.write_text('int helper(void) {\n    return 1;\n}\n')

    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}
    mock_gdb.get_registers.return_value = []
    mock_gdb.get_register_values.return_value = []
    mock_gdb.get_variables.return_value = []
    mock_gdb.get_call_stack.return_value = []

    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)
    window.source_viewer.load_source_file(str(first))
    assert window.source_viewer.current_file == str(first)

    # Same file: just move the highlight, do not reload
    window.update_ui_state({'state': 'stopped', 'file': 'first.c',
                            'fullname': str(first), 'line': 1})
    assert window.source_viewer.current_file == str(first)
    assert window.source_viewer.current_line == 1

    # Different file: the viewer follows the program
    window.update_ui_state({'state': 'stopped', 'file': 'second.c',
                            'fullname': str(second), 'line': 2})
    assert window.source_viewer.current_file == str(second)
    assert window.source_viewer.current_line == 2
    assert 'second.c' in window.current_file_label.text()


def test_resolve_source_path_falls_back_to_basename(qtbot, tmp_path):
    """A bare basename resolves next to the source already open."""
    folder = tmp_path / 'src'
    folder.mkdir()
    source = folder / 'main.c'
    source.write_text('int main(void) { return 0; }\n')

    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}

    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)
    window.source_viewer.load_source_file(str(source))

    # fullname missing, file is only a basename
    resolved = window._resolve_source_path({'file': 'main.c'})
    assert resolved == str(source)

    # Nothing on disk to resolve
    assert window._resolve_source_path({'file': 'nowhere.c'}) is None


def test_struct_expansion_in_variables_tree(qtbot):
    """A struct variable is expandable and shows its fields."""
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}
    mock_gdb.get_variables.return_value = [
        {'name': 'p', 'value': '{x = 1, y = 2}', 'type': 'struct Point'},
    ]
    mock_gdb.get_variable_children.return_value = [
        {'name': 'x', 'value': '1', 'type': 'int', 'numchild': '0'},
        {'name': 'y', 'value': '2', 'type': 'int', 'numchild': '0'},
    ]

    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)
    window._update_variables_tree()

    item = window.variables_tree.topLevelItem(0)
    assert item.text(0) == 'p'

    # Expanding the struct pulls its fields in
    item.setExpanded(True)
    assert item.childCount() == 2
    assert item.child(0).text(0) == 'x'
    assert item.child(1).text(1) == '2'
    assert item.child(1).text(2) == 'int'


def test_memory_tab_and_display(qtbot):
    """The Memory tab reads memory for an address such as a register value."""
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'stopped'}
    mock_gdb.read_memory.return_value = b'\x41\x42'

    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    assert window.tab_widget.indexOf(window.memory_viewer) != -1

    window._display_memory('0x1000')
    assert window.tab_widget.currentWidget() is window.memory_viewer
    mock_gdb.read_memory.assert_called_once_with(0x1000, 256)
    assert '41 42' in window.memory_viewer.dump.toPlainText()

    # A register without a value is ignored
    mock_gdb.read_memory.reset_mock()
    window._display_memory('N/A')
    mock_gdb.read_memory.assert_not_called()
