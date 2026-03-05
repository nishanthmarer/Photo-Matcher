##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: status_bar.py
# Description: Application status bar widget displayed at the bottom of the main window. Shows a color-coded pulsing
#              indicator dot, current status message, phase label, and GPU/CPU device indicator. Receives updates
#              from all workers via Qt slots.
# Year: 2026
###########################################################################################################################

from PySide6.QtCore import Qt, Slot, QTimer, QSize
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
)

from ui.theme import Colors


class PulsingDot(QWidget):
    """A small colored dot that pulses during active operations."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setFixedSize(QSize(12, 12))

        self._color = QColor(Colors.TEXT_DIM)
        self._opacity = 1.0
        self._pulsing = False
        self._fading_out = True

        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._animate)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def set_pulsing(self, pulsing: bool) -> None:
        self._pulsing = pulsing
        if pulsing:
            self._timer.start()
        else:
            self._timer.stop()
            self._opacity = 1.0
            self.update()

    def _animate(self) -> None:
        step = 0.04
        if self._fading_out:
            self._opacity -= step
            if self._opacity <= 0.3:
                self._opacity = 0.3
                self._fading_out = False
        else:
            self._opacity += step
            if self._opacity >= 1.0:
                self._opacity = 1.0
                self._fading_out = True
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(self._color)
        color.setAlphaF(self._opacity)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 8, 8)
        painter.end()


class StatusBar(QWidget):
    """Application status bar — sits at the bottom of the main window."""

    PHASE_COLORS = {
        "idle": Colors.TEXT_DIM,
        "loading": Colors.YELLOW,
        "caching": Colors.BLUE,
        "generating": Colors.PURPLE,
        "ready": Colors.GREEN,
        "done": Colors.GREEN,
        "error": Colors.RED,
        "stopped": Colors.YELLOW,
    }

    PHASE_LABELS = {
        "idle": "💤 Idle",
        "loading": "⏳ Initializing",
        "caching": "🔍 Building cache",
        "generating": "📂 Generating folders",
        "ready": "✅ Ready",
        "done": "✅ Complete",
        "error": "❌ Error",
        "stopped": "⏹ Stopped",
    }

    ACTIVE_PHASES = {"loading", "caching", "generating"}

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.setFixedHeight(34)
        self.setStyleSheet(f"""
            background-color: {Colors.BG_STATUS_BAR};
            border-top: 1px solid {Colors.BORDER};
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        self._dot = PulsingDot()
        layout.addWidget(self._dot)

        self._message_label = QLabel("Starting up...")
        self._message_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(self._message_label)

        layout.addStretch()

        self._phase_label = QLabel("⏳ Initializing")
        self._phase_label.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 13px; font-weight: bold;")
        layout.addWidget(self._phase_label)

        # Separator between phase and device indicator
        separator = QLabel("│")
        separator.setStyleSheet(f"color: {Colors.BORDER_ACCENT}; font-size: 13px;")
        layout.addWidget(separator)

        # GPU / CPU device indicator
        self._device_label = QLabel("")
        self._device_label.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 11px; font-weight: bold;")
        layout.addWidget(self._device_label)

    @Slot(str, str)
    def on_status_updated(self, message: str, phase: str) -> None:
        self._message_label.setText(message)

        color = self.PHASE_COLORS.get(phase, Colors.TEXT_DIM)
        self._dot.set_color(color)
        self._dot.set_pulsing(phase in self.ACTIVE_PHASES)

        label = self.PHASE_LABELS.get(phase, "")
        self._phase_label.setText(label)

        if phase in ("ready", "done"):
            self._message_label.setStyleSheet(f"color: {Colors.GREEN}; font-size: 12px;")
            self._phase_label.setStyleSheet(f"color: {Colors.GREEN}; font-size: 13px; font-weight: bold;")
        elif phase == "error":
            self._message_label.setStyleSheet(f"color: {Colors.RED}; font-size: 12px;")
            self._phase_label.setStyleSheet(f"color: {Colors.RED}; font-size: 13px; font-weight: bold;")
        elif phase == "stopped":
            self._message_label.setStyleSheet(f"color: {Colors.YELLOW}; font-size: 12px;")
            self._phase_label.setStyleSheet(f"color: {Colors.YELLOW}; font-size: 13px; font-weight: bold;")
        else:
            self._message_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
            self._phase_label.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 13px; font-weight: bold;")

    def set_device(self, device: str) -> None:
        """Show whether GPU or CPU is active in the status bar.

        Args:
            device: Device string — if it contains 'cuda' or 'gpu' (case-insensitive),
                    shows a green GPU badge. Otherwise shows a yellow CPU badge.
        """
        if "cuda" in device.lower() or "gpu" in device.lower():
            self._device_label.setText("🟢 GPU")
            self._device_label.setStyleSheet(
                f"color: {Colors.GREEN}; font-size: 11px; font-weight: bold;"
            )
        else:
            self._device_label.setText("🟡 CPU")
            self._device_label.setStyleSheet(
                f"color: {Colors.YELLOW}; font-size: 11px; font-weight: bold;"
            )