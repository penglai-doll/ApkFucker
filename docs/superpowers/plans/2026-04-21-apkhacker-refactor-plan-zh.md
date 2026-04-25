# APKHacker 重构规划

> 版本：2026-04-21
> 基准：本规划基于当前本地代码仓库实际结构与实现状态整理，不再沿用“从零搭新目录”的思路。

## 一、先说结论

当前项目已经不是“脚本堆”，而是一个已经形成主链路的工作台：

`WorkspaceService -> JobService -> StaticAnalyzer -> StaticAdapter -> MethodIndexer -> HookPlanService -> WorkspaceRuntimeService -> FastAPI -> React/Tauri`

这意味着本次重构不应该推倒重来，而应该做三件事：

1. 以现有分层为基础收敛边界，而不是引入第二套顶层架构。
2. 先把中间数据和运行时状态模型做稳，再拆分热点服务。
3. 在不破坏当前工作台闭环的前提下，把静态、Hook、执行、流量逐步升级为真正可扩展的能力层。

## 二、当前代码库现状

### 1. 已经稳定存在的骨架

- 后端主结构已经是 `src/apk_hacker/domain`、`application`、`infrastructure`、`interfaces`、`static_engine`。
- 前端主线已经是 `frontend + Tauri + FastAPI`，不是 PyQt 主导项目。
- 工作区模型已经存在：
  - `workspace.json`
  - `workspace-runtime.json`
  - `executions/run-*`
  - `reports/*.md`
  - `evidence/traffic/traffic-capture.json`
- Hook 规划链路已经存在：
  - `domain/services/method_indexer.py`
  - `domain/services/offline_rule_engine.py`
  - `domain/services/hook_advisor.py`
  - `application/services/hook_plan_service.py`
- 动态执行链路已经存在：
  - `infrastructure/execution/fake_backend.py`
  - `infrastructure/execution/real_backend.py`
  - `tools/frida_*`
  - `tools/adb_probe_backend.py`
- 流量导入与 live capture 第一版已经存在：
  - `application/services/traffic_capture_service.py`
  - `application/services/live_capture_runtime.py`
  - `interfaces/api_fastapi/routes_traffic.py`

### 2. 当前最重要的热点文件

- `application/services/workspace_runtime_service.py`
  - 约 1111 行，承担了 Hook 计划、执行状态、流量导入、报告导出、运行时持久化、执行校验等多类职责。
- `application/services/workspace_inspection_service.py`
  - 约 440 行，承担工作区加载、方法搜索、推荐、JADX 打开、缓存等读侧职责。
- `application/services/workspace_runtime_state.py`
  - 约 406 行，已经在承担一个“持久化格式 + 兼容渲染计划”的双重角色。
- `interfaces/api_fastapi/routes_workspace.py`
  - 约 510 行，存在明显的 presenter/assembler 逻辑堆积。

### 3. 当前设计里真正合理的部分

- `static_engine/analyzer.py` 作为 legacy 静态分析入口包装器，这条链路短期应保留。
- `application/services/static_adapter.py` 已经把旧 `analysis.json` 转成工作台可用的 `StaticInputs`。
- `JobService` 已经承担“导入样本 -> 跑静态 -> 建方法索引”的编排责任。
- `HookPlanService + ScriptRenderer` 已经形成“选源 -> 渲染脚本”的可复用链路。
- `HookLogStore` 已经把动态事件存进 SQLite，具备继续演进为统一事件存储的基础。
- 前端 `CaseWorkspacePage` 已经围绕静态摘要、Hook 工作台、执行控制台、流量证据、证据中心、报告导出形成单一产品面。

### 4. 当前真正限制扩展的地方

- 静态分析仍主要依赖 legacy 脚本输出，缺少标准化 artifact schema。
- `workspace_runtime_service.py` 过度集中，未来会成为扩展阻塞点。
- `HookPlanItem`、`HookEvent`、`TrafficCapture` 模型粒度偏粗，不足以支撑证据链关联。
- “真实设备”仍然是命令型 backend，而不是统一 `DeviceBackend` 抽象。
- 流量目前以 HAR 摘要和 preview 为主，还不是一等证据存储。
- 当前目录里同时存在“现有分层结构”和“旧规划里的 core/rules/templates/ai 设想”，需要收敛到单一路线。

