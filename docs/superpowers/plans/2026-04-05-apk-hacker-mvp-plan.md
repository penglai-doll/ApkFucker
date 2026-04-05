# APKHacker MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first testable APKHacker MVP: migrate the static analysis skill into the repository, expose method-level indexes, support function-centered Hook planning plus custom Frida scripts, run a fake dynamic workflow, and surface everything in a PyQt6 prototype that can open samples in local JADX.

**Architecture:** The implementation keeps analysis logic out of the GUI. `static_engine` owns the migrated static-analysis code and JADX export, `domain` owns stable models, `application` owns workflows and plugin orchestration, `infrastructure` owns SQLite/templates/execution backends, and `interfaces/gui_pyqt` stays a thin shell over application services. The MVP remains PyQt6-first but uses service boundaries that can later be wrapped by FastAPI and consumed by Tauri.

**Tech Stack:** Python 3.11+, PyQt6, Jinja2, sqlite3, pytest, pytest-qt, ripgrep, local JADX CLI/GUI

---

## File Map

### Create

- `/.gitignore`
- `/pyproject.toml`
- `/src/apk_hacker/__init__.py`
- `/src/apk_hacker/static_engine/__init__.py`
- `/src/apk_hacker/static_engine/analyzer.py`
- `/src/apk_hacker/static_engine/legacy/` copied from the installed `android-malware-analysis` skill
- `/src/apk_hacker/static_engine/tooling/jadx_exporter.py`
- `/src/apk_hacker/domain/models/static_inputs.py`
- `/src/apk_hacker/domain/models/indexes.py`
- `/src/apk_hacker/domain/models/hook_plan.py`
- `/src/apk_hacker/domain/models/hook_event.py`
- `/src/apk_hacker/domain/models/job.py`
- `/src/apk_hacker/domain/services/method_indexer.py`
- `/src/apk_hacker/application/plugins/contracts.py`
- `/src/apk_hacker/application/plugins/builtin/method_hook.py`
- `/src/apk_hacker/application/services/static_adapter.py`
- `/src/apk_hacker/application/services/hook_plan_service.py`
- `/src/apk_hacker/application/services/custom_script_service.py`
- `/src/apk_hacker/application/services/job_service.py`
- `/src/apk_hacker/infrastructure/persistence/hook_log_store.py`
- `/src/apk_hacker/infrastructure/execution/fake_backend.py`
- `/src/apk_hacker/infrastructure/integrations/jadx_launcher.py`
- `/src/apk_hacker/interfaces/gui_pyqt/main.py`
- `/src/apk_hacker/interfaces/gui_pyqt/main_window.py`
- `/templates/generic/method_hook.js.j2`
- `/tests/conftest.py`
- `/tests/fixtures/static_outputs/sample_analysis.json`
- `/tests/fixtures/static_outputs/sample_callback-config.json`
- `/tests/fixtures/jadx_sources/com/demo/net/Config.java`
- `/tests/fixtures/jadx_sources/com/demo/entry/MainActivity.java`
- `/tests/static_engine/test_static_analyzer.py`
- `/tests/static_engine/test_jadx_exporter.py`
- `/tests/application/test_static_adapter.py`
- `/tests/domain/test_method_indexer.py`
- `/tests/application/test_hook_plan_service.py`
- `/tests/infrastructure/test_hook_log_store.py`
- `/tests/infrastructure/test_fake_backend.py`
- `/tests/application/test_job_service.py`
- `/tests/interfaces/test_main_window_smoke.py`

### Modify

- `/docs/superpowers/specs/2026-04-05-apk-hacker-mvp-design.md`
  - Add a link to the implementation plan after the plan exists

---

### Task 1: Bootstrap The Python Project

**Files:**
- Create: `/.gitignore`
- Create: `/pyproject.toml`
- Create: `/src/apk_hacker/__init__.py`
- Create: `/tests/conftest.py`
- Test: `/tests/application/test_project_smoke.py`

- [ ] **Step 1: Write the failing smoke test**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/application/test_project_smoke.py
from apk_hacker import __version__


def test_project_version_string() -> None:
    assert __version__ == "0.1.0"
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run: `python -m pytest tests/application/test_project_smoke.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'apk_hacker'`

- [ ] **Step 3: Create the package skeleton and dependency metadata**

```toml
# /Users/penglai/Documents/Objects/APKHacker/pyproject.toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "apk-hacker"
version = "0.1.0"
description = "Local-first Android APK static and dynamic analysis workstation"
requires-python = ">=3.11"
dependencies = [
  "Jinja2>=3.1,<4",
  "PyQt6>=6.7,<7",
]

[project.optional-dependencies]
dev = [
  "pytest>=8,<9",
  "pytest-qt>=4.4,<5",
]

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
```

```gitignore
# /Users/penglai/Documents/Objects/APKHacker/.gitignore
__pycache__/
.pytest_cache/
.DS_Store
*.pyc
*.pyo
*.db
*.sqlite3
.venv/
dist/
build/
output/
报告/
cache/
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/__init__.py
__all__ = ["__version__"]

__version__ = "0.1.0"
```

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/conftest.py
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

- [ ] **Step 4: Run the smoke test to verify it passes**

Run: `python -m pytest tests/application/test_project_smoke.py -q`
Expected: PASS

- [ ] **Step 5: Commit the bootstrap**

```bash
git add .gitignore pyproject.toml src/apk_hacker/__init__.py tests/conftest.py tests/application/test_project_smoke.py
git commit -m "chore: bootstrap python project"
```

### Task 2: Seed The First-Party Static Engine

