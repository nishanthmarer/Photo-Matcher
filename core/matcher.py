##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: matcher.py
# Description: Direct face matching between individual embeddings using cosine distance. Used for small-scale
#              comparisons like checking a face against a handful of references. For large-scale search across
#              thousands of faces, use FaceIndexer (indexer.py) with FAISS instead.
# Year: 2026
###########################################################################################################################
import numpy as np

from config import MatchingConfig


class FaceMatcher:
    """Computes cosine distance between face embeddings and determines matches.

    Cosine distance = 1 - dot_product(a, b) for L2-normalized vectors.
    A distance of 0 means identical faces, ~0.4 means same person with variation, ~1.0+ means different people.

    This class handles direct 1-to-1 and 1-to-N comparisons. It does NOT scale to thousands of faces —
    use FaceIndexer for that. FaceMatcher is useful for:
    - Checking if two specific faces match
    - Finding the best match from a small set of references (e.g., 3-5 per person)

    Usage:
        matcher = FaceMatcher(config)
        is_same = matcher.is_match(embedding_a, embedding_b)
        best = matcher.find_best_match(target, references)
    """

    def __init__(self, config: MatchingConfig) -> None:
        """Initialize with matching configuration.

        Args:
            config: Matching configuration containing:
                    - distance_threshold: Maximum cosine distance to consider a match (default 0.5).
                      Lower = stricter matching, higher = more lenient.
        """
        self._threshold = config.distance_threshold

    @staticmethod
    def compute_distance(embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
        """Compute cosine distance between two embeddings.

        Both embeddings must be L2-normalized (output of FaceEmbedder). For normalized vectors,
        cosine distance = 1 - dot_product, which ranges from 0 (identical) to 2 (opposite).

        Args:
            embedding_a: First 512-d L2-normalized embedding vector.
            embedding_b: Second 512-d L2-normalized embedding vector.

        Returns:
            Cosine distance as a float. Typical thresholds: <0.3 very confident match,
            0.3-0.5 likely match, 0.5-0.7 uncertain, >0.7 different person.
        """
        similarity = np.dot(embedding_a, embedding_b)

        return float(1.0 - similarity)

    def is_match(self, embedding_a: np.ndarray, embedding_b: np.ndarray) -> bool:
        """Check if two embeddings belong to the same person.

        Args:
            embedding_a: First 512-d L2-normalized embedding vector.
            embedding_b: Second 512-d L2-normalized embedding vector.

        Returns:
            True if cosine distance is below the configured threshold.
        """
        return self.compute_distance(embedding_a, embedding_b) < self._threshold

    def find_best_match(self, target: np.ndarray, references: list[np.ndarray]) -> tuple[int, float] | None:
        """Find the closest matching reference for a target embedding.

        Compares the target against every reference and returns the best one if it's within threshold.
        Supports the 'match against closest' strategy — useful when a person has multiple reference photos
        from different angles (frontal, slight turn, etc.).

        Args:
            target: Target face embedding to match (512-d L2-normalized).
            references: List of reference embeddings for a single person.

        Returns:
            Tuple of (best_index, best_distance) if a match is found within threshold.
            None if no reference is close enough or if references list is empty.
        """
        if not references:
            return None

        distances = [self.compute_distance(target, ref) for ref in references]

        best_index = int(np.argmin(distances))
        best_distance = distances[best_index]

        if best_distance < self._threshold:
            return (best_index, best_distance)

        return None