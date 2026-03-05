##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: theme.py
# Description: Centralized theme and color definitions for the Photo Matcher UI. All colors, font sizes, and
#              reusable stylesheet strings live here so the entire look can be changed from one place. Includes
#              styles for the main application panels and the image review dialog. Font stacks are ordered for
#              cross-platform compatibility (system-ui first, platform-specific fonts as fallbacks).
# Year: 2026
###########################################################################################################################


# ---------------------------------------------------------------------------
# Color palette — deep navy theme
# ---------------------------------------------------------------------------

class Colors:
    """Application color palette."""

    # Backgrounds
    BG_APP = "#1a1a2e"
    BG_PANEL = "#16213e"
    BG_INPUT = "#0f172a"
    BG_STATUS_BAR = "#0f172a"

    # Borders
    BORDER = "#1e3a5f"
    BORDER_ACCENT = "#2d5a8e"
    SEPARATOR = "#1e3a5f"

    # Text
    TEXT_PRIMARY = "#f8fafc"
    TEXT_SECONDARY = "#e2e8f0"
    TEXT_MUTED = "#94a3b8"
    TEXT_DIM = "#64748b"
    TEXT_DARK = "#475569"

    # Action colors
    BLUE = "#2563eb"
    BLUE_HOVER = "#1d4ed8"
    GREEN = "#22c55e"
    GREEN_DARK = "#16a34a"
    RED = "#dc2626"
    RED_HOVER = "#b91c1c"
    RED_MUTED = "#ef444466"
    PURPLE = "#7c3aed"
    YELLOW = "#f59e0b"

    # Button backgrounds
    BTN_SECONDARY = "#1e3a5f"
    BTN_DISABLED = "#334155"


class Fonts:
    HEADER = "14px"
    BODY = "13px"
    SMALL = "12px"
    TINY = "11px"
    LABEL = "10px"


# ---------------------------------------------------------------------------
# Cross-platform font stacks
# ---------------------------------------------------------------------------
# system-ui resolves to the OS default on every platform:
#   Windows → Segoe UI, macOS → San Francisco, Linux → system default (often DejaVu/Noto)
# Platform-specific fonts are listed as fallbacks for environments where system-ui isn't supported.

_FONT_UI = "system-ui, -apple-system, 'Segoe UI', 'Roboto', 'Noto Sans', sans-serif"
_FONT_MONO = "'Fira Code', 'Cascadia Code', 'Consolas', 'DejaVu Sans Mono', 'Liberation Mono', monospace"


# ---------------------------------------------------------------------------
# Global application stylesheet
# ---------------------------------------------------------------------------

def app_stylesheet() -> str:
    """Global stylesheet — applied once to QApplication or QMainWindow."""
    return f"""
        QMainWindow {{
            background-color: {Colors.BG_APP};
        }}

        /* Default text color for everything */
        QWidget {{
            color: {Colors.TEXT_SECONDARY};
            font-family: {_FONT_UI};
            font-size: {Fonts.BODY};
        }}

        /* Input fields */
        QLineEdit {{
            background-color: {Colors.BG_INPUT};
            border: 1px solid {Colors.BORDER};
            border-radius: 6px;
            padding: 8px 12px;
            color: {Colors.TEXT_SECONDARY};
            font-size: {Fonts.BODY};
        }}
        QLineEdit:disabled {{
            color: {Colors.TEXT_DIM};
        }}

        /* Scroll areas — no border */
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}

        /* Scrollbar */
        QScrollBar:vertical {{
            background: transparent;
            width: 6px;
        }}
        QScrollBar::handle:vertical {{
            background: {Colors.BORDER};
            border-radius: 3px;
            min-height: 20px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        /* Progress bar */
        QProgressBar {{
            background-color: {Colors.BG_INPUT};
            border: 1px solid {Colors.BORDER};
            border-radius: 4px;
            max-height: 8px;
        }}
        QProgressBar::chunk {{
            background-color: {Colors.BLUE};
            border-radius: 3px;
        }}

        /* Log area */
        QTextEdit {{
            background-color: {Colors.BG_INPUT};
            border: 1px solid {Colors.BORDER};
            border-radius: 6px;
            padding: 8px;
            color: {Colors.TEXT_DIM};
            font-family: {_FONT_MONO};
            font-size: {Fonts.TINY};
        }}

        /* Labels — no border, no background */
        QLabel {{
            border: none;
            background: transparent;
            padding: 0px;
        }}
    """


