##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: cache_worker.py
# Description: Background thread worker for building the embedding cache. Runs the Segregator's process_photos()
#              off the UI thread to keep the interface responsive. Emits progress signals for the progress panel,
#              status signals for the status bar, and a completion signal with the summary. Supports graceful
#              stopping via request_stop().
# Year: 2026
###########################################################################################################################

from PySide6.QtCore import QThread, Signal

from services.segregator import Segregator


class CacheWorker(QThread):
    """Runs photo processing (Build Cache) in a background thread.

    Calls segregator.process_photos() which scans the source folder, checks cache staleness, and runs
    new/stale photos through the ML pipeline (detect → align → embed). Results are saved to disk cache.

    Communicates with the UI via Qt signals:
    - progress_updated(current, total, filename): for the progress panel bar and log
    - status_updated(message, phase): for the status bar at the bottom
    - cache_complete(summary): when processing finishes (or is stopped)
    - error_occurred(message): if an unhandled exception occurs

    Usage (from MainWindow):
        worker = CacheWorker(segregator, source_dir, output_dir)
        worker.progress_updated.connect(progress_panel.on_progress_updated)
        worker.status_updated.connect(status_bar.on_status_updated)
        worker.cache_complete.connect(self._on_cache_complete)
        worker.start()
    """

    progress_updated = Signal(int, int, str)
    status_updated = Signal(str, str)
    cache_complete = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, segregator: Segregator, source_dir: str, output_dir: str) -> None:
        """Initialize the worker with processing parameters.

        Args:
            segregator: Segregator instance with models loaded.
            source_dir: Path to the source photo directory.
            output_dir: Path to the output directory (excluded from scanning).
        """
        super().__init__()
        self._segregator = segregator
        self._source_dir = source_dir
        self._output_dir = output_dir

    def run(self) -> None:
        """Execute photo processing in the background thread."""
        try:
            self._segregator.reset_cache_stop()

            summary = self._segregator.process_photos(
                source_dir=self._source_dir,
                progress_callback=self._on_progress,
                status_callback=self._on_status,
                exclude_dirs=[self._output_dir],
            )

            self.cache_complete.emit(summary)

        except Exception as e:
            self.status_updated.emit(f"Cache error: {e}", "error")
            self.error_occurred.emit(str(e))

    def request_stop(self) -> None:
        """Request the segregator to stop cache building gracefully. Thread-safe."""
        self._segregator.request_cache_stop()

    def _on_progress(self, current: int, total: int, filename: str) -> None:
        """Progress callback — marshals to UI thread via signal."""
        self.progress_updated.emit(current, total, filename)

    def _on_status(self, message: str) -> None:
        """Status callback — marshals to status bar via signal."""
        self.status_updated.emit(message, "caching")