**Files:**
- Create: `/src/apk_hacker/static_engine/__init__.py`
- Create: `/src/apk_hacker/static_engine/analyzer.py`
- Create: `/src/apk_hacker/static_engine/legacy/` (copied source)
- Test: `/tests/static_engine/test_static_analyzer.py`

- [ ] **Step 1: Write the failing static-engine facade test**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/static_engine/test_static_analyzer.py
from pathlib import Path

from apk_hacker.static_engine.analyzer import StaticAnalyzer


def test_static_analyzer_exposes_legacy_entrypoint(tmp_path: Path) -> None:
    analyzer = StaticAnalyzer()
    assert analyzer.legacy_module_name == "investigate_android_app"
    assert analyzer.resolve_output_root(tmp_path / "sample.apk", None) == tmp_path
```

- [ ] **Step 2: Run the static-engine test to verify it fails**

Run: `python -m pytest tests/static_engine/test_static_analyzer.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'apk_hacker.static_engine'`

- [ ] **Step 3: Copy the installed skill into the repository and create a thin facade**

```bash
mkdir -p src/apk_hacker/static_engine/legacy
cp -R "${CODEX_HOME:-$HOME/.codex}/skills/android-malware-analysis/scripts/"* src/apk_hacker/static_engine/legacy/
cp -R "${CODEX_HOME:-$HOME/.codex}/skills/android-malware-analysis/references" src/apk_hacker/static_engine/legacy/
cp -R "${CODEX_HOME:-$HOME/.codex}/skills/android-malware-analysis/examples" src/apk_hacker/static_engine/legacy/
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/static_engine/__init__.py
from .analyzer import StaticAnalyzer, StaticArtifacts

__all__ = ["StaticAnalyzer", "StaticArtifacts"]
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/static_engine/analyzer.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


LEGACY_DIR = Path(__file__).resolve().parent / "legacy"
if str(LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(LEGACY_DIR))


@dataclass(frozen=True)
class StaticArtifacts:
    output_root: Path
    report_dir: Path
    cache_dir: Path
    analysis_json: Path | None = None
    callback_config_json: Path | None = None
    noise_log_json: Path | None = None
    jadx_sources_dir: Path | None = None


class StaticAnalyzer:
    legacy_module_name = "investigate_android_app"

    def resolve_output_root(self, target_path: Path, output_dir: Path | None) -> Path:
        if output_dir is not None:
            return output_dir.resolve()
        return target_path.resolve().parent
```

- [ ] **Step 4: Run the static-engine test to verify it passes**

Run: `python -m pytest tests/static_engine/test_static_analyzer.py -q`
Expected: PASS

- [ ] **Step 5: Commit the migrated static-engine seed**

```bash
git add src/apk_hacker/static_engine tests/static_engine/test_static_analyzer.py
git commit -m "feat: seed first-party static engine"
```

### Task 3: Add JADX Export Support And Artifact Contracts

**Files:**
- Create: `/src/apk_hacker/static_engine/tooling/jadx_exporter.py`
- Modify: `/src/apk_hacker/static_engine/analyzer.py`
- Test: `/tests/static_engine/test_jadx_exporter.py`

- [ ] **Step 1: Write the failing JADX exporter test**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/static_engine/test_jadx_exporter.py
from pathlib import Path

from apk_hacker.static_engine.tooling.jadx_exporter import build_jadx_command


def test_build_jadx_command_targets_source_directory(tmp_path: Path) -> None:
    apk_path = tmp_path / "demo.apk"
    out_dir = tmp_path / "jadx"
    command = build_jadx_command("jadx", apk_path, out_dir)
    assert command == [
        "jadx",
        "--output-dir-src",
        str(out_dir / "sources"),
        "--output-dir-res",
        str(out_dir / "resources"),
        str(apk_path),
    ]
```

- [ ] **Step 2: Run the exporter test to verify it fails**

Run: `python -m pytest tests/static_engine/test_jadx_exporter.py -q`
Expected: FAIL because `jadx_exporter.py` does not exist

- [ ] **Step 3: Implement the exporter helper and extend the artifact contract**

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/static_engine/tooling/jadx_exporter.py
from __future__ import annotations

from pathlib import Path


def build_jadx_command(jadx_binary: str, apk_path: Path, out_dir: Path) -> list[str]:
    return [
        jadx_binary,
        "--output-dir-src",
        str(out_dir / "sources"),
        "--output-dir-res",
        str(out_dir / "resources"),
        str(apk_path),
    ]
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/static_engine/analyzer.py
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StaticArtifacts:
    output_root: Path
    report_dir: Path
    cache_dir: Path
    analysis_json: Path | None = None
    callback_config_json: Path | None = None
    noise_log_json: Path | None = None
    jadx_project_dir: Path | None = None
    jadx_sources_dir: Path | None = None
