# Android APK 动态分析工具 — 项目完整规格说明

> 供 Claude Code 导入使用。本文档涵盖架构设计、模块职责、实施路线和关键工程决策。

------

## 一、项目背景与目标

### 现有基础

- 已有静态分析 Skill（`android-malware-analysis`），包含完整的 6 阶段 Python 管线
- 静态管线产出结构化 JSON（`analysis.json`、`callback-config.json`），是动态分析的天然输入
- Skill 明确边界：不执行样本、不接触真实 C2、不做动态操作

### 项目目标

在现有静态 Skill 基础上，构建配套的动态分析工具，实现：

1. **脱壳**：处理主流商业加固
2. **动态 Hook**：Frida 脚本自动生成与注入
3. **流量分析**：SSL Unpinning + 抓包 + AI 协议识别
4. **代码语义分析**：AI 精读 jadx 导出的一方代码
5. **跨平台可用**：分析端 Docker 化，设备端统一接口抽象

### 核心设计原则

- **离线可用**：无 API Key 时工具仍可运行，依赖模板引擎和人工经验
- **AI 增强**：有 API 时 AI 接管语义理解、脚本生成、日志解析
- **渐进实现**：统一设备接口层支持多后端逐步扩展
- **不重复造轮子**：静态分析完全复用现有 Skill 脚本

------

## 二、三层架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3：AI 增强层（需 API / 联网）                          │
│  Claude API 或 Ollama 本地模型                                │
│  职责：语义理解、精准脚本生成、日志解析、流量协议识别           │
├─────────────────────────────────────────────────────────────┤
│  Layer 2：离线智能层（完全离线）                               │
│  模板引擎 + 规则匹配                                          │
│  职责：特征 → 模板选择 → 填充 → 可用脚本；结构化日志存储       │
├─────────────────────────────────────────────────────────────┤
│  Layer 1：核心工具层（完全离线）                               │
│  jadx / apktool / Frida / Objection / ADB / mitmproxy       │
│  职责：解包反编译、特征提取、设备管理、注入、抓包               │
└─────────────────────────────────────────────────────────────┘
```

### 各层边界说明

| 任务                            | 所在层  | 是否需要 AI |
| ------------------------------- | ------- | ----------- |
| APK 解包 / 反编译               | Layer 1 | 否          |
| 特征提取（IP/域名/SDK/加固）    | Layer 1 | 否          |
| 环境检测（Root/Frida/SELinux）  | Layer 1 | 否          |
| Objection 联动                  | Layer 1 | 否          |
| 标准模板 Hook（okhttp3/AES 等） | Layer 2 | 否          |
| 离线规则匹配生成脚本            | Layer 2 | 否          |
| 结构化日志 SQLite 存储          | Layer 2 | 否          |
| 混淆类名语义推断                | Layer 3 | 是          |
| 复杂调用链 Hook 点选择          | Layer 3 | 是          |
| jadx 代码语义精读               | Layer 3 | 是          |
| 流量协议识别                    | Layer 3 | 是          |
| 动态 Frida 脚本生成（混淆场景） | Layer 3 | 是          |

------

## 三、与现有 Skill 的集成方式

### 关键决策：Skill 脚本直接调用，不经过 AI

```
静态阶段（直接跑 Skill Python 脚本）
  investigate_android_app.py → analysis.json + callback-config.json
                ↓ 结构化 JSON 作为上下文
动态阶段（新增模块消费 JSON）
  ├── ai/code_analyzer.py    读 jadx 一方代码 → AI 语义分析
  ├── ai/script_generator.py 读 analysis.json → 生成 Frida 脚本
  └── ai/traffic_analyzer.py 读流量 dump → AI 协议识别
