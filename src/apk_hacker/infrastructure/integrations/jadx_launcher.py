from __future__ import annotations

from pathlib import Path
import subprocess


def open_in_jadx(jadx_gui_path: str, target_path: Path) -> subprocess.Popen[bytes]:
    return subprocess.Popen([jadx_gui_path, str(target_path)])
