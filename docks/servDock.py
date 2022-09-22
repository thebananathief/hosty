from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import core.globals as g
import core.objects as o
from core.globals import get_path


class ServList_Dock(QDockWidget):
    def __init__(self, parent=None):
        super(ServList_Dock, self).__init__("Servers", parent)

        self.setWidget(ServerWidget(self))
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)


class ServerWidget(QWidget):
    def __init__(self, parent=None):
        super(ServerWidget, self).__init__(parent)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred))

        toolbar = QToolBar("Server Tool Bar", self)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toolbar.setIconSize(QSize(16, 16))

        toolbar_addServer = toolbar.addAction(QIcon(get_path("add.png")), "Add")
        toolbar_addServer.triggered.connect(self.toolbar_clickAddServer)
        toolbar_addServer.setToolTip("Adds a server")
        toolbar_addServer.setStatusTip("Adds a server")

        toolbar_renameServer = toolbar.addAction(QIcon(get_path("pencil.png")), "Rename")
        toolbar_renameServer.triggered.connect(self.toolbar_clickRenameServer)
        toolbar_renameServer.setToolTip("Renames a server")
        toolbar_renameServer.setStatusTip("Renames a server")

        toolbar_removeServer = toolbar.addAction(QIcon(get_path("delete.png")), "Remove")
        toolbar_removeServer.triggered.connect(self.toolbar_clickRemoveServer)
        toolbar_removeServer.setToolTip("Removes a server")
        toolbar_removeServer.setStatusTip("Removes a server")

        layout = QGridLayout(self)

        layout.setSpacing(g.DOCK_SPACING)
        layout.setContentsMargins(g.DOCK_MARGIN)

        self.pred = ServerPredictor(self)

        layout.addWidget(self.pred, 0, 0)
        layout.addWidget(toolbar, 1, 0)

        self.serverLineEdit = QLineEdit(self)
        layout.addWidget(self.serverLineEdit, 2, 0)

        self.servList = ServerList(self)
        layout.addWidget(self.servList, 3, 0)

        self.setLayout(layout)

    def sizeHint(self):
        return QSize(160, 100)

    def toolbar_clickRenameServer(self):
        select = self.servList.selected

        if select is None:
            return print("no selection")

        txt = self.serverLineEdit.text()
        if txt == "":
            return print("type something!")

        for server in g.ALL_SERVERS:
            if server.name == txt:
                return print("duplicate name")

        g.ALL_SERVERS[select.data(Qt.UserRole)].name = txt
        self.servList.populate_servers()

    def toolbar_clickRemoveServer(self):
        select = self.servList.selected

        if select is None:
            return print("no selection")

        # Store which row this server was on
        prev_idx = self.servList.row(select)
        # Delete the server
        g.ALL_SERVERS[select.data(Qt.UserRole)].deleteServer()
        # Set the selected item to the row we just deleted (if possible)
        self.servList.selected = self.servList.item(prev_idx)

    def toolbar_clickAddServer(self):
        txt = self.serverLineEdit.text()

        if txt == "":
            return print("type something!")

        for server in g.ALL_SERVERS:
            if server.name == txt:
                return print("duplicate name")

        o.POS_Server(txt)
        self.servList.populate_servers()


