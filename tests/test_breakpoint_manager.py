"""
Unit tests for breakpoint manager.
"""

import unittest
from unittest.mock import Mock
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ddd_clone.gui.breakpoint_manager import BreakpointManager, Breakpoint


class TestBreakpoint(unittest.TestCase):
    """Test cases for Breakpoint class."""

    def test_breakpoint_creation(self):
        """Test breakpoint creation."""
        bp = Breakpoint(1, "test.c", 10, "i > 5")

        self.assertEqual(bp.breakpoint_id, 1)
        self.assertEqual(bp.file, "test.c")
        self.assertEqual(bp.line, 10)
        self.assertEqual(bp.condition, "i > 5")
        self.assertEqual(bp.gdb_number, None)
        self.assertTrue(bp.enabled)

    def test_breakpoint_string_representation(self):
        """Test breakpoint string representation."""
        # With condition
        bp = Breakpoint(1, "test.c", 10, "i > 5")
        self.assertEqual(str(bp), "test.c:10 [i > 5]")

        # Without condition
        bp = Breakpoint(2, "test.c", 20)
        self.assertEqual(str(bp), "test.c:20")

        # Disabled
        bp.enabled = False
        self.assertEqual(str(bp), "test.c:20 (disabled)")

    def test_breakpoint_to_dict(self):
        """Test breakpoint to dictionary conversion."""
        bp = Breakpoint(1, "test.c", 10, "i > 5")
        bp_dict = bp.to_dict()

        expected = {
            'id': 1,
            'file': "test.c",
            'line': 10,
            'condition': "i > 5",
            'enabled': True
        }

        self.assertEqual(bp_dict, expected)


