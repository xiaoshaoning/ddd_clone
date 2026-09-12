"""
Breakpoint and watchpoint manager for handling breakpoints and watchpoints in the debugger.
"""

import json
import os

from typing import Dict, List, Optional
from PyQt5.QtCore import QObject, pyqtSignal


class Breakpoint:
    """
    Represents a single breakpoint.
    """

    def __init__(self, gdb_number: int, file: str, line: int,
                 condition: Optional[str] = None, enabled: bool = True):
        self.gdb_number = gdb_number  # GDB's breakpoint number, and our identity
        self.file = file
        self.line = line
        self.condition = condition
        self.enabled = enabled

    def __str__(self):
        condition_str = f" [{self.condition}]" if self.condition else ""
        enabled_str = "" if self.enabled else " (disabled)"
        return f"{self.file}:{self.line}{condition_str}{enabled_str}"

    def to_dict(self) -> Dict:
        """Convert breakpoint to dictionary for saving (nothing session-local)."""
        return {
            'file': self.file,
            'line': self.line,
            'condition': self.condition,
            'enabled': self.enabled
        }


class Watchpoint:
    """
    Represents a single watchpoint.
    """

    def __init__(self, gdb_number: int, expression: str, watch_type: str = "write",
                 enabled: bool = True):
        self.gdb_number = gdb_number  # GDB's breakpoint number, and our identity
        self.expression = expression
        self.watch_type = watch_type  # "write", "read", "access"
        self.enabled = enabled

    def __str__(self):
        type_str = f" ({self.watch_type})" if self.watch_type != "write" else ""
        enabled_str = "" if self.enabled else " (disabled)"
        return f"{self.expression}{type_str}{enabled_str}"

    def to_dict(self) -> Dict:
        """Convert watchpoint to dictionary for saving (nothing session-local)."""
        return {
            'expression': self.expression,
            'type': self.watch_type,
            'enabled': self.enabled
        }


