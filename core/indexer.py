##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: indexer.py
# Description: FAISS-based nearest neighbor search for face embeddings. Wraps FAISS IndexFlatIP (Inner Product) for
#              fast cosine similarity search across thousands of face embeddings. Maintains a mapping from FAISS index
#              positions back to source photos for traceability. Used during the matching phase to find which cached
#              photos contain faces matching the enrolled references.
# Year: 2026
###########################################################################################################################

from dataclasses import dataclass

import numpy as np
import faiss

from config import EmbeddingConfig


@dataclass
class IndexEntry:
    """Maps a FAISS index position back to its source.

    FAISS only stores vectors and returns integer positions. This entry links each position back to the original
    photo and which face within that photo it represents.

    Attributes:
        photo_path: Path to the source photo (or person name for reference index).
        face_index: Which face in the photo this embedding belongs to (0-based).
    """
    photo_path: str
    face_index: int


@dataclass
class SearchResult:
    """Represents a single match returned from an index query.

    Attributes:
        photo_path: Path to the matched photo (or person name for reference index).
        face_index: Which face in the matched photo.
        distance: Cosine distance from the query. 0 = identical, lower = better match.
    """
    photo_path: str
    face_index: int
    distance: float


class FaceIndexer:
    """Wraps FAISS for fast nearest neighbor search across face embeddings.

    Uses IndexFlatIP (Inner Product) on L2-normalized vectors, which is mathematically equivalent to cosine
    similarity. Exact brute-force search is used since the expected scale (~15-20K faces) completes in under
    2ms per query. Approximate indexes (IVF, HNSW) are unnecessary below ~100K vectors.

    The index serves two purposes in the app:
    1. During matching: holds reference embeddings (enrolled persons), queried with cached photo embeddings.
    2. Traceability: maintains an ordered list of IndexEntry objects that maps each FAISS position back to
       its source photo and face number.

    Usage:
        indexer = FaceIndexer(config)
        indexer.add(embeddings, "person_name")
        results = indexer.search(query_embedding, threshold=0.5)
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        """Initialize an empty FAISS index.

        Args:
            config: Embedding configuration containing:
                    - embedding_size: Dimensionality of vectors (512 for ArcFace).
        """
        self._embedding_size = config.embedding_size
        self._index = faiss.IndexFlatIP(config.embedding_size)
        self._entries: list[IndexEntry] = []

    def add(self, embeddings: list[np.ndarray], photo_path: str) -> None:
        """Add face embeddings from a single source to the index.

        Each embedding gets a corresponding IndexEntry for traceability. The photo_path can be an actual file
        path (for photo embeddings) or a person name (for reference embeddings).

        Args:
            embeddings: List of L2-normalized 512-d embedding vectors.
            photo_path: Identifier for the source — file path or person name.
        """
        if not embeddings:
            return

        vectors = np.stack(embeddings, axis=0).astype(np.float32)
        self._index.add(vectors)

        for face_idx in range(len(embeddings)):
            self._entries.append(IndexEntry(photo_path=photo_path, face_index=face_idx))

    def search(self, query: np.ndarray, threshold: float) -> list[SearchResult]:
        """Find all indexed faces matching a query embedding within a distance threshold.

        Searches the entire index and returns all matches below the cosine distance threshold, sorted by
        distance ascending (best match first). Cosine distance is computed as 1 - dot_product(query, indexed).

        Args:
            query: L2-normalized 512-d embedding vector to search for.
            threshold: Maximum cosine distance to consider a match. Typical values: 0.4 (strict) to 0.6 (lenient).

        Returns:
            List of SearchResult objects within threshold, sorted by distance ascending.
            Returns an empty list if the index is empty or no matches are found.
        """
        if self._index.ntotal == 0:
            return []

        query_vector = query.reshape(1, -1).astype(np.float32)
        similarities, indices = self._index.search(query_vector, self._index.ntotal)

        results = []
        for similarity, idx in zip(similarities[0], indices[0]):
            if idx < 0:
                continue

            distance = 1.0 - float(similarity)

            if distance < threshold:
                entry = self._entries[idx]
                results.append(SearchResult(
                    photo_path=entry.photo_path,
                    face_index=entry.face_index,
                    distance=distance
                ))

        results.sort(key=lambda r: r.distance)

        return results

    def reset(self) -> None:
        """Clear the index and all mappings.

        Called before rebuilding the reference index for a new matching run. Releases the FAISS internal
        memory and clears all IndexEntry objects.
        """
        self._index.reset()
        self._entries.clear()

    @property
    def size(self) -> int:
        """Number of embeddings currently in the index."""
        return self._index.ntotal