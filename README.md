# DDD Clone - Graphical Debugger Frontend for GDB

A Python-based graphical debugger frontend for the GNU Debugger (GDB), inspired by the classic Data Display Debugger (DDD).

## Features

- **Source Code Viewer**: Syntax-highlighted source code display with current execution line highlighting
- **Breakpoint Management**: Set, remove, and manage breakpoints with conditions
- **Variable Inspection**: View and inspect local and global variables
- **Watch Expressions**: Monitor specific expressions during execution
- **Memory Viewer**: Hex dump of memory at an address or any expression
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

1. Launch DDD Clone, optionally naming the program to debug
2. Click "Load" in the toolbar to choose an executable
3. The source code is displayed in the main window

### Setting Breakpoints

- Click in the left margin of the source code viewer to set or clear a breakpoint
- A click on a blank line, or one inside a comment, does nothing
- Right-click a row in the "Breakpoints" tab to edit its condition, enable or
  disable it, or delete it
- An empty condition removes the condition
- Breakpoints typed at the GDB prompt appear in the tab too, because the list
  is read back from GDB rather than tracked separately

### Controlling Execution

The toolbar has Load, Run/Continue, Pause, Step Over, Step Into and Step Out.
There are no keyboard shortcuts; the buttons are the only way to drive
execution.

### Inspecting Variables

- Locals appear in the "Variables" tab; right-click one to add it to "Watch"
- Arrays and structs expand, and so do their members, to any depth
- The "Add Watchpoint" toolbar button sets a watchpoint, which shows a live
  value once the program is stopped
- The "Memory" tab dumps memory at an address or any expression that
  evaluates to one (`&value`, `$rsp`)
- Double-click a row in the "Call Stack" tab to select that frame and show its
  source line
- The command box under the tabs runs raw GDB commands

Debug views refresh when the program stops, and when they are brought to the
front.

## Architecture

### Core Components

- **GDB Controller**: Manages GDB process and communication
- **Main Window**: Primary GUI with source code and debug panels
- **Source Viewer**: Displays source code with syntax highlighting
- **Breakpoint Manager**: Handles breakpoint operations
- **Variable Inspector**: Manages variable inspection and watch expressions
- **Memory Viewer**: Hex dump of a memory region, refreshed while stepping

### File Structure

```
ddd_clone/
├── README.md                          # Project documentation
├── CLAUDE.md                          # Project instructions for Claude Code
├── _headless_debug.py                 # Offscreen GUI harness (see Troubleshooting)
├── requirements.txt                   # Python dependencies
├── setup.py                           # Package installation configuration
├── ddd_clone/                         # Main application package
│   ├── __init__.py
│   ├── main.py                        # Entry point
│   ├── gui/                           # GUI components
│   │   ├── __init__.py
│   │   ├── main_window.py             # Window, panels and toolbar
│   │   ├── source_viewer.py           # Source display and breakpoint gutter
│   │   ├── line_number_area.py
│   │   ├── breakpoint_manager.py      # Mirrors GDB's breakpoint list
│   │   ├── variable_inspector.py      # Variables and watch expressions
│   │   └── memory_viewer.py           # Hex dump tab
│   └── gdb/                           # GDB integration
│       ├── __init__.py
│       ├── exceptions.py
│       └── gdb_controller.py          # The only reader of GDB/MI output
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── test_gdb_controller.py         # MI parsing and commands
│   ├── test_breakpoint_manager.py
│   ├── test_variable_inspector.py
│   ├── test_memory_viewer.py
│   ├── test_gui.py                    # Smoke test
│   ├── test_gui_automated.py          # qtbot-driven widget tests
│   ├── test_gui_components.py         # Tab wiring and dialogs
│   └── test_integration_headless.py   # Real Qt + real GDB (skips without them)
├── docs/                              # Historical notes and design reviews
└── examples/                          # Example program used by the tests
    ├── README.md
    └── simple_program.c
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_gdb_controller.py
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

### Headless Session

`_headless_debug.py` drives the real GUI offscreen against a real GDB session
and prints a trace, which is useful when there is no display:

```bash
export QT_QPA_PLATFORM=offscreen
python _headless_debug.py
```

It writes screenshots to a temporary directory. They show layout only: the
offscreen platform on most machines has no fonts, so text is never drawn.
The asserted end-to-end test is `tests/test_integration_headless.py`, which
skips when `gcc` or `gdb` is unavailable.

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.

## Acknowledgments

- Inspired by the original Data Display Debugger (DDD)
- Built with PyQt5 for the graphical interface
- Uses GDB Machine Interface for debugger integration