```

- [ ] **Step 4: Run the exporter test to verify it passes**

Run: `python -m pytest tests/static_engine/test_jadx_exporter.py -q`
Expected: PASS

- [ ] **Step 5: Commit the JADX export contract**

```bash
git add src/apk_hacker/static_engine/tooling/jadx_exporter.py src/apk_hacker/static_engine/analyzer.py tests/static_engine/test_jadx_exporter.py
git commit -m "feat: add jadx export contract"
```

### Task 4: Normalize Static Outputs Into Stable Models

**Files:**
- Create: `/src/apk_hacker/domain/models/config.py`
- Create: `/src/apk_hacker/domain/models/static_inputs.py`
- Create: `/src/apk_hacker/application/services/static_adapter.py`
- Create: `/tests/fixtures/static_outputs/sample_analysis.json`
- Create: `/tests/fixtures/static_outputs/sample_callback-config.json`
- Test: `/tests/application/test_static_adapter.py`

- [ ] **Step 1: Write the failing adapter test**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/application/test_static_adapter.py
from pathlib import Path
import json

from apk_hacker.application.services.static_adapter import StaticAdapter


def test_static_adapter_normalizes_skill_outputs() -> None:
    fixture_root = Path("tests/fixtures/static_outputs")
    analysis = json.loads((fixture_root / "sample_analysis.json").read_text(encoding="utf-8"))
    callback = json.loads((fixture_root / "sample_callback-config.json").read_text(encoding="utf-8"))

    result = StaticAdapter().adapt(
        sample_path=Path("/samples/demo.apk"),
        analysis_report=analysis,
        callback_config=callback,
        artifact_paths={"analysis_json": "cache/demo/analysis.json"},
    )

    assert result.package_name == "com.demo.shell"
    assert "webview-hybrid" in result.technical_tags
    assert "android.permission.READ_SMS" in result.dangerous_permissions
    assert result.callback_endpoints["domains"] == ["demo-c2.example"]
```

- [ ] **Step 2: Run the adapter test to verify it fails**

Run: `python -m pytest tests/application/test_static_adapter.py -q`
Expected: FAIL because the adapter and models do not exist

- [ ] **Step 3: Add fixture files and implement the normalized model**

```json
# /Users/penglai/Documents/Objects/APKHacker/tests/fixtures/static_outputs/sample_analysis.json
{
  "sample": {
    "target": "/samples/demo.apk",
    "package_type": "apk"
  },
  "base_info": {
    "package_name": "com.demo.shell",
    "dangerous_permissions": [
      "android.permission.READ_SMS",
      "android.permission.RECORD_AUDIO"
    ]
  },
  "technical_profile": {
    "primary_type": "webview-hybrid",
    "types": [
      {
        "name": "webview-hybrid"
      }
    ]
  },
  "crypto_profile": {
    "algorithms": [
      "AES"
    ]
  },
  "limitations": [
    "demo limitation"
  ]
}
```

```json
# /Users/penglai/Documents/Objects/APKHacker/tests/fixtures/static_outputs/sample_callback-config.json
{
  "endpoints": {
    "urls": [
      "https://demo-c2.example/api/upload"
    ],
    "domains": [
      "demo-c2.example"
    ],
    "ips": [],
    "emails": []
  },
  "clues": [
    {
      "source": "sources/com/demo/net/Config.java",
      "value": "\"https://\" + host + \"/api/upload\""
    }
  ]
}
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/domain/models/static_inputs.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StaticInputs:
    sample_path: Path
    package_name: str | None
    technical_tags: tuple[str, ...]
    dangerous_permissions: tuple[str, ...]
    callback_endpoints: dict[str, list[str]]
    callback_clues: tuple[dict[str, str], ...]
    crypto_signals: tuple[str, ...]
    packer_hints: tuple[str, ...]
    limitations: tuple[str, ...]
    artifact_paths: dict[str, str]
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/static_adapter.py
from __future__ import annotations

from pathlib import Path

from apk_hacker.domain.models.static_inputs import StaticInputs


class StaticAdapter:
    def adapt(
        self,
        sample_path: Path,
        analysis_report: dict,
        callback_config: dict,
        artifact_paths: dict[str, str],
    ) -> StaticInputs:
        types = tuple(item["name"] for item in analysis_report.get("technical_profile", {}).get("types", []))
        base_info = analysis_report.get("base_info", {})
        crypto = tuple(analysis_report.get("crypto_profile", {}).get("algorithms", []))

        return StaticInputs(
            sample_path=sample_path,
            package_name=base_info.get("package_name"),
            technical_tags=types,
            dangerous_permissions=tuple(base_info.get("dangerous_permissions", [])),
            callback_endpoints=callback_config.get("endpoints", {"urls": [], "domains": [], "ips": [], "emails": []}),
            callback_clues=tuple(callback_config.get("clues", [])),
            crypto_signals=crypto,
            packer_hints=tuple(),
            limitations=tuple(analysis_report.get("limitations", [])),
            artifact_paths=artifact_paths,
        )
```

- [ ] **Step 4: Run the adapter test to verify it passes**

Run: `python -m pytest tests/application/test_static_adapter.py -q`
Expected: PASS

- [ ] **Step 5: Commit the static adapter**

```bash
git add src/apk_hacker/domain/models/static_inputs.py src/apk_hacker/application/services/static_adapter.py tests/fixtures/static_outputs tests/application/test_static_adapter.py
git commit -m "feat: normalize static analysis outputs"
```

### Task 5: Build The Method Index And Search

**Files:**
- Create: `/src/apk_hacker/domain/models/indexes.py`
- Create: `/src/apk_hacker/domain/services/method_indexer.py`
- Create: `/src/apk_hacker/domain/services/hook_search.py`
- Create: `/tests/fixtures/jadx_sources/com/demo/net/Config.java`
- Create: `/tests/fixtures/jadx_sources/com/demo/entry/MainActivity.java`
- Test: `/tests/domain/test_method_indexer.py`

- [ ] **Step 1: Write the failing method-index test**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/domain/test_method_indexer.py
from pathlib import Path

from apk_hacker.domain.services.method_indexer import JavaMethodIndexer


