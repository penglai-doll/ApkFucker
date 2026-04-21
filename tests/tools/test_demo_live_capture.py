from __future__ import annotations

import json
from pathlib import Path
import signal
import subprocess
import sys
import time


def test_demo_live_capture_writes_har_on_shutdown(tmp_path: Path) -> None:
    output_path = tmp_path / "demo-live.har"
    process = subprocess.Popen(
        [sys.executable, "-m", "apk_hacker.tools.demo_live_capture", str(output_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        time.sleep(0.1)
        process.send_signal(signal.SIGTERM)
        return_code = process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    assert return_code == 0
    assert output_path.is_file()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    entries = payload["log"]["entries"]
    assert len(entries) == 2
    assert entries[0]["request"]["url"] == "https://demo-c2.example/api/upload"
