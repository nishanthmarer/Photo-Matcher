##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: detector.py
# Description: Face detection using RetinaFace (SCRFD) via InsightFace.
#              Detects faces in images and returns bounding boxes, 5-point landmarks, and confidence scores. This is the
#              first step in the pipeline: detect → align → embed.
# Year: 2026
###########################################################################################################################

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from insightface.app import FaceAnalysis

from config import DetectionConfig, LoggingConfig
from utils.logger import setup_logger

logger = setup_logger("core.detector", LoggingConfig())


@dataclass
class DetectedFace:
    """Represents a single detected face in an image.

    Attributes:
        bbox: Bounding box coordinates [x1, y1, x2, y2] in original image dimensions.
        landmarks: 5-point facial landmarks (left eye, right eye, nose tip, left mouth corner, right mouth corner),
                   shape (5, 2), in original image coordinates.
        confidence: Detection confidence score between 0.0 and 1.0.
                    Higher means the model is more certain this is a face.
    """
    bbox: np.ndarray
    landmarks: np.ndarray
    confidence: float


class FaceDetector:
    """Detects faces in images using RetinaFace (SCRFD) via InsightFace.

    The detector resizes input images internally to det_size (default 1280x1280) with letterboxing, runs the neural
    network, then maps detected coordinates back to the original image dimensions.

    Holds the loaded model as state for reuse across multiple images. Model loading is expensive (~1-2 seconds), so
    this class should be instantiated once and reused.

    Usage:
        detector = FaceDetector(config)
        faces = detector.detect(image)  # returns list of DetectedFace
    """

    def __init__(self, config: DetectionConfig) -> None:
        """Initialize and load the RetinaFace detection model.

        Downloads the model on first run (~300MB for buffalo_l detection).
        Subsequent runs load from ~/.insightface/models/.

        Args:
            config: Detection configuration containing:
                    - model_name: InsightFace model pack (e.g., "buffalo_l")
                    - confidence_threshold: Minimum score to keep a detection
                    - gpu_id: GPU device ID (negative = CPU only)
                    - det_size: Internal detection resolution (width, height)
        """
        self._config = config

        # Ensure model directory exists — models stored at {model_root}/models/{model_name}/
        model_root = Path(config.model_root).resolve()
        model_root.mkdir(parents=True, exist_ok=True)

        self._app = FaceAnalysis(
            name=config.model_name,
            root=str(model_root),
            allowed_modules=["detection"],
            providers=self._get_providers()
        )
        self._app.prepare(ctx_id=config.gpu_id, det_size=config.det_size)
        self._log_active_provider()

    def detect(self, image: np.ndarray) -> list[DetectedFace]:
        """Detect all faces in an image.

        The image is resized internally to det_size for detection, but returned bounding boxes and landmarks are in
        the original image's coordinate space. This means alignment can crop from the original full-resolution image
        for maximum quality.

        Args:
            image: BGR image as numpy array (OpenCV format). Can be any resolution — the model handles internal resizing.

        Returns:
            List of DetectedFace objects sorted by confidence descending, filtered by the configured confidence threshold.
            Returns an empty list if no faces are found.
        """
        raw_faces = self._app.get(image)

        detected = [
            DetectedFace(
                bbox=face.bbox,
                landmarks=face.kps,
                confidence=float(face.det_score)
            )
            for face in raw_faces
            if face.det_score >= self._config.confidence_threshold
        ]

        detected.sort(key=lambda f: f.confidence, reverse=True)

        return detected

    def _get_providers(self) -> list[str]:
        """Resolve ONNX Runtime execution providers based on GPU config.

        CUDA provider is preferred when a valid GPU ID is given. CPU provider is always included as a fallback — if
        CUDA is unavailable, ONNX Runtime will silently fall back to CPU.

        Returns:
            Ordered list of ONNX execution provider strings.
        """
        if self._config.gpu_id >= 0:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    def _log_active_provider(self) -> None:
        """Check which execution provider is actually active and log a warning if GPU is unavailable."""
        import onnxruntime as ort

        available = ort.get_available_providers()

        if "CUDAExecutionProvider" in available:
            logger.info("Detection model loaded — GPU (CUDA) active")
        else:
            logger.warning("GPU unavailable — running on CPU (slower). Check CUDA/cuDNN installation.")