class ServerPredictor(QWidget):
    def __init__(self, parent=None):
        super(ServerPredictor, self).__init__(parent)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed))
        self.choice = ""
        self.overflowColor = g.SETTINGS.value("data/overflowRules")["default"]["color"]
        self.overflow_score = 0

        # Initialize rects for the server guesser and overflow boxes
        self.predict_rect = self.rect().adjusted(0, 0, 0, 0)
        self.overflow_rect = self.rect().adjusted(0, 30, 0, 0)
        self.indicator_rect = QRect(5, 6, 18, 18)
        self.predict_no_server_rect = self.rect().marginsRemoved(QMargins(2, 2, 2, 2))
        self.predict_text_rect = self.rect().marginsRemoved(QMargins(27, 0, -20, 0))
        self.overflow_text_rect = self.overflow_rect.marginsRemoved(QMargins(2, 1, 2, 1))

        self.ticker = None

    def resizeEvent(self, e):
        # Update rects based on new size
        # QMargins(left, top, right, bottom)
        self.predict_rect = self.rect().marginsRemoved(QMargins(1, 1, 1, 21))
        self.overflow_rect = self.rect().marginsRemoved(QMargins(1, 31, 1, 1))
        self.indicator_rect = QRect(5, 6, 18, 18)
        self.predict_no_server_rect = self.predict_rect.marginsRemoved(QMargins(2, 2, 2, 2))
        self.predict_text_rect = self.predict_rect.marginsRemoved(QMargins(27, 0, -20, 0))
        self.overflow_text_rect = self.overflow_rect.marginsRemoved(QMargins(2, 1, 2, 1))

    def calculate_choice(self):
        if self.ticker is None:
            self.ticker = self.startTimer(1000)

        # Server Score Calculation
        highestTotal = 0

        for server in g.ALL_SERVERS:
            if server.headTotal > highestTotal:
                highestTotal = server.headTotal

        scores = {}

        for server in g.ALL_SERVERS:
            active = server.headActive

            if server.headActive == 0:
                active = -20

            scores[server] = highestTotal - server.headTotal - active

        # print("Prediction Scores:")
        # for k in scores:
        # 	print(k.name, scores[k])

        # Set the server prediction to the server with the highest score
        if len(scores) < 1:
            self.choice = ""
        else:
            self.choice = max(scores, key=lambda i: scores[i])

        self.update()

    def calculate_overflow(self):
        # BUG: OverflowScore fluctuates weirdly whenever multiple tables are down
        prev = self.overflow_score
        self.overflow_score = 0

        # Must copy the table because we'll be removing recents from it as we iterate
        # (removing during iteration leads to sometimes skipping one of the objects)
        tempRec = g.RECENTS.copy()

        # Overflow Score Calculation
        for seat in tempRec:
            # Seconds elapsed since the table was sat / 60
            # 5 seconds = 0.083
            # 60 seconds = 1
            min_diff = seat["time"].secsTo(QTime.currentTime()) / 60

            # customers - (elapsed * multiplier)
            sc = round(seat["num"] - (min_diff * float(g.SETTINGS.value("settings/overflowMultiplier"))), 4)

            # If this table's score is less than 0, remove it from the recents (deemed unecessary)
            if sc <= 0:
                g.RECENTS.remove(seat)
            else:
                self.overflow_score += sc

        # Sort overflow rules by threshold
        tempTbl = []
        for rule in g.overflowRules:
            tempTbl.append(rule)

        def sort_by_threshold(d):
            return g.overflowRules[d]["num"]

        tempTbl.sort(key=sort_by_threshold)

        # Set overflow color
        for rule in tempTbl:
            if self.overflow_score > g.overflowRules[rule]["num"]:
                self.overflowColor = g.overflowRules[rule]["color"]

        self.update()

    def timerEvent(self, e):
        if self.choice == "":
            self.killTimer(self.ticker)

            return

        # self.calculate_choice()
        self.calculate_overflow()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setPen(QPen(Qt.black, 1, Qt.SolidLine))
        # Draw the server prediction box
        p.drawRoundedRect(self.predict_rect, 2, 2)

        g.FONT_SERVERLIST.setPointSize(17)
        p.setFont(g.FONT_SERVERLIST)

        # There's a predicted server
        if self.choice:
            # Draw the server's color box and their name
            p.setBrush(QBrush(self.choice.color, Qt.SolidPattern))
            p.drawRoundedRect(self.indicator_rect, 2, 2)
            p.drawText(self.predict_text_rect, (Qt.AlignLeft | Qt.AlignVCenter), self.choice.name + " is next")

            # Smaller font
            g.FONT_SERVERLIST.setPointSize(13)
            p.setFont(g.FONT_SERVERLIST)

            # Draw box and text for overflow
            p.setBrush(QBrush(self.overflowColor, Qt.SolidPattern))
            p.drawRoundedRect(self.overflow_rect, 2, 2)
            p.drawText(self.overflow_text_rect, (Qt.AlignCenter | Qt.AlignVCenter),
                       "Overflow:" + str(round(self.overflow_score, 1)))
        # No prediction
        else:
            p.drawText(self.predict_no_server_rect, (Qt.AlignCenter | Qt.AlignVCenter), "Add a server!")

            # Draw box and text for overflow
            p.setBrush(QBrush(g.SETTINGS.value("data/overflowRules")["default"]["color"], Qt.SolidPattern))
            p.drawRoundedRect(self.overflow_rect, 2, 2)

    def sizeHint(self):
        return QSize(155, 50)


class ServerList(QListWidget):
    def __init__(self, parent=None):
        super(ServerList, self).__init__(parent)
        self.setSelectionMode(QAbstractItemView.NoSelection)

        def on_item_clicked(i: QListWidgetItem, prev: QListWidgetItem):
            if i is None:
                return

            self.parent().serverLineEdit.setText(g.ALL_SERVERS[i.data(Qt.UserRole)].name)
            self.parent().serverLineEdit.selectAll()
            self.parent().serverLineEdit.setFocus(Qt.MouseFocusReason)
            self.selected = i

        # self.itemPressed.connect(on_item_clicked)
        self.currentItemChanged.connect(on_item_clicked)
        self.selected = None

    def populate_servers(self):
        self.clear()

        for server in g.ALL_SERVERS:
            item = ServerListItem(server, self)
            item.setData(Qt.UserRole, server.num)

        g.SERVER_LIST.widget().update()


class ServerListItem(QListWidgetItem):
    def __init__(self, server, parent=None):
        super(ServerListItem, self).__init__("", parent)
        self.server = server
        self.setSizeHint(QSize(0, 40))

        self.listWidget().setItemWidget(self, ServerListWidget(self.server, self))


