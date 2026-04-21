from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GuidanceStep:
    key: str
    title: str
    detail: str
    emphasis: str = "info"


@dataclass(frozen=True, slots=True)
class SuggestedHookTemplate:
    template_id: str
    template_name: str
    plugin_id: str
    label: str

    @property
    def source_id(self) -> str:
        return f"template:{self.plugin_id}:{self.template_id}"


@dataclass(frozen=True, slots=True)
class LiveCaptureNetworkSummary:
    supports_https_intercept: bool
    supports_packet_capture: bool
    supports_ssl_hooking: bool
    proxy_ready: bool
    certificate_ready: bool
    https_capture_ready: bool


@dataclass(frozen=True, slots=True)
class SslHookGuidance:
    recommended: bool
    summary: str
    reason: str
    suggested_templates: tuple[str, ...] = ()
    suggested_template_entries: tuple[SuggestedHookTemplate, ...] = ()
    suggested_terms: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ToolStatus:
    name: str
    label: str
    available: bool
    path: str | None = None


@dataclass(frozen=True, slots=True)
class EnvironmentSnapshot:
    tools: tuple[ToolStatus, ...]

    def tool_available(self, name: str) -> bool:
        return any(tool.name == name and tool.available for tool in self.tools)

    def tool_status(self, name: str) -> ToolStatus | None:
        return next((tool for tool in self.tools if tool.name == name), None)

    @property
    def supports_https_intercept(self) -> bool:
        return self.tool_available("mitmdump") or self.tool_available("mitmproxy")

    @property
    def supports_packet_capture(self) -> bool:
        return self.tool_available("tcpdump")

    @property
    def supports_ssl_hooking(self) -> bool:
        return self.tool_available("adb") and (
            self.tool_available("frida") or self.tool_available("python-frida")
        )

    @property
    def available_count(self) -> int:
        return sum(1 for tool in self.tools if tool.available)

    @property
    def missing_count(self) -> int:
        return sum(1 for tool in self.tools if not tool.available)

    @property
    def summary(self) -> str:
        return f"{self.available_count} available, {self.missing_count} missing"


@dataclass(frozen=True, slots=True)
class ConnectedDevice:
    serial: str
    state: str
    model: str | None = None
    product: str | None = None
    device: str | None = None
    transport_id: str | None = None
    abi: str | None = None
    rooted: bool | None = None
    frida_visible: bool | None = None
    package_installed: bool | None = None
    is_emulator: bool = False

    @property
    def available(self) -> bool:
        return self.state == "device"


@dataclass(frozen=True, slots=True)
class DeviceInventorySnapshot:
    devices: tuple[ConnectedDevice, ...]

    @property
    def available_count(self) -> int:
        return sum(1 for device in self.devices if device.available)

    @property
    def recommended_serial(self) -> str | None:
        available_devices = [device.serial for device in self.devices if device.available]
        if len(available_devices) == 1:
            return available_devices[0]
        return None
