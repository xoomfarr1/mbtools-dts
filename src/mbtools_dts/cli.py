"""Unified CLI for mbtools-dts.

Entry point (also ``python -m mbtools_dts``):

    mbtools-dts connect --adapter pt3g --baud 500000
    mbtools-dts tester-present
    mbtools-dts echo --data hello
    mbtools-dts scan
    mbtools-dts read-dtcs
    mbtools-dts read-data --param 0x10000402
    mbtools-dts write-data --param 0x10000402 --value 0x1234
    mbtools-dts clear-dtc
    mbtools-dts disconnect

Example
-------
Connect to the PT3G VCI and read the DTCs:

    mbtools-dts connect --adapter pt3g
    mbtools-dts read-dtcs
    mbtools-dts disconnect
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Settings
from .engine import LogicEngine
from .hardware import HardwareError, get_hardware_adapter

_IGNORED_MBTOOLS_OPTIONS = {"--mbcode", "--nographic", "--log"}


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.  No command handlers are *run*, only
    registered, so parsing and execution are cleanly separated."""
    p = argparse.ArgumentParser(
        prog="mbtools-dts",
        description="Open-source Mercedes-Benz diagnostics: mbtools + DTS-Monaco + PT3G J2534.",
    )
    sub = p.add_subparsers(dest="command", help="subcommand")

    # --- connect ----------------------------------------------------------
    s = sub.add_parser("connect", help="connect to a hardware adapter")
    s.add_argument(
        "--adapter", choices=["pt3g", "virtual"], default="pt3g",
        help="hardware backend (default: pt3g).",
    )
    s.add_argument("--baud", type=int, default=500000,
                   help="CAN baud rate (default: 500000).")

    sub.add_parser("disconnect", help="disconnect from the current session")
    sub.add_parser("scan", help="scan for available hardware adapters")

    # --- diagnose ---------------------------------------------------------
    s = sub.add_parser("diagnose", help="run a full UDS diagnosis")
    s.add_argument("--service", type=lambda x: int(x, 0), default=0x10)
    s.add_argument("--data", type=str, default="")

    sub.add_parser("tester-present", help="send a 0x10 Tester Present")
    sub.add_parser("echo", help="send a 0x11 Echo request")

    # --- read dtcs --------------------------------------------------------
    s = sub.add_parser("read-dtcs", help="read DTCs from the ECU")
    s.add_argument("--mask", type=lambda x: int(x, 0), default=0x80,
                   help="DTC buffer mask (default: 0x80).")

    # --- read data --------------------------------------------------------
    s = sub.add_parser("read-data", help="read a data-by-identifier parameter")
    s.add_argument("--param", type=lambda x: int(x, 0), required=True)
    s.add_argument("--sub", type=lambda x: int(x, 0), default=0x00)

    # --- write data -------------------------------------------------------
    s = sub.add_parser("write-data", help="write a data-by-identifier parameter")
    s.add_argument("--param", type=lambda x: int(x, 0), required=True)
    s.add_argument(
        "--value", type=lambda x: bytes.fromhex(x[2:]) if x.startswith("0x") else x.encode(),
        required=True,
        help="hex value, e.g. 0x12 or 'hello'.",
    )

    sub.add_parser("clear-dtc", help="clear fault memory")
    sub.add_parser("flash", help="start an ECU flash operation (advanced)")

    return p


def _get_adapter(args):
    adapter_name = getattr(args, "adapter", "virtual")
    baud = getattr(args, "baud", 500000)
    if adapter_name == "virtual":
        from .hardware.virtual import VirtualAdapter

        return VirtualAdapter()
    return get_hardware_adapter(baud=baud)


def _connect(args):
    settings = Settings()
    engine = LogicEngine()
    adapter = _get_adapter(args)
    try:
        adapter.open()
    except HardwareError as err:
        print(f"ERROR: could not open adapter: {err}")
        return 1
    try:
        ecus = engine.scan_ecus(adapter)
        print(f"Connected to {len(ecus)} ECU(s):")
        for ecu in ecus:
            print(f"  - {ecu.name} (type={ecu.ecuc_type})")
        settings.hardware = args.adapter
        settings.save(Path.home() / ".mbtools-dts" / "settings.json")
        print(f"Adapter: {adapter.get_info()}")
    finally:
        adapter.close()
    return 0


def _disconnect(_args):
    print("Disconnected.")
    return 0


def _scan(_args):
    adapters = get_hardware_adapter().scan_devices()
    print(f"Found {len(adapters)} device(s):")
    for a in adapters:
        print(f"  - {a.get('description', a.get('name', 'unknown'))}")
    return 0


def _read_dtcs(args):
    engine = LogicEngine()
    adapter = _get_adapter(args)
    try:
        engine.connect(adapter)
        for r in engine.read_dtcs(dtc_buffer_mask=args.mask):
            print(f"  {r['code']} ({r['severity']})")
    finally:
        engine.disconnect()
    return 0


def _read_data(args):
    engine = LogicEngine()
    adapter = _get_adapter(args)
    try:
        engine.connect(adapter)
        print(f"0x{args.param:06X} = {engine.read_data_by_identifier(parameter_id=args.param).hex()}")
    finally:
        engine.disconnect()
    return 0


def _write_data(args):
    engine = LogicEngine()
    adapter = _get_adapter(args)
    try:
        engine.connect(adapter)
        engine.write_data_by_identifier(args.param, args.value)
        print(f"Wrote 0x{args.param:06X} = {args.value.hex()}")
    finally:
        engine.disconnect()
    return 0


def _clear_dtc(_args):
    engine = LogicEngine()
    adapter = _get_adapter(_args)
    try:
        engine.connect(adapter)
        engine.control_dtc_setting(control_mode=0x01)
        print("DTCs cleared.")
    finally:
        engine.disconnect()
    return 0


def _flash(_args):
    print("FLASH not implemented in this scaffold.")
    return 0


_HANDLERS = {
    "connect": _connect,
    "disconnect": _disconnect,
    "scan": _scan,
    "tester-present": lambda a: 0,
    "echo": lambda a: 0,
    "read-dtcs": _read_dtcs,
    "read-data": _read_data,
    "write-data": _write_data,
    "clear-dtc": _clear_dtc,
    "flash": _flash,
    "diagnose": lambda a: 0,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    handler = _HANDLERS.get(args.command)
    if handler is None:
        print(f"ERROR: unknown command {args.command}", file=sys.stderr)
        return 1
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
