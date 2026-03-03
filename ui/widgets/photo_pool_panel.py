##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: photo_pool_panel.py
# Description: Panel for selecting source/output folders and triggering cache building. Contains Build Cache + Stop
#              buttons and a Clear Cache button. Output defaults to a sibling folder of the source.
# Year: 2026
###########################################################################################################################

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QFrame,
)

from config import AppConfig
from services.photo_scanner import PhotoScanner
from ui.theme import (
    Colors, Fonts, PANEL_CARD_STYLE, header_stylesheet, label_stylesheet,
    btn_primary_stylesheet, btn_secondary_stylesheet, btn_stop_stylesheet,
    btn_clear_stylesheet,
)


class PhotoPoolPanel(QFrame):
    """Panel for selecting source/output folders and building the embedding cache."""

    source_selected = Signal(str)
    output_selected = Signal(str)
    cache_requested = Signal()
    cache_stop_requested = Signal()
    clear_cache_requested = Signal()

    def __init__(self, config: AppConfig, parent: QWidget = None) -> None:
        super().__init__(parent)

        self._config = config
        self._scanner = PhotoScanner(config)
        self._source_dir = ""
        self._output_dir = ""

        self.setStyleSheet(f"PhotoPoolPanel {{ {PANEL_CARD_STYLE} }}")
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        # Header with Clear Cache button
        header_row = QHBoxLayout()
        header = QLabel("📁 Photo Source")
        header.setStyleSheet(header_stylesheet())
        header_row.addWidget(header)
        header_row.addStretch()
        self._clear_cache_button = QPushButton("🗑 Clear Cache")
        self._clear_cache_button.setStyleSheet(btn_clear_stylesheet())
        self._clear_cache_button.setFixedHeight(24)
        header_row.addWidget(self._clear_cache_button)
        layout.addLayout(header_row)

        # Source folder
        source_label = QLabel("SOURCE FOLDER")
        source_label.setStyleSheet(label_stylesheet())
        layout.addWidget(source_label)

        source_row = QHBoxLayout()
        self._source_input = QLineEdit()
        self._source_input.setReadOnly(True)
        self._source_input.setPlaceholderText("Select folder containing photos")
        source_row.addWidget(self._source_input)
        self._source_browse_button = QPushButton("Browse")
        self._source_browse_button.setStyleSheet(btn_secondary_stylesheet())
        self._source_browse_button.setMinimumHeight(36)
        source_row.addWidget(self._source_browse_button)
        layout.addLayout(source_row)

        # Output folder
        output_label = QLabel("OUTPUT FOLDER")
        output_label.setStyleSheet(label_stylesheet())
        layout.addWidget(output_label)

        output_row = QHBoxLayout()
        self._output_input = QLineEdit()
        self._output_input.setReadOnly(True)
        self._output_input.setPlaceholderText("Defaults to source_output sibling folder")
        output_row.addWidget(self._output_input)
        self._output_browse_button = QPushButton("Browse")
        self._output_browse_button.setStyleSheet(btn_secondary_stylesheet())
        self._output_browse_button.setMinimumHeight(36)
        output_row.addWidget(self._output_browse_button)
        layout.addLayout(output_row)

        # Scan summary — plain text, no box
        self._summary_label = QLabel("Status: No folder selected")
        self._summary_label.setStyleSheet(f"font-size: {Fonts.SMALL}; color: {Colors.TEXT_DIM}; border: none; background: transparent;")
        self._summary_label.setWordWrap(True)
        layout.addWidget(self._summary_label)

        # Cache status
        self._cache_status_label = QLabel("")
        self._cache_status_label.setStyleSheet(f"font-size: {Fonts.SMALL}; color: {Colors.TEXT_DIM}; border: none; background: transparent;")
        layout.addWidget(self._cache_status_label)

        layout.addStretch()

        # Separator line + Build Cache + Stop
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {Colors.SEPARATOR}; border: none;")
        layout.addWidget(separator)

        cache_section = QWidget()
        cache_section.setStyleSheet("background: transparent; border: none;")
        cache_layout = QVBoxLayout(cache_section)
        cache_layout.setContentsMargins(0, 6, 0, 0)
        cache_layout.setSpacing(4)

        btn_row = QHBoxLayout()
        self._cache_button = QPushButton("🔍 Build Cache")
        self._cache_button.setStyleSheet(btn_primary_stylesheet())
        self._cache_button.setEnabled(False)
        self._cache_button.setMinimumHeight(38)
        btn_row.addWidget(self._cache_button)

        self._cache_stop_button = QPushButton("⏹")
        self._cache_stop_button.setStyleSheet(btn_stop_stylesheet())
        self._cache_stop_button.setEnabled(False)
        self._cache_stop_button.setFixedSize(42, 38)
        btn_row.addWidget(self._cache_stop_button)
        cache_layout.addLayout(btn_row)

        layout.addWidget(cache_section)

    def _connect_signals(self) -> None:
        self._source_browse_button.clicked.connect(self._on_source_browse)
        self._output_browse_button.clicked.connect(self._on_output_browse)
        self._cache_button.clicked.connect(self._on_cache_clicked)
        self._cache_stop_button.clicked.connect(self._on_cache_stop_clicked)
        self._clear_cache_button.clicked.connect(self._on_clear_cache_clicked)

    def _on_source_browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Photo Source Folder")
        if not directory:
            return

        self._source_dir = directory
        self._source_input.setText(directory)

        default_output = str(Path(directory).parent / f"{Path(directory).name}_output")
        self._output_dir = default_output
        self._output_input.setText(default_output)

        self._update_summary(directory)
        self._update_cache_button_state()
        self.source_selected.emit(directory)
        self.output_selected.emit(default_output)

    def _on_output_browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if not directory:
            return
        self._output_dir = directory
        self._output_input.setText(directory)
        self.output_selected.emit(directory)

    def _on_cache_clicked(self) -> None:
        self.cache_requested.emit()

    def _on_cache_stop_clicked(self) -> None:
        self._cache_stop_button.setEnabled(False)
        self.cache_stop_requested.emit()

    def _on_clear_cache_clicked(self) -> None:
        self.clear_cache_requested.emit()

    def _update_summary(self, directory: str) -> None:
        file_paths = self._scanner.scan(directory)
        summary = self._scanner.get_scan_summary(file_paths)
        total = summary.pop("total", 0)

        if total == 0:
            self._summary_label.setText("Status: No valid images found in this folder")
            return

        extension_parts = [f"{count:,} {ext}" for ext, count in sorted(summary.items())]
        self._summary_label.setText(f"📊 {total:,} images found: {', '.join(extension_parts)}")

    def _update_cache_button_state(self) -> None:
        self._cache_button.setEnabled(bool(self._source_dir))

    # ------------------------------------------------------------------------------------------------------------------
    # Public methods — called by MainWindow
    # ------------------------------------------------------------------------------------------------------------------

    def set_cache_status(self, found: bool, count: int = 0) -> None:
        """Update the cache status label.

        Args:
            found: True if a valid cache was found for the selected source.
            count: Number of cached entries.
        """
        if found:
            self._cache_status_label.setText(f"✅ Cache found — {count:,} photos cached")
            self._cache_status_label.setStyleSheet(f"font-size: {Fonts.SMALL}; color: {Colors.GREEN}; border: none; background: transparent;")
        else:
            self._cache_status_label.setText("❌ No cache found — build cache to process photos")
            self._cache_status_label.setStyleSheet(f"font-size: {Fonts.SMALL}; color: {Colors.RED}; border: none; background: transparent;")

    def set_cache_running(self, running: bool) -> None:
        if running:
            self._cache_button.setEnabled(False)
            self._cache_button.setText("🔍 Building Cache...")
            self._cache_stop_button.setEnabled(True)
            self._source_browse_button.setEnabled(False)
            self._output_browse_button.setEnabled(False)
            self._clear_cache_button.setEnabled(False)
        else:
            self._cache_button.setEnabled(bool(self._source_dir))
            self._cache_button.setText("✅ Cached — Rebuild")
            self._cache_stop_button.setEnabled(False)
            self._source_browse_button.setEnabled(True)
            self._output_browse_button.setEnabled(True)
            self._clear_cache_button.setEnabled(True)

    def set_cache_stopped(self) -> None:
        self._cache_button.setEnabled(bool(self._source_dir))
        self._cache_button.setText("🔍 Build Cache")
        self._cache_stop_button.setEnabled(False)
        self._source_browse_button.setEnabled(True)
        self._output_browse_button.setEnabled(True)
        self._clear_cache_button.setEnabled(True)

    def set_cache_cleared(self) -> None:
        self._cache_button.setEnabled(bool(self._source_dir))
        self._cache_button.setText("🔍 Build Cache")
        self._cache_stop_button.setEnabled(False)
        self._cache_status_label.setText("❌ Cache cleared")
        self._cache_status_label.setStyleSheet(f"font-size: {Fonts.SMALL}; color: {Colors.RED}; border: none; background: transparent;")

    def set_enabled(self, enabled: bool) -> None:
        self._source_browse_button.setEnabled(enabled)
        self._output_browse_button.setEnabled(enabled)
        self._cache_button.setEnabled(enabled and bool(self._source_dir))
        self._cache_stop_button.setEnabled(False)
        self._source_input.setEnabled(enabled)
        self._output_input.setEnabled(enabled)
        self._clear_cache_button.setEnabled(enabled)

    def get_source_dir(self) -> str:
        return self._source_dir

    def get_output_dir(self) -> str:
        return self._output_dir