##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: main.py
# Description: Application entry point for Photo Matcher. Creates the Qt application, initializes the main window,
#              and starts the event loop. Suppresses noisy ONNX Runtime logs — GPU status is logged cleanly by our
#              detector module. InsightFace's few startup prints (model loading) are left as-is since they're harmless.
# Year: 2026
###########################################################################################################################

import os
import sys
import traceback

# Suppress ONNX Runtime C++ error/warning logs before any ML imports.
os.environ["ORT_LOG_LEVEL"] = "3"

# Limit ONNX Runtime's CUDA arena allocator to prevent unbounded GPU memory growth.
# Without this, ORT grabs GPU memory in expanding chunks and never releases them.
os.environ["ORT_CUDA_ARENA_EXTEND_STRATEGY"] = "kSameAsRequested"

# Suppress ONNX Runtime Python-level session logs (the "Applied providers" spam).
import onnxruntime
onnxruntime.set_default_logger_severity(3)

from PySide6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow


def main() -> None:
    """Application entry point."""
    app = QApplication(sys.argv)

    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())

    except Exception as e:
        error_msg = f"{e}\n\n{traceback.format_exc()}"
        print(f"\n[FATAL ERROR] {error_msg}", file=sys.stderr)

        QMessageBox.critical(None, "Photo Matcher — Startup Error", f"Failed to start:\n\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()