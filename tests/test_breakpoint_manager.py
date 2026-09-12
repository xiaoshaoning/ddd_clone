"""
Unit tests for breakpoint manager.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock
import sys

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ddd_clone.gui.breakpoint_manager import BreakpointManager, Breakpoint, Watchpoint


class TestBreakpoint(unittest.TestCase):
    """Test cases for Breakpoint class."""

    def test_breakpoint_creation(self):
        """Test breakpoint creation."""
        bp = Breakpoint(1, "test.c", 10, "i > 5")

        self.assertEqual(bp.gdb_number, 1)
        self.assertEqual(bp.file, "test.c")
        self.assertEqual(bp.line, 10)
        self.assertEqual(bp.condition, "i > 5")
        self.assertTrue(bp.enabled)

    def test_breakpoint_creation_disabled(self):
        """A disabled breakpoint is created disabled, without mutation."""
        bp = Breakpoint(2, "test.c", 20, None, False)

        self.assertFalse(bp.enabled)

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
        """Saved breakpoints carry no session-local identity."""
        bp = Breakpoint(1, "test.c", 10, "i > 5")
        bp_dict = bp.to_dict()

        self.assertEqual(bp_dict, {
            'file': "test.c",
            'line': 10,
            'condition': "i > 5",
            'enabled': True
        })


class TestWatchpoint(unittest.TestCase):
    """Test cases for Watchpoint class."""

    def test_watchpoint_to_dict(self):
        """Saved watchpoints carry no session-local identity."""
        wp = Watchpoint(4, "count", "read")
        wp_dict = wp.to_dict()

        self.assertEqual(wp_dict, {
            'expression': "count",
            'type': "read",
            'enabled': True
        })


class TestBreakpointManager(unittest.TestCase):
    """Test cases for BreakpointManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_gdb = Mock()
        self.mock_gdb.get_breakpoints.return_value = []
        self.mock_gdb.set_breakpoint.return_value = 1
        self.mock_gdb.delete_breakpoint.return_value = True
        self.mock_gdb.enable_breakpoint.return_value = True
        self.mock_gdb.disable_breakpoint.return_value = True
        self.mock_gdb.set_breakpoint_condition.return_value = True
        self.mock_gdb.set_watchpoint.return_value = 2

        self.manager = BreakpointManager(self.mock_gdb)

    def test_refresh_projects_gdbs_list(self):
        """refresh() rebuilds both lists from GDB's breakpoint list."""
        self.mock_gdb.get_breakpoints.return_value = [
            {'number': 1, 'enabled': True, 'watchpoint': False,
             'file': 'test.c', 'line': 10, 'condition': 'i > 5'},
            {'number': 2, 'enabled': False, 'watchpoint': False,
             'file': 'test.c', 'line': 20, 'condition': None},
            {'number': 3, 'enabled': True, 'watchpoint': True,
             'expression': 'count', 'watch_type': 'read'},
        ]

        self.manager.refresh()

        self.assertEqual(sorted(self.manager.breakpoints), [1, 2])
        self.assertEqual(sorted(self.manager.watchpoints), [3])
        self.assertEqual(self.manager.breakpoints[1].condition, 'i > 5')
        self.assertFalse(self.manager.breakpoints[2].enabled)
        self.assertEqual(self.manager.watchpoints[3].expression, 'count')
        self.assertEqual(self.manager.watchpoints[3].watch_type, 'read')

    def test_refresh_replaces_stale_state(self):
        """A breakpoint deleted out of band disappears on refresh."""
        self.mock_gdb.get_breakpoints.return_value = [
            {'number': 1, 'enabled': True, 'watchpoint': False,
             'file': 'test.c', 'line': 10, 'condition': None},
        ]
        self.manager.refresh()

        self.mock_gdb.get_breakpoints.return_value = []
        self.manager.refresh()

        self.assertEqual(self.manager.breakpoints, {})

    def test_refresh_emits_changed(self):
        """refresh() tells the UI to re-read both lists."""
        breakpoints_changed = []
        watchpoints_changed = []
        self.manager.breakpoints_changed.connect(lambda: breakpoints_changed.append(True))
        self.manager.watchpoints_changed.connect(lambda: watchpoints_changed.append(True))

        self.manager.refresh()

        self.assertEqual(len(breakpoints_changed), 1)
        self.assertEqual(len(watchpoints_changed), 1)

    def test_add_breakpoint_success(self):
        """Test successful breakpoint addition, keyed by GDB's number."""
        bp = self.manager.add_breakpoint("test.c", 10, "i > 5")

        self.assertIsNotNone(bp)
        self.assertEqual(bp.file, "test.c")
        self.assertEqual(bp.line, 10)
        self.assertEqual(bp.condition, "i > 5")
        self.mock_gdb.set_breakpoint.assert_called_once_with("test.c", 10, "i > 5")
        self.assertEqual(bp.gdb_number, 1)
        self.assertIn(1, self.manager.breakpoints)

    def test_add_breakpoint_duplicate(self):
        """Test adding duplicate breakpoint."""
        bp1 = self.manager.add_breakpoint("test.c", 10)
        bp2 = self.manager.add_breakpoint("test.c", 10)

        self.assertEqual(bp1, bp2)
        self.mock_gdb.set_breakpoint.assert_called_once()

    def test_add_breakpoint_failure(self):
        """Test breakpoint addition failure."""
        self.mock_gdb.set_breakpoint.return_value = None

        bp = self.manager.add_breakpoint("test.c", 10)

        self.assertIsNone(bp)
        self.assertEqual(len(self.manager.breakpoints), 0)

    def test_remove_breakpoint_success(self):
        """Test successful breakpoint removal."""
        bp = self.manager.add_breakpoint("test.c", 10)

        result = self.manager.remove_breakpoint(bp.gdb_number)

        self.assertTrue(result)
        self.assertNotIn(bp.gdb_number, self.manager.breakpoints)
        self.mock_gdb.delete_breakpoint.assert_called_with(bp.gdb_number)

    def test_remove_breakpoint_nonexistent(self):
        """Test removing nonexistent breakpoint."""
        result = self.manager.remove_breakpoint(999)

        self.assertFalse(result)
        self.mock_gdb.delete_breakpoint.assert_not_called()

    def test_remove_breakpoint_gdb_failure(self):
        """A breakpoint GDB refused to delete is kept."""
        self.mock_gdb.delete_breakpoint.return_value = False
        bp = self.manager.add_breakpoint("test.c", 10)

        self.assertFalse(self.manager.remove_breakpoint(bp.gdb_number))
        self.assertIn(bp.gdb_number, self.manager.breakpoints)

    def test_toggle_breakpoint(self):
        """Test breakpoint toggling switches it in GDB by number."""
        bp = self.manager.add_breakpoint("test.c", 10)
        self.assertTrue(bp.enabled)

        result = self.manager.toggle_breakpoint(bp.gdb_number)

        self.assertTrue(result)
        self.assertFalse(bp.enabled)
        self.mock_gdb.disable_breakpoint.assert_called_once_with(bp.gdb_number)
        self.mock_gdb.set_breakpoint.assert_called_once()  # no re-insert

        result = self.manager.toggle_breakpoint(bp.gdb_number)
        self.assertTrue(result)
        self.assertTrue(bp.enabled)
        self.mock_gdb.enable_breakpoint.assert_called_once_with(bp.gdb_number)

    def test_update_breakpoint_condition_sets(self):
        """Setting a condition keeps GDB's breakpoint number."""
        bp = self.manager.add_breakpoint("test.c", 10)

        result = self.manager.update_breakpoint_condition(bp.gdb_number, "i == 0")

        self.assertTrue(result)
        self.assertEqual(bp.condition, "i == 0")
        self.mock_gdb.set_breakpoint_condition.assert_called_once_with(1, "i == 0")
        self.assertIn(1, self.manager.breakpoints)

    def test_update_breakpoint_condition_clears(self):
        """An empty condition removes it."""
        bp = self.manager.add_breakpoint("test.c", 10, "i == 0")

        result = self.manager.update_breakpoint_condition(bp.gdb_number, "")

        self.assertTrue(result)
        self.assertIsNone(bp.condition)

    def test_update_breakpoint_condition_failure(self):
        """A condition GDB rejects leaves the breakpoint unchanged."""
        bp = self.manager.add_breakpoint("test.c", 10, "i == 0")
        self.mock_gdb.set_breakpoint_condition.return_value = False

        self.assertFalse(self.manager.update_breakpoint_condition(bp.gdb_number, "junk"))
        self.assertEqual(bp.condition, "i == 0")

    def test_update_breakpoint_condition_unknown(self):
        """Updating an unknown breakpoint does nothing."""
        self.assertFalse(self.manager.update_breakpoint_condition(42, "i == 0"))

    def test_get_breakpoints(self):
        """Test getting all breakpoints."""
        bp1 = self.manager.add_breakpoint("test1.c", 10)
        self.mock_gdb.set_breakpoint.return_value = 2
        bp2 = self.manager.add_breakpoint("test2.c", 20)

        breakpoints = self.manager.get_breakpoints()

        self.assertEqual(len(breakpoints), 2)
        self.assertIn(bp1, breakpoints)
        self.assertIn(bp2, breakpoints)

    def test_clear_all_breakpoints_leaves_watchpoints(self):
        """Clearing breakpoints does not touch watchpoints."""
        self.manager.add_breakpoint("test1.c", 10)
        self.mock_gdb.set_breakpoint.return_value = 2
        self.manager.add_breakpoint("test2.c", 20)
        self.manager.add_watchpoint("x")

        self.manager.clear_all_breakpoints()

        self.assertEqual(len(self.manager.breakpoints), 0)
        self.assertEqual(len(self.manager.watchpoints), 1)
        self.assertEqual(self.mock_gdb.delete_breakpoint.call_count, 2)

    def test_add_watchpoint_records_gdb_number(self):
        """A watchpoint is keyed by GDB's number."""
        wp = self.manager.add_watchpoint("x", "write")

        self.assertIsNotNone(wp)
        self.mock_gdb.set_watchpoint.assert_called_once_with("x", "write")
        self.assertEqual(wp.gdb_number, 2)
        self.assertIn(2, self.manager.watchpoints)

    def test_add_watchpoint_failure(self):
        """A watchpoint GDB rejects is not stored."""
        self.mock_gdb.set_watchpoint.return_value = None

        self.assertIsNone(self.manager.add_watchpoint("x"))
        self.assertEqual(self.manager.get_watchpoints(), [])

    def test_remove_watchpoint(self):
        """Removing a watchpoint addresses GDB's number."""
        wp = self.manager.add_watchpoint("x")

        self.assertTrue(self.manager.remove_watchpoint(wp.gdb_number))
        self.mock_gdb.delete_breakpoint.assert_called_once_with(2)
        self.assertEqual(self.manager.get_watchpoints(), [])

    def test_toggle_watchpoint(self):
        """Watchpoints toggle in place, like breakpoints."""
        wp = self.manager.add_watchpoint("x")

        self.assertTrue(self.manager.toggle_watchpoint(wp.gdb_number))
        self.assertFalse(wp.enabled)
        self.mock_gdb.disable_breakpoint.assert_called_once_with(2)

        self.assertTrue(self.manager.toggle_watchpoint(wp.gdb_number))
        self.assertTrue(wp.enabled)
        self.mock_gdb.enable_breakpoint.assert_called_once_with(2)

    def test_update_watchpoint_expression_renumbers(self):
        """GDB cannot edit a watchpoint in place, so the number changes."""
        wp = self.manager.add_watchpoint("x")
        self.mock_gdb.set_watchpoint.return_value = 9

        result = self.manager.update_watchpoint_expression(wp.gdb_number, "y", "read")

        self.assertTrue(result)
        self.assertEqual(wp.expression, "y")
        self.assertEqual(wp.watch_type, "read")
        self.assertEqual(wp.gdb_number, 9)
        self.assertNotIn(2, self.manager.watchpoints)
        self.assertIn(9, self.manager.watchpoints)
        self.mock_gdb.delete_breakpoint.assert_called_once_with(2)

    def test_clear_all_watchpoints_leaves_breakpoints(self):
        """Clearing watchpoints does not touch breakpoints."""
        self.manager.add_breakpoint("test.c", 10)
        self.manager.add_watchpoint("x")

        self.manager.clear_all_watchpoints()

        self.assertEqual(len(self.manager.watchpoints), 0)
        self.assertEqual(len(self.manager.breakpoints), 1)

    def test_save_and_load_round_trip(self):
        """Saved breakpoints and watchpoints come back through GDB."""
        self.manager.add_breakpoint("test.c", 10, "i > 5")
        self.manager.add_watchpoint("x", "read")

        handle, path = tempfile.mkstemp(suffix='.json')
        os.close(handle)
        try:
            self.assertTrue(self.manager.save_breakpoints_to_file(path))
            saved = json.load(open(path))
            self.assertEqual(saved['breakpoints'], [
                {'file': 'test.c', 'line': 10, 'condition': 'i > 5', 'enabled': True},
            ])
            self.assertEqual(saved['watchpoints'], [
                {'expression': 'x', 'type': 'read', 'enabled': True},
            ])

            self.assertTrue(self.manager.load_breakpoints_from_file(path))
            self.mock_gdb.set_breakpoint.assert_called_with("test.c", 10, "i > 5")
            self.mock_gdb.set_watchpoint.assert_called_with("x", "read")
        finally:
            os.remove(path)


if __name__ == '__main__':
    unittest.main()
