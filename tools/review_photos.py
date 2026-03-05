##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: review_photos.py
# Description: Standalone entry point for the image review tool. Opens a themed window with a folder selection
#              landing page, then transitions into the image review view once a folder is chosen. Can be run
#              independently without loading any ML models — only needs PySide6 for image display.
#              Intended to be packaged as a separate EXE alongside the main Photo Matcher application.
# Year: 2026
###########################################################################################################################

import sys
import traceback
from pathlib import Path

# Ensure the project root is on sys.path so project-level imports (config, ui, services) resolve
# regardless of how this script is launched — direct execution, module execution, or packaged EXE.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QStackedWidget,
)

from config import AppConfig
from ui.theme import (
    Colors,
    Fonts,
    app_stylesheet,
    btn_review_back_stylesheet,
    btn_review_skip_stylesheet,
)
from ui.widgets.image_review_dialog import ImageReviewDialog


class ReviewWindow(QMainWindow):
    """Standalone image review application window.

    Shows a landing page with a folder selection button. Once a folder is chosen, transitions to the
    image review view. Supports selecting a different folder after completing a review session.

    Layout uses a QStackedWidget to switch between:
    - Page 0: Landing page (folder selection)
    - Page 1: Image review view
    """

    def __init__(self, config: AppConfig) -> None:
        super().__init__()

        self._config = config
        self._review_widget: ImageReviewDialog | None = None

        self._setup_window()
        self._setup_ui()

    def _setup_window(self) -> None:
        """Configure the main window — title, size, background."""
        self.setWindowTitle("Image Review")
        self.resize(
            self._config.review.window_width,
            self._config.review.window_height,
        )
        self.setMinimumSize(700, 500)
        self.setStyleSheet(app_stylesheet())

    def _setup_ui(self) -> None:
        """Build the stacked layout — landing page + review placeholder."""
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background-color: {Colors.BG_APP};")
        self.setCentralWidget(self._stack)

        self._landing_page = self._build_landing_page()
        self._stack.addWidget(self._landing_page)

    def _build_landing_page(self) -> QWidget:
        """Build the folder selection landing page."""
        page = QWidget()
        page.setStyleSheet(f"background-color: {Colors.BG_APP};")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        layout.addStretch(2)

        # Icon
        icon_label = QLabel("🖼")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 64px; background: transparent;")
        layout.addWidget(icon_label)

        # Title
        title_label = QLabel("Image Review")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(
            f"font-size: 28px; font-weight: bold; color: {Colors.TEXT_PRIMARY}; background: transparent;"
        )
        layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QLabel("Review and clean up photos in any folder")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet(
            f"font-size: {Fonts.BODY}; color: {Colors.TEXT_MUTED}; background: transparent;"
        )
        layout.addWidget(subtitle_label)

        layout.addSpacing(24)

        # Select folder button — centered
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._select_button = QPushButton("📂  Select Folder")
        self._select_button.setStyleSheet(btn_review_skip_stylesheet())
        self._select_button.setMinimumHeight(48)
        self._select_button.setFixedWidth(240)
        self._select_button.setCursor(Qt.PointingHandCursor)
        self._select_button.clicked.connect(self._on_select_folder)
        btn_row.addWidget(self._select_button)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Hint
        hint_label = QLabel("Supports: JPG, PNG, BMP, TIFF, WebP")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet(
            f"font-size: {Fonts.TINY}; color: {Colors.TEXT_DIM}; background: transparent;"
        )
        layout.addWidget(hint_label)

        layout.addStretch(3)

        return page

    def _on_select_folder(self) -> None:
        """Open folder picker and transition to review view if a folder is selected."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Review",
            "",
            QFileDialog.ShowDirsOnly,
        )

        if not directory:
            return

        self._start_review(directory)

    def _start_review(self, directory: str) -> None:
        """Create the review widget and switch to it.

        Removes any previous review widget from the stack before adding the new one.

        Args:
            directory: Path to the folder to review.
        """
        # Remove previous review widget if it exists
        if self._review_widget is not None:
            self._stack.removeWidget(self._review_widget)
            self._review_widget.deleteLater()
            self._review_widget = None

        self._review_widget = ImageReviewDialog(self._config, directory, show_change_folder=True)
        self._review_widget.dialog_closed.connect(self._on_review_closed)
        self._review_widget.change_folder_requested.connect(self._on_change_folder)

        # Override the independent window behavior — reparent into our stack
        self._review_widget.setParent(self._stack)
        self._review_widget.setWindowFlags(Qt.Widget)
        self._review_widget.setAttribute(Qt.WA_DeleteOnClose, False)

        self._stack.addWidget(self._review_widget)
        self._stack.setCurrentWidget(self._review_widget)

        folder_name = Path(directory).name
        self.setWindowTitle(f"Image Review — {folder_name}")

    def _on_review_closed(self) -> None:
        """Return to the landing page when the review session ends."""
        if self._review_widget is not None:
            self._stack.removeWidget(self._review_widget)
            self._review_widget.deleteLater()
            self._review_widget = None

        self._stack.setCurrentWidget(self._landing_page)
        self.setWindowTitle("Image Review")

    def _on_change_folder(self) -> None:
        """Return to the landing page and immediately open the folder picker."""
        if self._review_widget is not None:
            self._stack.removeWidget(self._review_widget)
            self._review_widget.deleteLater()
            self._review_widget = None

        self._stack.setCurrentWidget(self._landing_page)
        self.setWindowTitle("Image Review")

        # Immediately open folder picker so the user doesn't have to click again
        self._on_select_folder()


def main() -> None:
    """Standalone entry point — themed window with folder picker → image review."""
    app = QApplication(sys.argv)

    try:
        config = AppConfig()

        window = ReviewWindow(config)
        window.show()

        sys.exit(app.exec())

    except Exception as e:
        error_msg = f"{e}\n\n{traceback.format_exc()}"
        print(f"\n[FATAL ERROR] {error_msg}", file=sys.stderr)

        QMessageBox.critical(
            None,
            "Image Review — Error",
            f"Failed to start:\n\n{e}",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()