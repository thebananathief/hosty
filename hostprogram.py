import sqlite3 as sql
import sys

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import core.globals as g
from core.dialogs import SettingsDialog, TableDialog, FloorplanDialog
from core.objects import POS_Server, POS_Table
from docks.resDock import ResList_Dock
from docks.servDock import ServList_Dock


# Menu item for each recent floorplan
class FloorplanAction(QAction):
    # Init with the floorplan in a variable
    def __init__(self, plan_id, title, parent=None):
        super(FloorplanAction, self).__init__(title, parent)

        def on_clicked():
            # Load the stored layout
            g.VIEW.load_floorplan(plan_id)

        self.triggered.connect(on_clicked)


class MainToolBar(QToolBar):
    def __init__(self, parent=None):
        super(MainToolBar, self).__init__(parent)
        self.setIconSize(QSize(16, 16))

        # Layout menu button
        self.act_floorplan = self.addAction(QIcon("resources/layout_content.png"), "Floorplan Menu")
        self.act_floorplan.setToolTip("Opens the floorplan menu")
        self.act_floorplan.setStatusTip("Opens the floorplan menu")

        # Table / Head count mode swap button
        self.act_swapMode = self.addAction(QIcon("resources/user.png"), "Swap Heads/Tables")
        self.act_swapMode.setToolTip("Swaps between head count or table count modes")
        self.act_swapMode.setStatusTip("Swaps between head count or table count modes")

        # Settings menu button
        self.act_settings = self.addAction(QIcon("resources/cog.png"), "Settings")
        self.act_settings.setToolTip("Opens the settings menu")
        self.act_settings.setStatusTip("Opens the settings menu")

        # Editing mode toggle button
        self.act_editToggle = self.addAction(QIcon("resources/wrench.png"), "Edit Mode")
        self.act_editToggle.setToolTip("Toggles edit mode")
        self.act_editToggle.setStatusTip("Toggles edit mode")
        self.act_editToggle.setCheckable(True)

        # Add rectangular table button (only shows on edit mode)
        self.act_addRectTbl = self.addAction(QIcon("resources/rect.png"), "Add Rectangle Table")
        self.act_addRectTbl.setToolTip("Adds a rectangle table into the layout")
        self.act_addRectTbl.setStatusTip("Adds a rectangle table into the layout")
        self.act_addRectTbl.setCheckable(True)
        self.act_addRectTbl.setVisible(False)

        # Add circular table button (only shows on edit mode)
        self.act_addCircTbl = self.addAction(QIcon("resources/ellipse.png"), "Add Elliptical Table")
        self.act_addCircTbl.setToolTip("Adds an elliptical table into the layout")
        self.act_addCircTbl.setStatusTip("Adds an elliptical table into the layout")
        self.act_addCircTbl.setCheckable(True)
        self.act_addCircTbl.setVisible(False)


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle("Host Program")

        self.rubberBandRect = QRect(1, 0, 0, 0)
        self.toolbar = self.create_toolbar()
        self.addToolBar(Qt.RightToolBarArea, self.toolbar)
        self.statusBar().show()

    # Create and link the toolbar buttons with their cooresponding functions and return it
    def create_toolbar(self) -> QToolBar:
        toolbar = MainToolBar(self)

        toolbar.act_floorplan.triggered.connect(self.create_planmenu)
        toolbar.act_swapMode.triggered.connect(self.swap_seatmode)

        # Create the settings menu window
        def create_settingsmenu():
            SettingsDialog(self)

        toolbar.act_settings.triggered.connect(create_settingsmenu)
        toolbar.act_editToggle.triggered.connect(self.toggle_editmode)
        toolbar.act_addRectTbl.triggered.connect(self.rubberband_createobject)
        toolbar.act_addCircTbl.triggered.connect(self.rubberband_createobject)

        return toolbar

    # Create the layout menu at the cursor position
    def create_planmenu(self):
        # Alias the recents menu and clear it
        m = QMenu(self)
        m.clear()

        # If we have recents to iterate through
        if len(g.recentFloorplans) > 0:
            # Query floorplans table for the plan's name
            con = sql.connect("hostprogram.db")
            con.row_factory = sql.Row
            cur = con.cursor()
            plansList = cur.execute("SELECT plan_id, name FROM floorplans").fetchall()
            con.close()

            for row in plansList:
                plan_id = int(row["plan_id"])
                if str(plan_id) in g.recentFloorplans:
                    # Add each recent floorplan to the menu
                    new = FloorplanAction(plan_id, row["name"], m)
                    m.addAction(new)

        # No recents, display so
        else:
            new = QAction("No Recent Plans", m)
            m.addAction(new)

        # Creates a floorplan dialog menu
        def create_layoutdialog():
            FloorplanDialog(self)

        m.addSeparator()
        # The floorplan menu button at the bottom of the recents menu
        act_layoutdialog = m.addAction("Floorplan Menu")
        act_layoutdialog.triggered.connect(create_layoutdialog)

        # Show the menu
        m.exec_(QCursor.pos(), act_layoutdialog)

    def toggle_editmode(self, s):
        # Toggle is on
        if s:
            # Start edit mode, make the editing label on the scene, and show the table buttons
            g.EDIT_MODE = True
            g.SCENE.editLabel.setVisible(True)
            self.toolbar.act_addRectTbl.setVisible(True)
            self.toolbar.act_addCircTbl.setVisible(True)

        # Toggle is off
        else:
            g.EDIT_MODE = False
            g.SCENE.editLabel.setVisible(False)
            self.toolbar.act_addRectTbl.setVisible(False)
            self.toolbar.act_addCircTbl.setVisible(False)

    # Swap seating counts between heads / tables
    def swap_seatmode(self):
        # Confirm with the user
        ok = QMessageBox().question(self, "Head/Table Count Mode",
                                    "Do you wish to swap the counting mode?\n"
                                    "This will reset the layout and set all servers to 0",
                                    QMessageBox.No, QMessageBox.Yes)

        # User pressed YES
        if ok == QMessageBox.Yes:
            # If we're on headcount, switch to table count and change the icon of the swap button
            if g.COUNT_MODE == "heads":
                g.COUNT_MODE = "tables"
                self.toolbar.act_swapMode.setIcon(QIcon("resources/shape_square.png"))
            # Vice versa
            else:
                g.COUNT_MODE = "heads"
                self.toolbar.act_swapMode.setIcon(QIcon("resources/user.png"))

            # Reset all server's counts
            for server in g.ALL_SERVERS:
                server.headActive = 0
                server.headTotal = 0
                server.active = 0
                server.total = 0

            # If we reset while a table was sat, add that table to its server's active count
            # (depending on head or table count)
            for tbl in g.SCENE.items():
                if type(tbl) is POS_Table and tbl.state == 1:
                    if g.COUNT_MODE == "heads":
                        tbl.server.active += tbl.numCustomers
                    else:
                        tbl.server.active += 1

            g.RECENTS.clear()
            g.SERVER_LIST.widget().servList.update()
            g.SERVER_LIST.widget().pred.calculate_choice()

    # We created or canceled creating a table, set the buttons unchecked/pressed
    def finish_createobject(self):
        self.toolbar.act_addRectTbl.setChecked(False)
        self.toolbar.act_addCircTbl.setChecked(False)
        # g.VIEW.rubberBandChanged.disconnect(self.rubberBandUpdate)
        g.VIEW.setDragMode(QGraphicsView.NoDrag)

    # We're currently dragging a box inside the GraphicsView
    def rubberband_update(self, viewportRect):
        # If the drag box is reset (released mouse)
        if viewportRect == QRect(0, 0, 0, 0):
            # Disconnect from this function, so we don't keep running it, and we can reconnect it later
            g.VIEW.rubberBandChanged.disconnect(self.rubberband_update)
            # g.VIEW.setDragMode(QGraphicsView.NoDrag)

            # Depending on which add tbl button was pressed, make a table dialog for rectangular or circular
            if self.toolbar.act_addRectTbl.isChecked():
                TableDialog(self.rubberBandRect, False, g.WINDOW)
            elif self.toolbar.act_addCircTbl.isChecked():
                TableDialog(self.rubberBandRect, True, g.WINDOW)

        # We're still dragging a box
        else:
            self.rubberBandRect = viewportRect

    # Allow dragging boxes in the GraphicsView and connect the update function
    def rubberband_createobject(self):
        # If we're already in drag mode, reset creation mode and dragging, then halt
        if g.VIEW.dragMode() == QGraphicsView.RubberBandDrag:
            self.finish_createobject()
            return

        g.VIEW.setDragMode(QGraphicsView.RubberBandDrag)
        self.rubberBandRect = QRect(1, 0, 0, 0)
        g.VIEW.rubberBandChanged.connect(self.rubberband_update)


