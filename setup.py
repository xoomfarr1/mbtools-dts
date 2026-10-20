"""setup.py -- mbtools-dts (fallback for legacy setuptools builds).

The canonical build config is ``pyproject.toml``.  This file keeps the old
``python setup.py install`` path working on older setuptools versions.
"""

from __future__ import annotations

from setuptools import setup

setup()