# ---------------------------------------------------------------------------
# Component stylesheets — applied via setProperty("class", ...) or directly
# ---------------------------------------------------------------------------

PANEL_CARD_STYLE = f"""
    background-color: {Colors.BG_PANEL};
    border: 1px solid {Colors.BORDER};
    border-radius: 10px;
"""

def header_stylesheet() -> str:
    return f"font-size: {Fonts.HEADER}; font-weight: bold; color: {Colors.TEXT_PRIMARY}; border: none; background: transparent;"

def label_stylesheet() -> str:
    return f"font-size: 12px; font-weight: bold; color: {Colors.TEXT_MUTED}; letter-spacing: 0.5px; border: none; background: transparent;"

def hint_stylesheet() -> str:
    return f"font-size: {Fonts.LABEL}; color: {Colors.TEXT_DIM}; border: none; background: transparent;"

def summary_stylesheet() -> str:
    return f"""
        background-color: {Colors.BG_INPUT};
        border: 1px solid {Colors.BORDER};
        border-radius: 6px;
        padding: 8px 10px;
        font-size: {Fonts.TINY};
        color: {Colors.TEXT_MUTED};
    """

def person_entry_stylesheet() -> str:
    return f"""
        background-color: {Colors.BG_INPUT};
        border: 1px solid {Colors.BORDER};
        border-radius: 8px;
    """

def result_entry_stylesheet() -> str:
    return f"""
        background-color: {Colors.BG_INPUT};
        border: 1px solid {Colors.BORDER};
        border-radius: 8px;
    """


# ---------------------------------------------------------------------------
# Button stylesheets — main application
# ---------------------------------------------------------------------------

def btn_primary_stylesheet() -> str:
    return f"""
        QPushButton {{
            background-color: {Colors.BLUE};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            font-size: {Fonts.BODY};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.BLUE_HOVER};
        }}
        QPushButton:disabled {{
            background-color: {Colors.BTN_DISABLED};
            color: {Colors.TEXT_DIM};
        }}
    """

def btn_green_stylesheet() -> str:
    return f"""
        QPushButton {{
            background-color: {Colors.GREEN};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            font-size: {Fonts.BODY};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.GREEN_DARK};
        }}
        QPushButton:disabled {{
            background-color: {Colors.BTN_DISABLED};
            color: {Colors.TEXT_DIM};
        }}
    """

def btn_secondary_stylesheet() -> str:
    return f"""
        QPushButton {{
            background-color: {Colors.BTN_SECONDARY};
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid {Colors.BORDER_ACCENT};
            border-radius: 6px;
            padding: 8px 14px;
            font-size: {Fonts.BODY};
        }}
        QPushButton:hover {{
            background-color: {Colors.BORDER_ACCENT};
        }}
        QPushButton:disabled {{
            background-color: {Colors.BTN_DISABLED};
            color: {Colors.TEXT_DIM};
            border-color: {Colors.BORDER};
        }}
    """

def btn_stop_stylesheet() -> str:
    return f"""
        QPushButton {{
            background-color: {Colors.RED};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 15px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.RED_HOVER};
        }}
        QPushButton:disabled {{
            background-color: #3b1c1c;
            color: #6b3333;
        }}
    """

