import math
import random
import sqlite3
from datetime import datetime

from qtpy.QtCore import Qt, QRectF, QTimer, QPointF, QTime
from qtpy.QtGui import QPen, QBrush, QCursor, QIcon, QPixmap, QColor
from qtpy.QtWidgets import (QGraphicsItem, QAction, QMenu, QInputDialog)

import core.globals as g


def roundSnap(x, snap=1):
    x /= snap

    if x < 5:
        return int(math.ceil(x)) * snap
    else:
        return int(math.floor(x)) * snap


def formatTime(time):
    tt = datetime.fromtimestamp(time)

    return tt.strftime("%H:%M:%S")


class POS_Table(QGraphicsItem):
    def __init__(self, rect: QRectF, server=None, title="", circ=False, rotation=0.0, parent=None):
        super(POS_Table, self).__init__(parent)
        self.rect = QRectF(rect)
        self.title = title
        self.state = 0
        self.circ = circ
        self.color = g.COLORS["tbl_ready"]
        self.numCustomers = 0
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        if server is not None:
            self.server = g.ALL_SERVERS[server]
            self.serverColor = self.server.color
        else:
            self.server = None
            self.serverColor = Qt.black

        if rotation:
            self.rotate(rotation)

        self.activeTimer = QTimer()
        self.counter = 18000
        self.activeTimer.timeout.connect(self.timerEvent)

    # Method for converting the object into string form (for database storage)
    def __conform__(self, protocol):
        # Try to get the server's index, -1 if not
        try:
            server_num = self.server.num
        except AttributeError:
            server_num = -1

        if protocol is sqlite3.PrepareProtocol:
            return f"{self.rect.left()},{self.rect.top()},{self.rect.width()},{self.rect.height()};{server_num};{self.title};{self.circ};{self.rotation()}"

    # Method to parse the database string back into an object
    @staticmethod
    def parse(db_string: str):
        # Split the different parameters up
        parts = db_string.split(';')
        # Split the rectangle's dimensions up
        rect = parts[0].split(',')
        # Return the parsed object
        return POS_Table(QRectF(float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3])),
                         int(parts[1]),
                         parts[2],
                         parts[3] == "True",
                         float(parts[4]))

    def timerEvent(self):
        self.counter += 1
        self.update(self.rect)

    def boundingRect(self):
        return self.rect

    def gfxRect(self, penWidth=5.0):
        return self.boundingRect().adjusted(penWidth, penWidth, -penWidth, -penWidth)

    def paint(self, painter, option, widget):
        # Draw the table's graphics
        painter.setPen(QPen(self.serverColor, 5, Qt.SolidLine))
        painter.setBrush(QBrush(self.color, Qt.SolidPattern))

        if self.circ:
            painter.drawEllipse(self.gfxRect())
        else:
            painter.drawRoundedRect(self.gfxRect(), 8, 8)

        # Draw the table's title
        painter.setPen(QPen(Qt.black))
        # Get the sizing based on the table's width or height, whichever is least
        s1 = min(self.gfxRect().width(), self.gfxRect().height())
        # The actual font's size
        s2 = s1 / 2.5
        g.FONT_TABLE.setPointSize(s2)
        painter.setFont(g.FONT_TABLE)
        painter.drawText(self.gfxRect(), Qt.AlignCenter, self.title)

        # If the table is occupied
        if self.state == 1:
            # Position counter text
            offset = -self.gfxRect().height() / 1.5

            # If the table is circular, we have less space for text, so make the counter text 20% smaller
            if self.circ:
                s2 *= 0.8
                offset = -self.gfxRect().height() / 1.8

            # Draw counter text
            g.FONT.setPointSize(s2 / 2.2)
            painter.setFont(g.FONT)
            painter.drawText(self.gfxRect().adjusted(0, 0, 0, offset),
                             Qt.AlignCenter, formatTime(self.counter))

    def hoverEnterEvent(self, event):
        self.cycleState(False, True)

    def hoverLeaveEvent(self, event):
        self.cycleState(False, False)

    def mousePressEvent(self, event):
        # On leftclick
        if event.button() == Qt.LeftButton:
            # If in edit mode
            if g.EDIT_MODE:
                # Set the cursor to a closed hand (grabbing)
                self.setCursor(Qt.ClosedHandCursor)
                # "Select" the table (for the built-in graphicsitem functionality)
                self.setSelected(True)
                # Cycle the table to a mouseover state, but not advance the seated status
                self.cycleState(False, True)
            else:
                # Cycle the table, advance its seated status and mouseover
                self.cycleState(True, True)

    def mouseMoveEvent(self, event):
        # If the graphicsitem is selected
        if self.isSelected():
            # Move the object to the event's scene position (the mouse position with the scene as its origin)
            self.movePos(event.scenePos(), 10)

    def mouseReleaseEvent(self, event):
        # If we're currently moving a table
        if event.button() == Qt.LeftButton and g.EDIT_MODE and self.isSelected():
            # Move it one last time to snap it
            self.movePos(event.scenePos(), 10)
            # Unselect it
            self.setSelected(False)
            # Switch the cursor back to a pointing hand
            self.setCursor(Qt.PointingHandCursor)

    def contextMenuEvent(self, event):
        # Make sure edit mode is toggled
        if not g.EDIT_MODE:
            return

        # Make a new menu
        menu = QMenu(g.WINDOW)

        server_menu = QMenu("Server", menu)
        server_menu.setStatusTip("Assign a new server")
        # Iterate through servers
        for server in g.ALL_SERVERS:
            # Create a menu action that represents the server and table
            server_action = Server_Menu_Action(server, self, server_menu)

            # Mark the table's current server as checked
            if self.server == server:
                server_action.setChecked(True)

            # servAct.triggered.connect(server_action.changeServer)
            server_menu.addAction(server_action)

        menu.addMenu(server_menu)

        editAct = menu.addAction("Edit")
        editAct.triggered.connect(self.edit_table)
        editAct.setStatusTip("Edits the table")

        deleteAct = menu.addAction("Delete")
        deleteAct.triggered.connect(self.deleteSelf)
        deleteAct.setStatusTip("Deletes the table")

        menu.exec_(QCursor.pos(), editAct)

    def wheelEvent(self, event):
        if not g.EDIT_MODE:
            return

        if not self.server:
            if len(g.ALL_SERVERS) < 1:
                return

            self.server = g.ALL_SERVERS[0]

        servNum = self.server.num

        if event.delta() > 0:
            servNum += 1

            if servNum >= len(g.ALL_SERVERS):
                servNum = 0

            self.change_server(servNum)
        else:
            servNum -= 1

            if servNum < 0:
                servNum = len(g.ALL_SERVERS) - 1

            self.change_server(servNum)

    # Rotate the object
    def rotate(self, rot):
        # Set the pivot point to the center of the object
        self.setTransformOriginPoint(self.boundingRect().center())
        self.setRotation(rot)

    # Moves this object (snaps to the offset specified)
    def movePos(self, pos, snap=1):
        # Get the graphicsitem ready to change visually
        self.prepareGeometryChange()

        # Initialize a stored rotation var as 0
        storRot = 0

        # If the current rotation is not 0
        if self.rotation() != 0:
            # Store the current rotation
            storRot = self.rotation()
            # Rotate the object to 0 degrees (for fixing the moveTo function to the same axis as other objects)
            self.rotate(0)

        # Figure out what the X and Y will be (rounded to the snap offset)
        x, y = pos.x(), pos.y()
        x, y = (roundSnap(x, snap) - (self.rect.width() / 2),
                roundSnap(y, snap) - (self.rect.height() / 2))
        xy = QPointF(x, y)
        self.rect.moveTo(xy)
        # self.setPos(self.rect.topLeft())

        # Set the rotation back to what it was when we started moving
        self.rotate(storRot)

    def deleteSelf(self):
        g.SCENE.removeItem(self)
        del self

    def edit_table(self):
        from core.dialogs import TableDialog
        TableDialog(self.rect, parent=g.WINDOW, item=self)

    def change_server(self, server: int):
        self.prepareGeometryChange()

        if server is None:
            self.server = None
            self.serverColor = Qt.black

            return

        # We can't change to the server we already have
        # if server == self.server.num:
        #     return

        oldServ = self.server
        self.server = g.ALL_SERVERS[server]
        self.serverColor = self.server.color

        if self.state == 1:
            oldServ.headActive -= self.numCustomers
            oldServ.headTotal -= self.numCustomers
            oldServ.total -= 1
            oldServ.active -= 1
            # if oldServ.predWidget is not None:
            # 	oldServ.predWidget.update()

            self.server.headActive += self.numCustomers
            self.server.headTotal += self.numCustomers
            self.server.total += 1
            self.server.active += 1
            # if self.server.predWidget is not None:
            # 	self.server.predWidget.update()

            # g.SERVER_LIST.widget().servList.update()
            g.SERVER_LIST.widget().servList.populate_servers()
            g.SERVER_LIST.widget().pred.calculate_choice()

    def cycleState(self, advance, mouseover, override=-1):
        self.prepareGeometryChange()

        if self.isSelected():
            mouseover = True

        # If the override is set, set the state to that
        if override > -1:
            self.state = override

        # Advance the state if set
        if advance:
            if self.state >= 2:
                self.state = 0
            else:
                self.state += 1

        # If the state is "ready" or override is set
        if self.state == 0 or override != -1:
            if mouseover:
                self.color = g.COLORS["tbl_msoready"]
            else:
                self.color = g.COLORS["tbl_ready"]
        # If the state is "sat"
        elif self.state == 1:
            if advance:
                # Prompt user for party size
                inputDialog = QInputDialog(flags=Qt.WindowStaysOnBottomHint)
                num, ok = inputDialog.getInt(g.WINDOW, "Size", "Customers:", 2, 1, 100, 1)

                # Input was entered and the table's server exists
                if ok and self.server is not None:
                    self.numCustomers = num
                    # Start the time counter
                    self.activeTimer.start(1000)
                    self.server.headActive += self.numCustomers
                    self.server.headTotal += self.numCustomers
                    self.server.total += 1
                    self.server.active += 1
                    # Update the server's list item
                    self.server.predWidget.update()

                    mouseover = False

                    # Log this table as a recent seating so overflow can calculate
                    g.RECENTS.append({"num": self.numCustomers, "time": QTime.currentTime()})

                    # Recalculate overflow and server prediction
                    g.SERVER_LIST.widget().pred.calculate_overflow()
                    g.SERVER_LIST.widget().pred.calculate_choice()
                else:
                    self.state = 0
                    self.color = g.COLORS["tbl_ready"]
                    return print("error seating table / no server set")

            if mouseover:
                self.color = g.COLORS["tbl_msoactive"]
            else:
                self.color = g.COLORS["tbl_active"]
        # If the state is "vacant"
        else:
            if advance:
                # Stop the time counter and reset to 0:0:0
                self.activeTimer.stop()
                self.counter = 18000

                # Table's server exists
                if self.server is not None:
                    self.server.headActive -= self.numCustomers
                    self.server.active -= 1
                    # Update the server's list item
                    self.server.predWidget.update()

                    self.numCustomers = 0

                    # Recalculate server prediction
                    g.SERVER_LIST.widget().pred.calculate_choice()

            if mouseover:
                self.color = g.COLORS["tbl_msovacant"]
            else:
                self.color = g.COLORS["tbl_vacant"]


