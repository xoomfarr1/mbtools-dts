"""Unified PySide6 main window for mbtools-dts.

This is the single place where the user sees the tool.  It combines:

* the adapter protocol (connect to the PT3G VCI via J2534);
* the three diagnostic workbenches (DTC viewer, live data, variant coding);
* the menu / toolbar / status bar.

Layout
------
* QMainWindow + central widget with QVBoxLayout: the log at the top (a
  fixed, scrollable area) and the tabbed workbenches below it.
* The toolbar carries the connection settings and the live-actions.
* The menu bar carries File, Tools and Help.
* A log + three tabs: the log is the audit trail (every frame the bus sees,
  timestamped), and the tabs are the diagnostic workbenches.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QTextEdit,
    QTabWidget,
    QMessageBox,
    QStatusBar,
    QMenuBar,
    QAction,
)

from ..config import Settings
from ..engine import LogicEngine
from ..hardware import get_hardware_adapter, HardwareType
from ..protocols import uds as _uds


# ---------------------------------------------------------------------------
#  WORKBENCHS
# ---------------------------------------------------------------------------

class DtcView(QWidget):
    """List of DTCs (code, severity, type, status, description)."""

    def __init__(self):
        super().__init__()
        self._engine: Optional[LogicEngine] = None
        self._session = None

        layout = QVBoxLayout(self)
        self._title = QLabel("DTC / fault codes")
        self._title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._title)

        self._info = QLabel("No active session.")
        layout.addWidget(self._info)

        self._list = QTextEdit()
        self._list.setReadOnly(True)
        self._list.setMaximumHeight(200)
        layout.addWidget(self._list)

        btns = QHBoxLayout()
        self._refresh = QPushButton("Refresh DTCs")
        self._refresh.clicked.connect(self._refresh_clicked)
        btns.addWidget(self._refresh)
        layout.addLayout(btns)

    def set_engine(self, engine: LogicEngine):
        self._engine = engine

    def set_session(self, session):
        self._session = session
        self._info.setText(f"Session: {session.ecu_name if session else 'None'}")

    def _refresh_clicked(self):
        if self._session is None:
            self._list.setPlainText("No active session.")
            return
        try:
            dtcs = self._session.uds.read_dtcs(mask=0x80, number_of_buffers=1)
            lines = [f"{r['code']} ({r['type']}): {r['severity']}" for r in dtcs]
            self._list.setPlainText("\n".join(lines) if lines else "No DTCs found.")
        except Exception as exc:
            self._list.setPlainText(f"ERROR: {exc}")


class LiveDataView(QWidget):
    """Live data / parameter read."""

    def __init__(self):
        super().__init__()
        self._engine: Optional[LogicEngine] = None
        self._session = None

        layout = QVBoxLayout(self)
        self._title = QLabel("Live data")
        self._title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._title)

        self._info = QLabel("No active session.")
        layout.addWidget(self._info)

        self._param = QComboBox()
        self._param.addItem("0x10000402 (engine coolant temperature)")
        self._param.setMinimumWidth(200)
        layout.addWidget(self._param)

        self._read_btn = QPushButton("Read parameter")
        self._read_btn.clicked.connect(self._read_clicked)
        layout.addWidget(self._read_btn)

        self._value = QTextEdit()
        self._value.setReadOnly(True)
        self._value.setMaximumHeight(120)
        layout.addWidget(self._value)

        self._engine = None

    def set_engine(self, engine: LogicEngine):
        self._engine = engine

    def set_session(self, session):
        self._session = session
        self._info.setText(f"Session: {session.ecu_name if session else 'None'}")

    def _read_clicked(self):
        if self._session is None:
            self._value.setPlainText("No active session.")
            return
        try:
            pid = self._param.currentText().split(" ")[0]
            pid = int(pid, 0)
            payload = self._session.uds.read_data_by_identifier(parameter_id=pid)
            self._value.setPlainText(f"0x{pid:06X} = {payload.hex()}")
        except Exception as exc:
            self._value.setPlainText(f"ERROR: {exc}")


class CodingView(QWidget):
    """Variant coding (SA-code read/write).  Sample data."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self._title = QLabel("Variant coding")
        self._title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._title)
        self._info = QLabel("Coding tables are vehicle-specific; no active session.")
        layout.addWidget(self._info)
        self._value = QTextEdit()
        self._value.setReadOnly(True)
        self._value.setMaximumHeight(100)
        layout.addWidget(self._value)

    def set_engine(self, engine):
        self._engine = engine

    def set_session(self, session):
        self._session = session
        self._info.setText(f"Session: {session.ecu_name if session else 'None'}")
        self._value.setPlainText("SA-code read/write is a DataByIdentifier access ")


