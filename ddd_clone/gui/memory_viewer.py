"""
Memory viewer for displaying and analyzing memory contents.
"""

from typing import List, Optional, Tuple
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal


class MemoryRegion:
    """
    Represents a region of memory.
    """

    def __init__(self, address: int, size: int, data: bytes, permissions: str = "rwx"):
        self.address = address
        self.size = size
        self.data = data
        self.permissions = permissions

    def get_byte(self, offset: int) -> Optional[int]:
        """
        Get byte at specific offset.

        Args:
            offset: Offset from start address

        Returns:
            Byte value or None if out of bounds
        """
        if 0 <= offset < len(self.data):
            return self.data[offset]
        return None

    def get_word(self, offset: int, word_size: int = 4) -> Optional[int]:
        """
        Get word at specific offset.

        Args:
            offset: Offset from start address
            word_size: Size of word in bytes (default: 4)

        Returns:
            Word value or None if out of bounds
        """
        if 0 <= offset < len(self.data) - word_size + 1:
            word_bytes = self.data[offset:offset + word_size]
            return int.from_bytes(word_bytes, byteorder='little')
        return None


class MemoryViewer(QObject):
    """
    Manages memory viewing and analysis.
    """

    # Signals
    memory_updated = pyqtSignal(MemoryRegion)
    memory_error = pyqtSignal(str)

    def __init__(self, gdb_controller):
        super().__init__()
        self.gdb_controller = gdb_controller
        self.current_region: Optional[MemoryRegion] = None

    def read_memory(self, address: int, size: int = 256) -> Optional[MemoryRegion]:
        """
        Read memory from specified address.

        Args:
            address: Starting memory address
            size: Number of bytes to read

        Returns:
            MemoryRegion object if successful, None otherwise
        """
        try:
            # Use GDB to read memory
            # This would need to be implemented in the GDB controller
            # For now, return dummy data
            dummy_data = bytes([(address + i) % 256 for i in range(size)])

            region = MemoryRegion(address, size, dummy_data)
            self.current_region = region
            self.memory_updated.emit(region)
            return region

        except Exception as e:
            self.memory_error.emit(f"Failed to read memory: {e}")
            return None

    def write_memory(self, address: int, data: bytes) -> bool:
        """
        Write data to memory.

        Args:
            address: Starting memory address
            data: Data to write

        Returns:
            bool: True if write was successful
        """
        try:
            # Use GDB to write memory
            # This would need to be implemented in the GDB controller
            # For now, just update our current region if it matches
            if (self.current_region and
                self.current_region.address <= address <
                self.current_region.address + self.current_region.size):

                offset = address - self.current_region.address
                if offset + len(data) <= self.current_region.size:
                    # Update the region data
                    new_data = bytearray(self.current_region.data)
                    new_data[offset:offset + len(data)] = data
                    self.current_region.data = bytes(new_data)
                    self.memory_updated.emit(self.current_region)
                    return True

            return False

        except Exception as e:
            self.memory_error.emit(f"Failed to write memory: {e}")
            return False

    def search_memory(self, pattern: bytes, start_address: int = 0, end_address: int = 0xFFFFFFFF) -> List[int]:
        """
        Search for pattern in memory.

        Args:
            pattern: Byte pattern to search for
            start_address: Starting address for search
            end_address: Ending address for search

        Returns:
            List of addresses where pattern was found
        """
        addresses = []

        # For now, implement a simple search in the current region
        if self.current_region:
            region_start = self.current_region.address
            region_end = region_start + self.current_region.size

            # Adjust search range to region bounds
            search_start = max(start_address, region_start)
            search_end = min(end_address, region_end)

            if search_start < search_end:
                data = self.current_region.data
                pattern_len = len(pattern)

                for i in range(search_start - region_start, search_end - region_start - pattern_len + 1):
                    if data[i:i + pattern_len] == pattern:
                        addresses.append(region_start + i)

        return addresses

    def hex_dump(self, address: int, size: int = 256) -> List[str]:
        """
        Generate hex dump of memory.

        Args:
            address: Starting address
            size: Number of bytes to dump

        Returns:
            List of hex dump lines
        """
        region = self.read_memory(address, size)
        if not region:
            return ["Failed to read memory"]

        lines = []
        bytes_per_line = 16

        for i in range(0, size, bytes_per_line):
            # Address
            line = f"{address + i:08x}: "

            # Hex bytes
            hex_bytes = []
            ascii_chars = []

            for j in range(bytes_per_line):
                if i + j < size:
                    byte_val = region.get_byte(i + j)
                    if byte_val is not None:
                        hex_bytes.append(f"{byte_val:02x}")
                        # ASCII representation
                        if 32 <= byte_val <= 126:
                            ascii_chars.append(chr(byte_val))
                        else:
                            ascii_chars.append(".")
                    else:
                        hex_bytes.append("  ")
                        ascii_chars.append(" ")
                else:
                    hex_bytes.append("  ")
                    ascii_chars.append(" ")

            # Format hex bytes in groups
            hex_line = ""
            for k in range(0, bytes_per_line, 4):
                hex_line += " ".join(hex_bytes[k:k+4]) + "  "

            line += f"{hex_line:<50} |{''.join(ascii_chars)}|"
            lines.append(line)

        return lines

    def disassemble(self, address: int, instruction_count: int = 16) -> List[Tuple[int, str, str]]:
        """
        Disassemble memory at specified address.

        Args:
            address: Starting address
            instruction_count: Number of instructions to disassemble

        Returns:
            List of tuples (address, bytes, instruction)
        """
        # This would use GDB's disassembly capabilities
        # For now, return dummy disassembly
        disassembly = []

        for i in range(instruction_count):
            current_addr = address + i * 4
            # Dummy instruction bytes
            instr_bytes = bytes([(current_addr + j) % 256 for j in range(4)])
            # Dummy instruction
            instruction = f"mov r{i}, #{i}"

            disassembly.append((current_addr, instr_bytes.hex(), instruction))

        return disassembly

    def get_memory_map(self) -> List[Tuple[int, int, str]]:
        """
        Get memory map of the process.

        Returns:
            List of tuples (start_address, end_address, permissions)
        """
        # This would query GDB for memory regions
        # For now, return dummy memory map
        memory_map = [
            (0x00400000, 0x00401000, "r-x"),  # Code
            (0x00600000, 0x00601000, "rw-"),  # Data
            (0x7ffe0000, 0x7fff0000, "rw-"),  # Stack
            (0xffff0000, 0xffff1000, "r--"),  # Kernel
        ]

        return memory_map

    def analyze_memory_patterns(self, region: MemoryRegion) -> Dict[str, Any]:
        """
        Analyze memory patterns in a region.

        Args:
            region: Memory region to analyze

        Returns:
            Dictionary with analysis results
        """
        if not region:
            return {}

        data = np.frombuffer(region.data, dtype=np.uint8)

        analysis = {
            'size': len(data),
            'zero_bytes': np.sum(data == 0),
            'non_zero_bytes': np.sum(data != 0),
            'average_value': float(np.mean(data)),
            'entropy': self._calculate_entropy(data),
            'common_values': self._find_common_values(data),
        }

        return analysis

    def _calculate_entropy(self, data: np.ndarray) -> float:
        """
        Calculate entropy of data.

        Args:
            data: Numpy array of bytes

        Returns:
            Entropy value
        """
        value_counts = np.bincount(data, minlength=256)
        probabilities = value_counts / len(data)
        probabilities = probabilities[probabilities > 0]  # Remove zero probabilities
        entropy = -np.sum(probabilities * np.log2(probabilities))
        return entropy

    def _find_common_values(self, data: np.ndarray, top_n: int = 10) -> List[Tuple[int, int]]:
        """
        Find most common byte values.

        Args:
            data: Numpy array of bytes
            top_n: Number of top values to return

        Returns:
            List of tuples (value, count)
        """
        value_counts = np.bincount(data, minlength=256)
        # Get indices of top values
        top_indices = np.argsort(value_counts)[-top_n:][::-1]

        common_values = []
        for idx in top_indices:
            if value_counts[idx] > 0:
                common_values.append((idx, value_counts[idx]))

        return common_values