def test_method_indexer_extracts_class_and_method_signatures() -> None:
    root = Path("tests/fixtures/jadx_sources")
    result = JavaMethodIndexer().build(root)

    class_names = {item.class_name for item in result.classes}
    methods = {(item.class_name, item.method_name) for item in result.methods}

    assert "com.demo.net.Config" in class_names
    assert ("com.demo.entry.MainActivity", "onCreate") in methods
    assert ("com.demo.net.Config", "buildUploadUrl") in methods
```

- [ ] **Step 2: Run the method-index test to verify it fails**

Run: `python -m pytest tests/domain/test_method_indexer.py -q`
Expected: FAIL because the indexer and model do not exist

- [ ] **Step 3: Add a small JADX-style fixture and implement the indexer**

```java
// /Users/penglai/Documents/Objects/APKHacker/tests/fixtures/jadx_sources/com/demo/net/Config.java
package com.demo.net;

public class Config {
    public static String buildUploadUrl(String host) {
        return "https://" + host + "/api/upload";
    }
}
```

```java
// /Users/penglai/Documents/Objects/APKHacker/tests/fixtures/jadx_sources/com/demo/entry/MainActivity.java
package com.demo.entry;

public class MainActivity {
    protected void onCreate(Object state) {
    }
}
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/domain/models/indexes.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClassIndexEntry:
    class_name: str
    package_name: str
    source_path: str
    method_count: int
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class MethodIndexEntry:
    class_name: str
    method_name: str
    parameter_types: tuple[str, ...]
    return_type: str
    is_constructor: bool
    overload_count: int
    source_path: str
    line_hint: int | None
    tags: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class MethodIndex:
    classes: tuple[ClassIndexEntry, ...]
    methods: tuple[MethodIndexEntry, ...]
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/domain/services/method_indexer.py
from __future__ import annotations

from pathlib import Path
import re

from apk_hacker.domain.models.indexes import ClassIndexEntry, MethodIndex, MethodIndexEntry


CLASS_RE = re.compile(r"package\s+([A-Za-z0-9_.]+);\s+.*?class\s+([A-Za-z0-9_]+)", re.DOTALL)
METHOD_RE = re.compile(r"(public|protected|private)\s+([A-Za-z0-9_$.<>]+)\s+([A-Za-z0-9_]+)\(([^)]*)\)")


class JavaMethodIndexer:
    def build(self, sources_root: Path) -> MethodIndex:
        classes: list[ClassIndexEntry] = []
        methods: list[MethodIndexEntry] = []

        for source_file in sources_root.rglob("*.java"):
            text = source_file.read_text(encoding="utf-8")
            match = CLASS_RE.search(text)
            if not match:
                continue
            package_name, class_name = match.groups()
            fqcn = f"{package_name}.{class_name}"

            file_methods: list[MethodIndexEntry] = []
            for method_match in METHOD_RE.finditer(text):
                _, return_type, method_name, raw_params = method_match.groups()
                params = tuple(
                    part.strip().split(" ")[0]
                    for part in raw_params.split(",")
                    if part.strip()
                )
                file_methods.append(
                    MethodIndexEntry(
                        class_name=fqcn,
                        method_name=method_name,
                        parameter_types=params,
                        return_type=return_type,
                        is_constructor=method_name == class_name,
                        overload_count=1,
                        source_path=str(source_file),
                        line_hint=text[: method_match.start()].count("\n") + 1,
                    )
                )

            classes.append(
                ClassIndexEntry(
                    class_name=fqcn,
                    package_name=package_name,
                    source_path=str(source_file),
                    method_count=len(file_methods),
                )
            )
            methods.extend(file_methods)

        return MethodIndex(classes=tuple(classes), methods=tuple(methods))
```

- [ ] **Step 4: Run the method-index test to verify it passes**

Run: `python -m pytest tests/domain/test_method_indexer.py -q`
Expected: PASS

- [ ] **Step 5: Commit the method indexer**

```bash
git add src/apk_hacker/domain/models/indexes.py src/apk_hacker/domain/services/method_indexer.py tests/fixtures/jadx_sources tests/domain/test_method_indexer.py
git commit -m "feat: add jadx method indexing"
```

### Task 6: Add Hook Models, Plugins, And Custom Scripts

**Files:**
- Create: `/src/apk_hacker/domain/models/hook_plan.py`
- Create: `/src/apk_hacker/application/plugins/contracts.py`
- Create: `/src/apk_hacker/application/plugins/builtin/method_hook.py`
- Create: `/src/apk_hacker/application/services/hook_plan_service.py`
- Create: `/src/apk_hacker/application/services/custom_script_service.py`
- Create: `/templates/generic/method_hook.js.j2`
- Test: `/tests/application/test_hook_plan_service.py`

- [ ] **Step 1: Write the failing Hook-plan test**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/application/test_hook_plan_service.py
from pathlib import Path

from apk_hacker.application.services.custom_script_service import CustomScriptService
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.models.indexes import MethodIndexEntry


def test_hook_plan_service_turns_method_selection_into_plan_item() -> None:
    method = MethodIndexEntry(
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        is_constructor=False,
        overload_count=1,
        source_path="tests/fixtures/jadx_sources/com/demo/net/Config.java",
        line_hint=4,
    )

    result = HookPlanService().plan_for_methods([method])
    assert len(result.items) == 1
    assert result.items[0].kind == "method_hook"
    assert result.items[0].target.class_name == "com.demo.net.Config"


def test_custom_script_service_discovers_local_frida_scripts(tmp_path: Path) -> None:
    script_path = tmp_path / "trace_login.js"
    script_path.write_text("send('trace');\n", encoding="utf-8")

    result = CustomScriptService(tmp_path).discover()
    assert [item.name for item in result] == ["trace_login"]
```

