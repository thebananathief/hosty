# import pickle
import random
import sqlite3 as sql

from qtpy.QtCore import Qt, QRectF, QTime, QDate, QRegExp
from qtpy.QtGui import QColor, QIcon, QPixmap, QRegExpValidator, QBrush, QStandardItemModel, \
    QStandardItem
from qtpy.QtWidgets import *

import core.globals as g
import core.objects as o
from core.globals import get_path, create_connection


class ReservationDialog(QDialog):
    def __init__(self, parent=None, index=None):
        super(ReservationDialog, self).__init__(parent, flags=(Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint))
        self.setWindowTitle("Make Reservation")
        self.setWindowIcon(QIcon(get_path("user.png")))
        self.setSizeGripEnabled(False)
        self.setModal(True)

        # If a reservation index is supplied, set the editRes to represent its reservation data
        self.editRes = None
        if index is not None:
            # Query reservations table for the reservation that matches this id
            con = create_connection()
            con.row_factory = sql.Row
            cur = con.cursor()
            self.editRes = cur.execute("SELECT * FROM reservations WHERE res_id = ?", index).fetchone()
            con.close()

        # Set up name box
        self.nameLabel = QLabel("Name:", self)

        self.nameBox = QLineEdit(self)
        self.nameBox.setMaxLength(15)
        self.nameBox.setToolTip("Name of the reservation")

        # Set up party size box
        self.partySizeBox = QSpinBox(self)
        self.partySizeBox.setRange(1, 99)
        self.partySizeBox.setValue(2)
        self.partySizeBox.setToolTip("Party size of the reservation (how many customers)")

        # Set up arrival time box
        self.arrivalTimeLabel = QLabel("Time:", self)

        self.arrivalTimeBox = QTimeEdit(self)
        self.arrivalTimeBox.setTimeRange(g.SETTINGS.value("settings/minResTime"),
                                         g.SETTINGS.value("settings/maxResTime"))
        self.arrivalTimeBox.setTime(QTime.currentTime())
        self.arrivalTimeBox.setToolTip("Time the reservation is scheduled")

        # Set the arrival time's display format to 24 hour or 12 hour
        if bool(g.SETTINGS.value("settings/fullhour")):
            self.arrivalTimeBox.setDisplayFormat("hh:mm")
        else:
            self.arrivalTimeBox.setDisplayFormat("hh:mm A")

        # Set up the phone number box
        self.phoneNumBox = QLineEdit(self)
        self.phoneNumBox.setMaxLength(10)
        # Regular expression to allow only 10 digits
        rx = QRegExp("[0-9]{10}")
        self.phoneNumBox.setValidator(QRegExpValidator(rx, self.phoneNumBox))
        self.phoneNumBox.setPlaceholderText("1231231234")
        self.phoneNumBox.setToolTip("Phone number of the reservation")

        # Set up the notes box
        self.notesBox = QLineEdit(self)
        self.notesBox.setMaxLength(15)
        self.notesBox.setPlaceholderText("NSN, BluRm, etc")
        self.notesBox.setToolTip("Special instructions for the reservation")

        # Set up the calendar widget (popped up by the arrival date box)
        self.calendar = QCalendarWidget(self)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.SingleLetterDayNames)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setGridVisible(True)

        # Update the reservation list to the selected date
        # (so that we can check the day's reservations as we're making a new one)
        def on_changed_date(date):
            g.RES_LIST.widget().update_date(date)

        # Set up the arrival date box
        self.arrivalDateBox = QDateEdit(self)
        self.arrivalDateBox.setCalendarPopup(True)
        self.arrivalDateBox.setCalendarWidget(self.calendar)
        self.arrivalDateBox.setDisplayFormat("dddd - MMM / dd / yyyy")
        self.arrivalDateBox.setAlignment(Qt.AlignCenter)
        self.arrivalDateBox.setDate(g.RES_LIST.widget().resDateEdit.date())
        self.arrivalDateBox.dateChanged.connect(on_changed_date)
        self.arrivalDateBox.setToolTip("Arrival date of the reservation")

        # Default back to today and update the reservation list
        def on_clicked_showtoday():
            self.arrivalDateBox.setDate(QDate.currentDate())
            g.RES_LIST.widget().update_date(QDate.currentDate())

        # Set up the show today button
        self.showTodayButton = QToolButton(self)
        self.showTodayButton.setIcon(QIcon(get_path("arrow_refresh.png")))
        self.showTodayButton.clicked.connect(on_clicked_showtoday)
        self.showTodayButton.setToolTip("Resets the selected date to today")

        dateLayout = QHBoxLayout()
        dateLayout.addWidget(self.arrivalDateBox)
        dateLayout.addWidget(self.showTodayButton)

        # Color to show the user which field they still need to enter
        invalidGfx = QGraphicsColorizeEffect(self)
        invalidGfx.setColor(Qt.red)

        # Make a new reservation and add it to our database
        def add_reservation() -> bool:
            # If name input is invalid
            if self.nameBox.text() == "":
                # Color the label and outline the box with the invalid color
                self.nameLabel.setGraphicsEffect(invalidGfx)
                self.nameBox.setGraphicsEffect(invalidGfx)

                # Reject reservation
                return False

            # If open time is greater than the close time
            # (restaurant opens during day, closes after midnight)
            # e.g. open 14:00 > close 01:00
            # open < close is handled directly by input validation on the time input
            if g.SETTINGS.value("settings/minResTime") > g.SETTINGS.value("settings/maxResTime"):
                # If the input time is greater than open time or less than close time
                if g.SETTINGS.value("settings/minResTime") > \
                        self.arrivalTimeBox.time() > \
                        g.SETTINGS.value("settings/maxResTime"):
                    # Color the label and outline the box with the invalid color
                    self.arrivalTimeLabel.setGraphicsEffect(invalidGfx)
                    self.arrivalTimeBox.setGraphicsEffect(invalidGfx)

                    # Reject reservation
                    return False

            # If a reservation was supplied (editing an existing one)
            if index is not None:
                # Update the reservation in the database with its new data
                con = create_connection()
                cur = con.cursor()
                cur.execute(
                    "UPDATE reservations SET (date, time, name, size, phone, note) = (date(?), time(?), ?, ?, ?, ?) WHERE res_id = ?",
                    (self.arrivalDateBox.date().toString(Qt.ISODate),
                     self.arrivalTimeBox.time().toString(Qt.ISODate),
                     self.nameBox.text(),
                     str(self.partySizeBox.value()),
                     self.phoneNumBox.text(),
                     self.notesBox.text(),
                     index))
                con.commit()
                con.close()
            else:
                # Insert a new reservation into the database
                con = create_connection()
                cur = con.cursor()
                cur.execute("INSERT INTO reservations (date, time, name, size, phone, note) VALUES(?, ?, ?, ?, ?, ?)",
                            (self.arrivalDateBox.date().toString(Qt.ISODate),
                             self.arrivalTimeBox.time().toString(Qt.ISODate),
                             self.nameBox.text(),
                             str(self.partySizeBox.value()),
                             self.phoneNumBox.text(),
                             self.notesBox.text()))
                con.commit()
                con.close()

            # Refresh the visual list of reservations
            g.RES_LIST.widget().resList.populate_reservations(self.arrivalDateBox.date())

            return True

        def on_clicked_add():
            add_reservation()

        def on_clicked_addclose():
            if add_reservation():
                self.accept()

        self.addButton = QPushButton(QIcon(get_path("add.png")), "Add", self)
        self.addButton.setAutoDefault(False)
        self.addButton.clicked.connect(on_clicked_add)
        self.addButton.setToolTip("Adds the reservation without closing this dialog")

        self.addCloseButton = QPushButton(QIcon(get_path("accept.png")), "Add and Close", self)
        self.addCloseButton.setDefault(True)
        self.addCloseButton.clicked.connect(on_clicked_addclose)
        self.addCloseButton.setToolTip("Adds the reservation and closes this dialog")

        self.buttonBox = QDialogButtonBox()
        self.buttonBox.addButton(self.addCloseButton, QDialogButtonBox.AcceptRole)
        self.buttonBox.addButton(self.addButton, QDialogButtonBox.ApplyRole)

        # We are editing a reservation, set the dialog's inputs
        if self.editRes is not None:
            self.set_reservation(self.editRes)

        layout = QFormLayout(self)

        layout.setSpacing(g.DIA_SPACING)
        # layout.setMargin(g.DIA_MARGIN)

        layout.addRow(dateLayout)
        layout.addRow(self.nameLabel, self.nameBox)
        layout.addRow("Size:", self.partySizeBox)
        layout.addRow(self.arrivalTimeLabel, self.arrivalTimeBox)
        layout.addRow("Phone:", self.phoneNumBox)
        layout.addRow("Notes:", self.notesBox)
        layout.addRow(self.buttonBox)

        self.setLayout(layout)
        self.show()

    def set_reservation(self, res: sql.Row):
        self.setWindowTitle("Edit Reservation")
        self.nameBox.setText(res["name"])
        self.partySizeBox.setValue(res["size"])
        self.arrivalTimeBox.setTime(QTime.fromString(res["time"], "hh:mm"))
        self.phoneNumBox.setText(res["phone"])
        self.notesBox.setText(res["note"])
        self.arrivalDateBox.setDate(QDate.fromString(res["date"], Qt.ISODate))
        self.addButton.setVisible(False)
        self.addCloseButton.setText("Edit")


