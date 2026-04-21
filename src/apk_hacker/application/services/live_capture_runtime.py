from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import shutil

from apk_hacker.domain.models.environment import GuidanceStep


TRAFFIC_CAPTURE_COMMAND_ENV = "APKHACKER_TRAFFIC_CAPTURE_COMMAND"
TRAFFIC_CAPTURE_OUTPUT_PATH_ENV = "APKHACKER_TRAFFIC_OUTPUT_PATH"
TRAFFIC_CAPTURE_PREVIEW_PATH_ENV = "APKHACKER_TRAFFIC_PREVIEW_PATH"
TRAFFIC_CAPTURE_CASE_ID_ENV = "APKHACKER_TRAFFIC_CASE_ID"
TRAFFIC_CAPTURE_SESSION_ID_ENV = "APKHACKER_TRAFFIC_SESSION_ID"
TRAFFIC_CAPTURE_LISTEN_HOST_ENV = "APKHACKER_TRAFFIC_LISTEN_HOST"
TRAFFIC_CAPTURE_LISTEN_PORT_ENV = "APKHACKER_TRAFFIC_LISTEN_PORT"
DEFAULT_LIVE_CAPTURE_LISTEN_HOST = "0.0.0.0"
DEFAULT_LIVE_CAPTURE_LISTEN_PORT = 8080
DEFAULT_MITMPROXY_CONF_DIRNAME = ".mitmproxy"
DEFAULT_MITMPROXY_CERT_FILENAME = "mitmproxy-ca-cert.cer"
DEFAULT_LIVE_CAPTURE_PREVIEW_SUFFIX = ".preview.ndjson"


@dataclass(frozen=True, slots=True)
class LiveCaptureRuntimeAvailability:
    available: bool
    source: str
    detail: str
    listen_host: str
    listen_port: int
    help_text: str | None
    proxy_address_hint: str | None
    install_url: str | None
    certificate_path: str | None
    certificate_directory_path: str | None
    certificate_exists: bool
    certificate_help_text: str | None
    command_template: str | None
    proxy_ready: bool
    certificate_ready: bool
    https_capture_ready: bool
    setup_steps: tuple[GuidanceStep, ...]
    proxy_steps: tuple[GuidanceStep, ...]
    certificate_steps: tuple[GuidanceStep, ...]
    recommended_actions: tuple[str, ...]


def _guidance_step(key: str, title: str, detail: str, *, emphasis: str = "info") -> GuidanceStep:
    return GuidanceStep(key=key, title=title, detail=detail, emphasis=emphasis)


def default_mitmproxy_cert_root() -> Path:
    return Path.home() / DEFAULT_MITMPROXY_CONF_DIRNAME


def normalize_live_capture_listen_host(value: str | None) -> str:
    normalized = (value or "").strip()
    return normalized or DEFAULT_LIVE_CAPTURE_LISTEN_HOST


def normalize_live_capture_listen_port(value: str | int | None) -> int:
    if isinstance(value, int):
        candidate = value
    else:
        normalized = str(value or "").strip()
        if normalized == "":
            return DEFAULT_LIVE_CAPTURE_LISTEN_PORT
        try:
            candidate = int(normalized)
        except ValueError:
            return DEFAULT_LIVE_CAPTURE_LISTEN_PORT
    if 1 <= candidate <= 65535:
        return candidate
    return DEFAULT_LIVE_CAPTURE_LISTEN_PORT


def build_live_capture_preview_path(output_path: Path) -> Path:
    return output_path.with_suffix(DEFAULT_LIVE_CAPTURE_PREVIEW_SUFFIX)


def mitmdump_live_preview_helper_path() -> Path:
    return Path(__file__).resolve().parents[2] / "tools" / "mitmdump_live_preview.py"


def build_builtin_mitmdump_command_template(
    *,
    listen_host: str = DEFAULT_LIVE_CAPTURE_LISTEN_HOST,
    listen_port: int = DEFAULT_LIVE_CAPTURE_LISTEN_PORT,
) -> str:
    helper_path = shlex.quote(str(mitmdump_live_preview_helper_path()))
    return (
        "mitmdump "
        f"-s {helper_path} "
        "--set block_global=false "
        f"--listen-host {listen_host} "
        f"--listen-port {listen_port} "
        "--set hardump={output_path}"
    )


