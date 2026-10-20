"""UDS client over the mbtools protocol stack.

The client is the single place where a diagnostic *service* is turned into a
raw CAN/ISO-TP exchange.  It depends on the protocol layers:

    CANFrame (core.can)     -> raw CAN frame encode/decode
    isotp (core.isotp)      -> ISO 15765-2 fragmentation / reassembly
    uds   (core.uds)        -> service builders + response decoders

Its job is wire-level: build a request payload, send it over the adapter,
reconstruct the reply, and hand the decoded result back to the caller.
"""

from __future__ import annotations

from dataclasses import dataclass

from .protocols import can as _can
from .protocols import isotp as _isotp
from .protocols import uds as _uds
from .hardware.base import CanHardwareAdapter


@dataclass
class ClientSession:
    """One live connection to an ECU."""

    adapter: CanHardwareAdapter
    uds: "_UdsClient"

    @property
    def name(self):
        return self.uds._ecu_name or "unknown"


class _UdsClient:
    """Thin UDS wrapper that sends requests over a -> adapter -> bus -> reply."""

    def __init__(self, adapter: CanHardwareAdapter, ecu_name: str = "unknown"):
        self.adapter = adapter
        self._ecu_name = ecu_name
        self._session = None

    # -- session management ------------------------------------------------

    def connect(self, session_type: int = 0x10) -> None:
        """Open an application session (default: 0x10 Tester Present -> extended
        diagnostic session)."""
        self._session = session_type
        self.send(session_type)

    def disconnect(self) -> None:
        if self._session is not None:
            self.send(
                _uds.SVC_CONTROL_DTC_SETTING,
                sub_function=0x01,
                data=b"\x01\x00",
            )
            self._session = None

    # -- request helpers -------------------------------------------------

    def _send(self, payload: bytes, expect_response: bool = True, timeout_ms: int = 2000):
        self.adapter.write(payload)
        if not expect_response:
            return b""
        return self.adapter.read(timeout_ms) or b""

    def send(self, service: int, sub_function: int = 0x00, data: bytes = b"") -> bytes:
        """Build + send a UDS request and return the *raw* answer payload."""
        request = _uds.build_session_request(
            service, sub_function=sub_function, data=data
        )
        return self._send(request)

    def read_dtcs(self, dtc_buffer_mask: int = 0x80, number_of_buffers: int = 1) -> list[dict]:
        request = _uds.read_dtcs_request(dtc_buffer_mask=dtc_buffer_mask, number_of_buffers=number_of_buffers)
        raw = self.send(_uds.SVC_READ_DTCS, sub_function=0x01, data=request)
        return _uds.parse_dtc_response(raw)

    def read_data_by_identifier(self, parameter_id: int, data_identifiers: bytes = b"") -> bytes:
        request = _uds.read_data_by_identifier_request(parameter_id, data_identifiers)
        raw = self.send(_uds.SVC_READ_DTC_BY_IDENTIFIER, sub_function=0x01, data=request)
        resp = self.decode(raw)
        if not resp["positive"]:
            raise RuntimeError(f"UDS {nrc_name(resp['status'])}")
        return resp["data"]

    # -- decode ----------------------------------------------------------

    def decode(self, raw: bytes) -> dict:
        return _uds.decode_response(raw)

    @property
    def session(self):
        return self._session


class UdsClient:
    """High-level UDS client over a CanHardwareAdapter."""

    def __init__(self, adapter: CanHardwareAdapter, ecu_name: str = "unknown"):
        self.adapter = adapter
        self._uds = _UdsClient(adapter, ecu_name)

    def connect(self, session_type: int = 0x10) -> None:
        self._uds.connect(session_type)

    def disconnect(self) -> None:
        self._uds.disconnect()

    def send(self, service: int, sub_function: int = 0x00, data: bytes = b"") -> bytes:
        return self._uds.send(service, sub_function, data)

    def read_dtcs(self, dtc_buffer_mask: int = 0x80, number_of_buffers: int = 1) -> list[dict]:
        request = _uds.read_dtcs_request(dtc_buffer_mask=dtc_buffer_mask, number_of_buffers=number_of_buffers)
        raw = self.send(
            _uds.SVC_READ_DTCS, sub_function=0x01, data=request
        )
        return _uds.parse_dtc_response(raw)

    def read_data_by_identifier(self, parameter_id: int, data_identifiers: bytes = b"") -> bytes:
        request = _uds.read_data_by_identifier_request(parameter_id, data_identifiers)
        raw = self.send(
            _uds.SVC_READ_DTC_BY_IDENTIFIER, sub_function=0x01, data=request
        )
        resp = self._uds.decode(raw)
        if not resp["positive"]:
            raise RuntimeError(f"UDS {nrc_name(resp['status'])}")
        return resp["data"]