- [ ] **Step 2: Run the Hook-plan test to verify it fails**

Run: `python -m pytest tests/application/test_hook_plan_service.py -q`
Expected: FAIL because the Hook plan service does not exist

- [ ] **Step 3: Implement Hook plan models, the built-in method-hook plugin, and the template**

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/domain/models/hook_plan.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MethodHookTarget:
    target_id: str
    class_name: str
    method_name: str
    parameter_types: tuple[str, ...]
    return_type: str
    source_origin: str
    notes: str = ""


@dataclass(frozen=True)
class HookPlanItem:
    item_id: str
    kind: str
    enabled: bool
    inject_order: int
    target: MethodHookTarget | None
    render_context: dict[str, object]
    plugin_id: str | None = None


@dataclass(frozen=True)
class HookPlan:
    items: tuple[HookPlanItem, ...]
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/plugins/contracts.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlannedScript:
    plugin_id: str
    kind: str
    render_context: dict[str, object]


class HookStrategyPlugin:
    plugin_id: str

    def build(self, class_name: str, method_name: str, parameter_types: tuple[str, ...]) -> PlannedScript:
        raise NotImplementedError
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/plugins/builtin/method_hook.py
from __future__ import annotations

from apk_hacker.application.plugins.contracts import HookStrategyPlugin, PlannedScript


class MethodHookPlugin(HookStrategyPlugin):
    plugin_id = "builtin.method-hook"

    def build(self, class_name: str, method_name: str, parameter_types: tuple[str, ...]) -> PlannedScript:
        return PlannedScript(
            plugin_id=self.plugin_id,
            kind="method_hook",
            render_context={
                "className": class_name,
                "methodName": method_name,
                "paramTypes": list(parameter_types),
            },
        )
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/hook_plan_service.py
from __future__ import annotations

from uuid import uuid4

from apk_hacker.application.plugins.builtin.method_hook import MethodHookPlugin
from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanItem, MethodHookTarget


class HookPlanService:
    def __init__(self) -> None:
        self._method_hook = MethodHookPlugin()

    def plan_for_methods(self, methods: list) -> HookPlan:
        items: list[HookPlanItem] = []
        for inject_order, method in enumerate(methods, start=1):
            script = self._method_hook.build(method.class_name, method.method_name, method.parameter_types)
            target = MethodHookTarget(
                target_id=str(uuid4()),
                class_name=method.class_name,
                method_name=method.method_name,
                parameter_types=method.parameter_types,
                return_type=method.return_type,
                source_origin="method_index",
            )
            items.append(
                HookPlanItem(
                    item_id=str(uuid4()),
                    kind=script.kind,
                    enabled=True,
                    inject_order=inject_order,
                    target=target,
                    render_context=script.render_context,
                    plugin_id=script.plugin_id,
                )
            )
        return HookPlan(items=tuple(items))
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/custom_script_service.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from apk_hacker.domain.models.hook_plan import HookPlanItem


@dataclass(frozen=True)
class CustomScriptRecord:
    script_id: str
    name: str
    script_path: Path


class CustomScriptService:
    def __init__(self, scripts_root: Path) -> None:
        self._scripts_root = scripts_root

    def discover(self) -> list[CustomScriptRecord]:
        self._scripts_root.mkdir(parents=True, exist_ok=True)
        records: list[CustomScriptRecord] = []
        for script_path in sorted(self._scripts_root.glob("*.js")):
            records.append(
                CustomScriptRecord(
                    script_id=str(uuid4()),
                    name=script_path.stem,
                    script_path=script_path,
                )
            )
        return records

    def build_plan_item(self, record: CustomScriptRecord, inject_order: int) -> HookPlanItem:
        return HookPlanItem(
            item_id=str(uuid4()),
            kind="custom_script",
            enabled=True,
            inject_order=inject_order,
            target=None,
            render_context={"script_path": str(record.script_path)},
            plugin_id="custom.local-script",
        )
```

```javascript
// /Users/penglai/Documents/Objects/APKHacker/templates/generic/method_hook.js.j2
Java.perform(function() {
    var TargetClass = Java.use("{{ className }}");
    TargetClass["{{ methodName }}"].overloads.forEach(function(overload) {
        overload.implementation = function() {
            send(JSON.stringify({
                "event_type": "method_call",
                "class_name": "{{ className }}",
                "method_name": "{{ methodName }}"
            }));
            return overload.apply(this, arguments);
        };
    });
});
```

- [ ] **Step 4: Run the Hook-plan test to verify it passes**

Run: `python -m pytest tests/application/test_hook_plan_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit Hook planning**

```bash
git add src/apk_hacker/domain/models/hook_plan.py src/apk_hacker/application/plugins src/apk_hacker/application/services/hook_plan_service.py src/apk_hacker/application/services/custom_script_service.py templates/generic/method_hook.js.j2 tests/application/test_hook_plan_service.py
git commit -m "feat: add method-centered hook planning"
```

### Task 7: Implement Fake Execution And SQLite Storage

**Files:**
- Create: `/src/apk_hacker/domain/models/hook_event.py`
- Create: `/src/apk_hacker/infrastructure/execution/backend.py`
- Create: `/src/apk_hacker/infrastructure/execution/session.py`
- Create: `/src/apk_hacker/infrastructure/execution/fake_backend.py`
- Create: `/src/apk_hacker/infrastructure/persistence/hook_log_store.py`
- Test: `/tests/infrastructure/test_fake_backend.py`
- Test: `/tests/infrastructure/test_hook_log_store.py`