def resolve_live_capture_runtime(
    *,
    command_template: str | None = None,
    resolver: Callable[[str], str | None] | None = None,
    listen_host: str | None = DEFAULT_LIVE_CAPTURE_LISTEN_HOST,
    listen_port: str | int | None = DEFAULT_LIVE_CAPTURE_LISTEN_PORT,
    cert_root: Path | None = None,
) -> LiveCaptureRuntimeAvailability:
    resolved_listen_host = normalize_live_capture_listen_host(listen_host)
    resolved_listen_port = normalize_live_capture_listen_port(listen_port)
    normalized_template = (command_template or os.getenv(TRAFFIC_CAPTURE_COMMAND_ENV, "")).strip()
    if normalized_template:
        return LiveCaptureRuntimeAvailability(
            available=True,
            source="configured_command",
            detail="已配置自定义抓包命令",
            listen_host=resolved_listen_host,
            listen_port=resolved_listen_port,
            help_text="启动后会在停止时把抓包产物自动导入当前案件。",
            proxy_address_hint=None,
            install_url=None,
            certificate_path=None,
            certificate_directory_path=None,
            certificate_exists=False,
            certificate_help_text=None,
            command_template=normalized_template,
            proxy_ready=True,
            certificate_ready=False,
            https_capture_ready=False,
            setup_steps=(
                _guidance_step(
                    "capture-command",
                    "确认抓包命令",
                    "确认自定义抓包命令会把产物写到工作区，并且退出时不会丢失 HAR。",
                    emphasis="required",
                ),
                _guidance_step(
                    "device-proxy",
                    "配置设备代理",
                    "先在设备侧配置 HTTP / HTTPS 代理，再回到这里启动实时抓包。",
                    emphasis="required",
                ),
                _guidance_step(
                    "post-capture-review",
                    "检查导入结果",
                    "停止抓包后检查导入结果，再决定是否把网络 Hook 建议加入计划。",
                    emphasis="recommended",
                ),
            ),
            proxy_steps=(
                _guidance_step(
                    "proxy-bind",
                    "核对监听地址",
                    "确保自定义命令的监听地址和这里保存的主机/端口一致。",
                    emphasis="required",
                ),
                _guidance_step(
                    "proxy-apply",
                    "设置设备代理",
                    f"把测试设备 HTTP / HTTPS 代理指向分析机可达地址的 {resolved_listen_port} 端口。",
                    emphasis="required",
                ),
            ),
            certificate_steps=(
                _guidance_step(
                    "custom-cert-check",
                    "确认抓包证书来源",
                    "如果你依赖 HTTPS 解密，请确认自定义抓包链路已提供可安装证书。",
                    emphasis="recommended",
                ),
                _guidance_step(
                    "custom-cert-record",
                    "记录证书安装方式",
                    "没有自动安装入口时，可在工作台里手动记录证书路径和安装方式。",
                    emphasis="recommended",
                ),
            ),
            recommended_actions=(
                "优先复现登录、注册、心跳、上报、消息拉取等网络动作。",
                "如果请求仍然是 TLS 明文不可见，优先把 SSL / HTTPS 相关 Hook 建议加入计划。",
            ),
        )

    resolved_binary = (resolver or shutil.which)("mitmdump")
    if resolved_binary:
        resolved_cert_root = cert_root or default_mitmproxy_cert_root()
        certificate_path = resolved_cert_root / DEFAULT_MITMPROXY_CERT_FILENAME
        certificate_exists = certificate_path.exists()
        return LiveCaptureRuntimeAvailability(
            available=True,
            source="builtin_mitmdump",
            detail=f"内置 Mitmdump 已就绪（监听 {resolved_listen_host}:{resolved_listen_port}）",
            listen_host=resolved_listen_host,
            listen_port=resolved_listen_port,
            help_text=(
                f"请把设备 HTTP/HTTPS 代理指向分析机 IP 的 {resolved_listen_port} 端口，"
                "停止后会自动导入 HAR。"
            ),
            proxy_address_hint=f"分析机局域网 IP:{resolved_listen_port}",
            install_url="http://mitm.it",
            certificate_path=str(certificate_path.resolve()),
            certificate_directory_path=str(resolved_cert_root.resolve()),
            certificate_exists=certificate_exists,
            certificate_help_text=(
                "可直接把该证书安装到测试设备，或在设备浏览器访问 http://mitm.it。"
                if certificate_exists
                else "首次启动内置 Mitmdump 后会在本机生成证书，也可以在设备浏览器访问 http://mitm.it 下载。"
            ),
            command_template=build_builtin_mitmdump_command_template(
                listen_host=resolved_listen_host,
                listen_port=resolved_listen_port,
            ),
            proxy_ready=True,
            certificate_ready=True,
            https_capture_ready=True,
            setup_steps=(
                _guidance_step(
                    "builtin-proxy",
                    "设置代理",
                    f"先把测试设备 HTTP / HTTPS 代理指向分析机局域网 IP 的 {resolved_listen_port} 端口。",
                    emphasis="required",
                ),
                _guidance_step(
                    "builtin-cert",
                    "安装抓包证书",
                    "在设备浏览器访问 http://mitm.it，或直接安装工作台给出的 mitm 证书。",
                    emphasis="required",
                ),
                _guidance_step(
                    "builtin-replay",
                    "复现关键网络动作",
                    "开始抓包后优先复现登录、上报、证书校验或长连接建立等关键动作。",
                    emphasis="recommended",
                ),
            ),
            proxy_steps=(
                _guidance_step(
                    "proxy-host",
                    "使用局域网 IP",
                    f"代理主机建议使用分析机局域网 IP，端口固定为 {resolved_listen_port}。",
                    emphasis="required",
                ),
                _guidance_step(
                    "proxy-network",
                    "确认网络可达",
                    "如果设备和分析机不在同一网段，先确认路由或热点转发可达。",
                    emphasis="recommended",
                ),
            ),
            certificate_steps=(
                _guidance_step(
                    "certificate-verify",
                    "验证证书解密",
                    "安装 mitm 证书后，优先验证浏览器或 WebView 请求是否能正常解密。",
                    emphasis="recommended",
                ),
                _guidance_step(
                    "certificate-followup",
                    "处理 HTTPS 拒绝",
                    (
                        "若目标应用仍拒绝 HTTPS，请优先启用 SSL Unpinning / TrustManager 相关 Hook。"
                        if certificate_exists
                        else "证书文件还未生成，先启动一次内置抓包或访问 http://mitm.it 再继续。"
                    ),
                    emphasis="recommended",
                ),
            ),
            recommended_actions=(
                "优先接受网络、HTTPS、SSL 相关 Hook 建议，再开始复现关键请求。",
                "抓到高优流量后，结合 Hook 工作台查看对应类和方法，补齐明文链路。",
            ),
        )

    return LiveCaptureRuntimeAvailability(
        available=False,
        source="unavailable",
        detail="未配置抓包命令，且未检测到 mitmdump。",
        listen_host=resolved_listen_host,
        listen_port=resolved_listen_port,
        help_text="可以先设置 APKHACKER_TRAFFIC_CAPTURE_COMMAND，或在本机安装 mitmdump 后重试。",
        proxy_address_hint=None,
        install_url=None,
        certificate_path=None,
        certificate_directory_path=None,
        certificate_exists=False,
        certificate_help_text=None,
        command_template=None,
        proxy_ready=False,
        certificate_ready=False,
        https_capture_ready=False,
        setup_steps=(
            _guidance_step(
                "install-backend",
                "补齐抓包后端",
                "先安装 mitmdump，或在环境变量 APKHACKER_TRAFFIC_CAPTURE_COMMAND 中配置自定义抓包命令。",
                emphasis="required",
            ),
            _guidance_step(
                "verify-har",
                "验证 HAR 产物",
                "确认抓包命令能够在当前机器生成 HAR 产物，再回到工作台启动实时抓包。",
                emphasis="required",
            ),
        ),
        proxy_steps=(),
        certificate_steps=(),
        recommended_actions=(
            "当前先使用 HAR 导入链路保留流量证据。",
            "如果要做 HTTPS 解密，建议优先补齐 mitmdump 环境。",
        ),
    )
