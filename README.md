# MBTools-DTS
An open-source Mercedes-Benz diagnostic tool that combines the **mbtools**
protocol logic (ISO-TP / UDS), the **PT3G J2534** pass-thru hardware driver,
and the **DTS-Monaco** diagnostic workflow into a single Windows desktop
application.

## What you get
- **Windows-only** (PT3G J2534 is a Windows pass-thru driver).
- **Unified CLI** (`mbtools-dts`) for scripting and automation.
- **Unified GUI** (`mbtools-dts-gui`) for interactive diagnostics:
  - DTC / fault-code viewer
  - Live data / parameter read
  - Variant coding (SA code read/write)
  - ECU flashing
- **Hardware backends** (PT3G VCI over a J2534 adapter, and a headless
  virtual adapter for testing).

## Quick start (Windows)
1. Install the PT3G VCI USB adapter and open it in "J2534 mode" (the
   PT3G Device Manager).  Optionally install the official Actia PDU API so
   the legacy Windows backend also works.
2. Install the driver and this tool:
   ```
   # 1. build + install the PT3G J2534 driver (Windows .pyd)
   cd pt3g-j2534
   pip install -e .            # builds _pt3g_j2534.pyd into site-packages

   # 2. build + install this combined tool
   cd mbtools-dts
   pip install -e .
   ```
3. Run the GUI:
   ```
   mbtools-dts-gui
   ```
4. To automate from a script:
   ```
   mbtools-dts connect --baud 500000
   mbtools-dts read-dtcs
   mbtools-dts read-data-by-identifier --param 0x10000402
   mbtools-dts clear-dtc
   ```

## Repository layout
```
src/mbtools_dts/
├── cli.py                   # unified CLI entrypoint
├── config.py                # application configuration
├── engine.py                # unified diagnostic engine (session, sessions)
├── protocol_client.py       # UDS client over the CAN/ISO-TP stack
├── hardware/
│   ├── base.py              # CanHardwareAdapter + HardwareInfo
│   ├── pt3g_j2534.py        # PT3G VCI backend (J2534 pass-thru)
│   └── virtual.py           # headless FIFO virtual backend
├── protocols/
│   ├── can.py               # re-exported from mbtools.core.can
│   ├── isotp.py             # re-exported from mbtools.core.isotp
│   └── uds.py               # re-exported from mbtools.core.uds
├── logic/
│   ├── engine.py            # session management, DTC, variant coding, flash
│   ├── flashing.py          # BusMonitor + FlashProgrammer
│   └── logger.py            # timestamped bus log
└── gui/
    ├── main_window.py       # PySide6 main window
    └── views/               # DTC / live-data / coding workbenches
```

## License
GPL-3.0 (as shipped).
