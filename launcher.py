"""
Trade-Claw cross-platform launcher.

Single entry point that:
  1. Ensures a local ``venv`` exists, creating it if necessary.
  2. Installs ``requirements.txt`` (skipped when already up-to-date).
  3. Generates a ``.env`` from ``.env.example`` if absent.
  4. Starts uvicorn on http://localhost:<API_PORT> (default 8000).
  5. Opens the bundled UI in the user's default browser.

Used by ``start-app.bat`` (Windows) and ``start-app.command`` (macOS) so the
user only has to double-click one file. Run ``python launcher.py`` directly
on Linux.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / "venv"
REQS = ROOT / "requirements.txt"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
STAMP = VENV / ".trade_claw_install_stamp"


def _venv_python() -> Path:
    """Path to the Python binary inside ``venv``."""
    if platform.system() == "Windows":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def _ensure_venv() -> None:
    if _venv_python().exists():
        return
    print("[launcher] Creating virtual environment in ./venv …", flush=True)
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])


def _ensure_dependencies() -> None:
    """Install / update requirements when the lockfile changes."""
    if not REQS.exists():
        print(f"[launcher] WARNING: {REQS} missing — skipping pip install", flush=True)
        return
    fingerprint = REQS.stat().st_mtime_ns
    if STAMP.exists() and STAMP.read_text().strip() == str(fingerprint):
        return
    print("[launcher] Installing dependencies (this can take a minute) …", flush=True)
    subprocess.check_call(
        [str(_venv_python()), "-m", "pip", "install", "--upgrade", "pip"],
    )
    subprocess.check_call(
        [str(_venv_python()), "-m", "pip", "install", "-r", str(REQS)],
    )
    STAMP.write_text(str(fingerprint))


def _ensure_env_file() -> None:
    if ENV_FILE.exists():
        return
    if ENV_EXAMPLE.exists():
        print("[launcher] No .env found — copying from .env.example", flush=True)
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
    else:
        print(
            "[launcher] WARNING: neither .env nor .env.example found — backend "
            "may refuse to start.",
            flush=True,
        )


def _read_env(key: str, default: str) -> str:
    """Lightweight .env reader (no python-dotenv import yet)."""
    if not ENV_FILE.exists():
        return os.environ.get(key, default)
    for raw in ENV_FILE.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return os.environ.get(key, default)


def _wait_until_alive(url: str, timeout_seconds: int = 30) -> bool:
    """Poll ``url`` until it returns 2xx/3xx or the timeout expires."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if 200 <= resp.status < 400:
                    return True
        except Exception:
            pass
        time.sleep(0.4)
    return False


def main() -> int:
    print("=" * 60, flush=True)
    print(" Trade-Claw — starting …", flush=True)
    print("=" * 60, flush=True)

    _ensure_venv()
    _ensure_dependencies()
    _ensure_env_file()

    host = _read_env("API_HOST", "127.0.0.1")
    # 0.0.0.0 binds for the server but is not a valid URL for the browser.
    browser_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    port = _read_env("API_PORT", "8000")
    ui_url = f"http://{browser_host}:{port}/app/"
    health_url = f"http://{browser_host}:{port}/health"

    print(f"[launcher] API:     http://{browser_host}:{port}", flush=True)
    print(f"[launcher] UI:      {ui_url}", flush=True)
    print(f"[launcher] API key: TRADE_CLAW_API_KEY from .env", flush=True)
    print("[launcher] Press Ctrl+C to stop the server.\n", flush=True)

    cmd = [
        str(_venv_python()),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    proc = subprocess.Popen(cmd, cwd=str(ROOT))
    try:
        if _wait_until_alive(health_url, timeout_seconds=30):
            print(f"[launcher] Backend ready — opening {ui_url}", flush=True)
            try:
                webbrowser.open(ui_url)
            except Exception as exc:  # pragma: no cover
                print(f"[launcher] Could not open browser: {exc}", flush=True)
        else:
            print(
                "[launcher] Backend did not respond within 30s — "
                "check the log above.",
                flush=True,
            )
        return proc.wait()
    except KeyboardInterrupt:
        print("\n[launcher] Stopping …", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
