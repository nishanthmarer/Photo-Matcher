##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: image_review_dialog.py
# Description: PySide6 image review dialog for cleaning up photo folders. Shows images one-by-one with
#              mark/save/back/restore controls. Deletions are deferred until the user confirms on close.
#              Designed for dual use: launched from the main app's ResultsPanel (non-modal, independent lifecycle)
#              or as a standalone tool via tools/review_photos.py.
# Year: 2026
###########################################################################################################################

import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QShortcut, QKeySequence, QImageReader
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QDialog,
    QSizePolicy,
)

from config import AppConfig
from services.image_reviewer import ImageReviewer
from utils.file_utils import human_readable_size
from ui.theme import (
    Colors,
    Fonts,
    review_dialog_stylesheet,
    review_info_stylesheet,
    review_status_keeping_stylesheet,
    review_status_deleted_stylesheet,
    review_stats_stylesheet,
    btn_review_back_stylesheet,
    btn_review_delete_stylesheet,
    btn_review_restore_stylesheet,
    btn_review_skip_stylesheet,
    btn_review_quit_stylesheet,
)


class StyledConfirmDialog(QDialog):
    """Custom-styled confirmation dialog matching the application's dark theme.

    Replaces QMessageBox for the deletion confirmation prompt to maintain visual consistency
    across the entire application. Returns one of three results: Yes, No, or Cancel.

    Usage:
        dialog = StyledConfirmDialog(parent, "Title", "Message", marked_count=5)
        result = dialog.exec()  # returns QDialog.Accepted, QDialog.Rejected, or 2 (cancel)
    """

    RESULT_YES = QDialog.Accepted
    RESULT_NO = QDialog.Rejected
    RESULT_CANCEL = 2

    def __init__(self, parent: QWidget, title: str, message: str, marked_count: int) -> None:
        super().__init__(parent)
        self._result = self.RESULT_CANCEL

        self.setWindowTitle(title)
        self.setFixedSize(460, 280)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_PANEL};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
            }}
        """)

        self._setup_ui(message, marked_count)

    def _setup_ui(self, message: str, marked_count: int) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Title
        title_label = QLabel(f"🗑  {marked_count} image(s) marked for deletion")
        title_label.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {Colors.TEXT_PRIMARY}; background: transparent;"
        )
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Options
        options_text = (
            f"• <b>Delete</b> — Permanently delete them<br>"
            f"• <b>Keep All</b> — Discard marks and keep all<br>"
            f"• <b>Cancel</b> — Go back to reviewing"
        )
        options_label = QLabel(options_text)
        options_label.setStyleSheet(
            f"font-size: {Fonts.BODY}; color: {Colors.TEXT_SECONDARY}; background: transparent;"
        )
        options_label.setTextFormat(Qt.RichText)
        options_label.setWordWrap(True)
        layout.addWidget(options_label)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(btn_review_quit_stylesheet())
        btn_cancel.setMinimumHeight(38)
        btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(btn_cancel, stretch=1)

        btn_keep = QPushButton("✅  Keep All")
        btn_keep.setStyleSheet(btn_review_skip_stylesheet())
        btn_keep.setMinimumHeight(38)
        btn_keep.clicked.connect(self._on_no)
        btn_row.addWidget(btn_keep, stretch=1)

        btn_delete = QPushButton("🗑  Delete")
        btn_delete.setStyleSheet(btn_review_delete_stylesheet())
        btn_delete.setMinimumHeight(38)
        btn_delete.clicked.connect(self._on_yes)
        btn_row.addWidget(btn_delete, stretch=1)

        layout.addLayout(btn_row)

    def _on_yes(self) -> None:
        self._result = self.RESULT_YES
        self.accept()

    def _on_no(self) -> None:
        self._result = self.RESULT_NO
        self.reject()

    def _on_cancel(self) -> None:
        self._result = self.RESULT_CANCEL
        self.done(self.RESULT_CANCEL)

    @property
    def result_action(self) -> int:
        """Return the user's chosen action after exec()."""
        return self._result


