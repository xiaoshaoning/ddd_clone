"""
GDB controller for managing GDB process and communication.
"""

import os
import subprocess
import threading
import queue
import re
import time
from typing import Dict, List, Optional, Any, Tuple
from PyQt5.QtCore import QObject, pyqtSignal

from .exceptions import (
    GDBError,
    GDBConnectionError,
    GDBCommandError,
    GDBTimeoutError,
)


# C-string escapes used by GDB/MI stream records. Unknown escapes are
# passed through without their backslash.
_MI_ESCAPES = {
    'n': '\n', 't': '\t', 'r': '\r', 'a': '\a', 'b': '\b',
    'f': '\f', 'v': '\v', '"': '"', "'": "'", '\\': '\\',
}


def _unescape_mi_string(text: str) -> str:
    """Decode the C-string escapes GDB/MI uses inside stream records."""
    return re.sub(r'\\(.)', lambda m: _MI_ESCAPES.get(m.group(1), m.group(1)), text)


def _mi_stream_text(content: str) -> str:
    """Decode a stream record's content, dropping its surrounding quotes."""
    if len(content) >= 2 and content.startswith('"') and content.endswith('"'):
        content = content[1:-1]
    return _unescape_mi_string(content)


class GDBController(QObject):
    """
    Controller for managing GDB process and communication.
    """

    # Signals for UI updates. The controller is the only reader of GDB/MI
    # output, so what it emits is already decoded.
    state_changed = pyqtSignal(dict)
    console_output = pyqtSignal(str)           # user-facing GDB text
    breakpoint_created = pyqtSignal(str, int)  # (file, line) as GDB reports it

    def __init__(self):
        super().__init__()
        self.gdb_process = None
        self.output_queue = queue.Queue()
        self.read_thread = None
        self.current_state = {
            'state': 'disconnected',
            'file': None,
            'fullname': None,
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
            # --quiet suppresses the human-mode startup banner at the source,
            # so no output filtering is needed downstream.
            cmd = ['gdb', '--quiet', '--interpreter=mi2']
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
            self.console_output.emit(f"Failed to start GDB: {e}")
            return False

    def _read_output(self) -> None:
        """Read output from GDB process in a separate thread."""
        while self.gdb_process and self.gdb_process.poll() is None:
            try:
                line = self.gdb_process.stdout.readline()
                if line:
                    self.output_queue.put(line)
                    self._process_output(line)
            except (OSError, UnicodeDecodeError, TypeError, ValueError, RuntimeError) as e:
                try:
                    self.console_output.emit(f"Error reading GDB output: {e}")
                except RuntimeError:
                    pass  # Controller is being torn down; just stop the thread
                break

    def _parse_mi_output(self, output: str) -> Optional[Tuple[Optional[int], str, str]]:
        """
        Parse one line of GDB/MI output into (token, record_type, content).

        The leading token is optional. Record types:
            token^result              result record
            token*async-output        async exec record
            token+async-output        async status record
            token=async-output        async notify record
            ~"text" @"text" &"text"   console / target / log stream records
        (gdb) is reported as (None, 'prompt', '').
        Returns None when the line is not an MI record.
        """
        output = output.strip()
        if not output:
            return None

        if output == '(gdb)':
            return (None, 'prompt', '')

        match = re.match(r'^(\d+)?([\^*=+~@&])(.*)$', output)
        if match:
            token = int(match.group(1)) if match.group(1) else None
            return (token, match.group(2), match.group(3))

        return None

    def _process_output(self, output: str) -> None:
        """Decode one GDB/MI record and emit the resulting typed events."""
        parsed = self._parse_mi_output(output)
        if parsed is None:
            return

        token, record_type, content = parsed
        if record_type == 'prompt':
            return

        # Hand tokenized responses to the synchronous waiter, if any.
        if token is not None:
            with self.response_lock:
                response_queue = self.response_queues.get(token)
            if response_queue is not None:
                response_queue.put((record_type, content))

        if record_type in ('~', '@', '&'):
            # Stream records carry user-facing text.
            text = _mi_stream_text(content)
            if text.strip():
                self.console_output.emit(text)
        elif record_type == '^' and content.startswith('error'):
            match = re.search(r'msg="([^"]*)"', content)
            self.console_output.emit("Error: " + (match.group(1) if match else 'unknown error'))
        elif record_type in ('*', '^') and content.startswith('stopped'):
            self._handle_stopped_state(content)
        elif record_type in ('*', '^') and content.startswith('running'):
            self.current_state['state'] = 'running'
            self.state_changed.emit(self.current_state.copy())
        elif record_type == '^' and content.startswith('done') and 'bkpt={' in content:
            self._emit_breakpoint_created(content)
        elif record_type == '=' and content.startswith('breakpoint-created'):
            self._emit_breakpoint_created(content)

    def _emit_breakpoint_created(self, content: str) -> None:
        """Emit the source location of a breakpoint GDB just created."""
        file_match = re.search(r'file="([^"]*)"', content)
        line_match = re.search(r'line="(\d+)"', content)
        if file_match and line_match:
            self.breakpoint_created.emit(
                _unescape_mi_string(file_match.group(1)), int(line_match.group(1))
            )

    def _handle_stopped_state(self, content: str) -> None:
        """Update state from a stopped record's content (may report an exit)."""
        state = self.current_state

        if re.search(r'reason="(exited|exit-normal|exited-normally|exited-signalled)"', content):
            state['state'] = 'exited'
            state['line'] = None
            state['file'] = None
            state['fullname'] = None
            state['function'] = None
        else:
            # Normal stopped state (e.g., breakpoint hit)
            state['state'] = 'stopped'
            file_match = re.search(r'file="([^"]+)"', content)
            fullname_match = re.search(r'fullname="([^"]+)"', content)
            line_match = re.search(r'line="(\d+)"', content)
            func_match = re.search(r'func="([^"]+)"', content)
            # file is often just the basename; fullname is the absolute path
            if file_match:
                state['file'] = _unescape_mi_string(file_match.group(1))
            if fullname_match:
                state['fullname'] = _unescape_mi_string(fullname_match.group(1))
            if line_match:
                state['line'] = int(line_match.group(1))
            if func_match:
                state['function'] = func_match.group(1)

        self.state_changed.emit(state.copy())

    def send_command(self, command: str) -> bool:
        """
        Send a command to GDB.

        Reports only whether the command reached GDB, not whether GDB accepted
        it: GDB answers asynchronously through the console_output and
        breakpoint_created signals. Use send_mi_command_sync() when a caller
        needs the reply.

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
            self.console_output.emit(f"Failed to send command: {e}")
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

    def set_breakpoint(self, file: str, line: int, condition: Optional[str] = None) -> Optional[int]:
        """
        Insert a breakpoint and wait for GDB to confirm it.

        Args:
            file: Source file path
            line: Line number
            condition: Optional breakpoint condition

        Returns:
            GDB's breakpoint number, or None if GDB rejected the breakpoint
        """
        # GDB matches source files by the name recorded in the debug info,
        # which may differ from the current absolute path if the project was
        # built/moved elsewhere. Use the basename so GDB resolves it against
        # its own source catalog instead of erroring on a stale full path.
        cmd = f"-break-insert {os.path.basename(file)}:{line}"
        if condition:
            cmd += f" -c {condition}"

        try:
            result_type, content = self.send_mi_command_sync(cmd)
        except GDBError:
            return None
        if result_type != '^' or not content.startswith('done'):
            return None

        match = re.search(r'bkpt=\{[^}]*?number="(\d+)"', content)
        return int(match.group(1)) if match else None

    def enable_breakpoint(self, breakpoint_number: int) -> bool:
        """Enable a breakpoint, identified by GDB's breakpoint number."""
        return self.send_command(f"-break-enable {breakpoint_number}")

    def disable_breakpoint(self, breakpoint_number: int) -> bool:
        """Disable a breakpoint, identified by GDB's breakpoint number."""
        return self.send_command(f"-break-disable {breakpoint_number}")

    def delete_breakpoint(self, breakpoint_number: int) -> bool:
        """
        Delete a breakpoint.

        Args:
            breakpoint_number: GDB's breakpoint number

        Returns:
            bool: True if the delete command was sent successfully
        """
        return self.send_command(f"-break-delete {breakpoint_number}")

    def set_watchpoint(self, expression: str, watch_type: str = "write") -> Optional[int]:
        """
        Set a watchpoint on an expression and wait for GDB to confirm it.

        Args:
            expression: Expression to watch (variable name, address, etc.)
            watch_type: Type of watchpoint - "write" (default), "read", "access"

        Returns:
            GDB's watchpoint number, or None if GDB rejected the watchpoint
        """
        # Clean and validate inputs
        expression = expression.strip()
        if not expression:
            return None

        watch_type = watch_type.strip().lower()
        if watch_type not in ("write", "read", "access"):
            watch_type = "write"

        # GDB/MI spells the write watchpoint as the bare command; there is no
        # -w flag, and passing one makes GDB reject the whole command.
        flag = {"write": "", "read": "-r ", "access": "-a "}[watch_type]

        # Quote expression if it contains spaces and isn't already quoted
        quoted_expression = expression
        if ' ' in expression and not (expression.startswith('"') and expression.endswith('"')):
            quoted_expression = f'"{expression}"'

        try:
            result_type, content = self.send_mi_command_sync(
                f"-break-watch {flag}{quoted_expression}")
        except GDBError:
            return None
        if result_type != '^' or not content.startswith('done'):
            return None

        # The result key varies: wpt, hw-rwpt, hw-awpt - all carry number
        match = re.search(r'number="(\d+)"', content)
        return int(match.group(1)) if match else None

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
                frame_dict[key] = _unescape_mi_string(value)

            if frame_dict:
                frames.append(frame_dict)

        return frames

    def select_frame(self, level: int) -> bool:
        """
        Select a stack frame.

        Args:
            level: Frame level, where 0 is the innermost frame

        Returns:
            bool: True if GDB accepted the selection
        """
        try:
            result_type, content = self.send_mi_command_sync(f"-stack-select-frame {level}")
        except GDBError:
            return False
        return result_type == '^' and content.startswith('done')

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
        match = re.search(r'value="([^"]*)"', content)
        if not match:
            return None

        return match.group(1)

    def get_variable_children(self, expression: str) -> List[Dict[str, str]]:
        """
        List the children of a composite expression (struct fields, array
        elements) using a GDB variable object.

        A varobj is created, read once, and deleted again, so it is an
        implementation detail of this call rather than state the caller owns.

        Args:
            expression: Expression naming a struct, union or array

        Returns:
            List of dicts with 'name', 'value', 'type' and 'numchild'
        """
        if not self.gdb_process or self.gdb_process.poll() is not None:
            return []

        try:
            result_type, content = self.send_mi_command_sync(f"-var-create - * {expression}")
            name_match = re.search(r'name="([^"]+)"', content)
            if result_type != '^' or not content.startswith('done') or not name_match:
                return []
            variable_object = name_match.group(1)

            try:
                result_type, content = self.send_mi_command_sync(
                    f"-var-list-children --all-values {variable_object}")
            finally:
                self.send_command(f"-var-delete {variable_object}")

            if result_type != '^' or not content.startswith('done'):
                return []
        except GDBError:
            return []

        children = []
        for entry in re.findall(r'child=\{([^}]*)\}', content):
            fields = dict(re.findall(r'(\w[\w-]*)="([^"]*)"', entry))
            children.append({
                # 'exp' is the field name as written in the source
                'name': _unescape_mi_string(fields.get('exp') or fields.get('name', '')),
                'value': _unescape_mi_string(fields.get('value', '')),
                'type': _unescape_mi_string(fields.get('type', '')),
                'numchild': fields.get('numchild', '0'),
            })
        return children

    def read_memory(self, address: int, size: int = 256, columns: int = 16) -> Optional[bytes]:
        """
        Read memory from an address.

        Args:
            address: Starting address
            size: Number of bytes to read
            columns: Bytes per row, as GDB reports them

        Returns:
            Bytes read, or None if failed
        """
        if not self.gdb_process or self.gdb_process.poll() is not None:
            return None

        # -data-read-memory takes ADDR FORMAT WORD-SIZE NR-ROWS NR-COLS, so the
        # request has to be expressed as a grid of bytes.
        rows = max(1, -(-size // columns))
        try:
            response = self.send_mi_command_sync(
                f"-data-read-memory 0x{address:x} x 1 {rows} {columns}")
            result_type, content = response
            if result_type != '^' or not content.startswith('done'):
                return None
        except GDBError:
            return None

        # Format: memory=[{addr="0x...",data=["0x00",...]},{addr="0x...",data=[...]}]
        # One entry per row, so every row's data has to be concatenated.
        data = bytearray()
        for row in re.findall(r'data=\[([^\]]*)\]', content):
            for hex_value in re.findall(r'"([^"]*)"', row):
                try:
                    data.append(int(hex_value, 16))
                except ValueError:
                    # Invalid hex value, skip this byte
                    continue

        return bytes(data[:size])

    def shutdown(self) -> None:
        """Shutdown GDB process and stop the reader thread."""
        if self.gdb_process:
            try:
                self.send_command("-gdb-exit")
                self.gdb_process.terminate()
                self.gdb_process.wait(timeout=5)
            except Exception as e:
                # Log the error but still attempt to kill the process
                self.console_output.emit(f"Error during shutdown: {e}")
                self.gdb_process.kill()
            finally:
                self.gdb_process = None

        # Join the reader thread so it cannot emit signals after teardown
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=2)

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