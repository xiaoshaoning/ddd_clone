# Usage Summary for DDD Clone

**Date:** 2026-02-24
**Branch:** main (up to date with origin/main)
**Project Status:** Clean working tree, ready for use

## Overview

DDD Clone is a PyQt5-based graphical frontend for GDB (GNU Debugger), inspired by the classic DDD (Data Display Debugger). It provides a visual interface for debugging C/C++ programs with features similar to traditional IDE debuggers.

## Usage Guide

### 1. Environment Setup

#### Prerequisites
- **Python 3.8+** (already installed)
- **GDB (GNU Debugger)** - Must be installed separately and added to system PATH
- **Windows-specific:** Install appropriate toolchain (MinGW or MSYS2) for compilation

#### Dependencies Installation
```bash
# Install all dependencies
pip install -r requirements.txt

# Install package in editable mode (for development)
pip install -e .
```

### 2. Starting the Application

#### Command Line Interface
```bash
# Start the debugger without loading a program
ddd-clone

# Start with a specific program
ddd-clone examples/simple_program.exe
```

#### Python Module Execution
```bash
python -m ddd_clone.main examples/simple_program.exe
```

### 3. Verification

#### Test Suite
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_gdb_controller.py
```

## Project Architecture

The application follows a Model-View-Controller pattern:

- **Model Layer:** `gdb/gdb_controller.py` - Manages GDB process and MI protocol communication
- **View Layer:** `gui/` directory - PyQt5 UI components (main window, source viewer, etc.)
- **Controller Layer:** `main.py` - Coordinates interaction between model and view

### Key Components
- **Source Code Viewer:** Syntax-highlighted source display with execution line highlighting
- **Breakpoint Manager:** Set/remove breakpoints with conditions
- **Variable Inspector:** Real-time inspection of local/global variables
- **Execution Control:** Run, pause, step over/into/out, continue

## Core Features

### 1. Breakpoint Management
- Click in left margin of source code to set breakpoints
- Right-click for conditions or removal
- Manage all breakpoints in dedicated panel

### 2. Variable Inspection
- Automatic display of local variables in Variables tab
- Add watch expressions to monitor specific values
- Expand complex types (structs, arrays) to view members

### 3. Execution Control
- **Run (F5):** Start program execution
- **Pause:** Interrupt running program
- **Step Over (F10):** Execute line, skip function calls
- **Step Into (F11):** Enter function calls
- **Step Out (Shift+F11):** Exit current function
- **Continue (F5):** Resume until next breakpoint

### 4. Memory Analysis
- Examine memory contents with hex dump view
- Disassemble code at specific addresses
- Search for patterns in memory

## Current Branch Status

- **Branch:** `main`
- **Sync Status:** Up to date with `origin/main`
- **Working Tree:** Clean (no uncommitted changes)
- **Ready for:** Immediate use, development, or testing

## Potential Next Steps

1. **Test with Example Program:**
   ```bash
   ddd-clone examples/simple_program.exe
   ```

2. **Explore Specific Features:**
   - Implement custom breakpoint conditions
   - Add memory watchpoints
   - Extend variable formatting options

3. **Development Tasks:**
   - Run full test suite: `pytest`
   - Check code style: `flake8 ddd_clone/`
   - Type checking: `mypy ddd_clone/`

## Notes

- Follows project coding standards: snake_case naming, no Chinese in comments/prints
- Requires GDB installed and accessible via system PATH
- Test programs should be compiled with debug symbols (`-g` flag)
- Debug mode available via environment variable: `export DDD_DEBUG=1`

---

*This summary documents the current state and usage patterns of the DDD Clone project as of 2026-02-24.*