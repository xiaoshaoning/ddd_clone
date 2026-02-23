# DDD Clone - Graphical Debugger Frontend for GDB

A Python-based graphical debugger frontend for the GNU Debugger (GDB), inspired by the classic Data Display Debugger (DDD).

## Features

- **Source Code Viewer**: Syntax-highlighted source code display with current execution line highlighting
- **Breakpoint Management**: Set, remove, and manage breakpoints with conditions
- **Variable Inspection**: View and inspect local and global variables
- **Watch Expressions**: Monitor specific expressions during execution
- **Memory Visualization**: View and analyze memory contents with hex dump and disassembly
- **Execution Control**: Run, pause, step over, step into, step out, and continue execution
- **Call Stack**: View and navigate the call stack
- **GDB Integration**: Seamless integration with GDB using MI (Machine Interface)

## Requirements

- Python 3.8 or higher
- GDB (GNU Debugger) installed and available in PATH
- Windows, Linux, or macOS

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd ddd
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install the package:
   ```bash
   pip install -e .
   ```

## Usage

### Command Line

```bash
# Start DDD Clone without loading a program
ddd-clone

# Start DDD Clone with a specific program
ddd-clone /path/to/program
```

### Python API

```python
from ddd_clone.main import main

# Start the application
main()
```

## Basic Usage Guide

### Starting a Debugging Session

1. Launch DDD Clone
2. Use "File" → "Open Program" to load an executable
3. The source code will be displayed in the main window

### Setting Breakpoints

- Click in the left margin of the source code viewer to set a breakpoint
- Right-click on a breakpoint to set conditions or remove it
- Use the "Breakpoints" tab to manage all breakpoints

### Controlling Execution

- **Run (F5)**: Start program execution
- **Pause**: Interrupt running program
- **Step Over (F10)**: Execute current line, stepping over function calls
- **Step Into (F11)**: Step into function calls
- **Step Out (Shift+F11)**: Step out of current function
- **Continue (F5)**: Continue execution until next breakpoint

### Inspecting Variables

- Local variables are automatically displayed in the "Variables" tab
- Add watch expressions in the "Watch" tab to monitor specific values
- Expand complex variables (structs, arrays) to view their members

### Memory Analysis

- Use the memory viewer to examine memory contents
- Generate hex dumps of memory regions
- Disassemble code at specific addresses
- Search for patterns in memory

## Architecture

### Core Components

- **GDB Controller**: Manages GDB process and communication
- **Main Window**: Primary GUI with source code and debug panels
- **Source Viewer**: Displays source code with syntax highlighting
- **Breakpoint Manager**: Handles breakpoint operations
- **Variable Inspector**: Manages variable inspection and watch expressions
- **Memory Viewer**: Provides memory analysis capabilities

### File Structure

```
ddd/
├── ddd_clone/
│   ├── __init__.py
│   ├── main.py
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── source_viewer.py
│   │   ├── breakpoint_manager.py
│   │   ├── variable_inspector.py
│   │   └── memory_viewer.py
│   └── gdb/
│       ├── __init__.py
│       └── gdb_controller.py
├── tests/
│   ├── __init__.py
│   ├── test_gdb_controller.py
│   ├── test_breakpoint_manager.py
│   └── test_variable_inspector.py
├── requirements.txt
├── setup.py
└── README.md
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_gdb_controller.py

# Run tests with coverage
pytest --cov=ddd_clone
```

### Code Style

This project follows PEP 8 style guidelines. Use the provided tools:

```bash
# Format code
black ddd_clone/

# Check code style
flake8 ddd_clone/

# Type checking
mypy ddd_clone/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Troubleshooting

### Common Issues

**GDB not found**: Ensure GDB is installed and available in your PATH.

**Program won't load**: Check that the executable has proper permissions and is compiled with debug symbols (`-g` flag).

**Syntax highlighting not working**: Install pygments: `pip install pygments`

### Debug Mode

Enable debug output by setting the environment variable:

```bash
export DDD_DEBUG=1
ddd-clone
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by the original Data Display Debugger (DDD)
- Built with PyQt5 for the graphical interface
- Uses GDB Machine Interface for debugger integration