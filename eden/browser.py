from __future__ import annotations

import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BrowserOpenResult:
    ok: bool
    method: str
    detail: str | None = None


def _fallback_command() -> str | None:
    if sys.platform == "darwin":
        return "open"
    if sys.platform.startswith("linux"):
        return shutil.which("xdg-open")
    return None


def open_browser_url(url: str) -> BrowserOpenResult:
    try:
        if webbrowser.open(url):
            return BrowserOpenResult(ok=True, method="webbrowser")
        browser_error = "webbrowser.open returned False"
    except Exception as exc:  # pragma: no cover - exercised through callers/tests via monkeypatch
        browser_error = f"webbrowser.open raised {exc}"

    command = _fallback_command()
    if command:
        try:
            subprocess.Popen(
                [command, url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return BrowserOpenResult(ok=True, method=command, detail=browser_error)
        except Exception as exc:  # pragma: no cover - exercised through callers/tests via monkeypatch
            return BrowserOpenResult(
                ok=False,
                method=command,
                detail=f"{browser_error}; fallback {command} raised {exc}",
            )

    return BrowserOpenResult(ok=False, method="webbrowser", detail=browser_error)