class ServerListWidget(QWidget):
    def __init__(self, server, listItem, parent=None):
        super(ServerListWidget, self).__init__(parent)
        self.item = listItem

        # Initialize rects for each server's name, color and active/total text
        self.rect = QRect(0, 0, listItem.listWidget().size().width() - 2, listItem.sizeHint().height())
        # self.tallyRect = self.rect.marginsRemoved(QMargins(40, 10, 10, 10))
        self.indicatorRect = QRect(2, 2, 18, 18)
        self.nameRect = self.rect.marginsRemoved(QMargins(24, -2, 0, 17))
        self.textRect = self.rect.marginsRemoved(QMargins(2, 22, 2, -1))

        self.updateRects()

        self.server = server
        self.server.predWidget = self

    def resizeEvent(self, e):
        self.rect.setSize(e.size())
        self.rect.adjust(0, 0, -2, 0)
        self.updateRects()

    def updateRects(self):
        # QMargins(left, top, right, bottom)
        # self.tallyRect = self.rect.marginsRemoved(QMargins(40, 10, 10, 10))
        self.indicatorRect = QRect(2, 2, 18, 18)
        self.nameRect = self.rect.marginsRemoved(QMargins(24, -2, 0, 17))
        self.textRect = self.rect.marginsRemoved(QMargins(2, 22, 2, -1))

    def wheelEvent(self, e):
        if g.EDIT_MODE:
            if e.angleDelta().y() > 0:
                self.server.headTotal += 1
                self.update()
            elif e.angleDelta().y() < 0:
                self.server.headTotal -= 1
                self.update()

            g.SERVER_LIST.widget().pred.calculate_choice()
        else:
            e.ignore()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setPen(QPen(Qt.black, 1, Qt.SolidLine))
        p.setBrush(QBrush(self.server.color, Qt.SolidPattern))
        p.drawRoundedRect(self.indicatorRect, 2, 2)

        g.FONT_SERVERLIST.setPointSize(15)
        p.setFont(g.FONT_SERVERLIST)
        p.drawText(self.nameRect, (Qt.AlignLeft | Qt.AlignTop), self.server.name)

        g.FONT_SERVERLIST.setPointSize(13)
        p.setFont(g.FONT_SERVERLIST)
        if g.COUNT_MODE == "heads":
            p.drawText(self.textRect, (Qt.AlignLeft | Qt.AlignBottom), "Active:" + str(self.server.headActive))
            p.drawText(self.textRect, (Qt.AlignRight | Qt.AlignBottom), "Total:" + str(self.server.headTotal))
        else:
            p.drawText(self.textRect, (Qt.AlignLeft | Qt.AlignBottom), "Active:" + str(self.server.active))
            p.drawText(self.textRect, (Qt.AlignRight | Qt.AlignBottom), "Total:" + str(self.server.total))

    def editServer(self):
        curr = g.ALL_SERVERS[self.item.data(Qt.UserRole)]

        if not curr:
            return print("invalid selection")

        txt, ok = QInputDialog().getText(self, "Rename Server", "Name:", QLineEdit.Normal, curr.name)

        if not ok or txt == "":
            return print("type something!")

        for server in g.ALL_SERVERS:
            if server.name == txt:
                return print("duplicate")

        g.ALL_SERVERS[curr.num].name = txt
        g.SERVER_LIST.widget().servList.populate_servers()

    def editServerTotal(self):
        curr = g.ALL_SERVERS[self.item.data(Qt.UserRole)]

        if not curr:
            return print("invalid selection")

        inNum, ok = QInputDialog().getInt(self, "Edit Server's Total", "Total:", curr.total)

        if not ok:
            return print("type something!")

        # for server in g.ALL_SERVERS:
        # 	if server.name == txt : return print("duplicate")

        if g.COUNT_MODE == "heads":
            g.ALL_SERVERS[curr.num].headTotal = inNum
        else:
            g.ALL_SERVERS[curr.num].total = inNum

        g.SERVER_LIST.widget().servList.populate_servers()
        g.SERVER_LIST.widget().pred.calculate_choice()

    def removeServer(self):
        curr = g.ALL_SERVERS[self.item.data(Qt.UserRole)]

        if not curr:
            return print("invalid selection")

        g.ALL_SERVERS[curr.num].deleteServer()
        g.SERVER_LIST.widget().servList.populate_servers()

    def contextMenuEvent(self, event):
        menu = QMenu(g.WINDOW)

        editAct = menu.addAction("Rename")
        editAct.triggered.connect(self.editServer)
        editAct.setStatusTip("Rename the server")

        editTotalAct = menu.addAction("Edit Total")
        editTotalAct.triggered.connect(self.editServerTotal)
        editTotalAct.setStatusTip("Edit this server's seat total")

        deleteAct = menu.addAction("Delete")
        deleteAct.triggered.connect(self.removeServer)
        deleteAct.setStatusTip("Deletes the server")

        menu.exec_(QCursor.pos(), editAct)
