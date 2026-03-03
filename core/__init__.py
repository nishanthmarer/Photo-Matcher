##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: __init__.py (core)
# Description: Public API for the core ML package. Exposes the pipeline facade and all core components — detector,
#              aligner, embedder, matcher, and indexer — along with their data classes.
# Year: 2026
###########################################################################################################################

from core.detector import FaceDetector, DetectedFace
from core.aligner import FaceAligner
from core.embedder import FaceEmbedder
from core.matcher import FaceMatcher
from core.indexer import FaceIndexer, IndexEntry, SearchResult
from core.pipeline import FacePipeline, ProcessedFace, ProcessedImage

__all__ = [
    "FaceDetector",
    "DetectedFace",
    "FaceAligner",
    "FaceEmbedder",
    "FaceMatcher",
    "FaceIndexer",
    "IndexEntry",
    "SearchResult",
    "FacePipeline",
    "ProcessedFace",
    "ProcessedImage",
]