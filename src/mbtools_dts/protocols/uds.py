"""MBTools UDS (ISO 14229) service helpers.

This is a copy of ``mbtools.core.uds``.  It holds the service-layer
interpretation in exactly one place: building UDS requests, decoding
responses, and parsing DTC records.  Nothing here touches a socket, a CAN id or
a VCI handle -- it works purely on bytes.
"""

from __future__ import annotations

SVC_TESTER_PRESENT = 0x10
SVC_ECHO = 0x11
SVC_REQUEST_SEED = 0x13
SVC_REQUEST_KEY = 0x14
SVC_READ_DTC_INFORMATION = 0x19
SVC_READ_DTC_BY_IDENTIFIER = 0x22
SVC_READ_MEMORY_BY_ADDRESS = 0x23
SVC_DATA_BY_IDENTIFIER = 0x24
SVC_READ_DTCS = 0x27
SVC_SECURITY_ACCESS = 0x3C
SVC_CONTROL_DTC_SETTING = 0x3E
SVC_REQUEST_DOWNLOAD = 0x3F
SVC_RESPONSE_ON_EVENT = 0x2F
SVC_READ_DTC_BY_IDENTIFIER = 0x22
SVC_WRITE_DATA_BY_IDENTIFIER = 0x2E
SVC_CLEAR_DTC = 0x14
RESP_PASS = 0x00
RESP_GENERIC_FAILED = 0x10
RESP_FUNCTION_NOT_SUPPORTED = 0x12

SUB_FUNC_REQUEST_SEED = 0x13
SUB_FUNC_REQUEST_KEY = 0x14
SUB_FUNC_READ_DTC_BY_STATUS_MASK = 0x01
SUB_FUNC_REPORT_DTC_BY_STATUS_MASK = 0x02
SUB_FUNC_CONTROL_DTC_SETTING = 0x01
SUB_FUNC_RESPONSE_TIMEOUT = 0x01
SUB_FUNC_RESPONSE_DELAY = 0x02

NRC = {
    0x00: "NoFault", 0x10: "GenericReject", 0x11: "ServiceNotSupported",
    0x12: "SubFunctionNotSupported", 0x13: "OpenSecurityAccess",
    0x14: "SecureMarketingDataNotAvailable",
    0x15: "SubFunctionNotSupportedInActiveSession", 0x16: "RequestSequenceError",
    0x17: "NoResponseFromSubnet", 0x18: "SubFunctionNotSupportedByECHOPacket",
    0x21: "RoutineNotRunning", 0x22: "RoutineNotValid", 0x23: "RequestOutstanding",
    0x24: "TooManyPrograms", 0x25: "SubFunctionOutOfRange",
    0x26: "RequestVerificationError", 0x27: "RequestKeyNotVerified",
    0x28: "RequestBeforeAuthentication", 0x31: "RoutinePerformed",
    0x33: "SecurityAccessDenied", 0x35: "DoesNotSupportDTCs",
    0x36: "ValidMemoryDenied", 0x37: "InvalidKey", 0x38: "ConditionsNotCorrect",
    0x39: "DTCInformationNotAvailable",
    0x78: "RequestCorrectlyReceived_ResponsePending",
}

_DTC_SEVERITY_FLAGS = (
    ("test_failed", 0x01), ("failed_this_cycle", 0x02), ("pending", 0x04),
    ("confirmed", 0x08), ("not_completed_since_clear", 0x10),
    ("failed_since_clear", 0x20), ("not_completed_this_cycle", 0x40), ("mil_on", 0x80),
)

_SYSTEM_TO_TYPE = {0: "P", 1: "C", 2: "B", 3: "U"}
_SYSTEM_NAMES = {0: "powertrain", 1: "chassis", 2: "body", 3: "network"}


