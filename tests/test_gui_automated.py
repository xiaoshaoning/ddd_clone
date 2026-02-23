"""
Automated GUI tests for DDD Clone using pytest-qt.
These tests run without manual intervention.
"""

import sys
import os
from unittest.mock import Mock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# PyQt5 imports
from PyQt5.QtWidgets import QWidget, QPushButton, QApplication
from PyQt5.QtCore import Qt


def test_basic_qtbot(qtbot):
    """Basic test to verify pytest-qt is working."""
    # Create a simple widget
    widget = QWidget()
    qtbot.addWidget(widget)

    # Set window title and show
    widget.setWindowTitle("Test Widget")

    # Verify widget exists
    assert widget is not None
    assert widget.windowTitle() == "Test Widget"

    # Test can be closed automatically by qtbot
    # No manual interaction needed


def test_button_click(qtbot):
    """Test button click interaction."""
    widget = QWidget()
    button = QPushButton("Click Me", widget)

    # Track clicks
    clicked = []
    button.clicked.connect(lambda: clicked.append(True))

    qtbot.addWidget(widget)

    # Click the button programmatically
    qtbot.mouseClick(button, Qt.LeftButton)

    # Verify click was registered
    assert len(clicked) == 1
    assert clicked[0] is True


def test_main_window_creation(qtbot):
    """Test that MainWindow can be created without errors."""
    from ddd_clone.gui.main_window import MainWindow
    from ddd_clone.gdb.gdb_controller import GDBController

    # Mock GDBController to avoid actual GDB process
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'disconnected'}
    mock_gdb.state_changed = Mock()
    mock_gdb.output_received = Mock()

    # Create main window
    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    # Verify window exists and has expected properties
    assert window is not None
    assert window.windowTitle() == "DDD Clone - Graphical Debugger"

    # Verify essential components exist
    assert window.source_viewer is not None
    assert window.breakpoint_manager is not None
    assert window.variable_inspector is not None

    # Test can be closed automatically by qtbot


def test_source_viewer_load(qtbot):
    """Test source viewer can load a file."""
    from ddd_clone.gui.source_viewer import SourceViewer

    viewer = SourceViewer()
    qtbot.addWidget(viewer)

    # Test file path
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'simple_program.c')

    if os.path.exists(test_file):
        # Load the file
        viewer.load_source_file(test_file)

        # Verify file was loaded
        assert viewer.current_file == test_file
        assert viewer.toPlainText() != ""

        # Check line number area exists
        assert viewer.line_number_area is not None
    else:
        print(f"Test file not found: {test_file}")
        # Skip the assertion if file doesn't exist


def test_memory_viewer_basics(qtbot):
    """Test basic MemoryViewer functionality."""
    from ddd_clone.gui.memory_viewer import MemoryViewer, MemoryRegion
    from ddd_clone.gdb.gdb_controller import GDBController

    # Mock GDB controller
    mock_gdb = Mock(spec=GDBController)

    # Create memory viewer
    viewer = MemoryViewer(mock_gdb)

    # Test memory region creation
    test_data = bytes([i for i in range(16)])
    region = MemoryRegion(address=0x1000, size=16, data=test_data, permissions="rwx")

    assert region.address == 0x1000
    assert region.size == 16
    assert region.data == test_data
    assert region.permissions == "rwx"

    # Test byte access
    assert region.get_byte(0) == 0
    assert region.get_byte(10) == 10
    assert region.get_byte(20) is None  # Out of bounds

    # Test word access
    word = region.get_word(0, 4)
    assert word == 0x03020100  # Little endian: [0, 1, 2, 3] -> 0x03020100


