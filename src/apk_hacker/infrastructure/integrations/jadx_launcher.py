from __future__ import annotations

from collections.abc import Callable, Mapping
import os
from pathlib import Path
import shutil
import subprocess


def resolve_jadx_gui_path(
    explicit_path: str | None,
    environ: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] | None = None,
) -> str | None:
    if explicit_path is not None:
        normalized_explicit_path = explicit_path.strip()
        return normalized_explicit_path or None

    env = environ or os.environ
    env_path = env.get("APKHACKER_JADX_GUI_PATH", "").strip()
    if env_path:
        return env_path

    resolver = which or shutil.which
    return resolver("jadx-gui")


def open_in_jadx(jadx_gui_path: str, target_path: Path) -> subprocess.Popen[bytes]:
    return subprocess.Popen([jadx_gui_path, str(target_path)])
