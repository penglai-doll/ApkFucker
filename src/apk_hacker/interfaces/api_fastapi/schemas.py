from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from apk_hacker.domain.models.case_queue import CaseQueueItem


class CaseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    title: str
    workspace_root: str


class CaseListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CaseSummary] = Field(default_factory=list)


def case_summary_from_item(item: CaseQueueItem) -> CaseSummary:
    return CaseSummary(
        case_id=item.case_id,
        title=item.title,
        workspace_root=str(item.workspace_root),
    )
