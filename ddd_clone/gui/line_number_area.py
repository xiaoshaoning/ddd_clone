"""
Line number area for source viewer.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect, pyqtSignal
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
        self.setFont(QFont("Courier New", 12))  # Larger font

    def sizeHint(self):
        """Return the preferred size of the line number area."""
        return self.source_viewer.line_number_area_width(), 0

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse clicks in the line number area."""
        if event.button() == Qt.LeftButton:
            # Calculate which line was clicked based on y coordinate
            y_pos = event.pos().y()

            # Find the line number at this y position
            block = self.source_viewer.firstVisibleBlock()
            block_number = block.blockNumber()
            top = self.source_viewer.blockBoundingGeometry(block).translated(
                self.source_viewer.contentOffset()).top()
            bottom = top + self.source_viewer.blockBoundingRect(block).height()

            line_number = -1
            while block.isValid() and top <= y_pos:
                if bottom >= y_pos:
                    line_number = block_number + 1  # Convert to 1-based
                    break

                block = block.next()
                top = bottom
                bottom = top + self.source_viewer.blockBoundingRect(block).height()
                block_number += 1

            if line_number > 0:
                print(f"[LineNumberArea] Click detected at line {line_number}")
                self.line_number_clicked.emit(line_number)
                return  # Event handled

        super().mousePressEvent(event)

    def paintEvent(self, event):
        """Paint the line numbers and breakpoint markers."""
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor(240, 240, 240))

        block = self.source_viewer.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.source_viewer.blockBoundingGeometry(block).translated(
            self.source_viewer.contentOffset()).top()
        bottom = top + self.source_viewer.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_number = block_number + 1

                # Draw breakpoint marker if this line has a breakpoint
                if line_number in self.source_viewer.breakpoint_lines:
                    # Draw red circle for breakpoint (left of line numbers)
                    painter.setBrush(QBrush(QColor(255, 0, 0)))  # Red
                    painter.setPen(Qt.NoPen)
                    marker_size = 8
                    marker_x = 6  # Position to the left of line numbers
                    marker_y = int(top) + (self.fontMetrics().height() - marker_size) // 2
                    painter.drawEllipse(marker_x, marker_y, marker_size, marker_size)

                # Draw line number
                number = str(line_number)
                painter.setPen(Qt.black)
                rect = QRect(0, int(top), self.width() - 5, self.fontMetrics().height())
                painter.drawText(rect, Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.source_viewer.blockBoundingRect(block).height()
            block_number += 1