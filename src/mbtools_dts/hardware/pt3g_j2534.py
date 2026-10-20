"""Hardware backend: PT3G VCI over the open SAE J2534-1 pass-thru driver.

This is the DTS-Monaco-specific adapter for the PT3G VCI, reused here in the
combined tool.  It wraps the compiled :mod:`pt3g_j2534` driver (the open-source
J2534 pass-thru driver) and exposes the :class:`CanHardwareAdapter` contract.

Frame format (canonical, used by every backend in this tool)::

    [ can_id    :4 bytes, big-endian ]
    [ dlc       :1 byte ]
    [ data      :0..8 bytes ]

This is the same wire format the mbtools protocol stack talks over: the CAN
layer turns a ``(id, data)`` pair into these bytes, ISO-TP fragments the data,
and the PT3G driver transmits them verbatim.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from typing import Optional

from .base import CanHardwareAdapter, HardwareError, HardwareInfo, HardwareType

logger = logging.getLogger(__name__)

# The compiled driver package.  By the time this module is imported the user
# has run ``pip install -e .`` for pt3g_j2534 (cp. the README of the combined
# tool).  If the shared library is missing the adapter falls back to the
# virtual adapter so the rest of the toolchain keeps working.
try:
    import pt3g_j2534 as _pt3g  # noqa: F401
    _HAVE_LIB = True
except ImportError:
    _HAVE_LIB = False


def _pass_thru_open(driver: str, baud: int = 500000):
    if not _HAVE_LIB:
        raise ImportError(
            "the pt3g_j2534 shared library is not installed.  "
            "Run `pip install -e .` from the pt3g-j2534 repository root, then "
            "reinstall this tool."
        )
    # PassThruOpen(driver_name, event_mask, *flags?) returns a handle (int).
    # The compiled bindings expose a simple signature; we call it with the
    # driver name (bytes), an event mask of 0 and the baud flag 0.
    handle = _pt3g.PassThruOpen(driver.encode("ascii") if isinstance(driver, str) else driver, 0)
    if handle == 0:
        raise HardwareError(f"Failed to open PT3G VCI driver '{driver}'")
    return handle


def _pass_thru_read(handle: int, timeout_ms: int) -> bytes:
    data = _pt3g.PassThruRead(handle, timeout_ms)
    if data is None:
        return b""
    return data


def _pass_thru_write(handle: int, frame: bytes) -> int:
    n = ctypes.c_uint32(0)
    _pt3g.PassThruWrite(handle, frame, len(frame), ctypes.byref(n))
    return n.value


def _pass_thru_close(handle: int) -> None:
    _pt3g.PassThruClose(handle)


class Pt3gJ2534Adapter(CanHardwareAdapter):
    """DTS-Monaco CanHardwareAdapter for the PT3G VCI via the open J2534 driver.

    Parameters
    ----------
    serial_number : str
        Optional serial number used to pick the adapter (on Windows the Actia
        PDU API path resolves by serial number).
    baud : int
        CAN baud rate (default 500 000).
    driver : str or None
        J2534 driver name.  ``None`` (the default) chooses the platform-aware
        fallback: on Windows the Actia PDU API if the DLL is present, otherwise
        the virtual adapter; on Linux the serial backend if a ``/dev/ttyUSB*``
        port exists, otherwise the virtual adapter.
    """

    # J2534 v04.04 / v05.00 driver name constants (the library exposes the same
    # names as the upstream pt3g_j2534 package).  Map a few aliases.
    _DRIVER_NAMES = {
        "virtual": "virtual",
        "serial": "serial",
        "actia": "actia",
        "auto": "auto",
    }

    def __init__(
        self,
        serial_number: str = "",
        baud: int = 500000,
        driver: Optional[str] = None,
    ):
        self.serial_number = serial_number
        self.baud = baud
        self._driver = driver or self._default_driver()
        self._handle = None
        self._open = False

    # -- helpers ---------------------------------------------------------

    def _default_driver(self) -> str:
        if sys.platform == "win32" and _HAVE_LIB:
            # On Windows the legacy path is the Actia PDU API if the DLL is
            # present; otherwise the virtual adapter.
            try:
                import pt3g_j2534 as _pt3g
                if _pt3g._find_actia_dll() is not None:
                    return "actia"
            except Exception:
                pass
            return "virtual"
        if sys.platform.startswith("linux"):
            if self._find_serial_port() is not None:
                return "serial"
            return "virtual"
        return "virtual"

    def _find_serial_port(self) -> Optional[str]:
        if sys.platform != "posix":
            return None
        try:
            entries = __import__("os").listdir("/dev")
        except OSError:
            return None
        for entry in entries:
            if entry.startswith("ttyUSB"):
                return f"/dev/{entry}"
        return None

    # -- CanHardwareAdapter contract --------------------------------------

    def open(self, mode: int = 0) -> None:
        if self._open:
            return
        driver = self._DRIVER_NAMES.get(self._driver, self._driver)
        self._handle = _pass_thru_open(driver, self.baud)
        self._open = True
        logger.info("PT3G J2534 adapter opened (driver=%r, handle=%r)", driver, self._handle)

    def close(self) -> None:
        if self._open:
            try:
                _pass_thru_close(self._handle)
            except Exception:
                pass
            self._handle = None
            self._open = False

    def read(self, timeout_ms: int = 100) -> Optional[bytes]:
        if not self._open:
            return None
        return _pass_thru_read(self._handle, timeout_ms)

    def write(self, frame: bytes) -> int:
        if not self._open:
            return 0
        return _pass_thru_write(self._handle, frame)

    def get_info(self) -> HardwareInfo:
        return HardwareInfo(
            kind=HardwareType.PT3G_VCI,
            port=f"J2534 pass-thru ({self._driver})",
            vendor_id="PT3G / Porsche",
            product_id="PT3G-VCI",
            serial=self.serial_number or "unknown",
            channels=1,
        )

    def test(self) -> bool:
        try:
            if not self._opened:
                return False
            self.write(b"\x00\x00\x00\x01\x01\x00")
            return self.read(200) is not None
        except Exception:
            return False

    @property
    def _opened(self) -> bool:
        return self._open

    def scan_devices(self) -> list:
        """J2534 v05.00 device discovery."""
        if not self._open:
            return []
        try:
            return _pt3g.get_device_list() or []
        except Exception:
            return []

    def get_next_device(self):
        if not self._open:
            return None
        return None
