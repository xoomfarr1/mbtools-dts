# mbtools-dts — Windows installer build

This directory holds the build recipes for producing a **single-file Windows
executable** (and a Windows installer, via PyInstaller and/or NSIS) from the
`mbtools-dts` Python package.

Two outputs are produced:

| Output | How | Notes |
|--------|-----|-------|
| `build/dist/mbtools_dts.exe` | `python -m PyInstaller mbtools_dts.spec` | Dev.Bundle; run anywhere with a matching Python on Windows |
| `mbtools_dts_installer.exe` | PyInstaller + NSIS (`make_windows_installer.bat`) | User-facing installer; the CTTP that the community uses |

## Prerequisites (Windows)

1. Install Python **3.10+** from <https://www.python.org/downloads/windows/>.
   During install tick **"Add Python to PATH"**.
2. Install the build tools (one-time):
   ```bat
   pip install --upgrade pip setuptools wheel pyinstaller
   ```
3. Prepare a clean Python *virtual environment* (recommended) and *activate* it.
4. Install the mbtools-dts package (editable) and its GUI extras:
   ```bat
   pip install -e .[gui,dev]
   ```
   (the `pt3g_j2534` package is Windows-only and is pulled in automatically by
   the `pt3g` extra when you're on Windows).
5. Grab a Windows 10/11 SDK (the default one that ships with Visual Studio is
   fine) — the compiled `pyd` (if any) needs the Windows headers.

## 1. Build the bundled executable

```bat
pyinstaller --clean --noconfirm --onefile mbtools_dts.spec
```

The script writes to the PyInstaller `build/` and `dist/` directories:

* `dist\mbtools_dts.exe` — single, self-contained executable.
* `build\mbtools_dts\` — intermediate files (delete after a successful build
  if you want to save disk).

*Tip:* the `.spec` file pins the `mbtools_dts` package to the `src\`
directory and adds the `gui`, `logic`, `hardware`, `protocols` submodules.
Headless runs (no GUI) still work on CI by passing the path of the
application instead of a display.

## 2. Build the NSIS installer (optional)

Requires the **NSIS** compiler (<https://nsis.sourceforge.io/>) and the
`SignTool.exe` / `rundll32` utilities that ship with the Windows 10 SDK.

```bat
# 1. build the executable (PyInstaller)
pyinstaller --clean --noconfirm --onefile mbtools_dts.spec

# 2. build the installer
makensis /DOUTFILE=mbtools_dts_installer.exe mbtools_dts_installer.nsi
```

The installer script (`mbtools_dts_installer.nsi`) does:

* read `dist\mbtools_dts.exe` (the PyInstaller output),
* install it to `C:\Program Files\MBTools-DTS\bin\`
* create a Start-menu shortcut and a desktop icon,
* register an Uninstall entry under `HKCU\Software\MBTools-DTS`,

## 3. Cross-compilation (build on Windows from Linux)

PyInstaller cannot cross-compile for Windows from Linux, so run the build
commands above on a Windows machine (or a Windows VM). If you're doing
development on Linux you can still test the *bundle* by running the
executable under Wine **after** it has been produced (see the "Linux"
section below).

## 4. Reproducible builds

The spec file (`mbtools_dts.spec`) is versioned so that the bundle stays
reproducible. If you change the package layout, update the spec with:

```bat
pyi-grab-module mbtools_dts/__init__.py -n mbtools_dts
# then add the extra subpackages manually
pyi-grab-module mbtools_dts/hardware/__init__.py -n mbtools_dts.hardware
...
```

## 5. Linux (for testing / CI)

The PyInstaller bundle is Windows-only, so on Linux you can only test the
*source* distribution or the headless CLI:

```bat
pip install -e .
python -m mbtools_dts connect --adapter virtual   # headless driver smoke test
python -m mbtools_dts read-dtcs                   # needs a live PT3G VCI
```

> To run the *Windows* `.exe` under Linux, use Wine afterwards (the PNG at
> `$(pwd)/docs/WIN_BUILD.md` contains a screenshot of the working bundle).
