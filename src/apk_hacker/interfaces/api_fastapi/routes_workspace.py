from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from apk_hacker.application.services.case_queue_service import CaseQueueService
from apk_hacker.application.services.workspace_inspection_service import CaseNotFoundError
from apk_hacker.application.services.workspace_inspection_service import JadxUnavailableError
from apk_hacker.application.services.workspace_inspection_service import WorkspaceInspectionService
from apk_hacker.application.services.workspace_runtime_service import WorkspaceRuntimeService
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.domain.models.hook_advice import HookRecommendation
from apk_hacker.domain.models.indexes import MethodIndexEntry
from apk_hacker.interfaces.api_fastapi.routes_cases import _known_workspace_roots
from apk_hacker.interfaces.api_fastapi.schemas import CustomScriptCreateRequest
from apk_hacker.interfaces.api_fastapi.schemas import CustomScriptSummary
from apk_hacker.interfaces.api_fastapi.schemas import CustomScriptListResponse
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanCustomScriptRequest
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanItemResponse
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanMethodRequest
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanRecommendationRequest
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanResponse
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanSourceSummary
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanTargetSummary
from apk_hacker.interfaces.api_fastapi.schemas import HookRecommendationSummary
from apk_hacker.interfaces.api_fastapi.schemas import OpenJadxResponse
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceDetailResponse
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceMethodsResponse
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceMethodSummary
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceRecommendationsResponse
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceSummary


def _load_workspace_title(workspace_root: Path, case_id: str) -> str | None:
    for workspace_json in workspace_root.glob("*/workspace.json"):
        try:
            payload = json.loads(workspace_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue

        candidate_case_id = payload.get("case_id")
        title = payload.get("title")
        if not isinstance(candidate_case_id, str) or not isinstance(title, str):
            continue
        if candidate_case_id.strip() != case_id:
            continue

        normalized = title.strip()
        if normalized:
            return normalized

    return None


def build_workspace_router(
    *,
    registry_service: WorkspaceRegistryService,
    default_workspace_root: Path,
    case_queue_service: CaseQueueService | None = None,
    workspace_inspection_service: WorkspaceInspectionService | None = None,
    workspace_runtime_service: WorkspaceRuntimeService | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/cases", tags=["workspace"])
    queue_service = case_queue_service or CaseQueueService()
    inspection_service = workspace_inspection_service or WorkspaceInspectionService(
        registry_service=registry_service,
        default_workspace_root=default_workspace_root,
        case_queue_service=queue_service,
    )
    runtime_service = workspace_runtime_service or WorkspaceRuntimeService(
        registry_service=registry_service,
        default_workspace_root=default_workspace_root,
        inspection_service=inspection_service,
        case_queue_service=queue_service,
    )

    def _to_method_summary(entry: MethodIndexEntry) -> WorkspaceMethodSummary:
        return WorkspaceMethodSummary(
            class_name=entry.class_name,
            method_name=entry.method_name,
            parameter_types=list(entry.parameter_types),
            return_type=entry.return_type,
            is_constructor=entry.is_constructor,
            overload_count=entry.overload_count,
            source_path=entry.source_path,
            line_hint=entry.line_hint,
            tags=list(entry.tags),
            evidence=list(entry.evidence),
        )

    def _to_recommendation_summary(entry: HookRecommendation) -> HookRecommendationSummary:
        return HookRecommendationSummary(
            recommendation_id=entry.recommendation_id,
            kind=entry.kind,
            title=entry.title,
            reason=entry.reason,
            score=entry.score,
            matched_terms=list(entry.matched_terms),
            method=_to_method_summary(entry.method) if entry.method is not None else None,
            template_id=entry.template_id,
            template_name=entry.template_name,
            plugin_id=entry.plugin_id,
        )

    def _to_hook_plan_source_summary(source) -> HookPlanSourceSummary:
        return HookPlanSourceSummary(
            source_id=source.source_id,
            kind=source.kind,
            method=_to_method_summary(source.method) if source.method is not None else None,
            script_name=source.script_name,
            script_path=source.script_path,
            template_id=source.template_id,
            template_name=source.template_name,
            plugin_id=source.plugin_id,
        )

    def _to_hook_plan_target_summary(target) -> HookPlanTargetSummary:
        return HookPlanTargetSummary(
            target_id=target.target_id,
            class_name=target.class_name,
            method_name=target.method_name,
            parameter_types=list(target.parameter_types),
            return_type=target.return_type,
            source_origin=target.source_origin,
            notes=target.notes,
        )

    def _to_hook_plan_item_response(item) -> HookPlanItemResponse:
        return HookPlanItemResponse(
            item_id=item.item_id,
            kind=item.kind,
            enabled=item.enabled,
            inject_order=item.inject_order,
            target=_to_hook_plan_target_summary(item.target) if item.target is not None else None,
            render_context=dict(item.render_context),
            plugin_id=item.plugin_id,
        )

    def _to_hook_plan_response(case_id: str):
        state = runtime_service.get_state(case_id)
        return HookPlanResponse(
            case_id=case_id,
            updated_at=state.updated_at,
            selected_hook_sources=[_to_hook_plan_source_summary(source) for source in state.selected_hook_sources],
            items=[_to_hook_plan_item_response(item) for item in state.rendered_hook_plan.items],
            execution_count=state.execution_count,
            last_execution_run_id=state.last_execution_run_id,
            last_execution_mode=state.last_execution_mode,
            last_execution_status=state.last_execution_status,
            last_execution_event_count=state.last_execution_event_count,
            last_execution_result_path=str(state.last_execution_result_path) if state.last_execution_result_path else None,
            last_execution_db_path=str(state.last_execution_db_path) if state.last_execution_db_path else None,
            last_execution_bundle_path=str(state.last_execution_bundle_path) if state.last_execution_bundle_path else None,
            last_report_path=str(state.last_report_path) if state.last_report_path else None,
        )

    @router.get("/{case_id}/workspace", response_model=WorkspaceSummary)
    def get_workspace(case_id: str) -> WorkspaceSummary:
        for workspace_root in _known_workspace_roots(registry_service, default_workspace_root):
            items = queue_service.list_cases(workspace_root)
            for item in items:
                if item.case_id != case_id:
                    continue
                title = _load_workspace_title(workspace_root, case_id)
                if title is not None:
                    return WorkspaceSummary(case_id=case_id, title=title)

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    @router.get("/{case_id}/workspace/detail", response_model=WorkspaceDetailResponse)
    def get_workspace_detail(case_id: str) -> WorkspaceDetailResponse:
        try:
            record = inspection_service.get_detail(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc

        static_inputs = record.bundle.static_inputs
        return WorkspaceDetailResponse(
            case_id=record.case_id,
            title=record.title,
            package_name=static_inputs.package_name,
            technical_tags=list(static_inputs.technical_tags),
            dangerous_permissions=list(static_inputs.dangerous_permissions),
            callback_endpoints=list(static_inputs.callback_endpoints),
            callback_clues=list(static_inputs.callback_clues),
            crypto_signals=list(static_inputs.crypto_signals),
            packer_hints=list(static_inputs.packer_hints),
            limitations=list(static_inputs.limitations),
            custom_scripts=[
                CustomScriptSummary(
                    script_id=item.script_id,
                    name=item.name,
                    script_path=str(item.script_path),
                )
                for item in record.custom_scripts
            ],
            can_open_in_jadx=inspection_service.can_open_in_jadx(case_id),
            has_method_index=record.has_method_index,
            method_count=len(record.bundle.method_index.methods),
        )

    @router.get("/{case_id}/workspace/methods", response_model=WorkspaceMethodsResponse)
    def get_workspace_methods(case_id: str, query: str = "", limit: int = 50) -> WorkspaceMethodsResponse:
        try:
            items, total = inspection_service.search_methods(case_id, query=query, limit=limit)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc

        return WorkspaceMethodsResponse(
            items=[_to_method_summary(item) for item in items],
            total=total,
        )

    @router.get("/{case_id}/workspace/recommendations", response_model=WorkspaceRecommendationsResponse)
    def get_workspace_recommendations(case_id: str, limit: int = 8) -> WorkspaceRecommendationsResponse:
        try:
            recommendations = inspection_service.get_recommendations(case_id, limit=limit)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc

        return WorkspaceRecommendationsResponse(
            items=[_to_recommendation_summary(item) for item in recommendations],
        )

    @router.post("/{case_id}/actions/open-jadx", response_model=OpenJadxResponse)
    def post_open_jadx(case_id: str) -> OpenJadxResponse:
        try:
            inspection_service.open_in_jadx(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc
        except JadxUnavailableError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        return OpenJadxResponse(case_id=case_id, status="opened")

    @router.get("/{case_id}/hook-plan", response_model=HookPlanResponse)
    def get_hook_plan(case_id: str) -> HookPlanResponse:
        try:
            return _to_hook_plan_response(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc

    @router.post("/{case_id}/hook-plan/methods", response_model=HookPlanResponse)
    def add_hook_plan_method(case_id: str, payload: HookPlanMethodRequest) -> HookPlanResponse:
        try:
            runtime_service.add_method_to_plan(
                case_id,
                MethodIndexEntry(
                    class_name=payload.class_name,
                    method_name=payload.method_name,
                    parameter_types=tuple(payload.parameter_types),
                    return_type=payload.return_type,
                    is_constructor=payload.is_constructor,
                    overload_count=payload.overload_count,
                    source_path=payload.source_path,
                    line_hint=payload.line_hint,
                    tags=tuple(payload.tags),
                    evidence=tuple(payload.evidence),
                ),
            )
            return _to_hook_plan_response(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc

    @router.post("/{case_id}/hook-plan/recommendations", response_model=HookPlanResponse)
    def add_hook_plan_recommendation(
        case_id: str,
        payload: HookPlanRecommendationRequest,
    ) -> HookPlanResponse:
        try:
            runtime_service.add_recommendation_to_plan(case_id, payload.recommendation_id)
            return _to_hook_plan_response(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found") from exc

    @router.post("/{case_id}/hook-plan/custom-scripts", response_model=HookPlanResponse)
    def add_hook_plan_custom_script(case_id: str, payload: HookPlanCustomScriptRequest) -> HookPlanResponse:
        try:
            runtime_service.add_custom_script_to_plan(case_id, payload.script_id)
            return _to_hook_plan_response(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom script not found") from exc

    @router.delete("/{case_id}/hook-plan/items/{item_id}", response_model=HookPlanResponse)
    def remove_hook_plan_item(case_id: str, item_id: str) -> HookPlanResponse:
        try:
            runtime_service.remove_hook_plan_item(case_id, item_id)
            return _to_hook_plan_response(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook plan item not found") from exc

    @router.delete("/{case_id}/hook-plan", response_model=HookPlanResponse)
    def clear_hook_plan(case_id: str) -> HookPlanResponse:
        try:
            runtime_service.clear_hook_plan(case_id)
            return _to_hook_plan_response(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc

    @router.get("/{case_id}/custom-scripts", response_model=CustomScriptListResponse)
    def list_custom_scripts(case_id: str) -> CustomScriptListResponse:
        try:
            scripts = runtime_service.list_custom_scripts(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc
        return CustomScriptListResponse(
            items=[
                CustomScriptSummary(
                    script_id=script.script_id,
                    name=script.name,
                    script_path=str(script.script_path),
                )
                for script in scripts
            ]
        )

    @router.post("/{case_id}/custom-scripts", response_model=CustomScriptSummary)
    def save_custom_script(case_id: str, payload: CustomScriptCreateRequest) -> CustomScriptSummary:
        try:
            record = runtime_service.save_custom_script(case_id, payload.name, payload.content)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc
        return CustomScriptSummary(script_id=record.script_id, name=record.name, script_path=str(record.script_path))

    return router
