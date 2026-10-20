"""Headless virtual CAN adapter.

A pure-FIFO virtual backend.  No hardware, no dongle -- the bus is simulated in
memory.  It is used for tests and by machines that do not have a PT3G adapter
attached.  The virtual adapter still speaks the :class:`CanHardwareAdapter`
contract, so the rest of the toolchain is unaffected.

Usage
-----
    adapter = VirtualAdapter()
    adapter.open()
    adapter.write(b"\\x00\\x00\\x00\\x01\\x01\\x00")   # beat the bus
    frame = adapter.read(100)                          # wait up to 100 ms
    adapter.close()
"""

from __future__ import annotations

import queue
import threading
from typing import Optional

from .base import CanHardwareAdapter, HardwareError, HardwareInfo, HardwareType


class VirtualAdapter(CanHardwareAdapter):
    """A simulated CAN bus: frames written by one peer can be read by another."""

    def __init__(self, name: str = "virtual"):
        self._name = name
        self._tx = queue.Queue()  # frames written by peers
        self._rx = queue.Queue()  # frames queued for reads
        self._lock = threading.Lock()
        self._open = False
        self.handle = 0

    def open(self, mode: int = 0) -> None:
        if self._open:
            return
        self._open = True

    def close(self) -> None:
        self._open = False

    def read(self, timeout_ms: int = 100) -> Optional[bytes]:
        if not self._open:
            return None
        try:
            frame = self._rx.get(timeout=timeout_ms / 1000.0)
            return frame
        except queue.Empty:
            return None

    def write(self, frame: bytes) -> int:
        if not self._open:
            return 0
        self._tx.put(frame)
        # The "peer" reads from _rx; when the bus mirrors, we also queue for
        # reads so a single writer is seen by a single reader.
        with self._lock:
            self._rx.put(frame)
        return len(frame)

    def get_version(self) -> tuple:
        return (1, 0)

    def get_driver_description(self) -> str:
        return f"Virtual CAN adapter ({self._name})"

    def scan_devices(self) -> list:
        return [{"device_handle": 0, "name": f"PT3G-VCI (virtual: {self._name})"}]

    def get_next_device(self):
        return None

    def get_info(self) -> HardwareInfo:
        return HardwareInfo(
            kind=HardwareType.VIRTUAL,
            port=f"virtual ({self._name})",
            vendor_id="MBTools-DTS",
            product_id="vcan",
            serial="0",
        )
