##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: pipeline.py
# Description: Facade over the core ML modules: detect → align → embed. Provides a single entry point for the
#              services layer to process images without knowing about individual core components. The services layer
#              (segregator, reference_manager) calls pipeline.process_image() and gets back complete results with
#              bounding boxes, landmarks, aligned crops, and 512-d embeddings for every detected face.
# Year: 2026
###########################################################################################################################

from dataclasses import dataclass, field

import numpy as np

from config import AppConfig
from core.detector import FaceDetector
from core.aligner import FaceAligner
from core.embedder import FaceEmbedder


@dataclass
class ProcessedFace:
    """Complete result for a single detected face.

    Attributes:
        bbox: Bounding box [x1, y1, x2, y2] in original image coordinates.
        landmarks: 5-point facial landmarks, shape (5, 2), in original image coordinates.
        confidence: Detection confidence from RetinaFace (0.0 to 1.0).
        embedding: 512-d L2-normalized ArcFace embedding vector (the face "signature").
        aligned_face: 112x112 BGR aligned face crop used to generate the embedding.
    """
    bbox: np.ndarray
    landmarks: np.ndarray
    confidence: float
    embedding: np.ndarray
    aligned_face: np.ndarray


@dataclass
class ProcessedImage:
    """Complete result for a processed image.

    Attributes:
        photo_path: Path to the source image file.
        faces: List of ProcessedFace objects for every detected face. Empty if no faces found.
    """
    photo_path: str
    faces: list[ProcessedFace] = field(default_factory=list)

    @property
    def face_count(self) -> int:
        """Number of faces detected in this image."""
        return len(self.faces)


class FacePipeline:
    """Facade over core modules: detect → align → embed.

    Orchestrates the three core ML steps in sequence for each image:
    1. FaceDetector: finds faces and landmarks (runs on det_size internally, ~200-300ms)
    2. FaceAligner: produces 112x112 normalized crops from original resolution (~1-2ms per face)
    3. FaceEmbedder: converts crops to 512-d signature vectors (~5-10ms per face)

    The pipeline is stateful only in that it holds loaded ML models. It does not accumulate data between calls —
    each process_image() call is independent.

    Usage:
        pipeline = FacePipeline(config)
        result = pipeline.process_image(image, "/path/to/photo.jpg")
        for face in result.faces:
            print(face.confidence, face.embedding.shape)  # 0.87, (512,)
    """

    def __init__(self, config: AppConfig) -> None:
        """Initialize all core ML components.

        Loads both the RetinaFace detection model and ArcFace recognition model. This takes ~2-3 seconds
        on first run (model download) and ~1-2 seconds on subsequent runs (loading from disk).

        Args:
            config: Top-level application configuration. Sub-configs are passed to each component:
                    - config.detection → FaceDetector
                    - config.embedding + config.detection → FaceEmbedder
        """
        self._config = config
        self._detector = FaceDetector(config.detection)
        self._aligner = FaceAligner()
        self._embedder = FaceEmbedder(config.embedding, config.detection)

    def process_image(self, image: np.ndarray, photo_path: str) -> ProcessedImage:
        """Process a single image through the full detect → align → embed pipeline.

        The image is passed at full resolution. Detection resizes internally via det_size, but alignment
        crops from the original for maximum embedding quality.

        All faces detected above the confidence threshold are processed. Embeddings for all faces in the
        image are extracted in a single batched GPU call for efficiency.

        Args:
            image: BGR image as numpy array at full resolution (e.g., 6000x4000 from DSLR).
            photo_path: Path to the source image file, stored in the result for traceability.

        Returns:
            ProcessedImage containing all detected faces with embeddings.
            If no faces are found, returns a ProcessedImage with an empty faces list.
        """
        detected_faces = self._detector.detect(image)

        if not detected_faces:
            return ProcessedImage(photo_path=photo_path)

        aligned_crops = [self._aligner.align(image, face.landmarks) for face in detected_faces]

        embeddings = self._embedder.extract_batch(aligned_crops)

        processed_faces = [
            ProcessedFace(
                bbox=face.bbox,
                landmarks=face.landmarks,
                confidence=face.confidence,
                embedding=embedding,
                aligned_face=aligned_crop
            )
            for face, embedding, aligned_crop
            in zip(detected_faces, embeddings, aligned_crops)
        ]

        return ProcessedImage(photo_path=photo_path, faces=processed_faces)

    def release(self) -> None:
        """Destroy ONNX sessions to release GPU memory.

        Frees model weights and arena buffers from GPU. After calling this, process_image() cannot be used
        until reload() is called. ~300MB CUDA context residual remains (only freed on process exit).
        """
        import gc

        if hasattr(self, '_detector') and self._detector is not None:
            if hasattr(self._detector, '_app') and self._detector._app is not None:
                del self._detector._app
                self._detector._app = None

        if hasattr(self, '_embedder') and self._embedder is not None:
            if hasattr(self._embedder, '_model') and self._embedder._model is not None:
                del self._embedder._model
                self._embedder._model = None

        gc.collect()

    def reload(self) -> None:
        """Recreate ONNX sessions after a release().

        Reloads models from disk (~2-3 seconds). Called automatically before next operation.
        """
        self._detector = FaceDetector(self._config.detection)
        self._embedder = FaceEmbedder(self._config.embedding, self._config.detection)

    @property
    def is_loaded(self) -> bool:
        """Check if ML models are loaded and ready for inference."""
        det_ok = (hasattr(self, '_detector') and self._detector is not None
                  and hasattr(self._detector, '_app') and self._detector._app is not None)
        emb_ok = (hasattr(self, '_embedder') and self._embedder is not None
                  and hasattr(self._embedder, '_model') and self._embedder._model is not None)
        return det_ok and emb_ok

    def reload(self) -> None:
        """Destroy and recreate ONNX sessions to release GPU memory.

        ONNX Runtime's arena allocator never releases GPU memory back to CUDA during a session's lifetime.
        The only way to free it is to destroy the sessions and create new ones. This takes ~2-3 seconds
        but completely resets GPU memory to baseline.

        Called periodically during long processing runs to prevent GPU memory exhaustion.
        """
        import gc

        config = self._config

        # Destroy old sessions — releases GPU arena memory
        del self._detector
        del self._embedder
        gc.collect()

        # Recreate with fresh sessions — GPU memory starts from zero
        self._detector = FaceDetector(config.detection)
        self._embedder = FaceEmbedder(config.embedding, config.detection)