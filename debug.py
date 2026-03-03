"""Debug script — run this to find where the app fails."""

import sys
import traceback

try:
    print("Step 1: Testing PySide6...")
    from PySide6.QtWidgets import QApplication
    print("  OK")

    print("Step 2: Creating QApplication...")
    app = QApplication(sys.argv)
    print("  OK")

    print("Step 3: Testing config...")
    from config import AppConfig
    config = AppConfig()
    print("  OK")

    print("Step 4: Testing core imports...")
    from core.detector import FaceDetector, DetectedFace
    from core.aligner import FaceAligner
    from core.embedder import FaceEmbedder
    from core.matcher import FaceMatcher
    from core.indexer import FaceIndexer
    from core.pipeline import FacePipeline
    print("  OK")

    print("Step 5: Testing services imports...")
    from services.photo_scanner import PhotoScanner
    from services.cache_manager import CacheManager
    from services.reference_manager import ReferenceManager
    from services.segregator import Segregator
    print("  OK")

    print("Step 6: Testing UI imports...")
    from ui.main_window import MainWindow
    print("  OK")

    print("Step 7: Creating MainWindow...")
    window = MainWindow()
    print("  OK")

    print("Step 8: Showing window...")
    window.show()
    print("  OK")

    print("\nAll checks passed! Starting app...")
    sys.exit(app.exec())

except Exception as e:
    print(f"\nFAILED: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    input("\nPress Enter to exit...")