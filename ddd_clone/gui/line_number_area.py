"""
Line number area for source viewer.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QFont, QColor, QBrush, QMouseEvent


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
            # Convert click position to source viewer coordinates
            viewer_pos = self.source_viewer.mapFrom(self, event.pos())
            # Get cursor at this position
            cursor = self.source_viewer.cursorForPosition(viewer_pos)
            line_number = cursor.blockNumber() + 1  # Convert to 1-based

            if line_number > 0:
                self.line_number_clicked.emit(line_number)
                return  # Event handled

        super().mousePressEvent(event)

    def paintEvent(self, event):
        """Paint the line numbers and breakpoint markers."""
        painter = QPainter(self)
        # Explicitly set the painter font to ensure it uses our font
        painter.setFont(self.font())
        painter.fillRect(event.rect(), QColor(202, 234, 206))

        # Get first visible block using cursor at top-left of viewport
        cursor = self.source_viewer.cursorForPosition(QPoint(0, 0))
        block = cursor.block()
        block_number = block.blockNumber()

        # Get document layout
        layout = self.source_viewer.document().documentLayout()

        # Get viewport and scroll information
        viewport = self.source_viewer.viewport()
        scroll_y = self.source_viewer.verticalScrollBar().value()

        # Get block bounding rect (relative to document)
        block_rect = layout.blockBoundingRect(block)
        top = block_rect.y() - scroll_y
        bottom = top + block_rect.height()

        # Paint visible blocks
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_number = block_number + 1

                # Calculate block height for vertical alignment
                block_height = int(bottom - top)

                # Draw breakpoint marker if this line has a breakpoint
                if line_number in self.source_viewer.breakpoint_lines:
                    # Draw red circle for breakpoint (left of line numbers)
                    painter.setBrush(QBrush(QColor(255, 0, 0)))  # Red
                    painter.setPen(Qt.NoPen)
                    marker_size = 8
                    marker_x = 6  # Position to the left of line numbers
                    marker_y = int(top) + (block_height - marker_size) // 2
                    painter.drawEllipse(marker_x, marker_y, marker_size, marker_size)

                # Draw line number
                number = str(line_number)
                painter.setPen(Qt.black)
                rect = QRect(0, int(top), self.width() - 5, block_height)
                painter.drawText(rect, Qt.AlignRight | Qt.AlignVCenter, number)

            # Move to next block
            block = block.next()
            block_number += 1
            if not block.isValid():
                break

            block_rect = layout.blockBoundingRect(block)
            top = bottom
            bottom = top + block_rect.height()

    def changeEvent(self, event):
        """Handle change events, including font changes."""
        if event.type() == event.FontChange:
            self.update()
        super().changeEvent(event)