class Server_Menu_Action(QAction):
    def __init__(self, server, table, parent=None):
        super(Server_Menu_Action, self).__init__(server.name, parent)
        self.table = table
        self.server = server
        self.setCheckable(True)
        pix = QPixmap(12, 12)
        pix.fill(server.color)
        self.setIcon(QIcon(pix))

        def on_clicked():
            self.table.change_server(self.server.num)

        self.triggered.connect(on_clicked)


class POS_Server:
    def __init__(self, name):
        self.name = name
        # Set the server's internal index to the last index of all servers
        self.num = len(g.ALL_SERVERS)
        self.headActive = 0
        self.headTotal = 0
        self.active = 0
        self.total = 0
        # Refers to this server's listitemwidget on the visual server list
        self.predWidget = None

        # Attempt to set the server's color to what's in the global server colors at their index
        try:
            self.color = g.SERVER_COLORS[self.num]
        # Not enough colors? set it to a random one
        except IndexError:
            self.color = QColor.fromHsv(random.randint(0, 359), random.randint(128, 255), random.randint(110, 178))

        # Add the new server to the list of all servers
        g.ALL_SERVERS.append(self)

        # If there's only 1 server (this one), assign all tables to be served by self
        if len(g.ALL_SERVERS) == 1:
            for tbl in g.SCENE.items():
                if type(tbl) is POS_Table:
                    tbl.change_server(self.num)

        # Let the server predictor calculate who should get the next table
        g.SERVER_LIST.widget().pred.calculate_choice()

    def deleteServer(self):
        try:
            # Remove the server from the list of all servers
            g.ALL_SERVERS.pop(self.num)
        # Server doesn't exist in the list or its empty, return
        except IndexError:
            return print("Fatal error!", "IndexError deleting a server")

        # If this is the only server
        if len(g.ALL_SERVERS) == 0:
            print("only server")
            # Iterate through all tables and change their server to None
            for tbl in g.SCENE.items():
                if type(tbl) is POS_Table:
                    tbl.change_server(None)

        # If this isn't the last server in the list
        elif self.num != len(g.ALL_SERVERS):
            # Iterate through all servers with indexes after the removed one
            for server in g.ALL_SERVERS[self.num:]:
                # The server list decremented all indexes, so we need to decrement our index variable
                # on all of these servers
                server.num -= 1
                # Update their color
                try:
                    server.color = g.SERVER_COLORS[server.num]
                except IndexError:
                    server.color = QColor.fromHsv(random.randint(0, 359),
                                                  random.randint(128, 255),
                                                  random.randint(110, 178))

                # Iterate through all tables
                for tbl in g.SCENE.items():
                    if type(tbl) is POS_Table:
                        # If this table is served by the removed server or the iterated server
                        if tbl.server == server or tbl.server == self:
                            tbl.change_server(server.num)
                        elif tbl.server == self:
                            tbl.change_server(self.num - 1)

        # This is the last server in the list (but still multiple servers)
        else:
            # Iterate tables with this server
            for tbl in g.SCENE.items():
                if type(tbl) is POS_Table:
                    if tbl.server == self:
                        tbl.change_server(self.num - 1)
                        # try:
                        #     print("changed back 1")
                        # except IndexError:
                        #     tbl.change_server(None)

        # self = None
        del self

        g.SERVER_LIST.widget().pred.calculate_choice()
        g.SERVER_LIST.widget().servList.populate_servers()
