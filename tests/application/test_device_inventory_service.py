from __future__ import annotations

import subprocess

from apk_hacker.application.services.device_inventory_service import DeviceInventoryService


def _completed(*args: str, stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=list(args), returncode=returncode, stdout=stdout, stderr=stderr)


def test_device_inventory_service_parses_connected_devices_and_enriches_primary_metadata() -> None:
    responses: dict[tuple[str, ...], subprocess.CompletedProcess[str]] = {
        ("devices", "-l"): _completed(
            "adb",
            "devices",
            "-l",
            stdout=(
                "List of devices attached\n"
                "emulator-5554\tdevice product:sdk_gphone64_arm64 model:Pixel_8_Pro device:husky transport_id:7\n"
                "R5CX1234ABC\tdevice product:r0q model:SM_S9180 device:r0q transport_id:3\n"
                "unauth-1\tunauthorized usb:1-1 transport_id:9\n"
            ),
        ),
        ("-s", "emulator-5554", "shell", "getprop", "ro.product.cpu.abi"): _completed(
            "adb", "-s", "emulator-5554", "shell", "getprop", "ro.product.cpu.abi", stdout="arm64-v8a\n"
        ),
        ("-s", "R5CX1234ABC", "shell", "getprop", "ro.product.cpu.abi"): _completed(
            "adb", "-s", "R5CX1234ABC", "shell", "getprop", "ro.product.cpu.abi", stdout="arm64-v8a\n"
        ),
        ("-s", "emulator-5554", "shell", "su", "-c", "id"): _completed(
            "adb", "-s", "emulator-5554", "shell", "su", "-c", "id", returncode=1, stderr="su: not found"
        ),
        ("-s", "R5CX1234ABC", "shell", "su", "-c", "id"): _completed(
            "adb", "-s", "R5CX1234ABC", "shell", "su", "-c", "id", stdout="uid=0(root) gid=0(root)\n"
        ),
        ("-s", "emulator-5554", "shell", "pm", "path", "com.demo.app"): _completed(
            "adb", "-s", "emulator-5554", "shell", "pm", "path", "com.demo.app", returncode=1, stderr="package not found"
        ),
        ("-s", "R5CX1234ABC", "shell", "pm", "path", "com.demo.app"): _completed(
            "adb", "-s", "R5CX1234ABC", "shell", "pm", "path", "com.demo.app", stdout="package:/data/app/com.demo.app\n"
        ),
    }

    def adb_runner(*args: str) -> subprocess.CompletedProcess[str]:
        return responses.get(tuple(args), _completed(*args, returncode=1, stderr="unexpected adb call"))

    service = DeviceInventoryService(
        adb_runner=adb_runner,
        frida_device_provider=lambda: {"R5CX1234ABC"},
    )

    snapshot = service.inspect(package_name="com.demo.app")

    assert snapshot.available_count == 2
    assert snapshot.recommended_serial is None
    assert [device.serial for device in snapshot.devices] == ["emulator-5554", "R5CX1234ABC", "unauth-1"]

    emulator = snapshot.devices[0]
    assert emulator.model == "Pixel 8 Pro"
    assert emulator.abi == "arm64-v8a"
    assert emulator.is_emulator is True
    assert emulator.rooted is False
    assert emulator.frida_visible is False
    assert emulator.package_installed is False

    handset = snapshot.devices[1]
    assert handset.model == "SM S9180"
    assert handset.product == "r0q"
    assert handset.transport_id == "3"
    assert handset.rooted is True
    assert handset.frida_visible is True
    assert handset.package_installed is True

    unauthorized = snapshot.devices[2]
    assert unauthorized.state == "unauthorized"
    assert unauthorized.abi is None
    assert unauthorized.rooted is None
    assert unauthorized.package_installed is None


def test_device_inventory_service_recommends_single_connected_device() -> None:
    service = DeviceInventoryService(
        adb_runner=lambda *args: _completed(
            "adb",
            *args,
            stdout=(
                "List of devices attached\n"
                "R5CX1234ABC\tdevice product:r0q model:SM_S9180 device:r0q transport_id:3\n"
            )
            if args == ("devices", "-l")
            else "arm64-v8a\n",
        )
        if args in {("devices", "-l"), ("-s", "R5CX1234ABC", "shell", "getprop", "ro.product.cpu.abi")}
        else _completed("adb", *args, returncode=1, stderr="ignored"),
        frida_device_provider=lambda: set(),
    )

    snapshot = service.inspect()

    assert snapshot.available_count == 1
    assert snapshot.recommended_serial == "R5CX1234ABC"
