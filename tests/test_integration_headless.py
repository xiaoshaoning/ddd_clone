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
    if not _have('gcc'):
        pytest.skip('gcc not available to build the debug example')
    # Always rebuild so the test never runs against a stale binary
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
            # state_changed is emitted from the reader thread and delivered on
            # the next event loop pass; pump so the UI reflects it too.
            _pump(50)
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

    # The example opens with a /* ... */ block, so its first lines are not
    # breakable even though none of them starts with the comment marker.
    # This runs against the pygments-rendered document, not plain text.
    assert window.source_viewer.is_code_line(2) is False
    assert window.source_viewer.is_code_line(5) is False
    assert window.source_viewer.is_code_line(6) is True

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

    # 5. UI reflects the stop, and the visible tab was refreshed by it
    assert window.source_viewer.current_line > 0
    _pump(200)  # state_changed is queued from the reader thread
    assert window.variables_tree.topLevelItemCount() >= 1

    # 5b. Only the visible view is refreshed on a stop, so bringing another
    # one forward is what has to populate it.
    window.tab_widget.setCurrentWidget(window.registers_tree)
    assert window.registers_tree.topLevelItemCount() > 0
    window.tab_widget.setCurrentWidget(window.call_stack_tree)
    assert window.call_stack_tree.topLevelItemCount() >= 1
    assert window.call_stack_tree.topLevelItem(0).text(0) == 'main'
    window.tab_widget.setCurrentWidget(window.variables_tree)
    _pump(200)
    assert window.variables_tree.topLevelItemCount() >= 1

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

    # 7. Expand a struct (struct Point origin) -> fields should fill in
    origin_item = None
    for i in range(window.variables_tree.topLevelItemCount()):
        it = window.variables_tree.topLevelItem(i)
        if it.text(0) == 'origin':
            origin_item = it
            break
    assert origin_item is not None
    origin_item.setExpanded(True)
    _pump(400)
    assert origin_item.childCount() == 2
    assert [origin_item.child(i).text(0) for i in range(2)] == ['x', 'y']
    assert origin_item.child(0).text(2) == 'int'

    # 8. Memory viewer reads a real address, and the size selector re-reads it
    assert window.memory_viewer.set_address('&number') is True
    assert len(window.memory_viewer.dump.toPlainText().splitlines()) == 16  # 256 bytes
    window.memory_viewer.size_combo.setCurrentText('64')
    assert len(window.memory_viewer.dump.toPlainText().splitlines()) == 4

    # 9. Step over a few lines without crashing
    for _ in range(5):
        gdb_controller.step_over()
        _pump(300)
    assert gdb_controller.current_state['state'] == 'stopped'

    # 10. Tear down cleanly
    gdb_controller.shutdown()
    assert gdb_controller.current_state['state'] == 'disconnected'
