##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: review_photos.py
# Description: Standalone entry point for the image review tool. Launches a PySide6 folder picker, then opens the
#              same ImageReviewDialog used by the main Photo Matcher application. Can be run independently without
#              loading any ML models — only needs PySide6 and Pillow-free image display via Qt.
#              Intended to be packaged as a separate EXE alongside the main application.
# Year: 2026
###########################################################################################################################

import sys
import traceback

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from config import AppConfig
from ui.theme import app_stylesheet
from ui.widgets.image_review_dialog import ImageReviewDialog


def select_folder(app: QApplication) -> str:
    """Show a folder selection dialog and return the chosen path.

    Args:
        app: QApplication instance (must exist before any QWidget is created).

    Returns:
        Selected directory path, or empty string if the user cancelled.
    """
    directory = QFileDialog.getExistingDirectory(
        None,
        "Select Folder to Review",
        "",
        QFileDialog.ShowDirsOnly,
    )

    return directory


def main() -> None:
    """Standalone entry point — folder picker → image review dialog."""
    app = QApplication(sys.argv)
    app.setStyleSheet(app_stylesheet())

    try:
        config = AppConfig()

        directory = select_folder(app)

        if not directory:
            sys.exit(0)

        dialog = ImageReviewDialog(config, directory)
        dialog.show()

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