```

### Skill 输出 → 动态分析的映射关系

```python
# analysis.json 中已有的字段，直接作为动态分析输入
{
  "first_party_prefixes": ["com.evil.app"],   # → 限定 AI 代码分析范围
  "framework": "uniapp",                       # → 选择对应 Hook 模板
  "crypto": {"AES": true, "CBC": true},        # → 生成加密监控脚本
  "callback_config": {
    "code_inference": {
      "classes": ["com.evil.NetClient"],        # → 精准 Hook 目标
      "endpoints": ["http://1.2.3.4/api"]      # → mitmproxy 过滤规则
    }
  },
  "packer": "com.tencent.legu",               # → 选择脱壳方案
  "permissions": ["READ_SMS", "CAMERA"]        # → Hook 敏感 API
}
```

------

## 四、完整目录结构

```
android-analyzer/
│
├── skill/                                   # 现有 Skill（只读，不修改）
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── investigate_android_app.py       # 静态管线主入口
│   │   ├── analyze_package.py               # IOC 预检
│   │   ├── skill_ledger.py                  # 经验台账
│   │   └── android_tooling.py              # 工具检测
│   └── references/
│       ├── workflow.md
│       ├── decision-gates.md
│       ├── heuristics.md
│       ├── gotchas.md
│       ├── ledger.md
│       ├── library-triage.md
│       ├── reporting.md
│       └── validation.md
│
├── core/                                    # Layer 1：核心工具层
│   ├── device_manager.py                    # 统一设备接口层（关键）
│   ├── frida_manager.py                     # Frida Server 部署、注入、消息处理
│   ├── objection_bridge.py                  # Objection 命令封装
│   ├── traffic_capture.py                   # mitmproxy / Reqable 联动
│   ├── unpacker.py                          # 脱壳流程编排
│   └── env_checker.py                       # 设备环境检测
│
├── rules/                                   # Layer 2：离线智能层
│   ├── rule_engine.py                       # 规则匹配引擎
│   └── rules.yaml                           # 特征规则定义
│
├── templates/                               # Frida 脚本模板库（Jinja2）
│   ├── ssl/
│   │   ├── okhttp3_unpin.js
│   │   ├── webview_unpin.js
│   │   └── trustmanager_hook.js
│   ├── crypto/
│   │   ├── digest_monitor.js                # MD5/SHA 监控
│   │   ├── cipher_monitor.js                # AES/DES/RSA 监控
│   │   └── hmac_monitor.js
│   ├── anti_detection/
│   │   ├── root_bypass.js
│   │   ├── frida_detect_bypass.js
│   │   └── emulator_bypass.js
│   └── generic/
│       ├── method_hook.js                   # 通用方法 Hook（参数化）
│       ├── constructor_hook.js
│       └── native_hook.js                   # JNI/Native Hook
│
├── ai/                                      # Layer 3：AI 增强层
│   ├── script_generator.py                  # JSON → Frida 脚本（在线+离线）
│   ├── code_analyzer.py                     # jadx 源码 → AI 语义分析（新增核心能力）
│   ├── traffic_analyzer.py                  # 流量 dump → AI 协议识别（新增核心能力）
│   ├── claude_client.py                     # Claude API 封装
│   └── ollama_client.py                     # 本地模型（OpenAI 兼容接口）
│
├── sandbox/                                 # 云沙箱对接
│   ├── virustotal.py
│   └── joesandbox.py
│
├── report/
│   ├── merger.py                            # 静态 + 动态报告合并
│   └── db.py                               # SQLite 日志存储
│
├── orchestrator.py                          # 主入口：串联所有阶段
├── config.yaml                              # 配置文件（模式切换）
├── Dockerfile                               # 分析端容器化
└── docker-compose.yml                       # 含 MobSF / redroid 可选服务
```

------

## 五、统一设备接口层（最关键的工程组件）

### 抽象类设计

```python
# core/device_manager.py
from abc import ABC, abstractmethod

class DeviceBackend(ABC):
    """所有设备后端实现同一接口，上层调用方无需关心底层差异"""

    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def install_apk(self, path: str) -> bool: ...

    @abstractmethod
    def push_frida_server(self) -> bool: ...

    @abstractmethod
    def start_app(self, package: str) -> bool: ...

    @abstractmethod
    def inject_script(self, js: str) -> "Session": ...

    @abstractmethod
    def get_logcat(self) -> "Iterator[str]": ...

    @abstractmethod
    def get_arch(self) -> str: ...  # arm64-v8a / x86_64 / armeabi-v7a

    @abstractmethod
    def is_rooted(self) -> bool: ...

