"""PACOS one-click launcher — entry point for the PyInstaller exe.

Starts the FastAPI app (which also serves the built React frontend) and opens
the default browser. Close this window to stop PACOS.
"""
from __future__ import annotations

import socket
import threading
import webbrowser


def _free_port(preferred: int = 8000) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("no free port found between 8000 and 8019")


def main() -> None:
    import uvicorn

    from backend.main import app

    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    print(f"\n  PACOS is starting at {url}")
    print("  Close this window to stop it.\n")
    threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