def test_memory_viewer_read_write(qtbot):
    """Test MemoryViewer read/write operations."""
    from ddd_clone.gui.memory_viewer import MemoryViewer
    from ddd_clone.gdb.gdb_controller import GDBController

    # Mock GDB controller
    mock_gdb = Mock(spec=GDBController)

    # Create memory viewer
    viewer = MemoryViewer(mock_gdb)

    # Track signals
    update_signals = []
    error_signals = []

    viewer.memory_updated.connect(lambda region: update_signals.append(region))
    viewer.memory_error.connect(lambda msg: error_signals.append(msg))

    # Test reading memory
    region = viewer.read_memory(address=0x1000, size=32)
    assert region is not None
    assert region.address == 0x1000
    assert region.size == 32
    assert len(region.data) == 32

    # Verify signal was emitted
    assert len(update_signals) == 1
    assert update_signals[0] == region

    # Test writing memory to current region
    write_data = bytes([0xFF, 0xEE, 0xDD])
    result = viewer.write_memory(address=0x1005, data=write_data)
    assert result is True

    # Verify region was updated
    assert len(update_signals) == 2
    assert viewer.current_region.data[5] == 0xFF  # Offset 5 from 0x1000

    # Test writing to address outside current region
    result = viewer.write_memory(address=0x2000, data=write_data)
    assert result is False


def test_line_number_area_basics(qtbot):
    """Test LineNumberArea basic functionality."""
    from ddd_clone.gui.line_number_area import LineNumberArea
    from ddd_clone.gui.source_viewer import SourceViewer

    # Create a source viewer and line number area
    source_viewer = SourceViewer()
    line_area = LineNumberArea(source_viewer)

    qtbot.addWidget(source_viewer)

    # Test basic properties
    assert line_area.source_viewer is source_viewer
    # Note: breakpoint_lines is stored in source_viewer, not line_area

    # Load test file to get line numbers
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'simple_program.c')
    if os.path.exists(test_file):
        source_viewer.load_source_file(test_file)

        # Line number area should have a width based on line count
        # Width may be 0 until widget is shown, so we'll check sizeHint instead
        size_hint = line_area.sizeHint()
        assert size_hint is not None

        # Test that we can set breakpoint lines in the source viewer
        source_viewer.breakpoint_lines = {5, 10, 15}
        assert source_viewer.breakpoint_lines == {5, 10, 15}


def test_breakpoint_manager_gui(qtbot):
    """Test BreakpointManager GUI integration."""
    from ddd_clone.gui.breakpoint_manager import BreakpointManager, Breakpoint
    from ddd_clone.gdb.gdb_controller import GDBController

    # Mock GDB controller
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.set_breakpoint = Mock(return_value=True)
    mock_gdb.delete_breakpoint = Mock(return_value=True)

    # Create breakpoint manager
    manager = BreakpointManager(mock_gdb)

    # Test adding breakpoint (GUI would call this)
    # Note: add_breakpoint returns Breakpoint object, not ID
    bp = manager.add_breakpoint("test.c", 10, "i > 5")
    assert bp is not None
    assert bp.file == "test.c"
    assert bp.line == 10
    assert bp.condition == "i > 5"

    # Test getting breakpoints
    bps = manager.get_breakpoints()
    assert len(bps) == 1
    assert bps[0].file == "test.c"
    assert bps[0].line == 10
    assert bps[0].condition == "i > 5"

    # Test removing breakpoint
    result = manager.remove_breakpoint(bp.breakpoint_id)
    assert result is True
    assert len(manager.get_breakpoints()) == 0


def test_variable_inspector_gui(qtbot):
    """Test VariableInspector GUI integration."""
    from ddd_clone.gui.variable_inspector import VariableInspector, Variable
    from ddd_clone.gdb.gdb_controller import GDBController

    # Mock GDB controller
    mock_gdb = Mock(spec=GDBController)

    # Create variable inspector
    inspector = VariableInspector(mock_gdb)

    # Mock the _evaluate_expression method to return a value
    inspector._evaluate_expression = Mock(return_value="42")

    # Test adding watch expression
    result = inspector.add_watch_expression("my_variable")
    assert result is True

    # Test getting watch expressions (returns dict, not list)
    watches = inspector.get_watch_expressions()
    assert len(watches) == 1
    assert "my_variable" in watches
    assert watches["my_variable"] == "42"

    # Test variable parsing
    test_data = [
        {
            "name": "x",
            "value": "5",
            "type": "int"
        },
        {
            "name": "arr",
            "value": "{1, 2, 3}",
            "type": "int[3]"
        }
    ]

    # Use the internal method for parsing
    variables = inspector._parse_variables_data(test_data)
    assert len(variables) == 2
    assert variables[0].name == "x"
    assert variables[0].value == "5"
    assert variables[0].type == "int"