def build_session_request(session_type, sub_function=None, data=b""):
    if isinstance(session_type, int):
        service = session_type
        payload = bytes(data) if data else b""
        if sub_function is None:
            return bytes([service]) + payload
        return bytes([service, sub_function]) + payload
    if isinstance(session_type, (tuple, list)) and session_type:
        service = session_type[0]
        sub_function = session_type[1] if len(session_type) > 1 else None
        data = session_type[2] if len(session_type) > 2 else b""
        payload = bytes(data) if data else b""
        if sub_function is None:
            return bytes([service]) + payload
        return bytes([service, sub_function]) + payload
    raise TypeError("session_type must be an int service id or a (service[, sub], [data]) tuple")


def positive_response(service: int, sub_function: int, data: bytes = b"") -> bytes:
    return bytes([service + 0x40, sub_function]) + bytes(data)


def tester_present_request() -> bytes:
    return build_session_request(SVC_TESTER_PRESENT)


def echo_request(data: bytes = b"") -> bytes:
    return build_session_request(SVC_ECHO, data=data)


def request_seed_request(seed: bytes = b"") -> bytes:
    return build_session_request(SVC_REQUEST_SEED, data=seed)


def request_key_request(key: bytes = b"") -> bytes:
    return build_session_request(SVC_REQUEST_KEY, data=key)


def read_dtcs_request(dtc_buffer_mask: int = 0x80, number_of_buffers: int = 1) -> bytes:
    if not 0 <= dtc_buffer_mask <= 0xFF or not 0 <= number_of_buffers <= 8:
        raise ValueError("buffer mask must be 0..255, buffers 0..8")
    payload = bytes([dtc_buffer_mask, number_of_buffers])
    for _ in range(number_of_buffers):
        payload += bytes([dtc_buffer_mask, 0, 0, 0])
    return build_session_request(
        SVC_READ_DTCS,
        sub_function=SUB_FUNC_READ_DTC_BY_STATUS_MASK,
        data=payload,
    )


def read_dtc_information_request(dtc_buffer_mask: int = 0x80, number_of_buffers: int = 1) -> bytes:
    return _read_report_dtc_request(
        SVC_READ_DTC_INFORMATION, SUB_FUNC_REPORT_DTC_BY_STATUS_MASK,
        dtc_buffer_mask, number_of_buffers,
    )


def _read_report_dtc_request(service, sub_function, dtc_buffer_mask, number_of_buffers):
    if not 0 <= dtc_buffer_mask <= 0xFF or not 0 <= number_of_buffers <= 8:
        raise ValueError("buffer mask must be 0..255, buffers 0..8")
    payload = bytes([dtc_buffer_mask, number_of_buffers])
    for _ in range(number_of_buffers):
        payload += bytes([dtc_buffer_mask, 0, 0, 0])
    return build_session_request(service, sub_function, data=payload)


def read_memory_by_address_request(address: int, number_of_bytes: int = 1) -> bytes:
    if not 0 <= number_of_bytes <= 0xFF:
        raise ValueError("number_of_bytes must be 0..255")
    return build_session_request(
        SVC_READ_MEMORY_BY_ADDRESS,
        sub_function=0x00,
        data=bytes([address >> 24, address >> 16, address >> 8, address & 0xFF, number_of_bytes]),
    )


def data_by_identifier_request(parameter_id: int, data_identifiers: bytes = b"") -> bytes:
    if not 0 <= len(data_identifiers) <= 63:
        raise ValueError("data identifiers must be 0..63 bytes")
    return build_session_request(
        SVC_DATA_BY_IDENTIFIER,
        sub_function=SUB_FUNC_CONTROL_DTC_SETTING,
        data=bytes([parameter_id]) + bytes(data_identifiers),
    )


def read_data_by_identifier_request(parameter_id: int, data_identifiers: bytes = b"") -> bytes:
    if not 0 <= len(data_identifiers) <= 63:
        raise ValueError("data identifiers must be 0..63 bytes")
    return build_session_request(
        SVC_READ_DTC_BY_IDENTIFIER,
        sub_function=0x01,
        data=bytes([parameter_id]) + bytes(data_identifiers),
    )


