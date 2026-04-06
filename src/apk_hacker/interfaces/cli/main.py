from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from apk_hacker.application.services.execution_runtime import build_execution_backend_env
from apk_hacker.infrastructure.execution.real_backend import RealExecutionBackend
from apk_hacker.interfaces.gui_pyqt.viewmodels import WorkbenchController, WorkbenchState


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run APKHacker in headless CLI mode.")
    parser.add_argument("--sample", type=Path, required=True, help="APK or decoded sample path.")
    parser.add_argument("--output-dir", type=Path, help="Optional static-analysis output directory.")
    parser.add_argument(
        "--method-query",
        action="append",
        default=[],
        help="Search query for a method to add to the hook plan. Repeatable.",
    )
    parser.add_argument(
        "--add-top-recommendations",
        type=int,
        default=0,
        help="Add the top N offline method recommendations to the hook plan.",
    )
    parser.add_argument(
        "--execution-mode",
        default="fake_backend",
        help="Execution mode to use when --run is set. Default: fake_backend.",
    )
    parser.add_argument("--run", action="store_true", help="Run the selected execution mode after planning hooks.")
    parser.add_argument("--db-root", type=Path, help="Optional cache/database directory.")
    parser.add_argument("--scripts-root", type=Path, help="Optional custom Frida scripts directory.")
    parser.add_argument("--device-serial", help="Optional adb device serial for real backends.")
    parser.add_argument("--frida-server-binary", type=Path, help="Optional local frida-server binary path.")
    parser.add_argument("--frida-server-remote-path", help="Optional frida-server remote path.")
    parser.add_argument("--frida-session-seconds", type=float, help="Optional Frida session capture window.")
    parser.add_argument("--real-backend-command", help="Optional custom command for real_device mode.")
    parser.add_argument("--export-report", action="store_true", help="Export a markdown report to the default reports directory.")
    return parser.parse_args(list(argv) if argv is not None else None)


def _serialize_event(event: Any) -> dict[str, Any]:
    return {
        "timestamp": event.timestamp,
        "job_id": event.job_id,
        "event_type": event.event_type,
        "source": event.source,
        "class_name": event.class_name,
        "method_name": event.method_name,
        "arguments": list(event.arguments),
        "return_value": event.return_value,
        "stacktrace": event.stacktrace,
        "raw_payload": event.raw_payload,
    }


def _serialize_selected_targets(state: WorkbenchState) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for item in state.hook_plan.items:
        target = item.target
        if target is not None:
            selected.append(
                {
                    "kind": item.kind,
                    "class_name": target.class_name,
                    "method_name": target.method_name,
                    "parameter_types": list(target.parameter_types),
                    "return_type": target.return_type,
                }
            )
            continue
        selected.append(
            {
                "kind": item.kind,
                "template_name": str(item.render_context.get("template_name", "")),
                "script_name": str(item.render_context.get("script_name", "")),
            }
        )
    return selected


def build_controller(args: argparse.Namespace) -> WorkbenchController:
    repo_root = Path(__file__).resolve().parents[4]
    resolved_db_root = args.db_root or (repo_root / "cache" / "cli")
    execution_backend_env = build_execution_backend_env(
        device_serial=args.device_serial,
        frida_server_binary=args.frida_server_binary,
        frida_server_remote_path=args.frida_server_remote_path,
        frida_session_seconds=args.frida_session_seconds,
    )
    execution_backends = None
    if args.real_backend_command:
        execution_backends = {
            "real_device": RealExecutionBackend(
                command=args.real_backend_command,
                extra_env=execution_backend_env,
                artifact_root=resolved_db_root / "execution-runs",
            )
        }
    return WorkbenchController(
        scripts_root=args.scripts_root or (repo_root / "user_data" / "frida_plugins" / "custom"),
        db_root=resolved_db_root,
        execution_backend_env=execution_backend_env,
        execution_backends=execution_backends,
    )


def execute_cli(args: argparse.Namespace, controller: WorkbenchController | None = None) -> dict[str, Any]:
    resolved_controller = controller or build_controller(args)
    state = WorkbenchState(summary_text="CLI ready.")
    state = resolved_controller.refresh_environment(state, announce=False)
    state = resolved_controller.load_sample_workspace(args.sample)

    for query in args.method_query:
        state = resolved_controller.search_methods(state, query)
        if not state.visible_methods:
            raise RuntimeError(f"No method matched query: {query}")
        state = resolved_controller.add_method_to_plan(state, state.visible_methods[0])

    if args.add_top_recommendations > 0:
        state = resolved_controller.add_top_recommendations_to_plan(state, limit=args.add_top_recommendations)

    if args.run:
        if not state.hook_plan.items:
            raise RuntimeError("No hook plan items selected. Use --method-query or --add-top-recommendations.")
        state = resolved_controller.set_execution_mode(state, args.execution_mode)
        state = resolved_controller.run_analysis(state)
    if args.export_report:
        state = resolved_controller.export_report(state)
        if state.last_export_report_path is None:
            raise RuntimeError(state.summary_text)

    return {
        "job_id": state.current_job.job_id if state.current_job is not None else None,
        "sample_path": str(state.sample_path) if state.sample_path is not None else None,
        "package_name": state.static_inputs.package_name if state.static_inputs is not None else None,
        "method_count": len(state.method_index.methods),
        "recommendation_count": len(state.hook_recommendations),
        "selected_plan_count": len(state.hook_plan.items),
        "selected_targets": _serialize_selected_targets(state),
        "execution_mode": state.execution_mode,
        "event_count": len(state.hook_events),
        "events": [_serialize_event(event) for event in state.hook_events],
        "last_execution_db_path": (
            str(state.last_execution_db_path) if state.last_execution_db_path is not None else None
        ),
        "last_execution_bundle_path": (
            str(state.last_execution_bundle_path) if state.last_execution_bundle_path is not None else None
        ),
        "exported_report_path": (
            str(state.last_export_report_path) if state.last_export_report_path is not None else None
        ),
        "summary": state.summary_text,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = execute_cli(args)
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
