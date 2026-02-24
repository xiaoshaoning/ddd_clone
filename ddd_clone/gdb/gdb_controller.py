"""
GDB controller for managing GDB process and communication.
"""

import subprocess
import threading
import queue
import re
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from PyQt5.QtCore import QObject, pyqtSignal

from .exceptions import (
    GDBError,
    GDBConnectionError,
    GDBCommandError,
    GDBParseError,
    MemoryAccessError,
    GDBTimeoutError,
    GDBProcessError,
)


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
            # Wrap in GDBConnectionError for more specific error handling
            gdb_error = GDBConnectionError(f"Failed to start GDB: {e}")
            self.output_received.emit(f"Failed to start GDB: {e}")
            return False

    def _read_output(self) -> None:
        """Read output from GDB process in a separate thread."""
        while self.gdb_process and self.gdb_process.poll() is None:
            try:
                line = self.gdb_process.stdout.readline()
                if line:
                    self.output_queue.put(line)
                    self._process_output(line)
            except (OSError, UnicodeDecodeError) as e:
                self.output_received.emit(f"Error reading GDB output: {e}")
                break

    def _parse_mi_output(self, output: str) -> Optional[Tuple[Union[int, str], Optional[str], Optional[str]]]:
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

    def _process_output(self, output: str) -> None:
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

    def _handle_stopped_state(self, output: str) -> None:
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
        except (OSError, BrokenPipeError) as e:
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

    def kill(self) -> bool:
        """Kill the program being debugged."""
        return self.send_command("kill")

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

    def set_watchpoint(self, expression: str, watch_type: str = "write") -> bool:
        """
        Set a watchpoint on an expression.

        Args:
            expression: Expression to watch (variable name, address, etc.)
            watch_type: Type of watchpoint - "write" (default), "read", "access"

        Returns:
            bool: True if watchpoint was set successfully
        """
        # Clean and validate inputs
        expression = expression.strip()
        if not expression:
            return False

        watch_type = watch_type.strip().lower()

        # Validate watch_type
        valid_types = {"write", "read", "access"}
        if watch_type not in valid_types:
            watch_type = "write"

        # GDB/MI command: -break-watch [ -a | -r | -w ] expression
        type_flag = {
            "write": "-w",
            "read": "-r",
            "access": "-a"
        }[watch_type]  # Now guaranteed to be valid

        # Quote expression if it contains spaces and isn't already quoted
        quoted_expression = expression
        if ' ' in expression and not (expression.startswith('"') and expression.endswith('"')):
            quoted_expression = f'"{expression}"'

        cmd = f"-break-watch {type_flag} {quoted_expression}"
        return self.send_command(cmd)

    def get_registers(self) -> List[Dict[str, str]]:
        """
        Get list of register names.

        Returns:
            List of dictionaries with register information
        """
        if not self.gdb_process or self.gdb_process.poll() is not None:
            return []

        try:
            response = self.send_mi_command_sync("-data-list-register-names")
            if not response:
                return []
            result_type, content = response
            if result_type != '^' or not content.startswith('done'):
                return []
        except GDBError:
            return []

        # Parse register names from response
        # Format: ^done,register-names=["eax","ebx",...]
        import re
        match = re.search(r'register-names=\[([^\]]*)\]', content)
        if not match:
            return []

        names_str = match.group(1)
        # Parse quoted strings
        register_names = re.findall(r'"([^"]*)"', names_str)
        registers = []
        for i, name in enumerate(register_names):
            registers.append({"number": str(i), "name": name})
        return registers

    def get_register_values(self, format: str = "x") -> List[Dict[str, str]]:
        """
        Get current register values.

        Args:
            format: Output format - "x" (hex), "d" (decimal), "o" (octal), "t" (binary)

        Returns:
            List of dictionaries with register number, name, and value
        """
        if not self.gdb_process or self.gdb_process.poll() is not None:
            return []

        try:
            response = self.send_mi_command_sync(f"-data-list-register-values {format}")
            if not response:
                return []
            result_type, content = response
            if result_type != '^' or not content.startswith('done'):
                return []
        except GDBError:
            return []

        # Parse register values from response
        # Format: ^done,register-values=[{number="0",value="0x0"},...]
        import re
        match = re.search(r'register-values=\[([^\]]*)\]', content)
        if not match:
            return []

        values_str = match.group(1)
        # Parse each {number="...",value="..."} entry
        entries = re.findall(r'\{([^}]*)\}', values_str)
        registers = []
        for entry in entries:
            # Parse key-value pairs
            reg_dict = {}
            pattern = r'(\w+)="([^"]*)"'
            for key, value in re.findall(pattern, entry):
                reg_dict[key] = value
            if reg_dict:
                registers.append(reg_dict)
        return registers

    def _parse_variables_response(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse GDB MI response for -stack-list-variables.

        Args:
            content: The content part of MI response (after ^done,)

        Returns:
            List of variable dictionaries
        """
        import re

        # Find variables array pattern
        # Need to handle types with brackets like "int [5]" which contain ']'
        # Match everything between the first '[' and the last ']'
        # The pattern (.*) is greedy and will match up to the last ']'
        match = re.search(r'variables=\[(.*)\]', content)
        if not match:
            return []

        vars_str = match.group(1)
        # Parse individual variable entries
        # Each entry is {name="...",value="...",type="..."}
        variables = []
        # Use findall to extract each {} block, handling nested braces in types like int [5]
        # First, let's print the vars_str to see its exact content

        # Find all top-level {...} entries, being careful with nested braces in types
        # Simple approach: find all matches of { ... } where ... doesn't contain unmatched braces
        # Since types may contain brackets like int [5], we need a more robust method
        # Let's try parsing manually by scanning the string
        entries = []
        start = -1
        brace_count = 0
        for i, char in enumerate(vars_str):
            if char == '{':
                if brace_count == 0:
                    start = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start != -1:
                    entries.append(vars_str[start+1:i])  # Exclude braces
                    start = -1


        for entry in entries:
            if not entry.strip():
                continue

            # Parse key-value pairs
            var_dict = {}
            # Split by comma, but respect quoted strings
            # Match key=value pairs, handling optional comma and whitespace before key
            # Pattern: (optional comma or start) whitespace* key="value"
            # Key cannot contain =, ", comma, or whitespace
            pattern = r'(?:,|^)\s*([^=",\s]+?)="([^"]*)"'
            matches = re.findall(pattern, entry)
            # Debug: print matches for this entry
            for key, value in matches:
                var_dict[key] = value

            if var_dict:
                variables.append(var_dict)

        return variables

    def get_variables(self) -> List[Dict[str, Any]]:
        """
        Get current variable values.

        Returns:
            List of variable dictionaries
        """
        if not self.gdb_process or self.gdb_process.poll() is not None:
            return []

        variables = []

        try:
            # First get variables with types (--simple-values)
            response = self.send_mi_command_sync("-stack-list-variables --simple-values")
            result_type, content = response
            if result_type == '^' and content.startswith('done'):
                variables_with_types = self._parse_variables_response(content)

                # Then get variables with values (--all-values) for arrays
                response2 = self.send_mi_command_sync("-stack-list-variables --all-values")
                result_type2, content2 = response2
                if result_type2 == '^' and content2.startswith('done'):
                    variables_with_values = self._parse_variables_response(content2)

                    # Merge: start with types, then update with values
                    # Create a map by name for quick lookup
                    var_map = {v['name']: v for v in variables_with_types}

                    for var_with_value in variables_with_values:
                        name = var_with_value.get('name')
                        if name in var_map:
                            # Update value if present
                            if 'value' in var_with_value:
                                var_map[name]['value'] = var_with_value['value']
                            # Update any other fields (like addr)
                            for key in var_with_value:
                                if key not in ('name', 'value', 'type'):
                                    var_map[name][key] = var_with_value[key]

                    variables = list(var_map.values())
                else:
                    # Fallback to just types
                    variables = variables_with_types
            else:
                return []
        except GDBError:
            return []

        return variables

    def get_call_stack(self) -> List[Dict[str, Any]]:
        """
        Get current call stack.

        Returns:
            List of stack frame dictionaries
        """
        if not self.gdb_process or self.gdb_process.poll() is not None:
            return []

        try:
            response = self.send_mi_command_sync("-stack-list-frames")
            result_type, content = response
            if result_type != '^' or not content.startswith('done'):
                return []
        except GDBError:
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

        try:
            response = self.send_mi_command_sync(f"-data-evaluate-expression {expression}")
            result_type, content = response
            if result_type != '^' or not content.startswith('done'):
                return None
        except GDBError:
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

        try:
            response = self.send_mi_command_sync(f"-data-read-memory 0x{address:x} x 1 {size}")
            result_type, content = response
            if result_type != '^' or not content.startswith('done'):
                return None
        except GDBError:
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
                    # Invalid hex value, skip this byte
                    continue

        return bytes(bytes_list)

    def shutdown(self) -> None:
        """Shutdown GDB process."""
        if self.gdb_process:
            try:
                self.send_command("-gdb-exit")
                self.gdb_process.terminate()
                self.gdb_process.wait(timeout=5)
            except Exception as e:
                # Log the error but still attempt to kill the process
                self.output_received.emit(f"Error during shutdown: {e}")
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
            raise GDBConnectionError("GDB process not running")

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
                raise GDBCommandError(f"Failed to send command: {command}")

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
            raise GDBTimeoutError(f"Command timed out after {timeout} seconds: {command}")
        finally:
            # Clean up response queue
            with self.response_lock:
                if token in self.response_queues:
                    del self.response_queues[token]