def write_data_by_identifier_request(parameter_id: int, data: bytes = b"") -> bytes:
    if not 1 <= len(data) <= 63:
        raise ValueError("data must be 1..63 bytes")
    return build_session_request(
        SVC_WRITE_DATA_BY_IDENTIFIER,
        sub_function=0x01,
        data=bytes([parameter_id]) + bytes(data),
    )


def control_dtc_setting_request(control_mode: int, mask: int = 0x00) -> bytes:
    if control_mode not in (0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07):
        raise ValueError("invalid control mode")
    return build_session_request(
        SVC_CONTROL_DTC_SETTING,
        sub_function=SUB_FUNC_CONTROL_DTC_SETTING,
        data=bytes([control_mode, mask]),
    )


def ecu_reset_request(control_mode: int, mask: int = 0x00) -> bytes:
    return control_dtc_setting_request(control_mode, mask)


def request_download_request(address: int, block_size: int = 1, block_count: int = 1) -> bytes:
    if not 0 <= block_size <= 0xFF or not 0 < block_count <= 0xFFFF:
        raise ValueError("block_size 0..255, block_count 1..65535")
    return build_session_request(
        SVC_REQUEST_DOWNLOAD,
        sub_function=SUB_FUNC_RESPONSE_TIMEOUT,
        data=bytes([address >> 24, (address >> 16) & 0xFF, (address >> 8) & 0xFF, address & 0xFF,
                   block_size & 0xFF, block_count & 0xFF]),
    )


def response_on_event_request(timeout: int = 0, delay: int = 0) -> bytes:
    return build_session_request(
        SVC_RESPONSE_ON_EVENT, sub_function=SUB_FUNC_RESPONSE_TIMEOUT, data=bytes([timeout, delay])
    )


def decode_response(raw: bytes) -> dict:
    if not raw:
        raise ValueError("decode_response() expects a non-empty payload")
    res = {"positive": None, "service": None, "sub_function": 0, "data": b"", "status": None}
    if raw[0] == 0x7F:
        res["positive"] = False
        res["service"] = raw[1]
        res["sub_function"] = raw[2] if len(raw) > 2 else 0
        res["status"] = raw[3] if len(raw) > 3 else None
    else:
        res["positive"] = True
        res["service"] = raw[0]
        res["sub_function"] = raw[1] if len(raw) > 1 else 0
        res["data"] = raw[2:]
    return res


def nrc_name(status: int) -> str:
    return NRC.get(status, f"Unknown (0x{status:02X})")


def parse_dtc_response(data: bytes) -> list[dict]:
    if len(data) < 1:
        return []
    count = data[0]
    rest = data[1:]
    if len(rest) % 4 == 0:
        record_len = 4
    elif len(rest) % 3 == 0:
        record_len = 3
    else:
        raise ValueError(f"malformed DTC response payload: length {len(data)} (count {count}, rest {len(rest)})")
    if record_len == 4 and len(rest) != 4 * count:
        raise ValueError(f"4-byte record count mismatch: {len(rest)} bytes vs {count} records")
    if record_len == 3 and len(rest) != 3 * count:
        raise ValueError(f"3-byte record count mismatch: {len(rest)} bytes vs {count} records")

    records = []
    for i in range(count):
        base = 1 + i * record_len
        if base + record_len > len(data):
            raise ValueError(f"truncated DTC record {i} in payload of length {len(data)}")
        if record_len == 4:
            code = int.from_bytes(data[base:base + 3], "big")
            status = data[base + 3]
        else:
            code = int.from_bytes(data[base:base + 2], "big")
            status = data[base + 2]
        system = (code >> 22) & 0x03 if record_len == 4 else (code >> 14) & 0x03
        severity_parts = [name for name, mask in _DTC_SEVERITY_FLAGS if status & mask]
        records.append({
            "code": code,
            "type": _SYSTEM_TO_TYPE.get(system, "X"),
            "severity": "|".join(severity_parts) if severity_parts else "clear",
            "status": status,
        })
    return records