class TableDialog(QDialog):
    def __init__(self, startRect, circ=False, parent=None, item=None):
        super(TableDialog, self).__init__(parent, flags=(Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint))
        self.setWindowTitle("Create Table")
        self.setWindowIcon(QIcon(get_path("shape_square.png")))
        self.setSizeGripEnabled(False)
        self.setModal(True)

        self.item = item
        self.startRect = startRect

        self.titleBox = QLineEdit(self)

        self.wSpinBox = QSpinBox(self)
        self.wSpinBox.setRange(25, 999999)
        self.wSpinBox.setSingleStep(25)
        self.wSpinBox.setValue(startRect.width())

        self.hSpinBox = QSpinBox(self)
        self.hSpinBox.setRange(25, 999999)
        self.hSpinBox.setSingleStep(25)
        self.hSpinBox.setValue(startRect.height())

        self.rotSpinBox = QSpinBox(self)
        self.rotSpinBox.setRange(-180, 180)
        self.rotSpinBox.setSingleStep(5)

        self.circCheckBox = QCheckBox(self)

        # Create the server dropdown to select a server at table creation
        self.serverBox = QComboBox()
        self.serverBox.setVisible(False)
        # Populate the dropdown with servers
        for server in g.ALL_SERVERS:
            pix = QPixmap(12, 12)
            pix.fill(server.color)
            # Each item's userData is the server index
            self.serverBox.addItem(QIcon(pix), server.name, server.num)

        def on_closed_menu():
            g.WINDOW.finish_createobject()

        self.finished.connect(on_closed_menu)

        button_ok = QPushButton(QIcon(get_path("accept.png")), "Create", self)
        button_ok.setAutoDefault(True)

        # Editing an existing table
        if self.item:
            button_ok.setText("Edit")
            self.titleBox.setText(self.item.title)
            self.rotSpinBox.setValue(self.item.rotation())
            self.circCheckBox.setChecked(self.item.circ)
            if self.item.server:
                # Set the server selector's index to the table's server's index
                self.serverBox.setCurrentIndex(self.item.server.num)
        # Making a new table
        else:
            self.rotSpinBox.setValue(0)
            self.circCheckBox.setChecked(circ)

        def on_clicked_ok():
            rect = QRectF(startRect.x(), startRect.y(), self.wSpinBox.value(), self.hSpinBox.value())

            # Get the server index to set the table to
            s = self.serverBox.currentData()
            # If no servers, set to -1
            if s is None:
                s = -1

            if self.item:
                self.item.title = self.titleBox.text()
                self.item.prepareGeometryChange()
                self.item.rect = rect
                self.item.rotate(self.rotSpinBox.value())
                self.item.circ = self.circCheckBox.isChecked()

                if s is not None:
                    self.item.change_server(s)
            else:
                if self.circCheckBox.isChecked():
                    g.SCENE.addItem(
                        o.POS_Table(QRectF(rect), s, self.titleBox.text(), True))
                else:
                    g.SCENE.addItem(
                        o.POS_Table(QRectF(rect), s, self.titleBox.text(), False,
                                    self.rotSpinBox.value()))

            self.accept()

            g.WINDOW.finish_createobject()

        button_ok.clicked.connect(on_clicked_ok)

        layout = QFormLayout()

        layout.setSpacing(g.DIA_SPACING)
        # layout.setMargin(g.DIA_MARGIN)

        layout.addRow("Title:", self.titleBox)
        layout.addRow("W:", self.wSpinBox)
        layout.addRow("H:", self.hSpinBox)
        layout.addRow("Rotation:", self.rotSpinBox)
        layout.addRow("Circular:", self.circCheckBox)
        # Make the dropdown visible if any servers exist
        if len(g.ALL_SERVERS) > 0:
            self.serverBox.setVisible(True)
            layout.addRow("Server:", self.serverBox)

        layout.addRow(button_ok)

        self.setLayout(layout)
        self.exec_()