class SimpleWindow(QMainWindow):
    """The combined open-source Mercedes-Benz diagnostics window."""

    def __init__(self, settings: Settings | None = None):
        super().__init__()
        self.settings = settings or Settings()
        self.engine = LogicEngine()
        self.session = None

        self.setWindowTitle("MBTools-DTS - Open-Source Mercedes-Benz Diagnostics")
        self.setFixedSize(self.settings.window_width, self.settings.window_height)

        # ---- central widget + layout ----
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)

        # ---- toolbar ----
        self.toolbar = self.addToolBar("Main")
        self.btn_connect = QPushButton("Connect to car")
        self.btn_connect.setObjectName("primary")
        self.btn_connect.clicked.connect(self._on_connect)
        self.toolbar.addWidget(self.btn_connect)
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        self.toolbar.addWidget(self.btn_disconnect)

        # ---- log (top) ----
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(160)
        main.addWidget(self.log)

        # ---- tabs (workspace) ----
        self.workspace = QTabWidget()
        self.dtc_view = DtcView()
        self.live_view = LiveDataView()
        self.coding_view = CodingView()
        self.workspace.addTab(self.dtc_view, "DTCs")
        self.workspace.addTab(self.live_view, "Live data")
        self.workspace.addTab(self.coding_view, "Variant coding")
        main.addWidget(self.workspace)

        # ---- status bar ----
        self.statusBar().showMessage("Ready.")

        # ---- menu ----
        self._build_menu()

        # ---- tutorial ----
        self.tutorial_box = QLabel(
            "Connect to your car, then read fault codes, live data and variant coding. "
            "Always start with a backup."
        )
        self.tutorial_box.setStyleSheet(
            "background-color: #FFF8E1; border: 1px solid #FFD54F; "
            "padding: 8px; border-radius: 6px; font-size: 13px;"
        )
        main.addWidget(self.tutorial_box)

        self._engine = self.engine
        self.dtc_view.set_engine(self.engine)
        self.live_view.set_engine(self.engine)
        self.coding_view.set_engine(self.engine)

        self.show()

    # -- menu ------------------------------------------------------------

    def _build_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        connect_act = QAction("Connect", self)
        connect_act.triggered.connect(self._on_connect)
        file_menu.addAction(connect_act)
        disconnect_act = QAction("Disconnect", self)
        disconnect_act.triggered.connect(self._on_disconnect)
        file_menu.addAction(disconnect_act)
        tools_menu = menu_bar.addMenu("&Tools")
        tools_menu.addAction("Read DTCs", self._on_read_dtcs)
        tools_menu.addAction("Read live data", self._on_read_live)
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction("About", self._on_about)

    # -- actions ---------------------------------------------------------

    def _on_connect(self):
        self.log.append("Connecting to the PT3G VCI (J2534)...")
        try:
            adapter = get_hardware_adapter()
            adapter.open()
            self.session = self.engine.connect(adapter, ecu_name="PT3G VCI")
            self.session.uds.connect(0x10)
            self.dtc_view.set_session(self.session)
            self.live_view.set_session(self.session)
            self.coding_view.set_session(self.session)
            self.btn_disconnect.setEnabled(True)
            self.statusBar().showMessage(f"Connected to {self.session.ecu_name}")
            self.log.append(f"Connected: {self.session.ecu_name}")
        except Exception as exc:
            self.statusBar().showMessage(f"Connect failed: {exc}")
            self.log.append(f"ERROR: {exc}")

    def _on_disconnect(self):
        if self.session is not None:
            self.session.uds.disconnect()
            self.engine.disconnect(self.session)
            self.session = None
        self.btn_disconnect.setEnabled(False)
        self.statusBar().showMessage("Disconnected.")

    def _on_read_dtcs(self):
        if self.session is None:
            self.statusBar().showMessage("No active session.")
            return
        try:
            dtcs = self.session.uds.read_dtcs(mask=0x80, number_of_buffers=1)
            lines = [f"{r['code']} ({r['type']}): {r['severity']}" for r in dtcs]
            self.dtc_view._list.setPlainText("\n".join(lines) if lines else "No DTCs found.")
            self.log.append(f"Read {len(dtcs)} DTC(s).")
        except Exception as exc:
            self.statusBar().showMessage(f"Read DTCs failed: {exc}")
            self.log.append(f"ERROR: {exc}")

    def _on_read_live(self):
        if self.session is None:
            self.statusBar().showMessage("No active session.")
            return
        try:
            pid = int(self.live_view._param.currentText().split(" ")[0], 0)
            payload = self.session.uds.read_data_by_identifier(parameter_id=pid)
            self.live_view._value.setPlainText(f"0x{pid:06X} = {payload.hex()}")
            self.log.append(f"Read 0x{pid:06X} = {payload.hex()}")
        except Exception as exc:
            self.statusBar().showMessage(f"Read live data failed: {exc}")
            self.log.append(f"ERROR: {exc}")

    def _on_about(self):
        QMessageBox.information(self, "About", "MBTools-DTS\n\nOpen-source Mercedes-Benz diagnostics.\n\nCombining mbtools, DTS-Monaco and the PT3G J2534 driver.")
