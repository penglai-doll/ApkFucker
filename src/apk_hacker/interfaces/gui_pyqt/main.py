from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from PyQt6.QtWidgets import QApplication

from apk_hacker.interfaces.gui_pyqt.main_window import MainWindow


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the APKHacker PyQt6 workbench.")
    parser.add_argument("--sample", type=Path, help="Optional sample path to prefill in the task center.")
    parser.add_argument("--jadx-gui-path", help="Optional local jadx-gui executable path.")
    parser.add_argument("--scripts-root", type=Path, help="Optional custom Frida scripts directory.")
    parser.add_argument("--db-root", type=Path, help="Optional cache/database directory.")
    parser.add_argument("--fixture-root", type=Path, help="Optional demo fixture root.")
    parser.add_argument("--jadx-sources-root", type=Path, help="Optional demo JADX sources root.")
    return parser.parse_args(list(argv) if argv is not None else None)


def build_window(args: argparse.Namespace) -> MainWindow:
    window = MainWindow(
        fixture_root=args.fixture_root,
        jadx_sources_root=args.jadx_sources_root,
        scripts_root=args.scripts_root,
        db_root=args.db_root,
        jadx_gui_path=args.jadx_gui_path,
    )
    if args.sample is not None:
        window.task_center.sample_path_input.setText(str(args.sample))
    return window


def run(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    app = QApplication.instance() or QApplication([])
    window = build_window(args)
    window.show()
    return app.exec()


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
