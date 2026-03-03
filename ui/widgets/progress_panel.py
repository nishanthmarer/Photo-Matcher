##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: progress_panel.py
# Description: Generic progress display panel. Acts as a simple output screen — any worker or component can send
#              data to it via two slots: update_bar (progress bar + stats) and write_log (log entries). The panel
#              does not know or care what operation is running.
# Year: 2026
###########################################################################################################################

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QTextEdit,
    QFrame,
)

from ui.theme import Colors, PANEL_CARD_STYLE, header_stylesheet


class ProgressPanel(QFrame):
    """Generic progress display — a dumb screen that shows whatever is sent to it.

    Two slots:
        update_bar(current, total, message): updates the progress bar and stats label.
        write_log(message, color): appends a line to the log area.

    Any worker, any phase, any operation can use these. The panel doesn't care what's running.
    """

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"ProgressPanel {{ {PANEL_CARD_STYLE} }}")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        header = QLabel("⚡ Progress")
        header.setStyleSheet(header_stylesheet())
        layout.addWidget(header)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        layout.addWidget(self._progress_bar)

        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_MUTED};")
        layout.addWidget(self._stats_label)

        self._log_area = QTextEdit()
        self._log_area.setReadOnly(True)
        layout.addWidget(self._log_area)

    @Slot(int, int, str)
    def update_bar(self, current: int, total: int, message: str) -> None:
        """Update the progress bar and stats label.

        Args:
            current: Current progress count.
            total: Total count.
            message: Text to show in the stats label.
        """
        if total > 0:
            self._progress_bar.setValue(int((current / total) * 100))
        self._stats_label.setText(message)

    @Slot(str)
    def write_log(self, message: str, color: str = None) -> None:
        """Append a line to the log area.

        Args:
            message: Text to append.
            color: Optional CSS color. Defaults to dim gray.
        """
        c = color or Colors.TEXT_DIM
        self._log_area.append(f'<span style="color: {c}">{message}</span>')
        scrollbar = self._log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_bar_value(self, value: int) -> None:
        """Directly set progress bar percentage (0-100)."""
        self._progress_bar.setValue(value)

    def set_stats_text(self, text: str) -> None:
        """Directly set stats label text."""
        self._stats_label.setText(text)

    def reset_bar(self) -> None:
        """Reset only the progress bar and stats — log preserved."""
        self._progress_bar.setValue(0)
        self._stats_label.setText("")

    def reset_all(self) -> None:
        """Clear everything including log."""
        self._progress_bar.setValue(0)
        self._stats_label.setText("")
        self._log_area.clear()