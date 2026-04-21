from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Sequence

from apk_hacker.application.services.execution_runtime import build_execution_backend_env
from apk_hacker.application.services.workspace_registry_service import default_workspace_data_root


LEGACY_GUI_DEPRECATION_MESSAGE = (
    "旧版 PyQt 工作台已退役，当前唯一继续演进的桌面主线是 Tauri + React + FastAPI。\n"
    "请改用 `npm run dev:tauri` 启动桌面工作台，"
    "或使用 `uv run apk-hacker` 单独启动本地 API。"
)


@dataclass(frozen=True, slots=True)
class LegacyGuiCompatWindow:
    sample_path: Path | None
    jadx_gui_path: str | None
    scripts_root: Path
    db_root: Path
    fixture_root: Path | None
    jadx_sources_root: Path | None
    execution_backend_env: dict[str, str]
    real_backend_command: str | None
    deprecation_message: str = LEGACY_GUI_DEPRECATION_MESSAGE

    def show(self) -> None:
        return None

    def close(self) -> None:
        return None


def _build_execution_backend_env(args: argparse.Namespace) -> dict[str, str]:
    return build_execution_backend_env(
        device_serial=args.device_serial,
        frida_server_binary=args.frida_server_binary,
        frida_server_remote_path=args.frida_server_remote_path,
        frida_session_seconds=args.frida_session_seconds,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Legacy compatibility entrypoint for APKHacker. "
            "The PyQt workbench has been retired during the Tauri + React + FastAPI migration."
        )
    )
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


def build_window(args: argparse.Namespace) -> LegacyGuiCompatWindow:
    execution_backend_env = _build_execution_backend_env(args)
    repo_root = Path(__file__).resolve().parents[4]
    resolved_db_root = args.db_root or default_workspace_data_root(repo_root)
    resolved_scripts_root = args.scripts_root or (
        repo_root / "user_data" / "frida_plugins" / "custom"
    )
    return LegacyGuiCompatWindow(
        sample_path=args.sample,
        jadx_gui_path=args.jadx_gui_path,
        scripts_root=resolved_scripts_root,
        db_root=resolved_db_root,
        fixture_root=args.fixture_root,
        jadx_sources_root=args.jadx_sources_root,
        execution_backend_env=execution_backend_env,
        real_backend_command=args.real_backend_command,
    )


def run(argv: Sequence[str] | None = None) -> int:
    build_window(parse_args(argv))
    print(LEGACY_GUI_DEPRECATION_MESSAGE, file=sys.stderr)
    return 1


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
