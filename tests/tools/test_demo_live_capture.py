from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys


def test_demo_live_capture_writes_har_on_shutdown(tmp_path: Path) -> None:
    output_path = tmp_path / "demo-live.har"
    process = subprocess.Popen(
        [sys.executable, "-m", "apk_hacker.tools.demo_live_capture", str(output_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0,
    )

    try:
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "demo-live-capture-ready"
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
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
