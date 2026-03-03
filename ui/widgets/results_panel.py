##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: results_panel.py
# Description: Displays segregation results with per-person photo counts. Shows matched photos per person with
#              buttons to open output folders and review images for cleanup. Shows "All up to date" when re-running
#              with no new matches.
# Year: 2026
###########################################################################################################################

from pathlib import Path

from PySide6.QtCore import Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QSizePolicy,
)

from ui.theme import (
    Colors, PANEL_CARD_STYLE, header_stylesheet,
    btn_secondary_stylesheet, result_entry_stylesheet,
    btn_review_stylesheet,
)


class ResultsPanel(QFrame):
    """Displays segregation results with per-person photo counts."""

    review_requested = Signal(str)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self._output_dir = ""
        self._result_widgets: list[QWidget] = []

        self.setStyleSheet(f"ResultsPanel {{ {PANEL_CARD_STYLE} }}")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        header = QLabel("✅ Results")
        header.setStyleSheet(header_stylesheet())
        layout.addWidget(header)

        self._placeholder_label = QLabel("Results appear after generating folders")
        self._placeholder_label.setStyleSheet(f"font-size: 12px; color: {Colors.TEXT_DARK};")
        layout.addWidget(self._placeholder_label)

        self._results_widget = QWidget()
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setSpacing(5)
        self._results_layout.addStretch()

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setWidget(self._results_widget)
        self._scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._scroll_area.setVisible(False)
        layout.addWidget(self._scroll_area)

        self._open_output_button = QPushButton("📂 Open Output Folder")
        self._open_output_button.setStyleSheet(btn_secondary_stylesheet())
        self._open_output_button.setVisible(False)
        self._open_output_button.setMinimumHeight(34)
        self._open_output_button.clicked.connect(self._on_open_output_clicked)
        layout.addWidget(self._open_output_button)

    def display_results(self, summary: dict, output_dir: str) -> None:
        self._output_dir = output_dir
        self._clear_results()

        self._placeholder_label.setVisible(False)
        self._scroll_area.setVisible(True)
        self._open_output_button.setVisible(True)

        if "error" in summary:
            self._add_result_entry("Error", summary["error"], is_error=True)
            return

        if summary.get("stopped"):
            self._add_result_entry("Stopped", "Generation was stopped by user", is_error=True)
            return

        total_new = sum(v for v in summary.values() if isinstance(v, int))

        if total_new == 0:
            self._add_result_entry("All up to date", "No new photos to copy — output folders are current.", is_success=True)
            return

        for name, count in summary.items():
            if not isinstance(count, int) or count == 0:
                continue
            folder_path = str(Path(output_dir) / name)
            self._add_result_entry(name, f"{count:,} new photos copied", folder_path=folder_path)

    def reset(self) -> None:
        self._clear_results()
        self._placeholder_label.setVisible(True)
        self._scroll_area.setVisible(False)
        self._open_output_button.setVisible(False)
        self._output_dir = ""

    def _add_result_entry(self, name: str, detail: str, folder_path: str = "",
                          is_error: bool = False, is_success: bool = False) -> None:
        entry = QFrame()
        entry.setStyleSheet(result_entry_stylesheet())
        entry_layout = QHBoxLayout(entry)
        entry_layout.setContentsMargins(10, 8, 10, 8)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(name)
        if is_error:
            name_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {Colors.RED};")
        elif is_success:
            name_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {Colors.GREEN};")
        else:
            name_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {Colors.TEXT_PRIMARY};")

        detail_label = QLabel(detail)
        if is_error:
            detail_label.setStyleSheet(f"font-size: 11px; color: #f87171;")
        elif is_success:
            detail_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_MUTED};")
        else:
            detail_label.setStyleSheet(f"font-size: 11px; color: {Colors.GREEN};")

        info_layout.addWidget(name_label)
        info_layout.addWidget(detail_label)
        entry_layout.addLayout(info_layout)
        entry_layout.addStretch()

        if folder_path and not is_error and not is_success:
            review_button = QPushButton("🔍 Review")
            review_button.setStyleSheet(btn_review_stylesheet())
            review_button.clicked.connect(
                lambda checked=False, path=folder_path: self._on_review_clicked(path)
            )
            entry_layout.addWidget(review_button)

            open_button = QPushButton("📂 Open")
            open_button.setStyleSheet(btn_secondary_stylesheet())
            open_button.clicked.connect(
                lambda checked=False, path=folder_path: self._open_folder(path)
            )
            entry_layout.addWidget(open_button)

        insert_position = self._results_layout.count() - 1
        self._results_layout.insertWidget(insert_position, entry)
        self._result_widgets.append(entry)

    def _clear_results(self) -> None:
        for widget in self._result_widgets:
            self._results_layout.removeWidget(widget)
            widget.deleteLater()
        self._result_widgets.clear()

    def _on_review_clicked(self, folder_path: str) -> None:
        """Emit review_requested signal with the folder path for the clicked person."""
        self.review_requested.emit(folder_path)

    @staticmethod
    def _open_folder(folder_path: str) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

    def _on_open_output_clicked(self) -> None:
        if self._output_dir:
            self._open_folder(self._output_dir)