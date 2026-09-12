"""
Unit tests for variable inspector.
"""

import unittest
from unittest.mock import Mock
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ddd_clone.gui.variable_inspector import VariableInspector, Variable


class TestVariable(unittest.TestCase):
    """Test cases for Variable class."""

    def test_variable_creation(self):
        """Test variable creation."""
        var = Variable("x", "42", "int", "0x7ffe1234")

        self.assertEqual(var.name, "x")
        self.assertEqual(var.path, "x")  # a top-level path is its name
        self.assertEqual(var.value, "42")
        self.assertEqual(var.type, "int")
        self.assertEqual(var.address, "0x7ffe1234")
        self.assertEqual(var.children, [])
        self.assertFalse(var.expanded)

    def test_variable_string_representation(self):
        """Test variable string representation."""
        var = Variable("x", "42", "int")
        self.assertEqual(str(var), "x = 42 (int)")

    def test_variable_to_dict(self):
        """Test variable to dictionary conversion."""
        var = Variable("x", "42", "int", "0x7ffe1234")
        var_dict = var.to_dict()

        expected = {
            'name': "x",
            'value': "42",
            'type': "int",
            'address': "0x7ffe1234",
            'children': []
        }

        self.assertEqual(var_dict, expected)


class TestVariableInspector(unittest.TestCase):
    """Test cases for VariableInspector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_gdb = Mock()
        self.inspector = VariableInspector(self.mock_gdb)

    def test_initial_state(self):
        """Test initial state of variable inspector."""
        self.assertEqual(self.inspector.local_variables, [])
        self.assertEqual(self.inspector.global_variables, [])
        self.assertEqual(self.inspector.watch_expressions, {})

    def test_add_watch_expression(self):
        """Test adding watch expressions."""
        # Mock expression evaluation
        self.inspector._evaluate_expression = Mock(return_value="42")

        # Add watch expression
        result = self.inspector.add_watch_expression("x")

        # Verify expression was added
        self.assertTrue(result)
        self.assertIn("x", self.inspector.watch_expressions)
        self.assertEqual(self.inspector.watch_expressions["x"], "42")

    def test_add_watch_expression_duplicate(self):
        """Test adding duplicate watch expression."""
        self.inspector._evaluate_expression = Mock(return_value="42")

        # Add first expression
        result1 = self.inspector.add_watch_expression("x")
        # Add duplicate
        result2 = self.inspector.add_watch_expression("x")

        # Both should succeed
        self.assertTrue(result1)
        self.assertTrue(result2)
        # Expression should only be evaluated once
        self.assertEqual(self.inspector._evaluate_expression.call_count, 1)

    def test_add_watch_expression_failure(self):
        """Test adding watch expression that fails evaluation."""
        self.inspector._evaluate_expression = Mock(return_value=None)

        result = self.inspector.add_watch_expression("invalid_expression")

        # Should return False
        self.assertFalse(result)
        # Expression should not be added
        self.assertNotIn("invalid_expression", self.inspector.watch_expressions)

    def test_remove_watch_expression(self):
        """Test removing watch expressions."""
        # Add an expression
        self.inspector._evaluate_expression = Mock(return_value="42")
        self.inspector.add_watch_expression("x")

        # Remove the expression
        result = self.inspector.remove_watch_expression("x")

        # Verify removal
        self.assertTrue(result)
        self.assertNotIn("x", self.inspector.watch_expressions)

    def test_remove_watch_expression_nonexistent(self):
        """Test removing nonexistent watch expression."""
        result = self.inspector.remove_watch_expression("nonexistent")

        # Should return False
        self.assertFalse(result)

    def test_update_watch_expressions(self):
        """Test updating watch expression values."""
        # Add some expressions
        self.inspector.watch_expressions = {
            "x": "old_value",
            "y": "old_value"
        }

        # Mock evaluation to return new values
        def mock_evaluate(expr):
            return f"new_{expr}"

        self.inspector._evaluate_expression = Mock(side_effect=mock_evaluate)

        # Update expressions
        self.inspector.update_watch_expressions()

        # Verify values were updated
        self.assertEqual(self.inspector.watch_expressions["x"], "new_x")
        self.assertEqual(self.inspector.watch_expressions["y"], "new_y")

    def test_clear_watch_expressions(self):
        """Test clearing all watch expressions."""
        # Add some expressions
        self.inspector.watch_expressions = {
            "x": "42",
            "y": "100"
        }

        # Clear all expressions
        self.inspector.clear_watch_expressions()

        # Verify all expressions are removed
        self.assertEqual(self.inspector.watch_expressions, {})

    def test_get_variable_value(self):
        """Test getting variable value."""
        # Create some test variables
        var1 = Variable("x", "42", "int")
        var2 = Variable("y", "100", "int")
        self.inspector.local_variables = [var1, var2]

        # Get existing variable value
        value = self.inspector.get_variable_value("x")
        self.assertEqual(value, "42")

        # Get nonexistent variable value
        value = self.inspector.get_variable_value("z")
        self.assertIsNone(value)

    def test_expand_variable(self):
        """Expanding returns the children, and loads them only once."""
        self.mock_gdb.get_variable_children.return_value = [
            {'name': 'x', 'value': '1', 'type': 'int', 'numchild': '0'},
        ]
        var = Variable("p", "{x = 1}", "struct Point")
        self.inspector.local_variables = [var]

        children = self.inspector.expand_variable("p")

        self.assertEqual([c.name for c in children], ['x'])
        self.assertTrue(var.expanded)

        self.mock_gdb.get_variable_children.reset_mock()
        self.assertEqual(self.inspector.expand_variable("p"), children)
        self.mock_gdb.get_variable_children.assert_not_called()

    def test_expand_variable_nonexistent(self):
        """Expanding something unknown yields nothing."""
        self.assertEqual(self.inspector.expand_variable("nonexistent"), [])

    def test_collapse_variable(self):
        """Test collapsing variables."""
        var = Variable("struct_var", "{...}", "struct")
        var.expanded = True
        self.inspector.local_variables = [var]

        # Collapse variable
        result = self.inspector.collapse_variable("struct_var")

        # Verify collapse
        self.assertTrue(result)
        self.assertFalse(var.expanded)

    def test_parse_variables_data(self):
        """Test parsing variables data."""
        variables_data = [
            {
                'name': 'x',
                'value': '42',
                'type': 'int',
                'address': '0x7ffe1234'
            },
            {
                'name': 'arr',
                'value': '{...}',
                'type': 'int[5]',
                'children': [
                    {
                        'name': '[0]',
                        'value': '1',
                        'type': 'int'
                    }
                ]
            }
        ]

        variables = self.inspector._parse_variables_data(variables_data)

        # Verify parsing
        self.assertEqual(len(variables), 2)
        self.assertEqual(variables[0].name, "x")
        self.assertEqual(variables[1].name, "arr")
        self.assertEqual(len(variables[1].children), 1)
        self.assertEqual(variables[1].children[0].name, "[0]")

    def test_is_struct_type(self):
        """Struct, union and class types are recognised as composite."""
        self.assertTrue(VariableInspector._is_struct_type("struct Point"))
        self.assertTrue(VariableInspector._is_struct_type("union Value"))
        self.assertTrue(VariableInspector._is_struct_type("class Widget"))
        self.assertFalse(VariableInspector._is_struct_type("int"))
        self.assertFalse(VariableInspector._is_struct_type("int [5]"))

    def test_load_struct_fields(self):
        """Expanding a struct loads its fields from GDB."""
        self.mock_gdb.get_variable_children.return_value = [
            {'name': 'x', 'value': '1', 'type': 'int', 'numchild': '0'},
            {'name': 'y', 'value': '2', 'type': 'int', 'numchild': '0'},
        ]
        var = Variable('p', '{x = 1, y = 2}', 'struct Point')
        self.inspector.local_variables = [var]

        self.assertEqual(len(self.inspector.expand_variable('p')), 2)

        self.mock_gdb.get_variable_children.assert_called_once_with('p')
        self.assertEqual([c.name for c in var.children], ['x', 'y'])
        self.assertEqual(var.children[1].value, '2')
        self.assertEqual(var.children[0].type, 'int')
        # Children are addressable by the expression that reaches them
        self.assertEqual([c.path for c in var.children], ['p.x', 'p.y'])

    def test_load_array_elements(self):
        """Array expansion still evaluates elements one by one."""
        self.mock_gdb.evaluate_expression.side_effect = ['4', '5']
        var = Variable('arr', '{...}', 'int [2]')
        self.inspector.local_variables = [var]

        self.assertEqual(len(self.inspector.expand_variable('arr')), 2)

        self.assertEqual([c.name for c in var.children], ['[0]', '[1]'])
        self.assertEqual([c.value for c in var.children], ['4', '5'])
        self.assertEqual(var.children[0].type, 'int')
        self.assertEqual([c.path for c in var.children], ['arr[0]', 'arr[1]'])
        # Arrays use the element-wise path, not the varobj path
        self.mock_gdb.get_variable_children.assert_not_called()

    def test_expand_nested_struct(self):
        """A field of a struct is expanded by its own path."""
        self.mock_gdb.get_variable_children.side_effect = [
            # children of `b`
            [{'name': 'lo', 'value': '', 'type': 'struct Point', 'numchild': '2'}],
            # children of `b.lo`
            [{'name': 'x', 'value': '0', 'type': 'int', 'numchild': '0'}],
        ]
        var = Variable('b', '{lo = {...}}', 'struct Box')
        self.inspector.local_variables = [var]

        outer = self.inspector.expand_variable('b')
        self.assertEqual([c.path for c in outer], ['b.lo'])

        inner = self.inspector.expand_variable('b.lo')

        self.mock_gdb.get_variable_children.assert_called_with('b.lo')
        self.assertEqual([c.name for c in inner], ['x'])
        self.assertEqual([c.path for c in inner], ['b.lo.x'])
        # find_variable reaches any depth
        self.assertIs(self.inspector.find_variable('b.lo.x'), inner[0])

    def test_find_variable_unknown(self):
        """An unknown path finds nothing."""
        self.assertIsNone(self.inspector.find_variable('nope'))
        self.assertIsNone(self.inspector.find_variable('nope.deeper'))


if __name__ == '__main__':
    unittest.main()