class StyledSummaryDialog(QDialog):
    """Custom-styled summary dialog matching the application's dark theme.

    Replaces QMessageBox.information for the final summary to maintain visual consistency.
    """

    def __init__(self, parent: QWidget, title: str, message: str) -> None:
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setFixedSize(380, 220)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_PANEL};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
            }}
        """)

        self._setup_ui(message)

    def _setup_ui(self, message: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        msg_label = QLabel(message)
        msg_label.setStyleSheet(
            f"font-size: {Fonts.BODY}; color: {Colors.TEXT_SECONDARY}; background: transparent;"
        )
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        layout.addStretch()

        btn_ok = QPushButton("OK")
        btn_ok.setStyleSheet(btn_review_back_stylesheet())
        btn_ok.setMinimumHeight(38)
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)


class ImageReviewDialog(QWidget):
    """PySide6 image review dialog for cleaning up photo folders.

    Shows images one-by-one with mark-for-deletion, save, back, and restore controls.
    Deletions are deferred — files are only marked during the session. On close, the user
    gets a 3-way confirmation: permanently delete, discard marks, or go back to reviewing.

    Lifecycle:
    - Non-modal: does not block the main application window.
    - Independent: created with no parent, survives main window closure.
    - One-at-a-time: MainWindow enforces a single active instance.

    Signals:
        dialog_closed: Emitted when the dialog is closed, so the caller can clear its reference.

    Usage (from MainWindow):
        dialog = ImageReviewDialog(config, "/output/Alice")
        dialog.dialog_closed.connect(self._on_review_closed)
        dialog.show()

    Usage (standalone):
        dialog = ImageReviewDialog(config, "/some/folder")
        dialog.show()
    """

    dialog_closed = Signal()

    # Canvas fallback size when the widget hasn't been laid out yet
    _CANVAS_MIN_WIDTH = 600
    _CANVAS_MIN_HEIGHT = 400

    # Maximum pixel dimension for loading images — prevents lag on large DSLR photos
    _MAX_LOAD_DIMENSION = 2400

    def __init__(self, config: AppConfig, directory: str) -> None:
        """Initialize the review dialog and load images from the given directory.

        Args:
            config: Application configuration (provides review window settings and image extensions).
            directory: Path to the folder to review.
        """
        super().__init__(None)

        self._config = config
        self._reviewer = ImageReviewer(config)
        self._images: list[str] = []
        self._index: int = 0
        self._current_pixmap: QPixmap | None = None
        self._close_confirmed: bool = False

        self._setup_window(config, directory)
        self._setup_ui()
        self._setup_shortcuts()
        self._load_directory(directory)

    # ------------------------------------------------------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------------------------------------------------------

    def _setup_window(self, config: AppConfig, directory: str) -> None:
        """Configure the window — title, size, background, flags."""
        folder_name = Path(directory).name
        self.setWindowTitle(f"{config.review.window_title} — {folder_name}")
        self.resize(config.review.window_width, config.review.window_height)
        self.setMinimumSize(700, 500)
        self.setStyleSheet(f"background-color: {Colors.BG_APP};")
        self.setAttribute(Qt.WA_DeleteOnClose, True)

    def _setup_ui(self) -> None:
        """Build the complete UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(0)

        layout.addLayout(self._build_info_bar())
        layout.addWidget(self._build_details_label())
        layout.addWidget(self._build_canvas(), stretch=1)
        layout.addLayout(self._build_stats_bar())
        layout.addLayout(self._build_button_bar())

    def _build_info_bar(self) -> QHBoxLayout:
        """Top row — counter label (left) + status badge (right)."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 4)

        self._counter_label = QLabel("")
        self._counter_label.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {Colors.TEXT_PRIMARY}; background: transparent;"
        )
        row.addWidget(self._counter_label)

        row.addStretch()

        self._status_label = QLabel("")
        row.addWidget(self._status_label)

        return row

    def _build_details_label(self) -> QLabel:
        """Image dimensions and file size label."""
        self._details_label = QLabel("")
        self._details_label.setStyleSheet(review_info_stylesheet())
        self._details_label.setAlignment(Qt.AlignCenter)
        self._details_label.setContentsMargins(0, 0, 0, 8)

        return self._details_label

    def _build_canvas(self) -> QLabel:
        """Central image display area — a QLabel with scaled pixmap."""
        self._canvas = QLabel()
        self._canvas.setAlignment(Qt.AlignCenter)
        self._canvas.setStyleSheet(
            f"background-color: {Colors.BG_INPUT}; border: 1px solid {Colors.BORDER}; border-radius: 8px;"
        )
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._canvas.setMinimumSize(self._CANVAS_MIN_WIDTH, self._CANVAS_MIN_HEIGHT)

        return self._canvas

    def _build_stats_bar(self) -> QHBoxLayout:
        """Bottom stats row — deletion/keeping counts (left) + directory path (right)."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 8, 0, 4)

        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(review_stats_stylesheet())
        row.addWidget(self._stats_label)

        row.addStretch()

        self._dir_label = QLabel("")
        self._dir_label.setStyleSheet(review_stats_stylesheet())
        row.addWidget(self._dir_label)

        return row

    def _build_button_bar(self) -> QHBoxLayout:
        """Action buttons — Back, Delete/Restore, Save, Quit."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 0, 0)
        row.setSpacing(8)

        self._back_button = QPushButton("◀  Back (B)")
        self._back_button.setStyleSheet(btn_review_back_stylesheet())
        self._back_button.setMinimumHeight(42)
        self._back_button.clicked.connect(self._on_back)
        row.addWidget(self._back_button, stretch=1)

        self._delete_button = QPushButton("🗑  Delete (D)")
        self._delete_button.setStyleSheet(btn_review_delete_stylesheet())
        self._delete_button.setMinimumHeight(42)
        self._delete_button.clicked.connect(self._on_delete)
        row.addWidget(self._delete_button, stretch=1)

        self._restore_button = QPushButton("♻  Restore (R)")
        self._restore_button.setStyleSheet(btn_review_restore_stylesheet())
        self._restore_button.setMinimumHeight(42)
        self._restore_button.clicked.connect(self._on_restore)
        self._restore_button.setVisible(False)
        row.addWidget(self._restore_button, stretch=1)

        self._save_button = QPushButton("💾  Save (S)")
        self._save_button.setStyleSheet(btn_review_skip_stylesheet())
        self._save_button.setMinimumHeight(42)
        self._save_button.clicked.connect(self._on_save)
        row.addWidget(self._save_button, stretch=1)

        self._quit_button = QPushButton("✖  Quit (Q)")
        self._quit_button.setStyleSheet(btn_review_quit_stylesheet())
        self._quit_button.setMinimumHeight(42)
        self._quit_button.clicked.connect(self._on_quit)
        row.addWidget(self._quit_button, stretch=1)

        return row

    def _setup_shortcuts(self) -> None:
        """Register keyboard shortcuts."""
        QShortcut(QKeySequence("D"), self).activated.connect(self._on_delete)
        QShortcut(QKeySequence("S"), self).activated.connect(self._on_save)
        QShortcut(QKeySequence("B"), self).activated.connect(self._on_back)
        QShortcut(QKeySequence("R"), self).activated.connect(self._on_restore)
        QShortcut(QKeySequence("Q"), self).activated.connect(self._on_quit)
        QShortcut(QKeySequence(Qt.Key_Right), self).activated.connect(self._on_save)
        QShortcut(QKeySequence(Qt.Key_Left), self).activated.connect(self._on_back)
        QShortcut(QKeySequence(Qt.Key_Delete), self).activated.connect(self._on_delete)
        QShortcut(QKeySequence(Qt.Key_Escape), self).activated.connect(self._on_quit)

    def _load_directory(self, directory: str) -> None:
        """Scan the directory and defer first image display until layout is complete."""
        self._images = self._reviewer.scan(directory)
        self._dir_label.setText(f"📂 {directory}")

        if not self._images:
            self._show_empty_state()
            return

        self._index = 0

        # Defer first display so the canvas has its final layout dimensions
        QTimer.singleShot(0, self._display_current)

    # ------------------------------------------------------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------------------------------------------------------

    def _display_current(self) -> None:
        """Render the current image with all UI state — counter, status, stats, buttons.

        If the index has advanced past the last image, triggers the quit/confirmation flow.
        If the user cancels and returns to reviewing, the index is reset to the last image.
        """
        if self._index >= len(self._images):
            if not self._handle_unsaved_marks():
                # User cancelled — go back to the last image
                self._index = len(self._images) - 1
                self._display_current()
                return

            self._close_confirmed = True
            self.close()
            return

        path = self._images[self._index]
        is_marked = self._reviewer.is_marked(path)

        self._update_counter(path)
        self._update_status(is_marked)
        self._update_details(path)
        self._update_canvas(path, is_marked)
        self._update_stats()
        self._update_buttons(is_marked)

    def _update_counter(self, path: str) -> None:
        """Update the counter label — [current / total] filename."""
        filename = Path(path).name
        self._counter_label.setText(f"[{self._index + 1} / {len(self._images)}]  {filename}")

    def _update_status(self, is_marked: bool) -> None:
        """Update the status badge — KEEPING or MARKED FOR DELETION."""
        if is_marked:
            self._status_label.setText("🔴  MARKED FOR DELETION")
            self._status_label.setStyleSheet(review_status_deleted_stylesheet())
        else:
            self._status_label.setText("✅  KEEPING")
            self._status_label.setStyleSheet(review_status_keeping_stylesheet())

    def _update_details(self, path: str) -> None:
        """Update dimensions and file size label."""
        try:
            stat = os.stat(path)
            size_text = human_readable_size(stat.st_size)

            reader = QImageReader(path)
            img_size = reader.size()

            if not img_size.isValid():
                self._details_label.setText(f"⚠ Could not read image dimensions  •  {size_text}")
                return

            self._details_label.setText(f"{img_size.width()} × {img_size.height()}  •  {size_text}")
        except OSError:
            self._details_label.setText("⚠ Could not read file info")

    def _update_canvas(self, path: str, is_marked: bool) -> None:
        """Load and display the image, applying a DELETED overlay if marked.

        Uses QImageReader with setScaledSize to load a pre-scaled version of the image,
        avoiding the cost of loading full-resolution DSLR photos (6000x4000+) into memory.
        """
        pixmap = self._load_scaled_pixmap(path)

        if pixmap is None or pixmap.isNull():
            self._canvas.setText("Could not load image")
            self._canvas.setStyleSheet(
                f"background-color: {Colors.BG_INPUT}; border: 1px solid {Colors.BORDER}; "
                f"border-radius: 8px; color: {Colors.RED}; font-size: 16px;"
            )
            return

        # Reset canvas style in case it was set to error state
        self._canvas.setStyleSheet(
            f"background-color: {Colors.BG_INPUT}; border: 1px solid {Colors.BORDER}; border-radius: 8px;"
        )

        if is_marked:
            pixmap = self._apply_deleted_overlay(pixmap)

        canvas_width = max(self._canvas.width(), self._CANVAS_MIN_WIDTH)
        canvas_height = max(self._canvas.height(), self._CANVAS_MIN_HEIGHT)

        scaled = pixmap.scaled(
            canvas_width - 4, canvas_height - 4,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self._current_pixmap = scaled
        self._canvas.setPixmap(scaled)

    def _load_scaled_pixmap(self, path: str) -> QPixmap | None:
        """Load an image from disk, pre-scaling large images to a reasonable size.

        Uses QImageReader to instruct the decoder to load at a reduced resolution. This avoids
        allocating a full 6000x4000 pixel buffer in memory, dramatically reducing load time and
        memory usage for DSLR photos.

        Args:
            path: Path to the image file.

        Returns:
            A QPixmap scaled to at most _MAX_LOAD_DIMENSION on its longest side, or None on failure.
        """
        reader = QImageReader(path)
        reader.setAutoTransform(True)

        original_size = reader.size()

        if not original_size.isValid():
            return None

        max_dim = self._MAX_LOAD_DIMENSION

        if original_size.width() > max_dim or original_size.height() > max_dim:
            scaled_size = original_size.scaled(
                QSize(max_dim, max_dim),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
            reader.setScaledSize(scaled_size)

        image = reader.read()

        if image.isNull():
            return None

        return QPixmap.fromImage(image)

    def _apply_deleted_overlay(self, pixmap: QPixmap) -> QPixmap:
        """Draw a semi-transparent red wash and DELETED text over the pixmap."""
        overlay = QPixmap(pixmap.size())
        overlay.fill(Qt.transparent)

        painter = QPainter(overlay)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw the original image
        painter.drawPixmap(0, 0, pixmap)

        # Semi-transparent red wash
        painter.fillRect(overlay.rect(), QColor(220, 38, 38, 80))

        # DELETED text
        font_size = max(pixmap.width(), pixmap.height()) // 10
        font = QFont("Segoe UI", max(font_size, 24), QFont.Bold)
        painter.setFont(font)

        text = "DELETED"
        text_rect = painter.fontMetrics().boundingRect(text)
        x = (pixmap.width() - text_rect.width()) // 2
        y = (pixmap.height() + text_rect.height()) // 2

        # Shadow
        painter.setPen(QColor(0, 0, 0, 160))
        painter.drawText(x + 3, y + 3, text)

        # Main text
        painter.setPen(QColor(220, 38, 38, 200))
        painter.drawText(x, y, text)

        painter.end()

        return overlay

    def _update_stats(self) -> None:
        """Update the stats bar — marked/keeping counts."""
        self._stats_label.setText(
            f"🗑 {self._reviewer.marked_count} marked for deletion   •   "
            f"✅ {self._reviewer.keeping_count} keeping"
        )

    def _update_buttons(self, is_marked: bool) -> None:
        """Toggle Delete/Restore visibility and update Back button state."""
        self._delete_button.setVisible(not is_marked)
        self._restore_button.setVisible(is_marked)
        self._back_button.setEnabled(self._index > 0)

    def _show_empty_state(self) -> None:
        """Display when the directory has no valid images."""
        self._counter_label.setText("No images found")
        self._status_label.setText("")
        self._details_label.setText("")
        self._stats_label.setText("")
        self._canvas.setText("No valid images in this folder")
        self._canvas.setStyleSheet(
            f"background-color: {Colors.BG_INPUT}; border: 1px solid {Colors.BORDER}; "
            f"border-radius: 8px; color: {Colors.TEXT_DIM}; font-size: 14px;"
        )
        self._back_button.setEnabled(False)
        self._delete_button.setEnabled(False)
        self._save_button.setEnabled(False)
        self._restore_button.setVisible(False)

    # ------------------------------------------------------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------------------------------------------------------

    def _on_delete(self) -> None:
        """Mark current image for deletion and advance to the next."""
        if self._index >= len(self._images):
            return

        self._reviewer.mark_for_deletion(self._images[self._index])
        self._index += 1
        self._display_current()

    def _on_save(self) -> None:
        """Save (keep) current image and advance to the next."""
        if self._index >= len(self._images):
            return

        self._index += 1
        self._display_current()

    def _on_back(self) -> None:
        """Go back to the previous image."""
        if self._index > 0:
            self._index -= 1
            self._display_current()

    def _on_restore(self) -> None:
        """Remove deletion mark from the current image."""
        if self._index >= len(self._images):
            return

        path = self._images[self._index]

        if self._reviewer.is_marked(path):
            self._reviewer.restore(path)
            self._display_current()

    def _on_quit(self) -> None:
        """Handle quit — show confirmation if there are marks, then close."""
        if self._handle_unsaved_marks():
            self._close_confirmed = True
            self.close()

    def _handle_unsaved_marks(self) -> bool:
        """Prompt the user to confirm or discard pending deletion marks.

        Returns:
            True if the dialog should close (user confirmed or discarded).
            False if the user chose to cancel and continue reviewing.
        """
        marked = self._reviewer.marked_count

        if marked == 0:
            self._show_summary(deleted_count=0)
            return True

        confirm = StyledConfirmDialog(
            self,
            "Confirm Deletion",
            "Review your marked images before proceeding.",
            marked_count=marked,
        )
        confirm.exec()

        result = confirm.result_action

        if result == StyledConfirmDialog.RESULT_CANCEL:
            return False

        if result == StyledConfirmDialog.RESULT_YES:
            summary = self._reviewer.execute_deletions()
            self._show_summary(
                deleted_count=summary["deleted"],
                errors=summary["errors"],
            )
            return True

        # No — discard marks
        self._reviewer.discard_all_marks()
        self._show_summary(deleted_count=0)
        return True

    def _show_summary(self, deleted_count: int, errors: list[str] = None) -> None:
        """Show a styled summary dialog.

        Args:
            deleted_count: Number of files actually deleted.
            errors: Optional list of error messages from failed deletions.
        """
        total = self._reviewer.total_count

        if deleted_count > 0:
            kept = total - deleted_count
            msg = (
                f"✅ Done!\n\n"
                f"  Total images:   {total}\n"
                f"  Deleted:          {deleted_count}\n"
                f"  Kept:              {kept}"
            )
            if errors:
                msg += f"\n\n⚠ Errors ({len(errors)}):\n" + "\n".join(errors)
        else:
            msg = f"No files were deleted.\nAll {total} images kept."

        summary_dialog = StyledSummaryDialog(self, "Summary", msg)
        summary_dialog.exec()

    # ------------------------------------------------------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        """Handle window close — confirm unsaved marks before closing.

        Triggered by both the Quit button (via self.close()) and the window X button.
        If called from _on_quit, _close_confirmed is already True and we skip re-prompting.
        If called from the X button, we run the confirmation flow first.
        """
        if not self._close_confirmed:
            if self._reviewer.marked_count > 0:
                should_close = self._handle_unsaved_marks()
                if not should_close:
                    event.ignore()
                    return
            elif self._reviewer.total_count > 0:
                self._show_summary(deleted_count=0)

        self._reviewer.reset()
        self.dialog_closed.emit()
        super().closeEvent(event)