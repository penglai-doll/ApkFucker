# APKHacker 项目结构整理

> 本文件用于固定当前仓库主线，避免后续继续被旧模型生成的多套架构带偏。

## 当前主线

APKHacker 当前唯一继续演进的产品主线是：

```text
Tauri + React 前端
        ↓
FastAPI 接口层
        ↓
application 用例编排层
        ↓
domain / infrastructure / static_engine
```

不要再新增独立的顶层 `core/`、`rules/`、`ai/`、`report/`、`sandbox/`、`orchestrator.py` 作为第二套主架构。动态分析能力应收敛进现有 Python 包结构。

## 顶层目录职责

```text
frontend/      React 工作台前端，当前桌面 UI 的主要演进位置
src-tauri/     Tauri 桌面壳与 sidecar 启动逻辑
src/           Python 后端包源码
templates/     Frida/Jinja2 脚本模板
tests/         Python 测试
docs/          设计、规划与项目整理文档
custom-scripts/ 本地用户自定义脚本目录；默认不提交内容
user_data/     本地用户数据目录；默认不提交内容
```

## Python 包结构

```text
src/apk_hacker/
  domain/          稳定业务模型与纯领域规则
  application/     工作台用例编排、状态迁移、artifact 生命周期
  infrastructure/  工具接入、执行后端、持久化、模板渲染
  interfaces/      FastAPI / CLI / 旧 GUI 兼容入口
  static_engine/   legacy 静态分析管线兼容入口
  tools/           可独立运行的诊断/后端辅助命令
```

## 当前需要继续收敛的热点

- `src/apk_hacker/application/services/workspace_runtime_service.py`
  - 已经从更大的服务降到约 700+ 行，但仍是运行时 Facade 热点。
  - 后续应继续把 Hook 计划、执行、流量、报告等职责委托给专门服务。
- `src/apk_hacker/interfaces/api_fastapi/routes_workspace.py`
  - API presenter/assembler 逻辑仍偏多，后续可拆到 schema/mapper 层。
- `frontend/src/pages/CaseWorkspacePage.tsx`
  - 单页承担工作台大量 UI 状态，后续可按面板继续下沉。

## 生成物与本地状态

以下内容属于本地运行/构建产物，已经被 `.gitignore` 忽略，不应提交：

```text
.venv/
node_modules/
dist/
.pytest_cache/
__pycache__/
cache/
workspaces/
.apkhacker/
.claude/
.superpowers/
*.pyc
.DS_Store
```

其中：

- `.venv/`、`node_modules/` 是开发依赖目录，通常保留在本地。
- `workspaces/` 和 `cache/` 可能包含真实样本、分析报告和本地工作台状态，清理前必须单独确认。
- `dist/` 可随时由 `npm run build:web` 重新生成。

## 后续整理规则

1. 新业务模型优先放入 `src/apk_hacker/domain/models/`。
2. 新用例编排优先放入 `src/apk_hacker/application/services/`。
3. ADB / Frida / mitmproxy / SQLite / JADX 等具体工具实现放入 `src/apk_hacker/infrastructure/` 或 `src/apk_hacker/tools/`。
4. FastAPI 路由只做输入输出转换，不承载核心业务逻辑。
5. 前端只跟随稳定 API 契约演进，不先行发散出另一套业务状态模型。
6. 文档规划统一放在 `docs/` 下，根目录只保留 README、构建配置和许可证等入口文件。
