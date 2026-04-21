from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
import subprocess

from apk_hacker.domain.models.environment import ConnectedDevice
from apk_hacker.domain.models.environment import DeviceInventorySnapshot


def _normalize_model(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().replace("_", " ")
    return normalized or None


def _parse_adb_devices_long(stdout: str) -> tuple[ConnectedDevice, ...]:
    devices: list[ConnectedDevice] = []
    for raw_line in stdout.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("List of devices attached"):
            continue
        columns = stripped.split()
        if len(columns) < 2:
            continue
        serial = columns[0]
        state = columns[1]
        metadata: dict[str, str] = {}
        for token in columns[2:]:
            key, separator, value = token.partition(":")
            if not separator or not value:
                continue
            metadata[key] = value
        product = metadata.get("product")
        device_name = metadata.get("device")
        model = _normalize_model(metadata.get("model"))
        is_emulator = serial.startswith("emulator-") or (product or "").startswith("sdk_") or device_name in {
            "generic",
            "generic_x86",
        }
        devices.append(
            ConnectedDevice(
                serial=serial,
                state=state,
                model=model,
                product=product,
                device=device_name,
                transport_id=metadata.get("transport_id"),
                is_emulator=is_emulator,
            )
        )
    return tuple(devices)


class DeviceInventoryService:
    def __init__(
        self,
        adb_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
        frida_device_provider: Callable[[], Iterable[str]] | None = None,
    ) -> None:
        self._adb_runner = adb_runner or self._run_adb
        self._frida_device_provider = frida_device_provider or self._list_frida_devices

    def inspect(self, package_name: str | None = None) -> DeviceInventorySnapshot:
        try:
            completed = self._adb_runner("devices", "-l")
        except OSError:
            return DeviceInventorySnapshot(devices=())
        if completed.returncode != 0:
            return DeviceInventorySnapshot(devices=())

        devices = list(_parse_adb_devices_long(completed.stdout))
        frida_serials = set(self._safe_frida_devices())
        enriched_devices: list[ConnectedDevice] = []
        for device in devices:
            if not device.available:
                enriched_devices.append(device)
                continue
            abi = self._read_abi(device.serial)
            rooted = self._detect_root(device.serial)
            package_installed = self._check_package_installed(device.serial, package_name) if package_name else None
            enriched_devices.append(
                ConnectedDevice(
                    serial=device.serial,
                    state=device.state,
                    model=device.model,
                    product=device.product,
                    device=device.device,
                    transport_id=device.transport_id,
                    abi=abi,
                    rooted=rooted,
                    frida_visible=device.serial in frida_serials,
                    package_installed=package_installed,
                    is_emulator=device.is_emulator,
                )
            )
        return DeviceInventorySnapshot(devices=tuple(enriched_devices))

    def _read_abi(self, serial: str) -> str | None:
        completed = self._adb_runner("-s", serial, "shell", "getprop", "ro.product.cpu.abi")
        if completed.returncode != 0:
            return None
        value = completed.stdout.strip()
        return value or None

    def _detect_root(self, serial: str) -> bool | None:
        completed = self._adb_runner("-s", serial, "shell", "su", "-c", "id")
        if completed.returncode == 0:
            return "uid=0" in completed.stdout
        return False

    def _check_package_installed(self, serial: str, package_name: str) -> bool:
        completed = self._adb_runner("-s", serial, "shell", "pm", "path", package_name)
        return completed.returncode == 0 and completed.stdout.strip().startswith("package:")

    def _safe_frida_devices(self) -> tuple[str, ...]:
        try:
            return tuple(serial for serial in self._frida_device_provider() if serial)
        except Exception:
            return ()

    @staticmethod
    def _run_adb(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["adb", *args],
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def _list_frida_devices() -> tuple[str, ...]:
        try:
            import frida  # type: ignore
        except ImportError:
            return ()
        manager = frida.get_device_manager()
        devices = manager.enumerate_devices()
        return tuple(
            str(getattr(device, "id", "")).strip()
            for device in devices
            if str(getattr(device, "id", "")).strip()
        )
