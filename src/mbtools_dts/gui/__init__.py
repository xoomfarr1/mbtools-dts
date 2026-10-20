"""Package init for the desktop GUI.

The real importable gui package is ``mbtools_dts.gui``.  This alias only exists
to make dotted-name resolution match the mbtools-open layout.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REAL_ROOT = _HERE.parent
if str(_REAL_ROOT) not in sys.path:
    sys.path.insert(0, str(_REAL_ROOT))

import gui as _gui  # noqa: E402  (absolute import of the sibling package)

sys.modules.setdefault("mbtools_dts.gui", _gui)

__all__ = []
