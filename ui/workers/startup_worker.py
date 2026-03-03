##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: startup_worker.py
# Description: Background thread worker for application startup. Loads the Segregator (which initializes the ML
#              pipeline). Checks if models exist locally — if not, shows a download message since InsightFace will
#              download them automatically on first run (~326MB). Emits status signals for each step.
# Year: 2026
###########################################################################################################################

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from config import AppConfig
from services.segregator import Segregator


class StartupWorker(QThread):
    """Loads the Segregator and ML models in a background thread.

    Checks if model files exist locally before loading. If models need to be downloaded (first run),
    emits a clear download status message. Otherwise shows a loading message.

    Signals:
        status_updated(message, phase): For the status bar.
        startup_complete(segregator): When all models are loaded and ready.
        startup_failed(error_message): If loading fails.
    """

    status_updated = Signal(str, str)
    startup_complete = Signal(object)
    startup_failed = Signal(str)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config

    def run(self) -> None:
        """Load the Segregator and all ML models in the background."""
        try:
            model_root = Path(self._config.detection.model_root).resolve()
            model_dir = model_root / "models" / self._config.detection.model_name

            # Check if models exist locally
            det_model = model_dir / "det_10g.onnx"
            rec_model = model_dir / "w600k_r50.onnx"

            if not det_model.exists() or not rec_model.exists():
                self.status_updated.emit(
                    f"Downloading ML models to {model_dir} (first time only, ~326MB)...",
                    "loading"
                )
            else:
                self.status_updated.emit("Loading ML models...", "loading")

            segregator = Segregator(self._config)

            self.status_updated.emit("Ready — models loaded", "ready")
            self.startup_complete.emit(segregator)

        except Exception as e:
            self.status_updated.emit(f"Startup failed: {e}", "error")
            self.startup_failed.emit(str(e))