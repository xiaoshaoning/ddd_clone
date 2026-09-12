"""
Memory viewer: a hex dump of a memory region read from GDB.
"""

import re
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QPlainTextEdit,
)
from PyQt5.QtGui import QFont


class MemoryViewer(QWidget):
    """
    Shows a hex dump of memory at an address.

    The address may be written as a literal (0x7ffd1234) or as any GDB
    expression that evaluates to one (&value, $rsp, main).
    """

    BYTES_PER_ROW = 16
    BYTE_COUNT = 256  # ponytail: fixed for now; add a size selector when asked

    def __init__(self, gdb_controller, parent=None):
        super().__init__(parent)
        self.gdb_controller = gdb_controller
        self.address_expression = None

        layout = QVBoxLayout(self)

        address_layout = QHBoxLayout()
        address_layout.addWidget(QLabel("Address:"))
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("0x7ffd1234 or &value")
        self.address_input.returnPressed.connect(self.read_from_input)
        address_layout.addWidget(self.address_input)

        self.read_button = QPushButton("Read")
        self.read_button.clicked.connect(self.read_from_input)
        address_layout.addWidget(self.read_button)
        layout.addLayout(address_layout)

        self.dump = QPlainTextEdit()
        self.dump.setReadOnly(True)
        self.dump.setFont(QFont("Courier New", 12))
        self.dump.setPlaceholderText("Enter an address to display memory")
        layout.addWidget(self.dump)

    def read_from_input(self) -> None:
        """Read whatever address is typed into the input field."""
        self.set_address(self.address_input.text())

    def set_address(self, expression: str) -> bool:
        """
        Show the memory at an address.

        Args:
            expression: An address literal or a GDB expression

        Returns:
            bool: True if memory was read and displayed
        """
        expression = (expression or "").strip()
        if not expression:
            return False

        self.address_expression = expression
        self.address_input.setText(expression)
        return self.refresh()

    def refresh(self) -> bool:
        """
        Re-read the current address, e.g. after the program stops.

        Returns:
            bool: True if memory was read and displayed
        """
        if not self.address_expression:
            return False

        address = self._resolve_address(self.address_expression)
        if address is None:
            self.dump.setPlainText(f"Cannot resolve: {self.address_expression}")
            return False

        data = self.gdb_controller.read_memory(address, self.BYTE_COUNT)
        if data is None:
            self.dump.setPlainText(f"Cannot read memory at 0x{address:x}")
            return False

        self.dump.setPlainText(self.format_dump(address, data))
        return True

    def _resolve_address(self, expression: str) -> Optional[int]:
        """Turn an address literal or a GDB expression into an integer."""
        try:
            return int(expression, 0)
        except ValueError:
            pass

        value = self.gdb_controller.evaluate_expression(expression)
        if not value:
            return None
        match = re.search(r'0x[0-9a-fA-F]+', value)
        return int(match.group(0), 16) if match else None

    @classmethod
    def format_dump(cls, address: int, data: bytes) -> str:
        """Render a hex dump: address, hex bytes, printable ASCII."""
        width = cls.BYTES_PER_ROW * 3 - 1
        lines = []
        for offset in range(0, len(data), cls.BYTES_PER_ROW):
            row = data[offset:offset + cls.BYTES_PER_ROW]
            hex_bytes = ' '.join(f'{byte:02x}' for byte in row)
            text = ''.join(chr(byte) if 32 <= byte < 127 else '.' for byte in row)
            lines.append(f'0x{address + offset:08x}  {hex_bytes:<{width}}  {text}')
        return '\n'.join(lines)
