# APKHacker Tauri 重构设计

> 状态：Draft
> 日期：2026-04-06
> 适用范围：替代现有 PyQt6 桌面前端，重构为 `Tauri + React + 本地 API + Python workers` 的新工作台
> 关联文档：
> - `/Users/penglai/Documents/Objects/APKHacker/docs/superpowers/specs/2026-04-05-apk-hacker-mvp-design.md`
> - `/Users/penglai/Documents/Objects/APKHacker/docs/superpowers/plans/2026-04-05-apk-hacker-mvp-plan.md`

Implementation plan: `/Users/penglai/Documents/Objects/APKHacker/docs/superpowers/plans/2026-04-06-apk-hacker-tauri-redesign-plan.md`

## 1. 背景与目标

> 2026-04-13 更新：本设计已从“重构候选方案”升级为当前产品主线。后续新增功能默认只落在 `Tauri + React + FastAPI`，`PyQt6` 进入冻结并淘汰流程，不再承载新能力。

现有 PyQt6 原型已经验证了 APKHacker 的核心分析闭环是可行的：

- 导入样本并运行静态分析
- 构建方法索引与 Hook 建议
- 管理 Hook 计划与自定义 Frida 脚本
- 执行 fake/real backend
- 汇总日志、运行包、HAR 与导出报告

当前问题不在分析能力不足，而在于桌面工作台本身已经接近原型上限：

- 信息架构偏“页签堆叠”，不适合持续扩展
- 界面状态和产品流程已开始复杂化
- 未来要支持更完整的本地发行、打包和后端演进，PyQt6 不再是理想长期前端

因此当前阶段的目标不是“把 PyQt6 翻译成 Tauri”，而是：

1. 直接用 Tauri 替代 PyQt6 成为唯一桌面入口
2. 以 React + TypeScript 重新设计工作台信息架构和页面系统
3. 把现有 Python 分析内核外包为本地 API 服务
4. 保证后续可以逐步把 API/编排层迁移到 Rust

对应迁移映射：

- `Task Center` -> `Case Queue / Case Workspace`
- `Script Plan` -> `Hook Studio + Execution Console`
- `Results Summary` -> `Reports + Evidence + Execution`

## 2. 已确认的产品与技术决策

以下决策已在需求收敛阶段确认：

- 首发平台：`macOS Apple Silicon`
- UI 语言：`全中文`
- 前端框架：`React + TypeScript`
- 桌面壳：`Tauri v2`
- 实时通道：`WebSocket`
- 数据模型：`每个样本一个独立 workspace`
- 导入策略：`导入时默认复制样本到 workspace`
- workspace 根目录：`默认可配置，单次导入也可覆盖`
- 默认启动行为：`优先恢复上次打开的 Case Workspace；恢复失败时回到 Case Queue`
- 后端首版：`FastAPI Local API`
- 后端分发：`随应用打包的 Python sidecar`
- 长期演进：`Rust 优先接管 API 与编排层，静态分析与 Frida worker 暂时保留 Python`

## 3. 北极星产品形态

新版 APKHacker 不是“一个 APK 页签工具”，而是“本地案件分析工作台”。

顶层采用双模式产品结构：

### 3.1 `Case Queue`

面向多样本与案件队列管理。

主要职责：

- 导入样本
- 创建 workspace
- 批量发起静态分析
- 查看任务状态和失败原因
- 按标签、风险、状态和时间筛选
- 一键进入某个样本的深度分析工作台

### 3.2 `Case Workspace`

面向单样本深度分析。

主要职责：

- 浏览静态摘要
- 搜索方法和筛选候选 Hook 点
- 使用 Hook 助手和模板建议构建计划
- 管理自定义 Frida 脚本
- 运行 fake/real backend
- 查看执行日志、运行包、HAR 与证据
- 导出报告

两种模式共用同一套后端与数据模型，只是面向不同分析粒度的视图。

## 4. 总体架构

## 4.1 逻辑分层

```text
Tauri Desktop Shell (Rust)
  ├── 窗口/菜单/文件选择/生命周期/打包
  └── 启动与守护本地 API sidecar

React Frontend (TypeScript)
  ├── Case Queue
  ├── Case Workspace
  ├── 全局状态
  └── REST + WebSocket 客户端

App API Layer (FastAPI first, Rust later)
  ├── Case API
  ├── Workspace API
  ├── Hook Plan API
  ├── Execution API
  ├── Report API
  └── WebSocket Event Hub

Worker Layer (Python first)
  ├── Static Analysis Worker
  ├── Frida Worker
  ├── Traffic/Report Worker
  └── 后续可逐步替换

Python Core
  ├── static_engine
  ├── application
  ├── domain
  ├── infrastructure
  └── tools
```

