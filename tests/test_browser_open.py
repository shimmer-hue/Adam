from __future__ import annotations

from eden import browser


def test_open_browser_url_falls_back_to_platform_launcher(monkeypatch) -> None:
    launches: list[list[str]] = []

    monkeypatch.setattr(browser.webbrowser, "open", lambda url: False)
    monkeypatch.setattr(browser, "_fallback_command", lambda: "open")

    class PopenStub:
        def __init__(self, args, **_kwargs) -> None:
            launches.append(list(args))

    monkeypatch.setattr(browser.subprocess, "Popen", PopenStub)

    result = browser.open_browser_url("http://127.0.0.1:8741/example")

    assert result.ok is True
    assert result.method == "open"
    assert launches == [["open", "http://127.0.0.1:8741/example"]]


def test_open_browser_url_reports_total_failure(monkeypatch) -> None:
    monkeypatch.setattr(browser.webbrowser, "open", lambda url: False)
    monkeypatch.setattr(browser, "_fallback_command", lambda: None)

    result = browser.open_browser_url("http://127.0.0.1:8741/example")

    assert result.ok is False
    assert result.method == "webbrowser"
    assert "returned False" in (result.detail or "")