class RealDevice(DeviceBackend): ...      # ADB 真机（Phase 1 实现）
class RedroidDevice(DeviceBackend): ...   # Docker Android（Phase 3 实现）
class AVDDevice(DeviceBackend): ...       # Android 模拟器（Phase 3 实现）
class MobSFBackend(DeviceBackend): ...    # MobSF API（Phase 3 实现）
```

### 后端能力对比

| 后端          | 一键启动    | ARM 兼容   | Hook 能力 | 推荐场景       |
| ------------- | ----------- | ---------- | --------- | -------------- |
| RealDevice    | 需 ADB 连接 | 完整       | 完整      | 主力分析环境   |
| RedroidDevice | Docker      | 需 KVM     | 完整      | 无真机备用     |
| AVDDevice     | 脚本化      | x86 兼容层 | 完整      | CI/CD 批量分析 |
| MobSFBackend  | API         | 依赖设备   | 有限      | 快速预分析     |

### 实施策略

- Phase 1 只实现 `RealDevice`，接口设计好后，后续后端只是新增实现
- 配置文件 `device_backend: auto` 时自动检测可用后端

------

## 六、Frida 脚本生成流程

### 离线模式（模板引擎）

```python
# rules/rule_engine.py
def generate_scripts_offline(analysis_json: dict) -> list[str]:
    scripts = []
    deps = analysis_json.get("dependencies", [])
    crypto = analysis_json.get("crypto", {})
    packer = analysis_json.get("packer", "")

    # 规则 1：检测到 okhttp3 → SSL Unpinning
    if any("okhttp3" in d for d in deps):
        scripts.append(render("ssl/okhttp3_unpin.js"))

    # 规则 2：检测到加密类 → 注入监控
    if crypto.get("AES") or crypto.get("Cipher"):
        scripts.append(render("crypto/cipher_monitor.js"))

    # 规则 3：检测到加固 → 选择脱壳脚本
    if "legu" in packer or "jiagu" in packer:
        scripts.append(render("anti_detection/frida_detect_bypass.js"))

    # 规则 4：用户指定函数 → 通用 Hook 模板
    if analysis_json.get("target_method"):
        scripts.append(render("generic/method_hook.js", **analysis_json["target_method"]))

    return scripts
```

### AI 模式（联网）

```python
# ai/script_generator.py
def generate_scripts_ai(analysis_json: dict, code_context: str, ai_client) -> list[str]:
    prompt = f"""
    目标 APK 静态分析结果：
    - 框架：{analysis_json['framework']}
    - 一方包前缀：{analysis_json['first_party_prefixes']}
    - 已发现加密模式：{analysis_json['crypto']}
    - 回连候选类：{analysis_json['callback_config']['code_inference']['classes']}
    - 关键代码片段：{code_context}

    请生成 Frida Hook 脚本，要求：
    1. 使用实际类名和方法签名（从代码片段提取）
    2. 处理方法重载
    3. 打印参数、返回值和调用堆栈
    4. 输出统一 JSON 格式供后续解析
    """
    return ai_client.generate(prompt)
