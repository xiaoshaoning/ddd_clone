"""
Unit tests for the memory viewer.
"""

import os
import sys
from unittest.mock import Mock

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ddd_clone.gui.memory_viewer import MemoryViewer
from ddd_clone.gdb.gdb_controller import GDBController


def test_format_dump():
    """A dump shows address, hex bytes and printable ASCII."""
    data = bytes(range(0x40, 0x50)) + b'\x00\x01\x7f'
    lines = MemoryViewer.format_dump(0x1000, data).splitlines()

    assert lines[0].startswith('0x00001000  40 41 42 43')
    assert lines[0].endswith('@ABCDEFGHIJKLMNO')
    assert lines[1].startswith('0x00001010  00 01 7f')
    assert lines[1].endswith('...')


def test_set_address_literal(qtbot):
    """A literal address is read directly, without evaluating it."""
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.read_memory.return_value = b'ABCD'

    viewer = MemoryViewer(mock_gdb)
    qtbot.addWidget(viewer)

    assert viewer.set_address('0x1000') is True
    mock_gdb.read_memory.assert_called_once_with(0x1000, MemoryViewer.BYTE_COUNT)
    assert '41 42 43 44' in viewer.dump.toPlainText()
    mock_gdb.evaluate_expression.assert_not_called()


def test_set_address_expression(qtbot):
    """A GDB expression is evaluated to an address first."""
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.evaluate_expression.return_value = '(struct Point *) 0x5ffe78'
    mock_gdb.read_memory.return_value = b'\x01\x02'

    viewer = MemoryViewer(mock_gdb)
    qtbot.addWidget(viewer)

    assert viewer.set_address('&origin') is True
    mock_gdb.evaluate_expression.assert_called_once_with('&origin')
    mock_gdb.read_memory.assert_called_once_with(0x5ffe78, MemoryViewer.BYTE_COUNT)


def test_refresh_without_address(qtbot):
    """Refreshing before an address is set does nothing."""
    mock_gdb = Mock(spec=GDBController)
    viewer = MemoryViewer(mock_gdb)
    qtbot.addWidget(viewer)

    assert viewer.refresh() is False
    mock_gdb.read_memory.assert_not_called()


def test_refresh_reuses_address(qtbot):
    """Refreshing re-reads the address set most recently."""
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.read_memory.return_value = b'\x01'

    viewer = MemoryViewer(mock_gdb)
    qtbot.addWidget(viewer)
    assert viewer.set_address('0x2000') is True
    mock_gdb.read_memory.reset_mock()

    assert viewer.refresh() is True
    mock_gdb.read_memory.assert_called_once_with(0x2000, MemoryViewer.BYTE_COUNT)


def test_unreadable_address_reports(qtbot):
    """A failure is reported instead of dumping garbage."""
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.evaluate_expression.return_value = None

    viewer = MemoryViewer(mock_gdb)
    qtbot.addWidget(viewer)

    assert viewer.set_address('nosuchthing') is False
    assert 'Cannot resolve' in viewer.dump.toPlainText()

    mock_gdb.read_memory.return_value = None
    assert viewer.set_address('0x1000') is False
    assert 'Cannot read memory' in viewer.dump.toPlainText()


def test_size_selector_default_and_change(qtbot):
    """The size selector re-reads the same address at the new size."""
    mock_gdb = Mock(spec=GDBController)
    mock_gdb.read_memory.return_value = b'\x01'

    viewer = MemoryViewer(mock_gdb)
    qtbot.addWidget(viewer)
    assert viewer.size_combo.currentText() == str(MemoryViewer.BYTE_COUNT)

    assert viewer.set_address('0x2000') is True
    mock_gdb.read_memory.reset_mock()

    viewer.size_combo.setCurrentText('512')

    mock_gdb.read_memory.assert_called_once_with(0x2000, 512)
    assert viewer.byte_count == 512
