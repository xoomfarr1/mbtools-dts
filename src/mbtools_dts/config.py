"""Application configuration and project-file model.

Everything the user touches (window size, which vehicle data files to load,
which hardware port) lives here.

Project files (``.mbtools-dts`` / ``project.json``) are JSON that hold:
  - which ECU / vehicle project to open
  - the last selected hardware port
  - the position of UI panels
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# Where to look for the ODX / SMR-D vehicle data folders supplied by the user.
DEFAULT_DATA_FOLDERS = [
    Path(r"C:\MBTools-DTS_Data"),
    Path(r"D:\Vehicle_Data"),
]

WELCOME_PAGE = (
    "WELCOME TO MBTools-DTS\n"
    "This is a safe, open, free diagnostic tool. It reads and writes data "
    "to your car's computers (ECUs) but does NOT change anything permanent "
    "unless you ask it to. Always start with a backup of the file you are about "
    "to change. If you are not sure what you are doing, press \"Begin with the basics\"."
)


class Settings(BaseModel):
    """User preferences (kept in %APPDATA% on Windows)."""

    data_folders: list[Path] = Field(default_factory=lambda: list(DEFAULT_DATA_FOLDERS))
    window_width: int = 1280
    window_height: int = 800
    dark_mode: bool = True
    show_tutorial: bool = True
    # which hardware to use: "pt3g" | "virtual"
    hardware: str = "virtual"

    model_config = {"protected_namespaces": ()}

    def save(self, path: Path) -> None:
        import json

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.model_dump(), fh, indent=2, default=str)

    @classmethod
    def default(cls) -> "Settings":
        return cls()

    @classmethod
    def load(cls, path: Path) -> "Settings":
        import json

        if not path.exists():
            return cls.default()
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls(**data)
