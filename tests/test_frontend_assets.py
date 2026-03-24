from __future__ import annotations

import json
from pathlib import Path

from eden.observatory import frontend_assets


def _write_frontend_source_tree(root: Path) -> None:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text('{"name":"observatory-test"}\n', encoding="utf-8")
    (root / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    (root / "tsconfig.json").write_text('{"compilerOptions":{}}\n', encoding="utf-8")
    (root / "src" / "App.tsx").write_text("export default function App() { return null; }\n", encoding="utf-8")


def test_build_status_distinguishes_missing_bundle_and_missing_metadata(tmp_path, monkeypatch) -> None:
    source_root = tmp_path / "web" / "observatory"
    static_root = tmp_path / "static" / "observatory_app"
    _write_frontend_source_tree(source_root)
    monkeypatch.setattr(frontend_assets, "FRONTEND_SOURCE_ROOT", source_root)
    monkeypatch.setattr(frontend_assets, "FRONTEND_STATIC_ROOT", static_root)

    missing_bundle = frontend_assets.build_status()
    assert missing_bundle["available"] is False
    assert missing_bundle["state"] == "bundle_missing"
    assert "npm --prefix web/observatory run build" in missing_bundle["reason"]

    static_root.mkdir(parents=True)
    metadata_missing = frontend_assets.build_status()
    assert metadata_missing["available"] is True
    assert metadata_missing["state"] == "metadata_missing"
    assert "shell metadata missing" in metadata_missing["reason"]


def test_build_status_distinguishes_stale_and_current_metadata(tmp_path, monkeypatch) -> None:
    source_root = tmp_path / "web" / "observatory"
    static_root = tmp_path / "static" / "observatory_app"
    _write_frontend_source_tree(source_root)
    static_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(frontend_assets, "FRONTEND_SOURCE_ROOT", source_root)
    monkeypatch.setattr(frontend_assets, "FRONTEND_STATIC_ROOT", static_root)

    manifest_path = static_root / frontend_assets.BUILD_META_NAME
    manifest_path.write_text(json.dumps({"source_hash": "stale-hash", "built_at": "2026-03-24T16:00:00Z"}), encoding="utf-8")

    stale_status = frontend_assets.build_status()
    assert stale_status["available"] is True
    assert stale_status["warning"] is True
    assert stale_status["state"] == "stale"
    assert "frontend shell is older than the current source tree" in stale_status["reason"]

    current_hash = frontend_assets.frontend_source_hash()
    manifest_path.write_text(json.dumps({"source_hash": current_hash, "built_at": "2026-03-24T16:00:00Z"}), encoding="utf-8")

    current_status = frontend_assets.build_status()
    assert current_status["available"] is True
    assert current_status["warning"] is False
    assert current_status["state"] == "ok"
    assert current_status["reason"] == "ok"
