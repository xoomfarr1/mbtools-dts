"""python -m mbtools_dts -- unified entry point (same CLI as mbtools-dts)."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