## 4.2 关键架构原则

- 前端只依赖 API，不依赖 Python 内部对象
- Tauri 只负责桌面能力和进程生命周期，不承载分析业务逻辑
- API 层只做应用契约和状态编排，不直接耦合 React 组件
- worker 层可替换，允许未来逐步把 API/编排层迁到 Rust，而保留 Python 分析 worker

## 5. 为什么采用 `Python sidecar` 而不是立即 Rust 后端

当前仓库里最成熟的能力仍然集中在 Python：

- 静态分析引擎：`src/apk_hacker/static_engine/`
- 工作台编排与状态语义：`src/apk_hacker/interfaces/gui_pyqt/viewmodels.py`
- 真实执行链路：`src/apk_hacker/infrastructure/execution/` 与 `src/apk_hacker/tools/`

其中最难直接迁到 Rust 的是 Frida 相关能力：

- 设备连接与重试
- `spawn / attach / load script / receive message`
- 多脚本顺序加载
- `frida-server` bootstrap
- 与 `adb`、环境变量、stdout/stderr、运行包目录的联动

因此当前阶段的最佳路线不是一次性 Rust 化，而是：

1. 先把 PyQt6 替换为 Tauri + React
2. 先把后端服务化为本地 FastAPI
3. 后续再把 API/编排层逐步替换为 Rust
4. 将静态分析和 Frida 长期作为 worker 保留更久

## 6. 页面级信息架构

## 6.1 顶层结构

### 顶栏

- 应用名
- 当前模式切换：`案件队列 / 案件工作台`
- 当前工作区名称
- 全局搜索入口
- 环境状态指示器
- 设置入口

### 左侧主导航

在 `Case Queue` 和 `Case Workspace` 下显示不同导航。

## 6.2 `Case Queue` 页面结构

### 页面目标

把“文件导入 + 任务队列 + 样本筛选 + 运行状态”合并成一个真正的案件队列视图。

### 一级区块

#### `导入区`

- 拖拽或选择 APK/APKS/XAPK/ZIP
- 选择 workspace 根目录
- 导入策略提示：默认复制到 workspace

#### `案件列表`

核心表格字段建议：

- 案件名称
- 包名
- 当前状态
- 风险标签
- 技术标签
- 最后更新时间
- 是否已有执行结果
- 快捷动作

#### `筛选与分组`

- 按状态筛选
- 按风险标签筛选
- 按时间排序
- 按技术框架筛选
- 按是否失败/需重试筛选

#### `右侧快速摘要`

选中某个案件后显示：

- 样本基本信息
- 静态摘要卡片
- 推荐下一步动作
- “进入工作台”按钮

## 6.3 `Case Workspace` 页面结构

`Case Workspace` 采用单工作面，而不是多个松散页签。

### 一级模块

#### `静态简报`

取代当前 `Static Summary` 页，重构为案件简报视图：

- 包名和样本信息
- 技术栈
- 危险权限
- 回连线索
- 加密线索
- packer 提示
- 关键限制说明
- 一键 `Open in JADX`

#### `Hook Studio`

这是新版最关键的重构页面，负责取代当前这些分散页面：

- `Method Index`
- `Hook Assistant`
- `Custom Frida Scripts`
- `Script Plan`

页面内部建议分为四栏或三栏布局：

- 方法搜索与筛选区
- 推荐与模板建议区
- 当前 Hook 计划区
- 自定义脚本编辑/预览区

典型动作：

- 搜索方法
- 选择方法加入计划
- 接受模板建议
- 保存并插入自定义脚本
- 预览渲染后的脚本

#### `执行控制台`

取代当前 `Execution & Logs` 与部分 `Script Plan` 运行逻辑：

- 执行模式选择
- 环境诊断
- `Fake Backend / Real Device / ADB Probe / Frida Session` 等预设
- 开始执行按钮
- 实时 WebSocket 日志流
- stderr/stdout 视图
- bundle 路径和数据库路径

#### `证据中心`

统一承接动态产物，而不是分散显示：

- Hook 事件流
- 结构化详情
- HAR 导入结果
- 可疑流量摘要
- 执行包
- SQLite 数据

