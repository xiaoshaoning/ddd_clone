"""
Unit tests for GDB controller.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
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

    def test_set_breakpoint(self):
        """Test setting breakpoints."""
        self.controller.send_command = Mock(return_value=True)

        # Test setting breakpoint without condition
        result = self.controller.set_breakpoint("test.c", 10)
        self.assertTrue(result)
        self.controller.send_command.assert_called_with("-break-insert test.c:10")

        # Test setting breakpoint with condition
        result = self.controller.set_breakpoint("test.c", 20, "i > 5")
        self.assertTrue(result)
        self.controller.send_command.assert_called_with("-break-insert test.c:20 -c i > 5")

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
        mock_send_mi.assert_called_with("-stack-list-variables --simple-values")

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
        mock_response = ('^', 'done,stack=[frame={level="0",addr="0x1234",func="main",file="test.c",line="10"},frame={level="1",addr="0x5678",func="foo",file="test.c",line="20"}]')
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
    def test_read_memory(self, mock_send_mi):
        """Test reading memory."""
        mock_response = ('^', 'done,memory=[{addr="0x1000",data=["0x41","0x42","0x43"]}]')
        mock_send_mi.return_value = mock_response
        self.controller.gdb_process = Mock()
        self.controller.gdb_process.poll.return_value = None

        result = self.controller.read_memory(0x1000, 3)
        self.assertEqual(result, b'ABC')
        mock_send_mi.assert_called_with("-data-read-memory 0x1000 x 1 3")

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


if __name__ == '__main__':
    unittest.main()