## 三、本次重构原则

### 原则 1：保留当前主分层，不再引入第二套顶层目录

本项目后续统一使用：

```text
src/apk_hacker/
  domain/
  application/
  infrastructure/
  interfaces/
  static_engine/
```

不再另起一套仓库级 `core/ rules/ ai/ report/ sandbox/ orchestrator.py` 作为主线。

### 原则 2：先 schema，后功能

先把以下四类中间数据做稳定：

- `StaticResult / ArtifactManifest`
- `HookPlan / HookTemplateDescriptor`
- `DynamicEvent`
- `TrafficFlow / TrafficCapture`

之后再继续扩大 Frida、抓包、AI、Flutter 分析能力。

### 原则 3：迁移优先，不做一次性替换

- legacy 静态分析脚本继续保留。
- 当前 FastAPI + React 工作台继续保留。
- 当前 Hook 模板继续保留。
- 当前 fake/real backend 协议继续保留。

新架构优先以 adapter、normalizer、facade 的方式落地。

### 原则 4：前端不先行重构

在后端模型、artifact 结构和运行时状态没稳定之前，不做大规模 UI 改版。前端只跟随后端契约做收敛式升级。

## 四、目标架构

## 1. 目录演进目标

```text
src/apk_hacker/
  domain/
    models/
      artifact.py
      finding.py
      evidence.py
      static_result.py
      hook_plan.py
      hook_event.py
      traffic.py
      device.py
      workspace.py
      execution.py
    services/
      method_indexer.py
      hook_advisor.py
      offline_rule_engine.py
      template_registry.py
      traffic_correlator.py

  application/
    services/
      job_service.py
      static_adapter.py
      static_result_normalizer.py
      workspace_service.py
      workspace_inspection_service.py
      workspace_state_service.py
      workspace_hook_plan_service.py
      workspace_execution_service.py
      workspace_traffic_service.py
      workspace_report_service.py
      workspace_runtime_service.py   # 过渡期 facade，最终变薄

  infrastructure/
    static/
      legacy_static_gateway.py
      manifest_reader.py
      resource_inventory.py
      secret_scanner.py
      jadx_source_indexer.py
      framework_detector.py
      packer_detector.py
    execution/
      backend.py
      fake_backend.py
      real_backend.py
      device_backend.py
      device_real.py
      frida_runtime.py
      traffic_runtime.py
      session.py
    persistence/
      hook_log_store.py
      traffic_flow_store.py
      artifact_manifest_store.py
      workspace_state_store.py
    templates/
      script_renderer.py

  interfaces/
    api_fastapi/
    cli/
    gui_pyqt/   # 冻结，仅兼容

  static_engine/
    analyzer.py
    tooling/
    legacy/
```

### 2. 各层职责

#### `static_engine`

- 继续作为 legacy 静态分析的兼容入口。
- 职责是“调用旧脚本并拿回产物”，不再承担长期的数据模型职责。

#### `domain`

- 只定义稳定业务模型和纯规则逻辑。
- 不直接依赖 FastAPI、文件路径组织、具体工具命令。

#### `application`

- 负责用例编排、状态迁移、artifact 生命周期。
- 是未来 API 和 CLI 共用的主编排层。

#### `infrastructure`

- 负责具体工具接入：
  - legacy 静态脚本
  - JADX/APKTool
  - ADB/Frida
  - mitmproxy
  - SQLite

#### `interfaces`

- 只负责把 `application` 层结果映射成 API/CLI/UI 可消费结构。

## 五、统一数据模型目标

### 1. 静态结果标准化

当前的 `StaticInputs` 仍然保留，但新增标准化 artifact：

```python
ArtifactManifest:
  schema_version: str
  case_id: str
  sample_path: str
  artifacts: list[ArtifactRef]

ArtifactRef:
  artifact_id: str
  kind: str
  path: str
  producer: str
  created_at: str
  metadata: dict

StaticResult:
  package_name: str
  technical_tags: tuple[str, ...]
  dangerous_permissions: tuple[str, ...]
  callback_endpoints: tuple[str, ...]
  callback_clues: tuple[str, ...]
  crypto_signals: tuple[str, ...]
  packer_hints: tuple[str, ...]
  limitations: tuple[str, ...]
  findings: tuple[Finding, ...]
  evidence: tuple[Evidence, ...]
```