class FloorplanDialog(QDialog):
    def __init__(self, parent=None):
        super(FloorplanDialog, self).__init__(parent, flags=Qt.WindowCloseButtonHint)
        self.setWindowTitle("Floorplan Menu")
        self.setWindowIcon(QIcon(get_path("layout_content.png")))
        self.setSizeGripEnabled(False)
        self.setModal(True)

        # Populate the stored plan (so that we can restore this plan given we're on a preview
        g.VIEW.store_plan()

        grid = QGridLayout(self)
        grid.setSpacing(g.DIA_SPACING)
        # layout.setMargin(g.DIA_MARGIN)

        category_label = QLabel("Category", self)

        def on_clicked_category(curr: QListWidgetItem):
            if not curr:
                return

            # Clear the current list of floorplans
            plan_list.clear()

            # Alias the server count
            count = curr.data(Qt.UserRole)

            # Query for all floorplans with this server count
            con = create_connection()
            con.row_factory = sql.Row
            cur = con.cursor()
            plans = cur.execute("SELECT * FROM floorplans WHERE server_count = ?", str(count)).fetchall()
            con.close()

            # Iterate all floorplans
            for row in plans:
                # Makes a new floorplan row and sets its data to the plan_id
                plan_item = QListWidgetItem(row["name"])
                plan_item.setData(Qt.UserRole, row["plan_id"])
                plan_list.addItem(plan_item)

        # Create category list
        category_list = QListWidget(self)
        # category_list.setSortingEnabled(True)
        category_list.currentItemChanged.connect(on_clicked_category)

        def create_categories():
            # Clear out the category list
            category_list.clear()

            # Query for all floorplans
            con = create_connection()
            con.row_factory = sql.Row
            cur = con.cursor()
            plans = cur.execute("SELECT * FROM floorplans").fetchall()
            con.close()

            server_counts = []

            # Iterate through all floorplans
            for row in plans:
                # No duplicate numbers
                if row["server_count"] not in server_counts:
                    # Mark that we need a category for this server count
                    server_counts.append(row["server_count"])

            # Sort the list by their counts
            def sort_by_count(d):
                return d

            server_counts.sort(key=sort_by_count)

            # Iterate through the marked category numbers we need to populate
            for num in server_counts:
                # Make a new category row for each number of servers in floorplans
                category_item = QListWidgetItem(str(num) + " Servers")
                category_item.setData(Qt.UserRole, num)
                # Special grammar case for single server
                if num == 1:
                    category_item.setText("1 Server")
                elif num == 0:
                    category_item.setText("No Servers")

                category_list.addItem(category_item)

        create_categories()

        plan_label = QLabel("Floorplans", self)
        plan_lineedit = QLineEdit(self)

        def on_clicked_addplan():
            # Get the input plan name
            txt = plan_lineedit.text()

            # Empty input error
            if txt == "":
                QErrorMessage.showMessage("Type a name for the floorplan in the box on the left.")
                return print("name input error")
            # No servers error
            # if len(g.ALL_SERVERS) < 1:
            #     QErrorMessage.showMessage("Add at least 1 server to the floorplan to save it.")
            #     return print("no servers error")

            # Insert the floorplan into the database
            con = create_connection()
            cur = con.cursor()
            cur.execute("INSERT INTO floorplans (name, server_count) VALUES (?, ?)", (txt, len(g.ALL_SERVERS)))
            # Get the plan id of the floorplan we just added
            plan_id = cur.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Insert all tables into the database
            for tbl in g.SCENE.items():
                if type(tbl) is o.POS_Table:
                    cur.execute("INSERT INTO plan_tables (data, plan_id) VALUES (?, ?)", (tbl, plan_id))

            con.commit()
            con.close()

            # If there's no categories
            if category_list.count() == 0:
                # Re-create them so the newly added floorplan shows up
                create_categories()
                category_list.setCurrentRow(0)

                return print("no categories")

            # The current category's server count (-1 if no category selected)
            category_count = -1
            curr_category = category_list.currentItem()
            if curr_category is not None:
                category_count = category_list.currentItem().data(Qt.UserRole)

            # Amount of servers
            server_count = len(g.ALL_SERVERS)

            # If the current category's server count is not the amount of servers
            if category_count != server_count:
                # Re-create them so any newly added plans show up
                create_categories()
                # Iterate through each category, selecting the one that matches the server count
                for row in range(category_list.count()):
                    category_item = category_list.item(row)
                    if category_item.data(Qt.UserRole) == server_count:
                        category_list.setCurrentItem(category_item)

                return print("swapping category")

            new = QListWidgetItem(txt)
            new.setData(1, txt)
            plan_list.addItem(new)

        button_addplan = QPushButton(QIcon(get_path("add.png")), "Add", self)
        button_addplan.clicked.connect(on_clicked_addplan)

        def on_clicked_rename():
            curr = plan_list.currentItem()

            if not curr:
                return print("invalid selection")

            txt = plan_lineedit.text()
            if txt == "":
                return print("type something!")

            plan_id = curr.data(Qt.UserRole)
            # Update name query
            con = create_connection()
            cur = con.cursor()
            cur.execute("UPDATE floorplans SET name = ? WHERE plan_id = ?", (txt, str(plan_id)))
            con.commit()
            con.close()
            # Update the text of the visual list item
            curr.setText(txt)

        button_rename = QPushButton(QIcon(get_path("pencil.png")), "Rename", self)
        button_rename.clicked.connect(on_clicked_rename)

        def on_clicked_plan(curr: QListWidgetItem):
            # This should never trigger, but if it does, halt
            if not curr:
                return

            # Change the edit line's text to the current floorplan's name
            plan_lineedit.setText(curr.text())

            # If preview mode is checked, temporarily load the selected floorplan
            if checkbox_preview.isChecked():
                g.VIEW.load_floorplan(curr.data(Qt.UserRole), True)

        plan_list = QListWidget(self)
        plan_list.currentItemChanged.connect(on_clicked_plan)

        def on_checked_preview(s: int):
            # Unchecked
            if s == 0:
                # Set the view to the main scene
                g.VIEW.restore_plan()
            # Checked
            else:
                curr = plan_list.currentItem()
                if curr:
                    # Load the currently selected floorplan onto the temporary scene
                    g.VIEW.load_floorplan(curr.data(Qt.UserRole), True)

            g.SETTINGS.setValue("b_preview", s)

        checkbox_preview = QCheckBox("Preview", self)
        checkbox_preview.stateChanged.connect(on_checked_preview)

        x = g.SETTINGS.value("b_preview")
        if x == 0:
            checkbox_preview.setChecked(False)
        else:
            checkbox_preview.setChecked(True)

        def on_clicked_delete():
            curr = plan_list.currentItem()

            if not curr:
                return print("invalid selection")

            plan_id = curr.data(Qt.UserRole)

            # Remove this plan ID from the recents if it exists
            if plan_id in g.recentFloorplans:
                g.recentFloorplans.remove(plan_id)

            # Delete query
            con = create_connection()
            cur = con.cursor()
            cur.execute("DELETE FROM floorplans WHERE plan_id = ?", str(plan_id))
            cur.execute("DELETE FROM plan_tables WHERE plan_id = ?", str(plan_id))
            con.commit()
            con.close()

            # Remove the plan from the category (visually)
            plan_list.takeItem(plan_list.currentRow())

            # If the category is empty now
            if plan_list.count() == 0:
                # Re-create the categories list
                create_categories()

        button_delete = QPushButton(QIcon(get_path("delete.png")), "Delete", self)
        button_delete.clicked.connect(on_clicked_delete)

        def on_clicked_load():
            curr = plan_list.currentItem()

            if not curr:
                return

            # Set the view's scene to the main scene (in case we're in a preview)
            g.VIEW.setScene(g.SCENE)
            # Populate the scene and make servers
            g.VIEW.load_floorplan(curr.data(Qt.UserRole))

            self.accept()

        button_load = QPushButton(QIcon(get_path("accept.png")), "Load", self)
        button_load.setAutoDefault(True)
        button_load.clicked.connect(on_clicked_load)

        def on_closed_menu():
            if checkbox_preview.isChecked() and self.result() == 0:
                g.VIEW.restore_plan()

        self.finished.connect(on_closed_menu)

        grid.addWidget(category_label, 1, 0)
        grid.addWidget(category_list, 2, 0)
        grid.addWidget(plan_label, 1, 1, 1, 3)
        grid.addWidget(plan_lineedit, 0, 0)
        grid.addWidget(button_rename, 0, 1)
        grid.addWidget(button_addplan, 0, 2)
        grid.addWidget(plan_list, 2, 1, 1, 3)
        grid.addWidget(checkbox_preview, 3, 0)
        grid.addWidget(button_delete, 3, 1)
        grid.addWidget(button_load, 3, 2)
        self.setLayout(grid)

        self.resize(250, 300)
        # self.move(QPoint(g.WINDOW.width()-self.width()*1.2,g.WINDOW.height()-self.height()*1.2))
        self.exec_()


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent, flags=Qt.WindowCloseButtonHint)
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon(get_path("cog.png")))
        self.setSizeGripEnabled(False)
        self.setModal(True)
        self.setMaximumWidth(300)

        tabs = QTabWidget(self)
        tabs.addTab(GeneralTab(self), "General")
        tabs.addTab(OverflowTab(self), "Overflow")

        button_accept = QPushButton(QIcon(get_path("accept.png")), "Done", self)
        button_accept.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setSpacing(g.DIA_SPACING)
        # layout.setMargin(g.DIA_MARGIN)
        layout.addWidget(tabs)
        layout.addWidget(button_accept)

        self.setLayout(layout)

        def on_closed_menu():
            # If the max recent floorplans was lowered, trim the recents off the top
            if len(g.recentFloorplans) > g.SETTINGS.value("settings/maxrecents"):
                del g.recentFloorplans[g.SETTINGS.value("settings/maxrecents"):]

            g.SETTINGS.setValue("data/recentFloorplans", g.recentFloorplans)
            g.SETTINGS.setValue("data/overflowRules", g.overflowRules)
            g.SETTINGS.sync()
            g.SERVER_LIST.widget().pred.update()

        self.finished.connect(on_closed_menu)

        # self.resize(250, 300)
        # self.move(QPoint(g.WINDOW.width()-self.width()*1.2,g.WINDOW.height()-self.height()*1.2))
        self.exec_()


