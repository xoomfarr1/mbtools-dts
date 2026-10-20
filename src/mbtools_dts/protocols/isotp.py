"""ISO 15765-2 (ISO-TP) transport for CAN diagnostics.

This is a copy of ``mbtools.core.isotp``.  It turns one (arbitration id,
payload) pair into the ordered list of CAN frames to transmit, and reassembles
a stream of received CAN frames back into the original payload plus a protocol
status.  The flow-control handshake is the receiver's job -- this module only
recognises the 0x31/0x33 flow-control frames and builds FC frames for the
receiver to send.
"""

from __future__ import annotations

from .can import CANFrame, CAN_DLC_MAX, CAN_ID_EXT_MASK

FRAME_TYPE_SINGLE = 0x00
FRAME_TYPE_FIRST = 0x10
FRAME_TYPE_CONSECUTIVE = 0x20
FRAME_TYPE_FLOW_CONTROL = 0x30

PADDING_BYTE = 0xCC

FC_WAIT = 0x31
FC_OVERFLOW = 0x32
FC_ABORT = 0x33

SINGLE_DATA_LEN = 7
CONSECUTIVE_DATA_LEN = 7
MAX_PAYLOAD = 4095

STATUS_OK = 0
STATUS_FLOW_CONTROL = 0x24
STATUS_FLOW_CONTROL_ABORT = 0x25
STATUS_OVERFLOW = 0x23
STATUS_TOO_FEW = 0x21
STATUS_TOO_MANY = 0x22
STATUS_PROTOCOL_ERROR = 0x26


def _pad(data: bytes, length: int) -> bytes:
    if len(data) > length:
        raise ValueError(f"data longer than target length {length}")
    return data + bytes([PADDING_BYTE]) * (length - len(data))


def encode_single_frame(payload: bytes) -> bytes:
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    payload = bytes(payload)
    if not 0 <= len(payload) <= SINGLE_DATA_LEN:
        raise ValueError(f"single frame payload must be 0..{SINGLE_DATA_LEN} bytes")
    return bytes([FRAME_TYPE_SINGLE | len(payload)]) + _pad(payload, SINGLE_DATA_LEN)


def encode_first_frame(total_len: int, first_data: bytes = b"") -> bytes:
    if not isinstance(total_len, int) or not 8 <= total_len <= MAX_PAYLOAD:
        raise ValueError(f"first frame total length must be 8..{MAX_PAYLOAD}")
    if not isinstance(first_data, (bytes, bytearray)):
        raise TypeError("first_data must be bytes")
    first_data = bytes(first_data)
    if len(first_data) > 6:
        raise ValueError("first frame data may hold at most 6 bytes")
    return (
        bytes([FRAME_TYPE_FIRST | ((total_len >> 8) & 0x0F)]) + bytes([total_len & 0xFF])
        + _pad(first_data, 6)
    )


def encode_consecutive_frame(seq: int, payload: bytes) -> bytes:
    if not isinstance(seq, int) or not 0 <= seq <= 0x0F:
        raise ValueError("CF sequence number must be 0..15")
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    payload = bytes(payload)
    if not 0 <= len(payload) <= CONSECUTIVE_DATA_LEN:
        raise ValueError(f"CF payload must be 0..{CONSECUTIVE_DATA_LEN} bytes")
    return bytes([FRAME_TYPE_CONSECUTIVE | seq]) + _pad(payload, CONSECUTIVE_DATA_LEN)


def encode_flow_control(
    total_bytes: int,
    block_size: int = 6,
    st_min: int = 10,
    status: int = 0,
) -> bytes:
    if not isinstance(status, int) or not 0 <= status <= 3:
        raise ValueError("status must be 0..3")
    if not isinstance(block_size, int) or not 0 <= block_size <= 0xFF:
        raise ValueError("block_size must be 0..255")
    if not isinstance(st_min, int) or not 0 <= st_min <= 0xFF:
        raise ValueError("st_min must be 0..255")
    if not isinstance(total_bytes, int) or not 0 <= total_bytes <= 0xFF:
        raise ValueError("total_bytes must be 0..255")
    return (
        bytes([FRAME_TYPE_FLOW_CONTROL | status])
        + block_size.to_bytes(2, "big")
        + st_min.to_bytes(2, "big")
        + bytes([total_bytes])
        + bytes([PADDING_BYTE])
    )


