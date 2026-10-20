from __future__ import annotations

__app_name__ = "mbtools-dts"
__version__ = "1.0.0"

# Re-exported protocol stack (from mbtools.core).
from . import protocols as _protocols
from .protocols import can as _can
from .protocols import ecu as _ecu
from .protocols import isotp as _isotp
from .protocols import uds as _uds

# Sub-packages (imported so the dotted names resolve anywhere).
from . import engine
from . import hardware
from . import logic

# Public entry points.
from . import cli

# VIN helpers.
from .protocols import ecu as _ecu_public

__all__ = [
    "__app_name__", "__version__",
    # protocols
    "__can__", "__isotp__", "__uds__", "__ecu__",
    "CANFrame", "encode", "decode", "CAN_ID_EXT_MASK", "CAN_DLC_MAX",
    "CAN_MAX_LEN", "CAN_BITTIMING", "ISO_TP_PADDING_BYTE",
    "FRAME_TYPE_SINGLE", "FRAME_TYPE_FIRST", "FRAME_TYPE_CONSECUTIVE",
    "FRAME_TYPE_FLOW_CONTROL", "PADDING_BYTE", "FC_WAIT", "FC_OVERFLOW",
    "FC_ABORT", "SINGLE_DATA_LEN", "CONSECUTIVE_DATA_LEN", "MAX_PAYLOAD",
    "STATUS_OK", "STATUS_FLOW_CONTROL", "STATUS_FLOW_CONTROL_ABORT",
    "STATUS_OVERFLOW", "STATUS_TOO_FEW", "STATUS_TOO_MANY",
    "STATUS_PROTOCOL_ERROR",
    # uds
    "SVC_TESTER_PRESENT", "SVC_ECHO", "SVC_REQUEST_SEED", "SVC_REQUEST_KEY",
    "SVC_READ_DTC_INFORMATION", "SVC_READ_DTC_BY_IDENTIFIER",
    "SVC_DATA_BY_IDENTIFIER", "SVC_READ_MEMORY_BY_ADDRESS",
    "SVC_READ_DTCS", "SVC_SECURITY_ACCESS", "SVC_CONTROL_DTC_SETTING",
    "SVC_REQUEST_DOWNLOAD", "SVC_RESPONSE_ON_EVENT",
    "SVC_READ_DTC_BY_IDENTIFIER", "SVC_WRITE_DATA_BY_IDENTIFIER",
    "SVC_CLEAR_DTC", "RESP_PASS", "RESP_GENERIC_FAILED",
    "RESP_FUNCTION_NOT_SUPPORTED", "NRC", "build_session_request",
    "positive_response", "nrc_name", "parse_dtc_response",
    # ecu
    "identify_maker", "model_year_from_char", "validate_vin", "parse_vin",
    # sub-packages (convenience)
    "engine", "hardware", "logic", "gui", "cli",
]