class GeneralTab(QWidget):
    def __init__(self, parent=None):
        super(GeneralTab, self).__init__(parent)
        layout = QFormLayout(self)
        layout.setSpacing(g.DIA_SPACING)

        # resTab.setMargin(g.DIA_MARGIN)

        minResTimeBox = QTimeEdit(g.SETTINGS.value("settings/minResTime"), self)
        maxResTimeBox = QTimeEdit(g.SETTINGS.value("settings/maxResTime"), self)

        def on_changed_mintime(time):
            g.SETTINGS.setValue("settings/minResTime", time)

        def on_changed_maxtime(time):
            g.SETTINGS.setValue("settings/maxResTime", time)

        def on_checked_24hour(s):
            if s > 0:
                g.SETTINGS.setValue("settings/fullhour", 1)
                minResTimeBox.setDisplayFormat("hh:mm")
                maxResTimeBox.setDisplayFormat("hh:mm")
            else:
                g.SETTINGS.setValue("settings/fullhour", 0)
                minResTimeBox.setDisplayFormat("h:mm A")
                maxResTimeBox.setDisplayFormat("h:mm A")

            widg = g.RES_LIST.widget()
            widg.resList.populate_reservations(widg.resDateEdit.date())

        minResTimeBox.timeChanged.connect(on_changed_mintime)
        maxResTimeBox.timeChanged.connect(on_changed_maxtime)

        fullHourCheckBox = QCheckBox("24-Hour Times", self)
        fullHourCheckBox.stateChanged.connect(on_checked_24hour)
        fullHourCheckBox.setChecked(bool(g.SETTINGS.value("settings/fullhour")))

        def on_changed_maxrecents(n):
            g.SETTINGS.setValue("settings/maxrecents", n)

        maxRecentPlans = QSpinBox(self)
        maxRecentPlans.setRange(1, 100)
        maxRecentPlans.setSingleStep(1)
        maxRecentPlans.setValue(g.SETTINGS.value("settings/maxrecents"))
        maxRecentPlans.valueChanged.connect(on_changed_maxrecents)

        if bool(g.SETTINGS.value("settings/fullhour")):
            minResTimeBox.setDisplayFormat("hh:mm")
            maxResTimeBox.setDisplayFormat("hh:mm")
        else:
            minResTimeBox.setDisplayFormat("h:mm A")
            maxResTimeBox.setDisplayFormat("h:mm A")

        layout.addRow("Minimum Reservation Time", minResTimeBox)
        layout.addRow("Maximum Reservation Time", maxResTimeBox)
        layout.addRow(fullHourCheckBox)
        layout.addRow("Recent Floorplans", maxRecentPlans)


