"""
Source code viewer with syntax highlighting.
"""

from PyQt5.QtWidgets import QPlainTextEdit, QTextEdit, QToolTip
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRectF
from PyQt5.QtGui import QFont, QTextCursor, QColor, QTextCharFormat, QMouseEvent

from .line_number_area import LineNumberArea


try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import HtmlFormatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


class SourceViewer(QTextEdit):
    """
    Source code viewer with basic syntax highlighting.
    """

    current_line_changed = pyqtSignal(int)
    breakpoint_toggled = pyqtSignal(int)  # line_number
    variable_hovered = pyqtSignal(str)  # variable_name

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Courier New", 18))  # Larger font
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

        # Set background color to bean green (RGB: 202, 234, 206)
        self.setStyleSheet("background-color: rgb(202, 234, 206);")

        self.setup_ui()

    def setup_ui(self):
        """Set up the source viewer UI."""
        # Set line wrap mode
        self.setLineWrapMode(QTextEdit.NoWrap)

        # Set tab width
        self.setTabStopDistance(40)

        # Enable mouse tracking for tooltips
        self.setMouseTracking(True)

        # Connect signals for line number area
        # Use document's blockCountChanged signal if available
        if hasattr(self.document(), 'blockCountChanged'):
            self.document().blockCountChanged.connect(self.update_line_number_area_width)
        else:
            # Fallback to textChanged signal
            self.textChanged.connect(self.update_line_number_area_width)

        # Connect scroll bar value change to update line number area
        self.verticalScrollBar().valueChanged.connect(self._handle_scroll_for_line_numbers)

        # Connect line number area click signal
        self.line_number_area.line_number_clicked.connect(self.toggle_breakpoint)

        # Set initial line number area width
        self.update_line_number_area_width(0)

    def change_font_size(self, delta: int):
        """
        Change font size by delta (positive to increase, negative to decrease).

        Args:
            delta: Change in font size (e.g., +1 to increase, -1 to decrease)
        """
        current_font = self.font()
        current_size = current_font.pointSize()
        new_size = max(8, current_size + delta)  # Minimum size 8

        if new_size != current_size:
            # Create new font by copying current font and changing size
            new_font = QFont(current_font)
            new_font.setPointSize(new_size)

            # Update source viewer font
            self.setFont(new_font)

            # Update line number area font
            self.line_number_area.set_font(new_font)

            # Update line number area width
            self.update_line_number_area_width(0)

            # Update line number area geometry
            cr = self.contentsRect()
            self.line_number_area.setGeometry(
                cr.left(), cr.top(),
                self.line_number_area_width(), cr.height()
            )

            # Trigger repaint of line number area
            self.line_number_area.update()

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

            # Create HTML formatter with transparent background
            # Use 'pastie' style for good contrast on light backgrounds
            formatter = HtmlFormatter(
                style='pastie',
                noclasses=True,
                nobackground=True
            )

            # Highlight code
            highlighted_code = highlight(source_code, lexer, formatter)

            # Debug: print first 500 chars of HTML to verify highlighting
            # print(f"Generated HTML (first 500 chars): {highlighted_code[:500]}")

            # Set HTML content
            self.setHtml(highlighted_code)

        except Exception as e:
            # Fallback to plain text if highlighting fails
            # print(f"Syntax highlighting failed: {e}")
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
        # Calculate line number area width
        line_number_width = self.line_number_area_width()

        # Check if click is in the line number area (including breakpoint marker area)
        if (event.button() == Qt.LeftButton and
            event.pos().x() <= line_number_width):  # Click within line number area

            # Get the line number that was clicked
            cursor = self.cursorForPosition(event.pos())
            line_number = cursor.blockNumber() + 1  # Convert to 1-based line numbers

            # Toggle breakpoint
            self.toggle_breakpoint(line_number)
            return  # Don't propagate the event
        else:
            pass  # Click outside line number area

        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for font size adjustment."""
        # Check for Ctrl+ or Ctrl- (usually Ctrl+= and Ctrl+-)
        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Equal or event.key() == Qt.Key_Plus:
                # Increase font size (Ctrl+ or Ctrl+=)
                self.change_font_size(1)
                event.accept()
                return
            elif event.key() == Qt.Key_Minus:
                # Decrease font size (Ctrl-)
                self.change_font_size(-1)
                event.accept()
                return

        super().keyPressEvent(event)

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
        else:
            # Hide tooltip if not over a valid variable
            QToolTip.hideText()
            self.current_hover_variable = None

        super().mouseMoveEvent(event)

    def _handle_hover_timeout(self):
        """Handle hover timer timeout - query variable value after delay."""
        if self.current_hover_variable and self.last_hover_pos:
            # Emit signal for variable hover (this triggers GDB query)
            self.variable_hovered.emit(self.current_hover_variable)

            # Show tooltip with "Loading..." message
            QToolTip.showText(self.last_hover_pos, "Loading...", self)
        else:
            pass  # No valid variable for hover

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
        # Emit signal first - the main window will handle actual breakpoint setting
        # The visual marker will be updated based on whether GDB successfully sets the breakpoint
        self.breakpoint_toggled.emit(line_number)

    def add_breakpoint_marker(self, line_number: int):
        """Add visual breakpoint marker."""
        self.breakpoint_lines.add(line_number)
        # Trigger repaint of line number area
        self.line_number_area.update()

    def remove_breakpoint_marker(self, line_number: int):
        """Remove visual breakpoint marker."""
        if line_number in self.breakpoint_lines:
            self.breakpoint_lines.remove(line_number)
        # Trigger repaint of line number area
        self.line_number_area.update()

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

    def update_variable_tooltip(self, variable_name: str, value: str):
        """Update the tooltip with the actual variable value."""
        # Update stored value
        self.update_variable_value(variable_name, value)

        # If this is the current hover variable, update the tooltip immediately
        if (variable_name == self.current_hover_variable and
            self.last_hover_pos is not None):
            QToolTip.showText(self.last_hover_pos, f"{value}", self)

    def get_variable_value(self, variable_name: str) -> str:
        """Get the stored value for a variable."""
        return self.variable_values.get(variable_name, "Loading...")

    # Line number area methods
    def blockCount(self):
        """Return the number of blocks (lines) in the document."""
        return self.document().blockCount()

    def firstVisibleBlock(self):
        """Return the first visible block in the viewport."""
        cursor = self.cursorForPosition(QPoint(0, 0))
        return cursor.block()

    def blockBoundingGeometry(self, block):
        """Return the bounding geometry of a block in document coordinates."""
        if not block.isValid():
            return QRectF()
        layout = self.document().documentLayout()
        return layout.blockBoundingRect(block)

    def blockBoundingRect(self, block):
        """Return the bounding rectangle of a block in viewport coordinates."""
        geometry = self.blockBoundingGeometry(block)
        if geometry.isNull():
            return QRectF()
        # Only need height for line number area calculations
        return QRectF(0, 0, 0, geometry.height())

    def contentOffset(self):
        """Return the content offset (scroll position)."""
        # For QTextEdit, content offset is the scroll position
        return QPoint(self.horizontalScrollBar().value(), self.verticalScrollBar().value())

    def line_number_area_width(self):
        """Calculate the width needed for the line number area."""
        digits = 1
        # Use document's blockCount method
        max_num = max(1, self.document().blockCount())
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

    def _handle_scroll_for_line_numbers(self):
        """Handle scroll bar value change to update line number area."""
        self.line_number_area.update()

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            cr.left(), cr.top(),
            self.line_number_area_width(), cr.height()
        )