class GraphicsScene(QGraphicsScene):
    def __init__(self, parent=None):
        super(GraphicsScene, self).__init__(parent)
        # self.setSceneRect(QRectF(0,0,1,1))
        # We don't utilize the item indexing from GraphicsScene
        self.setItemIndexMethod(QGraphicsScene.NoIndex)

        # Create a label on the scene to indicate edit mode (invisible)
        font = QFont("Calibri", 22)
        self.editLabel = self.addSimpleText("Editing Mode", font)
        self.editLabel.setBrush(QBrush(QColor(255, 255, 255, 230), Qt.SolidPattern))
        self.editLabel.setVisible(False)
        self.editLabel.setPos(25, 25)
        self.editLabel.setZValue(1)

    def recenter(self):
        rect = self.itemsBoundingRect()
        g.VIEW.ensureVisible(rect)


class GraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super(GraphicsView, self).__init__(scene, parent)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setBackgroundBrush(QBrush(g.COLORS["background"], Qt.SolidPattern))
        self.setSceneRect(QRectF(0, 0, 1, 1))

        self.storServ = {
            "servers": [],
            "tables":  {}
        }

    # Populate the server list and fill scene with tables
    @staticmethod
    def add_layout_items(scene: QGraphicsScene, tbl_list: list, servers: int):
        for i in range(servers):
            POS_Server("Server " + str(i + 1))

        # Populate tables
        for table in tbl_list:
            # Use POS_Table's parsing method to convert the database's string to an object
            scene.addItem(POS_Table.parse(table[0]))

    # Resets and stores current server data (and the tables' servers)
    def store_plan(self):
        # Reset the current stored data and store the current servers
        self.storServ = {
            "servers": g.ALL_SERVERS.copy(),
            "tables":  {}
        }

        # Store the current floorplan's tables' servers (the actual tables are still on the main scene)
        # (key is the POS_Table object, value is the server number)
        for item in g.SCENE.items():
            if type(item) is POS_Table:
                if item.server is not None:
                    self.storServ["tables"][item] = item.server.num
                else:
                    self.storServ["tables"][item] = None

    # Restores the server list from the stored list and restores tables from the stored tables
    def restore_plan(self):
        # Restore the server list from the stored list
        g.ALL_SERVERS = self.storServ["servers"].copy()

        # Change the servers for the main scene's tables to be what they were previous to the preview
        for tbl in self.storServ["tables"]:
            tbl.change_server(self.storServ["tables"][tbl])

        # Update the visual server list widget
        g.SERVER_LIST.widget().servList.populate_servers()

        # Let the server predictor calculate who should get the next table
        g.SERVER_LIST.widget().pred.calculate_choice()

        # Set the current scene to the main scene
        self.setScene(g.SCENE)

    # Loads a floorplan onto the GraphicsView
    def load_floorplan(self, plan_id: int, temp=False):
        # Query for requested plan tables
        con = sql.connect("hostprogram.db")
        # con.row_factory = sql.Row
        cur = con.cursor()
        server_count = cur.execute("SELECT server_count FROM floorplans WHERE plan_id = ?", str(plan_id)).fetchone()[0]
        plan_tables = cur.execute("SELECT data FROM plan_tables WHERE plan_id = ?", str(plan_id)).fetchall()
        con.close()

        # If the floorplan doesn't exist, halt
        if cur.rowcount == 0:
            return

        # Free up all server objects
        # for i in g.ALL_SERVERS:
        # i = None
        # del i

        # Clears the server list
        g.ALL_SERVERS.clear()

        # If in preview mode
        if temp:
            # Create a new scene
            tempScene = GraphicsScene()

            # Create a label indicating this is a preview floorplan
            font = QFont("Calibri", 22)
            tempScene.previewLabel = tempScene.addSimpleText("Preview Mode", font)
            tempScene.previewLabel.setBrush(QBrush(QColor(230, 230, 230, 230), Qt.SolidPattern))
            tempScene.previewLabel.setPos(25, 25)
            tempScene.previewLabel.setZValue(1)

            # Populate the preview scene with tables and servers
            self.add_layout_items(tempScene, plan_tables, server_count)

            # Set it to be viewed
            self.setScene(tempScene)

        # Fully loading a floorplan onto the main scene
        else:
            # Clear tables
            for item in g.SCENE.items():
                if type(item) is POS_Table:
                    g.SCENE.removeItem(item)

            # Plan is already in recents
            if plan_id in g.recentFloorplans:
                # Remove it from recents (so that the order is correct)
                # idx = g.recentFloorplans.index(plan_id)
                # del g.recentFloorplans[idx]
                g.recentFloorplans.remove(str(plan_id))

            # Add plan to the recents
            g.recentFloorplans.insert(0, str(plan_id))

            # Too many recents, delete the oldest one
            if len(g.recentFloorplans) > 5:
                del g.recentFloorplans[5]

            # Update the persistant floorplans settings data (for persisting the recents)
            g.SETTINGS.setValue("data/recentFloorplans", g.recentFloorplans)
            g.SETTINGS.sync()

            # Populate the main scene with tables and servers
            self.add_layout_items(g.SCENE, plan_tables, server_count)

        # Update the visual server list widget
        g.SERVER_LIST.widget().servList.populate_servers()

        # Make sure the scene is in its static position
        g.SCENE.recenter()

    def sizeHint(self):
        return QSize(900, 700)


