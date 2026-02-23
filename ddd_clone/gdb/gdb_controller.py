"""
GDB controller for managing GDB process and communication.
"""

import subprocess
import threading
import queue
import re
from typing import Dict, List, Optional, Any
from PyQt5.QtCore import QObject, pyqtSignal


class GDBController(QObject):
    """
    Controller for managing GDB process and communication.
    """

    # Signals for UI updates
    state_changed = pyqtSignal(dict)
    output_received = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.gdb_process = None
        self.output_queue = queue.Queue()
        self.read_thread = None
        self.current_state = {
            'state': 'disconnected',
            'file': None,
            'line': None,
            'function': None
        }

    def start_gdb(self, program_path: Optional[str] = None) -> bool:
        """
        Start GDB process.

        Args:
            program_path: Path to the program to debug

        Returns:
            bool: True if GDB started successfully
        """
        try:
            # Start GDB process
            cmd = ['gdb', '--interpreter=mi2']
            if program_path:
                cmd.append(program_path)

            self.gdb_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            # Start output reading thread
            self.read_thread = threading.Thread(target=self._read_output)
            self.read_thread.daemon = True
            self.read_thread.start()

            self.current_state['state'] = 'connected'
            self.state_changed.emit(self.current_state.copy())
            return True

        except Exception as e:
            self.output_received.emit(f"Failed to start GDB: {e}")
            return False

    def _read_output(self):
        """Read output from GDB process in a separate thread."""
        while self.gdb_process and self.gdb_process.poll() is None:
            try:
                line = self.gdb_process.stdout.readline()
                if line:
                    self.output_queue.put(line)
                    self._process_output(line)
            except Exception as e:
                self.output_received.emit(f"Error reading GDB output: {e}")
                break

    def _process_output(self, output: str):
        """Process GDB output and update state accordingly."""
        # Emit raw output
        self.output_received.emit(output)

        # Parse GDB/MI output for state changes
        if 'stopped' in output:
            self._handle_stopped_state(output)
        elif 'running' in output:
            self.current_state['state'] = 'running'
            self.state_changed.emit(self.current_state.copy())

    def _handle_stopped_state(self, output: str):
        """Handle stopped state and extract location information."""
        self.current_state['state'] = 'stopped'

        # Extract file and line information
        file_match = re.search(r'file="([^"]+)"', output)
        line_match = re.search(r'line="(\d+)"', output)
        func_match = re.search(r'func="([^"]+)"', output)

        if file_match:
            self.current_state['file'] = file_match.group(1)
        if line_match:
            self.current_state['line'] = int(line_match.group(1))
        if func_match:
            self.current_state['function'] = func_match.group(1)

        self.state_changed.emit(self.current_state.copy())

    def send_command(self, command: str) -> bool:
        """
        Send a command to GDB.

        Args:
            command: GDB command to execute

        Returns:
            bool: True if command was sent successfully
        """
        if not self.gdb_process or self.gdb_process.poll() is not None:
            return False

        try:
            self.gdb_process.stdin.write(command + '\n')
            self.gdb_process.stdin.flush()
            return True
        except Exception as e:
            self.output_received.emit(f"Failed to send command: {e}")
            return False

    def run(self) -> bool:
        """Start program execution."""
        return self.send_command("-exec-run")

    def pause(self) -> bool:
        """Pause program execution."""
        return self.send_command("-exec-interrupt")

    def step_over(self) -> bool:
        """Step over current line."""
        return self.send_command("-exec-next")

    def step_into(self) -> bool:
        """Step into function call."""
        return self.send_command("-exec-step")

    def step_out(self) -> bool:
        """Step out of current function."""
        return self.send_command("-exec-finish")

    def continue_execution(self) -> bool:
        """Continue program execution."""
        return self.send_command("-exec-continue")

    def set_breakpoint(self, file: str, line: int, condition: Optional[str] = None) -> bool:
        """
        Set a breakpoint.

        Args:
            file: Source file path
            line: Line number
            condition: Optional breakpoint condition

        Returns:
            bool: True if breakpoint was set successfully
        """
        cmd = f"-break-insert {file}:{line}"
        if condition:
            cmd += f" -c {condition}"

        # Send command and check for success
        if self.send_command(cmd):
            # The actual success/failure will be reported via output_received signal
            # For now, we assume it succeeded unless we get an error response
            return True
        return False

    def delete_breakpoint(self, breakpoint_id: int) -> bool:
        """
        Delete a breakpoint.

        Args:
            breakpoint_id: Breakpoint ID

        Returns:
            bool: True if breakpoint was deleted successfully
        """
        return self.send_command(f"-break-delete {breakpoint_id}")

    def get_variables(self) -> List[Dict[str, Any]]:
        """
        Get current variable values.

        Returns:
            List of variable dictionaries
        """
        # This would need to parse GDB output to get variables
        # For now, return empty list
        return []

    def get_call_stack(self) -> List[Dict[str, Any]]:
        """
        Get current call stack.

        Returns:
            List of stack frame dictionaries
        """
        # This would need to parse GDB output to get call stack
        # For now, return empty list
        return []

    def shutdown(self):
        """Shutdown GDB process."""
        if self.gdb_process:
            try:
                self.send_command("-gdb-exit")
                self.gdb_process.terminate()
                self.gdb_process.wait(timeout=5)
            except:
                self.gdb_process.kill()
            finally:
                self.gdb_process = None

        self.current_state['state'] = 'disconnected'
        self.state_changed.emit(self.current_state.copy())