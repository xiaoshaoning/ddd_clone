"""
Source code viewer with syntax highlighting.
"""

from PyQt5.QtWidgets import QPlainTextEdit, QTextEdit, QToolTip
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QColor, QTextCharFormat, QMouseEvent

from .line_number_area import LineNumberArea


try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import HtmlFormatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


class SourceViewer(QPlainTextEdit):
    """
    Source code viewer with basic syntax highlighting.
    """

    current_line_changed = pyqtSignal(int)
    breakpoint_toggled = pyqtSignal(int)  # line_number
    variable_hovered = pyqtSignal(str)  # variable_name

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Courier New", 12))  # Larger font
        self.current_line = -1
        self.highlighted_lines = {}
        self.current_file = None
        self.breakpoint_lines = set()
        self.variable_values = {}  # Store variable values for tooltips

        # Hover timer for delayed variable inspection
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._handle_hover_timeout)
        self.current_hover_variable = None
        self.last_hover_pos = None
        self.hover_timer_active = False

        # Line number area
        self.line_number_area = LineNumberArea(self)

        self.setup_ui()

    def setup_ui(self):
        """Set up the source viewer UI."""
        # Set line wrap mode
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        # Set tab width
        self.setTabStopDistance(40)

        # Enable mouse tracking for tooltips
        self.setMouseTracking(True)

        # Connect signals for line number area
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)

        # Connect line number area click signal
        self.line_number_area.line_number_clicked.connect(self.toggle_breakpoint)

        # Set initial line number area width
        self.update_line_number_area_width(0)

    def load_source_file(self, file_path: str, current_line: int = -1):
        """
        Load and display a source file.

        Args:
            file_path: Path to the source file
            current_line: Current execution line (for highlighting)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            self.current_file = file_path

            if PYGMENTS_AVAILABLE:
                # Use pygments for syntax highlighting
                self._load_with_syntax_highlighting(source_code, file_path)
            else:
                # Fallback to plain text
                self.setPlainText(source_code)

            # Highlight current line
            if current_line > 0:
                self.highlight_current_line(current_line)

        except Exception as e:
            self.setPlainText(f"Error loading file {file_path}: {e}")

    def _load_with_syntax_highlighting(self, source_code: str, file_path: str):
        """
        Load source code with syntax highlighting using pygments.

        Args:
            source_code: The source code text
            file_path: Path to the source file (for determining language)
        """
        try:
            # Determine language from file extension
            language = self._get_language_from_file(file_path)
            lexer = get_lexer_by_name(language)

            # Create HTML formatter
            formatter = HtmlFormatter(
                style='default',
                noclasses=True,
                nobackground=True
            )

            # Highlight code
            highlighted_code = highlight(source_code, lexer, formatter)

            # Set HTML content
            self.setHtml(highlighted_code)

        except Exception as e:
            # Fallback to plain text if highlighting fails
            self.setPlainText(source_code)

    def _get_language_from_file(self, file_path: str) -> str:
        """
        Determine programming language from file extension.

        Args:
            file_path: Path to the source file

        Returns:
            str: Language name for pygments
        """
        extension_map = {
            '.c': 'c',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.h': 'cpp',
            '.hpp': 'cpp',
            '.py': 'python',
            '.java': 'java',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.rs': 'rust',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.cs': 'csharp',
            '.swift': 'swift',
            '.m': 'objective-c',
            '.mm': 'objective-c++',
        }

        for ext, lang in extension_map.items():
            if file_path.lower().endswith(ext):
                return lang

        return 'text'  # Default to plain text

    def highlight_current_line(self, line_number: int):
        """
        Highlight the current execution line.

        Args:
            line_number: Line number to highlight
        """
        # Safety check for invalid line numbers
        if line_number is None or line_number <= 0:
            return

        # Clear previous highlight
        if self.current_line > 0:
            self._clear_line_highlight(self.current_line)

        self.current_line = line_number

        # Create highlight format
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor(255, 255, 200))  # Light yellow

        # Apply highlight
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.Start)

        # Move to the target line
        for _ in range(line_number - 1):
            cursor.movePosition(QTextCursor.Down)

        # Select the entire line
        cursor.movePosition(QTextCursor.StartOfLine)
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)

        # Apply formatting
        cursor.setCharFormat(highlight_format)

        # Store the highlight
        self.highlighted_lines[line_number] = highlight_format

        # Scroll to the highlighted line
        self.centerCursor()

        # Emit signal
        self.current_line_changed.emit(line_number)

    def _clear_line_highlight(self, line_number: int):
        """
        Clear highlight from a specific line.

        Args:
            line_number: Line number to clear
        """
        if line_number in self.highlighted_lines:
            cursor = QTextCursor(self.document())
            cursor.movePosition(QTextCursor.Start)

            # Move to the target line
            for _ in range(line_number - 1):
                cursor.movePosition(QTextCursor.Down)

            # Select the entire line
            cursor.movePosition(QTextCursor.StartOfLine)
            cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)

            # Clear formatting
            default_format = QTextCharFormat()
            cursor.setCharFormat(default_format)

            del self.highlighted_lines[line_number]

    def clear_all_highlights(self):
        """Clear all line highlights."""
        for line_number in list(self.highlighted_lines.keys()):
            self._clear_line_highlight(line_number)
        self.current_line = -1

    def goto_line(self, line_number: int):
        """
        Scroll to and highlight a specific line.

        Args:
            line_number: Line number to go to
        """
        self.highlight_current_line(line_number)

    def get_current_line_content(self) -> str:
        """
        Get the content of the current highlighted line.

        Returns:
            str: Content of the current line
        """
        if self.current_line <= 0:
            return ""

        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.Start)

        # Move to the target line
        for _ in range(self.current_line - 1):
            cursor.movePosition(QTextCursor.Down)

        # Select the entire line
        cursor.movePosition(QTextCursor.StartOfLine)
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)

        return cursor.selectedText()

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse clicks for breakpoint setting."""
        # Debug print
        print(f"Mouse press at: {event.pos().x()}, {event.pos().y()}, button: {event.button()}")
        print(f"Viewport margins: {self.viewportMargins()}")
        print(f"Contents rect: {self.contentsRect()}")

        # Calculate line number area width
        line_number_width = self.line_number_area_width()
        print(f"Line number area width: {line_number_width}")

        # Check if click is in the line number area (including breakpoint marker area)
        if (event.button() == Qt.LeftButton and
            event.pos().x() <= line_number_width):  # Click within line number area
            print(f"Line number area clicked (x={event.pos().x()} <= {line_number_width})")

            # Get the line number that was clicked
            cursor = self.cursorForPosition(event.pos())
            line_number = cursor.blockNumber() + 1  # Convert to 1-based line numbers
            print(f"Line number clicked: {line_number}")

            # Toggle breakpoint
            self.toggle_breakpoint(line_number)
            return  # Don't propagate the event
        else:
            print(f"Click outside line number area (x={event.pos().x()} > {line_number_width})")

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse movement for variable tooltips with delay."""
        # Get cursor position and extract potential variable name
        cursor = self.cursorForPosition(event.pos())
        cursor.select(QTextCursor.WordUnderCursor)
        variable_name = cursor.selectedText().strip()

        # Stop any existing hover timer
        if self.hover_timer_active:
            self.hover_timer.stop()
            self.hover_timer_active = False

        # Check if we're over a valid variable name
        if variable_name and self._is_valid_variable_name(variable_name):
            # Store variable name and mouse position for later use
            self.current_hover_variable = variable_name
            self.last_hover_pos = event.globalPos()

            # Start 2-second delay timer
            self.hover_timer.start(2000)  # 2000 milliseconds = 2 seconds
            self.hover_timer_active = True
            print(f"Hover timer started for variable: {variable_name}")
        else:
            # Hide tooltip if not over a valid variable
            QToolTip.hideText()
            self.current_hover_variable = None

        super().mouseMoveEvent(event)

    def _handle_hover_timeout(self):
        """Handle hover timer timeout - query variable value after delay."""
        if self.current_hover_variable and self.last_hover_pos:
            print(f"Hover timeout for variable: {self.current_hover_variable}")
            # Emit signal for variable hover (this triggers GDB query)
            self.variable_hovered.emit(self.current_hover_variable)

            # Show tooltip with "Loading..." message
            QToolTip.showText(self.last_hover_pos, f"{self.current_hover_variable}: Loading...", self)
        else:
            print(f"Hover timeout but no valid variable")

    def _is_valid_variable_name(self, text: str) -> bool:
        """
        Check if text could be a valid variable name.

        Args:
            text: Text to check

        Returns:
            bool: True if text could be a valid variable name
        """
        # Basic variable name validation
        if not text:
            return False

        # Check if it's a valid identifier (starts with letter/underscore, followed by alphanumeric/underscore)
        if not text[0].isalpha() and text[0] != '_':
            return False

        # Check remaining characters
        for char in text[1:]:
            if not (char.isalnum() or char == '_'):
                return False

        # Avoid C/C++ keywords and common library functions
        keywords = {
            # C keywords
            'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do', 'double',
            'else', 'enum', 'extern', 'float', 'for', 'goto', 'if', 'int', 'long', 'register',
            'return', 'short', 'signed', 'sizeof', 'static', 'struct', 'switch', 'typedef',
            'union', 'unsigned', 'void', 'volatile', 'while',
            # C++ keywords (common subset)
            'bool', 'catch', 'class', 'const_cast', 'delete', 'dynamic_cast', 'explicit',
            'false', 'friend', 'inline', 'mutable', 'namespace', 'new', 'operator',
            'private', 'protected', 'public', 'reinterpret_cast', 'static_cast', 'template',
            'this', 'throw', 'true', 'try', 'typeid', 'typename', 'using', 'virtual',
            # Common library functions (to reduce false positives)
            'printf', 'scanf', 'malloc', 'free', 'calloc', 'realloc', 'sizeof', 'strlen',
            'strcpy', 'strcmp', 'fopen', 'fclose', 'fread', 'fwrite', 'main', 'exit'
        }
        if text in keywords:
            return False

        return True

    def toggle_breakpoint(self, line_number: int):
        """Toggle breakpoint at specified line."""
        print(f"toggle_breakpoint called for line {line_number}")
        # Emit signal first - the main window will handle actual breakpoint setting
        # The visual marker will be updated based on whether GDB successfully sets the breakpoint
        self.breakpoint_toggled.emit(line_number)

    def add_breakpoint_marker(self, line_number: int):
        """Add visual breakpoint marker."""
        self.breakpoint_lines.add(line_number)
        # Trigger repaint of line number area
        self.line_number_area.update()
        print(f"Breakpoint visual marker added at line {line_number}")

    def remove_breakpoint_marker(self, line_number: int):
        """Remove visual breakpoint marker."""
        if line_number in self.breakpoint_lines:
            self.breakpoint_lines.remove(line_number)
        # Trigger repaint of line number area
        self.line_number_area.update()
        print(f"Breakpoint visual marker removed at line {line_number}")

    def get_breakpoint_lines(self) -> set:
        """Get all breakpoint line numbers."""
        return self.breakpoint_lines.copy()

    def clear_all_breakpoints(self):
        """Clear all breakpoints."""
        for line_number in list(self.breakpoint_lines):
            self._clear_breakpoint_marker(line_number)
        self.breakpoint_lines.clear()

    def update_variable_value(self, variable_name: str, value: str):
        """Update the stored value for a variable."""
        self.variable_values[variable_name] = value
        print(f"Updated variable value: {variable_name} = {value}")

    def get_variable_value(self, variable_name: str) -> str:
        """Get the stored value for a variable."""
        return self.variable_values.get(variable_name, "Loading...")

    # Line number area methods
    def line_number_area_width(self):
        """Calculate the width needed for the line number area."""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num /= 10
            digits += 1
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        """Update the line number area width."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """Update the line number area."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            cr.left(), cr.top(),
            self.line_number_area_width(), cr.height()
        )