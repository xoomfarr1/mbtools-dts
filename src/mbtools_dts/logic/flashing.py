"""BusMonitor and FlashProgrammer.

These two classes own the *bus* and the *flash* side of the engine:

    BusMonitor       -- captures every CAN frame the bus sees into a log.
    FlashProgrammer  -- walks a firmware image and uploads it to the ECU.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..hardware.base import CanHardwareAdapter
from ..protocols import uds as _uds
from ..protocols.uds import positive_response


class BusMonitor:
    """Captures every CAN frame on the bus into a log."""

    def __init__(self, adapter: CanHardwareAdapter, log_path: Path | None = None):
        self.adapter = adapter
        self.log_path = log_path or (Path.cwd() / "bus.log")
        self.frames: list[bytes] = []

    def start(self) -> None:
        print("BusMonitor started (capturing frames).")

    def stop(self) -> None:
        import json

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as fh:
            json.dump(
                [
                    {"frame": f.hex(), "timestamp": t}
                    for f, t in self.frames
                ],
                fh,
                indent=2,
            )
        print(f"BusMonitor stopped. {len(self.frames)} frames logged to {self.log_path}")

    def capture(self, frame: bytes, timestamp: float = 0.0) -> None:
        self.frames.append((frame, timestamp))


class FlashProgrammer:
    """Walks a firmware image and uploads it to the ECU.

    The real sequence is RequestDownload -> Download -> TransferExit.  The
    details are vehicle-specific; this scaffold shows the pattern and leaves
    the service-id mapping to the caller (override ``flash`` in a subclass if
    you need a particular vehicle's sequence).
    """

    # The classic Mercedes diagnostic "ECU download" service ids (ISO 14229-1).
    SVC_REQUEST_DOWNLOAD = 0x3F
    SVC_TRANSFER_EXIT = 0x3D
    SVC_REQUEST_TRANSFER = 0x3E

    SERVICE_ID_LOOKUP = {
        "request_download": SVC_REQUEST_DOWNLOAD,
        "transfer_exit": SVC_TRANSFER_EXIT,
        "request_transfer": SVC_REQUEST_TRANSFER,
    }

    def __init__(self, adapter: CanHardwareAdapter, block_size: int = 1):
        self.adapter = adapter
        self.block_size = block_size
        self._image: bytes = b""

    def load(self, image_path: Path) -> None:
        self._image = image_path.read_bytes()

    def request_download(self, image_address: int, block_size: int):
        """Send 0x3F RequestDownload."""
        payload = bytes(
            [
                (image_address >> 24) & 0xFF,
                (image_address >> 16) & 0xFF,
                (image_address >> 8) & 0xFF,
                image_address & 0xFF,
                block_size & 0xFF,
                0x00,  # block count placeholder
            ]
        )
        self.adapter.write(payload)
        print(f"Flash: RequestDownload @ 0x{image_address:08X}, block_size={block_size}")

    def transfer_exit(self, transfer_exit_type: int = 0):
        self.adapter.write(bytes([self.SVC_TRANSFER_EXIT, transfer_exit_type]))
        print("Flash: TransferExit sent.")

    def start(self, session) -> None:
        """Kick off the flash: RequestDownload + TransferExit."""
        self.request_download(image_address=0x00000000, block_size=self.block_size)
        self.transfer_exit()
