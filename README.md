# APKHacker

本项目是一个面向本地环境的 Android APK 静态/动态分析工作台，当前处于 `pre-release` 阶段。

## 当前产品方向

当前唯一的产品主线是 `Tauri + React + FastAPI`。

- `Tauri + React` 是唯一继续演进的桌面工作台
- `FastAPI` 是唯一应用契约与状态编排入口
- `PyQt6` 已冻结，只作为迁移期参考实现，后续将淘汰
- 新增功能默认只允许落在 `API + React` 主线，不再向 PyQt 回填

当前版本重点是把可测试的主闭环先跑通，并把旧工作台能力迁移到新主线：

- 迁入第一方静态分析引擎
- 在案件工作台中导入样本并运行静态分析
- 浏览方法索引并生成 Hook 计划
- 编写、保存并插入自定义 Frida 脚本
- 使用 `Fake Backend` 跑通动态日志闭环
- 将样本一键交给本地 `jadx-gui` 深入查看

## 当前状态

已经可用于本地初步试用，但还不是完整动态分析发行版。

当前可用：

- `FastAPI + React` 工作台主闭环
- 真实静态分析入口
- 方法级 Hook 计划
- Hook 计划顺序调整、启用/禁用
- 离线 Hook Assistant / 模板建议
- 离线 HAR 导入与可疑流量标记
- 流量证据 provenance 区分：手工 HAR / 实时抓包自动导入
- 自定义 Frida 脚本编辑与加入计划
- 自定义脚本读取 / 更新 / 删除
- 启动即加载已有自定义 Frida 脚本
- `Fake Backend / Real Device` 执行模式切换
- 独立执行前检查（preflight）API 与工作台提示
- 多次执行历史列表与事件回放
- 脚本真实渲染与预览
- `Open in JADX`
- 工作台运行参数持久化
- 真实后端运行包持久化
- 日志事件详情面板
- 结果页路径一键复制
- 日志详情一键复制
- 本地 Markdown 合并报告导出
- 实时抓包第一版：命令型 live capture + HAR 自动导入

当前未完成：

- 原生 ADB / Frida 一体化设备执行
- SSL Unpinning、完整抓包编排、脱壳
- AI 代码分析、AI 流量分析
- 完整的 Tauri 默认桌面交付与 PyQt 淘汰收口

## 迁移映射

旧工作台术语与新主线的对应关系如下：

- `Task Center` -> `Case Queue / Case Workspace`
- `Script Plan` -> `Hook Studio + Execution Console`
- `Results Summary` -> `Reports + Evidence + Execution`

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
npm install
```

## 启动

推荐的桌面主线启动方式：

```bash
npm run dev:tauri
```

开发态 `Tauri` 现在仍会优先走本地 sidecar，但前端不再依赖 `Vite` 代理才能访问 API：

- 浏览器开发态：默认继续使用相对路径，由 `frontend/vite.config.ts` 代理到 `127.0.0.1:8765`
- `Tauri` 运行态：如果没有显式配置 `VITE_API_BASE_URL`，前端会自动回落到 `http://127.0.0.1:8765`
- 本地 API 会额外放行 `http://127.0.0.1:5173`、`http://localhost:5173`、`http://tauri.localhost`、`https://tauri.localhost` 和 `tauri://localhost` 这些运行来源

如果你只想单独调试前端：

```bash
npm run dev:web
```

如果你只想启动本地 API：

```bash
uv run apk-hacker
```

兼容命令 `apk-hacker-legacy` 仍然保留，但它现在只作为迁移提示入口，不再启动旧版 GUI：

```bash
uv run apk-hacker-legacy
```

这个兼容入口会保留原有参数面，方便旧脚本或启动器识别，但运行时只会提示迁移到：

- `npm run dev:tauri`
- `uv run apk-hacker`

## Tauri 打包运行时说明

当前 `Tauri` 运行时已经往“更自包含”推进了一版，但还不是完全无依赖分发：

- 打包态前端会默认直连 `http://127.0.0.1:8765`，不再假定存在 `Vite` 代理
- `src-tauri` 会把 `src/` 和 `pyproject.toml` 一起打进 `Resources`，sidecar 优先尝试从打包资源或当前工程树里启动本地 API
- sidecar 启动顺序大致是：
  1. `APKHACKER_API_COMMAND` 显式覆盖
  2. 开发态工程根目录下的 `uv/python`
  3. 打包资源目录里的 `uv/python`
  4. PATH 中已有的 `apk-hacker-api`

这意味着当前版本在 `no-bundle` 或正式 bundle 下，仍然建议满足以下前提之一：

- 已经在本机准备好 `uv sync --dev`
- 或者至少存在可用的 `python3` / `python`，并且已经安装 `fastapi`、`uvicorn`
- 或者显式提供 `APKHACKER_API_COMMAND`

