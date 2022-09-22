import sqlite3 as sql
import time

from qtpy.QtCore import QSize, Qt, QDate, QTime, QModelIndex, QAbstractItemModel
from qtpy.QtGui import QBrush, QCursor, QIcon, QStandardItemModel, QStandardItem
from qtpy.QtWidgets import *

import core.globals as g
# import core.objects
from core.dialogs import ReservationDialog
from core.globals import get_path


class ResList_Dock(QDockWidget):
    def __init__(self, parent=None):
        super(ResList_Dock, self).__init__("Reservations", parent)

        self.setWidget(ResWidget(self))
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)


class ResWidget(QWidget):
    def __init__(self, parent=None):
        super(ResWidget, self).__init__(parent)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred))

        toolbar = self.create_toolbar()

        self.resList = ResList(self)

        self.calendar = QCalendarWidget(self)
        self.calendar.setHorizontalHeaderFormat(QCalendarWidget.SingleLetterDayNames)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setGridVisible(True)

        def on_changed_date(date):
            self.resList.populate_reservations(date)

        self.resDateEdit = QDateEdit(self)
        self.resDateEdit.setCalendarPopup(True)
        self.resDateEdit.setCalendarWidget(self.calendar)
        self.resDateEdit.setDisplayFormat("dddd - MMM / dd / yyyy")
        self.resDateEdit.setAlignment(Qt.AlignCenter)
        self.resDateEdit.setDate(QDate.currentDate())
        self.resDateEdit.dateChanged.connect(on_changed_date)
        self.resDateEdit.setToolTip("Sets the date to view reservations for")
        self.resDateEdit.setStatusTip("Sets the date to view reservations for")

        def on_clicked_showtoday():
            self.resDateEdit.setDate(QDate.currentDate())
            self.resList.populate_reservations(QDate.currentDate())

        self.showTodayButton = QToolButton(self)
        self.showTodayButton.setIcon(QIcon(get_path("arrow_refresh.png")))
        self.showTodayButton.clicked.connect(on_clicked_showtoday)
        self.showTodayButton.setToolTip("Resets the date to today")
        self.showTodayButton.setStatusTip("Resets the date to today")

        dateLayout = QHBoxLayout()
        dateLayout.addWidget(self.resDateEdit)
        dateLayout.addWidget(self.showTodayButton)

        layout = QGridLayout(self)
        layout.setSpacing(g.DOCK_SPACING)
        layout.setContentsMargins(g.DOCK_MARGIN)

        layout.addWidget(toolbar, 0, 0)
        layout.addLayout(dateLayout, 1, 0)
        layout.addWidget(self.resList, 2, 0)

    def create_toolbar(self):
        def toolbar_clickArriveRes():
            curr = self.resList.selectedIndexes()
            if not curr or len(curr) < 1:
                return print("invalid selection")

            for index in curr:
                self.resList.arrive_reservation(index)

        def on_clicked_edit():
            curr = self.resList.selectedIndexes()
            if not curr or len(curr) < 1:
                return print("invalid selection")

            for index in curr:
                self.resList.edit_reservation(index)

        def on_clicked_remove():
            curr = self.resList.selectedIndexes()
            if not curr or len(curr) < 1:
                return print("invalid selection")

            for index in curr:
                self.resList.cancel_reservation(index)

        def on_clicked_add():
            ReservationDialog(self)

        tb = QToolBar("Server Tally Bar", self)
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        tb.setIconSize(QSize(16, 16))

        toolbar_addRes = tb.addAction(QIcon(get_path("add.png")), "Add")
        toolbar_addRes.triggered.connect(on_clicked_add)
        toolbar_addRes.setToolTip("Adds a reservation")
        toolbar_addRes.setStatusTip("Adds a reservation")

        toolbar_editRes = tb.addAction(QIcon(get_path("pencil.png")), "Edit")
        toolbar_editRes.triggered.connect(on_clicked_edit)
        toolbar_editRes.setToolTip("Edits a reservation")
        toolbar_editRes.setStatusTip("Edits a reservation")

        toolbar_arriveRes = tb.addAction(QIcon(get_path("bell.png")), "Arrived")
        toolbar_arriveRes.triggered.connect(toolbar_clickArriveRes)
        toolbar_arriveRes.setToolTip("Marks a reservation as arrived")
        toolbar_arriveRes.setStatusTip("Marks a reservation as arrived")

        toolbar_removeRes = tb.addAction(QIcon(get_path("delete.png")), "Cancel")
        toolbar_removeRes.triggered.connect(on_clicked_remove)
        toolbar_removeRes.setToolTip("Cancels a reservation, deletes if pressed twice")
        toolbar_removeRes.setStatusTip("Cancels a reservation, deletes if pressed twice")

        return tb

    def sizeHint(self):
        return QSize(300, 100)

    def update_date(self, date):
        self.resDateEdit.setDate(date)
        self.resList.populate_reservations(date)


