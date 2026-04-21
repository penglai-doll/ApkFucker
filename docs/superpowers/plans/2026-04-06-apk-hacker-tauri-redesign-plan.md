# APKHacker Tauri Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 APKHacker PyQt6 工作台替换为 macOS Apple Silicon 首发的 `Tauri + React + FastAPI + Python sidecar` 桌面应用，并重构为 `Case Queue + Case Workspace` 双模式中文工作台。

**Architecture:** 本计划不重写分析内核，而是先把现有 Python 工作流抽成稳定 API，再用 Tauri + React 重建前端。后端首版保持 Python sidecar 与现有 workers，WebSocket 负责实时事件，workspace 采用“每个样本一个独立目录”的案件模型，为后续 Rust 编排层迁移留出清晰边界。

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, pydantic, React, TypeScript, Vite, Vitest, Tauri v2, Rust, WebSocket, SQLite

---

## File Map

### Create

- `/package.json`
- `/frontend/index.html`
- `/frontend/tsconfig.json`
- `/frontend/vite.config.ts`
- `/frontend/src/main.tsx`
- `/frontend/src/App.tsx`
- `/frontend/src/routes/router.tsx`
- `/frontend/src/lib/api.ts`
- `/frontend/src/lib/ws.ts`
- `/frontend/src/lib/types.ts`
- `/frontend/src/store/app-store.ts`
- `/frontend/src/pages/CaseQueuePage.tsx`
- `/frontend/src/pages/CaseWorkspacePage.tsx`
- `/frontend/src/components/layout/AppFrame.tsx`
- `/frontend/src/components/queue/CaseQueueTable.tsx`
- `/frontend/src/components/workspace/StaticBriefPanel.tsx`
- `/frontend/src/components/workspace/HookStudioPanel.tsx`
- `/frontend/src/components/workspace/ExecutionConsolePanel.tsx`
- `/frontend/src/components/workspace/EvidencePanel.tsx`
- `/frontend/src/components/workspace/ReportsPanel.tsx`
- `/frontend/src/test/app-shell.test.tsx`
- `/frontend/src/test/queue-page.test.tsx`
- `/frontend/src/test/workspace-page.test.tsx`
- `/src-tauri/Cargo.toml`
- `/src-tauri/build.rs`
- `/src-tauri/tauri.conf.json`
- `/src-tauri/capabilities/default.json`
- `/src-tauri/src/main.rs`
- `/src-tauri/src/lib.rs`
- `/src/apk_hacker/domain/models/workspace.py`
- `/src/apk_hacker/domain/models/case_queue.py`
- `/src/apk_hacker/application/services/workspace_registry_service.py`
- `/src/apk_hacker/application/services/workspace_service.py`
- `/src/apk_hacker/application/services/case_queue_service.py`
- `/src/apk_hacker/application/services/workspace_controller.py`
- `/src/apk_hacker/interfaces/api_fastapi/__init__.py`
- `/src/apk_hacker/interfaces/api_fastapi/app.py`
- `/src/apk_hacker/interfaces/api_fastapi/schemas.py`
- `/src/apk_hacker/interfaces/api_fastapi/websocket_hub.py`
- `/src/apk_hacker/interfaces/api_fastapi/routes_cases.py`
- `/src/apk_hacker/interfaces/api_fastapi/routes_workspace.py`
- `/src/apk_hacker/interfaces/api_fastapi/routes_execution.py`
- `/src/apk_hacker/interfaces/api_fastapi/routes_reports.py`
- `/src/apk_hacker/interfaces/api_fastapi/routes_settings.py`
- `/src/apk_hacker/interfaces/api_fastapi/main.py`
- `/tests/application/test_workspace_registry_service.py`
- `/tests/application/test_workspace_service.py`
- `/tests/application/test_workspace_controller.py`
- `/tests/interfaces/test_fastapi_cases.py`
- `/tests/interfaces/test_fastapi_workspace.py`
- `/tests/interfaces/test_fastapi_execution.py`
- `/tests/interfaces/test_fastapi_reports.py`

### Modify

- `/pyproject.toml`
- `/README.md`
- `/docs/superpowers/specs/2026-04-06-apk-hacker-tauri-redesign.md`
- `/src/apk_hacker/application/services/job_service.py`
- `/src/apk_hacker/application/services/report_export_service.py`
- `/src/apk_hacker/application/services/traffic_capture_service.py`
- `/src/apk_hacker/application/services/custom_script_service.py`

### Leave Untouched During This Plan

