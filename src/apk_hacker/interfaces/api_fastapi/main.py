from __future__ import annotations

import uvicorn

from apk_hacker.interfaces.api_fastapi.app import build_app

app = build_app()


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8765)
