"""Hardware abstraction layer for mbtools-dts.

The hardware layer sits at the very bottom of the stack.  It exposes a single
interface -- :class:`CanHardwareAdapter` -- that every higher layer (ISO-TP,
UDS, the engine, the GUI) depends on.  The adapter is responsible for:

    * opening / closing the physical or virtual device,
    * reading one raw CAN frame from the bus,
    * writing one raw CAN frame to the bus,
    * discovering devices and reporting their info.

Implementation details (the PT3G VCI via a J2534 pass-thru adapter, the legacy
Actia PDU API, or a headless virtual bus) live in separate backends that the
adapter selects for you.  Higher layers never touch the raw API -- they only
talk to the adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

__all__ = [
    "HardwareType", "HardwareInfo", "CanHardwareAdapter", "HardwareError",
]


class HardwareType(Enum):
    """What kind of device the adapter is talking to."""

    VIRTUAL = "virtual"
    PT3G_VCI = "pt3g-vci"
    ACTIA_PDU = "actia-pdu"
    USB_DONGLE = "usb-dongle"


@dataclass(frozen=True)
class HardwareInfo:
    """One-line description of a hardware adapter."""

    kind: HardwareType
    port: str
    vendor_id: str
    product_id: str
    serial: str
    channels: int = 1


class HardwareError(Exception):
    """Anything that can go wrong when talking to a physical or virtual adapter."""


class CanHardwareAdapter:
    """The contract every backend must fulfil.

    The frame format is the same for every backend:

        [id:4 bytes][dlc:1 byte][data:0..8 bytes]
    """

    # -- lifecycle ------------------------------------------------------

    def open(self, mode: int = 0) -> None:
        """Open the device.  May raise :class:`HardwareError`."""
        raise NotImplementedError

    def close(self) -> None:
        """Close the device."""
        raise NotImplementedError

    # -- I/O ------------------------------------------------------------

    def read(self, timeout_ms: int = 100) -> Optional[bytes]:
        """Return one raw CAN frame (or ``None`` if nothing arrived)."""
        raise NotImplementedError

    def write(self, frame: bytes) -> int:
        """Transmit a raw CAN frame.  Returns the number of bytes sent."""
        raise NotImplementedError

    # -- discovery ------------------------------------------------------

    def get_info(self) -> HardwareInfo:
        """Return the adapter's hardware description."""
        raise NotImplementedError

    def test(self) -> bool:
        """Send a heartbeat frame and check the adapter is alive."""
        return False

    # -- discovery helpers ----------------------------------------------

    def scan_devices(self) -> list[dict]:
        """Return a list of discovered devices (overridable by backends)."""
        return []
