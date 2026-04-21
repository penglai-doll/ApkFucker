# APKHacker Tauri 工作台壳层重构实施计划

> 基于 `/Users/penglai/Documents/Objects/APKHacker/docs/superpowers/specs/2026-04-18-tauri-winui-shell-refresh-design.md`

## 目标

把当前 React/Tauri 前端从“功能平铺页”重构为“左侧文字导航 + 顶部 WinUI 风格 banner + 分区工作台”的中文桌面界面，同时保持现有核心功能链路不回退。

## 实施顺序

### 任务 1：建立统一壳层与全局样式

- 重构 `frontend/src/components/layout/AppFrame.tsx`
- 新增全局样式文件并在 `frontend/src/main.tsx` 引入
- 建立：
  - 左侧导航栏
  - 顶部 banner
  - 主内容区容器

### 任务 2：重构案件队列页

- 重排 `frontend/src/pages/CaseQueuePage.tsx`
- 优化 `frontend/src/components/queue/CaseQueueTable.tsx`
- 形成：
  - 页面头部
  - 导入区
  - 快速摘要
  - 案件列表

### 任务 3：重构案件工作台页

- 重排 `frontend/src/pages/CaseWorkspacePage.tsx`
- 新增工作台头部摘要和页内 section 导航
- 重新组织各业务 panel 的顺序和布局

### 任务 4：增强工作台子模块的可读性样式

- 视需要给各个 workspace panel 增加 className 或结构包装
- 统一按钮、表单、表格、列表和状态展示观感

### 任务 5：测试与验证

- 更新受影响的 web 测试
- 运行：
  - `npm run test:web`
  - `npm run typecheck:web`
  - `npm run build:web`
- 如壳层改动涉及桌面构建，再运行：
  - `cargo check --manifest-path src-tauri/Cargo.toml`
  - `npm run build:tauri -- --no-bundle`

## 文件范围

优先修改：

- `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/layout/AppFrame.tsx`
- `/Users/penglai/Documents/Objects/APKHacker/frontend/src/main.tsx`
- `/Users/penglai/Documents/Objects/APKHacker/frontend/src/pages/CaseQueuePage.tsx`
- `/Users/penglai/Documents/Objects/APKHacker/frontend/src/pages/CaseWorkspacePage.tsx`
- `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/queue/CaseQueueTable.tsx`
- `/Users/penglai/Documents/Objects/APKHacker/frontend/src/components/workspace/*.tsx`
- `/Users/penglai/Documents/Objects/APKHacker/frontend/src/test/*.test.tsx`

新增：

- `/Users/penglai/Documents/Objects/APKHacker/frontend/src/styles/app.css`

## 验收标准

- 左侧导航与顶部 banner 生效
- 队列页和工作台页都有明显的信息层级提升
- 中文界面保持一致
- 现有主功能可继续使用
- 前端测试、类型检查和构建通过

