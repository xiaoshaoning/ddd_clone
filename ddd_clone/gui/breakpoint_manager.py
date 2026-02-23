"""
Breakpoint manager for handling breakpoints in the debugger.
"""

from typing import Dict, List, Optional
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


class BreakpointManager(QObject):
    """
    Manages breakpoints in the debugger.
    """

    # Signals
    breakpoint_added = pyqtSignal(Breakpoint)
    breakpoint_removed = pyqtSignal(int)  # breakpoint_id
    breakpoint_updated = pyqtSignal(Breakpoint)

    def __init__(self, gdb_controller):
        super().__init__()
        self.gdb_controller = gdb_controller
        self.breakpoints: Dict[int, Breakpoint] = {}
        self.next_breakpoint_id = 1

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

    def load_breakpoints_from_file(self, file_path: str):
        """
        Load breakpoints from a file.

        Args:
            file_path: Path to breakpoints file
        """
        # TODO: Implement breakpoint file loading
        pass

    def save_breakpoints_to_file(self, file_path: str):
        """
        Save breakpoints to a file.

        Args:
            file_path: Path to save breakpoints to
        """
        # TODO: Implement breakpoint file saving
        pass