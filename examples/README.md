# DDD Clone Examples

This directory contains example programs for testing DDD Clone functionality.

## Simple C Program

### Compilation

```bash
# Compile with debug symbols
gcc -g -o simple_program simple_program.c
```

On Windows the executable is written as `simple_program.exe`.

### Usage with DDD Clone

1. Start DDD Clone with the program:

   ```bash
   ddd-clone examples/simple_program        # examples/simple_program.exe on Windows
   ```

2. Set breakpoints by clicking in the left margin: line 8 (`factorial`),
   line 15 (`fibonacci`) or line 23 (`main`).

3. Run with the "Run/Continue" toolbar button.

4. Step through the code with the toolbar's "Step Into" and "Step Over", and
   "Run/Continue" to run on to the next breakpoint.

5. Inspect variables:

   - Watch `number`, `fact_result` and `fib_result` in the Variables tab
   - Expand `arr` to see individual elements
   - Expand `origin` to see the fields of a struct

### Features to Test

- **Breakpoints**: set at function entries and specific lines
- **Conditional breakpoints**: right-click a row in the Breakpoints tab and
  choose "Edit Condition...", e.g. `n <= 1` on the `factorial` breakpoint
- **Watchpoints**: "Add Watchpoint" in the toolbar, then watch a value change
- **Step Operations**: step into the recursive `factorial` and `fibonacci`
- **Variable Inspection**: expand arrays and structs, to any depth
- **Call Stack**: double-click a frame to select it and show its source line
- **Memory Viewer**: enter `&number` in the Memory tab
