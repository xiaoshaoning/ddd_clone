# DDD Clone Examples

This directory contains example programs for testing DDD Clone functionality.

## Simple C Program

### Compilation

```bash
# Compile with debug symbols
gcc -g -o simple_program simple_program.c
```

### Usage with DDD Clone

1. Start DDD Clone:
   ```bash
   ddd-clone examples/simple_program
   ```

2. Set breakpoints:
   - Click in the left margin at line 15 (factorial function)
   - Click at line 25 (fibonacci function)

3. Run the program (F5)

4. Step through the code:
   - Use Step Into (F11) to enter functions
   - Use Step Over (F10) to skip function calls
   - Use Continue (F5) to run to next breakpoint

5. Inspect variables:
   - Watch the `number`, `fact_result`, and `fib_result` variables
   - Expand the `arr` array to see individual elements

### Features to Test

- **Breakpoints**: Set at function entries and specific lines
- **Step Operations**: Step into recursive functions
- **Variable Inspection**: Watch local variables change
- **Call Stack**: Navigate through recursive function calls
- **Memory View**: Examine array memory layout

## Debugging Tips

1. **Use conditional breakpoints**: Set breakpoints that only trigger when specific conditions are met
2. **Watch expressions**: Add expressions like `i > 2` to monitor specific conditions
3. **Memory analysis**: Use the memory viewer to examine array contents and pointer values
4. **Call stack navigation**: Use the call stack to understand the flow of recursive functions