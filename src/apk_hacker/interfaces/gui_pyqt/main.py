from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from PyQt6.QtWidgets import QApplication

from apk_hacker.application.services.execution_runtime import build_execution_backend_env
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend
from apk_hacker.interfaces.gui_pyqt.main_window import MainWindow
from apk_hacker.interfaces.gui_pyqt.viewmodels import WorkbenchController


def _build_execution_backend_env(args: argparse.Namespace) -> dict[str, str]:
    return build_execution_backend_env(
        device_serial=args.device_serial,
        frida_server_binary=args.frida_server_binary,
        frida_server_remote_path=args.frida_server_remote_path,
        frida_session_seconds=args.frida_session_seconds,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the APKHacker PyQt6 workbench.")
    parser.add_argument("--sample", type=Path, help="Optional sample path to prefill in the task center.")
    parser.add_argument("--jadx-gui-path", help="Optional local jadx-gui executable path.")
    parser.add_argument("--scripts-root", type=Path, help="Optional custom Frida scripts directory.")
    parser.add_argument("--db-root", type=Path, help="Optional cache/database directory.")
    parser.add_argument("--fixture-root", type=Path, help="Optional demo fixture root.")
    parser.add_argument("--jadx-sources-root", type=Path, help="Optional demo JADX sources root.")
    parser.add_argument("--device-serial", help="Optional adb device serial for built-in real backends.")
    parser.add_argument("--frida-server-binary", type=Path, help="Optional local frida-server binary for bootstrap.")
    parser.add_argument(
        "--frida-server-remote-path",
        help="Optional target path used by the Frida Bootstrap preset on the device.",
    )
    parser.add_argument(
        "--frida-session-seconds",
        type=float,
        help="Optional capture window for the Frida Session preset.",
    )
    parser.add_argument(
        "--real-backend-command",
        help="Optional command bridge for the Real Device execution mode.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def build_window(args: argparse.Namespace) -> MainWindow:
    execution_backend_env = _build_execution_backend_env(args)
    repo_root = Path(__file__).resolve().parents[4]
    resolved_db_root = args.db_root or (repo_root / "cache" / "gui")
    resolved_scripts_root = args.scripts_root or (
        repo_root / "user_data" / "frida_plugins" / "custom"
    )
    controller = None
    if args.real_backend_command:
        controller = WorkbenchController(
            fixture_root=args.fixture_root,
            jadx_sources_root=args.jadx_sources_root,
            scripts_root=resolved_scripts_root,
            db_root=resolved_db_root,
            execution_backend_env=execution_backend_env,
            execution_backends={
                "real_device": RealExecutionBackend(
                    command=args.real_backend_command,
                    extra_env=execution_backend_env,
                    artifact_root=resolved_db_root / "execution-runs",
                ),
            },
        )
    elif execution_backend_env:
        controller = WorkbenchController(
            fixture_root=args.fixture_root,
            jadx_sources_root=args.jadx_sources_root,
            scripts_root=resolved_scripts_root,
            db_root=resolved_db_root,
            execution_backend_env=execution_backend_env,
        )

    window = MainWindow(
        fixture_root=args.fixture_root,
        jadx_sources_root=args.jadx_sources_root,
        scripts_root=resolved_scripts_root,
        db_root=resolved_db_root,
        jadx_gui_path=args.jadx_gui_path,
        controller=controller,
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