- `/.claude/`
- `/AGENTS.md`
- `/CLAUDE.md`
- `/.superpowers/`

---

### Task 1: Bootstrap Tauri + React Desktop Workspace

**Files:**
- Create: `/package.json`
- Create: `/frontend/index.html`
- Create: `/frontend/tsconfig.json`
- Create: `/frontend/vite.config.ts`
- Create: `/frontend/src/main.tsx`
- Create: `/frontend/src/App.tsx`
- Create: `/frontend/src/routes/router.tsx`
- Create: `/frontend/src/test/app-shell.test.tsx`
- Create: `/src-tauri/Cargo.toml`
- Create: `/src-tauri/build.rs`
- Create: `/src-tauri/tauri.conf.json`
- Create: `/src-tauri/capabilities/default.json`
- Create: `/src-tauri/src/main.rs`
- Create: `/src-tauri/src/lib.rs`

- [ ] **Step 1: Write the failing frontend shell smoke test**

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/test/app-shell.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "../App";

describe("App shell", () => {
  it("renders the Chinese workspace frame", () => {
    render(<App />);
    expect(screen.getByText("APKHacker")).toBeInTheDocument();
    expect(screen.getByText("案件队列")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Create the web and Tauri toolchain**

```json
// /Users/penglai/Documents/Objects/APKHacker/package.json
{
  "name": "apkhacker-desktop",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev:web": "vite --config frontend/vite.config.ts",
    "build:web": "vite build --config frontend/vite.config.ts",
    "test:web": "vitest run --config frontend/vite.config.ts",
    "dev:tauri": "tauri dev",
    "build:tauri": "tauri build"
  },
  "dependencies": {
    "@tauri-apps/api": "^2.0.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.30.0",
    "zustand": "^5.0.3"
  },
  "devDependencies": {
    "@tauri-apps/cli": "^2.0.0",
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.3.0",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "jsdom": "^25.0.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.3"
  }
}
```

```json
// /Users/penglai/Documents/Objects/APKHacker/frontend/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"]
}
```

```ts
// /Users/penglai/Documents/Objects/APKHacker/frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  root: "frontend",
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: []
  }
});
```

- [ ] **Step 3: Write the minimal React shell and Tauri skeleton**

```html
<!-- /Users/penglai/Documents/Objects/APKHacker/frontend/index.html -->
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>APKHacker</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/App.tsx
export default function App(): JSX.Element {
  return (
    <main>
      <h1>APKHacker</h1>
      <nav>
        <button type="button">案件队列</button>
        <button type="button">案件工作台</button>
      </nav>
    </main>
  );
}
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

```toml
# /Users/penglai/Documents/Objects/APKHacker/src-tauri/Cargo.toml
[package]
name = "apkhacker-desktop"
version = "0.1.0"
edition = "2021"

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-shell = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

```rust
// /Users/penglai/Documents/Objects/APKHacker/src-tauri/src/main.rs
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    apkhacker_desktop::run();
}
```

```rust
// /Users/penglai/Documents/Objects/APKHacker/src-tauri/src/lib.rs
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .run(tauri::generate_context!())
        .expect("failed to run tauri app");
}
```

```json
// /Users/penglai/Documents/Objects/APKHacker/src-tauri/tauri.conf.json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "APKHacker",
  "version": "0.1.0",
  "identifier": "com.apkhacker.desktop",
  "build": {
    "beforeDevCommand": "npm run dev:web",
    "beforeBuildCommand": "npm run build:web",
    "frontendDist": "../frontend/dist",
    "devUrl": "http://localhost:5173"
  },
  "bundle": {
    "active": true,
    "targets": "app"
  },
  "app": {
    "windows": [
      {
        "label": "main",
        "title": "APKHacker",
        "width": 1440,
        "height": 960
      }
    ],
    "security": {
      "capabilities": ["default"]
    }
  }
}
```

```json
// /Users/penglai/Documents/Objects/APKHacker/src-tauri/capabilities/default.json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "shell:allow-execute"
  ]
}
```

- [ ] **Step 4: Run the frontend smoke test**

Run: `npm run test:web -- frontend/src/test/app-shell.test.tsx`
Expected: PASS with `App shell > renders the Chinese workspace frame`

- [ ] **Step 5: Commit the bootstrap**

```bash
git add package.json frontend src-tauri
git commit -m "feat: bootstrap tauri react desktop shell"
```

### Task 2: Add Workspace Storage and Global Registry Services

**Files:**
- Create: `/src/apk_hacker/domain/models/workspace.py`
- Create: `/src/apk_hacker/domain/models/case_queue.py`
- Create: `/src/apk_hacker/application/services/workspace_registry_service.py`
- Create: `/src/apk_hacker/application/services/workspace_service.py`
- Create: `/tests/application/test_workspace_registry_service.py`
- Create: `/tests/application/test_workspace_service.py`

- [ ] **Step 1: Write failing tests for workspace creation and restore**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/application/test_workspace_service.py
from pathlib import Path

from apk_hacker.application.services.workspace_service import WorkspaceService


def test_create_workspace_copies_sample_and_writes_metadata(tmp_path: Path) -> None:
    sample = tmp_path / "demo.apk"
    sample.write_bytes(b"apk-bytes")
    root = tmp_path / "cases"

    service = WorkspaceService()
    workspace = service.create_workspace(sample, root, title="测试样本")

    assert workspace.workspace_root.exists()
    assert (workspace.workspace_root / "sample" / "original.apk").read_bytes() == b"apk-bytes"
    assert (workspace.workspace_root / "workspace.json").exists()
    assert workspace.title == "测试样本"
```

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/application/test_workspace_registry_service.py
from pathlib import Path

from apk_hacker.application.services.workspace_registry_service import WorkspaceRegistryService


def test_registry_restores_last_opened_workspace(tmp_path: Path) -> None:
    registry = WorkspaceRegistryService(tmp_path / "settings.json")
    workspace_root = tmp_path / "cases" / "case-001"
    workspace_root.mkdir(parents=True)

    registry.set_last_opened_workspace(workspace_root)
    restored = registry.load()

    assert restored.last_opened_workspace == workspace_root
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/application/test_workspace_service.py tests/application/test_workspace_registry_service.py -q`
Expected: FAIL with `ModuleNotFoundError` for the new services

- [ ] **Step 3: Implement the minimal workspace models and services**

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/domain/models/workspace.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WorkspaceRecord:
    case_id: str
    title: str
    workspace_root: Path
    sample_path: Path
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/domain/models/case_queue.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CaseQueueItem:
    case_id: str
    title: str
    workspace_root: str
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/workspace_service.py
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2
from uuid import uuid4
import json

from apk_hacker.domain.models.workspace import WorkspaceRecord


class WorkspaceService:
    def create_workspace(self, sample_path: Path, workspace_root: Path, title: str | None = None) -> WorkspaceRecord:
        case_id = f"case-{uuid4().hex[:12]}"
        destination_root = workspace_root / case_id
        sample_dir = destination_root / "sample"
        sample_dir.mkdir(parents=True, exist_ok=False)
        copied_sample = sample_dir / "original.apk"
        copy2(sample_path, copied_sample)
        metadata = {
            "workspace_version": 1,
            "case_id": case_id,
            "title": title or sample_path.stem,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "sample_filename": copied_sample.name
        }
        (destination_root / "workspace.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return WorkspaceRecord(
            case_id=case_id,
            title=metadata["title"],
            workspace_root=destination_root,
            sample_path=copied_sample,
        )
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/workspace_registry_service.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True, slots=True)
class WorkspaceRegistry:
    default_workspace_root: Path | None = None
    last_opened_workspace: Path | None = None


class WorkspaceRegistryService:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> WorkspaceRegistry:
        if not self._path.exists():
            return WorkspaceRegistry()
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return WorkspaceRegistry(
            default_workspace_root=Path(payload["default_workspace_root"]) if payload.get("default_workspace_root") else None,
            last_opened_workspace=Path(payload["last_opened_workspace"]) if payload.get("last_opened_workspace") else None,
        )

    def set_last_opened_workspace(self, workspace_root: Path) -> None:
        current = self.load()
        payload = {
            "default_workspace_root": str(current.default_workspace_root) if current.default_workspace_root else "",
            "last_opened_workspace": str(workspace_root),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/application/test_workspace_service.py tests/application/test_workspace_registry_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit the workspace storage layer**

```bash
git add src/apk_hacker/domain/models/workspace.py src/apk_hacker/domain/models/case_queue.py src/apk_hacker/application/services/workspace_registry_service.py src/apk_hacker/application/services/workspace_service.py tests/application/test_workspace_registry_service.py tests/application/test_workspace_service.py
git commit -m "feat: add workspace storage services"
```

### Task 3: Extract a GUI-Neutral Workspace Controller

**Files:**
- Create: `/src/apk_hacker/application/services/case_queue_service.py`
- Create: `/src/apk_hacker/application/services/workspace_controller.py`
- Modify: `/src/apk_hacker/application/services/job_service.py`
- Modify: `/src/apk_hacker/application/services/custom_script_service.py`
- Modify: `/src/apk_hacker/application/services/report_export_service.py`
- Create: `/tests/application/test_workspace_controller.py`

- [ ] **Step 1: Write the failing controller test**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/application/test_workspace_controller.py
from pathlib import Path

from apk_hacker.application.services.workspace_controller import WorkspaceController


def test_workspace_controller_loads_static_workspace_and_returns_summary(tmp_path: Path) -> None:
    controller = WorkspaceController(db_root=tmp_path / "cache", scripts_root=tmp_path / "scripts")
    sample_path = tmp_path / "sample.apk"
    sample_path.write_bytes(b"apk")

    state = controller.initialize_workspace(sample_path=sample_path, workspace_root=tmp_path / "workspaces")

    assert state.sample_path.name == "original.apk"
    assert state.summary_text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/application/test_workspace_controller.py -q`
Expected: FAIL with `ModuleNotFoundError` for `workspace_controller`

- [ ] **Step 3: Implement the neutral controller over existing services**

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/workspace_controller.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from apk_hacker.application.services.job_service import JobService
from apk_hacker.application.services.workspace_service import WorkspaceService


@dataclass(frozen=True, slots=True)
class WorkspaceState:
    case_id: str
    workspace_root: Path
    sample_path: Path
    summary_text: str


class WorkspaceController:
    def __init__(self, db_root: Path, scripts_root: Path, job_service: JobService | None = None) -> None:
        self._db_root = db_root
        self._scripts_root = scripts_root
        self._workspace_service = WorkspaceService()
        self._job_service = job_service or JobService()

    def initialize_workspace(self, sample_path: Path, workspace_root: Path) -> WorkspaceState:
        workspace = self._workspace_service.create_workspace(sample_path, workspace_root)
        self._job_service.load_static_workspace(
            workspace.sample_path,
            output_dir=workspace.workspace_root / "static",
        )
        return WorkspaceState(
            case_id=workspace.case_id,
            workspace_root=workspace.workspace_root,
            sample_path=workspace.sample_path,
            summary_text=f"已初始化工作区 {workspace.title}",
        )
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/case_queue_service.py
from __future__ import annotations

from pathlib import Path
import json


class CaseQueueService:
    def list_workspaces(self, root: Path) -> list[dict[str, str]]:
        if not root.exists():
            return []
        workspaces: list[dict[str, str]] = []
        for workspace_json in root.glob("*/workspace.json"):
            payload = json.loads(workspace_json.read_text(encoding="utf-8"))
            workspaces.append(
                {
                    "case_id": payload["case_id"],
                    "title": payload["title"],
                    "workspace_root": str(workspace_json.parent),
                }
            )
        return sorted(workspaces, key=lambda item: item["case_id"])
```

- [ ] **Step 4: Run the controller test**

Run: `uv run pytest tests/application/test_workspace_controller.py -q`
Expected: PASS

- [ ] **Step 5: Commit the controller extraction**

```bash
git add src/apk_hacker/application/services/case_queue_service.py src/apk_hacker/application/services/workspace_controller.py src/apk_hacker/application/services/job_service.py src/apk_hacker/application/services/custom_script_service.py src/apk_hacker/application/services/report_export_service.py tests/application/test_workspace_controller.py
git commit -m "feat: extract gui neutral workspace controller"
```

### Task 4: Expose FastAPI REST and WebSocket Endpoints

**Files:**
- Modify: `/pyproject.toml`
- Create: `/src/apk_hacker/interfaces/api_fastapi/__init__.py`
- Create: `/src/apk_hacker/interfaces/api_fastapi/app.py`
- Create: `/src/apk_hacker/interfaces/api_fastapi/schemas.py`
- Create: `/src/apk_hacker/interfaces/api_fastapi/websocket_hub.py`
- Create: `/src/apk_hacker/interfaces/api_fastapi/routes_cases.py`
- Create: `/src/apk_hacker/interfaces/api_fastapi/routes_workspace.py`
- Create: `/src/apk_hacker/interfaces/api_fastapi/routes_execution.py`
- Create: `/src/apk_hacker/interfaces/api_fastapi/routes_reports.py`
- Create: `/src/apk_hacker/interfaces/api_fastapi/routes_settings.py`
- Create: `/src/apk_hacker/interfaces/api_fastapi/main.py`
- Create: `/tests/interfaces/test_fastapi_cases.py`
- Create: `/tests/interfaces/test_fastapi_workspace.py`
- Create: `/tests/interfaces/test_fastapi_execution.py`
- Create: `/tests/interfaces/test_fastapi_reports.py`

- [ ] **Step 1: Write failing API tests**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_fastapi_cases.py
from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_list_cases_returns_ok() -> None:
    client = TestClient(build_app())
    response = client.get("/api/cases")
    assert response.status_code == 200
    assert response.json()["items"] == []
```

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_fastapi_execution.py
from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_websocket_accepts_connections() -> None:
    client = TestClient(build_app())
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "ping"})
        payload = websocket.receive_json()
        assert payload["type"] == "pong"
```

- [ ] **Step 2: Add API dependencies and run the tests**

```toml
# /Users/penglai/Documents/Objects/APKHacker/pyproject.toml
[project]
dependencies = [
  "fastapi>=0.115,<1",
  "Jinja2>=3.1,<4",
  "PyQt6>=6.7,<7",
  "uvicorn>=0.32,<1"
]
```

Run: `uv run pytest tests/interfaces/test_fastapi_cases.py tests/interfaces/test_fastapi_execution.py -q`
Expected: FAIL with `ModuleNotFoundError` for `api_fastapi`

- [ ] **Step 3: Implement the minimal FastAPI app and WebSocket hub**

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/websocket_hub.py
from __future__ import annotations

from fastapi import WebSocket


class WebSocketHub:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/app.py
from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from apk_hacker.interfaces.api_fastapi.websocket_hub import WebSocketHub


def build_app() -> FastAPI:
    app = FastAPI(title="APKHacker Local API")
    hub = WebSocketHub()

    @app.get("/api/cases")
    def list_cases() -> dict[str, list[dict[str, str]]]:
        return {"items": []}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await hub.connect(websocket)
        try:
            while True:
                payload = await websocket.receive_json()
                if payload.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
        except WebSocketDisconnect:
            hub.disconnect(websocket)

    return app
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/main.py
from __future__ import annotations

import uvicorn

from apk_hacker.interfaces.api_fastapi.app import build_app


def main() -> None:
    uvicorn.run(build_app(), host="127.0.0.1", port=8765)
```

- [ ] **Step 4: Run the API tests**

Run: `uv run pytest tests/interfaces/test_fastapi_cases.py tests/interfaces/test_fastapi_execution.py -q`
Expected: PASS

- [ ] **Step 5: Commit the API layer**

```bash
git add pyproject.toml src/apk_hacker/interfaces/api_fastapi tests/interfaces/test_fastapi_cases.py tests/interfaces/test_fastapi_workspace.py tests/interfaces/test_fastapi_execution.py tests/interfaces/test_fastapi_reports.py
git commit -m "feat: add local fastapi api and websocket hub"
```

### Task 5: Build the Chinese React App Frame and Dual-Mode Routing

**Files:**
- Create: `/frontend/src/lib/types.ts`
- Create: `/frontend/src/store/app-store.ts`
- Create: `/frontend/src/pages/CaseQueuePage.tsx`
- Create: `/frontend/src/pages/CaseWorkspacePage.tsx`
- Create: `/frontend/src/components/layout/AppFrame.tsx`
- Create: `/frontend/src/test/queue-page.test.tsx`
- Create: `/frontend/src/test/workspace-page.test.tsx`
- Modify: `/frontend/src/App.tsx`
- Modify: `/frontend/src/routes/router.tsx`

- [ ] **Step 1: Write failing route tests**

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/test/queue-page.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CaseQueuePage } from "../pages/CaseQueuePage";

describe("CaseQueuePage", () => {
  it("renders the queue title in Chinese", () => {
    render(<CaseQueuePage />);
    expect(screen.getByText("案件队列")).toBeInTheDocument();
  });
});
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/test/workspace-page.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CaseWorkspacePage } from "../pages/CaseWorkspacePage";

describe("CaseWorkspacePage", () => {
  it("renders the workspace heading in Chinese", () => {
    render(<CaseWorkspacePage />);
    expect(screen.getByText("案件工作台")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the route tests**

Run: `npm run test:web -- frontend/src/test/queue-page.test.tsx frontend/src/test/workspace-page.test.tsx`
Expected: FAIL with `Cannot find module '../pages/CaseQueuePage'`

- [ ] **Step 3: Implement the shell, routes, and pages**

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/components/layout/AppFrame.tsx
import { Link, Outlet } from "react-router-dom";

export function AppFrame(): JSX.Element {
  return (
    <div>
      <header>
        <h1>APKHacker</h1>
        <nav>
          <Link to="/queue">案件队列</Link>
          <Link to="/workspace">案件工作台</Link>
        </nav>
      </header>
      <Outlet />
    </div>
  );
}
```

```ts
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/store/app-store.ts
import { create } from "zustand";

type AppStore = {
  currentMode: "queue" | "workspace";
  setCurrentMode: (mode: "queue" | "workspace") => void;
};

export const useAppStore = create<AppStore>((set) => ({
  currentMode: "queue",
  setCurrentMode: (mode) => set({ currentMode: mode }),
}));
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/pages/CaseQueuePage.tsx
export function CaseQueuePage(): JSX.Element {
  return (
    <section>
      <h2>案件队列</h2>
      <p>管理导入样本、批量状态和案件筛选。</p>
    </section>
  );
}
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/pages/CaseWorkspacePage.tsx
export function CaseWorkspacePage(): JSX.Element {
  return (
    <section>
      <h2>案件工作台</h2>
      <p>查看静态简报、Hook Studio、执行控制台与导出结果。</p>
    </section>
  );
}
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/routes/router.tsx
import { createBrowserRouter, Navigate } from "react-router-dom";

import { AppFrame } from "../components/layout/AppFrame";
import { CaseQueuePage } from "../pages/CaseQueuePage";
import { CaseWorkspacePage } from "../pages/CaseWorkspacePage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppFrame />,
    children: [
      { index: true, element: <Navigate to="/queue" replace /> },
      { path: "queue", element: <CaseQueuePage /> },
      { path: "workspace", element: <CaseWorkspacePage /> },
    ],
  },
]);
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/App.tsx
import { RouterProvider } from "react-router-dom";

import { router } from "./routes/router";

export default function App(): JSX.Element {
  return <RouterProvider router={router} />;
}
```

- [ ] **Step 4: Run the route tests**

Run: `npm run test:web -- frontend/src/test/queue-page.test.tsx frontend/src/test/workspace-page.test.tsx frontend/src/test/app-shell.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit the dual-mode shell**

```bash
git add frontend/src/App.tsx frontend/src/routes/router.tsx frontend/src/pages frontend/src/components/layout frontend/src/test
git commit -m "feat: add dual mode chinese react shell"
```

### Task 6: Implement Case Queue and Workspace Data Flows

**Files:**
- Create: `/frontend/src/lib/api.ts`
- Create: `/frontend/src/lib/types.ts`
- Create: `/frontend/src/components/queue/CaseQueueTable.tsx`
- Create: `/frontend/src/components/workspace/StaticBriefPanel.tsx`
- Create: `/frontend/src/components/workspace/HookStudioPanel.tsx`
- Modify: `/frontend/src/pages/CaseQueuePage.tsx`
- Modify: `/frontend/src/pages/CaseWorkspacePage.tsx`
- Modify: `/src/apk_hacker/interfaces/api_fastapi/routes_cases.py`
- Modify: `/src/apk_hacker/interfaces/api_fastapi/routes_workspace.py`
- Create: `/tests/interfaces/test_fastapi_workspace.py`

- [ ] **Step 1: Write failing queue/workspace API tests**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_fastapi_workspace.py
from pathlib import Path

from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_import_case_creates_workspace(tmp_path: Path) -> None:
    sample = tmp_path / "demo.apk"
    sample.write_bytes(b"apk")
    client = TestClient(build_app())

    response = client.post(
        "/api/cases/import",
        json={
            "sample_path": str(sample),
            "workspace_root": str(tmp_path / "workspaces"),
            "title": "队列测试"
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "队列测试"
```

- [ ] **Step 2: Run the API test**

Run: `uv run pytest tests/interfaces/test_fastapi_workspace.py -q`
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Implement case import and workspace fetch endpoints**

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_cases.py
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, status
from pydantic import BaseModel

from apk_hacker.application.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/api/cases", tags=["cases"])
workspace_service = WorkspaceService()


class ImportCaseRequest(BaseModel):
    sample_path: str
    workspace_root: str
    title: str | None = None


@router.post("/import", status_code=status.HTTP_201_CREATED)
def import_case(payload: ImportCaseRequest) -> dict[str, str]:
    record = workspace_service.create_workspace(
        sample_path=Path(payload.sample_path),
        workspace_root=Path(payload.workspace_root),
        title=payload.title,
    )
    return {
        "case_id": record.case_id,
        "title": record.title,
        "workspace_root": str(record.workspace_root),
        "sample_path": str(record.sample_path),
    }
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_workspace.py
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/cases", tags=["workspace"])


@router.get("/{case_id}/workspace")
def get_workspace(case_id: str) -> dict[str, str]:
    return {
        "case_id": case_id,
        "view": "workspace",
    }
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/lib/api.ts
export type CaseItem = {
  case_id: string;
  title: string;
  workspace_root?: string;
};

export async function listCases(): Promise<{ items: CaseItem[] }> {
  const response = await fetch("/api/cases");
  if (!response.ok) {
    throw new Error("加载案件列表失败");
  }
  return response.json();
}
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/components/queue/CaseQueueTable.tsx
type QueueItem = {
  case_id: string;
  title: string;
};

export function CaseQueueTable({ items }: { items: QueueItem[] }): JSX.Element {
  return (
    <table>
      <thead>
        <tr>
          <th>案件</th>
          <th>编号</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.case_id}>
            <td>{item.title}</td>
            <td>{item.case_id}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 4: Add the first queue and workspace panels**

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/StaticBriefPanel.tsx
export function StaticBriefPanel(): JSX.Element {
  return (
    <section>
      <h3>静态简报</h3>
      <p>这里展示包名、技术标签、危险权限、回连线索和加密信号。</p>
    </section>
  );
}
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/HookStudioPanel.tsx
export function HookStudioPanel(): JSX.Element {
  return (
    <section>
      <h3>Hook Studio</h3>
      <p>这里整合方法搜索、Hook 推荐、模板建议、脚本编辑与计划预览。</p>
    </section>
  );
}
```

Run: `uv run pytest tests/interfaces/test_fastapi_workspace.py -q && npm run test:web -- frontend/src/test/workspace-page.test.tsx frontend/src/test/queue-page.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit the queue/workspace data flow**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/types.ts frontend/src/components/queue frontend/src/components/workspace frontend/src/pages/CaseQueuePage.tsx frontend/src/pages/CaseWorkspacePage.tsx src/apk_hacker/interfaces/api_fastapi/routes_cases.py src/apk_hacker/interfaces/api_fastapi/routes_workspace.py tests/interfaces/test_fastapi_workspace.py
git commit -m "feat: add queue and workspace data flows"
```

### Task 7: Implement Execution Console, Startup Restore, WebSocket Events, and macOS Sidecar Startup

**Files:**
- Create: `/frontend/src/lib/ws.ts`
- Create: `/frontend/src/components/workspace/ExecutionConsolePanel.tsx`
- Create: `/frontend/src/components/workspace/EvidencePanel.tsx`
- Create: `/frontend/src/components/workspace/ReportsPanel.tsx`
- Modify: `/frontend/src/pages/CaseWorkspacePage.tsx`
- Modify: `/src-tauri/src/lib.rs`
- Modify: `/src-tauri/tauri.conf.json`
- Modify: `/src-tauri/capabilities/default.json`
- Modify: `/src/apk_hacker/interfaces/api_fastapi/main.py`
- Modify: `/src/apk_hacker/interfaces/api_fastapi/routes_execution.py`
- Modify: `/src/apk_hacker/interfaces/api_fastapi/routes_reports.py`
- Modify: `/src/apk_hacker/interfaces/api_fastapi/routes_settings.py`
- Modify: `/README.md`
- Modify: `/docs/superpowers/specs/2026-04-06-apk-hacker-tauri-redesign.md`

- [ ] **Step 1: Write failing tests for execution events and startup restore**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_fastapi_reports.py
from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_export_report_endpoint_returns_path() -> None:
    client = TestClient(build_app())
    response = client.post("/api/cases/case-001/reports/export")
    assert response.status_code == 200
    assert "report_path" in response.json()
```

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_fastapi_execution.py
from fastapi.testclient import TestClient

from apk_hacker.interfaces.api_fastapi.app import build_app


def test_startup_settings_include_last_workspace() -> None:
    client = TestClient(build_app())
    response = client.get("/api/settings/startup")
    assert response.status_code == 200
    assert "launch_view" in response.json()
```

```ts
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/lib/ws.ts
export type WorkspaceEvent = {
  type: string;
  case_id?: string;
  payload?: Record<string, unknown>;
};
```

- [ ] **Step 2: Run the failing backend test**

Run: `uv run pytest tests/interfaces/test_fastapi_reports.py tests/interfaces/test_fastapi_execution.py -q`
Expected: FAIL with `404 Not Found`

- [ ] **Step 3: Add execution/report endpoints and the React console panels**

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_reports.py
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/cases", tags=["reports"])


@router.post("/{case_id}/reports/export")
def export_report(case_id: str) -> dict[str, str]:
    return {
        "case_id": case_id,
        "report_path": f"/tmp/{case_id}/reports/merged-report.md",
    }
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_execution.py
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/cases", tags=["execution"])


@router.post("/{case_id}/executions")
def create_execution(case_id: str) -> dict[str, str]:
    return {
        "case_id": case_id,
        "status": "started",
    }
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/api_fastapi/routes_settings.py
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/startup")
def get_startup_settings() -> dict[str, str | None]:
    return {
        "launch_view": "workspace",
        "last_workspace_root": None,
    }
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/ExecutionConsolePanel.tsx
export function ExecutionConsolePanel(): JSX.Element {
  return (
    <section>
      <h3>执行控制台</h3>
      <button type="button">开始执行</button>
      <p>这里展示执行模式、实时日志、stderr/stdout 和运行包路径。</p>
    </section>
  );
}
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/EvidencePanel.tsx
export function EvidencePanel(): JSX.Element {
  return (
    <section>
      <h3>证据中心</h3>
      <p>这里展示 Hook 事件、HAR 导入、SQLite 与运行包信息。</p>
    </section>
  );
}
```

```tsx
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/ReportsPanel.tsx
export function ReportsPanel(): JSX.Element {
  return (
    <section>
      <h3>报告与导出</h3>
      <button type="button">导出报告</button>
    </section>
  );
}
```

```ts
// /Users/penglai/Documents/Objects/APKHacker/frontend/src/lib/ws.ts
export function connectWorkspaceEvents(onMessage: (event: WorkspaceEvent) => void): WebSocket {
  const socket = new WebSocket("ws://127.0.0.1:8765/ws");
  socket.onmessage = (message) => {
    onMessage(JSON.parse(message.data) as WorkspaceEvent);
  };
  return socket;
}
```

- [ ] **Step 4: Wire Tauri to start the Python sidecar on macOS**

```json
// /Users/penglai/Documents/Objects/APKHacker/src-tauri/tauri.conf.json
{
  "bundle": {
    "active": true,
    "targets": "app",
    "externalBin": ["binaries/apkhacker-api"]
  }
}
```

```json
// /Users/penglai/Documents/Objects/APKHacker/src-tauri/capabilities/default.json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "shell:allow-execute",
    "shell:allow-spawn"
  ]
}
```

```rust
// /Users/penglai/Documents/Objects/APKHacker/src-tauri/src/lib.rs
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let sidecar = app.shell().sidecar("apkhacker-api")?;
            let (_rx, _child) = sidecar.spawn()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("failed to run tauri app");
}
```

- [ ] **Step 5: Verify and commit the first end-to-end replacement milestone**

Run:

```bash
uv run pytest tests/interfaces/test_fastapi_reports.py -q
uv run pytest tests/interfaces/test_fastapi_execution.py -q
npm run test:web -- frontend/src/test/workspace-page.test.tsx
npm run build:web
```

Expected:

- FastAPI report test PASS
- FastAPI startup settings test PASS
- React workspace page test PASS
- frontend build PASS

Commit:

```bash
git add frontend/src/lib/ws.ts frontend/src/components/workspace src-tauri src/apk_hacker/interfaces/api_fastapi/routes_execution.py src/apk_hacker/interfaces/api_fastapi/routes_reports.py src/apk_hacker/interfaces/api_fastapi/routes_settings.py src/apk_hacker/interfaces/api_fastapi/main.py README.md docs/superpowers/specs/2026-04-06-apk-hacker-tauri-redesign.md tests/interfaces/test_fastapi_reports.py tests/interfaces/test_fastapi_execution.py
git commit -m "feat: add execution console and tauri sidecar startup"
```

---

## Self-Review Checklist

- 该计划覆盖了新 spec 中的核心要求：双模式 IA、REST/WebSocket、本地 workspace、macOS Apple Silicon 首发、Python sidecar、Rust 友好迁移。
- 该计划故意先做 API 抽离，再做 Tauri 外壳和新前端，避免“前端重做和后端大切换同时发生”。
- 该计划没有要求在本阶段迁移静态分析引擎和 Frida worker 到 Rust，符合当前工程现实。

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-06-apk-hacker-tauri-redesign-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