### 2. 证据与发现

```python
Evidence:
  evidence_id: str
  source_type: str    # manifest / resource / source / traffic / hook_event / runtime
  path: str | None
  line: int | None
  excerpt: str | None
  tags: tuple[str, ...]
  metadata: dict[str, object]

Finding:
  finding_id: str
  category: str       # network / crypto / permission / secret / packer / framework
  severity: str       # info / low / medium / high
  title: str
  summary: str
  confidence: float
  evidence_ids: tuple[str, ...]
  tags: tuple[str, ...]
```

### 3. Hook 计划

保留当前 `HookPlanSource / HookPlanItem / HookPlan`，但扩展为：

```python
HookPlanItem:
  item_id: str
  kind: str                 # method_hook / template_hook / custom_script
  source_kind: str          # selected_method / recommended / custom_script / ai / framework_plugin
  enabled: bool
  inject_order: int
  target: MethodHookTarget | None
  template_id: str | None
  plugin_id: str | None
  evidence_ids: tuple[str, ...]
  tags: tuple[str, ...]
  render_context: dict[str, object]
```

### 4. 动态事件

当前 `HookEvent` 继续保留，但应演进成统一 `DynamicEvent` 语义：

```python
DynamicEvent:
  timestamp: str
  run_id: str
  event_type: str
  source: str
  class_name: str
  method_name: str
  arguments: tuple[str, ...]
  return_value: str | None
  stacktrace: str
  raw_payload: dict[str, object]
  tags: tuple[str, ...]
  evidence_ids: tuple[str, ...]
```

### 5. 流量模型

当前 `TrafficCapture` 更偏展示摘要，需要补齐“存储层模型”：

```python
TrafficFlow:
  flow_id: str
  capture_id: str
  method: str
  url: str
  host: str
  status_code: int | None
  mime_type: str | None
  request_preview: str
  response_preview: str
  matched_indicators: tuple[str, ...]
  suspicious: bool
  evidence_ids: tuple[str, ...]
```

## 六、工作区产物布局

当前工作区已经在使用 `workspace.json`、`workspace-runtime.json`、`executions/`、`reports/`、`evidence/traffic/`。重构后保持兼容，并逐步演进为：

```text
workspaces/<case_id>/
  workspace.json
  workspace-runtime.json

  sample/
    original.apk

  static/
    legacy/
      analysis.json
      callback-config.json
      noise-log.json
      report.md
      report.docx
    normalized/
      artifact-manifest.json
      static-result.v1.json
      findings.jsonl
      evidence.jsonl
      method-index.jsonl
      class-index.jsonl
    jadx/
      sources/
      project/

  executions/
    run-1/
      plan.json
      scripts/
      stdout.log
      stderr.log
      hook-events.sqlite3

  evidence/
    traffic/
      traffic-capture.json
      flows.sqlite3
      live/
        <session>.har
        <session>.preview.ndjson

  reports/
    <case_id>-report.md
```

### 兼容策略

- Phase 1 之前，现有 `workspace-runtime.json`、`traffic-capture.json` 继续保留。
- 新结构先以“新增 normalized artifact”的方式写入。
- 不要求前端一次切到新目录，只要求 API 能优先消费新结构。

## 七、分阶段实施路线

## Phase 0：架构收敛与冻结边界

### 目标

- 停止继续使用“第二套顶层架构”描述项目。
- 明确本项目后续只在现有分层结构中演进。

### 任务

- 更新项目文档，使重构目标与当前代码结构一致。
- 明确 `static_engine` 是 legacy 入口，不是未来所有静态能力的长期落点。
- 明确 `workspace_runtime_service.py` 是当前最大拆分热点。

### 完成标准

- 文档和 README 不再同时出现相互冲突的目录主线。

## Phase 1：先做 Schema 和 Artifact Normalization

### 目标

在不破坏当前工作台导入流程的前提下，引入标准化静态产物。

### 重点文件

- 新增：`domain/models/artifact.py`
- 新增：`domain/models/finding.py`
- 新增：`domain/models/evidence.py`
- 新增：`domain/models/static_result.py`
- 新增：`application/services/static_result_normalizer.py`
- 调整：`application/services/job_service.py`
- 调整：`application/services/static_adapter.py`

### 任务