```

### 通用方法 Hook 模板（generic/method_hook.js）

```javascript
// 参数：{{className}} {{methodName}} {{paramTypes}}
Java.perform(function() {
    var TargetClass = Java.use("{{className}}");

    TargetClass["{{methodName}}"].overload({{paramTypes}}).implementation = function({{params}}) {
        var args_array = [{{params}}].map(function(a) {
            return a !== null ? a.toString() : "null";
        });

        send(JSON.stringify({
            "hook_type": "method",
            "class": "{{className}}",
            "method": "{{methodName}}",
            "args": args_array,
            "return": null,  // 执行后填充
            "stack": Thread.backtrace(this.context, Backtracer.ACCURATE)
                           .map(DebugSymbol.fromAddress).join('\n')
        }));

        var ret = this["{{methodName}}"].call(this, {{params}});
        send(JSON.stringify({
            "hook_type": "method_return",
            "class": "{{className}}",
            "method": "{{methodName}}",
            "return": ret !== null ? ret.toString() : "null"
        }));

        return ret;
    };
});
```

------

## 七、AI 代码分析模块（新增核心能力）

### 设计原则

利用 Skill 已输出的 `first_party_prefixes` 限定分析范围，避免超出上下文窗口。

```python
# ai/code_analyzer.py
def analyze_code(jadx_dir: str, analysis_json: dict, ai_client) -> dict:
    # Step 1：从静态分析结果提取焦点
    prefixes = analysis_json["first_party_prefixes"]
    callback_classes = analysis_json["callback_config"]["code_inference"]["classes"]
    crypto_hits = analysis_json["crypto"]

    # Step 2：只读一方代码 + 回连链路上的类（控制上下文）
    target_files = collect_targeted_sources(
        jadx_dir,
        prefixes=prefixes,
        class_hints=callback_classes,
        max_files=20,
        max_tokens=60000
    )

    # Step 3：分批送 AI 分析
    insights = []
    for chunk in chunk_files(target_files):
        result = ai_client.analyze(
            system="你是 Android 恶意软件逆向工程师，分析反编译后的 Java 代码",
            user=f"""
            代码来自可疑 APK，框架：{analysis_json['framework']}
            已发现加密模式：{crypto_hits}
            请分析：
            1. 数据采集逻辑（哪些敏感数据被读取）
            2. 加密/编码流程（密钥来源、算法参数）
            3. 回连逻辑（URL 构造方式、请求格式）
            4. 推荐的 Frida Hook 点（类名 + 方法签名）

            代码内容：
            {chunk}
            """
        )
        insights.append(result)

    return merge_insights(insights)
```

------

## 八、AI 流量分析模块（新增核心能力）

### 两种模式

**模式 1：离线批量分析（推荐先实现）**

```python
# ai/traffic_analyzer.py
def analyze_traffic_batch(har_file: str, callback_candidates: list, ai_client) -> dict:
    flows = load_har(har_file)

    # 用已知 C2 候选过滤
    suspicious = [f for f in flows
                  if any(c in f.url for c in callback_candidates)]

    results = []
    for flow in suspicious:
        result = ai_client.analyze(f"""
        HTTP 流量分析，请识别：
        1. 请求体编码方式（是否自定义加密）
        2. 数据字段语义（设备指纹/OTP/位置等）
        3. 与 Frida Hook 明文对比（如有）

        请求：{flow.request_body}
        响应：{flow.response_body}
        """)
        results.append(result)

    return summarize_traffic_analysis(results)
```

**模式 2：实时 Hook（mitmproxy addon）**

```python
class MalwareTrafficAddon:
    def response(self, flow):
        if self.is_suspicious(flow):
            # 异步送 AI，不阻塞流量
            asyncio.create_task(self.ai_analyze_async(flow))

    def is_suspicious(self, flow) -> bool:
        return any(c in flow.request.url for c in self.c2_candidates)
```

------

## 九、结构化日志规范

所有 Frida Hook 脚本统一输出 JSON，Python 层解析存 SQLite。

```json
{
  "timestamp": "2025-01-01T00:00:00Z",
  "session_id": "abc123",
  "package": "com.evil.app",
  "hook_type": "crypto",
  "class": "com.evil.Encrypt",
  "method": "aesEncrypt",
  "args": ["plaintext_data", "hardcoded_key_16bytes"],
  "return": "base64_ciphertext==",
  "stack": "com.evil.NetClient.sendData:142\ncom.evil.MainActivity.onButton:89"
}
# report/db.py
class HookLogDB:
    def insert(self, event: dict): ...
    def query_crypto(self, session_id: str) -> list: ...
    def correlate_key_plaintext(self, session_id: str) -> list: ...
    def export_for_ai(self, session_id: str) -> str: ...
