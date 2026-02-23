"""
Custom exceptions for GDB integration.
"""

class GDBError(Exception):
    """Base exception for all GDB-related errors."""
    pass


class GDBConnectionError(GDBError):
    """Raised when GDB connection fails."""
    pass


class GDBCommandError(GDBError):
    """Raised when a GDB command fails."""
    pass


class GDBParseError(GDBError):
    """Raised when parsing GDB/MI output fails."""
    pass


class MemoryAccessError(GDBError):
    """Raised when memory access fails."""
    pass


class GDBTimeoutError(GDBError):
    """Raised when a GDB operation times out."""
    pass


class GDBProcessError(GDBError):
    """Raised when GDB process management fails."""
    pass