- 让 `JobService.load_static_workspace_bundle()` 在 legacy 输出基础上再写一份 normalized artifacts。
- 保留 `StaticInputs` 作为工作台最小输入，同时引入 `StaticResult` 作为后续演进的真实基础。
- 产出 `artifact-manifest.json`、`static-result.v1.json`、`method-index.jsonl`。

### 完成标准

- 导入 case 后，不仅有 `StaticInputs`，也有稳定 artifact 清单。
- 现有测试不回归。

## Phase 2：拆分 Runtime 编排热点

### 目标

把 `workspace_runtime_service.py` 从“大一统服务”拆成多个明确职责的服务。

### 拆分方向

- `workspace_state_service.py`
  - 负责 `workspace-runtime.json` 的加载与保存。
- `workspace_hook_plan_service.py`
  - 负责 Hook 源维护、计划增删改、重渲染。
- `workspace_execution_service.py`
  - 负责 preflight、执行、运行历史、日志落盘。
- `workspace_traffic_service.py`
  - 负责 HAR 导入、live capture 状态、流量摘要持久化。
- `workspace_report_service.py`
  - 负责报告导出。
- `workspace_runtime_service.py`
  - 过渡期保留为 facade，统一协调上述服务。

### 重点文件

- 调整：`application/services/workspace_runtime_service.py`
- 新增：上述 4~5 个分拆服务
- 调整：`application/services/workspace_runtime_state.py`

### 完成标准

- `workspace_runtime_service.py` 降为协调层。
- 状态存储、执行编排、流量持久化不再耦合在一个文件中。

## Phase 3：统一 Hook Plan 与模板注册表

### 目标

让“点方法 Hook”“规则推荐 Hook”“自定义脚本 Hook”统一进入同一计划模型。

### 重点文件

- 调整：`domain/models/hook_plan.py`
- 新增：`domain/services/template_registry.py`
- 调整：`application/services/hook_plan_service.py`
- 调整：`infrastructure/templates/script_renderer.py`
- 保留：`templates/ssl/*`、`templates/crypto/*`、`templates/anti_detection/*`、`templates/generic/*`

### 任务

- 为模板增加 metadata 描述。
- 让计划项显式带上 `template_id / source_kind / evidence_ids / tags`。
- 渲染脚本时统一结构化事件输出约定。

### 完成标准

- Hook 计划不再只是“渲染后的脚本文本列表”，而是明确的可解释计划对象。

## Phase 4：把动态执行升级成可扩展设备模型

### 目标

保留当前命令型 `RealExecutionBackend` 能力，同时引入真正的设备抽象。

### 重点文件

- 新增：`domain/models/device.py`
- 新增：`infrastructure/execution/device_backend.py`
- 新增：`infrastructure/execution/device_real.py`
- 调整：`application/services/execution_runtime.py`
- 调整：`infrastructure/execution/real_backend.py`
- 保留：`tools/adb_probe_backend.py`、`tools/frida_*`

### 目标接口

```python
class DeviceBackend:
    def connect(self) -> bool: ...
    def install_apk(self, path: str) -> bool: ...
    def start_app(self, package: str) -> bool: ...
    def stop_app(self, package: str) -> bool: ...
    def get_arch(self) -> str: ...
    def is_rooted(self) -> bool: ...
    def push_frida_server(self, binary: str) -> bool: ...
```

### 迁移策略

- 当前 preset runner 仍然保留，用于继续驱动 `real_adb_probe`、`real_frida_probe`、`real_frida_session`。
- 新 `DeviceBackend` 优先作为这些 runner 的统一适配层，而不是一开始替换所有工具脚本。

### 完成标准

- 当前执行模式继续可用。
- 设备侧逻辑开始从“命令枚举”收敛到“能力接口”。

## Phase 5：让流量从“摘要”变成“一等证据”

### 目标

当前 `TrafficCaptureService` 以 HAR 摘要为主，需要补齐持久化和关联能力。

### 重点文件

- 新增：`infrastructure/persistence/traffic_flow_store.py`
- 调整：`application/services/traffic_capture_service.py`
- 调整：`application/services/live_capture_runtime.py`
- 调整：`application/services/workspace_traffic_service.py`
- 调整：`interfaces/api_fastapi/routes_traffic.py`

### 任务

