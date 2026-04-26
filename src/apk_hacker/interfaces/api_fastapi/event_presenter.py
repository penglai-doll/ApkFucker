from __future__ import annotations

from apk_hacker.domain.models.dynamic_event import DynamicEvent
from apk_hacker.interfaces.api_fastapi.schemas import WorkspaceEventResponse


def dynamic_event_response(case_id: str, event: DynamicEvent) -> WorkspaceEventResponse:
    payload = event.to_payload()
    return WorkspaceEventResponse(
        type="execution.event",
        case_id=case_id,
        timestamp=event.timestamp,
        message=event.message,
        schema_version=event.schema_version,
        job_id=event.job_id,
        session_id=event.session_id,
        event_type=event.event_type,
        hook_type=event.hook_type,
        source=event.source,
        source_script=event.source_script,
        class_name=event.class_name,
        method_name=event.method_name,
        arguments=list(event.arguments),
        return_value=event.return_value,
        stacktrace=event.stacktrace,
        payload=payload,
    )