class TestBreakpointManager(unittest.TestCase):
    """Test cases for BreakpointManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_gdb = Mock()
        self.mock_gdb.set_breakpoint.return_value = 1
        self.mock_gdb.delete_breakpoint.return_value = True
        self.mock_gdb.enable_breakpoint.return_value = True
        self.mock_gdb.disable_breakpoint.return_value = True
        self.mock_gdb.set_watchpoint.return_value = 2

        self.manager = BreakpointManager(self.mock_gdb)

    def test_add_breakpoint_success(self):
        """Test successful breakpoint addition."""
        bp = self.manager.add_breakpoint("test.c", 10, "i > 5")

        # Verify breakpoint was created
        self.assertIsNotNone(bp)
        self.assertEqual(bp.file, "test.c")
        self.assertEqual(bp.line, 10)
        self.assertEqual(bp.condition, "i > 5")

        # Verify GDB was called and its number was recorded
        self.mock_gdb.set_breakpoint.assert_called_once_with("test.c", 10, "i > 5")
        self.assertEqual(bp.gdb_number, 1)

        # Verify breakpoint is stored
        self.assertIn(bp.breakpoint_id, self.manager.breakpoints)

    def test_add_breakpoint_duplicate(self):
        """Test adding duplicate breakpoint."""
        # Add first breakpoint
        bp1 = self.manager.add_breakpoint("test.c", 10)

        # Try to add duplicate
        bp2 = self.manager.add_breakpoint("test.c", 10)

        # Should return existing breakpoint
        self.assertEqual(bp1, bp2)
        # GDB should only be called once
        self.mock_gdb.set_breakpoint.assert_called_once()

    def test_add_breakpoint_failure(self):
        """Test breakpoint addition failure."""
        self.mock_gdb.set_breakpoint.return_value = None

        bp = self.manager.add_breakpoint("test.c", 10)

        # Should return None
        self.assertIsNone(bp)
        # No breakpoint should be stored
        self.assertEqual(len(self.manager.breakpoints), 0)

    def test_remove_breakpoint_success(self):
        """Test successful breakpoint removal."""
        # Add a breakpoint
        bp = self.manager.add_breakpoint("test.c", 10)
        bp_id = bp.breakpoint_id

        # Remove the breakpoint
        result = self.manager.remove_breakpoint(bp_id)

        # Verify removal
        self.assertTrue(result)
        self.assertNotIn(bp_id, self.manager.breakpoints)
        # GDB is addressed by its own breakpoint number, not our id
        self.mock_gdb.delete_breakpoint.assert_called_with(bp.gdb_number)

    def test_remove_breakpoint_without_gdb_number(self):
        """A breakpoint GDB never accepted is dropped locally."""
        bp = Breakpoint(1, "test.c", 10, None, None)
        self.manager.breakpoints[1] = bp

        self.assertTrue(self.manager.remove_breakpoint(1))
        self.mock_gdb.delete_breakpoint.assert_not_called()

    def test_remove_breakpoint_nonexistent(self):
        """Test removing nonexistent breakpoint."""
        result = self.manager.remove_breakpoint(999)

        # Should return False
        self.assertFalse(result)
        # GDB should not be called
        self.mock_gdb.delete_breakpoint.assert_not_called()

    def test_toggle_breakpoint(self):
        """Test breakpoint toggling switches it in GDB by number."""
        # Add a breakpoint
        bp = self.manager.add_breakpoint("test.c", 10)
        self.assertTrue(bp.enabled)

        # Toggle breakpoint off
        result = self.manager.toggle_breakpoint(bp.breakpoint_id)

        # Verify toggling
        self.assertTrue(result)
        self.assertFalse(bp.enabled)
        self.mock_gdb.disable_breakpoint.assert_called_once_with(bp.gdb_number)
        self.mock_gdb.set_breakpoint.assert_called_once()  # no re-insert

        # Toggle back on
        result = self.manager.toggle_breakpoint(bp.breakpoint_id)
        self.assertTrue(result)
        self.assertTrue(bp.enabled)
        self.mock_gdb.enable_breakpoint.assert_called_once_with(bp.gdb_number)

    def test_update_breakpoint_condition(self):
        """Test updating breakpoint condition re-inserts and re-captures the number."""
        # Add a breakpoint
        bp = self.manager.add_breakpoint("test.c", 10)
        self.mock_gdb.set_breakpoint.return_value = 7

        # Update condition
        result = self.manager.update_breakpoint_condition(bp.breakpoint_id, "i == 0")

        # Verify update
        self.assertTrue(result)
        self.assertEqual(bp.condition, "i == 0")
        self.assertEqual(bp.gdb_number, 7)
        self.mock_gdb.delete_breakpoint.assert_called_once_with(1)

    def test_get_breakpoints(self):
        """Test getting all breakpoints."""
        # Add multiple breakpoints
        bp1 = self.manager.add_breakpoint("test1.c", 10)
        bp2 = self.manager.add_breakpoint("test2.c", 20)

        # Get all breakpoints
        breakpoints = self.manager.get_breakpoints()

        # Verify all breakpoints are returned
        self.assertEqual(len(breakpoints), 2)
        self.assertIn(bp1, breakpoints)
        self.assertIn(bp2, breakpoints)

    def test_get_breakpoints_in_file(self):
        """Test getting breakpoints in specific file."""
        # Add breakpoints in different files
        bp1 = self.manager.add_breakpoint("test.c", 10)
        bp2 = self.manager.add_breakpoint("test.c", 20)
        bp3 = self.manager.add_breakpoint("other.c", 30)

        # Get breakpoints in test.c
        breakpoints = self.manager.get_breakpoints_in_file("test.c")

        # Verify only breakpoints in test.c are returned
        self.assertEqual(len(breakpoints), 2)
        self.assertIn(bp1, breakpoints)
        self.assertIn(bp2, breakpoints)
        self.assertNotIn(bp3, breakpoints)

    def test_clear_all_breakpoints(self):
        """Test clearing all breakpoints."""
        # Add multiple breakpoints
        self.manager.add_breakpoint("test1.c", 10)
        self.manager.add_breakpoint("test2.c", 20)

        # Clear all breakpoints
        self.manager.clear_all_breakpoints()

        # Verify all breakpoints are removed
        self.assertEqual(len(self.manager.breakpoints), 0)
        # GDB delete should be called twice
        self.assertEqual(self.mock_gdb.delete_breakpoint.call_count, 2)

    def test_add_watchpoint_records_gdb_number(self):
        """A watchpoint records GDB's number for later enable/delete."""
        wp = self.manager.add_watchpoint("x", "write")

        self.assertIsNotNone(wp)
        self.mock_gdb.set_watchpoint.assert_called_once_with("x", "write")
        self.assertEqual(wp.gdb_number, 2)

    def test_add_watchpoint_failure(self):
        """A watchpoint GDB rejects is not stored."""
        self.mock_gdb.set_watchpoint.return_value = None

        self.assertIsNone(self.manager.add_watchpoint("x"))
        self.assertEqual(self.manager.get_watchpoints(), [])

    def test_remove_watchpoint_uses_gdb_number(self):
        """Removing a watchpoint addresses GDB's number, not our own id."""
        wp = self.manager.add_watchpoint("x")

        self.assertTrue(self.manager.remove_watchpoint(wp.watchpoint_id))
        self.mock_gdb.delete_breakpoint.assert_called_once_with(2)
        self.assertEqual(self.manager.get_watchpoints(), [])

    def test_toggle_watchpoint_uses_gdb_number(self):
        """Watchpoints toggle in place, like breakpoints."""
        wp = self.manager.add_watchpoint("x")

        self.assertTrue(self.manager.toggle_watchpoint(wp.watchpoint_id))
        self.assertFalse(wp.enabled)
        self.mock_gdb.disable_breakpoint.assert_called_once_with(2)

        self.assertTrue(self.manager.toggle_watchpoint(wp.watchpoint_id))
        self.assertTrue(wp.enabled)
        self.mock_gdb.enable_breakpoint.assert_called_once_with(2)


if __name__ == '__main__':
    unittest.main()