def isotp_encode(frame, *, flow_control: bool = True) -> list[CANFrame]:
    if isinstance(frame, tuple) and len(frame) == 2:
        can_id, payload = frame
    else:
        raise TypeError("isotp_encode() expects a (can_id, payload) tuple")
    if isinstance(can_id, bool) or not isinstance(can_id, int):
        raise TypeError("can_id must be an int")
    if not 0 <= can_id <= CAN_ID_EXT_MASK:
        raise ValueError(f"can_id out of range: 0x{can_id:08X}")
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    payload = bytes(payload)
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"payload exceeds ISO 15765-2 maximum of {MAX_PAYLOAD} bytes")

    frames = []
    length = len(payload)
    if length <= SINGLE_DATA_LEN:
        frames.append(CANFrame(id=can_id, data=encode_single_frame(payload)))
        return frames

    first = (
        bytes([FRAME_TYPE_FIRST | ((length >> 8) & 0x0F)])
        + bytes([length & 0xFF])
        + payload[:6]
    )
    frames.append(CANFrame(id=can_id, data=first))

    seq = 1
    offset = 6
    while offset < length:
        chunk = payload[offset : offset + CONSECUTIVE_DATA_LEN]
        frames.append(CANFrame(id=can_id, data=encode_consecutive_frame(seq & 0x0F, chunk)))
        seq += 1
        offset += CONSECUTIVE_DATA_LEN

    return frames


def isotp_decode(frames) -> tuple[bytes | None, int]:
    if not isinstance(frames, (list, tuple)):
        raise TypeError("frames must be a list/tuple of bytes-like objects")

    payload_parts: list[bytes] = []
    state: str = "NEW"
    total_expected: int | None = None
    expected_seq: int = 0
    fc_status: int = 0

    for idx, fb in enumerate(frames):
        if isinstance(fb, (bytearray, memoryview)):
            fb = bytes(fb)
        if not isinstance(fb, bytes):
            raise TypeError(f"frame {idx} is not bytes-like")
        if not 1 <= len(fb) <= 8:
            return None, STATUS_PROTOCOL_ERROR

        b0 = fb[0]
        ptype = b0 >> 4

        if ptype == 0x0:  # single frame
            if state != "NEW":
                return None, STATUS_PROTOCOL_ERROR
            length = b0 & 0x0F
            if len(fb) < 1 + length:
                return None, STATUS_PROTOCOL_ERROR
            payload_parts.append(fb[1:1 + length])
            state = "DONE"
            return b"".join(payload_parts), STATUS_OK

        if ptype == 0x1:  # first frame
            if state != "NEW":
                return None, STATUS_PROTOCOL_ERROR
            if len(fb) < 8:
                return None, STATUS_PROTOCOL_ERROR
            total = ((b0 & 0x0F) << 8) | fb[1]
            if not 8 <= total <= MAX_PAYLOAD:
                return None, STATUS_PROTOCOL_ERROR
            payload_parts.append(fb[2:8])
            total_expected = total
            state = "WAITING"
            expected_seq = 1
            fc_status = 0

        elif ptype == 0x2:  # consecutive frame
            if state == "NEW":
                return None, STATUS_PROTOCOL_ERROR
            if state == "WAITING":
                if fc_status in (STATUS_OVERFLOW, STATUS_FLOW_CONTROL_ABORT):
                    return None, fc_status
                if fc_status == STATUS_FLOW_CONTROL:
                    return None, STATUS_FLOW_CONTROL
            seq = b0 & 0x0F
            if seq != expected_seq:
                return None, STATUS_PROTOCOL_ERROR
            payload_parts.append(fb[1:1 + CONSECUTIVE_DATA_LEN])
            expected_seq = (seq + 1) & 0x0F
            if len(b"".join(payload_parts)) >= total_expected:
                state = "DONE"

        elif ptype == 0x3:  # flow control frame
            if state not in ("WAITING", "NEW"):
                return None, STATUS_PROTOCOL_ERROR
            fs = b0 & 0x0F
            if not 0 <= fs <= 3:
                raise ValueError(f"invalid FC flow status 0x{fs:02X}")
            if fs == 1:
                return None, STATUS_FLOW_CONTROL
            if fs == 2:
                return None, STATUS_OVERFLOW
            if fs == 3:
                return None, STATUS_FLOW_CONTROL_ABORT

        else:
            return None, STATUS_PROTOCOL_ERROR

    if state == "WAITING":
        if total_expected is None:
            return None, STATUS_PROTOCOL_ERROR
        if not payload_parts:
            return None, STATUS_FLOW_CONTROL
        return None, STATUS_TOO_FEW
    if state == "NEW":
        return None, STATUS_PROTOCOL_ERROR
    payload = b"".join(payload_parts)
    if total_expected is None:
        return payload, STATUS_PROTOCOL_ERROR
    if len(payload) >= total_expected:
        return payload[:total_expected], STATUS_OK
    return None, STATUS_TOO_FEW
