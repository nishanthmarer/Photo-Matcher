##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: reference_panel.py
# Description: Panel for adding/managing reference faces and triggering folder generation. Contains the Generate
#              Folders + Stop buttons, Clear All button, and a scrollable list of enrolled persons with thumbnails.
# Year: 2026
###########################################################################################################################

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QFileDialog,
    QScrollArea,
    QFrame,
    QSizePolicy,
)

from ui.theme import (
    Colors, Fonts, PANEL_CARD_STYLE, header_stylesheet, hint_stylesheet,
    btn_primary_stylesheet, btn_green_stylesheet, btn_secondary_stylesheet,
    btn_stop_stylesheet, btn_remove_stylesheet, btn_clear_stylesheet,
    person_entry_stylesheet,
)


class ReferencePanel(QFrame):
    """Panel for adding/managing reference faces and generating output folders."""

    person_added = Signal(str, list)
    person_removed = Signal(str)
    generate_requested = Signal()
    generate_stop_requested = Signal()
    clear_all_requested = Signal()

    IMAGE_FILTER = "Images (*.jpg *.jpeg *.png *.bmp *.tiff *.webp)"
    THUMBNAIL_SIZE = 34

    # How long (ms) the "✅ Generated" label stays before reverting to "📂 Generate Folders"
    _GENERATE_SUCCESS_DISPLAY_MS = 5000

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self._selected_paths: list[str] = []
        self._person_widgets: dict[str, QWidget] = {}
        self._cache_is_built = False

        # Timer for reverting generate button text after success
        self._generate_revert_timer = QTimer(self)
        self._generate_revert_timer.setSingleShot(True)
        self._generate_revert_timer.timeout.connect(self._revert_generate_button_text)

        self.setStyleSheet(f"ReferencePanel {{ {PANEL_CARD_STYLE} }}")
        self._setup_ui()
        self._connect_signals()
        self._update_add_button_state()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        # Header with Clear All button
        header_row = QHBoxLayout()
        header = QLabel("👤 Reference Faces")
        header.setStyleSheet(header_stylesheet())
        header_row.addWidget(header)
        header_row.addStretch()
        self._clear_all_button = QPushButton("🗑 Clear All")
        self._clear_all_button.setStyleSheet(btn_clear_stylesheet())
        self._clear_all_button.setFixedHeight(24)
        header_row.addWidget(self._clear_all_button)
        layout.addLayout(header_row)

        # Name input
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Person name")
        layout.addWidget(self._name_input)

        # Browse + count + Add
        photo_row = QHBoxLayout()
        self._browse_button = QPushButton("📷 Browse Photos")
        self._browse_button.setStyleSheet(btn_secondary_stylesheet())
        self._browse_button.setMinimumHeight(36)
        photo_row.addWidget(self._browse_button, stretch=1)

        self._photo_count_label = QLabel("No photos selected")
        self._photo_count_label.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_DIM};")
        photo_row.addWidget(self._photo_count_label)

        self._add_button = QPushButton("+ Add")
        self._add_button.setStyleSheet(btn_primary_stylesheet())
        self._add_button.setEnabled(False)
        self._add_button.setMinimumHeight(36)
        photo_row.addWidget(self._add_button)
        layout.addLayout(photo_row)

        # Scrollable person list
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setSpacing(5)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self._list_widget)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(scroll_area, stretch=1)

        # Separator line + Generate Folders + Stop
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {Colors.SEPARATOR}; border: none;")
        layout.addWidget(separator)

        gen_section = QWidget()
        gen_section.setStyleSheet("background: transparent; border: none;")
        gen_layout = QVBoxLayout(gen_section)
        gen_layout.setContentsMargins(0, 6, 0, 0)
        gen_layout.setSpacing(4)

        btn_row = QHBoxLayout()
        self._generate_button = QPushButton("📂 Generate Folders")
        self._generate_button.setStyleSheet(btn_green_stylesheet())
        self._generate_button.setEnabled(False)
        self._generate_button.setMinimumHeight(38)
        btn_row.addWidget(self._generate_button)

        self._generate_stop_button = QPushButton("⏹")
        self._generate_stop_button.setStyleSheet(btn_stop_stylesheet())
        self._generate_stop_button.setEnabled(False)
        self._generate_stop_button.setFixedSize(42, 38)
        btn_row.addWidget(self._generate_stop_button)
        gen_layout.addLayout(btn_row)

        self._generate_hint = QLabel("Status: Build cache first")
        self._generate_hint.setStyleSheet(f"font-size: {Fonts.SMALL}; color: {Colors.TEXT_DIM}; border: none; background: transparent;")
        gen_layout.addWidget(self._generate_hint)

        layout.addWidget(gen_section)

    def _connect_signals(self) -> None:
        self._browse_button.clicked.connect(self._on_browse_clicked)
        self._add_button.clicked.connect(self._on_add_clicked)
        self._name_input.textChanged.connect(self._update_add_button_state)
        self._generate_button.clicked.connect(self._on_generate_clicked)
        self._generate_stop_button.clicked.connect(self._on_generate_stop_clicked)
        self._clear_all_button.clicked.connect(self._on_clear_all_clicked)

    def _on_browse_clicked(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Reference Photos", "", self.IMAGE_FILTER)
        if paths:
            self._selected_paths = paths
            self._photo_count_label.setText(f"{len(paths)} photo(s) selected")
            self._update_add_button_state()

    def _on_add_clicked(self) -> None:
        person_name = self._name_input.text().strip()
        if not person_name or not self._selected_paths:
            return
        if person_name in self._person_widgets:
            return

        self.person_added.emit(person_name, self._selected_paths.copy())
        self._add_person_to_list(person_name, self._selected_paths)

        self._name_input.clear()
        self._selected_paths.clear()
        self._photo_count_label.setText("No photos selected")
        self._update_add_button_state()
        self._update_generate_button_state()

    def _on_remove_clicked(self, person_name: str) -> None:
        if person_name in self._person_widgets:
            widget = self._person_widgets.pop(person_name)
            self._list_layout.removeWidget(widget)
            widget.deleteLater()
            self.person_removed.emit(person_name)
            self._update_generate_button_state()

    def _on_generate_clicked(self) -> None:
        # Stop any pending revert timer if the user re-clicks while "✅ Generated" is showing
        self._generate_revert_timer.stop()
        self.generate_requested.emit()

    def _on_generate_stop_clicked(self) -> None:
        self._generate_stop_button.setEnabled(False)
        self.generate_stop_requested.emit()

    def _on_clear_all_clicked(self) -> None:
        for name in list(self._person_widgets.keys()):
            self._on_remove_clicked(name)
        self.clear_all_requested.emit()

    def _add_person_to_list(self, name: str, photo_paths: list[str]) -> None:
        entry = QFrame()
        entry.setStyleSheet(person_entry_stylesheet())
        entry_layout = QHBoxLayout(entry)
        entry_layout.setContentsMargins(8, 6, 8, 6)

        thumbnail = self._create_thumbnail(photo_paths[0])
        entry_layout.addWidget(thumbnail)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        name_label = QLabel(name)
        name_label.setStyleSheet(
            f"font-weight: bold; font-size: 12px; color: {Colors.TEXT_PRIMARY}; "
            f"border: none; background: transparent;"
        )
        count_label = QLabel(f"{len(photo_paths)} reference(s)")
        count_label.setStyleSheet(
            f"font-size: 10px; color: {Colors.TEXT_DIM}; "
            f"border: none; background: transparent;"
        )
        info_layout.addWidget(name_label)
        info_layout.addWidget(count_label)
        entry_layout.addLayout(info_layout)

        entry_layout.addStretch()

        remove_button = QPushButton("✕")
        remove_button.setStyleSheet(btn_remove_stylesheet())
        remove_button.setFixedSize(28, 28)
        remove_button.clicked.connect(lambda: self._on_remove_clicked(name))
        entry_layout.addWidget(remove_button)

        insert_position = self._list_layout.count() - 1
        self._list_layout.insertWidget(insert_position, entry)
        self._person_widgets[name] = entry

    def _create_thumbnail(self, image_path: str) -> QLabel:
        label = QLabel()
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE,
                aspectMode=Qt.AspectRatioMode.KeepAspectRatio,
                mode=Qt.TransformationMode.SmoothTransformation,
            )
        label.setPixmap(pixmap)
        label.setFixedSize(self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE)
        return label

    def _update_add_button_state(self) -> None:
        has_name = bool(self._name_input.text().strip())
        has_photos = bool(self._selected_paths)
        self._add_button.setEnabled(has_name and has_photos)

    def _update_generate_button_state(self) -> None:
        has_persons = len(self._person_widgets) > 0
        self._generate_button.setEnabled(self._cache_is_built and has_persons)
        if not self._cache_is_built:
            self._generate_hint.setText("Status: Build cache first")
        elif not has_persons:
            self._generate_hint.setText("Status: Add at least one person")
        else:
            self._generate_hint.setText("Status: Ready to generate")

    def _revert_generate_button_text(self) -> None:
        """Revert the generate button back to its default text after the success display period."""
        self._generate_button.setText("📂 Generate Folders")
        self._update_generate_button_state()

    # ------------------------------------------------------------------------------------------------------------------
    # Public methods — called by MainWindow
    # ------------------------------------------------------------------------------------------------------------------

    def set_cache_built(self, built: bool) -> None:
        self._cache_is_built = built
        self._update_generate_button_state()

    def set_generate_running(self, running: bool) -> None:
        if running:
            self._generate_revert_timer.stop()
            self._generate_button.setEnabled(False)
            self._generate_button.setText("📂 Generating...")
            self._generate_stop_button.setEnabled(True)
            self._generate_hint.setText("")
            self._add_button.setEnabled(False)
            self._browse_button.setEnabled(False)
            self._name_input.setEnabled(False)
            self._clear_all_button.setEnabled(False)
        else:
            self._generate_button.setText("📂 Generate Folders")
            self._generate_stop_button.setEnabled(False)
            self._add_button.setEnabled(True)
            self._browse_button.setEnabled(True)
            self._name_input.setEnabled(True)
            self._clear_all_button.setEnabled(True)
            self._update_add_button_state()
            self._update_generate_button_state()

    def set_generate_complete(self) -> None:
        """Show a temporary success label on the generate button, then revert after 5 seconds."""
        self._generate_button.setText("✅ Generated")
        self._update_generate_button_state()
        self._generate_revert_timer.start(self._GENERATE_SUCCESS_DISPLAY_MS)

    def set_enabled(self, enabled: bool) -> None:
        self._name_input.setEnabled(enabled)
        self._browse_button.setEnabled(enabled)
        self._clear_all_button.setEnabled(enabled)
        self._add_button.setEnabled(False)
        self._generate_button.setEnabled(False)
        self._generate_stop_button.setEnabled(False)

    def get_person_count(self) -> int:
        return len(self._person_widgets)