"""
Line number area for source viewer.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QFont, QColor, QBrush, QMouseEvent, QTextCursor


class LineNumberArea(QWidget):
    """
    Widget that displays line numbers for the source viewer.
    """

    # Signal emitted when line number area is clicked
    line_number_clicked = pyqtSignal(int)  # line_number

    def __init__(self, source_viewer):
        super().__init__(source_viewer)
        self.source_viewer = source_viewer
        self.setFont(QFont("Courier New", 18))  # Larger font

    def set_font(self, font):
        """Set font for line number area and trigger repaint."""
        self.setFont(font)
        self.update()
        self.repaint()  # Force immediate repaint

    def sizeHint(self):
        """Return the preferred size of the line number area."""
        return self.source_viewer.line_number_area_width(), 0

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse clicks in the line number area."""
        if event.button() == Qt.LeftButton:
            try:
                # Get click position relative to this widget
                pos_in_self = event.pos()

                # Map the position to the source viewer's coordinate system
                # This accounts for the line number area's position within the source viewer
                viewer_pos = self.mapTo(self.source_viewer, pos_in_self)

                # Get cursor at this position in the source viewer
                cursor = self.source_viewer.cursorForPosition(viewer_pos)
                if not cursor:
                    raise ValueError("Invalid cursor")

                # Get the block and ensure it's valid
                block = cursor.block()
                if not block.isValid():
                    raise ValueError("Invalid block")

                line_number = block.blockNumber() + 1  # Convert to 1-based

                if line_number > 0:
                    self.line_number_clicked.emit(line_number)
                    event.accept()  # Mark event as handled
                    return  # Event handled
            except Exception as e:
                # If anything goes wrong, fall back to default behavior
                print(f"Error in line number area mousePressEvent: {e}")
                pass

        # Call super for non-left button clicks, invalid line numbers, or errors
        super().mousePressEvent(event)

    def paintEvent(self, event):
        """Paint the line numbers and breakpoint markers."""
        painter = QPainter(self)
        # Explicitly set the painter font to ensure it uses our font
        painter.setFont(self.font())
        painter.fillRect(event.rect(), QColor(202, 234, 206))

        content_offset = self.source_viewer.contentOffset()

        block = self.source_viewer.firstVisibleBlock()
        while block.isValid():
            if not block.isVisible():
                block = block.next()
                continue

            # Calculate block position in line number area coordinates
            block_geom = self.source_viewer.blockBoundingGeometry(block)
            if block_geom.isNull():
                break

            # Convert document coordinates to viewport coordinates
            top = block_geom.translated(content_offset).top()
            block_height = block_geom.height()
            bottom = top + block_height

            # Check if block is visible in line number area
            if top > event.rect().bottom():
                break  # Blocks are sorted, no more visible blocks
            if bottom < event.rect().top():
                block = block.next()
                continue  # Block not visible yet

            line_number = block.blockNumber() + 1

            # Convert to integers for drawing
            top_int = int(top)
            block_height_int = int(block_height)

            # Draw breakpoint marker if this line has a breakpoint
            if line_number in self.source_viewer.breakpoint_lines:
                # Draw red circle for breakpoint (left of line numbers)
                painter.setBrush(QBrush(QColor(255, 0, 0)))  # Red
                painter.setPen(Qt.NoPen)
                marker_size = 8
                marker_x = 6  # Position to the left of line numbers
                marker_y = top_int + (block_height_int - marker_size) // 2
                painter.drawEllipse(marker_x, marker_y, marker_size, marker_size)

            # Draw line number
            number = str(line_number)
            painter.setPen(Qt.black)
            rect = QRect(0, top_int, self.width() - 5, block_height_int)
            painter.drawText(rect, Qt.AlignRight | Qt.AlignVCenter, number)

            block = block.next()

    def changeEvent(self, event):
        """Handle change events, including font changes."""
        if event.type() == event.FontChange:
            self.update()
        super().changeEvent(event)