```

------

## 十、主编排器

```python
# orchestrator.py
def run_full_analysis(apk_path: str, config: Config) -> AnalysisResult:

    # ── 阶段 A：静态分析（调用 Skill 脚本）──────────────────────
    static = run_static_pipeline(apk_path, config.output_dir)
    # 产出：analysis.json, callback-config.json, report.md, report.docx

    # ── 阶段 B1：AI 代码语义分析 ────────────────────────────────
    code_insights = None
    if config.ai_enabled and static.jadx_dir:
        code_insights = ai.analyze_code(
            jadx_dir=static.jadx_dir,
            analysis=static.analysis_json
        )

    # ── 阶段 B2：生成 Frida 脚本 ────────────────────────────────
    frida_scripts = generate_frida_scripts(
        analysis=static,
        code_insights=code_insights,
        mode="ai" if config.ai_enabled else "offline"
    )

    # ── 阶段 B3：动态分析 ────────────────────────────────────────
    dynamic_result = None
    with device_manager.get_backend(config) as device:
        if config.unpack and static.packer:
            device.unpack(apk_path)  # 脱壳

        device.install_apk(apk_path)
        session = device.inject_frida(frida_scripts)
        traffic = device.start_capture(
            c2_hints=static.callback_candidates,
            ssl_unpin=True
        )
        # 运行应用，等待数据
        device.start_app(static.package)
        hook_logs = session.collect_logs(timeout=config.capture_timeout)

    # ── 阶段 B4：AI 分析动态结果 ────────────────────────────────
    dynamic_report = None
    if config.ai_enabled:
        dynamic_report = ai.analyze_traffic(
            traffic_dump=traffic,
            frida_logs=hook_logs,
            static_context=static
        )

    # ── 阶段 B5：合并报告 ────────────────────────────────────────
    return merge_reports(static.report, dynamic_report)
```

------

## 十一、配置文件

```yaml
# config.yaml
mode: offline          # offline | ai_enhanced | full_auto
api_key: ""            # 空则自动降级到 offline
ai_model: claude-sonnet-4-20250514

device_backend: auto   # auto | real | redroid | avd | mobsf
capture_timeout: 120   # 秒

frida:
  auto_detect_arch: true
  server_version: latest
  server_path: ./frida-server

unpack: false          # 是否执行脱壳（加固样本开启）

offline_rules:
  ssl_libs: [okhttp3, retrofit, volley, conscrypt]
  crypto_classes: [MessageDigest, Cipher, Mac, KeyGenerator]
  root_check_patterns: [su, RootBeer, SafetyNet]

sandbox:
  provider: virustotal  # virustotal | joesandbox | none
  api_key: ""

local_llm:
  enabled: false
  model: qwen2.5-coder:7b
  endpoint: http://localhost:11434

output:
  report_lang: zh-CN
  include_noise_log: true
  sqlite_path: ./logs/hooks.db
```

------

## 十二、Docker 环境

```dockerfile
# Dockerfile — 分析端（不包含 Android 运行环境）
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    default-jre-headless \
    adb \
    wget unzip

# 安装 jadx
RUN wget https://github.com/skylot/jadx/releases/latest/download/jadx-1.5.0.zip \
    && unzip jadx-*.zip -d /opt/jadx

# 安装 apktool
RUN wget https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_2.9.3.jar \
    -O /opt/apktool.jar

# 安装 frida-tools
RUN pip install frida-tools mitmproxy jinja2 requests

COPY . /app
WORKDIR /app

ENTRYPOINT ["python", "orchestrator.py"]
# docker-compose.yml
services:
  analyzer:
    build: .
    volumes:
      - ./samples:/samples
      - ./output:/output
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

  # 可选：无真机时使用
  redroid:
    image: redroid/redroid:12.0.0-latest
    privileged: true
    ports:
      - "5555:5555"

  # 可选：快速预分析
  mobsf:
    image: opensecurity/mobile-security-framework-mobsf
    ports:
      - "8000:8000"
