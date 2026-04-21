from __future__ import annotations

import platform
from pathlib import Path
import subprocess


def open_local_path(target_path: Path) -> subprocess.Popen[bytes]:
    system = platform.system()
    if system == "Darwin":
        return subprocess.Popen(["open", str(target_path)])
    if system == "Windows":
        return subprocess.Popen(["cmd", "/c", "start", "", str(target_path)])
    return subprocess.Popen(["xdg-open", str(target_path)])