如果你想验证当前这条打包链，可以直接运行：

```bash
npm run smoke:packaged
```

如果你只想产出不打包成 `.app` 的桌面可执行文件，可以使用：

```bash
npm run build:tauri:no-bundle
```

当前 `no-bundle` 产物依然会尝试从：

- 当前工程树
- 打包资源目录
- 或 PATH 中的 `apk-hacker-api`

这几个来源启动 sidecar；如果都不可用，请显式设置：

```bash
export APKHACKER_API_COMMAND="uv run apk-hacker-api"
```

如果你想走 headless 批处理，也可以直接使用 CLI：

```bash
uv run apk-hacker-cli \
  --sample /path/to/sample.apk \
  --method-query buildUploadUrl \
  --add-top-recommendations 2 \
  --run
```

CLI 会输出一份 JSON 摘要，包含：

- 静态分析识别到的包名
- 方法索引数量与推荐数量
- 当前 Hook 计划项
- 执行模式、事件数量与事件详情
- 最近一次执行产生的 SQLite 路径和运行包路径

如果你希望直接走真实后端，也可以：

```bash
uv run apk-hacker-cli \
  --sample /path/to/sample.apk \
  --method-query buildUploadUrl \
  --execution-mode real_device \
  --real-backend-command "uv run apk-hacker-frida-session-backend" \
  --device-serial serial-123 \
  --run
```

当 CLI 无法匹配方法、没有计划项却要求执行，或真实后端返回受控错误时，它会向 `stderr` 输出 JSON 错误并以非零退出码结束，方便后续脚本或 CI 直接消费。

如果你希望在 CLI 里顺手导出一份本地 Markdown 报告，可以加上：

```bash
uv run apk-hacker-cli \
  --sample /path/to/sample.apk \
  --method-query buildUploadUrl \
  --export-report
```

导出的报告默认会写到 `cache/cli/reports/` 或你自定义的 `--db-root/reports/` 下，CLI 返回的 JSON 里会额外带上 `exported_report_path`。

## 典型工作流

1. 启动桌面工作台
2. 在 `案件队列` 中导入 APK 并选择工作目录
3. 在 `案件工作台` 中运行静态分析
4. 在 `Hook 工作台` 中搜索方法、接受建议并维护 Hook 计划
5. 在 `自定义 Frida 脚本` 区域编写、保存并加入计划
6. 在 `执行控制台` 中先做预检，再选择执行模式
7. 需要真机时，在工作台里填写 `设备序列号` 和 `Frida Server 文件`
8. 先用 `Fake Backend` 验证计划、日志与摘要，再切到真实预设
9. 需要深入看反编译代码时，使用 `Open in JADX`
10. 需要本地归档时，在 `报告与导出` 中导出 Markdown 报告

当前 GUI 的执行模式下拉框已经内置这些预设：

- `Fake Backend`
- `Real Device`
- `ADB Probe`
- `Frida Bootstrap`
- `Frida Probe`
- `Frida Inject`
- `Frida Session`

其中后五者会直接调用仓库自带的后端 runner，适合本地逐步验证 `adb / frida` 链路；只有在你想接自定义执行器时，才需要继续使用 `--real-backend-command` 或环境变量覆盖 `Real Device`。
工作台会根据当前环境自动评估这些预设的可用性：例如缺少 `adb` 时会禁用 `ADB Probe` 和 `Frida Bootstrap`，缺少 Python `frida` 模块时会禁用 `Frida Session`，并在 `执行控制台` 里显示每个预设当前是 `ready` 还是 `unavailable`。
`Real Device` 本身会自动路由到当前最合适的内置后端：优先 `Frida Session`，其次 `Frida Inject`、`Frida Probe`、`ADB Probe`；如果你显式传入 `--real-backend-command`，则优先使用你的自定义后端。
如果你不想每次都从命令行传参数，工作台的 `执行控制台` 里也提供了 `Device Serial`、`Frida Server Binary`、`Frida Remote Path` 和 `Session Seconds` 四个输入框；它们会直接透传到真实后端执行环境中。
这些输入以及上次使用的样本路径、执行模式，都会保存在本地 `workbench-settings.json` 里，重新打开工作台后会自动恢复。
当你走真实后端链路时，工作台还会把每次执行对应的 `plan.json`、渲染脚本、`stdout.log` 和 `stderr.log` 保存在本地运行包目录里，并在 `证据中心` 与 `报告与导出` 里直接显示 SQLite 和运行包路径。
结果页还提供了路径一键复制按钮，方便直接贴到终端、Finder 或其他工具里继续排查。
在 `执行控制台` 中选中任意事件后，也可以直接一键复制完整详情，包含参数、返回值、堆栈和原始 payload。

