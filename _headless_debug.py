"""
Headless GUI debug session for DDD Clone.

Runs the real PyQt5 app with QT_QPA_PLATFORM=offscreen (Qt's offscreen
platform - the desktop-GUI equivalent of a headless browser), drives a real
GDB session on the example program, and captures screenshots + a trace so the
GUI behavior can be verified without a display.
"""
import os
import subprocess
import sys
import time

os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # render without a display
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from ddd_clone.gui.main_window import MainWindow
from ddd_clone.gdb.gdb_controller import GDBController

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'examples', 'simple_program.c')
EXE = os.path.join(ROOT, 'examples', 'simple_program_g.exe')  # fresh debug build
LINE = 22  # int main()

# Build the debug executable if it is missing (keeps the repo binary-free)
if not os.path.exists(EXE):
    print(f'[build] gcc -g -o {EXE}')
    subprocess.run(['gcc', '-g', '-O0', '-o', EXE, SRC], check=True)

gdb_out = []


def pump(ms):
    end = time.time() + ms / 1000.0
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def wait_state(state, timeout=15.0):
    start = time.time()
    while time.time() - start < timeout:
        if gdb_controller.current_state['state'] == state:
            return True
        pump(50)
    return False


def snapshot(label):
    pix = window.grab()
    path = os.path.join(ROOT, f'shot_{label}.png')
    pix.save(path)
    print(f'[shot] saved {path}')


app = QApplication(sys.argv)
gdb_controller = GDBController()
gdb_controller.output_received.connect(lambda o: gdb_out.append(o))
window = MainWindow(gdb_controller)
window.show()

print('=== 1. load source ===')
window.source_viewer.load_source_file(SRC)
print('lines displayed:', window.source_viewer.blockCount())

print('=== 2. start gdb on debug exe ===')
print('start_gdb:', gdb_controller.start_gdb(EXE))
pump(800)

print('=== 3. set breakpoint at main (line %d) ===' % LINE)
bp = window.breakpoint_manager.add_breakpoint(SRC, LINE)
window.source_viewer.add_breakpoint_marker(LINE)
print('breakpoint:', bp)

print('=== 4. run until breakpoint ===')
print('run:', gdb_controller.run())
stopped = wait_state('stopped', 20)
print('stopped:', stopped, 'state=', dict(gdb_controller.current_state))
pump(500)

print('=== 5. UI state after stop ===')
print('highlighted current_line:', window.source_viewer.current_line)
print('breakpoint markers:', window.source_viewer.breakpoint_lines)
window._update_variables_tree()
window._update_registers_tree()
print('variables tree top-level:', window.variables_tree.topLevelItemCount())
print('registers count:', len(gdb_controller.get_registers()))
print('call stack:', gdb_controller.get_call_stack())
vars = gdb_controller.get_variables()
print('locals:', [(v.get('name'), v.get('value'), v.get('type')) for v in vars][:8])

# Expand the arr array in the Variables tree to verify wiring
arr_item = None
for i in range(window.variables_tree.topLevelItemCount()):
    it = window.variables_tree.topLevelItem(i)
    if it.text(0) == 'arr':
        arr_item = it
        break
if arr_item:
    arr_item.setExpanded(True)  # fires itemExpanded -> _on_variable_expanded
    pump(400)
    print('arr expanded, child count:', arr_item.childCount())
    for j in range(arr_item.childCount()):
        c = arr_item.child(j)
        print('   ', c.text(0), '=', c.text(1), '(', c.text(2), ')')
else:
    print('arr item not found in variables tree')
snapshot('stopped')

print('=== 6. step over a few lines + inspect a variable ===')
for _ in range(3):
    gdb_controller.step_over()
    pump(400)
    print('  stepped -> line', gdb_controller.current_state['line'],
          'state', gdb_controller.current_state['state'])
print('number =', gdb_controller.evaluate_expression('number'))
print('factorial =', gdb_controller.evaluate_expression('factorial'))
window.source_viewer.highlight_current_line(gdb_controller.current_state['line'])
snapshot('stepped')

print('=== 7. shutdown ===')
gdb_controller.shutdown()
pump(300)
print('final state:', gdb_controller.current_state['state'])

print('=== 8. recent GDB output ===')
for line in gdb_out[-18:]:
    print('  |', line.rstrip())

print('DONE')