class OverflowTab(QWidget):
    def __init__(self, parent=None):
        super(OverflowTab, self).__init__(parent)
        overflowTab = QFormLayout(self)
        overflowTab.setSpacing(g.DIA_SPACING)
        # overflowTab.setMargin(g.DIA_MARGIN)

        overflowTable = RuleTable(self)

        def on_clicked_delete():
            for i in overflowTable.selectedIndexes():
                # Delete the rule from the global rules table
                del g.overflowRules[overflowTable.model().index(i.row(), 0).data()]
                # Delete the rule from the visual table
                overflowTable.model().takeRow(i.row())
                # g.SETTINGS.setValue("data/overflowRules", g.overflowRules)

        label = QLabel(
            "Overflow is calculated for recently sat tables based on this formula:<br>"
            "<i># customers - (minutes passed * kitchen speed)</i><br>"
            "A kitchen speed of 1.0 means the kitchen can serve 1 head every minute (0.5 = 1 customer every 2 minutes, 2.0 = 2 customers every minute).")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)

        def on_changed_overflowmult(n):
            g.SETTINGS.setValue("settings/overflowMultiplier", n)

        overflowMultBox = QDoubleSpinBox(self)
        overflowMultBox.setRange(0.1, 100)
        overflowMultBox.setSingleStep(0.5)
        overflowMultBox.setValue(float(g.SETTINGS.value("settings/overflowMultiplier")))
        overflowMultBox.valueChanged.connect(on_changed_overflowmult)

        label2 = QLabel("The thresholds in the table below allow you to change the color and note it shows when going past a certain threshold. (Double click a cell to modify)")
        label2.setAlignment(Qt.AlignCenter)
        label2.setWordWrap(True)

        newButton = QPushButton(QIcon(get_path("add.png")), "Add", self)
        newButton.clicked.connect(overflowTable.add_rule)
        delButton = QPushButton(QIcon(get_path("delete.png")), "Delete", self)
        delButton.clicked.connect(on_clicked_delete)

        hLayout = QHBoxLayout()
        hLayout.addWidget(newButton)
        hLayout.addWidget(delButton)

        overflowTab.addRow(label)
        overflowTab.addRow("Kitchen Speed", overflowMultBox)
        overflowTab.addRow(label2)
        overflowTab.addRow(hLayout)
        overflowTab.addRow(overflowTable)

        self.setLayout(overflowTab)


