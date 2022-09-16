from qtpy.QtCore import Qt, QMargins
from qtpy.QtGui import QColor, QFont

# START Style Settings#

# Dialog Layouts
DIA_SPACING = 3
DIA_MARGIN = 8

# Dock Layouts
DOCK_SPACING = 2
DOCK_MARGIN = QMargins(3, 3, 3, 3)

# Custom colors
COLORS = {
    "tbl_textfg":         QColor(0, 0, 0),
    # "tbl_msoready":             QColor(77, 255, 77),
    "tbl_ready":          QColor(0, 179, 0),
    # "tbl_msoactive":            QColor(255, 255, 102),
    "tbl_active":         QColor(230, 230, 0),
    # "tbl_msovacant":            QColor(255, 163, 102),
    "tbl_vacant":         QColor(255, 102, 0),
    "background":         QColor(40, 40, 40),
    "reservation_arrive": QColor(128, 255, 128),
    "reservation_cancel": QColor(255, 128, 128)
}

# Uses the ready, active and vacant colors to dynamically lighten them for the mouseover colors
COLORS["tbl_msoready"] = QColor.lighter(COLORS["tbl_ready"], 120)
COLORS["tbl_msoactive"] = QColor.lighter(COLORS["tbl_active"], 120)
COLORS["tbl_msovacant"] = QColor.lighter(COLORS["tbl_vacant"], 120)

# Colors to set new servers to
SERVER_COLORS = [
    Qt.red,
    Qt.blue,
    Qt.green,
    Qt.cyan,
    Qt.yellow,
    Qt.magenta,
    Qt.darkRed,
    Qt.darkBlue,
    Qt.darkGreen,
    Qt.darkCyan,
    Qt.darkYellow,
    Qt.darkMagenta
    # QColor(0, 0, 255)
]

# Regular font for UI elements
FONT = QFont("Calibri", 20)
# Font on all tables
FONT_TABLE = QFont("Calibri", 20)
# Font on the server list
FONT_SERVERLIST = QFont("Calibri", 16)

# END Style Settings#

# Default overflow rules
overflowRules = {
    "default": {"num": 0, "color": QColor(100, 255, 100)}
}

# Default recent floorplans list
recentFloorplans = []

global APP
global WINDOW
global SCENE
global VIEW
global SERVER_LIST
global RES_LIST
global SETTINGS

COUNT_MODE = "heads"
EDIT_MODE = False
ALL_SERVERS = []
RECENTS = []
