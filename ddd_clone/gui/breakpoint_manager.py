"""
Breakpoint and watchpoint manager for handling breakpoints and watchpoints in the debugger.
"""

from typing import Dict, List, Optional, Union
from PyQt5.QtCore import QObject, pyqtSignal


class Breakpoint:
    """
    Represents a single breakpoint.
    """

    def __init__(self, breakpoint_id: int, file: str, line: int, condition: Optional[str] = None):
        self.breakpoint_id = breakpoint_id
        self.file = file
        self.line = line
        self.condition = condition
        self.enabled = True

    def __str__(self):
        condition_str = f" [{self.condition}]" if self.condition else ""
        enabled_str = "" if self.enabled else " (disabled)"
        return f"{self.file}:{self.line}{condition_str}{enabled_str}"

    def to_dict(self) -> Dict:
        """Convert breakpoint to dictionary."""
        return {
            'id': self.breakpoint_id,
            'file': self.file,
            'line': self.line,
            'condition': self.condition,
            'enabled': self.enabled
        }


class Watchpoint:
    """
    Represents a single watchpoint.
    """

    def __init__(self, watchpoint_id: int, expression: str, watch_type: str = "write"):
        self.watchpoint_id = watchpoint_id
        self.expression = expression
        self.watch_type = watch_type  # "write", "read", "access"
        self.enabled = True

    def __str__(self):
        type_str = f" ({self.watch_type})" if self.watch_type != "write" else ""
        enabled_str = "" if self.enabled else " (disabled)"
        return f"{self.expression}{type_str}{enabled_str}"

    def to_dict(self) -> Dict:
        """Convert watchpoint to dictionary."""
        return {
            'id': self.watchpoint_id,
            'expression': self.expression,
            'type': self.watch_type,
            'enabled': self.enabled
        }


