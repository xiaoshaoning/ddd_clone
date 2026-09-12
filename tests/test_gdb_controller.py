"""
Unit tests for GDB controller.
"""

import unittest
from unittest.mock import Mock, patch
import queue
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ddd_clone.gdb.gdb_controller import GDBController


class TestGDBController(unittest.TestCase):
    """Test cases for GDBController class."""

    def setUp(self):
        """Set up test fixtures."""
        self.controller = GDBController()

    def test_initial_state(self):
        """Test initial state of GDB controller."""
        self.assertEqual(self.controller.current_state['state'], 'disconnected')
        self.assertIsNone(self.controller.gdb_process)
        self.assertIsNone(self.controller.read_thread)

    @patch('subprocess.Popen')
    def test_start_gdb_success(self, mock_popen):
        """Test successful GDB startup."""
        # Mock the subprocess
        mock_process = Mock()
        mock_popen.return_value = mock_process

        # Test starting GDB
        result = self.controller.start_gdb("test_program")

        # Verify GDB was started
        self.assertTrue(result)
        self.assertEqual(self.controller.current_state['state'], 'connected')
        mock_popen.assert_called_once()

    @patch('subprocess.Popen')
    def test_start_gdb_failure(self, mock_popen):
        """Test GDB startup failure."""
        # Mock subprocess to raise exception
        mock_popen.side_effect = Exception("Failed to start")

        # Test starting GDB
        result = self.controller.start_gdb("test_program")

        # Verify startup failed
        self.assertFalse(result)
        self.assertEqual(self.controller.current_state['state'], 'disconnected')

    def test_send_command_no_process(self):
        """Test sending command when no GDB process is running."""
        result = self.controller.send_command("test_command")
        self.assertFalse(result)

    @patch('subprocess.Popen')
    def test_send_command_success(self, mock_popen):
        """Test successful command sending."""
        # Mock the subprocess
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.stdin = Mock()
        mock_popen.return_value = mock_process

        # Start GDB
        self.controller.start_gdb("test_program")

        # Test sending command
        result = self.controller.send_command("test_command")

        # Verify command was sent
        self.assertTrue(result)
        mock_process.stdin.write.assert_called_once_with("test_command\n")

        # Stop the reader thread so it does not emit on a deleted controller
        self.controller.shutdown()

    def test_debug_commands(self):
        """Test debug command methods."""
        # Mock send_command
        self.controller.send_command = Mock(return_value=True)

        # Test all debug commands
        self.assertTrue(self.controller.run())
        self.assertTrue(self.controller.pause())
        self.assertTrue(self.controller.step_over())
        self.assertTrue(self.controller.step_into())
        self.assertTrue(self.controller.step_out())
        self.assertTrue(self.controller.continue_execution())

        # Verify correct commands were sent
        expected_commands = [
            "-exec-run",
            "-exec-interrupt",
            "-exec-next",
            "-exec-step",
            "-exec-finish",
            "-exec-continue"
        ]

        actual_commands = [call[0][0] for call in self.controller.send_command.call_args_list]
        self.assertEqual(actual_commands, expected_commands)

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_set_breakpoint(self, mock_send_mi):
        """Setting breakpoints returns GDB's breakpoint number."""
        mock_send_mi.return_value = ('^', 'done,bkpt={number="3",type="breakpoint",line="10"}')

        # Without condition
        result = self.controller.set_breakpoint("test.c", 10)
        self.assertEqual(result, 3)
        mock_send_mi.assert_called_with("-break-insert test.c:10")

        # With condition
        result = self.controller.set_breakpoint("test.c", 20, "i > 5")
        self.assertEqual(result, 3)
        mock_send_mi.assert_called_with("-break-insert test.c:20 -c i > 5")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_set_breakpoint_uses_basename(self, mock_send_mi):
        """GDB should receive the source basename, not the current full path."""
        mock_send_mi.return_value = ('^', 'done,bkpt={number="1",line="22"}')

        result = self.controller.set_breakpoint("D:/Projects/codes/x/simple_program.c", 22)
        self.assertEqual(result, 1)
        mock_send_mi.assert_called_with("-break-insert simple_program.c:22")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_set_breakpoint_rejected(self, mock_send_mi):
        """A breakpoint GDB rejects yields no number."""
        mock_send_mi.return_value = ('^', 'error,msg="No line 99 in file test.c"')
        self.assertIsNone(self.controller.set_breakpoint("test.c", 99))

    def test_enable_disable_breakpoint(self):
        """Enable and disable address the breakpoint by GDB's number."""
        self.controller.send_command = Mock(return_value=True)

        self.assertTrue(self.controller.enable_breakpoint(2))
        self.controller.send_command.assert_called_with("-break-enable 2")

        self.assertTrue(self.controller.disable_breakpoint(2))
        self.controller.send_command.assert_called_with("-break-disable 2")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_select_frame(self, mock_send_mi):
        """Selecting a frame reports whether GDB accepted it."""
        mock_send_mi.return_value = ('^', 'done')
        self.assertTrue(self.controller.select_frame(2))
        mock_send_mi.assert_called_with("-stack-select-frame 2")

        mock_send_mi.return_value = ('^', 'error,msg="No frame at level 9"')
        self.assertFalse(self.controller.select_frame(9))

    def test_delete_breakpoint(self):
        """Test deleting breakpoints."""
        self.controller.send_command = Mock(return_value=True)

        result = self.controller.delete_breakpoint(1)
        self.assertTrue(result)
        self.controller.send_command.assert_called_with("-break-delete 1")

    def test_shutdown(self):
        """Test GDB shutdown."""
        # Mock the subprocess
        mock_process = Mock()
        mock_process.wait.return_value = 0
        self.controller.gdb_process = mock_process

        # Mock send_command
        self.controller.send_command = Mock(return_value=True)

        # Test shutdown
        self.controller.shutdown()

        # Verify shutdown sequence
        self.controller.send_command.assert_called_with("-gdb-exit")
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        self.assertIsNone(self.controller.gdb_process)
        self.assertEqual(self.controller.current_state['state'], 'disconnected')

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_variables(self, mock_send_mi):
        """Test getting variables."""
        # Mock response
        mock_response = ('^', 'done,variables=[{name="x",value="1",type="int"},{name="y",value="2",type="int"}]')
        mock_send_mi.return_value = mock_response

        # Mock GDB process as running
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        variables = self.controller.get_variables()

        # Verify result
        self.assertEqual(len(variables), 2)
        self.assertEqual(variables[0]['name'], 'x')
        self.assertEqual(variables[0]['value'], '1')
        self.assertEqual(variables[0]['type'], 'int')
        self.assertEqual(variables[1]['name'], 'y')
        self.assertEqual(variables[1]['value'], '2')
        # Verify both simple-values and all-values calls were made
        assert mock_send_mi.call_count == 2
        mock_send_mi.assert_any_call("-stack-list-variables --simple-values")
        mock_send_mi.assert_any_call("-stack-list-variables --all-values")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_variables_no_process(self, mock_send_mi):
        """Test getting variables when no GDB process."""
        # No GDB process
        self.controller.gdb_process = None
        variables = self.controller.get_variables()
        self.assertEqual(variables, [])
        mock_send_mi.assert_not_called()

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_variables_failed_response(self, mock_send_mi):
        """Test getting variables with failed response."""
        mock_response = ('*', 'async-output')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        variables = self.controller.get_variables()
        self.assertEqual(variables, [])
        mock_send_mi.assert_called()

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_call_stack(self, mock_send_mi):
        """Test getting call stack."""
        mock_response = ('^', 'done,stack=[frame={level="0",addr="0x1234",func="main",file="test.c",line="10"},frame={level="1",addr="0x5678",func="foo",file="D:\\\\build\\\\test.c",fullname="D:\\\\build\\\\test.c",line="20"}]')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        frames = self.controller.get_call_stack()
        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0]['level'], '0')
        self.assertEqual(frames[0]['addr'], '0x1234')
        self.assertEqual(frames[0]['func'], 'main')
        self.assertEqual(frames[0]['file'], 'test.c')
        self.assertEqual(frames[0]['line'], '10')
        self.assertEqual(frames[1]['level'], '1')
        # MI escapes backslashes; paths must come back usable
        self.assertEqual(frames[1]['file'], 'D:\\build\\test.c')
        self.assertEqual(frames[1]['fullname'], 'D:\\build\\test.c')
        mock_send_mi.assert_called_with("-stack-list-frames")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_evaluate_expression(self, mock_send_mi):
        """Test evaluating expression."""
        mock_response = ('^', 'done,value="42"')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        result = self.controller.evaluate_expression("x")
        self.assertEqual(result, "42")
        mock_send_mi.assert_called_with("-data-evaluate-expression x")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_evaluate_expression_failed(self, mock_send_mi):
        """Test evaluating expression that fails."""
        mock_response = ('^', 'error,msg="No symbol \\"x\\" in current context"')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        result = self.controller.evaluate_expression("x")
        self.assertIsNone(result)

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_breakpoints(self, mock_send_mi):
        """GDB's breakpoint list is decoded into breakpoints and watchpoints."""
        mock_send_mi.return_value = (
            '^', 'done,BreakpointTable={nr_rows="4",nr_cols="6",body=['
                 'bkpt={number="1",type="breakpoint",disp="keep",enabled="y",'
                 'file="simple.c",fullname="D:\\\\p\\\\simple.c",line="5",'
                 'original-location="simple.c:5"},'
                 'bkpt={number="2",type="breakpoint",disp="keep",enabled="n",'
                 'file="simple.c",fullname="D:\\\\p\\\\simple.c",line="9",'
                 'cond="i > 5",original-location="simple.c:9"},'
                 'bkpt={number="3",type="hw watchpoint",disp="keep",enabled="y",'
                 'what="p",original-location="p"},'
                 'bkpt={number="4",type="read watchpoint",disp="keep",enabled="y",'
                 'what="n",original-location="n"}'
                 ']}')
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        entries = self.controller.get_breakpoints()

        self.assertEqual(entries, [
            {'number': 1, 'enabled': True, 'watchpoint': False,
             'file': 'D:\\p\\simple.c', 'line': 5, 'condition': None},
            {'number': 2, 'enabled': False, 'watchpoint': False,
             'file': 'D:\\p\\simple.c', 'line': 9, 'condition': 'i > 5'},
            {'number': 3, 'enabled': True, 'watchpoint': True,
             'expression': 'p', 'watch_type': 'write'},
            {'number': 4, 'enabled': True, 'watchpoint': True,
             'expression': 'n', 'watch_type': 'read'},
        ])
        mock_send_mi.assert_called_with("-break-list")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_breakpoints_falls_back_to_basename(self, mock_send_mi):
        """Without a fullname, GDB's basename is all there is."""
        mock_send_mi.return_value = (
            '^', 'done,BreakpointTable={nr_rows="1",body=['
                 'bkpt={number="1",type="breakpoint",enabled="y",file="simple.c",line="5"}'
                 ']}')
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        self.assertEqual(self.controller.get_breakpoints()[0]['file'], 'simple.c')

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_breakpoints_empty_table(self, mock_send_mi):
        """An empty breakpoint table yields no entries."""
        mock_send_mi.return_value = ('^', 'done,BreakpointTable={nr_rows="0",body=[]}')
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        self.assertEqual(self.controller.get_breakpoints(), [])

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_breakpoints_does_not_look_like_a_creation(self, mock_send_mi):
        """A -break-list answer must not be read as a new breakpoint.

        The list contains bkpt={...} tuples, so a loose match would make every
        refresh trigger another refresh.
        """
        created = []
        self.controller.breakpoint_created.connect(lambda f, l: created.append((f, l)))
        mock_send_mi.return_value = (
            '^', 'done,BreakpointTable={nr_rows="1",body=['
                 'bkpt={number="1",type="breakpoint",enabled="y",file="simple.c",line="5"}'
                 ']}')
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        self.controller.get_breakpoints()

        self.assertEqual(created, [])

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_set_breakpoint_condition(self, mock_send_mi):
        """Conditions are set and cleared with GDB's own command."""
        mock_send_mi.return_value = ('^', 'done')

        self.assertTrue(self.controller.set_breakpoint_condition(2, 'i == 5'))
        mock_send_mi.assert_called_with("condition 2 i == 5")

        # An empty condition removes it
        self.assertTrue(self.controller.set_breakpoint_condition(2, ''))
        mock_send_mi.assert_called_with("condition 2")

        self.assertTrue(self.controller.set_breakpoint_condition(2, None))
        mock_send_mi.assert_called_with("condition 2")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_set_breakpoint_condition_rejected(self, mock_send_mi):
        """A condition GDB rejects is reported as a failure."""
        mock_send_mi.return_value = ('^', 'error,msg="No symbol \\"junk\\""')

        self.assertFalse(self.controller.set_breakpoint_condition(2, 'junk'))

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_variable_children(self, mock_send_mi):
        """Children come from a varobj that is created and then deleted."""
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None
        self.controller.send_command = Mock(return_value=True)
        mock_send_mi.side_effect = [
            ('^', 'done,name="var1",numchild="2",value="{...}",type="struct Point"'),
            ('^', 'done,numchild="2",children=[child={name="var1.x",exp="x",'
                  'numchild="0",value="1",type="int"},child={name="var1.y",'
                  'exp="y",numchild="0",value="2",type="int"}],has_more="0"'),
        ]

        children = self.controller.get_variable_children('p')

        self.assertEqual(children, [
            {'name': 'x', 'value': '1', 'type': 'int', 'numchild': '0'},
            {'name': 'y', 'value': '2', 'type': 'int', 'numchild': '0'},
        ])
        mock_send_mi.assert_any_call('-var-create - * p')
        mock_send_mi.assert_any_call('-var-list-children --all-values var1')
        self.controller.send_command.assert_called_once_with('-var-delete var1')

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_variable_children_aggregate_value(self, mock_send_mi):
        """A child whose value contains braces still yields its type.

        GDB reports an unexpanded aggregate as value="{...}", and a plain
        [^}]* would stop at that brace and drop every later field.
        """
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None
        self.controller.send_command = Mock(return_value=True)
        mock_send_mi.side_effect = [
            ('^', 'done,name="var1",numchild="3",value="{...}",type="struct Box"'),
            ('^', 'done,numchild="3",children=['
                  'child={name="var1.lo",exp="lo",numchild="2",value="{...}",'
                  'type="struct Point",thread-id="1"},'
                  'child={name="var1.id",exp="id",numchild="0",value="7",type="int"}'
                  '],has_more="0"'),
        ]

        children = self.controller.get_variable_children('b')

        self.assertEqual(children[0], {
            'name': 'lo', 'value': '{...}', 'type': 'struct Point', 'numchild': '2'})
        self.assertEqual(children[1]['type'], 'int')

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_variable_children_rejects_bad_expression(self, mock_send_mi):
        """An expression GDB cannot make a varobj for yields no children."""
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None
        mock_send_mi.return_value = ('^', 'error,msg="No symbol nothere"')

        self.assertEqual(self.controller.get_variable_children('nothere'), [])

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_read_memory(self, mock_send_mi):
        """Test reading memory."""
        mock_response = ('^', 'done,memory=[{addr="0x1000",data=["0x41","0x42","0x43"]}]')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        result = self.controller.read_memory(0x1000, 3)
        self.assertEqual(result, b'ABC')
        # ADDR FORMAT WORD-SIZE NR-ROWS NR-COLS
        mock_send_mi.assert_called_with("-data-read-memory 0x1000 x 1 1 16")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_read_memory_concatenates_rows(self, mock_send_mi):
        """Every row GDB returns contributes bytes."""
        mock_send_mi.return_value = (
            '^', 'done,addr="0x1000",nr-bytes="4",memory=['
                 '{addr="0x1000",data=["0x41","0x42"]},'
                 '{addr="0x1002",data=["0x43","0x44"]}]')
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        result = self.controller.read_memory(0x1000, 4, columns=2)
        self.assertEqual(result, b'ABCD')
        mock_send_mi.assert_called_with("-data-read-memory 0x1000 x 1 2 2")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_read_memory_invalid_hex(self, mock_send_mi):
        """Test reading memory with invalid hex data."""
        mock_response = ('^', 'done,memory=[{addr="0x1000",data=["0xZZ","0x42"]}]')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        result = self.controller.read_memory(0x1000, 2)
        # Should skip invalid hex and return valid bytes
        self.assertEqual(result, b'B')

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_set_watchpoint(self, mock_send_mi):
        """Setting watchpoints returns GDB's watchpoint number."""
        # A write watchpoint is the bare command: GDB has no -w flag
        mock_send_mi.return_value = ('^', 'done,wpt={number="2",exp="x"}')
        self.assertEqual(self.controller.set_watchpoint("x"), 2)
        mock_send_mi.assert_called_with("-break-watch x")

        # Read watchpoint
        mock_send_mi.return_value = ('^', 'done,hw-rwpt={number="3",exp="y"}')
        self.assertEqual(self.controller.set_watchpoint("y", "read"), 3)
        mock_send_mi.assert_called_with("-break-watch -r y")

        # Access watchpoint
        mock_send_mi.return_value = ('^', 'done,hw-awpt={number="4",exp="z"}')
        self.assertEqual(self.controller.set_watchpoint("z", "access"), 4)
        mock_send_mi.assert_called_with("-break-watch -a z")

        # Invalid watch type defaults to write
        mock_send_mi.return_value = ('^', 'done,wpt={number="5",exp="w"}')
        self.assertEqual(self.controller.set_watchpoint("w", "invalid"), 5)
        mock_send_mi.assert_called_with("-break-watch w")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_set_watchpoint_rejected(self, mock_send_mi):
        """A watchpoint GDB rejects yields no number."""
        mock_send_mi.return_value = ('^', 'error,msg="No symbol x in current context"')
        self.assertIsNone(self.controller.set_watchpoint("x"))

    def test_set_watchpoint_no_process(self):
        """Test setting watchpoint when no GDB process."""
        self.controller.gdb_process = None
        result = self.controller.set_watchpoint("x")
        self.assertFalse(result)

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_registers(self, mock_send_mi):
        """Test getting register names."""
        # Mock response
        mock_response = ('^', 'done,register-names=["eax","ebx","ecx"]')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        registers = self.controller.get_registers()

        # Verify result
        self.assertEqual(len(registers), 3)
        self.assertEqual(registers[0]['number'], '0')
        self.assertEqual(registers[0]['name'], 'eax')
        self.assertEqual(registers[1]['number'], '1')
        self.assertEqual(registers[1]['name'], 'ebx')
        self.assertEqual(registers[2]['number'], '2')
        self.assertEqual(registers[2]['name'], 'ecx')
        mock_send_mi.assert_called_with("-data-list-register-names")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_registers_error_response(self, mock_send_mi):
        """Test getting registers with error response."""
        # Mock error response
        mock_response = ('^', 'error,msg="Failed"')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        registers = self.controller.get_registers()
        self.assertEqual(registers, [])

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_registers_invalid_response(self, mock_send_mi):
        """Test getting registers with invalid response format."""
        # Mock invalid response
        mock_response = ('*', 'async-output')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        registers = self.controller.get_registers()
        self.assertEqual(registers, [])

    def test_get_registers_no_process(self):
        """Test getting registers when no GDB process."""
        self.controller.gdb_process = None
        registers = self.controller.get_registers()
        self.assertEqual(registers, [])

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_registers_cached(self, mock_send_mi):
        """Register names are fetched once per session."""
        mock_send_mi.return_value = ('^', 'done,register-names=["eax","ebx"]')
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        first = self.controller.get_registers()
        second = self.controller.get_registers()

        self.assertEqual(first, second)
        mock_send_mi.assert_called_once_with("-data-list-register-names")

        # A new session starts with an empty cache
        self.controller.shutdown()
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None
        self.controller.get_registers()
        self.assertEqual(mock_send_mi.call_count, 2)

    def test_parse_variables_response_unescapes(self):
        """Variable values come back with MI escapes decoded."""
        content = 'done,variables=[{name="path",value="C:\\\\dir\\\\file",type="char *"}]'

        variables = self.controller._parse_variables_response(content)

        self.assertEqual(variables, [
            {'name': 'path', 'value': 'C:\\dir\\file', 'type': 'char *'},
        ])

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_evaluate_expression_unescapes(self, mock_send_mi):
        """Evaluated string values come back with MI escapes decoded."""
        mock_send_mi.return_value = ('^', 'done,value="C:\\\\dir\\\\file"')
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        self.assertEqual(self.controller.evaluate_expression('path'),
                         'C:\\dir\\file')

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_evaluate_expression_escaped_quotes(self, mock_send_mi):
        """A value is not truncated at an escaped quote inside it."""
        mock_send_mi.return_value = (
            '^', 'done,value="0x1000 \\"C:\\\\file\\""')
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        self.assertEqual(self.controller.evaluate_expression('path'),
                         '0x1000 "C:\\file"')

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_register_values(self, mock_send_mi):
        """Test getting register values."""
        # Mock response
        mock_response = ('^', 'done,register-values=[{number="0",value="0x1234"},{number="1",value="0x5678"}]')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        registers = self.controller.get_register_values()

        # Verify result
        self.assertEqual(len(registers), 2)
        self.assertEqual(registers[0]['number'], '0')
        self.assertEqual(registers[0]['value'], '0x1234')
        self.assertEqual(registers[1]['number'], '1')
        self.assertEqual(registers[1]['value'], '0x5678')
        mock_send_mi.assert_called_with("-data-list-register-values x")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_register_values_different_formats(self, mock_send_mi):
        """Test getting register values with different formats."""
        # Mock response for decimal format
        mock_response = ('^', 'done,register-values=[{number="0",value="4660"}]')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        # Test hex format (default)
        registers = self.controller.get_register_values("x")
        self.assertEqual(registers[0]['value'], '4660')
        mock_send_mi.assert_called_with("-data-list-register-values x")

        # Test decimal format
        mock_send_mi.return_value = ('^', 'done,register-values=[{number="0",value="4660"}]')
        registers = self.controller.get_register_values("d")
        self.assertEqual(registers[0]['value'], '4660')
        mock_send_mi.assert_called_with("-data-list-register-values d")

        # Test octal format
        mock_send_mi.return_value = ('^', 'done,register-values=[{number="0",value="11064"}]')
        registers = self.controller.get_register_values("o")
        self.assertEqual(registers[0]['value'], '11064')
        mock_send_mi.assert_called_with("-data-list-register-values o")

        # Test binary format
        mock_send_mi.return_value = ('^', 'done,register-values=[{number="0",value="1001001000100"}]')
        registers = self.controller.get_register_values("t")
        self.assertEqual(registers[0]['value'], '1001001000100')
        mock_send_mi.assert_called_with("-data-list-register-values t")

    @patch.object(GDBController, 'send_mi_command_sync')
    def test_get_register_values_error_response(self, mock_send_mi):
        """Test getting register values with error response."""
        # Mock error response
        mock_response = ('^', 'error,msg="Failed"')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        registers = self.controller.get_register_values()
        self.assertEqual(registers, [])

    def test_get_register_values_no_process(self):
        """Test getting register values when no GDB process."""
        self.controller.gdb_process = None
        registers = self.controller.get_register_values()
        self.assertEqual(registers, [])

    def test_parse_mi_output_record_types(self):
        """Parse tokenized, untokenized, stream and prompt lines."""
        parse = self.controller._parse_mi_output
        self.assertEqual(parse('7^done,value="3"'), (7, '^', 'done,value="3"'))
        self.assertEqual(parse('*stopped,reason="exited"'), (None, '*', 'stopped,reason="exited"'))
        self.assertEqual(parse('~"hello\\n"'), (None, '~', '"hello\\n"'))
        self.assertEqual(parse('=breakpoint-created,bkpt={}'), (None, '=', 'breakpoint-created,bkpt={}'))
        self.assertEqual(parse('(gdb) '), (None, 'prompt', ''))
        self.assertIsNone(parse(''))
        self.assertIsNone(parse('not an MI line'))

    def test_process_output_console_stream(self):
        """Stream records are decoded and emitted as console text."""
        received = []
        self.controller.console_output.connect(received.append)
        self.controller._process_output('~"$1 = 0\\n"')
        self.assertEqual(received, ['$1 = 0\n'])
        self.controller._process_output('&"break main\\n"')
        self.assertEqual(received[-1], 'break main\n')

    def test_process_output_error(self):
        """Result error records are reported as console text."""
        received = []
        self.controller.console_output.connect(received.append)
        self.controller._process_output('^error,msg="No symbol table"')
        self.assertEqual(received, ['Error: No symbol table'])

    def test_process_output_breakpoint_created(self):
        """A breakpoint-created record emits its file and line."""
        created = []
        self.controller.breakpoint_created.connect(lambda f, l: created.append((f, l)))
        self.controller._process_output(
            '=breakpoint-created,bkpt={number="1",file="simple.c",'
            'fullname="/tmp/simple.c",line="5",addr="0x1"}'
        )
        self.controller._process_output(
            '^done,bkpt={number="2",file="simple.c",fullname="/tmp/simple.c",line="9"}'
        )
        self.assertEqual(created, [('simple.c', 5), ('simple.c', 9)])

        # MI escapes backslashes; the emitted path must be decoded
        self.controller._process_output(
            '^done,bkpt={number="3",file="D:\\\\build\\\\simple.c",line="12"}'
        )
        self.assertEqual(created[-1], ('D:\\build\\simple.c', 12))

    def test_process_output_breakpoint_hit_is_not_creation(self):
        """A stopped record updates state but does not create a marker."""
        created = []
        states = []
        self.controller.breakpoint_created.connect(lambda f, l: created.append((f, l)))
        self.controller.state_changed.connect(states.append)
        self.controller._process_output(
            '*stopped,reason="breakpoint-hit",bkptno="1",frame={addr="0x1",'
            'func="main",args=[],file="simple.c",'
            'fullname="D:\\\\proj\\\\simple.c",line="5"}'
        )
        self.assertEqual(created, [])
        self.assertEqual(states[-1]['state'], 'stopped')
        self.assertEqual(states[-1]['file'], 'simple.c')
        self.assertEqual(states[-1]['fullname'], 'D:\\proj\\simple.c')
        self.assertEqual(states[-1]['line'], 5)
        self.assertEqual(states[-1]['function'], 'main')

    def test_process_output_running_and_exit(self):
        """Running and exited records update the state."""
        states = []
        self.controller.state_changed.connect(states.append)
        self.controller._process_output('*running,thread-id="all"')
        self.assertEqual(states[-1]['state'], 'running')
        self.controller._process_output('*stopped,reason="exited-normally"')
        self.assertEqual(states[-1]['state'], 'exited')
        self.assertIsNone(states[-1]['line'])
        self.assertIsNone(states[-1]['fullname'])

    def test_process_output_routes_tokenized_response(self):
        """A tokenized result reaches the waiter for that token."""
        response_queue = queue.Queue()
        self.controller.response_queues[42] = response_queue
        self.controller._process_output('42^done,value="3"')
        self.assertEqual(response_queue.get_nowait(), ('^', 'done,value="3"'))

    def test_process_output_ignores_non_mi(self):
        """Plain text that is not an MI record is dropped."""
        received = []
        self.controller.console_output.connect(received.append)
        self.controller._process_output('just some text')
        self.assertEqual(received, [])


if __name__ == '__main__':
    unittest.main()