"""Unified diagnostic engine for mbtools-dts.

The engine owns *sessions* and *logical operations* on a vehicle:

  * connect/disconnect to an ECU
  * read and clear fault codes (DTCs)
  * read/write diagnostic data identifiers (parameter read/write)
  * variant coding (read/write SA codes)
  * flashing (via BusMonitor + FlashProgrammer)

Everything works with plain Python structures -- no GPIO, no CAN wiring.  The
engine is deliberately thin: it builds the UDS requests and turns the raw
responses into plain structures.  The protocol stack (CAN, ISO-TP, UDS) and the
hardware adapter are injected from outside, so the engine can be tested
headless and the GUI mirrors what's already proven to work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .hardware.base import CanHardwareAdapter, HardwareError
from .logic.flashing import BusMonitor, FlashProgrammer
from .protocol_client import _UdsClient
from .protocols import uds as _uds

__all__ = ["FaultCode", "Session", "LogicEngine"]


@dataclass
class FaultCode:
    """One stored diagnostic trouble code (DTC)."""

    code: str
    description: str = "Unspecified fault"
    status: int = 0
    timestamp: str = ""

    def __str__(self) -> str:
        return f"{self.code} ({self.description})"


@dataclass
class Session:
    """A live connection to one ECU."""

    ecu_name: str
    adapter: CanHardwareAdapter
    uds: "_UdsClient"
    ecuc_type: Optional[str] = None
    coding_tables: list = field(default_factory=list)
    fault_codes: list[FaultCode] = field(default_factory=list)
    is_connected: bool = False

    @property
    def name(self) -> str:
        """Public name used by the CLI and GUI to report the active ECU."""
        return self.ecu_name

    def __str__(self):
        return f"Session({self.ecu_name}, connected={self.is_connected})"


class LogicEngine:
    """The brain of the tool.

    It has two jobs:
      1) Manage all the Sessions (connect/disconnect, read/write).
      2) Turn any operation into a human-friendly explanation the user can
         understand, no matter their experience level.
    """

    def __init__(self, data_folder: str | Path | None = None):
        self.data_folder = Path(data_folder) if data_folder else None
        self.sessions: list[Session] = []
        self._next_session_id = 0
        self._flash_programmer: Optional[FlashProgrammer] = None

    # -- hardware ----------------------------------------------------------

    def scan_ecus(self, adapter: CanHardwareAdapter) -> list["Session"]:
        """Probe the adapter for candidate ECUs."""
        try:
            adapter.open()
        except HardwareError:
            return []
        infos = adapter.scan_devices()
        sessions = []
        for info in infos:
            session = Session(
                ecu_name=info.get("description", info.get("name", "unknown ECU")),
                adapter=adapter,
                uds=None,  # set up by connect()
                ecuc_type=info.get("product_id", "unknown"),
            )
            sessions.append(session)
        adapter.close()
        return sessions

    def connect(self, adapter: CanHardwareAdapter, ecu_name: str = "unknown ECU") -> Session:
        uds = _UdsClient(adapter, ecu_name)
        uds.connect()
        session = Session(
            ecu_name=ecu_name,
            adapter=adapter,
            uds=uds,
            ecuc_type=None,
            is_connected=True,
        )
        self.sessions.append(session)
        return session

    def disconnect(self, session: Session | None = None) -> None:
        if session is None:
            # Called without a session: disconnect the most recent one.
            if not self.sessions:
                return
            session = self.sessions[-1]
        if session.is_connected:
            try:
                session.uds.disconnect()
            finally:
                session.adapter.close()
                session.is_connected = False

    # - read DTCs ---------------------------------------------------------

    def read_dtcs(self, dtc_buffer_mask: int = 0x80, number_of_buffers: int = 1) -> list[dict]:
        session = self._active_session()
        if session is None:
            raise RuntimeError("no active session")
        return session.uds.read_dtcs(dtc_buffer_mask=dtc_buffer_mask, number_of_buffers=number_of_buffers)

    # - read/write parameters ---------------------------------------------

    def read_data_by_identifier(self, parameter_id: int, data_identifiers: bytes = b"") -> bytes:
        session = self._active_session()
        if session is None:
            raise RuntimeError("no active session")
        return session.uds.read_data_by_identifier(
            parameter_id=parameter_id, data_identifiers=data_identifiers
        )

    def write_data_by_identifier(self, parameter_id: int, data: bytes = b"") -> None:
        session = self._active_session()
        if session is None:
            raise RuntimeError("no active session")
        session.uds.send(
            _uds.SVC_WRITE_DATA_BY_IDENTIFIER,
            sub_function=0x01,
            data=data,
        )

    # - clear DTCs --------------------------------------------------------

    def control_dtc_setting(self, control_mode: int = 0x01, mask: int = 0x00) -> None:
        session = self._active_session()
        if session is None:
            raise RuntimeError("no active session")
        session.uds.send(
            _uds.SVC_CONTROL_DTC_SETTING,
            sub_function=0x01,
            data=bytes([control_mode, mask]),
        )

    # - variant coding ----------------------------------------------------
    # (SA-code read/write is a DataByIdentifier access over a tuned DP area;
    #  the mbtools layer already exposes DataByIdentifier.)

    # - flashing ----------------------------------------------------------

    def start_flash(self, session: Session, image_path: Path, block_size: int = 1):
        if not image_path.exists():
            raise FileNotFoundError(f"image not found: {image_path}")
        self._flash_programmer = FlashProgrammer(session.adapter, block_size=block_size)
        self._flash_programmer.load(image_path)
        print(f"Ready to flash {image_path.name} ({len(image_path.read_bytes())} bytes).")

    @property
    def flash_programmer(self) -> Optional[FlashProgrammer]:
        return self._flash_programmer

    # -- helpers ---------------------------------------------------------

    def _active_session(self) -> Optional["Session"]:
        if not self.sessions:
            return None
        return self.sessions[-1]