class BreakpointManager(QObject):
    """
    Manages breakpoints in the debugger.
    """

    # Signals
    breakpoint_added = pyqtSignal(Breakpoint)
    breakpoint_removed = pyqtSignal(int)  # breakpoint_id
    breakpoint_updated = pyqtSignal(Breakpoint)
    watchpoint_added = pyqtSignal(Watchpoint)
    watchpoint_removed = pyqtSignal(int)  # watchpoint_id
    watchpoint_updated = pyqtSignal(Watchpoint)

    def __init__(self, gdb_controller):
        super().__init__()
        self.gdb_controller = gdb_controller
        self.breakpoints: Dict[int, Breakpoint] = {}
        self.watchpoints: Dict[int, Watchpoint] = {}
        self.next_breakpoint_id = 1
        self.next_watchpoint_id = 1

    def add_breakpoint(self, file: str, line: int, condition: Optional[str] = None) -> Optional[Breakpoint]:
        """
        Add a new breakpoint.

        Args:
            file: Source file path
            line: Line number
            condition: Optional breakpoint condition

        Returns:
            Breakpoint object if successful, None otherwise
        """
        # Check if breakpoint already exists at this location
        existing_bp = self._find_breakpoint(file, line)
        if existing_bp:
            return existing_bp

        # Create new breakpoint
        breakpoint_id = self.next_breakpoint_id
        self.next_breakpoint_id += 1

        breakpoint = Breakpoint(breakpoint_id, file, line, condition)

        # Set breakpoint in GDB
        if self.gdb_controller.set_breakpoint(file, line, condition):
            self.breakpoints[breakpoint_id] = breakpoint
            self.breakpoint_added.emit(breakpoint)
            return breakpoint
        else:
            # GDB failed to set the breakpoint - don't add it to our internal state
            return None

    def remove_breakpoint(self, breakpoint_id: int) -> bool:
        """
        Remove a breakpoint.

        Args:
            breakpoint_id: ID of the breakpoint to remove

        Returns:
            bool: True if breakpoint was removed successfully
        """
        if breakpoint_id not in self.breakpoints:
            return False

        # Remove breakpoint from GDB
        if self.gdb_controller.delete_breakpoint(breakpoint_id):
            del self.breakpoints[breakpoint_id]
            self.breakpoint_removed.emit(breakpoint_id)
            return True

        return False

    def toggle_breakpoint(self, breakpoint_id: int) -> bool:
        """
        Toggle breakpoint enabled/disabled state.

        Args:
            breakpoint_id: ID of the breakpoint to toggle

        Returns:
            bool: True if breakpoint was toggled successfully
        """
        if breakpoint_id not in self.breakpoints:
            return False

        breakpoint = self.breakpoints[breakpoint_id]
        breakpoint.enabled = not breakpoint.enabled

        # TODO: Implement enabling/disabling in GDB
        # For now, we'll remove and re-add the breakpoint
        if breakpoint.enabled:
            # Re-enable by re-adding
            self.gdb_controller.set_breakpoint(
                breakpoint.file,
                breakpoint.line,
                breakpoint.condition
            )
        else:
            # Disable by removing
            self.gdb_controller.delete_breakpoint(breakpoint_id)

        self.breakpoint_updated.emit(breakpoint)
        return True

    def update_breakpoint_condition(self, breakpoint_id: int, condition: str) -> bool:
        """
        Update breakpoint condition.

        Args:
            breakpoint_id: ID of the breakpoint to update
            condition: New condition string

        Returns:
            bool: True if breakpoint was updated successfully
        """
        if breakpoint_id not in self.breakpoints:
            return False

        breakpoint = self.breakpoints[breakpoint_id]
        old_condition = breakpoint.condition
        breakpoint.condition = condition

        # Update breakpoint in GDB by removing and re-adding
        self.gdb_controller.delete_breakpoint(breakpoint_id)
        if self.gdb_controller.set_breakpoint(breakpoint.file, breakpoint.line, condition):
            self.breakpoint_updated.emit(breakpoint)
            return True
        else:
            # Restore old condition if update failed
            breakpoint.condition = old_condition
            self.gdb_controller.set_breakpoint(breakpoint.file, breakpoint.line, old_condition)
            return False

    def get_breakpoint(self, breakpoint_id: int) -> Optional[Breakpoint]:
        """
        Get breakpoint by ID.

        Args:
            breakpoint_id: ID of the breakpoint

        Returns:
            Breakpoint object if found, None otherwise
        """
        return self.breakpoints.get(breakpoint_id)

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
        """Clear all breakpoints."""
        for breakpoint_id in list(self.breakpoints.keys()):
            self.remove_breakpoint(breakpoint_id)

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

    def sync_with_gdb(self):
        """
        Synchronize breakpoints with GDB.
        This would query GDB for current breakpoints and update our internal state.
        """
        # TODO: Implement GDB breakpoint querying
        # For now, we assume our internal state matches GDB
        pass

    def load_breakpoints_from_file(self, file_path: str) -> bool:
        """
        Load breakpoints and watchpoints from a file.

        Args:
            file_path: Path to breakpoints file

        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            import os

            if not os.path.exists(file_path):
                return False

            with open(file_path, 'r') as f:
                data = json.load(f)

            # Clear existing breakpoints and watchpoints
            self.clear_all_breakpoints()
            self.clear_all_watchpoints()

            # Load breakpoints
            for bp_data in data.get('breakpoints', []):
                bp_id = bp_data.get('id')
                file = bp_data.get('file')
                line = bp_data.get('line')
                condition = bp_data.get('condition')
                enabled = bp_data.get('enabled', True)

                # Create breakpoint
                bp = Breakpoint(bp_id, file, line, condition)
                bp.enabled = enabled
                self.breakpoints[bp_id] = bp

                # Set in GDB if enabled
                if enabled and self.gdb_controller:
                    self.gdb_controller.set_breakpoint(file, line, condition)

            # Update next breakpoint ID
            if self.breakpoints:
                self.next_breakpoint_id = max(self.breakpoints.keys()) + 1

            # Load watchpoints
            for wp_data in data.get('watchpoints', []):
                wp_id = wp_data.get('id')
                expression = wp_data.get('expression')
                watch_type = wp_data.get('type', 'write')  # Note: 'type' key from to_dict()
                enabled = wp_data.get('enabled', True)

                # Create watchpoint
                wp = Watchpoint(wp_id, expression, watch_type)
                wp.enabled = enabled
                self.watchpoints[wp_id] = wp

                # Set in GDB if enabled
                if enabled and self.gdb_controller:
                    self.gdb_controller.set_watchpoint(expression, watch_type)

            # Update next watchpoint ID
            if self.watchpoints:
                self.next_watchpoint_id = max(self.watchpoints.keys()) + 1

            # Emit signals for UI updates
            for bp in self.breakpoints.values():
                self.breakpoint_added.emit(bp)

            for wp in self.watchpoints.values():
                self.watchpoint_added.emit(wp)

            return True
        except Exception as e:
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
            import json
            import os

            # Prepare data structure
            data = {
                'breakpoints': [bp.to_dict() for bp in self.breakpoints.values()],
                'watchpoints': [wp.to_dict() for wp in self.watchpoints.values()]
            }

            # Write to file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            return False

    # Watchpoint management methods
    def add_watchpoint(self, expression: str, watch_type: str = "write") -> Optional[Watchpoint]:
        """
        Add a new watchpoint.

        Args:
            expression: Expression to watch (variable name, address, etc.)
            watch_type: Type of watchpoint - "write" (default), "read", "access"

        Returns:
            Watchpoint object if successful, None otherwise
        """
        # Check if watchpoint already exists for this expression
        existing_wp = self._find_watchpoint(expression, watch_type)
        if existing_wp:
            return existing_wp

        # Create new watchpoint
        watchpoint_id = self.next_watchpoint_id
        self.next_watchpoint_id += 1

        watchpoint = Watchpoint(watchpoint_id, expression, watch_type)

        # Set watchpoint in GDB
        if self.gdb_controller.set_watchpoint(expression, watch_type):
            self.watchpoints[watchpoint_id] = watchpoint
            self.watchpoint_added.emit(watchpoint)
            return watchpoint
        else:
            # GDB failed to set the watchpoint - don't add it to our internal state
            return None

    def remove_watchpoint(self, watchpoint_id: int) -> bool:
        """
        Remove a watchpoint.

        Args:
            watchpoint_id: ID of the watchpoint to remove

        Returns:
            bool: True if watchpoint was removed successfully
        """
        if watchpoint_id not in self.watchpoints:
            return False

        # Remove watchpoint from GDB - use breakpoint-delete command for watchpoints
        if self.gdb_controller.delete_breakpoint(watchpoint_id):
            del self.watchpoints[watchpoint_id]
            self.watchpoint_removed.emit(watchpoint_id)
            return True

        return False

    def toggle_watchpoint(self, watchpoint_id: int) -> bool:
        """
        Toggle watchpoint enabled/disabled state.

        Args:
            watchpoint_id: ID of the watchpoint to toggle

        Returns:
            bool: True if watchpoint was toggled successfully
        """
        if watchpoint_id not in self.watchpoints:
            return False

        watchpoint = self.watchpoints[watchpoint_id]
        watchpoint.enabled = not watchpoint.enabled

        # TODO: Implement enabling/disabling in GDB
        # For now, we'll remove and re-add the watchpoint
        if watchpoint.enabled:
            # Re-enable by re-adding
            self.gdb_controller.set_watchpoint(watchpoint.expression, watchpoint.watch_type)
        else:
            # Disable by removing
            self.gdb_controller.delete_breakpoint(watchpoint_id)

        self.watchpoint_updated.emit(watchpoint)
        return True

    def update_watchpoint_expression(self, watchpoint_id: int, expression: str, watch_type: str = None) -> bool:
        """
        Update watchpoint expression or type.

        Args:
            watchpoint_id: ID of the watchpoint to update
            expression: New expression string
            watch_type: New watch type (optional, keeps current if None)

        Returns:
            bool: True if watchpoint was updated successfully
        """
        if watchpoint_id not in self.watchpoints:
            return False

        watchpoint = self.watchpoints[watchpoint_id]
        old_expression = watchpoint.expression
        old_type = watchpoint.watch_type
        watchpoint.expression = expression
        if watch_type is not None:
            watchpoint.watch_type = watch_type

        # Update watchpoint in GDB by removing and re-adding
        self.gdb_controller.delete_breakpoint(watchpoint_id)
        new_type = watch_type if watch_type is not None else old_type
        if self.gdb_controller.set_watchpoint(expression, new_type):
            self.watchpoint_updated.emit(watchpoint)
            return True
        else:
            # Restore old values if update failed
            watchpoint.expression = old_expression
            watchpoint.watch_type = old_type
            self.gdb_controller.set_watchpoint(old_expression, old_type)
            return False

    def get_watchpoint(self, watchpoint_id: int) -> Optional[Watchpoint]:
        """
        Get watchpoint by ID.

        Args:
            watchpoint_id: ID of the watchpoint

        Returns:
            Watchpoint object if found, None otherwise
        """
        return self.watchpoints.get(watchpoint_id)

    def get_watchpoints(self) -> List[Watchpoint]:
        """
        Get all watchpoints.

        Returns:
            List of all watchpoints
        """
        return list(self.watchpoints.values())

    def clear_all_watchpoints(self):
        """Clear all watchpoints."""
        for watchpoint_id in list(self.watchpoints.keys()):
            self.remove_watchpoint(watchpoint_id)

    def _find_watchpoint(self, expression: str, watch_type: str = None) -> Optional[Watchpoint]:
        """
        Find watchpoint for specific expression and type.

        Args:
            expression: Expression being watched
            watch_type: Type of watchpoint (optional)

        Returns:
            Watchpoint object if found, None otherwise
        """
        for watchpoint in self.watchpoints.values():
            if watchpoint.expression == expression:
                if watch_type is None or watchpoint.watch_type == watch_type:
                    return watchpoint
        return None