## 实时抓包（第一版）

当前实时抓包采用“命令型 live capture”模式：工作台负责启动/停止一个外部抓包进程，并约定它在停止时把 HAR 产物写到指定路径。

如果你本机已经安装了 `mitmdump`，工作台现在会自动识别并启用一条内置抓包后端，不再强制要求你先配置环境变量。内置后端默认监听 `0.0.0.0:8080`，并在停止时通过 `--set hardump=...` 导出 HAR。
你也可以直接在 `案件工作台 -> 流量证据` 里修改：

- `抓包监听地址`
- `抓包监听端口`

保存后，工作台会立即刷新当前生效的代理提示。对于自定义抓包命令，模板现在也支持：

- `{listen_host}`
- `{listen_port}`

后端通过环境变量 `APKHACKER_TRAFFIC_CAPTURE_COMMAND` 读取命令模板，模板里可以使用占位符：

- `{output_path}`：工作台为当前案件分配的 HAR 输出路径
- `{case_id}`：当前案件编号
- `{session_id}`：本次实时抓包会话编号

如果你只是想先体验整条链路，不想自己准备抓包脚本，可以直接使用仓库自带的 demo runner：

```bash
export APKHACKER_TRAFFIC_CAPTURE_COMMAND="uv run apk-hacker-demo-live-capture {output_path}"
npm run dev:tauri
```

启动后进入 `案件工作台 -> 流量证据`，点击“开始实时抓包”，再点击“停止实时抓包”，工作台会把 demo 生成的 HAR 自动导入到当前案件里。

如果你已经有 `mitmdump`，也可以直接不配任何环境变量，工作台会在 `流量证据` 面板里显示：

- `抓包引擎：内置 Mitmdump 已就绪（监听 0.0.0.0:8080）`
- `请把设备 HTTP/HTTPS 代理指向分析机 IP 的 8080 端口，停止后会自动导入 HAR。`
- `代理地址：分析机局域网 IP:8080`
- `安装地址：http://mitm.it`
- `证书路径：~/.mitmproxy/mitmproxy-ca-cert.cer`（首次启动后生成）

如果本机证书已经存在，工作台还会直接提供：

- `打开证书文件`
- `打开证书目录`
- `复制代理地址`
- `复制安装地址`
- `复制证书路径`
- `保存抓包参数`

这样你可以更快把 mitmproxy CA 装到测试设备上。

## 报告导出

工作台导出的 Markdown 报告现在会保留最近一次执行的关键语义，而不只是路径和事件数，包括：

- `Last Status`
- `Requested Mode`
- `Executed Backend`
- `Failure Code`
- `Failure Message`

同时，桌面工作台在导出失败时会直接显示中文错误提示，不会再把错误文案误当成“最近导出路径”。

如果你想接自己的抓包器，只要保证停止时能把 HAR 写到 `{output_path}` 即可。第一版的工作台默认展示：

- `实时抓包状态`
- `最近产物路径`
- `开始实时抓包 / 停止实时抓包`
- 已导入 HAR 的流量摘要

## 执行模式说明

- `Fake Backend`
  - 当前默认模式
  - 用于验证计划、脚本、日志存储和 GUI 交互
- `Real Device`
  - 目前是“命令型真实后端”骨架
  - 可以通过环境变量 `APKHACKER_REAL_BACKEND_COMMAND` 指向你自己的执行器脚本
  - 也可以不配置自定义命令，让工作台自动路由到当前可用的内置真实后端
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
npm run dev:tauri
```

仓库里也自带了一个演示执行器，方便本地先验证真实后端协议：

```bash
export APKHACKER_REAL_BACKEND_COMMAND="uv run apk-hacker-demo-real-backend"
npm run dev:tauri
```

如果你本机已经装好了 `adb`，也可以直接用仓库内置的设备探测 runner：

```bash
export APKHACKER_REAL_BACKEND_COMMAND="uv run apk-hacker-adb-probe-backend"
npm run dev:tauri
```

这个 runner 目前不会注入 Frida，但会把 `adb devices` 和设备 ABI 探测结果以真实事件的方式回传到工作台，用来验证本机到设备的桥接链路。

如果你已经有可用的 `frida-server` 二进制，并且设备已经 Root，可以先用内置的 `Frida Bootstrap` 预设或对应 runner 做一次自举：

先启动桌面工作台：

- 打开 `案件工作台 -> 执行控制台`
- 填写 `Device Serial` 和 `Frida Server Binary`
- 选择 `Frida Bootstrap` 预设并执行

或在 API / CLI 场景下传入：

```bash
uv run apk-hacker-cli \
  --sample /path/to/sample.apk \
  --device-serial serial-123 \
  --frida-server-binary /path/to/frida-server