#### `报告与导出`

- 报告摘要
- 导出 Markdown
- 显示静态报告路径
- 显示动态报告路径
- 复制路径
- 打开工作区目录

## 7. 状态模型

前端不再使用 PyQt 的 `WorkbenchState`，但需要保留其业务语义。

建议拆成以下前端状态域：

### 7.1 `AppSessionState`

- 最近打开的 workspace
- 当前模式：`queue | workspace`
- 当前语言：固定中文
- 后端连通性
- 全局环境状态摘要

### 7.2 `CaseQueueState`

- 案件列表
- 当前筛选条件
- 当前排序
- 导入任务状态
- 当前选中案件

### 7.3 `WorkspaceState`

- 当前 workspace 元数据
- 静态摘要
- 方法索引
- 当前搜索查询
- Hook 建议
- Hook 计划
- 当前自定义脚本草稿
- 实时执行状态
- 执行事件流
- HAR 与证据摘要
- 导出状态

## 8. 后端 API 草案

## 8.1 REST 资源模型

### `Case`

表示一个案件记录，对应一个独立 workspace。

建议字段：

- `case_id`
- `title`
- `package_name`
- `sample_name`
- `workspace_root`
- `status`
- `risk_tags`
- `technical_tags`
- `updated_at`

### `Workspace`

表示案件的分析上下文。

建议字段：

- `case_id`
- `sample_path`
- `static_artifacts`
- `hook_plan`
- `last_execution`
- `traffic_capture`
- `report_exports`

### `ExecutionRun`

表示一次 fake/real backend 执行。

建议字段：

- `run_id`
- `case_id`
- `mode`
- `status`
- `started_at`
- `finished_at`
- `db_path`
- `bundle_path`
- `event_count`

## 8.2 REST 接口草案

### 案件队列

- `GET /api/cases`
- `POST /api/cases/import`
- `GET /api/cases/{case_id}`
- `DELETE /api/cases/{case_id}`
- `POST /api/cases/{case_id}/open`

### 静态分析

- `POST /api/cases/{case_id}/static-analysis`
- `GET /api/cases/{case_id}/static-brief`
- `GET /api/cases/{case_id}/methods`
- `GET /api/cases/{case_id}/methods/search?q=...`

### Hook Studio

- `GET /api/cases/{case_id}/hook-recommendations`
- `GET /api/cases/{case_id}/hook-plan`
- `POST /api/cases/{case_id}/hook-plan/methods`
- `POST /api/cases/{case_id}/hook-plan/templates`
- `POST /api/cases/{case_id}/hook-plan/custom-scripts`
- `DELETE /api/cases/{case_id}/hook-plan/items/{item_id}`
- `POST /api/cases/{case_id}/custom-scripts`
- `GET /api/cases/{case_id}/custom-scripts`

### 执行与证据

- `POST /api/cases/{case_id}/executions`
- `GET /api/cases/{case_id}/executions/latest`
- `GET /api/cases/{case_id}/events`
- `POST /api/cases/{case_id}/traffic/import`
- `GET /api/cases/{case_id}/traffic`

### 报告

- `POST /api/cases/{case_id}/reports/export`
- `GET /api/cases/{case_id}/reports`

### 环境与设置

- `GET /api/environment`
- `GET /api/execution-presets`
- `GET /api/settings`
- `PUT /api/settings`

## 8.3 WebSocket 事件草案

统一 WebSocket 端点建议：

- `GET /ws`

按消息类型推送事件：

- `app.ready`
- `case.imported`
- `case.updated`
- `static.started`
- `static.progress`
- `static.completed`
- `hook_plan.updated`
- `execution.started`
- `execution.event`
- `execution.stderr`
- `execution.bundle_ready`
- `execution.completed`
- `traffic.updated`
- `report.exported`
- `worker.error`

建议统一消息结构：

```json
{
  "type": "execution.event",
  "case_id": "case_123",
  "run_id": "run_001",
  "timestamp": "2026-04-06T10:00:00Z",
  "payload": {}
}
```

## 9. Workspace 存储模型

每个案件一个独立目录，默认由用户指定的 workspace 根目录派生。

建议目录结构：

```text
<workspace-root>/
  workspace.json
  sample/
    original.apk
  static/
    analysis.json
    callback-config.json
    noise-log.json
    report.md
    report.docx
    jadx/
  hooks/
    plan.json
    rendered/
    custom/
  runs/
    run-001/
      stdout.log
      stderr.log
      bundle/
  traffic/
    capture.har
  reports/
    merged-report.md
  data/
    hooks.sqlite3
```

