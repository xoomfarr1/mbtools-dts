"""MBTools CAN layer -- ISO 11898-1 frame encode / decode.

This is a copy of ``mbtools.core.can``.  It is the wire format that every
higher layer (ISO-TP, UDS, J1939) agrees on: it turns a 29-bit identifier plus
a 0..8-byte payload into the bytes the PT3G VCI transmits, and reverses the
operation on bytes that arrive off the bus.

Frame layout (ISO 11898-1 base frame, start-of-frame byte first)::

    byte 0  : start byte + ID class
        0x00 = SFF  (standard format, 11-bit identifier, IDE=0)
        0x01 = EFF  (extended format, 29-bit identifier, IDE=1)
    bytes 1-4: identifier, big-endian over 29 bits
    byte 5  : data length code (DLC), lower nibble only
    bytes 6..: payload, 0 .. CAN_DLC_MAX bytes
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

__all__ = [
    "CANFrame", "encode", "decode", "CAN_ID_EXT_MASK", "CAN_DLC_MAX",
    "CAN_MAX_LEN", "CAN_BITTIMING", "CAN_STATUS_OK", "CAN_STATUS_BUS_OFF",
    "CAN_STATUS_ERR_PASSIVE", "CAN_STATUS_BUS_LOCKED", "ISO_TP_PADDING_BYTE",
    "CTRL_DATA_STD", "CTRL_DATA_EXT", "CTRL_REMOTE_STD", "CTRL_REMOTE_EXT",
    "is_extended_frame", "pack_can_frame", "split_can_id",
]

# Frame class markers.
CTRL_DATA_STD = 0x00
CTRL_DATA_EXT = 0x40
CTRL_REMOTE_STD = 0x80
CTRL_REMOTE_EXT = 0xC0

CAN_ID_EXT_MASK = 0x1FFFFFFE
CAN_DLC_MAX = 8
CAN_MAX_LEN = 6 + CAN_DLC_MAX
CAN_MAX_DLC = 8
CAN_ID_DIAGNOSTIC = 0x7DF

CAN_BITTIMING = {
    "baudrate": 500_000,
    "sjw": 8,
    "prop_seg": 8,
    "phase_seg1": 10,
    "phase_seg2": 3,
    "sample_point": 80,
}

CAN_STATUS_OK = 0x00
CAN_STATUS_BUS_OFF = 0x01
CAN_STATUS_ERR_PASSIVE = 0x02
CAN_STATUS_BUS_LOCKED = 0x03

ISO_TP_PADDING_BYTE = 0xFC


@dataclass(frozen=True)
class CANFrame:
    id: int
    data: bytes
    ack: bool = False


def encode(can_id: int, data: bytes) -> bytes:
    if isinstance(can_id, bool) or not isinstance(can_id, int):
        raise TypeError("can_id must be an int")
    if not 0 <= can_id <= CAN_ID_EXT_MASK:
        raise ValueError(f"can_id out of range: 0x{can_id:08X}")
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes")
    data = bytes(data)
    if not 0 <= len(data) <= CAN_DLC_MAX:
        raise ValueError(f"payload must be 0..{CAN_DLC_MAX} bytes (got {len(data)})")

    extended = can_id > 0x7FF
    start = 0x01 if extended else 0x00
    id_bytes = struct.pack(">I", can_id)
    return bytes([start]) + id_bytes + bytes([len(data)]) + data


def decode(frame_bytes) -> CANFrame:
    if isinstance(frame_bytes, (bytearray, memoryview)):
        frame_bytes = bytes(frame_bytes)
    if not isinstance(frame_bytes, bytes):
        raise TypeError("frame_bytes must be bytes")
    if len(frame_bytes) < 6 or len(frame_bytes) > CAN_MAX_LEN:
        raise ValueError(f"CAN frame too short or long: {len(frame_bytes)} bytes")

    b0 = frame_bytes[0]
    if b0 not in (0x00, 0x01):
        raise ValueError(f"invalid start byte 0x{b0:02X}")

    extended = bool(b0 & 0x01)
    can_id = int.from_bytes(frame_bytes[1:5], "big")
    if extended:
        if can_id > CAN_ID_EXT_MASK:
            raise ValueError(f"identifier exceeds 29 bits: 0x{can_id:08X}")
    else:
        if can_id > 0x7FF:
            raise ValueError(f"standard frame identifier exceeds 11 bits: 0x{can_id:08X}")

    dlc = frame_bytes[5] & 0x0F
    if not 0 <= dlc <= CAN_DLC_MAX:
        raise ValueError(f"DLC out of range: {dlc}")

    data = frame_bytes[6 : 6 + dlc]
    if len(data) != dlc:
        raise ValueError(f"frame too short for declared DLC ({len(data)} of {dlc})")

    ack = bool(b0 & 0x40)
    return CANFrame(id=can_id, data=data, ack=ack)


def is_extended_frame(data: bytes) -> bool:
    return bool(data) and (data[0] & CTRL_DATA_EXT) != 0


def pack_can_frame(can_id: int, payload: bytes, extended: bool = False) -> bytes:
    if not 0 <= can_id <= CAN_ID_EXT_MASK:
        raise ValueError(f"can_id out of range: 0x{can_id:08X}")
    if len(payload) > CAN_MAX_DLC:
        raise ValueError(f"payload exceeds CAN max DLC ({CAN_MAX_DLC})")
    control = CTRL_DATA_EXT if extended else CTRL_DATA_STD
    return bytes([control, can_id & 0xFF]) + bytes(payload[:CAN_MAX_DLC])


def split_can_id(data: bytes):
    if len(data) < 2:
        return None, False, False, b""
    control = data[0]
    extended = bool(control & CTRL_DATA_EXT)
    rtr = bool(control & CTRL_REMOTE_STD)
    can_id = data[1]
    payload = bytes(data[2:])
    return can_id, extended, rtr, payload