class BreakpointManager(QObject):
    """
    Mirrors the breakpoints and watchpoints GDB has.

    GDB owns that list; this class only projects it for the UI. Anything that
    changes it out of band - a `break` or `delete` typed at the console, a
    watchpoint firing - is picked up by refresh() rather than tracked here.
    """

    # One signal per list: the UI re-reads the list, so a payload would never
    # be used.
    breakpoints_changed = pyqtSignal()
    watchpoints_changed = pyqtSignal()

    def __init__(self, gdb_controller):
        super().__init__()
        self.gdb_controller = gdb_controller
        self.breakpoints: Dict[int, Breakpoint] = {}  # keyed by GDB number
        self.watchpoints: Dict[int, Watchpoint] = {}  # keyed by GDB number

    def refresh(self) -> None:
        """
        Rebuild both lists from GDB.

        The lists are replaced rather than patched: GDB is the only owner of
        the breakpoint set, so there is no local state worth preserving.
        """
        breakpoints = {}
        watchpoints = {}
        for entry in self.gdb_controller.get_breakpoints():
            number = entry['number']
            if entry['watchpoint']:
                watchpoints[number] = Watchpoint(
                    number, entry['expression'], entry['watch_type'], entry['enabled'])
            else:
                breakpoints[number] = Breakpoint(
                    number, entry['file'], entry['line'],
                    entry['condition'], entry['enabled'])

        self.breakpoints = breakpoints
        self.watchpoints = watchpoints
        self.breakpoints_changed.emit()
        self.watchpoints_changed.emit()

    # Breakpoint management methods
    def add_breakpoint(self, file: str, line: int,
                       condition: Optional[str] = None) -> Optional[Breakpoint]:
        """
        Add a breakpoint, or return the one already at that location.

        Args:
            file: Source file path
            line: Line number
            condition: Optional breakpoint condition

        Returns:
            Breakpoint object, or None if GDB rejected the location
        """
        existing_bp = self._find_breakpoint(file, line)
        if existing_bp:
            return existing_bp

        gdb_number = self.gdb_controller.set_breakpoint(file, line, condition)
        if gdb_number is None:
            # GDB rejected the location - don't add it to our mirror
            return None

        breakpoint = Breakpoint(gdb_number, file, line, condition)
        self.breakpoints[gdb_number] = breakpoint
        self.breakpoints_changed.emit()
        return breakpoint

    def remove_breakpoint(self, gdb_number: int) -> bool:
        """
        Remove a breakpoint.

        Args:
            gdb_number: GDB's breakpoint number

        Returns:
            bool: True if breakpoint was removed successfully
        """
        if gdb_number not in self.breakpoints:
            return False

        if not self.gdb_controller.delete_breakpoint(gdb_number):
            return False

        del self.breakpoints[gdb_number]
        self.breakpoints_changed.emit()
        return True

    def toggle_breakpoint(self, gdb_number: int) -> bool:
        """
        Toggle breakpoint enabled/disabled state.

        Args:
            gdb_number: GDB's breakpoint number

        Returns:
            bool: True if breakpoint was toggled successfully
        """
        breakpoint = self.breakpoints.get(gdb_number)
        if breakpoint is None:
            return False

        # GDB can enable/disable a breakpoint in place; the number is stable.
        if breakpoint.enabled:
            if not self.gdb_controller.disable_breakpoint(gdb_number):
                return False
            breakpoint.enabled = False
        else:
            if not self.gdb_controller.enable_breakpoint(gdb_number):
                return False
            breakpoint.enabled = True

        self.breakpoints_changed.emit()
        return True

    def update_breakpoint_condition(self, gdb_number: int,
                                    condition: Optional[str]) -> bool:
        """
        Set a breakpoint's condition.

        Args:
            gdb_number: GDB's breakpoint number
            condition: New condition, or None/'' to remove the condition

        Returns:
            bool: True if breakpoint was updated successfully
        """
        breakpoint = self.breakpoints.get(gdb_number)
        if breakpoint is None:
            return False

        if not self.gdb_controller.set_breakpoint_condition(gdb_number, condition):
            return False

        breakpoint.condition = condition or None
        self.breakpoints_changed.emit()
        return True

    def get_breakpoint(self, gdb_number: int) -> Optional[Breakpoint]:
        """
        Get breakpoint by GDB's breakpoint number.

        Args:
            gdb_number: GDB's breakpoint number

        Returns:
            Breakpoint object if found, None otherwise
        """
        return self.breakpoints.get(gdb_number)

    def get_breakpoints(self) -> List[Breakpoint]:
        """
        Get all breakpoints.

        Returns:
            List of all breakpoints
        """
        return list(self.breakpoints.values())

    def get_breakpoints_in_file(self, file_path: str) -> List[Breakpoint]:
        """
        Get all breakpoints in a specific file.

        Args:
            file_path: Path to the source file

        Returns:
            List of breakpoints in the file
        """
        return [bp for bp in self.breakpoints.values() if bp.file == file_path]

    def clear_all_breakpoints(self):
        """Clear all breakpoints, leaving watchpoints alone."""
        for gdb_number in list(self.breakpoints.keys()):
            self.remove_breakpoint(gdb_number)

    def _find_breakpoint(self, file: str, line: int) -> Optional[Breakpoint]:
        """
        Find breakpoint at specific file and line.

        Args:
            file: Source file path
            line: Line number

        Returns:
            Breakpoint object if found, None otherwise
        """
        for breakpoint in self.breakpoints.values():
            if breakpoint.file == file and breakpoint.line == line:
                return breakpoint
        return None

    def load_breakpoints_from_file(self, file_path: str) -> bool:
        """
        Replace the current breakpoints and watchpoints with those in a file.

        Args:
            file_path: Path to breakpoints file

        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                return False

            with open(file_path, 'r') as f:
                data = json.load(f)

            self.clear_all_breakpoints()
            self.clear_all_watchpoints()

            # GDB assigns the numbers, so the saved ones are not restored
            for bp_data in data.get('breakpoints', []):
                number = self.gdb_controller.set_breakpoint(
                    bp_data.get('file'), bp_data.get('line'), bp_data.get('condition'))
                if number is None:
                    continue
                if not bp_data.get('enabled', True):
                    self.gdb_controller.disable_breakpoint(number)

            for wp_data in data.get('watchpoints', []):
                number = self.gdb_controller.set_watchpoint(
                    wp_data.get('expression'), wp_data.get('type', 'write'))
                if number is None:
                    continue
                if not wp_data.get('enabled', True):
                    self.gdb_controller.disable_breakpoint(number)

            self.refresh()
            return True
        except Exception:
            return False

    def save_breakpoints_to_file(self, file_path: str) -> bool:
        """
        Save breakpoints and watchpoints to a file.

        Args:
            file_path: Path to save breakpoints to

        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                'breakpoints': [bp.to_dict() for bp in self.breakpoints.values()],
                'watchpoints': [wp.to_dict() for wp in self.watchpoints.values()]
            }

            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception:
            return False

    # Watchpoint management methods
    def add_watchpoint(self, expression: str, watch_type: str = "write") -> Optional[Watchpoint]:
        """
        Add a watchpoint, or return the one already set on that expression.

        Args:
            expression: Expression to watch (variable name, address, etc.)
            watch_type: Type of watchpoint - "write" (default), "read", "access"

        Returns:
            Watchpoint object, or None if GDB rejected the expression
        """
        existing_wp = self._find_watchpoint(expression, watch_type)
        if existing_wp:
            return existing_wp

        gdb_number = self.gdb_controller.set_watchpoint(expression, watch_type)
        if gdb_number is None:
            # GDB rejected the expression - don't add it to our mirror
            return None

        watchpoint = Watchpoint(gdb_number, expression, watch_type)
        self.watchpoints[gdb_number] = watchpoint
        self.watchpoints_changed.emit()
        return watchpoint

    def remove_watchpoint(self, gdb_number: int) -> bool:
        """
        Remove a watchpoint.

        Args:
            gdb_number: GDB's breakpoint number

        Returns:
            bool: True if watchpoint was removed successfully
        """
        if gdb_number not in self.watchpoints:
            return False

        # Watchpoints are breakpoints to GDB, addressed by its own number
        if not self.gdb_controller.delete_breakpoint(gdb_number):
            return False

        del self.watchpoints[gdb_number]
        self.watchpoints_changed.emit()
        return True

    def toggle_watchpoint(self, gdb_number: int) -> bool:
        """
        Toggle watchpoint enabled/disabled state.

        Args:
            gdb_number: GDB's breakpoint number

        Returns:
            bool: True if watchpoint was toggled successfully
        """
        watchpoint = self.watchpoints.get(gdb_number)
        if watchpoint is None:
            return False

        # A watchpoint is a breakpoint to GDB, so it toggles in place.
        if watchpoint.enabled:
            if not self.gdb_controller.disable_breakpoint(gdb_number):
                return False
            watchpoint.enabled = False
        else:
            if not self.gdb_controller.enable_breakpoint(gdb_number):
                return False
            watchpoint.enabled = True

        self.watchpoints_changed.emit()
        return True

    def update_watchpoint_expression(self, gdb_number: int, expression: str,
                                     watch_type: str = None) -> bool:
        """
        Update watchpoint expression or type.

        GDB cannot change a watchpoint in place, so this drops the old one and
        creates a new one, which means the watchpoint gets a new number.

        Args:
            gdb_number: GDB's breakpoint number
            expression: New expression string
            watch_type: New watch type (optional, keeps current if None)

        Returns:
            bool: True if watchpoint was updated successfully
        """
        watchpoint = self.watchpoints.get(gdb_number)
        if watchpoint is None:
            return False

        old_expression = watchpoint.expression
        old_type = watchpoint.watch_type
        new_type = watch_type if watch_type is not None else old_type

        self.gdb_controller.delete_breakpoint(gdb_number)
        new_number = self.gdb_controller.set_watchpoint(expression, new_type)
        if new_number is None:
            # Put the original watchpoint back
            new_number = self.gdb_controller.set_watchpoint(old_expression, old_type)
            if new_number is not None and not watchpoint.enabled:
                self.gdb_controller.disable_breakpoint(new_number)
            self.refresh()
            return False

        del self.watchpoints[gdb_number]
        watchpoint.gdb_number = new_number
        watchpoint.expression = expression
        watchpoint.watch_type = new_type
        if not watchpoint.enabled:
            self.gdb_controller.disable_breakpoint(new_number)
        self.watchpoints[new_number] = watchpoint
        self.watchpoints_changed.emit()
        return True

    def get_watchpoint(self, gdb_number: int) -> Optional[Watchpoint]:
        """
        Get watchpoint by GDB's breakpoint number.

        Args:
            gdb_number: GDB's breakpoint number

        Returns:
            Watchpoint object if found, None otherwise
        """
        return self.watchpoints.get(gdb_number)

    def get_watchpoints(self) -> List[Watchpoint]:
        """
        Get all watchpoints.

        Returns:
            List of all watchpoints
        """
        return list(self.watchpoints.values())

    def clear_all_watchpoints(self):
        """Clear all watchpoints, leaving breakpoints alone."""
        for gdb_number in list(self.watchpoints.keys()):
            self.remove_watchpoint(gdb_number)

    def _find_watchpoint(self, expression: str,
                         watch_type: str = None) -> Optional[Watchpoint]:
        """
        Find watchpoint for specific expression and type.

        Args:
            expression: Expression being watched
            watch_type: Watch type, or None to match any type

        Returns:
            Watchpoint object if found, None otherwise
        """
        for watchpoint in self.watchpoints.values():
            if watchpoint.expression == expression:
                if watch_type is None or watchpoint.watch_type == watch_type:
                    return watchpoint
        return None
