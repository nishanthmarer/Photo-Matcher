##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: aligner.py
# Description: Face alignment using 5-point landmarks via InsightFace's norm_crop. Applies an affine transformation
#              to map detected landmarks onto standard ArcFace reference positions, producing a normalized 112x112 crop.
#              This is the second step in the pipeline: detect → align → embed.
# Year: 2026
###########################################################################################################################

import numpy as np
from insightface.utils.face_align import norm_crop


class FaceAligner:
    """Aligns detected faces to a normalized 112x112 crop using 5-point landmarks.

    The alignment applies an affine transformation that rotates, scales, and translates the face so that the eyes,
    nose, and mouth corners land on fixed reference positions expected by ArcFace. This normalization is critical —
    without it, the same face at different angles would produce different embeddings.

    This class is stateless — no model is loaded, no GPU is used. The affine math runs on CPU and takes ~1-2ms per face.

    Usage:
        aligner = FaceAligner()
        aligned_crop = aligner.align(image, landmarks)  # returns 112x112 BGR numpy array
    """

    def align(self, image: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
        """Align a face using its 5-point landmarks.

        Crops from the ORIGINAL full-resolution image (not the det_size-resized version), so the 112x112 output
        retains maximum detail. The landmarks must be in the original image's coordinate space.

        Args:
            image: Full BGR image containing the face. Should be the original resolution for best quality.
            landmarks: 5-point facial landmarks, shape (5, 2), in the same coordinate space as the image.
                       Order: [left_eye, right_eye, nose_tip, left_mouth, right_mouth].

        Returns:
            Aligned face crop as a 112x112 BGR numpy array, ready for embedding extraction by ArcFace.
        """
        landmarks = np.array(landmarks, dtype=np.float32)
        aligned_face = norm_crop(image, landmarks)

        return aligned_face