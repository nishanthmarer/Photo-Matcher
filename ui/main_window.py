##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: main_window.py
# Description: Main application window — coordinates all UI panels and connects them to the services layer. Shows
#              immediately on launch with panels disabled, loads ML models in background via StartupWorker, then
#              enables controls. Manages two independent operations: Build Cache and Generate Folders. Supports
#              launching a non-modal, independent image review dialog for per-person folder cleanup.
# Year: 2026
###########################################################################################################################

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QSplitter,
    QMessageBox,
)

from config import AppConfig
from ui.theme import app_stylesheet, Colors
from ui.widgets.reference_panel import ReferencePanel
from ui.widgets.photo_pool_panel import PhotoPoolPanel
from ui.widgets.progress_panel import ProgressPanel
from ui.widgets.results_panel import ResultsPanel
from ui.widgets.status_bar import StatusBar
from ui.widgets.image_review_dialog import ImageReviewDialog
from ui.workers.startup_worker import StartupWorker
from ui.workers.cache_worker import CacheWorker
from ui.workers.generate_worker import GenerateWorker


class MainWindow(QMainWindow):
    """Main application window — coordinates all UI panels.

    Layout:
        Left: ReferencePanel (persons + Generate Folders) / PhotoPoolPanel (folders + Build Cache)
        Right: ProgressPanel (progress bar + log) / ResultsPanel (per-person counts)
        Bottom: StatusBar (pulsing dot + status message + phase + device indicator)
    """

    def __init__(self) -> None:
        super().__init__()

        self._config = AppConfig()
        self._segregator = None
        self._cache_worker = None
        self._generate_worker = None
        self._review_dialog = None
        self._source_dir = ""
        self._output_dir = ""
        self._cache_is_built = False

        self._setup_ui()
        self._connect_signals()
        self._disable_all_panels()
        self._start_model_loading()

    def _setup_ui(self) -> None:
        self.setWindowTitle(self._config.ui.window_title)
        self.resize(self._config.ui.window_width, self._config.ui.window_height)
        self.setStyleSheet(app_stylesheet())

        central_widget = QWidget()
        central_widget.setStyleSheet(f"background-color: {Colors.BG_APP};")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {Colors.BG_APP};
                width: 8px;
            }}
        """)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(10)
        self._reference_panel = ReferencePanel()
        self._photo_pool_panel = PhotoPoolPanel(self._config)
        left_layout.addWidget(self._reference_panel, stretch=1)
        left_layout.addWidget(self._photo_pool_panel, stretch=1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(10)
        self._progress_panel = ProgressPanel()
        self._results_panel = ResultsPanel()
        right_layout.addWidget(self._progress_panel, stretch=2)
        right_layout.addWidget(self._results_panel, stretch=1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([380, 620])

        main_layout.addWidget(splitter, stretch=1)

        self._status_bar = StatusBar()
        main_layout.addWidget(self._status_bar)

    def _connect_signals(self) -> None:
        self._reference_panel.person_added.connect(self._on_person_added)
        self._reference_panel.person_removed.connect(self._on_person_removed)
        self._reference_panel.generate_requested.connect(self._on_generate_requested)
        self._reference_panel.generate_stop_requested.connect(self._on_generate_stop)
        self._reference_panel.clear_all_requested.connect(self._on_clear_all_persons)

        self._photo_pool_panel.source_selected.connect(self._on_source_selected)
        self._photo_pool_panel.output_selected.connect(self._on_output_selected)
        self._photo_pool_panel.cache_requested.connect(self._on_cache_requested)
        self._photo_pool_panel.cache_stop_requested.connect(self._on_cache_stop)
        self._photo_pool_panel.clear_cache_requested.connect(self._on_clear_cache)

        self._results_panel.review_requested.connect(self._on_review_requested)

    # ------------------------------------------------------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------------------------------------------------------

    def _start_model_loading(self) -> None:
        self._startup_worker = StartupWorker(self._config)
        self._startup_worker.status_updated.connect(self._status_bar.on_status_updated)
        self._startup_worker.startup_complete.connect(self._on_startup_complete)
        self._startup_worker.startup_failed.connect(self._on_startup_failed)
        self._startup_worker.start()

    def _on_startup_complete(self, segregator) -> None:
        self._segregator = segregator
        self._enable_all_panels()
        self._startup_worker = None

        # Detect and display GPU/CPU status in the status bar
        try:
            import onnxruntime as ort
            available_providers = ort.get_available_providers()
            if "CUDAExecutionProvider" in available_providers:
                self._status_bar.set_device("GPU")
            else:
                self._status_bar.set_device("CPU")
        except Exception:
            self._status_bar.set_device("CPU")

    def _on_startup_failed(self, error_message: str) -> None:
        self._startup_worker = None
        self._status_bar.set_device("CPU")
        QMessageBox.critical(self, "Startup Error", f"Failed to load ML models:\n\n{error_message}")

    # ------------------------------------------------------------------------------------------------------------------
    # Person management
    # ------------------------------------------------------------------------------------------------------------------

    def _on_person_added(self, name: str, image_paths: list[str]) -> None:
        if self._segregator is None:
            return
        count = self._segregator.add_references(name, image_paths)
        if count == 0:
            QMessageBox.warning(self, "Enrollment Failed",
                                f"No faces detected in the reference photos for '{name}'.")

    def _on_person_removed(self, name: str) -> None:
        if self._segregator:
            self._segregator.remove_reference(name)

    def _on_clear_all_persons(self) -> None:
        if self._segregator:
            for name in self._segregator._reference_manager.get_all_persons().copy():
                self._segregator.remove_reference(name)

    def _on_source_selected(self, directory: str) -> None:
        self._source_dir = directory
        self._check_cache_for_source(directory)

    def _on_output_selected(self, directory: str) -> None:
        self._output_dir = directory

    # ------------------------------------------------------------------------------------------------------------------
    # Cache validation
    # ------------------------------------------------------------------------------------------------------------------

    def _check_cache_for_source(self, source_dir: str) -> None:
        if self._segregator is None:
            return

        if self._segregator.has_cache_for_source(source_dir):
            count = self._segregator.get_cache_size()
            self._photo_pool_panel.set_cache_status(found=True, count=count)
            self._cache_is_built = True
            self._reference_panel.set_cache_built(True)
            self._photo_pool_panel.set_cache_running(False)
            self._status_bar.on_status_updated(f"Cache found — {count:,} photos cached", "ready")
        else:
            self._photo_pool_panel.set_cache_status(found=False)
            self._cache_is_built = False
            self._reference_panel.set_cache_built(False)

    # ------------------------------------------------------------------------------------------------------------------
    # Build Cache
    # ------------------------------------------------------------------------------------------------------------------

    def _on_cache_requested(self) -> None:
        if self._segregator is None or not self._source_dir or not self._output_dir:
            QMessageBox.warning(self, "Missing Input", "Please select source and output folders.")
            return

        self._progress_panel.reset_all()
        self._progress_panel.write_log("═══ BUILD CACHE ═══", Colors.BLUE)
        self._progress_panel.write_log("")
        self._photo_pool_panel.set_cache_running(True)
        self._reference_panel.set_cache_built(False)
        self._cache_is_built = False

        self._cache_worker = CacheWorker(
            segregator=self._segregator,
            source_dir=self._source_dir,
            output_dir=self._output_dir,
        )
        self._cache_worker.progress_updated.connect(self._on_cache_progress)
        self._cache_worker.status_updated.connect(self._status_bar.on_status_updated)
        self._cache_worker.cache_complete.connect(self._on_cache_complete)
        self._cache_worker.error_occurred.connect(self._on_cache_error)
        self._cache_worker.start()

    def _on_cache_stop(self) -> None:
        if self._cache_worker:
            self._cache_worker.request_stop()

    def _on_cache_progress(self, current: int, total: int, filename: str) -> None:
        short_name = Path(filename).name
        self._progress_panel.update_bar(current, total, f"Processing {current:,} / {total:,} — {short_name}")
        self._progress_panel.write_log(f"[{current}/{total}] {short_name}")

    def _on_cache_complete(self, summary: dict) -> None:
        self._progress_panel.set_bar_value(100)
        self._progress_panel.set_stats_text("")

        if summary.get("stopped_early"):
            processed = summary.get("actually_processed", 0)
            self._progress_panel.write_log("")
            self._progress_panel.write_log(f"⏹ Cache stopped — {processed:,} photos saved", Colors.YELLOW)
            self._photo_pool_panel.set_cache_stopped()
            self._status_bar.on_status_updated(
                f"Cache stopped — {processed:,} photos saved", "stopped")
            self._check_cache_for_source(self._source_dir)
        else:
            total = summary.get("total_scanned", 0)
            new = summary.get("new_processed", 0)
            cached = summary.get("cached_skipped", 0)
            self._progress_panel.write_log("")
            if new == 0:
                self._progress_panel.write_log(
                    f"✅ All {total:,} photos already cached — nothing to process", Colors.GREEN)
            else:
                self._progress_panel.write_log(
                    f"✅ Cache complete — {new:,} processed, {cached:,} already cached ({total:,} total)",
                    Colors.GREEN)
            self._photo_pool_panel.set_cache_running(False)
            self._cache_is_built = True
            self._reference_panel.set_cache_built(True)
            count = self._segregator.get_cache_size()
            self._photo_pool_panel.set_cache_status(found=True, count=count)
            self._status_bar.on_status_updated(f"Cache complete — {count:,} photos cached", "ready")
        self._cache_worker = None

    def _on_cache_error(self, error_message: str) -> None:
        self._photo_pool_panel.set_cache_running(False)
        self._progress_panel.write_log(f"❌ ERROR: {error_message}", Colors.RED)
        self._status_bar.on_status_updated(f"Cache error: {error_message}", "error")
        self._cache_worker = None
        QMessageBox.critical(self, "Cache Error",
                             f"An error occurred during cache building:\n\n{error_message}")

    # ------------------------------------------------------------------------------------------------------------------
    # Generate Folders
    # ------------------------------------------------------------------------------------------------------------------

    def _on_generate_requested(self) -> None:
        if self._segregator is None:
            return
        if not self._cache_is_built:
            QMessageBox.warning(self, "Cache Required", "Please build the cache first.")
            return
        if not self._source_dir or not self._output_dir:
            QMessageBox.warning(self, "Missing Input", "Please select source and output folders.")
            return
        if self._reference_panel.get_person_count() == 0:
            QMessageBox.warning(self, "No References", "Please add at least one person.")
            return

        self._results_panel.reset()
        self._progress_panel.reset_all()
        self._progress_panel.write_log("═══ GENERATE FOLDERS ═══", Colors.PURPLE)
        self._progress_panel.write_log("")
        self._reference_panel.set_generate_running(True)

        self._generate_worker = GenerateWorker(
            segregator=self._segregator,
            source_dir=self._source_dir,
            output_dir=self._output_dir,
        )
        self._generate_worker.status_updated.connect(self._status_bar.on_status_updated)
        self._generate_worker.progress_updated.connect(self._on_match_progress)
        self._generate_worker.copy_progress.connect(self._on_copy_progress)
        self._generate_worker.generate_complete.connect(self._on_generate_complete)
        self._generate_worker.error_occurred.connect(self._on_generate_error)
        self._generate_worker.start()

    def _on_generate_stop(self) -> None:
        if self._generate_worker:
            self._generate_worker.request_stop()

    def _on_match_progress(self, current: int, total: int, filename: str) -> None:
        if current == 1:
            self._progress_panel.write_log(f"Matching against {total:,} cached photos...")
        self._progress_panel.update_bar(
            current, total, f"Matching {current:,} / {total:,} cached photos...")

    def _on_copy_progress(self, current: int, total: int, filename: str) -> None:
        if current == 1:
            self._progress_panel.write_log("")
            self._progress_panel.write_log(f"Copying {total:,} matched photos...")
        short_name = Path(filename).name
        self._progress_panel.update_bar(
            current, total, f"Copying {current:,} / {total:,} — {short_name}")
        self._progress_panel.write_log(f"  📂 [{current}/{total}] {short_name}")

    def _on_generate_complete(self, summary: dict) -> None:
        self._reference_panel.set_generate_running(False)

        if summary.get("stopped"):
            self._progress_panel.write_log("⏹ Folder generation stopped", Colors.YELLOW)
            self._status_bar.on_status_updated("Folder generation stopped", "stopped")
        elif "error" in summary:
            self._progress_panel.write_log(f"❌ Error: {summary['error']}", Colors.RED)
            self._status_bar.on_status_updated(f"Generate error: {summary['error']}", "error")
        else:
            total_copied = sum(v for v in summary.values() if isinstance(v, int))

            self._progress_panel.write_log("")
            for name, count in summary.items():
                if isinstance(count, int) and count > 0:
                    self._progress_panel.write_log(f"  📂 {name}: {count:,} photos copied")

            if total_copied == 0:
                self._progress_panel.write_log(
                    "✅ All up to date — no new photos to copy", Colors.GREEN)
                self._status_bar.on_status_updated(
                    "All up to date — no new photos to copy", "done")
            else:
                self._progress_panel.write_log(
                    f"✅ Complete — {total_copied:,} photos copied", Colors.GREEN)
                self._status_bar.on_status_updated(
                    f"Complete — {total_copied:,} photos copied", "done")

            self._reference_panel.set_generate_complete()
            self._results_panel.display_results(summary, self._output_dir)

        self._progress_panel.set_bar_value(100)
        self._progress_panel.set_stats_text("")
        self._generate_worker = None

    def _on_generate_error(self, error_message: str) -> None:
        self._reference_panel.set_generate_running(False)
        self._progress_panel.write_log(f"❌ ERROR: {error_message}", Colors.RED)
        self._status_bar.on_status_updated(f"Generate error: {error_message}", "error")
        self._generate_worker = None
        QMessageBox.critical(self, "Generate Error",
                             f"An error occurred during folder generation:\n\n{error_message}")

    # ------------------------------------------------------------------------------------------------------------------
    # Image Review
    # ------------------------------------------------------------------------------------------------------------------

    def _on_review_requested(self, folder_path: str) -> None:
        """Launch the image review dialog for a person's output folder.

        Enforces one-at-a-time — if a review dialog is already open, it is focused instead of opening a new one.

        Args:
            folder_path: Path to the person's output folder to review.
        """
        if self._review_dialog is not None:
            self._review_dialog.activateWindow()
            self._review_dialog.raise_()
            return

        self._review_dialog = ImageReviewDialog(self._config, folder_path)
        self._review_dialog.dialog_closed.connect(self._on_review_closed)
        self._review_dialog.show()

    def _on_review_closed(self) -> None:
        """Clear the review dialog reference when it is closed."""
        self._review_dialog = None

    # ------------------------------------------------------------------------------------------------------------------
    # Clear actions
    # ------------------------------------------------------------------------------------------------------------------

    def _on_clear_cache(self) -> None:
        if self._segregator:
            self._segregator.clear_cache()
            self._cache_is_built = False
            self._reference_panel.set_cache_built(False)
            self._photo_pool_panel.set_cache_cleared()
            self._status_bar.on_status_updated("Cache cleared", "ready")

    # ------------------------------------------------------------------------------------------------------------------
    # Panel enable/disable
    # ------------------------------------------------------------------------------------------------------------------

    def _disable_all_panels(self) -> None:
        self._reference_panel.set_enabled(False)
        self._photo_pool_panel.set_enabled(False)

    def _enable_all_panels(self) -> None:
        self._reference_panel.set_enabled(True)
        self._photo_pool_panel.set_enabled(True)