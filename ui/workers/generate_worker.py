##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: generate_worker.py
# Description: Background thread worker for folder generation. Runs the Segregator's match_and_copy() off the UI
#              thread — matches cached face embeddings against references and copies matched photos to per-person
#              output folders. Emits progress signals for matching and copying phases.
# Year: 2026
###########################################################################################################################

from PySide6.QtCore import QThread, Signal

from services.segregator import Segregator


class GenerateWorker(QThread):
    """Runs face matching and file copying (Generate Folders) in a background thread.

    Signals:
        status_updated(message, phase): for the status bar
        progress_updated(current, total, filename): for the progress bar during matching
        copy_progress(current, total, filename): for the progress bar + log during copying
        generate_complete(summary): when matching and copying finishes
        error_occurred(message): if an unhandled exception occurs
    """

    status_updated = Signal(str, str)
    progress_updated = Signal(int, int, str)
    copy_progress = Signal(int, int, str)
    generate_complete = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, segregator: Segregator, source_dir: str, output_dir: str) -> None:
        super().__init__()
        self._segregator = segregator
        self._source_dir = source_dir
        self._output_dir = output_dir

    def run(self) -> None:
        """Execute matching and folder generation in the background thread."""
        try:
            self._segregator.reset_generate_stop()

            summary = self._segregator.match_and_copy(
                source_dir=self._source_dir,
                output_dir=self._output_dir,
                status_callback=self._on_status,
                match_progress_callback=self._on_match_progress,
                copy_progress_callback=self._on_copy_progress,
            )

            self.generate_complete.emit(summary)

        except Exception as e:
            self.status_updated.emit(f"Generate error: {e}", "error")
            self.error_occurred.emit(str(e))

    def request_stop(self) -> None:
        """Request the segregator to stop folder generation gracefully. Thread-safe."""
        self._segregator.request_generate_stop()

    def _on_status(self, message: str) -> None:
        self.status_updated.emit(message, "generating")

    def _on_match_progress(self, current: int, total: int, filename: str) -> None:
        self.progress_updated.emit(current, total, filename)

    def _on_copy_progress(self, current: int, total: int, filename: str) -> None:
        self.copy_progress.emit(current, total, filename)