### `workspace.json` 建议字段

- `workspace_version`
- `case_id`
- `title`
- `created_at`
- `updated_at`
- `sample_filename`
- `package_name`
- `last_opened_page`
- `last_execution_mode`
- `tags`

## 10. macOS Apple Silicon 首发打包方案

## 10.1 首发范围

首发只面向：

- `macOS`
- `Apple Silicon`

暂不以 Windows 和 Docker 为第一版打包目标。

## 10.2 打包策略

### Tauri 侧

- 使用 `Tauri v2`
- 通过 `bundle.externalBin` 打包 Python sidecar
- 通过 `bundle.resources` 打包额外资源
- 通过 `capabilities` 限定 shell/process 权限

### Python sidecar 侧

首版目标是把 FastAPI 服务与现有 Python worker 打成可随应用分发的本地二进制或可执行包。

最低要求：

- 应用启动时可被 Tauri 拉起
- 应用退出时可被 Tauri 回收
- 监听本地环回地址
- 端口由主程序控制或自动协商
- 运行日志可回写到 workspace 或应用日志目录

## 10.3 本地依赖处理策略

首发不强行把所有外部工具一起内嵌进 App。

分为三类：

### 应用内分发

- Python sidecar
- 前端资源
- 应用自身默认配置

### 外部依赖探测

- `jadx-gui`
- `adb`
- `frida`
- `apktool`
- `apkanalyzer` / `aapt` / `aapt2`

### 用户提示策略

应用内必须有完整中文环境诊断：

- 缺失哪个工具
- 当前路径在哪里
- 会影响哪些功能
- 如何修复

## 11. Rust 迁移友好设计

为了避免未来二次大换血，本次设计从第一天就要求“Rust 友好”。

### 11.1 当前不迁的部分

- `static_engine`
- `Frida worker`
- 各类复杂工具链编排脚本

### 11.2 后续优先迁 Rust 的部分

- API 层
- case/workspace 状态机
- 队列管理
- 报告导出编排
- 事件总线
- 运行配置与环境诊断编排

### 11.3 为 Rust 迁移预留的约束

- 所有前端调用必须经过 REST/WebSocket
- 不允许前端依赖 Python 内部结构
- API 契约优先稳定
- worker 通过明确定义的输入/输出协议与 API 层交互

## 12. 迁移路线

### Phase A：API 抽离

目标：

- 从现有 Python 内核中抽出本地 FastAPI
- 保留现有业务语义
- 不在这一阶段重写分析逻辑

产出：

- API 原型
- WebSocket 事件流
- workspace 存储落盘

### Phase B：Tauri + React 新前端

目标：

- 用新信息架构重建工作台
- 直接按 `Case Queue + Case Workspace` 实现
- UI 全中文

产出：

- macOS Apple Silicon 可运行的新桌面应用
- 可恢复上次 workspace

### Phase C：替代 PyQt6

目标：

- 达成功能对齐
- 移除 PyQt6 作为主入口

产出：

- Tauri 成为唯一桌面入口

### Phase D：Rust 编排层替换

目标：

- 逐步把 API/编排层从 Python 迁到 Rust

产出：

- Rust API
- Python worker 留存

## 13. 风险与缓解策略

### 13.1 主要风险

- 同时更换桌面壳、前端框架、后端交互模式和信息架构，复杂度高
- Python sidecar 打包与本地工具探测会带来首发集成成本
- 如果 API 契约不稳定，未来 Rust 迁移成本会急剧上升

### 13.2 缓解方式

- 先冻结 API 契约，再做前端
- 先做 macOS Apple Silicon，压缩平台变量
- 保留独立 workspace 模型，避免全局状态混乱
- 把 Frida 和静态分析留在 worker 层，避免一次性重写最难部分

## 14. 成功标准

当以下条件同时满足时，视为本轮 Tauri 重构成功：

- 新应用在 macOS Apple Silicon 上可独立启动
- 启动后默认恢复上次 workspace
- 可以导入 APK 并创建独立 workspace
- 可以完成静态分析并展示中文静态简报
- 可以在 `Hook Studio` 中完成方法搜索、计划构建和自定义脚本操作
- 可以通过 WebSocket 实时看到执行事件
- 可以导出报告并定位到 workspace 内产物
- 用户无需预装 Python
