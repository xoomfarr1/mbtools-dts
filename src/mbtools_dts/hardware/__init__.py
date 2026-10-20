"""Hardware backends for mbtools-dts.

Backends (plug-and-play, selected by the engine):

* :class:`virtual.VirtualAdapter`   -- in-memory CAN bus, no hardware.
* :class:`pt3g_j2534.Pt3gJ2534Adapter` -- the PT3G VCI over a J2534 pass-thru
  adapter (the open-source PT3G driver).  Windows-only.

The public surface is intentionally small: everything above the hardware layer
talks to a :class:`CanHardwareAdapter`, so swapping a physical PT3G VCI for a
virtual bus (for tests or for machines with no adapter) is a one-line change.
"""

from __future__ import annotations

from .base import CanHardwareAdapter, HardwareError, HardwareInfo, HardwareType

# The PT3G J2534 driver backend (imported lazily; the compiled driver may not
# be present yet, in which case the adapter falls back to the virtual adapter).
from . import pt3g_j2534

__all__ = [
    "CanHardwareAdapter", "HardwareError", "HardwareInfo", "HardwareType",
    "get_hardware_adapter", "pt3g_j2534",
]


def get_hardware_adapter(baud: int = 500000):
    """Return the platform-default adapter (virtual on headless machines).

    Callers that need a specific backend should import it directly instead of
    going through this helper.
    """
    # The default is the headless virtual adapter.  The PT3G/VCI backend is only
    # selected when a real adapter exists (the CLI asks for it explicitly).
    try:
        from .virtual import VirtualAdapter

        return VirtualAdapter()
    except Exception:
        return None
