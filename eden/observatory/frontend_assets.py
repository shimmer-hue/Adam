from __future__ import annotations

import json
import shutil
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SOURCE_ROOT = REPO_ROOT / "web" / "observatory"
FRONTEND_STATIC_ROOT = Path(__file__).resolve().parent / "static" / "observatory_app"
BUILD_META_NAME = "build-meta.json"


def frontend_asset_root() -> Path:
    return FRONTEND_STATIC_ROOT


def frontend_asset_manifest() -> Path:
    return frontend_asset_root() / BUILD_META_NAME


def frontend_asset_version() -> str:
    manifest_path = frontend_asset_manifest()
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
        version = str(manifest.get("source_hash") or manifest.get("built_at") or "").strip()
        if version:
            return "".join(char if char.isalnum() else "-" for char in version).strip("-") or "observatory"
    asset_root = frontend_asset_root()
    if asset_root.exists():
        return str(int(asset_root.stat().st_mtime))
    return "missing"


def frontend_source_hash() -> str:
    files: list[Path] = []
    for relative in ("package.json", "package-lock.json", "vite.config.ts", "tsconfig.json"):
        candidate = FRONTEND_SOURCE_ROOT / relative
        if candidate.exists():
            files.append(candidate)
    src_root = FRONTEND_SOURCE_ROOT / "src"
    if src_root.exists():
        files.extend(sorted(path for path in src_root.rglob("*") if path.is_file()))
    if not files:
        return "missing"
    digest = sha256()
    for path in sorted(files):
        digest.update(str(path.relative_to(FRONTEND_SOURCE_ROOT)).encode("utf-8"))
        digest.update(b":")
        digest.update(path.read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()[:16]


def build_status() -> dict[str, Any]:
    asset_root = frontend_asset_root()
    manifest_path = frontend_asset_manifest()
    source_hash = frontend_source_hash()
    if not asset_root.exists() or not manifest_path.exists():
        return {
            "available": False,
            "warning": True,
            "reason": "frontend assets missing",
            "source_hash": source_hash,
        }
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "available": False,
            "warning": True,
            "reason": "invalid build metadata",
            "source_hash": source_hash,
        }
    built_hash = str(manifest.get("source_hash") or "")
    stale = built_hash != source_hash
    return {
        "available": True,
        "warning": stale,
        "reason": "stale build" if stale else "ok",
        "source_hash": source_hash,
        "built_hash": built_hash,
        "manifest": manifest,
        "asset_root": str(asset_root),
    }


def copy_frontend_assets(target_root: Path) -> Path:
    asset_root = frontend_asset_root()
    target = target_root / "_observatory_app"
    if target.exists():
        shutil.rmtree(target)
    if asset_root.exists():
        shutil.copytree(asset_root, target)
    return target
