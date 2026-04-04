from __future__ import annotations

from pathlib import Path


def build_jadx_command(jadx_binary: Path | str, apk_path: Path | str, out_dir: Path | str) -> list[Path | str]:
    out_dir = Path(out_dir)
    return [
        Path(jadx_binary),
        "--output-dir-src",
        out_dir / "sources",
        "--output-dir-res",
        out_dir / "resources",
        Path(apk_path),
    ]