# Formats a string a numbers into a phone number with dashes
def formatPhone(ph):
    uSt = str(ph)
    s1 = uSt[0:3]
    s2 = uSt[3:6]
    s3 = uSt[6:]

    return "{}-{}-{}".format(s1, s2, s3)


# Formats time based on 24 or 12 hour time setting
# variable time can be str or QTime
def formatTime(t):
    if bool(g.SETTINGS.value("settings/fullhour")):
        formatString = "hh:mm"
    else:
        formatString = "h:mmA"

    if type(t) is str:
        return QTime.fromString(t, formatString)
    elif type(t) is QTime:
        return t.toString(formatString)


class ResList(QTableView):
    def __init__(self, parent=None):
        super(ResList, self).__init__(parent)

        # Setup list attributes
        self.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setItemDelegate(ResDelegate(self))
        self.setAlternatingRowColors(True)

        # Create item model
        model = QStandardItemModel(0, 5)
        # Set the column headers
        model.setHorizontalHeaderLabels(["Time", "Size", "Name", "Phone", "Notes"])
        self.setModel(model)

        # Setup header attributes (remove vertical header)
        hHead = QHeaderView(Qt.Horizontal)
        hHead.setSectionResizeMode(QHeaderView.ResizeToContents)
        # hHead.resizeSection(0, 65)
        hHead.setDefaultSectionSize(50)
        hHead.setStretchLastSection(True)
        self.setHorizontalHeader(hHead)
        vHead = QHeaderView(Qt.Vertical)
        vHead.setVisible(False)
        vHead.setDefaultSectionSize(20)
        self.setVerticalHeader(vHead)

        self.populate_reservations()

        self.pressed.connect(self.on_clicked_cell)

    # Populate the reservation list with reservations for a date
    def populate_reservations(self, date=QDate.currentDate()):
        # Remove the current rows
        if self.model().rowCount() > 0:
            self.model().removeRows(0, self.model().rowCount())

        # Query reservations table for the reservations on this date
        con = sql.connect("hostprogram.db")
        con.row_factory = sql.Row
        cur = con.cursor()
        resData = cur.execute("SELECT * FROM reservations WHERE date = date('" + date.toString(Qt.ISODate) + "')") \
            .fetchall()
        con.close()

        # Sort the table by time
        def sort_by_time(d):
            # Parse the time string into a time object for sorting
            return time.strptime(d["time"], "%H:%M:%S")

        resData.sort(key=sort_by_time)

        # Iterate through the sorted table
        for res in resData:
            # Assemble the row and append it to the model
            self.model().appendRow(self.new_reservation(res))

            # If the reservation is arrived or canceled
            if res["state"] == 1:
                col = QBrush(g.COLORS["reservation_arrive"], Qt.SolidPattern)
            elif res["state"] == 2:
                col = QBrush(g.COLORS["reservation_cancel"], Qt.SolidPattern)
            else:
                # No need to color this row so move on
                continue

            # Iterate through columns
            for column in range(self.model().columnCount()):
                # Set background to the arrival or cancel color
                self.model().setData(self.model().index(self.model().rowCount() - 1, column), col, Qt.BackgroundRole)

        # All data is populated, now we can resize columns
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)

    # Create a list of standard items to be inserted into the model (for each row)
    @staticmethod
    def new_reservation(res: sql.Row) -> list:
        # Convert the time string -> QTime -> string in desired format
        c1 = QStandardItem(formatTime(QTime.fromString(res["time"], Qt.ISODate)))
        # Set the 1st column's UserRole to the database's res_id
        c1.setData(res["res_id"], Qt.UserRole)

        c2 = QStandardItem(str(res["size"]))
        # Set the 2nd column's UserRole to the reservation's state
        c2.setData(res["state"], Qt.UserRole)

        return [c1,
                c2,
                QStandardItem(res["name"]),
                QStandardItem(formatPhone(res["phone"])),
                QStandardItem(res["note"])]

    def on_clicked_cell(self, model_index):
        # Make sure right mouse button was pressed
        if g.APP.mouseButtons() != Qt.RightButton:
            return

        # Create the context menu for reservation rows
        menu = QMenu(g.WINDOW)

        # Each of these actions need to have the index of the row clicked
        def on_clicked_arrive():
            self.arrive_reservation(model_index)

        arriveAct = menu.addAction("Arrived")
        arriveAct.triggered.connect(on_clicked_arrive)
        arriveAct.setStatusTip("Marks the reservation as arrived")

        def on_clicked_edit():
            self.edit_reservation(model_index)

        editAct = menu.addAction("Edit")
        editAct.triggered.connect(on_clicked_edit)
        editAct.setStatusTip("Edits the reservation")

        def on_clicked_cancel():
            self.cancel_reservation(model_index)

        deleteAct = menu.addAction("Cancel")
        deleteAct.triggered.connect(on_clicked_cancel)
        deleteAct.setStatusTip("Cancels the reservation, double click deletes it")

        menu.exec_(QCursor.pos(), arriveAct)

    # Set's a reservation's state
    # model_index is the QModelIndex that represents a cell in the model
    # state is the state the reservation should be set to
    def set_reservation_state(self, model_index, state):
        # Get the reservation's database ID
        res_id = self.model().index(model_index.row(), 0).data(Qt.UserRole)

        # Update the database with the new state (not arrived)
        con = sql.connect("hostprogram.db")
        cur = con.cursor()
        cur.execute("UPDATE reservations SET state = ? WHERE res_id = ?",
                    (state, res_id))
        con.commit()
        con.close()

        # Update the row's state data
        self.model().setData(self.model().index(model_index.row(), 1), state, Qt.UserRole)

        # Depending on the state, choose a color for the background of the row
        col = QBrush()
        if state == 1:
            col = QBrush(g.COLORS["reservation_arrive"], Qt.SolidPattern)
        elif state == 2:
            col = QBrush(g.COLORS["reservation_cancel"], Qt.SolidPattern)

        # Set the background role of the model
        for column in range(self.model().columnCount()):
            self.model().setData(self.model().index(model_index.row(), column), col, Qt.BackgroundRole)

    def arrive_reservation(self, model_index):
        # Get the reservation's state
        res_state = self.model().index(model_index.row(), 1).data(Qt.UserRole)

        # If the reservation hasn't arrived, set it to arrive, if it has arrived, set it to not arrived
        self.set_reservation_state(model_index, 1) if res_state == 0 else self.set_reservation_state(model_index, 0)

    # Create the edit reservation dialog
    def edit_reservation(self, model_index):
        ReservationDialog(self, str(self.model().index(model_index.row(), 0).data(Qt.UserRole)))

    # Mark a reservation as canceled or delete if ran twice
    def cancel_reservation(self, model_index):
        # Get the reservation's database ID and state
        res_state = self.model().index(model_index.row(), 1).data(Qt.UserRole)

        # If the reservation is already canceled
        if res_state == 2:
            # Delete the row (it remains in the database table for future usage)
            self.model().removeRow(model_index.row())

        # Reservation hasn't arrived or has arrived
        else:
            # Mark it as canceled
            self.set_reservation_state(model_index, 2)


class ResDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(ResDelegate, self).__init__(parent)

    # Defines which editor should be used and their parameters when a cell is double-clicked
    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex):
        # Time
        if index.column() == 0:
            box = QTimeEdit(parent)
            box.setTimeRange(g.SETTINGS.value("settings/minResTime"), g.SETTINGS.value("settings/maxResTime"))
            box.setToolTip("Time the reservation is scheduled")
            box.setFrame(False)
            box.setTime(formatTime(index.data()))

            if bool(g.SETTINGS.value("settings/fullhour")):
                box.setDisplayFormat("hh:mm")
            else:
                box.setDisplayFormat("hh:mm A")

            return box

        # Size
        elif index.column() == 1:
            box = QSpinBox(parent)
            box.setRange(1, 99)
            box.setToolTip("Party size of the reservation (how many customers)")
            # box.setAlignment(Qt.AlignCenter)
            box.setFrame(False)

            return box

        # Name
        elif index.column() == 2:
            box = QLineEdit(parent)
            box.setMaxLength(15)
            box.setToolTip("Name of the reservation")
            box.setFrame(False)

            return box

        # Phone number
        elif index.column() == 3:
            box = QLineEdit(parent)
            box.setInputMask("999-999-9999")
            # box.setInputMask("9999999999")
            box.setToolTip("Phone number of the reservation")
            box.setFrame(False)

            return box

        # Notes
        else:
            box = QLineEdit(parent)
            box.setMaxLength(15)
            box.setToolTip("Special instructions for the reservation")
            box.setFrame(False)

            return box

    # Behavior for when editing a cell is finished
    def setModelData(self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex):
        # Get the data that this row represents
        res_id = model.index(index.row(), 0).data(Qt.UserRole)
        # print(fetchRes)

        # Time
        if index.column() == 0:
            # Execute an update command on the database
            con = sql.connect("hostprogram.db")
            cur = con.cursor()
            cur.execute("UPDATE reservations SET time = time(?) WHERE res_id = ?",
                        (editor.time().toString("hh:mm"), res_id))
            con.commit()
            con.close()
            # Set the display data on the visual cell to the new time
            model.setData(index, formatTime(editor.time()))
        # self.parent().sortByColumn(0, Qt.AscendingOrder)

        # Size
        elif index.column() == 1:
            con = sql.connect("hostprogram.db")
            cur = con.cursor()
            cur.execute("UPDATE reservations SET size = ? WHERE res_id = ?",
                        (editor.value(), res_id))
            con.commit()
            con.close()

            model.setData(index, editor.value())

        # Name
        elif index.column() == 2:
            con = sql.connect("hostprogram.db")
            cur = con.cursor()
            cur.execute("UPDATE reservations SET name = ? WHERE res_id = ?",
                        (editor.text(), res_id))
            con.commit()
            con.close()

            model.setData(index, editor.text())

        # Phone number
        elif index.column() == 3:
            # Box text contains dashes from formatting, so we need to unformat it by removing the dashes
            u_str = editor.text().replace("-", "")

            con = sql.connect("hostprogram.db")
            cur = con.cursor()
            cur.execute("UPDATE reservations SET phone = ? WHERE res_id = ?",
                        (u_str, res_id))
            con.commit()
            con.close()

            # model.setData(index, newStr, Qt.EditRole)
            model.setData(index, editor.text(), Qt.DisplayRole)

        # Notes
        else:
            con = sql.connect("hostprogram.db")
            cur = con.cursor()
            cur.execute("UPDATE reservations SET note = ? WHERE res_id = ?",
                        (editor.text(), res_id))
            con.commit()
            con.close()