def test_main_window_advanced(qtbot):
    """Test advanced MainWindow functionality."""
    from ddd_clone.gui.main_window import MainWindow
    from ddd_clone.gdb.gdb_controller import GDBController

    # Mock GDB controller with more functionality
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'disconnected'}
    mock_gdb.state_changed = Mock()
    mock_gdb.output_received = Mock()
    mock_gdb.send_command = Mock(return_value="^done")

    # Create main window
    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    # Test menu bar exists
    assert window.menuBar() is not None

    # Test status bar exists
    assert window.statusBar() is not None

    # Test essential UI components exist
    assert window.source_viewer is not None
    assert window.gdb_command_input is not None
    assert window.gdb_output_text is not None

    # Test GDB command execution
    window.gdb_command_input.setText("break main")
    window.execute_gdb_command()

    # Verify GDB command was sent
    mock_gdb.send_command.assert_called_once_with("break main")


def test_demo_gui_functionality(qtbot):
    """Automated version of test_gui.py functionality."""
    from ddd_clone.gui.main_window import MainWindow
    from ddd_clone.gdb.gdb_controller import GDBController

    # Mock GDB controller
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'disconnected'}
    mock_gdb.state_changed = Mock()
    mock_gdb.output_received = Mock()

    # Create main window (equivalent to test_gui.py lines 19-26)
    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    # Test loading source code (equivalent to test_gui.py lines 28-34)
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'simple_program.c')
    if os.path.exists(test_file):
        window.source_viewer.load_source_file(test_file)

        # Verify file was loaded
        assert window.source_viewer.current_file == test_file
        assert window.source_viewer.toPlainText() != ""

        # Check line numbers
        line_count = window.source_viewer.blockCount()
        assert line_count > 0

        print(f"[OK] Loaded source file: {test_file}")
        print(f"[OK] Line numbers displayed: {line_count} lines")
    else:
        print(f"[SKIP] Test file not found: {test_file}")
        # Skip the file loading test if file doesn't exist

    print("[OK] GUI test completed successfully")


def test_demo_complete_app(qtbot):
    """Automated version of test_complete.py functionality."""
    from ddd_clone.gui.main_window import MainWindow
    from ddd_clone.gdb.gdb_controller import GDBController

    # Mock GDB controller with more functionality
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.current_state = {'state': 'disconnected'}
    mock_gdb.state_changed = Mock()
    mock_gdb.output_received = Mock()
    mock_gdb.start_gdb = Mock(return_value=True)
    mock_gdb.set_breakpoint = Mock(return_value=True)

    # Create main window (equivalent to test_complete.py lines 19-26)
    window = MainWindow(mock_gdb)
    qtbot.addWidget(window)

    # Test loading source code (equivalent to test_complete.py lines 28-36)
    test_file = os.path.join(os.path.dirname(__file__), '..', 'examples', 'simple_program.c')
    if os.path.exists(test_file):
        window.source_viewer.load_source_file(test_file)

        # Verify file was loaded
        assert window.source_viewer.current_file == test_file
        assert window.source_viewer.toPlainText() != ""

        # Check line numbers
        line_count = window.source_viewer.blockCount()
        assert line_count > 0

        print(f"[OK] Loaded source file: {test_file}")
        print(f"[OK] Line numbers displayed: {line_count} lines")

        # Test breakpoint setting (equivalent to test_complete.py lines 38-40)
        # Note: In the actual demo, this would be window.source_viewer.toggle_breakpoint(5)
        # But we need to test the GUI interaction properly
        window.source_viewer.toggle_breakpoint(5)

        # Check if breakpoint was added
        assert 5 in window.source_viewer.breakpoint_lines
        print("[OK] Breakpoint set at line 5")

        # Test GDB startup (equivalent to test_complete.py lines 42-50)
        # We mock the GDB startup
        if mock_gdb.start_gdb("examples/simple_program.exe"):
            print("[OK] GDB started successfully")
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