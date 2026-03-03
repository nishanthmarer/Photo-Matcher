##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: embedder.py
# Description: Face embedding extraction using ArcFace (w600k_r50) via InsightFace. Converts aligned 112x112 face
#              crops into 512-dimensional L2-normalized vectors (signatures). Two faces of the same person produce
#              vectors that are close together; different people produce vectors that are far apart.
#              This is the third step in the pipeline: detect → align → embed.
# Year: 2026
###########################################################################################################################

from pathlib import Path

import numpy as np
from insightface.model_zoo import get_model

from config import EmbeddingConfig, DetectionConfig


class FaceEmbedder:
    """Extracts 512-d ArcFace embeddings from aligned 112x112 face crops.

    Loads the w600k_r50 recognition model from the buffalo_l model pack. This model was trained on WebFace600K
    (600K identities, ~10M images) and produces embeddings that are L2-normalized — meaning they sit on a unit
    hypersphere and can be compared using cosine similarity (dot product).

    Model loading is expensive (~1 second), so this class should be instantiated once and reused.

    Usage:
        embedder = FaceEmbedder(embedding_config, detection_config)
        vector = embedder.extract(aligned_face)          # single face → 512-d vector
        vectors = embedder.extract_batch(aligned_faces)   # multiple faces → list of 512-d vectors
    """

    RECOGNITION_MODEL = "w600k_r50.onnx"

    def __init__(self, config: EmbeddingConfig, detection_config: DetectionConfig) -> None:
        """Initialize and load the ArcFace recognition model.

        Args:
            config: Embedding configuration containing:
                    - embedding_size: Dimensionality of output vectors (512 for ArcFace).
            detection_config: Detection configuration containing:
                              - gpu_id: GPU device ID for inference (negative = CPU only).
                              - model_dir: Root directory for model storage.
                              - model_name: Model pack name (e.g., "buffalo_l").
        """
        self._config = config
        model_dir = Path(detection_config.model_root).resolve() / "models" / detection_config.model_name
        model_path = str(model_dir / self.RECOGNITION_MODEL)
        self._model = get_model(model_path, providers=self._get_providers(detection_config.gpu_id))
        self._model.prepare(ctx_id=detection_config.gpu_id)

    def extract(self, aligned_face: np.ndarray) -> np.ndarray:
        """Extract embedding from a single aligned face.

        Args:
            aligned_face: Aligned BGR face crop, 112x112, numpy array. Must be the output of FaceAligner.align().

        Returns:
            L2-normalized 512-d embedding vector as a 1-D numpy array.
        """
        embedding = self._model.get_feat([aligned_face])

        return self._normalize(embedding[0].flatten())

    def extract_batch(self, aligned_faces: list[np.ndarray]) -> list[np.ndarray]:
        """Extract embeddings from multiple aligned faces in a single GPU call.

        Passes all faces as a list to InsightFace's get_feat, which handles batching internally via
        cv2.dnn.blobFromImages. More efficient than calling extract() in a loop because the GPU processes
        all faces in one forward pass.

        Args:
            aligned_faces: List of aligned BGR face crops, each 112x112 numpy array.

        Returns:
            List of L2-normalized 512-d embedding vectors. Same order as input.
            Returns an empty list if input is empty.
        """
        if not aligned_faces:
            return []

        embeddings = self._model.get_feat(aligned_faces)

        return [self._normalize(emb.flatten()) for emb in embeddings]

    @staticmethod
    def _normalize(embedding: np.ndarray) -> np.ndarray:
        """L2-normalize an embedding vector to unit length.

        After normalization, the vector sits on a unit hypersphere. This means cosine similarity between two
        normalized vectors equals their dot product, which is what FAISS IndexFlatIP computes.

        Args:
            embedding: Raw embedding vector from the model.

        Returns:
            L2-normalized embedding vector. Returns the original if norm is zero (degenerate case).
        """
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding

        return embedding / norm

    @staticmethod
    def _get_providers(gpu_id: int) -> list[str]:
        """Resolve ONNX Runtime execution providers based on GPU config.

        Args:
            gpu_id: GPU device ID. Negative value means CPU only.

        Returns:
            Ordered list of ONNX execution provider strings.
        """
        if gpu_id >= 0:
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]

        return ["CPUExecutionProvider"]