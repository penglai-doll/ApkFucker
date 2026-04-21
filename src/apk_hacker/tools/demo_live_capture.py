from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import sys
import time


def _demo_har_payload() -> dict[str, object]:
    return {
        "log": {
            "version": "1.2",
            "creator": {"name": "apk-hacker-demo-live-capture", "version": "0.1.0"},
            "entries": [
                {
                    "request": {
                        "method": "POST",
                        "url": "https://demo-c2.example/api/upload",
                        "postData": {"text": '{"device_id":"demo-123","sms_body":"hello"}'},
                    },
                    "response": {
                        "status": 200,
                        "content": {"mimeType": "application/json", "text": '{"ok":true}'},
                    },
                },
                {
                    "request": {
                        "method": "GET",
                        "url": "https://example.org/ping",
                    },
                    "response": {
                        "status": 204,
                        "content": {"mimeType": "text/plain", "text": ""},
                    },
                },
            ],
        }
    }


def _write_har(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(_demo_har_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="apk-hacker-demo-live-capture",
        description="Demo live traffic capture runner for APKHacker.",
    )
    parser.add_argument("output_path", help="Path where the demo HAR artifact should be written on shutdown.")
    args = parser.parse_args()

    output_path = Path(args.output_path).expanduser().resolve()
    running = True

    def _stop(*_args: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    try:
        while running:
            time.sleep(0.1)
    finally:
        _write_har(output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