```

对应的命令行 runner 是：

```bash
uv run apk-hacker-frida-bootstrap-backend
```

它会做这几件事：
- 枚举 `adb` 设备并选择目标序列号
- 读取设备 ABI
- 检查 Root 能力
- 检查 `frida-server` 是否已在运行
- 如未运行且提供了本地二进制，则自动 `push -> chmod -> start`

如果你在 GUI 或命令行里给了 `--frida-server-binary`，`Frida Session` 在首次 USB 连接失败时也会自动尝试一次同样的 bootstrap，然后再重试连接。

如果你本机已经装好了 `frida-tools`，也可以直接用仓库内置的 Frida 目标探测 runner：

```bash
export APKHACKER_REAL_BACKEND_COMMAND="uv run apk-hacker-frida-probe-backend"
npm run dev:tauri
```

这个 runner 会调用 `frida-ps -Uai`，并根据当前工作台里样本的包名回传目标可见性事件，适合先验证 `Real Device -> Frida -> 目标包识别` 这条最小链路。

如果你想继续往前验证一次最小注入探针，也可以使用：

先启动桌面工作台，然后在 `执行控制台` 中选择 `Frida Inject` 预设。

或在 API / CLI 场景下传入：

```bash
uv run apk-hacker-cli \
  --sample /path/to/sample.apk \
  --real-backend-command "uv run apk-hacker-frida-inject-backend"
```

这个 runner 会选取当前计划里第一份已渲染脚本，调用 `frida -U -f <package> -l <script>` 做一次短时注入探针，并把结果折叠成单条 `frida_injection` 事件。它当前更适合做链路验证，还不是长期会话采集器。
当你提供 `--frida-server-binary` 时，`Frida Inject` 也会在执行注入前自动做一次 bootstrap；如果当前样本 APK 还没有安装到目标设备上，它还会先尝试 `adb install -r` 自动补装，再继续进行最小注入探针。

如果你已经安装了 Python 版 `frida` 模块，并且想把脚本消息真正回流到工作台，可以使用：

先启动桌面工作台，然后在 `执行控制台` 中选择 `Frida Session` 预设。

或在 API / CLI 场景下传入：

```bash
uv run apk-hacker-cli \
  --sample /path/to/sample.apk \
  --real-backend-command "uv run apk-hacker-frida-session-backend"
```

这个 runner 会通过 Python `frida` API 执行 `spawn -> attach -> load -> resume`，并把脚本里的 `send(...)` 消息转成结构化事件。当前版本只做最小会话，不负责长期保持连接或复杂的多脚本编排。
当前已经支持按 `Hook Plan` 顺序依次加载多份脚本，并在事件里附带来源脚本名，方便在工作台日志中区分不同脚本的输出。
如果会话期间没有收到脚本消息，会回传 `frida_session_timeout`；如果连接设备、加载脚本或恢复进程失败，会回传 `frida_session_error`，便于在工作台里区分“链路不通”和“脚本本身没产生日志”。
当你提供 `--frida-server-binary` 时，`Frida Session` 还会在第一次 `get_usb_device()` 失败后自动尝试 bootstrap，再重试一次 USB 连接。
如果当前样本 APK 尚未安装到目标设备，`Frida Session` 还会在会话开始前尝试用 `adb install -r` 自动补装；只有真正发生安装或安装失败时，才会额外回传 `app_install_status` / `app_install_error` 事件。
如果 `spawn` 当前目标包失败，`Frida Session` 还会自动尝试 `attach(package)` 方式降级接入，并回传 `frida_session_status / attach_fallback`，这样对“只能附加、不能直接拉起”的目标更友好。

## 目录说明

- `src/apk_hacker/static_engine/`
  - 第一方静态分析引擎与 JADX 导出契约
- `src/apk_hacker/application/services/`
  - 静态适配、Hook 计划、自定义脚本、任务服务
- `src/apk_hacker/infrastructure/execution/`
  - fake / real 执行后端抽象
- `src/apk_hacker/interfaces/gui_pyqt/`
  - 旧入口兼容 shim，仅保留迁移提示与参数面
- `tests/`
  - 单元测试、集成测试、Web/Tauri 回归测试

## 测试

```bash
uv run pytest -q
```

当前分支验证结果为：

- Python：`177 passed, 8 skipped`
- Web：`53 passed`
- `cargo check --manifest-path src-tauri/Cargo.toml`
- `npm run build:tauri -- --no-bundle`

## 注意事项

- 当前版本更适合本地研究和工作流验证，不适合作为完整恶意样本动态分析平台直接投入生产使用
- 请在隔离环境中处理可疑 APK
- `Real Device` 相关能力仍在持续补完，当前不要把它当成已完成特性