class RuleTable(QTableView):
    def __init__(self, parent=None):
        super(RuleTable, self).__init__(parent)

        self.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.resize(200, 150)
        self.setItemDelegate(RuleDelegate(self))

        # Table structure
        model = QStandardItemModel(0, 3)
        model.setHorizontalHeaderLabels(["Note", "Threshold", "Color"])
        self.setModel(model)

        hHead = QHeaderView(Qt.Horizontal)
        hHead.setSectionResizeMode(QHeaderView.Stretch)
        hHead.resizeSection(1, 60)
        hHead.setDefaultSectionSize(82)
        self.setHorizontalHeader(hHead)
        vHead = QHeaderView(Qt.Vertical)
        vHead.setVisible(False)
        vHead.setDefaultSectionSize(25)
        self.setVerticalHeader(vHead)

        self.populate_list()

    def add_rule(self):
        colorNames = QColor.colorNames()
        name = QStandardItem("newRule")
        num = QStandardItem("1")
        num.setTextAlignment(Qt.AlignCenter)
        rngBrush = QBrush(QColor(colorNames[random.randrange(0, len(colorNames))]), Qt.SolidPattern)
        color = QStandardItem()
        color.setBackground(rngBrush)
        color.setSelectable(False)

        b_dupe = False
        for row in range(self.model().rowCount()):
            if self.model().index(row, 0).data() == "newRule":
                b_dupe = True

        if b_dupe:
            g.overflowRules["newRule"] = {"num": 1, "color": rngBrush.color()}
        else:
            self.model().appendRow([name, num, color])
            g.overflowRules["newRule"] = {"num": 1, "color": rngBrush.color()}

        self.sortByColumn(1, Qt.AscendingOrder)

    # g.SETTINGS.setValue("data/overflowRules", g.overflowRules)

    def populate_list(self):
        tbl = g.SETTINGS.value("data/overflowRules")

        for rule in tbl:
            name = QStandardItem(rule)
            num = QStandardItem()
            num.setData(tbl[rule]["num"])
            num.setData(tbl[rule]["num"], Qt.DisplayRole)
            num.setTextAlignment(Qt.AlignCenter)
            color = QStandardItem()
            color.setBackground(QBrush(tbl[rule]["color"], Qt.SolidPattern))
            color.setSelectable(False)

            if rule == "default":
                name.setEditable(False)
                name.setEnabled(False)
                name.setSelectable(False)
                name.setBackground(QBrush(QColor(255, 150, 150), Qt.BDiagPattern))
                num.setEditable(False)
                num.setEnabled(False)
                num.setSelectable(False)
                num.setBackground(QBrush(QColor(255, 150, 150), Qt.BDiagPattern))

            self.model().appendRow([name, num, color])

        self.sortByColumn(1, Qt.AscendingOrder)


class RuleDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(RuleDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        if index.column() == 1:
            box = QSpinBox(parent)
            box.setRange(1, 100)
            box.setAlignment(Qt.AlignCenter)
            box.setFrame(False)

            return box
        elif index.column() == 2:
            box = QColorDialog(index.data(Qt.BackgroundRole).color(), parent)

            return box
        else:
            return super(RuleDelegate, self).createEditor(parent, option, index)

    def setModelData(self, editor, model, index):
        if index.column() == 1:
            model.setData(index, editor.value())
            g.overflowRules[model.index(index.row(), 0).data()].update({"num": editor.value()})
            self.parent().sortByColumn(1, Qt.AscendingOrder)
        elif index.column() == 2:
            model.setData(index, QBrush(editor.currentColor(), Qt.SolidPattern), Qt.BackgroundRole)
            g.overflowRules[model.index(index.row(), 0).data()].update({"color": editor.currentColor()})
        else:
            if editor.text() == "default":
                return

            copy = g.overflowRules.pop(index.data())
            model.setData(index, editor.text())
            g.overflowRules[index.data()] = copy