- HAR 导入后同时写入 `flows.sqlite3`。
- live preview 继续保留 NDJSON，但最终以 SQLite/结构化 flow 为主。
- 增加“命中 callback clue”“疑似加密”“与 Hook 事件相关”的关联字段。

### 完成标准

- 流量不仅能展示，还能被证据中心和报告稳定复用。

## Phase 6：静态分析模块化，但不拆 legacy 主链

### 目标

逐步把 legacy 静态脚本中的可独立能力抽出来。

### 重点文件

- 新增：`infrastructure/static/legacy_static_gateway.py`
- 新增：`infrastructure/static/manifest_reader.py`
- 新增：`infrastructure/static/resource_inventory.py`
- 新增：`infrastructure/static/secret_scanner.py`
- 新增：`infrastructure/static/framework_detector.py`
- 新增：`infrastructure/static/packer_detector.py`
- 调整：`static_engine/analyzer.py`

### 任务

- 先让 legacy 输出继续成为事实来源。
- 新模块逐步补充 `Finding/Evidence` 和独立 artifact。
- `method_indexer.py` 先继续服务 Java/JADX，后续再扩展 smali/native。

### 完成标准

- 新静态能力以独立 artifact 增量加入，而不是继续向 legacy 报告文本里堆字段。

## Phase 7：AI 与框架插件放到稳定数据层之后

### 目标

AI、Flutter、React Native、uni-app、壳识别增强等能力，在 schema 稳定后再加入。

### 原则

- 不在现阶段继续扩大“AI 模块目录”。
- 优先确保它们未来消费的输入是 `StaticResult / Evidence / HookPlan / TrafficFlow`。

## 八、对现有文件的处置建议

### 保留并继续作为主线

- `application/services/job_service.py`
- `application/services/static_adapter.py`
- `application/services/hook_plan_service.py`
- `domain/services/hook_advisor.py`
- `domain/services/offline_rule_engine.py`
- `domain/services/method_indexer.py`
- `infrastructure/templates/script_renderer.py`
- `infrastructure/persistence/hook_log_store.py`
- `interfaces/api_fastapi/*`
- `frontend/src/pages/CaseWorkspacePage.tsx`

### 保留但降级为兼容层/过渡层

- `static_engine/analyzer.py`
- `static_engine/legacy/*`
- `application/services/workspace_runtime_service.py`
- `application/services/workspace_runtime_state.py`
- `infrastructure/execution/real_backend.py`

### 后续只做冻结兼容，不再扩展

- `interfaces/gui_pyqt/*`

## 九、优先级排序

### P0：现在就该做

- 文档与目录主线收敛
- `StaticResult / ArtifactManifest / Finding / Evidence`
- `workspace_runtime_service.py` 拆分设计
- Hook 模型扩展但保持 API 兼容

### P1：紧接着做

- `flows.sqlite3`
- 统一模板注册表
- 统一动态事件 schema
- 设备抽象接口第一版

### P2：之后做

- static 子模块化
- live capture 实时化增强
- 证据链关联

### P3：最后做

- AI 代码分析
- AI 流量分析
- Flutter/React Native/uni-app 插件
- 脱壳深度能力

## 十、验证门槛

每一阶段都应至少通过以下验证：

```bash
uv run pytest -q
npm run typecheck:web
npm run test:web -- --run
```

如涉及桌面壳或 sidecar 行为，再补：

```bash
cargo check --manifest-path src-tauri/Cargo.toml
```

## 十一、最终落地标准

当以下条件同时满足时，视为本轮重构完成：

1. 项目只保留一条清晰的架构主线。
2. 静态结果、Hook 计划、动态事件、流量证据都具有稳定 schema。
3. `workspace_runtime_service.py` 不再是唯一编排黑洞。
4. FastAPI 响应不再依赖前端做大量启发式重建。
5. 当前工作台闭环不被破坏：
   - 导入样本
   - 查看静态摘要
   - 搜索方法
   - 生成 Hook 计划
   - 启动执行
   - 导入或抓取流量
   - 导出报告

## 十二、一句话总结

本次重构不是“给 APKHacker 设计一套全新的理想目录”，而是：

**以现有工作台主链为基础，先做 schema 和服务边界收敛，再把静态、Hook、执行、流量逐步升级成真正可扩展的分析平台。**