if __name__ == "__main__":
    # Setup app name
    # Needed for QSettings to work properly
    QCoreApplication.setOrganizationName("Navimode")
    QCoreApplication.setApplicationName("Hosty")

    # Setup default settings
    g.SETTINGS = QSettings()

    # No value set in persistant settings
    if not g.SETTINGS.value("b_preview"):
        # Set the default value
        g.SETTINGS.setValue("b_preview", 0)
    if not g.SETTINGS.value("settings/fullhour"):
        g.SETTINGS.setValue("settings/fullhour", 0)
    if not g.SETTINGS.value("settings/minResTime"):
        g.SETTINGS.setValue("settings/minResTime", QTime(0, 0))
    if not g.SETTINGS.value("settings/maxResTime"):
        g.SETTINGS.setValue("settings/maxResTime", QTime(23, 59))
    if not g.SETTINGS.value("settings/overflowMultiplier"):
        g.SETTINGS.setValue("settings/overflowMultiplier", 1)
    if not g.SETTINGS.value("data/overflowRules"):
        g.SETTINGS.setValue("data/overflowRules", g.overflowRules)
    if not g.SETTINGS.value("data/recentFloorplans"):
        g.SETTINGS.setValue("data/recentFloorplans", g.recentFloorplans)

    # Settings are established, set the floorplan and overflow rules tables
    g.overflowRules = g.SETTINGS.value("data/overflowRules")
    g.recentFloorplans = g.SETTINGS.value("data/recentFloorplans")

    # Scales the application for high DPI monitors
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    # Setup application window and theme
    g.APP = QApplication(sys.argv)
    g.APP.setStyle("fusion")

    # Setup main window and docks
    g.WINDOW = MainWindow()

    g.SERVER_LIST = ServList_Dock(g.WINDOW)
    g.RES_LIST = ResList_Dock(g.WINDOW)

    g.WINDOW.addDockWidget(Qt.RightDockWidgetArea, g.RES_LIST)
    g.WINDOW.addDockWidget(Qt.RightDockWidgetArea, g.SERVER_LIST)

    # Setup the floorplan viewer
    g.SCENE = GraphicsScene()
    g.VIEW = GraphicsView(g.SCENE, g.WINDOW)
    g.VIEW.setCursor(Qt.ArrowCursor)

    g.WINDOW.setCentralWidget(g.VIEW)

    # Show the application and maximize it
    # g.WINDOW.show()
    # g.WINDOW.showFullScreen()
    g.WINDOW.showMaximized()

    # Stops the application as soon as the user closes it
    sys.exit(g.APP.exec_())
