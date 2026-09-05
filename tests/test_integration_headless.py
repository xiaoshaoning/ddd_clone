"""
Headless end-to-end integration test: real GUI + real GDB.

Drives the actual PyQt5 app against a real GDB subprocess on the example
program (the desktop-GUI equivalent of a headless-browser test). It is
skipped when gdb -- or gcc, needed to build the debug example -- is not
available, so the suite still passes on machines without a toolchain.

Note: run headless CI with `QT_QPA_PLATFORM=offscreen` set so Qt needs no
display. This test honors whatever platform the session already uses.
"""
import os
import shutil
import subprocess
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from PyQt5.QtWidgets import QApplication

ROOT = os.path.join(os.path.dirname(__file__), '..')
SRC = os.path.join(ROOT, 'examples', 'simple_program.c')
EXE = os.path.join(ROOT, 'examples', 'simple_program_g.exe')
LINE = 22  # int main()


def _have(cmd):
    return shutil.which(cmd) is not None


def _build_debug_exe():
    subprocess.run(
        ['gcc', '-g', '-O0', '-o', EXE, SRC], check=True, cwd=ROOT
    )


@pytest.fixture
def debug_exe():
    if not _have('gdb'):
        pytest.skip('gdb not available')
    if not os.path.exists(EXE) and not _have('gcc'):
        pytest.skip('gcc not available to build the debug example')
    if not os.path.exists(EXE):
        _build_debug_exe()
    return EXE


def _pump(ms):
    app = QApplication.instance()
    end = time.time() + ms / 1000.0
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def _wait_state(ctrl, state, timeout_ms=15000):
    start = time.time()
    while time.time() - start < timeout_ms / 1000.0:
        if ctrl.current_state['state'] == state:
            return True
        _pump(50)
    return False


def test_headless_gdb_session(qtbot, debug_exe):
    """Full GUI + GDB session: load source, breakpoint, run, step, expand."""
    from ddd_clone.gui.main_window import MainWindow
    from ddd_clone.gdb.gdb_controller import GDBController

    gdb_controller = GDBController()
    window = MainWindow(gdb_controller)
    qtbot.addWidget(window)

    # 1. Load source
    window.source_viewer.load_source_file(SRC)
    assert window.source_viewer.current_file == SRC
    assert window.source_viewer.blockCount() > 0

    # 2. Start GDB
    assert gdb_controller.start_gdb(debug_exe) is True
    _pump(800)

    # 3. Set a breakpoint at main
    window.breakpoint_manager.add_breakpoint(SRC, LINE)
    window.source_viewer.add_breakpoint_marker(LINE)
    assert LINE in window.source_viewer.breakpoint_lines

    # 4. Run -> should stop at main
    assert gdb_controller.run() is True
    assert _wait_state(gdb_controller, 'stopped'), dict(gdb_controller.current_state)
    assert gdb_controller.current_state['function'] == 'main'

    # 5. UI reflects the stop
    assert window.source_viewer.current_line > 0
    window._update_variables_tree()
    assert window.variables_tree.topLevelItemCount() >= 1
    assert gdb_controller.get_call_stack() != []

    # 6. Expand an array (int arr[5]) -> children should fill in
    arr_item = None
    for i in range(window.variables_tree.topLevelItemCount()):
        it = window.variables_tree.topLevelItem(i)
        if it.text(0) == 'arr':
            arr_item = it
            break
    assert arr_item is not None
    arr_item.setExpanded(True)
    _pump(400)
    assert arr_item.childCount() == 5
    assert arr_item.child(0).text(0) == '[0]'

    # 7. Step over a few lines without crashing
    for _ in range(5):
        gdb_controller.step_over()
        _pump(300)
    assert gdb_controller.current_state['state'] == 'stopped'

    # 8. Tear down cleanly
    gdb_controller.shutdown()
    assert gdb_controller.current_state['state'] == 'disconnected'
