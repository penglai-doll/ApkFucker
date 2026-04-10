from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2
from uuid import uuid4

from apk_hacker.domain.models.workspace import WorkspaceRecord


class WorkspaceService:
    def create_workspace(
        self,
        sample_path: Path,
        workspace_root: Path,
        title: str | None = None,
    ) -> WorkspaceRecord:
        case_id = f"case-{uuid4().hex[:12]}"
        destination_root = workspace_root / case_id
        sample_dir = destination_root / "sample"
        sample_dir.mkdir(parents=True, exist_ok=False)

        copied_sample = sample_dir / "original.apk"
        copy2(sample_path, copied_sample)

        now = datetime.now(timezone.utc).isoformat()
        metadata = {
            "workspace_version": 1,
            "case_id": case_id,
            "title": title or sample_path.stem,
            "created_at": now,
            "updated_at": now,
            "sample_filename": copied_sample.name,
        }
        (destination_root / "workspace.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return WorkspaceRecord(
            case_id=case_id,
            title=metadata["title"],
            workspace_root=destination_root,
            sample_path=copied_sample,
        )
