"""
GDB controller for managing GDB process and communication.
"""

import subprocess
import threading
import queue
import re
import time
from typing import Dict, List, Optional, Any, Tuple
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
        self.response_queues = {}
        self.token_counter = 0
        self.response_lock = threading.Lock()

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

    def _parse_mi_output(self, output: str):
        """
        Parse GDB/MI output line.
        Returns (token, result_type, content) or None if not a tokenized response.
        GDB/MI output formats:
        token^result
        token*async-output
        token+async-output
        token=async-output
        (gdb)
        """
        output = output.strip()
        if not output:
            return None

        # Check for (gdb) prompt
        if output == '(gdb)':
            return ('prompt', None, None)

        # Check for tokenized response: token^result, token*async, etc.
        # Token is a number
        import re
        match = re.match(r'^(\d+)([\^*=+])(.*)$', output)
        if match:
            token = int(match.group(1))
            result_type = match.group(2)  # ^, *, +, =
            content = match.group(3)
            return (token, result_type, content)

        return None

    def _process_output(self, output: str):
        """Process GDB output and update state accordingly."""
        # Emit raw output
        self.output_received.emit(output)

        # First, try to parse as MI response
        parsed = self._parse_mi_output(output)
        if parsed:
            token, result_type, content = parsed
            if token == 'prompt':
                # Ignore prompt for now
                pass
            else:
                # Put response in corresponding queue
                with self.response_lock:
                    if token in self.response_queues:
                        self.response_queues[token].put((result_type, content))
        else:
            # Not a tokenized MI response, process for state changes
            # Check for exited first, as exited messages may also contain 'stopped'
            import re
            # Check for various forms of exit messages
            exit_pattern = r'reason="(exited|exit-normal|exited-normally|exited-signalled)"'
            exit_match = re.search(exit_pattern, output)

            if exit_match:
                # Program has exited, clear line and file info
                self.current_state['state'] = 'exited'
                self.current_state['line'] = None
                self.current_state['file'] = None
                self.current_state['function'] = None
                self.state_changed.emit(self.current_state.copy())
            elif 'stopped' in output:
                self._handle_stopped_state(output)
            elif 'running' in output:
                self.current_state['state'] = 'running'
                self.state_changed.emit(self.current_state.copy())

    def _handle_stopped_state(self, output: str):
        """Handle stopped state and extract location information."""
        import re
        # Check if this is actually an exit message
        exit_pattern = r'reason="(exited|exit-normal|exited-normally|exited-signalled)"'
        exit_match = re.search(exit_pattern, output)

        if exit_match:
            # Program has exited, not stopped
            self.current_state['state'] = 'exited'
            self.current_state['line'] = None
            self.current_state['file'] = None
            self.current_state['function'] = None
        else:
            # Normal stopped state (e.g., breakpoint hit)
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
        if not self.gdb_process or self.gdb_process.poll() is not None:
            return []

        response = self.send_mi_command_sync("-stack-list-variables --simple-values")
        if not response:
            return []

        result_type, content = response
        if result_type != '^' or not content.startswith('done'):
            return []

        # Parse variables from MI response
        # Format: ^done,variables=[{name="var1",value="1",type="int",...},...]
        # Simple parsing: find variables array
        import re
        # Find variables array pattern
        match = re.search(r'variables=\[([^\]]*)\]', content)
        if not match:
            return []

        vars_str = match.group(1)
        # Parse individual variable entries
        # Each entry is {name="...",value="...",type="..."}
        variables = []
        # Split by '},{' to separate entries
        entries = re.split(r'\},\s*\{', vars_str)
        for entry in entries:
            # Clean up braces
            entry = entry.strip()
            if entry.startswith('{'):
                entry = entry[1:]
            if entry.endswith('}'):
                entry = entry[:-1]

            if not entry:
                continue

            # Parse key-value pairs
            var_dict = {}
            # Split by comma, but respect quoted strings
            # Simple approach: find all key="value" patterns
            pattern = r'(\w+)="([^"]*)"'
            for key, value in re.findall(pattern, entry):
                var_dict[key] = value

            if var_dict:
                variables.append(var_dict)

        return variables

    def get_call_stack(self) -> List[Dict[str, Any]]:
        """
        Get current call stack.

        Returns:
            List of stack frame dictionaries
        """
        if not self.gdb_process or self.gdb_process.poll() is not None:
            return []

        response = self.send_mi_command_sync("-stack-list-frames")
        if not response:
            return []

        result_type, content = response
        if result_type != '^' or not content.startswith('done'):
            return []

        # Parse stack frames from MI response
        # Format: ^done,stack=[frame={level="0",addr="0x...",func="...",file="...",line="..."},...]
        import re
        # Find stack array pattern
        match = re.search(r'stack=\[([^\]]*)\]', content)
        if not match:
            return []

        stack_str = match.group(1)
        # Parse individual frame entries
        # Each entry is frame={level="...",addr="...",func="...",file="...",line="..."}
        frames = []
        # Split by 'frame=' to separate entries
        # The pattern is: frame={...},frame={...}
        entries = re.findall(r'frame=\{([^}]*)\}', stack_str)
        for entry in entries:
            # Parse key-value pairs
            frame_dict = {}
            pattern = r'(\w+)="([^"]*)"'
            for key, value in re.findall(pattern, entry):
                frame_dict[key] = value

            if frame_dict:
                frames.append(frame_dict)

        return frames

    def evaluate_expression(self, expression: str) -> Optional[str]:
        """
        Evaluate expression in GDB.

        Args:
            expression: Expression to evaluate

        Returns:
            Evaluated value as string, or None if evaluation failed
        """
        if not self.gdb_process or self.gdb_process.poll() is not None:
            return None

        response = self.send_mi_command_sync(f"-data-evaluate-expression {expression}")
        if not response:
            return None

        result_type, content = response
        if result_type != '^' or not content.startswith('done'):
            return None

        # Parse value from response: ^done,value="..."
        import re
        match = re.search(r'value="([^"]*)"', content)
        if not match:
            return None

        return match.group(1)

    def read_memory(self, address: int, size: int = 256) -> Optional[bytes]:
        """
        Read memory from address.

        Args:
            address: Starting address
            size: Number of bytes to read

        Returns:
            Bytes read, or None if failed
        """
        if not self.gdb_process or self.gdb_process.poll() is not None:
            return None

        response = self.send_mi_command_sync(f"-data-read-memory 0x{address:x} x 1 {size}")
        if not response:
            return None

        result_type, content = response
        if result_type != '^' or not content.startswith('done'):
            return None

        # Parse memory data from response
        # Format: ^done,memory=[{addr="0x...",data=["0x00","0x01",...]},...]
        import re
        match = re.search(r'data=\[([^\]]*)\]', content)
        if not match:
            return None

        data_str = match.group(1)
        # Parse hex values: "0x00","0x01",...
        hex_values = re.findall(r'"([^"]*)"', data_str)
        bytes_list = []
        for hex_val in hex_values:
            if hex_val.startswith('0x'):
                try:
                    bytes_list.append(int(hex_val, 16))
                except ValueError:
                    continue

        return bytes(bytes_list)

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

    def _get_next_token(self) -> int:
        """Get next unique token for MI commands."""
        with self.response_lock:
            self.token_counter += 1
            return self.token_counter

    def send_mi_command_sync(self, command: str, timeout: float = 5.0) -> Optional[Tuple[str, str]]:
        """
        Send MI command synchronously and wait for response.

        Args:
            command: MI command (without token)
            timeout: Timeout in seconds

        Returns:
            Tuple of (result_type, content) or None on timeout/error
            result_type: '^' (result), '*' (async), '+' (async), '=' (async)
            content: The response content
        """
        if not self.gdb_process or self.gdb_process.poll() is not None:
            return None

        token = self._get_next_token()
        token_str = str(token)

        # Create response queue for this token
        response_queue = queue.Queue()
        with self.response_lock:
            self.response_queues[token] = response_queue

        try:
            # Send command with token
            full_command = f"{token_str}{command}"
            if not self.send_command(full_command):
                return None

            # Wait for response
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # Check if there's a response in the queue
                    result = response_queue.get(timeout=0.1)
                    return result
                except queue.Empty:
                    continue

            # Timeout
            return None
        finally:
            # Clean up response queue
            with self.response_lock:
                if token in self.response_queues:
                    del self.response_queues[token]