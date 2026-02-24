"""
Line number area for source viewer.
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QFont, QColor, QBrush, QMouseEvent, QTextCursor, QPen, QPainterPath


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
        self.arrow_area_width = 20  # Width for debug arrow area
        # Connect to current line changes to update arrow
        self.source_viewer.current_line_changed.connect(self.update)

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
        # Debug: print paint event information
        # print(f"LineNumberArea paintEvent: event.rect={event.rect()}, self.rect={self.rect()}")

        painter = QPainter(self)
        # Explicitly set the painter font to ensure it uses our font
        painter.setFont(self.font())
        # Fill the update region background (use event.rect() as in the working version)
        painter.fillRect(event.rect(), QColor(202, 234, 206))

        block = self.source_viewer.firstVisibleBlock()
        if not block.isValid():
            return

        block_number = block.blockNumber()

        while block.isValid():
            # Get block rectangle in viewport coordinates
            block_rect = self.source_viewer.blockBoundingRect(block)
            if block_rect.isNull():
                break

            top = block_rect.top()
            bottom = top + block_rect.height()

            # Debug: print block information (only first few)
            # if block_number < 3:
            #     print(f"Block {block_number}: top={top}, bottom={bottom}, height={block_rect.height()}")

            # Check if block is visible in line number area
            if block.isVisible() and top <= event.rect().bottom() and bottom >= event.rect().top():
                line_number = block_number + 1

                # Calculate block height for vertical alignment
                block_height = int(block_rect.height())

                # Draw debug arrow for current line
                if hasattr(self.source_viewer, 'current_line') and line_number == self.source_viewer.current_line:
                    # Draw dark green right-pointing arrow in left area
                    arrow_size = min(6, block_height // 3)
                    arrow_center_x = self.arrow_area_width // 2
                    arrow_center_y = int(top) + block_height // 2

                    # Create right-pointing triangle
                    arrow_path = QPainterPath()
                    arrow_path.moveTo(arrow_center_x - arrow_size, arrow_center_y - arrow_size)  # Left-top
                    arrow_path.lineTo(arrow_center_x + arrow_size, arrow_center_y)              # Right tip
                    arrow_path.lineTo(arrow_center_x - arrow_size, arrow_center_y + arrow_size)  # Left-bottom
                    arrow_path.closeSubpath()

                    # Fill with dark green
                    painter.save()
                    painter.setBrush(QBrush(QColor(0, 150, 0)))  # Dark green
                    painter.setPen(Qt.NoPen)
                    painter.drawPath(arrow_path)
                    painter.restore()

                # Draw breakpoint marker if this line has a breakpoint
                if line_number in self.source_viewer.breakpoint_lines:
                    # Draw transparent red box around line number
                    # Calculate text width for proper box sizing
                    number_text = str(line_number)
                    text_width = painter.fontMetrics().horizontalAdvance(number_text)
                    # Box dimensions with padding
                    box_padding = 4
                    box_width = text_width + box_padding * 2
                    box_height = block_height - 2  # Slightly smaller than line height
                    # Position box to align with right-aligned line numbers
                    box_right = self.width() - 10  # Same right edge as line numbers
                    box_left = box_right - box_width
                    box_top = int(top) + 1

                    # Draw semi-transparent red box
                    painter.setBrush(QBrush(QColor(255, 0, 0, 64)))  # Semi-transparent red fill
                    painter.setPen(QColor(255, 0, 0))  # Solid red border
                    painter.drawRect(box_left, box_top, box_width, box_height)

                # Draw line number
                number = str(line_number)
                painter.setPen(Qt.black)
                rect = QRect(self.arrow_area_width, int(top), self.width() - 10 - self.arrow_area_width, block_height)
                painter.drawText(rect, Qt.AlignRight | Qt.AlignVCenter, number)

            # If block is below the visible area, stop (blocks are sorted)
            if top > event.rect().bottom():
                break

            # Move to next block
            block = block.next()
            if not block.isValid():
                break
            block_number += 1

        # Draw vertical separator line between line numbers and code
        painter.setPen(QPen(QColor(180, 180, 180), 1))  # Light gray, 1px wide solid line
        line_x = self.width() - 1  # Right edge of line number area
        painter.drawLine(line_x, 0, line_x, self.height())

    def changeEvent(self, event):
        """Handle change events, including font changes."""
        if event.type() == event.FontChange:
            self.update()
        super().changeEvent(event)