from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket

from apk_hacker.application.services.workspace_registry_service import default_workspace_registry_path
from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService
from apk_hacker.interfaces.api_fastapi.routes_cases import build_cases_router
from apk_hacker.interfaces.api_fastapi.routes_workspace import build_workspace_router
from apk_hacker.interfaces.api_fastapi.websocket_hub import WebSocketHub

def build_app(
    *,
    default_workspace_root: Path | None = None,
    registry_path: Path | None = None,
) -> FastAPI:
    hub = WebSocketHub()
    repo_root = Path(__file__).resolve().parents[4]
    workspace_root = default_workspace_root or repo_root / "workspaces"
    resolved_registry_path = registry_path or default_workspace_registry_path(workspace_root.parent)
    registry_service = WorkspaceRegistryService(resolved_registry_path)

    app = FastAPI(
        title="APKHacker Local API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.include_router(
        build_cases_router(
            registry_service=registry_service,
            default_workspace_root=workspace_root,
        )
    )
    app.include_router(
        build_workspace_router(
            registry_service=registry_service,
            default_workspace_root=workspace_root,
        )
    )

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await hub.handle(websocket)

    return app