- [ ] **Step 1: Write the failing execution and storage tests**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/infrastructure/test_fake_backend.py
from apk_hacker.domain.models.hook_plan import HookPlan, HookPlanItem, MethodHookTarget
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend


def test_fake_backend_emits_hook_events() -> None:
    target = MethodHookTarget(
        target_id="target-1",
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        parameter_types=("String",),
        return_type="String",
        source_origin="method_index",
    )
    plan = HookPlan(
        items=(
            HookPlanItem(
                item_id="item-1",
                kind="method_hook",
                enabled=True,
                inject_order=1,
                target=target,
                render_context={},
                plugin_id="builtin.method-hook",
            ),
        )
    )

    events = FakeExecutionBackend().execute("job-1", plan)
    assert events[0].class_name == "com.demo.net.Config"
    assert events[0].method_name == "buildUploadUrl"
```

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/infrastructure/test_hook_log_store.py
from pathlib import Path

from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


def test_hook_log_store_inserts_and_reads_events(tmp_path: Path) -> None:
    store = HookLogStore(tmp_path / "hooks.sqlite3")
    event = HookEvent(
        timestamp="2026-04-05T00:00:00Z",
        job_id="job-1",
        event_type="method_call",
        source="fake",
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        arguments=["demo-c2.example"],
        return_value="https://demo-c2.example/api/upload",
        stacktrace="demo stack",
        raw_payload={"ok": True},
    )
    store.insert(event)
    rows = store.list_for_job("job-1")
    assert len(rows) == 1
    assert rows[0].event_type == "method_call"
```

- [ ] **Step 2: Run the execution and storage tests to verify they fail**

Run: `python -m pytest tests/infrastructure/test_fake_backend.py tests/infrastructure/test_hook_log_store.py -q`
Expected: FAIL because execution and storage modules do not exist

- [ ] **Step 3: Implement the event model, fake backend, and SQLite store**

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/domain/models/hook_event.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HookEvent:
    timestamp: str
    job_id: str
    event_type: str
    source: str
    class_name: str
    method_name: str
    arguments: list[str]
    return_value: str | None
    stacktrace: str
    raw_payload: dict[str, object]
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/infrastructure/execution/fake_backend.py
from __future__ import annotations

from datetime import datetime, timezone

from apk_hacker.domain.models.hook_event import HookEvent


class FakeExecutionBackend:
    def execute(self, job_id: str, plan) -> list[HookEvent]:
        events: list[HookEvent] = []
        for item in plan.items:
            if not item.enabled or item.target is None:
                continue
            events.append(
                HookEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    job_id=job_id,
                    event_type="method_call",
                    source="fake",
                    class_name=item.target.class_name,
                    method_name=item.target.method_name,
                    arguments=[str(v) for v in item.target.parameter_types],
                    return_value="fake-return",
                    stacktrace=f"{item.target.class_name}.{item.target.method_name}:1",
                    raw_payload={"plugin_id": item.plugin_id or ""},
                )
            )
        return events
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/infrastructure/persistence/hook_log_store.py
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from apk_hacker.domain.models.hook_event import HookEvent


class HookLogStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hook_events (
                    timestamp TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    class_name TEXT NOT NULL,
                    method_name TEXT NOT NULL,
                    arguments TEXT NOT NULL,
                    return_value TEXT,
                    stacktrace TEXT NOT NULL,
                    raw_payload TEXT NOT NULL
                )
                """
            )

    def insert(self, event: HookEvent) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO hook_events (
                    timestamp, job_id, event_type, source, class_name, method_name,
                    arguments, return_value, stacktrace, raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.timestamp,
                    event.job_id,
                    event.event_type,
                    event.source,
                    event.class_name,
                    event.method_name,
                    json.dumps(event.arguments),
                    event.return_value,
                    event.stacktrace,
                    json.dumps(event.raw_payload),
                ),
            )

    def list_for_job(self, job_id: str) -> list[HookEvent]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT timestamp, job_id, event_type, source, class_name, method_name,
                       arguments, return_value, stacktrace, raw_payload
                FROM hook_events
                WHERE job_id = ?
                ORDER BY timestamp ASC
                """,
                (job_id,),
            ).fetchall()
        return [
            HookEvent(
                timestamp=row[0],
                job_id=row[1],
                event_type=row[2],
                source=row[3],
                class_name=row[4],
                method_name=row[5],
                arguments=json.loads(row[6]),
                return_value=row[7],
                stacktrace=row[8],
                raw_payload=json.loads(row[9]),
            )
            for row in rows
        ]
```

- [ ] **Step 4: Run the execution and storage tests to verify they pass**

Run: `python -m pytest tests/infrastructure/test_fake_backend.py tests/infrastructure/test_hook_log_store.py -q`
Expected: PASS

- [ ] **Step 5: Commit fake execution and storage**

```bash
git add src/apk_hacker/domain/models/hook_event.py src/apk_hacker/infrastructure/execution src/apk_hacker/infrastructure/persistence/hook_log_store.py tests/infrastructure/test_fake_backend.py tests/infrastructure/test_hook_log_store.py
git commit -m "feat: add fake execution and hook storage"
```

### Task 8: Orchestrate Jobs And Support Local JADX Launching

**Files:**
- Create: `/src/apk_hacker/domain/models/job.py`
- Create: `/src/apk_hacker/application/dto/requests.py`
- Create: `/src/apk_hacker/application/dto/results.py`
- Create: `/src/apk_hacker/application/services/job_service.py`
- Create: `/src/apk_hacker/infrastructure/integrations/jadx_launcher.py`
- Test: `/tests/application/test_job_service.py`

- [ ] **Step 1: Write the failing job-service test**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/application/test_job_service.py
from pathlib import Path

from apk_hacker.application.services.job_service import JobService


def test_job_service_creates_job_record() -> None:
    service = JobService()
    job = service.create_job(Path("/samples/demo.apk"))
    assert job.status == "queued"
    assert job.input_target == "/samples/demo.apk"
```

