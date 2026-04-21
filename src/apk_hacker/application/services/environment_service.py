from __future__ import annotations

from collections.abc import Callable
import importlib.util
from pathlib import Path
import shutil

from apk_hacker.application.services.live_capture_runtime import LiveCaptureRuntimeAvailability
from apk_hacker.domain.models.environment import EnvironmentSnapshot, ToolStatus
from apk_hacker.domain.models.environment import LiveCaptureNetworkSummary
from apk_hacker.domain.models.environment import SuggestedHookTemplate
from apk_hacker.domain.models.environment import SslHookGuidance


BINARY_TOOL_CATALOG: tuple[tuple[str, str], ...] = (
    ("jadx", "jadx"),
    ("jadx-gui", "jadx-gui"),
    ("apktool", "apktool"),
    ("adb", "adb"),
    ("frida", "frida"),
    ("mitmdump", "mitmdump"),
    ("mitmproxy", "mitmproxy"),
    ("tcpdump", "tcpdump"),
)

PYTHON_MODULE_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("frida", "python-frida", "module:frida"),
)

SSL_TEMPLATE_SUGGESTIONS: tuple[SuggestedHookTemplate, ...] = (
    SuggestedHookTemplate(
        template_id="ssl.okhttp3_unpin",
        template_name="OkHttp3 SSL Unpinning",
        plugin_id="builtin.ssl-okhttp3-unpin",
        label="OkHttp3 SSL Unpinning",
    ),
)

_SSL_TEMPLATE_PATHS: dict[str, Path] = {
    "ssl.okhttp3_unpin": Path(__file__).resolve().parents[4] / "templates" / "ssl" / "okhttp3_unpin.js.j2",
}


class EnvironmentService:
    def __init__(
        self,
        resolver: Callable[[str], str | None] | None = None,
        module_resolver: Callable[[str], object | None] | None = None,
    ) -> None:
        self._resolver = resolver or shutil.which
        self._module_resolver = module_resolver or importlib.util.find_spec

    def inspect(self) -> EnvironmentSnapshot:
        binary_tools = tuple(
            ToolStatus(
                name=name,
                label=label,
                available=(resolved := self._resolver(name)) is not None,
                path=resolved,
            )
            for name, label in BINARY_TOOL_CATALOG
        )
        python_modules = tuple(
            ToolStatus(
                name=label,
                label=label,
                available=(resolved := self._module_resolver(module_name)) is not None,
                path=display_path if resolved is not None else None,
            )
            for module_name, label, display_path in PYTHON_MODULE_CATALOG
        )
        return EnvironmentSnapshot(tools=(*binary_tools, *python_modules))

    def resolve_binary(self, name: str) -> str | None:
        return self._resolver(name)


def list_available_ssl_hook_templates() -> tuple[SuggestedHookTemplate, ...]:
    return tuple(
        entry
        for entry in SSL_TEMPLATE_SUGGESTIONS
        if _SSL_TEMPLATE_PATHS.get(entry.template_id, Path()).exists()
    )


def resolve_ssl_hook_template(
    *,
    template_id: str,
    plugin_id: str | None = None,
) -> SuggestedHookTemplate | None:
    for entry in list_available_ssl_hook_templates():
        if entry.template_id != template_id:
            continue
        if plugin_id is not None and entry.plugin_id != plugin_id:
            continue
        return entry
    return None


def build_live_capture_network_summary(
    snapshot: EnvironmentSnapshot,
    runtime: LiveCaptureRuntimeAvailability,
) -> LiveCaptureNetworkSummary:
    return LiveCaptureNetworkSummary(
        supports_https_intercept=runtime.available or snapshot.supports_https_intercept,
        supports_packet_capture=snapshot.supports_packet_capture,
        supports_ssl_hooking=snapshot.supports_ssl_hooking,
        proxy_ready=runtime.proxy_ready,
        certificate_ready=runtime.certificate_ready,
        https_capture_ready=runtime.https_capture_ready,
    )


def build_ssl_hook_guidance(
    snapshot: EnvironmentSnapshot,
    runtime: LiveCaptureRuntimeAvailability,
) -> SslHookGuidance:
    available_templates = list_available_ssl_hook_templates()
    suggested_templates = tuple(entry.label for entry in available_templates)
    suggested_terms = ("https", "ssl", "certificate", "network")
    if not runtime.available:
        return SslHookGuidance(
            recommended=False,
            summary="先补齐抓包环境，再考虑 SSL / HTTPS Hook。",
            reason="当前实时抓包后端未就绪，先安装 mitmdump 或配置自定义抓包命令。",
            suggested_templates=(),
            suggested_template_entries=(),
            suggested_terms=(),
        )
    if snapshot.supports_ssl_hooking:
        return SslHookGuidance(
            recommended=True,
            summary="建议优先启用 SSL / HTTPS 相关 Hook。",
            reason="当前已具备抓包与设备注入基础，优先启用 SSL Hook 更容易拿到 HTTPS 明文与协议细节。",
            suggested_templates=suggested_templates,
            suggested_template_entries=available_templates,
            suggested_terms=suggested_terms,
        )
    return SslHookGuidance(
        recommended=False,
        summary="抓包可用，但 SSL Hook 基础尚未就绪。",
        reason="当前缺少可用的 ADB/Frida 注入能力，建议先补齐真实设备 Hook 环境，再启用 SSL / HTTPS Hook。",
        suggested_templates=suggested_templates,
        suggested_template_entries=available_templates,
        suggested_terms=suggested_terms,
    )