def btn_remove_stylesheet() -> str:
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {Colors.RED};
            border: 1px solid {Colors.RED_MUTED};
            border-radius: 4px;
            font-size: 12px;
            padding: 2px;
        }}
        QPushButton:hover {{
            background-color: {Colors.RED};
            color: white;
        }}
    """

def btn_clear_stylesheet() -> str:
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {Colors.TEXT_MUTED};
            border: 1px solid {Colors.BTN_DISABLED};
            border-radius: 5px;
            padding: 3px 10px;
            font-size: {Fonts.LABEL};
        }}
        QPushButton:hover {{
            background-color: {Colors.BTN_DISABLED};
            color: {Colors.TEXT_SECONDARY};
        }}
    """


# ---------------------------------------------------------------------------
# Button & label stylesheets — image review dialog
# ---------------------------------------------------------------------------

def btn_review_stylesheet() -> str:
    """Stylesheet for the Review button in results panel."""
    return f"""
        QPushButton {{
            background-color: {Colors.PURPLE};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: {Fonts.SMALL};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #6d28d9;
        }}
    """


def review_dialog_stylesheet() -> str:
    """Global stylesheet for the image review dialog window."""
    return f"""
        QWidget {{
            color: {Colors.TEXT_SECONDARY};
            font-family: {_FONT_UI};
            font-size: {Fonts.BODY};
        }}
    """


def review_info_stylesheet() -> str:
    """Stylesheet for counter and detail labels in the review dialog."""
    return f"font-size: {Fonts.SMALL}; color: {Colors.TEXT_MUTED}; background: transparent;"


def review_status_keeping_stylesheet() -> str:
    """Stylesheet for the KEEPING status badge."""
    return f"font-size: {Fonts.BODY}; font-weight: bold; color: {Colors.GREEN}; background: transparent;"


def review_status_deleted_stylesheet() -> str:
    """Stylesheet for the MARKED FOR DELETION status badge."""
    return f"font-size: {Fonts.BODY}; font-weight: bold; color: {Colors.RED}; background: transparent;"


def review_stats_stylesheet() -> str:
    """Stylesheet for the stats bar at the bottom of the review dialog."""
    return f"font-size: {Fonts.SMALL}; color: {Colors.TEXT_DIM}; background: transparent;"


def btn_review_back_stylesheet() -> str:
    """Stylesheet for the Back button in the review dialog."""
    return f"""
        QPushButton {{
            background-color: {Colors.BLUE};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 16px;
            font-size: {Fonts.BODY};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.BLUE_HOVER};
        }}
        QPushButton:disabled {{
            background-color: {Colors.BTN_DISABLED};
            color: {Colors.TEXT_DIM};
        }}
    """


def btn_review_delete_stylesheet() -> str:
    """Stylesheet for the Delete button in the review dialog."""
    return f"""
        QPushButton {{
            background-color: {Colors.RED};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 16px;
            font-size: {Fonts.BODY};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.RED_HOVER};
        }}
    """


def btn_review_restore_stylesheet() -> str:
    """Stylesheet for the Restore button in the review dialog."""
    return f"""
        QPushButton {{
            background-color: {Colors.YELLOW};
            color: #1e1e2e;
            border: none;
            border-radius: 8px;
            padding: 10px 16px;
            font-size: {Fonts.BODY};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #d97706;
        }}
    """


def btn_review_skip_stylesheet() -> str:
    """Stylesheet for the Skip button in the review dialog."""
    return f"""
        QPushButton {{
            background-color: {Colors.GREEN};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 16px;
            font-size: {Fonts.BODY};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.GREEN_DARK};
        }}
    """


def btn_review_quit_stylesheet() -> str:
    """Stylesheet for the Quit button in the review dialog."""
    return f"""
        QPushButton {{
            background-color: {Colors.BTN_SECONDARY};
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid {Colors.BORDER_ACCENT};
            border-radius: 8px;
            padding: 10px 16px;
            font-size: {Fonts.BODY};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.BORDER_ACCENT};
        }}
    """