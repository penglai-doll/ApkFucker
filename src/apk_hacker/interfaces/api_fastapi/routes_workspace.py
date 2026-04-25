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
from apk_hacker.interfaces.api_fastapi.schemas import CustomScriptContentResponse
from apk_hacker.interfaces.api_fastapi.schemas import CustomScriptSummary
from apk_hacker.interfaces.api_fastapi.schemas import CustomScriptListResponse
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanCustomScriptRequest
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanItemResponse
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanItemMoveRequest
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanItemUpdateRequest
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanMethodRequest
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanRecommendationRequest
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanResponse
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanTemplateRequest
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanSourceSummary
from apk_hacker.interfaces.api_fastapi.schemas import HookPlanTargetSummary
from apk_hacker.interfaces.api_fastapi.schemas import HookRecommendationSummary
from apk_hacker.interfaces.api_fastapi.schemas import OpenJadxResponse
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceDetailResponse
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceMethodsResponse
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceMethodSummary
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceRecommendationsResponse
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceEventResponse
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceEventsResponse
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceRuntimeSummary
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceSummary
from apk_hacker.interfaces.api_fastapi.schemas import CustomScriptUpdateRequest


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
            declaration=entry.declaration or None,
            source_preview=entry.source_preview or None,
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

    def _to_workspace_event(case_id: str, event) -> WorkspaceEventResponse:
        message_parts = [f"{event.class_name}.{event.method_name}"]
        if event.return_value:
            message_parts.append(event.return_value)
        return WorkspaceEventResponse(
            type="execution.event",
            case_id=case_id,
            timestamp=event.timestamp,
            message=" · ".join(message_parts),
            payload={
                "event_type": event.event_type,
                "source": event.source,
                "class_name": event.class_name,
                "method_name": event.method_name,
                "arguments": list(event.arguments),
                "return_value": event.return_value,
                "stacktrace": event.stacktrace,
                "raw_payload": dict(event.raw_payload),
            },
        )

    def _to_runtime_summary(case_id: str) -> WorkspaceRuntimeSummary:
        state = runtime_service.get_state(case_id)
        return WorkspaceRuntimeSummary(
            execution_count=state.execution_count,
            last_execution_run_id=state.last_execution_run_id,
            last_execution_mode=state.last_execution_mode,
            last_executed_backend_key=state.last_executed_backend_key,
            last_execution_status=state.last_execution_status,
            last_execution_stage=state.last_execution_stage,
            last_execution_error_code=state.last_execution_error_code,
            last_execution_error_message=state.last_execution_error_message,
            last_execution_event_count=state.last_execution_event_count,
            last_execution_result_path=str(state.last_execution_result_path) if state.last_execution_result_path else None,
            last_execution_db_path=str(state.last_execution_db_path) if state.last_execution_db_path else None,
            last_execution_bundle_path=str(state.last_execution_bundle_path) if state.last_execution_bundle_path else None,
            last_report_path=str(state.last_report_path) if state.last_report_path else None,
            traffic_capture_source_path=(
                str(state.traffic_capture_source_path) if state.traffic_capture_source_path else None
            ),
            traffic_capture_summary_path=(
                str(state.traffic_capture_summary_path) if state.traffic_capture_summary_path else None
            ),
            traffic_capture_flow_count=state.traffic_capture_flow_count,
            traffic_capture_suspicious_count=state.traffic_capture_suspicious_count,
            live_traffic_status=state.live_traffic_capture.status,
            live_traffic_artifact_path=(
                str(state.live_traffic_capture.output_path) if state.live_traffic_capture.output_path else None
            ),
            live_traffic_message=state.live_traffic_capture.message,
        )

    def _to_hook_plan_item_response(item, source=None) -> HookPlanItemResponse:
        return HookPlanItemResponse(
            item_id=item.item_id,
            kind=item.kind,
            enabled=item.enabled,
            inject_order=item.inject_order,
            source=_to_hook_plan_source_summary(source) if source is not None else None,
            target=_to_hook_plan_target_summary(item.target) if item.target is not None else None,
            render_context=dict(item.render_context),
            plugin_id=item.plugin_id,
        )

    def _to_hook_plan_response(case_id: str):
        hook_plan_view = runtime_service.get_hook_plan_view(case_id)
        state = hook_plan_view.state
        source_by_item_id = hook_plan_view.source_by_item_id
        return HookPlanResponse(
            case_id=case_id,
            updated_at=state.updated_at,
            selected_hook_sources=[_to_hook_plan_source_summary(source) for source in state.selected_hook_sources],
            items=[
                _to_hook_plan_item_response(item, source_by_item_id.get(item.item_id))
                for item in state.rendered_hook_plan.items
            ],
            execution_count=state.execution_count,
            last_execution_run_id=state.last_execution_run_id,
            last_execution_mode=state.last_execution_mode,
            last_executed_backend_key=state.last_executed_backend_key,
            last_execution_status=state.last_execution_status,
            last_execution_stage=state.last_execution_stage,
            last_execution_error_code=state.last_execution_error_code,
            last_execution_error_message=state.last_execution_error_message,
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
    def get_workspace_detail(case_id: str, refresh: bool = False) -> WorkspaceDetailResponse:
        try:
            record = inspection_service.refresh_detail(case_id) if refresh else inspection_service.get_detail(case_id)
            registry_service.set_last_opened_workspace(record.workspace_root)
            runtime_summary = _to_runtime_summary(case_id)
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
            runtime=runtime_summary,
        )

    @router.get("/{case_id}/workspace/methods", response_model=WorkspaceMethodsResponse)
    def get_workspace_methods(
        case_id: str,
        query: str = "",
        limit: int = 50,
        scope: str = "first_party",
    ) -> WorkspaceMethodsResponse:
        try:
            items, total, normalized_scope = inspection_service.search_methods(
                case_id,
                query=query,
                limit=limit,
                scope=scope,
            )
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc

        return WorkspaceMethodsResponse(
            items=[_to_method_summary(item) for item in items],
            total=total,
            scope=normalized_scope,
            available_scopes=["first_party", "related_candidates", "all"],
        )

    @router.get("/{case_id}/workspace/events", response_model=WorkspaceEventsResponse)
    def get_workspace_events(case_id: str, limit: int = 20) -> WorkspaceEventsResponse:
        try:
            events = runtime_service.get_execution_events(case_id, limit=limit)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc

        return WorkspaceEventsResponse(
            case_id=case_id,
            items=[_to_workspace_event(case_id, event) for event in events],
        )

    @router.get("/{case_id}/workspace/recommendations", response_model=WorkspaceRecommendationsResponse)
    def get_workspace_recommendations(
        case_id: str,
        limit: int = 8,
        query: str = "",
    ) -> WorkspaceRecommendationsResponse:
        try:
            recommendations = inspection_service.get_recommendations(case_id, limit=limit, query=query)
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
                    declaration=payload.declaration or "",
                    source_preview=payload.source_preview or "",
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

    @router.post("/{case_id}/hook-plan/templates", response_model=HookPlanResponse)
    def add_hook_plan_template(case_id: str, payload: HookPlanTemplateRequest) -> HookPlanResponse:
        try:
            runtime_service.add_template_to_plan(
                case_id,
                template_id=payload.template_id,
                template_name=payload.template_name,
                plugin_id=payload.plugin_id,
            )
            return _to_hook_plan_response(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

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

    @router.patch("/{case_id}/hook-plan/items/{item_id}", response_model=HookPlanResponse)
    def patch_hook_plan_item(
        case_id: str,
        item_id: str,
        payload: HookPlanItemUpdateRequest,
    ) -> HookPlanResponse:
        try:
            runtime_service.update_hook_plan_item(
                case_id,
                item_id,
                enabled=payload.enabled,
                inject_order=payload.inject_order,
            )
            return _to_hook_plan_response(case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook plan item not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @router.post("/{case_id}/hook-plan/items/{item_id}/move", response_model=HookPlanResponse)
    def move_hook_plan_item(
        case_id: str,
        item_id: str,
        payload: HookPlanItemMoveRequest,
    ) -> HookPlanResponse:
        try:
            hook_plan_view = runtime_service.get_hook_plan_view(case_id)
            current_items = list(hook_plan_view.state.rendered_hook_plan.items)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc

        current_index = next((index for index, item in enumerate(current_items) if item.item_id == item_id), None)
        if current_index is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook plan item not found")

        direction = payload.direction.strip().lower()
        if direction == "up":
            target_order = max(1, current_items[current_index].inject_order - 1)
        elif direction == "down":
            target_order = min(len(current_items), current_items[current_index].inject_order + 1)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported move direction")

        runtime_service.update_hook_plan_item(case_id, item_id, inject_order=target_order)
        return _to_hook_plan_response(case_id)

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
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return CustomScriptSummary(script_id=record.script_id, name=record.name, script_path=str(record.script_path))

    @router.get("/{case_id}/custom-scripts/{script_id:path}", response_model=CustomScriptContentResponse)
    def get_custom_script(case_id: str, script_id: str) -> CustomScriptContentResponse:
        try:
            record, content = runtime_service.get_custom_script(case_id, script_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom script not found") from exc
        return CustomScriptContentResponse(
            script_id=record.script_id,
            name=record.name,
            script_path=str(record.script_path),
            content=content,
        )

    @router.put("/{case_id}/custom-scripts/{script_id:path}", response_model=CustomScriptSummary)
    def update_custom_script(
        case_id: str,
        script_id: str,
        payload: CustomScriptUpdateRequest,
    ) -> CustomScriptSummary:
        try:
            current_record, _current_content = runtime_service.get_custom_script(case_id, script_id)
            record = runtime_service.update_custom_script(
                case_id,
                script_id,
                name=payload.name or current_record.name,
                content=payload.content,
            )
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom script not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return CustomScriptSummary(script_id=record.script_id, name=record.name, script_path=str(record.script_path))

    @router.delete("/{case_id}/custom-scripts/{script_id:path}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_custom_script(case_id: str, script_id: str) -> None:
        try:
            runtime_service.delete_custom_script(case_id, script_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found") from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom script not found") from exc

    return router
