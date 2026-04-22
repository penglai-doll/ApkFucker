from __future__ import annotations

from pathlib import Path

from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionRecord
from apk_hacker.application.services.workspace_runtime_state import build_default_runtime_state
from apk_hacker.application.services.workspace_runtime_state import load_workspace_runtime_state
from apk_hacker.application.services.workspace_runtime_state import save_workspace_runtime_state
from apk_hacker.application.services.workspace_runtime_state import WorkspaceRuntimeState


class WorkspaceStateService:
    def __init__(self, hook_plan_service: HookPlanService | None = None) -> None:
        self._hook_plan_service = hook_plan_service or HookPlanService()

    def state_path(self, workspace_root: Path) -> Path:
        return workspace_root / "workspace-runtime.json"

    def load_for_case(self, case_id: str, workspace_root: Path) -> WorkspaceRuntimeState:
        path = self.state_path(workspace_root)
        state = load_workspace_runtime_state(
            case_id=case_id,
            workspace_root=workspace_root,
            path=path,
            hook_plan_service=self._hook_plan_service,
        )
        if not path.exists():
            return build_default_runtime_state(case_id, workspace_root)
        return state

    def load_from_record(self, record: WorkspaceInspectionRecord) -> WorkspaceRuntimeState:
        return self.load_for_case(record.case_id, record.workspace_root)

    def save(self, state: WorkspaceRuntimeState) -> WorkspaceRuntimeState:
        return save_workspace_runtime_state(state, self.state_path(state.workspace_root))
