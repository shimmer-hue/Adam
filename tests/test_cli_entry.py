from __future__ import annotations

from eden import app as app_module


def test_main_defaults_to_app_when_no_subcommand(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_cmd_app(args) -> int:
        captured["command"] = args.command
        captured["backend"] = args.backend
        captured["model_path"] = args.model_path
        return 11

    monkeypatch.setattr(app_module, "cmd_app", fake_cmd_app)

    assert app_module.main([]) == 11
    assert captured["command"] == "app"
    assert captured["backend"] is None
    assert captured["model_path"] is None


def test_main_defaults_to_app_when_only_app_flags_are_provided(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_cmd_app(args) -> int:
        captured["command"] = args.command
        captured["backend"] = args.backend
        captured["model_path"] = args.model_path
        return 13

    monkeypatch.setattr(app_module, "cmd_app", fake_cmd_app)

    assert app_module.main(["--backend", "mock"]) == 13
    assert captured["command"] == "app"
    assert captured["backend"] == "mock"
