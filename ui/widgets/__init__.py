##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: __init__.py (ui/widgets)
# Description: Public API for the UI widgets package. Exposes the five main panels that make up the application
#              interface — reference management, photo source selection, progress tracking, results display,
#              the status bar, and the image review dialog.
# Year: 2026
###########################################################################################################################

from ui.widgets.reference_panel import ReferencePanel
from ui.widgets.photo_pool_panel import PhotoPoolPanel
from ui.widgets.progress_panel import ProgressPanel
from ui.widgets.results_panel import ResultsPanel
from ui.widgets.status_bar import StatusBar
from ui.widgets.image_review_dialog import ImageReviewDialog

__all__ = [
    "ReferencePanel",
    "PhotoPoolPanel",
    "ProgressPanel",
    "ResultsPanel",
    "StatusBar",
    "ImageReviewDialog",
]