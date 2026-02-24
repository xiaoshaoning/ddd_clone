"""
Variable inspector for displaying and managing variables during debugging.
"""

import re
from typing import Dict, List, Optional, Any
from PyQt5.QtCore import QObject, pyqtSignal


class Variable:
    """
    Represents a variable in the debugger.
    """

    def __init__(self, name: str, value: str, var_type: str, address: Optional[str] = None):
        self.name = name
        self.value = value
        self.type = var_type
        self.address = address
        self.children: List['Variable'] = []
        self.expanded = False

    def __str__(self):
        return f"{self.name} = {self.value} ({self.type})"

    def to_dict(self) -> Dict:
        """Convert variable to dictionary."""
        return {
            'name': self.name,
            'value': self.value,
            'type': self.type,
            'address': self.address,
            'children': [child.to_dict() for child in self.children]
        }


class VariableInspector(QObject):
    """
    Manages variable inspection in the debugger.
    """

    # Signals
    variables_updated = pyqtSignal(list)  # List of Variable objects
    watch_expression_added = pyqtSignal(str, str)  # expression, value
    watch_expression_removed = pyqtSignal(str)  # expression

    def __init__(self, gdb_controller):
        super().__init__()
        self.gdb_controller = gdb_controller
        self.local_variables: List[Variable] = []
        self.global_variables: List[Variable] = []
        self.watch_expressions: Dict[str, str] = {}  # expression -> value

    @staticmethod
    def _is_array_type(var_type: str) -> bool:
        """Check if type string represents an array."""
        return '[' in var_type and ']' in var_type

    @staticmethod
    def _parse_array_size(var_type: str) -> Optional[int]:
        """Parse array size from type string like 'int [5]' or 'char[10]'."""
        match = re.search(r'\[(\d+)\]', var_type)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None

    @staticmethod
    def _get_array_element_type(var_type: str) -> str:
        """Extract element type from array type string."""
        # Remove everything after '[' including the brackets
        match = re.match(r'([^[]+)', var_type)
        if match:
            return match.group(1).strip()
        return var_type

    def update_variables(self):
        """
        Update variable information from GDB.
        """
        # Get variables from GDB controller
        variables_data = self.gdb_controller.get_variables()

        # Parse variables data and update local variables
        self.local_variables = self._parse_variables_data(variables_data)

        # Emit signal with updated variables
        self.variables_updated.emit(self.local_variables)

    def _parse_variables_data(self, variables_data: List[Dict[str, Any]]) -> List[Variable]:
        """
        Parse raw variables data from GDB.

        Args:
            variables_data: Raw variables data from GDB

        Returns:
            List of parsed Variable objects
        """
        variables = []

        for var_data in variables_data:
            # Extract variable information
            name = var_data.get('name', 'unknown')
            value = var_data.get('value', 'unknown')
            var_type = var_data.get('type', 'unknown')
            address = var_data.get('address')

            # Check if this is an array with no value
            if value == 'unknown' and self._is_array_type(var_type):
                value = '{...}'

            # Create variable object
            variable = Variable(name, value, var_type, address)

            # Handle children (for structs, arrays, etc.)
            children_data = var_data.get('children', [])
            if children_data:
                variable.children = self._parse_variables_data(children_data)

            variables.append(variable)

        return variables

    def add_watch_expression(self, expression: str) -> bool:
        """
        Add a watch expression.

        Args:
            expression: Expression to watch

        Returns:
            bool: True if watch expression was added successfully
        """
        if expression in self.watch_expressions:
            return True  # Already exists

        # Evaluate expression in GDB
        value = self._evaluate_expression(expression)
        if value is not None:
            self.watch_expressions[expression] = value
            self.watch_expression_added.emit(expression, value)
            return True

        return False

    def remove_watch_expression(self, expression: str) -> bool:
        """
        Remove a watch expression.

        Args:
            expression: Expression to remove

        Returns:
            bool: True if watch expression was removed successfully
        """
        if expression in self.watch_expressions:
            del self.watch_expressions[expression]
            self.watch_expression_removed.emit(expression)
            return True

        return False

    def update_watch_expressions(self):
        """
        Update values of all watch expressions.
        """
        updated_expressions = {}

        for expression in self.watch_expressions.keys():
            value = self._evaluate_expression(expression)
            if value is not None:
                updated_expressions[expression] = value
                # Emit signal if value changed
                if value != self.watch_expressions[expression]:
                    self.watch_expression_added.emit(expression, value)

        self.watch_expressions = updated_expressions

    def _evaluate_expression(self, expression: str) -> Optional[str]:
        """
        Evaluate an expression in GDB.

        Args:
            expression: Expression to evaluate

        Returns:
            Evaluated value as string, or None if evaluation failed
        """
        return self.gdb_controller.evaluate_expression(expression)

    def get_local_variables(self) -> List[Variable]:
        """
        Get local variables.

        Returns:
            List of local Variable objects
        """
        return self.local_variables

    def get_global_variables(self) -> List[Variable]:
        """
        Get global variables.

        Returns:
            List of global Variable objects
        """
        return self.global_variables

    def get_watch_expressions(self) -> Dict[str, str]:
        """
        Get current watch expressions and their values.

        Returns:
            Dictionary mapping expressions to values
        """
        return self.watch_expressions.copy()

    def clear_watch_expressions(self):
        """Clear all watch expressions."""
        expressions = list(self.watch_expressions.keys())
        for expression in expressions:
            self.remove_watch_expression(expression)

    def get_variable_value(self, variable_name: str) -> Optional[str]:
        """
        Get value of a specific variable.

        Args:
            variable_name: Name of the variable

        Returns:
            Variable value as string, or None if not found
        """
        # Search in local variables
        for var in self.local_variables:
            if var.name == variable_name:
                return var.value

        # Search in global variables
        for var in self.global_variables:
            if var.name == variable_name:
                return var.value

        return None

    def expand_variable(self, variable_name: str) -> bool:
        """
        Expand a variable to show its children (for structs, arrays, etc.).

        Args:
            variable_name: Name of the variable to expand

        Returns:
            bool: True if variable was expanded successfully
        """
        # Find the variable
        variable = self._find_variable(variable_name)
        if variable and not variable.expanded:
            variable.expanded = True
            # Load children from GDB for arrays and structs
            self._load_variable_children(variable)
            return True

        return False

    def _load_variable_children(self, variable: 'Variable') -> None:
        """
        Load children for a variable (arrays, structs, etc.) from GDB.

        Args:
            variable: Variable object to load children for
        """
        # Handle arrays
        if self._is_array_type(variable.type):
            self._load_array_elements(variable)
        # TODO: Handle structs and other composite types

    def _load_array_elements(self, variable: 'Variable') -> None:
        """
        Load array elements as children of the given array variable.

        Args:
            variable: Array variable object
        """
        size = self._parse_array_size(variable.type)
        if size is None or size <= 0:
            return

        # Clear any existing children
        variable.children.clear()

        for i in range(size):
            # Evaluate array element
            expr = f"{variable.name}[{i}]"
            value = self.gdb_controller.evaluate_expression(expr)
            if value is None:
                value = 'unknown'

            # Create child variable
            child_name = f"[{i}]"
            child_type = self._get_array_element_type(variable.type)
            child_var = Variable(child_name, value, child_type)
            variable.children.append(child_var)

    def collapse_variable(self, variable_name: str) -> bool:
        """
        Collapse a variable to hide its children.

        Args:
            variable_name: Name of the variable to collapse

        Returns:
            bool: True if variable was collapsed successfully
        """
        variable = self._find_variable(variable_name)
        if variable and variable.expanded:
            variable.expanded = False
            return True

        return False

    def _find_variable(self, variable_name: str) -> Optional[Variable]:
        """
        Find a variable by name.

        Args:
            variable_name: Name of the variable to find

        Returns:
            Variable object if found, None otherwise
        """
        # Search in local variables
        for var in self.local_variables:
            if var.name == variable_name:
                return var

        # Search in global variables
        for var in self.global_variables:
            if var.name == variable_name:
                return var

        return None