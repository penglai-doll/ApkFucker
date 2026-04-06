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
- 离线 Hook Assistant / 模板建议
- 离线 HAR 导入与可疑流量标记
- 自定义 Frida 脚本编辑与加入计划
- `Fake Backend / Real Device` 执行模式切换
- 脚本真实渲染与预览
- `Open in JADX`

当前未完成：

- 原生 ADB / Frida 一体化设备执行
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

如果你想直接指定 `Real Device` 的命令型后端，也可以在启动时传入：

```bash
uv run apk-hacker \
  --sample /path/to/sample.apk \
  --real-backend-command "uv run apk-hacker-frida-probe-backend"
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
  - 目前是“命令型真实后端”骨架
  - 可以通过环境变量 `APKHACKER_REAL_BACKEND_COMMAND` 指向你自己的执行器脚本
  - 后端会把当前计划和已渲染的脚本写入临时目录，再把路径和运行上下文通过环境变量传给执行器：
    - `APKHACKER_JOB_ID`
    - `APKHACKER_TARGET_PACKAGE`
    - `APKHACKER_PLAN_PATH`
    - `APKHACKER_SCRIPTS_DIR`
    - `APKHACKER_WORKDIR`
    - `APKHACKER_SAMPLE_PATH`（有样本路径时）
  - 执行器向标准输出打印 JSON 行后，工作台会把它解析成真实事件

一个最简单的外部执行器可以是：

```bash
export APKHACKER_REAL_BACKEND_COMMAND="python /path/to/runner.py"
uv run apk-hacker
```

仓库里也自带了一个演示执行器，方便本地先验证真实后端协议：

```bash
export APKHACKER_REAL_BACKEND_COMMAND="uv run apk-hacker-demo-real-backend"
uv run apk-hacker
```

如果你本机已经装好了 `adb`，也可以直接用仓库内置的设备探测 runner：

```bash
export APKHACKER_REAL_BACKEND_COMMAND="uv run apk-hacker-adb-probe-backend"
uv run apk-hacker
```

这个 runner 目前不会注入 Frida，但会把 `adb devices` 和设备 ABI 探测结果以真实事件的方式回传到工作台，用来验证本机到设备的桥接链路。

如果你本机已经装好了 `frida-tools`，也可以直接用仓库内置的 Frida 目标探测 runner：

```bash
export APKHACKER_REAL_BACKEND_COMMAND="uv run apk-hacker-frida-probe-backend"
uv run apk-hacker
```

这个 runner 会调用 `frida-ps -Uai`，并根据当前工作台里样本的包名回传目标可见性事件，适合先验证 `Real Device -> Frida -> 目标包识别` 这条最小链路。

如果你想继续往前验证一次最小注入探针，也可以使用：

```bash
uv run apk-hacker \
  --sample /path/to/sample.apk \
  --real-backend-command "uv run apk-hacker-frida-inject-backend"
```

这个 runner 会选取当前计划里第一份已渲染脚本，调用 `frida -U -f <package> -l <script>` 做一次短时注入探针，并把结果折叠成单条 `frida_injection` 事件。它当前更适合做链路验证，还不是长期会话采集器。

如果你已经安装了 Python 版 `frida` 模块，并且想把脚本消息真正回流到工作台，可以使用：

```bash
uv run apk-hacker \
  --sample /path/to/sample.apk \
  --real-backend-command "uv run apk-hacker-frida-session-backend"
```

这个 runner 会通过 Python `frida` API 执行 `spawn -> attach -> load -> resume`，并把脚本里的 `send(...)` 消息转成结构化事件。当前版本只做最小会话，不负责长期保持连接或复杂的多脚本编排。
当前已经支持按 `Hook Plan` 顺序依次加载多份脚本，并在事件里附带来源脚本名，方便在工作台日志中区分不同脚本的输出。
如果会话期间没有收到脚本消息，会回传 `frida_session_timeout`；如果连接设备、加载脚本或恢复进程失败，会回传 `frida_session_error`，便于在工作台里区分“链路不通”和“脚本本身没产生日志”。

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

- `91 passed`

## 注意事项

- 当前版本更适合本地研究和工作流验证，不适合作为完整恶意样本动态分析平台直接投入生产使用
- 请在隔离环境中处理可疑 APK
- `Real Device` 相关能力仍在持续补完，当前不要把它当成已完成特性