- [ ] **Step 2: Run the job-service test to verify it fails**

Run: `python -m pytest tests/application/test_job_service.py -q`
Expected: FAIL because the job service does not exist

- [ ] **Step 3: Implement the job model and the JADX launcher integration**

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/domain/models/job.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class AnalysisJob:
    job_id: str
    status: str
    input_target: str
    created_at: str
    updated_at: str
    artifacts: dict[str, str] = field(default_factory=dict)
    summary: dict[str, object] = field(default_factory=dict)
    error: str | None = None

    @classmethod
    def queued(cls, input_target: str) -> "AnalysisJob":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            job_id=str(uuid4()),
            status="queued",
            input_target=input_target,
            created_at=now,
            updated_at=now,
        )
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/job_service.py
from __future__ import annotations

from pathlib import Path

from apk_hacker.domain.models.job import AnalysisJob


class JobService:
    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}

    def create_job(self, input_target: Path) -> AnalysisJob:
        job = AnalysisJob.queued(str(input_target))
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> AnalysisJob:
        return self._jobs[job_id]
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/infrastructure/integrations/jadx_launcher.py
from __future__ import annotations

from pathlib import Path
import subprocess


def open_in_jadx(jadx_gui_path: str, target_path: Path) -> subprocess.Popen:
    return subprocess.Popen([jadx_gui_path, str(target_path)])
```

- [ ] **Step 4: Run the job-service test to verify it passes**

Run: `python -m pytest tests/application/test_job_service.py -q`
Expected: PASS

- [ ] **Step 5: Commit orchestration primitives**

```bash
git add src/apk_hacker/domain/models/job.py src/apk_hacker/application/services/job_service.py src/apk_hacker/infrastructure/integrations/jadx_launcher.py tests/application/test_job_service.py
git commit -m "feat: add job orchestration primitives"
```

### Task 9: Build The PyQt6 Workbench Shell

**Files:**
- Create: `/src/apk_hacker/interfaces/gui_pyqt/main.py`
- Create: `/src/apk_hacker/interfaces/gui_pyqt/main_window.py`
- Create: `/src/apk_hacker/interfaces/gui_pyqt/viewmodels.py`
- Create: `/src/apk_hacker/interfaces/gui_pyqt/widgets/task_center.py`
- Create: `/src/apk_hacker/interfaces/gui_pyqt/widgets/static_summary.py`
- Create: `/src/apk_hacker/interfaces/gui_pyqt/widgets/method_index.py`
- Create: `/src/apk_hacker/interfaces/gui_pyqt/widgets/script_plan.py`
- Create: `/src/apk_hacker/interfaces/gui_pyqt/widgets/custom_scripts.py`
- Create: `/src/apk_hacker/interfaces/gui_pyqt/widgets/execution_logs.py`
- Create: `/src/apk_hacker/interfaces/gui_pyqt/widgets/results_summary.py`
- Test: `/tests/interfaces/test_main_window_smoke.py`

- [ ] **Step 1: Write the failing GUI smoke test**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/interfaces/test_main_window_smoke.py
from apk_hacker.interfaces.gui_pyqt.main_window import MainWindow


def test_main_window_has_expected_navigation(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    labels = [window.nav_list.item(i).text() for i in range(window.nav_list.count())]
    assert labels == [
        "Task Center",
        "Static Summary",
        "Method Index",
        "Hook Assistant",
        "Script Plan",
        "Custom Frida Scripts",
        "Execution & Logs",
        "Results Summary",
    ]
    assert window.open_jadx_action.text() == "Open in JADX"
```

- [ ] **Step 2: Run the GUI smoke test to verify it fails**

Run: `python -m pytest tests/interfaces/test_main_window_smoke.py -q`
Expected: FAIL because the GUI modules do not exist

- [ ] **Step 3: Create the thin PyQt6 workbench shell**

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/gui_pyqt/main_window.py
from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QListWidget, QMainWindow, QSplitter, QStackedWidget, QWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("APKHacker")
        self.resize(1400, 900)

        self.open_jadx_action = QAction("Open in JADX", self)
        self.menuBar().addAction(self.open_jadx_action)

        self.nav_list = QListWidget()
        self.nav_list.addItems(
            [
                "Task Center",
                "Static Summary",
                "Method Index",
                "Hook Assistant",
                "Script Plan",
                "Custom Frida Scripts",
                "Execution & Logs",
                "Results Summary",
            ]
        )

        self.content_stack = QStackedWidget()
        for _ in range(self.nav_list.count()):
            self.content_stack.addWidget(QWidget())

        splitter = QSplitter()
        splitter.addWidget(self.nav_list)
        splitter.addWidget(self.content_stack)
        self.setCentralWidget(splitter)

        self.nav_list.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/interfaces/gui_pyqt/main.py
from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from apk_hacker.interfaces.gui_pyqt.main_window import MainWindow


def run() -> int:
    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