```

------

## 十三、实施路线图

### Phase 1（2-3 周）— 基础可用

- [ ] `core/device_manager.py`：`DeviceBackend` 抽象类 + `RealDevice` 实现
- [ ] `core/frida_manager.py`：自动检测设备 ABI，下载对应 frida-server，注入脚本
- [ ] `core/objection_bridge.py`：封装 `android sslpinning disable`、`android hooking watch class` 等命令
- [ ] `report/db.py`：SQLite 结构化日志
- [ ] `templates/generic/method_hook.js`：通用 Hook 模板
- [ ] `templates/ssl/okhttp3_unpin.js`：SSL Unpinning
- [ ] `orchestrator.py`：骨架，串联静态 Skill + 基础动态流程
- [ ] `Dockerfile`：分析端镜像

### Phase 2（2-3 周）— 离线智能

- [ ] `rules/rule_engine.py`：特征匹配 → 模板选择
- [ ] `templates/crypto/`：完整加密监控模板组
- [ ] `templates/anti_detection/`：Root/Frida/模拟器检测绕过
- [ ] `core/traffic_capture.py`：mitmproxy 联动 + 证书自动安装
- [ ] `core/unpacker.py`：FART / BlackDex 脱壳编排
- [ ] `sandbox/virustotal.py`：预分析接入
- [ ] `core/env_checker.py`：完整环境评分

### Phase 3（持续迭代）— AI 增强

- [ ] `ai/code_analyzer.py`：jadx 代码 AI 语义分析（优先，最核心新能力）
- [ ] `ai/script_generator.py`：AI 精准 Frida 脚本生成
- [ ] `ai/traffic_analyzer.py`：流量 AI 协议识别
- [ ] `ai/ollama_client.py`：本地模型离线备用
- [ ] `core/device_manager.py`：新增 `RedroidDevice` / `AVDDevice` 后端
- [ ] MobSF API 对接
- [ ] 反 Frida 检测对抗（frida-gadget + LSPosed 方案）
- [ ] 动态 URL 构造识别（补充 `code_inference` 的正则局限）

------

## 十四、关键工程注意事项

### Frida Server 部署

```python
# 必须自动匹配设备 ABI，否则 frida-server 无法运行
def push_frida_server(device):
    arch = device.get_arch()  # arm64-v8a / x86_64
    server = download_frida_server(arch)
    device.adb_push(server, "/data/local/tmp/frida-server")
    device.adb_shell("chmod 755 /data/local/tmp/frida-server")
    device.adb_shell("/data/local/tmp/frida-server &")
```

### 方法重载处理

```javascript
// Hook 时必须处理重载，否则只 Hook 第一个签名
var methods = TargetClass["{{methodName}}"].overloads;
methods.forEach(function(overload) {
    overload.implementation = function() { ... };
});
```

### Android 7+ 证书信任

```
Android 7+ 不信任用户证书
解决方案（按难度排序）：
1. LSPosed + TrustMeAlready 模块（推荐）
2. 将证书写入系统证书目录（需 Root）
3. Frida Hook TrustManager（代码级绕过）
```

### 反 Frida 检测

```
常见检测手段：
1. 进程名检测（frida-server）→ 重命名绕过
2. 端口检测（27042）→ 修改默认端口
3. /proc/maps 检测 → frida-gadget 注入模式
4. ptrace 检测 → LSPosed 隐藏

推荐方案：Magisk + Shamiko + LSPosed，而不是纯 Frida 对抗
```

------

## 十五、与现有 Skill 的分工总结

| 功能                  | 归属           | 实现方式                     |
| --------------------- | -------------- | ---------------------------- |
| APK 解包 / 反编译     | 现有 Skill     | `investigate_android_app.py` |
| 静态特征提取          | 现有 Skill     | `investigate_android_app.py` |
| 双阶段回连分析        | 现有 Skill     | `investigate_android_app.py` |
| 中文静态分析报告      | 现有 Skill     | `report.md` / `report.docx`  |
| 经验台账              | 现有 Skill     | `skill_ledger.py`            |
| 设备管理 + Frida 注入 | 本项目 Layer 1 | `core/`                      |
| SSL Unpinning + 抓包  | 本项目 Layer 1 | `core/traffic_capture.py`    |
| 脱壳                  | 本项目 Layer 1 | `core/unpacker.py`           |
| 模板 Frida 脚本生成   | 本项目 Layer 2 | `rules/` + `templates/`      |
| 结构化日志            | 本项目 Layer 2 | `report/db.py`               |
| 代码语义 AI 分析      | 本项目 Layer 3 | `ai/code_analyzer.py`        |
| 流量 AI 识别          | 本项目 Layer 3 | `ai/traffic_analyzer.py`     |
| AI 精准脚本生成       | 本项目 Layer 3 | `ai/script_generator.py`     |
| 动态 + 静态合并报告   | 本项目         | `report/merger.py`           |