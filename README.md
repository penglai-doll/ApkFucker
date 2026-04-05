# APKHacker

本项目是一个面向本地环境的 Android APK 静态/动态分析工作台，当前处于 `pre-release` 阶段。

当前版本重点是把可测试的主闭环先跑通：

- 迁入第一方静态分析引擎
- 在 PyQt6 工作台里导入样本并运行静态分析
- 浏览方法索引并生成 Hook 计划
- 编写、保存并插入自定义 Frida 脚本
- 使用 `Fake Backend` 跑通动态日志闭环
- 将样本一键交给本地 `jadx-gui` 深入查看

## 当前状态

已经可用于本地初步试用，但还不是完整动态分析发行版。

当前可用：

- GUI 启动与基本工作流
- 真实静态分析入口
- 方法级 Hook 计划
- 自定义 Frida 脚本编辑与加入计划
- `Fake Backend / Real Device` 执行模式切换
- `Open in JADX`

当前未完成：

- 真实 ADB / Frida 设备执行
- 抓包、SSL Unpinning、脱壳
- AI 代码分析、AI 流量分析
- FastAPI/Tauri 前端层

## 运行环境

推荐：

- Python `3.11+`
- `uv`
- Java runtime
- `jadx`
- `apktool`

完整静态分析最好还能提供以下工具中的至少一种：

- `apkanalyzer`
- `aapt`
- `aapt2`

可选但推荐：

- `jadx-gui`
- `adb`

## 安装

```bash
uv sync --dev
```

## 启动

最简单的启动方式：

```bash
uv run apk-hacker
```

也可以预填样本路径和本地 `jadx-gui`：

```bash
uv run apk-hacker \
  --sample /path/to/sample.apk \
  --jadx-gui-path /path/to/jadx-gui
```

如果 `jadx-gui` 已经在 `PATH` 上，或者设置了环境变量 `APKHACKER_JADX_GUI_PATH`，应用会自动发现它。

查看参数：

```bash
uv run apk-hacker --help
```

## 典型工作流

1. 启动工作台
2. 在 `Task Center` 中填入 APK 路径
3. 点击 `Run Static Analysis`
4. 在 `Method Index` 中搜索并选择方法，加入 `Hook Plan`
5. 在 `Custom Frida Scripts` 中编写或保存脚本，并加入计划
6. 在 `Script Plan` 中选择执行模式
7. 用 `Fake Backend` 验证计划、日志与摘要是否符合预期
8. 需要深入看反编译代码时，使用 `Open in JADX`

## 执行模式说明

- `Fake Backend`
  - 当前默认模式
  - 用于验证计划、脚本、日志存储和 GUI 交互
- `Real Device`
  - 目前只有骨架
  - 如果没有注入真实后端，会明确提示未配置

## 目录说明

- `src/apk_hacker/static_engine/`
  - 第一方静态分析引擎与 JADX 导出契约
- `src/apk_hacker/application/services/`
  - 静态适配、Hook 计划、自定义脚本、任务服务
- `src/apk_hacker/infrastructure/execution/`
  - fake / real 执行后端抽象
- `src/apk_hacker/interfaces/gui_pyqt/`
  - PyQt6 工作台
- `tests/`
  - 单元测试、集成测试、GUI smoke/workflow 测试

## 测试

```bash
uv run pytest -q
```

当前分支验证结果为：

- `63 passed`

## 注意事项

- 当前版本更适合本地研究和工作流验证，不适合作为完整恶意样本动态分析平台直接投入生产使用
- 请在隔离环境中处理可疑 APK
- `Real Device` 相关能力仍在持续补完，当前不要把它当成已完成特性
