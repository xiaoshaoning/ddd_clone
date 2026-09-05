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


class GDBTimeoutError(GDBError):
    """Raised when a GDB operation times out."""
    pass