```

- [ ] **Step 4: Run the GUI smoke test to verify it passes**

Run: `python -m pytest tests/interfaces/test_main_window_smoke.py -q`
Expected: PASS

- [ ] **Step 5: Commit the GUI shell**

```bash
git add src/apk_hacker/interfaces/gui_pyqt tests/interfaces/test_main_window_smoke.py
git commit -m "feat: add pyqt workstation shell"
```

### Task 10: Close The MVP Loop With An Integration Test

**Files:**
- Modify: `/src/apk_hacker/application/services/job_service.py`
- Create: `/tests/application/test_mvp_flow.py`
- Modify: `/docs/superpowers/specs/2026-04-05-apk-hacker-mvp-design.md`

- [ ] **Step 1: Write the failing end-to-end MVP integration test**

```python
# /Users/penglai/Documents/Objects/APKHacker/tests/application/test_mvp_flow.py
from pathlib import Path
import json

from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.services.method_indexer import JavaMethodIndexer
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


def test_mvp_flow_static_to_fake_dynamic(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/static_outputs")
    analysis = json.loads((fixture_root / "sample_analysis.json").read_text(encoding="utf-8"))
    callback = json.loads((fixture_root / "sample_callback-config.json").read_text(encoding="utf-8"))

    static_inputs = StaticAdapter().adapt(
        sample_path=Path("/samples/demo.apk"),
        analysis_report=analysis,
        callback_config=callback,
        artifact_paths={"analysis_json": "cache/demo/analysis.json"},
    )
    index = JavaMethodIndexer().build(Path("tests/fixtures/jadx_sources"))
    selected = [method for method in index.methods if method.method_name == "buildUploadUrl"]
    plan = HookPlanService().plan_for_methods(selected)
    events = FakeExecutionBackend().execute("job-1", plan)

    store = HookLogStore(tmp_path / "hooks.sqlite3")
    for event in events:
        store.insert(event)

    rows = store.list_for_job("job-1")
    assert static_inputs.package_name == "com.demo.shell"
    assert len(rows) == 1
    assert rows[0].method_name == "buildUploadUrl"
```

- [ ] **Step 2: Run the MVP integration test to verify it fails**

Run: `python -m pytest tests/application/test_mvp_flow.py -q`
Expected: FAIL because one or more cross-module imports or contracts are incomplete

- [ ] **Step 3: Fill any missing imports, wire the remaining application seams, and link the plan from the spec**

```markdown
# /Users/penglai/Documents/Objects/APKHacker/docs/superpowers/specs/2026-04-05-apk-hacker-mvp-design.md
Implementation plan: `/Users/penglai/Documents/Objects/APKHacker/docs/superpowers/plans/2026-04-05-apk-hacker-mvp-plan.md`
```

```python
# /Users/penglai/Documents/Objects/APKHacker/src/apk_hacker/application/services/job_service.py
from __future__ import annotations

from pathlib import Path

from apk_hacker.application.services.static_adapter import StaticAdapter
from apk_hacker.application.services.hook_plan_service import HookPlanService
from apk_hacker.domain.models.job import AnalysisJob
from apk_hacker.domain.services.method_indexer import JavaMethodIndexer
from apk_hacker.infrastructure.execution.fake_backend import FakeExecutionBackend
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


class JobService:
    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}

    def create_job(self, input_target: Path) -> AnalysisJob:
        job = AnalysisJob.queued(str(input_target))
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> AnalysisJob:
        return self._jobs[job_id]

    def run_fake_flow(
        self,
        analysis_report: dict,
        callback_config: dict,
        jadx_sources_dir: Path,
        db_path: Path,
    ) -> tuple:
        static_inputs = StaticAdapter().adapt(
            sample_path=Path("/samples/demo.apk"),
            analysis_report=analysis_report,
            callback_config=callback_config,
            artifact_paths={"analysis_json": "cache/demo/analysis.json"},
        )
        index = JavaMethodIndexer().build(jadx_sources_dir)
        selected = [method for method in index.methods if method.method_name == "buildUploadUrl"]
        plan = HookPlanService().plan_for_methods(selected)
        events = FakeExecutionBackend().execute("job-1", plan)
        store = HookLogStore(db_path)
        for event in events:
            store.insert(event)
        return static_inputs, plan, store.list_for_job("job-1")
```

- [ ] **Step 4: Run the focused test suite to verify the MVP loop passes**

Run: `python -m pytest tests/static_engine tests/domain tests/application tests/infrastructure tests/interfaces -q`
Expected: PASS

- [ ] **Step 5: Commit the MVP plan baseline**

```bash
git add docs/superpowers/specs/2026-04-05-apk-hacker-mvp-design.md docs/superpowers/plans/2026-04-05-apk-hacker-mvp-plan.md src tests
git commit -m "docs: add apkhacker mvp implementation plan"
```

## Self-Review

### Spec Coverage

- Static-engine migration: covered in Tasks 2 and 3
- Stable internal models: covered in Tasks 4, 5, 7, and 8
- Method-centered Hook workflow: covered in Tasks 5 and 10
- Custom Frida scripts: introduced in Task 6, with GUI integration reserved for the widgets created in Task 9
- Fake execution backend and SQLite: covered in Task 7
- PyQt6 workstation: covered in Task 9
- Local JADX open action: covered in Task 8

### Placeholder Scan

- No unresolved placeholder markers remain
- Each task contains exact file paths, commands, and code or shell blocks

### Type Consistency

- `StaticInputs`, `MethodIndexEntry`, `MethodHookTarget`, `HookPlanItem`, `HookEvent`, and `AnalysisJob` are introduced before later tasks consume them
- Job orchestration references the same normalized adapter and fake backend contracts used in earlier tasks

## Execution Handoff

Plan complete and saved to `/Users/penglai/Documents/Objects/APKHacker/docs/superpowers/plans/2026-04-05-apk-hacker-mvp-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
