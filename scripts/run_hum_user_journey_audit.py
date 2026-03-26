from __future__ import annotations

import argparse
import importlib
import json
import platform
import re
import subprocess
import sys
import traceback
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BACKEND = "mock"
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".tsx",
    ".ts",
}
SCAN_ROOTS = ("docs", "eden", "tests", "scripts")
SCAN_EXCLUDED_PREFIXES = ("eden/observatory/static/",)
HUM_CLAIM_RE = re.compile(
    r"(?i)(\bhum\b|hum:|hum_state|adam_hum|logs/hum_state|continuity artifact|low-bandwidth continuity)"
)
HUM_FILENAME_RE = re.compile(r"(?i)(adam_hum|hum_state|\bhum\b)")
MOTIF_RE = re.compile(r"(?i)\b(glmmr|mrmr|hush|pulse|thread|bloom)\b")
HISTORICAL_MARKERS = ("[HUM_STATS]", "[HUM_METRICS]", "[HUM_TABLE]")
TIMESTAMP_RE = re.compile(r"\[\d{4}-\d{2}-\d{2}[^\]]+\]")
HUM_JSON_REQUIRED_FIELDS = {
    "artifact_version",
    "generated_at",
    "experiment_id",
    "session_id",
    "latest_turn_id",
    "turn_ids",
    "turn_indices",
    "derived_from",
    "boundedness",
    "status",
    "continuity",
    "metrics",
    "text_surface",
}

FAILURE_INTERPRETATION = {
    "PASS": "Proved in the current run.",
    "NOT_PRESENT": "Audited and absent in the current run or current source surface.",
    "HISTORICAL_ONLY": "Present only in the historical artifact or historical references.",
    "DOCS_ONLY": "Present in docs/spec language without runtime support.",
    "STALE_RESIDUE": "Dead or misleading leftover wording or residue.",
    "MANUAL_REQUIRED": "Not safely automatable from the current surface.",
    "UNKNOWN": "Automation could not decide from available evidence.",
}

BASELINE_STATUS_REGISTER = {
    "Implemented": "No current repo-tracked first-class hum runtime surface is proved in the present build.",
    "Instrumented": "Historical hum artifact evidence exists in /Users/brianray/Desktop/adam_hum_ALL.md, including timestamped hum: entries plus [HUM_STATS], [HUM_METRICS], and [HUM_TABLE].",
    "Conceptual": "The hum fits the current persistence model as a low-bandwidth continuity artifact shaped by graph state, regard, feedback, and bounded retrieval.",
    "Unknown": "Whether the current build still generates, foregrounds, injects, or membrane-processes a live hum channel.",
}

JOURNEY_TITLES = {
    "HJ01": "contract and claim scan",
    "HJ02": "safe scratch boot and baseline continuity surfaces",
    "HJ03": "first turn persistence journey",
    "HJ04": "feedback and regard-adjacent continuity journey",
    "HJ05": "resume and recurrence journey",
    "HJ06": "export and observatory scan",
    "HJ07": "historical hum artifact comparison",
    "HJ08": "dead-path versus live-path audit",
    "HJ09": "final status register",
    "HJ10": "next shortest proof paths",
}


@dataclass(slots=True)
class ImportedRuntimeAnchors:
    runtime_module: Any | None
    runtime_cls: Any | None
    store_cls: Any | None
    runtime_log_cls: Any | None
    settings_cls: Any | None
    errors: list[str]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def should_scan_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.name.startswith("."):
        return False
    relative = repo_relative(path)
    if any(relative.startswith(prefix) for prefix in SCAN_EXCLUDED_PREFIXES):
        return False
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    return True


def iter_scan_files() -> list[Path]:
    paths: list[Path] = []
    for root_name in SCAN_ROOTS:
        root = REPO_ROOT / root_name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if should_scan_file(path):
                paths.append(path)
    notes_path = REPO_ROOT / "codex_notes_garden.md"
    if notes_path.exists():
        paths.append(notes_path)
    return paths


def classify_claim_hit(path: Path, line: str) -> str:
    relative = repo_relative(path)
    lowered = line.lower()
    if relative == "scripts/run_hum_user_journey_audit.py":
        return "docs_spec_wording"
    if "/users/brianray/desktop/adam_hum_all.md" in lowered or any(marker.lower() in lowered for marker in HISTORICAL_MARKERS):
        return "historical_artifact_reference"
    if relative.startswith("docs/"):
        return "docs_spec_wording"
    if relative == "codex_notes_garden.md":
        if "historical hum artifact" in lowered or "/users/brianray/desktop/adam_hum_all.md" in lowered:
            return "historical_artifact_reference"
        return "docs_spec_wording"
    if relative.startswith("tests/"):
        return "tests_only"
    if relative.startswith("eden/") or relative.startswith("scripts/"):
        if any(token in lowered for token in ("hum_state", "adam_hum", "logs/hum_state", "hum:")):
            return "runtime_code_path"
        return "stale_dead_residue"
    return "docs_spec_wording"


def scan_claims(repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    del repo_root
    inventory: list[dict[str, Any]] = []
    for path in iter_scan_files():
        text = safe_read_text(path)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if not HUM_CLAIM_RE.search(line):
                continue
            classification = classify_claim_hit(path, line)
            inventory.append(
                {
                    "path": str(path.resolve()),
                    "relative_path": repo_relative(path),
                    "line": line_no,
                    "match": line.strip(),
                    "classification": classification,
                    "source_surface": repo_relative(path).split("/", 1)[0],
                    "evidence_note": claim_evidence_note(classification, path),
                }
            )
    return inventory


def claim_evidence_note(classification: str, path: Path) -> str:
    relative = repo_relative(path)
    if classification == "runtime_code_path":
        return f"Hum-specific wording appears in source code under {relative}."
    if classification == "historical_artifact_reference":
        return f"Historical hum artifact is referenced from {relative}."
    if classification == "tests_only":
        return f"Hum wording appears only in test material under {relative}."
    if classification == "stale_dead_residue":
        return f"Hum wording appears in source-adjacent material without proving a live path under {relative}."
    return f"Hum wording appears in documentation or notes under {relative}."


def import_runtime_anchors() -> ImportedRuntimeAnchors:
    errors: list[str] = []
    runtime_module = None
    runtime_cls = None
    store_cls = None
    runtime_log_cls = None
    settings_cls = None

    try:
        runtime_module = importlib.import_module("eden.runtime")
        runtime_cls = getattr(runtime_module, "EdenRuntime", None)
    except Exception as exc:  # pragma: no cover - exercised through failure path
        errors.append(f"eden.runtime import failed: {type(exc).__name__}: {exc}")
    try:
        store_module = importlib.import_module("eden.storage.graph_store")
        store_cls = getattr(store_module, "GraphStore", None)
    except Exception as exc:  # pragma: no cover - exercised through failure path
        errors.append(f"eden.storage.graph_store import failed: {type(exc).__name__}: {exc}")
    try:
        logging_module = importlib.import_module("eden.logging")
        runtime_log_cls = getattr(logging_module, "RuntimeLog", None)
    except Exception as exc:  # pragma: no cover - exercised through failure path
        errors.append(f"eden.logging import failed: {type(exc).__name__}: {exc}")
    try:
        config_module = importlib.import_module("eden.config")
        settings_cls = getattr(config_module, "RuntimeSettings", None)
    except Exception as exc:  # pragma: no cover - exercised through failure path
        errors.append(f"eden.config import failed: {type(exc).__name__}: {exc}")

    if runtime_cls is None:
        errors.append("EdenRuntime anchor is unavailable.")
    if store_cls is None:
        errors.append("GraphStore anchor is unavailable.")
    if runtime_log_cls is None:
        errors.append("RuntimeLog anchor is unavailable.")
    if settings_cls is None:
        errors.append("RuntimeSettings anchor is unavailable.")

    return ImportedRuntimeAnchors(
        runtime_module=runtime_module,
        runtime_cls=runtime_cls,
        store_cls=store_cls,
        runtime_log_cls=runtime_log_cls,
        settings_cls=settings_cls,
        errors=errors,
    )


def probe_runtime_capabilities(runtime: Any | None) -> dict[str, Any]:
    if runtime is None:
        return {
            "available": False,
            "required_ready": False,
            "available_capabilities": [],
            "missing_capabilities": [
                "initialize_experiment",
                "start_session",
                "preview_turn",
                "chat",
                "apply_feedback",
            ],
        }
    capability_names = [
        "initialize_experiment",
        "start_session",
        "preview_turn",
        "chat",
        "apply_feedback",
        "export_observability",
        "session_state_snapshot",
        "write_conversation_log",
    ]
    capability_map = {name: callable(getattr(runtime, name, None)) for name in capability_names}
    available_capabilities = [name for name, ok in capability_map.items() if ok]
    missing_capabilities = [name for name, ok in capability_map.items() if not ok]
    required_ready = all(capability_map.get(name, False) for name in ("initialize_experiment", "start_session", "chat"))
    return {
        "available": True,
        "required_ready": required_ready,
        "capabilities": capability_map,
        "available_capabilities": available_capabilities,
        "missing_capabilities": missing_capabilities,
        "has_store": hasattr(runtime, "store"),
        "has_retrieval_service": hasattr(runtime, "retrieval_service"),
        "has_observatory_service": hasattr(runtime, "observatory_service"),
        "has_observatory_server": hasattr(runtime, "observatory_server"),
        "has_exporter": hasattr(runtime, "exporter"),
    }


def probe_observatory_capabilities(runtime: Any | None) -> dict[str, Any]:
    service = getattr(runtime, "observatory_service", None) if runtime is not None else None
    exporter = getattr(runtime, "exporter", None) if runtime is not None else None
    server = getattr(runtime, "observatory_server", None) if runtime is not None else None
    service_names = [
        "refresh_exports",
        "experiment_overview",
        "graph_payload",
        "basin_payload",
        "measurement_payload",
        "session_turns",
        "session_active_set",
    ]
    exporter_names = ["export_all"]
    capability_map = {f"service.{name}": callable(getattr(service, name, None)) for name in service_names}
    capability_map.update({f"exporter.{name}": callable(getattr(exporter, name, None)) for name in exporter_names})
    capability_map["server.root"] = hasattr(server, "root")
    capability_map["service.export_root"] = hasattr(service, "export_root")
    available_capabilities = [name for name, ok in capability_map.items() if ok]
    missing_capabilities = [name for name, ok in capability_map.items() if not ok]
    return {
        "available": service is not None or exporter is not None,
        "capabilities": capability_map,
        "available_capabilities": available_capabilities,
        "missing_capabilities": missing_capabilities,
    }


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_scratch_runtime(out_dir: Path, anchors: ImportedRuntimeAnchors) -> tuple[Any | None, dict[str, Any]]:
    scratch_root = ensure_dir(out_dir / "_scratch")
    export_root = ensure_dir(out_dir / "scratch_exports")
    conversation_root = ensure_dir(out_dir / "scratch_conversations")
    hum_root = ensure_dir(out_dir / "scratch_hum")
    context = {
        "scratch_root": str(scratch_root.resolve()),
        "scratch_db_path": str((scratch_root / "eden.db").resolve()),
        "scratch_runtime_log_path": str((scratch_root / "runtime.jsonl").resolve()),
        "scratch_export_root": str(export_root.resolve()),
        "scratch_conversation_root": str(conversation_root.resolve()),
        "scratch_hum_root": str(hum_root.resolve()),
        "runtime_build_error": None,
    }
    if anchors.errors:
        context["runtime_build_error"] = "; ".join(anchors.errors)
        return None, context
    try:
        store = anchors.store_cls(Path(context["scratch_db_path"]))
        runtime_log = anchors.runtime_log_cls(Path(context["scratch_runtime_log_path"]))
        settings = anchors.settings_cls(model_backend=DEFAULT_BACKEND)
        runtime = anchors.runtime_cls(store=store, settings=settings, runtime_log=runtime_log)
        if hasattr(runtime, "conversation_export_root"):
            runtime.conversation_export_root = Path(context["scratch_conversation_root"])
        hum_service = getattr(runtime, "hum_service", None)
        if hum_service is not None and hasattr(hum_service, "root"):
            hum_service.root = Path(context["scratch_hum_root"])
        service = getattr(runtime, "observatory_service", None)
        if service is not None and hasattr(service, "export_root"):
            service.export_root = Path(context["scratch_export_root"])
        server = getattr(runtime, "observatory_server", None)
        if server is not None and hasattr(server, "root"):
            server.root = Path(context["scratch_export_root"])
        exporter = getattr(runtime, "exporter", None)
        if exporter is not None and hasattr(exporter, "tanakh_service"):
            exporter.tanakh_service = None
        if service is not None and hasattr(service, "tanakh_service"):
            service.tanakh_service = None
        context["runtime_ready"] = True
        return runtime, context
    except Exception as exc:  # pragma: no cover - exercised through script failure path
        context["runtime_ready"] = False
        context["runtime_build_error"] = f"{type(exc).__name__}: {exc}"
        return None, context


def close_runtime(runtime: Any | None) -> None:
    if runtime is None:
        return
    store = getattr(runtime, "store", None)
    if store is not None and callable(getattr(store, "close", None)):
        store.close()


def safe_call(func: Any, /, *args: Any, **kwargs: Any) -> tuple[bool, Any, str | None]:
    try:
        return True, func(*args, **kwargs), None
    except Exception as exc:
        return False, None, f"{type(exc).__name__}: {exc}"


def path_artifact(journey_id: str, name: str, path: Path, note: str) -> dict[str, Any]:
    return {
        "journey_id": journey_id,
        "name": name,
        "path": str(path.resolve()),
        "note": note,
    }


def normalize_text_excerpt(value: str, *, limit: int = 240) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def scan_text_for_hum(text: str, *, path_hint: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if HUM_CLAIM_RE.search(line):
            matches.append(
                {
                    "path_hint": path_hint,
                    "line": line_no,
                    "match": line.strip(),
                }
            )
    return matches


def scan_object_for_hum(value: Any, *, path_hint: str = "root") -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []

    def _walk(node: Any, prefix: str) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                key_text = str(key)
                if HUM_CLAIM_RE.search(key_text):
                    matches.append(
                        {
                            "path_hint": prefix,
                            "line": None,
                            "match": f"key:{key_text}",
                        }
                    )
                _walk(child, f"{prefix}.{key_text}")
            return
        if isinstance(node, list):
            for index, child in enumerate(node):
                _walk(child, f"{prefix}[{index}]")
            return
        if isinstance(node, str) and HUM_CLAIM_RE.search(node):
            matches.append(
                {
                    "path_hint": prefix,
                    "line": None,
                    "match": normalize_text_excerpt(node),
                }
            )

    _walk(value, path_hint)
    return matches


def scan_directory_for_hum(root: Path) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    if not root.exists():
        return matches
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = repo_relative(path)
        if path.suffix.lower() not in {".html", ".json", ".md", ".txt", ".log", ".jsonl"}:
            if HUM_FILENAME_RE.search(path.name):
                matches.append({"path": str(path.resolve()), "line": None, "match": path.name, "relative_path": relative})
            continue
        if HUM_FILENAME_RE.search(path.name):
            matches.append({"path": str(path.resolve()), "line": None, "match": path.name, "relative_path": relative})
        for hit in scan_text_for_hum(safe_read_text(path), path_hint=relative):
            matches.append(
                {
                    "path": str(path.resolve()),
                    "line": hit["line"],
                    "match": hit["match"],
                    "relative_path": relative,
                }
            )
    return matches


def parse_metadata_json(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def render_scratch_conversation_log(runtime: Any, session_id: str, out_path: Path) -> Path:
    store = runtime.store
    session = store.get_session(session_id)
    experiment = store.get_experiment(session["experiment_id"])
    turns = store.list_all_turns(session_id)
    lines = [
        "# Adam Conversation Log",
        "",
        f"- experiment: {experiment['name']} ({experiment['id']})",
        f"- session: {session['title']} ({session['id']})",
        f"- updated_at: {now_utc()}",
        "",
    ]
    if not turns:
        lines.append("_No turns yet. The session exists, but no persisted turn is present._")
    for turn in turns:
        lines.extend(
            [
                f"## Turn T{turn['turn_index']}",
                "",
                "### Brian",
                "```text",
                str(turn.get("user_text") or ""),
                "```",
                "",
                "### Adam",
                "```text",
                str(turn.get("membrane_text") or turn.get("response_text") or ""),
                "```",
                "",
            ]
        )
        feedback_entries = store.list_feedback_for_turn(turn["id"])
        if feedback_entries:
            lines.append("### Feedback")
            lines.append("")
            for feedback in feedback_entries:
                lines.append(f"- {str(feedback.get('verdict') or '').upper()}: {feedback.get('explanation') or ''}")
            lines.append("")
    ensure_dir(out_path.parent)
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_path


def build_local_session_snapshot(runtime: Any, session_id: str, conversation_log_path: Path) -> dict[str, Any]:
    store = runtime.store
    session = store.get_session(session_id)
    experiment = store.get_experiment(session["experiment_id"])
    turns = store.list_all_turns(session_id)
    last_turn = turns[-1] if turns else None
    metadata = parse_metadata_json(last_turn.get("metadata_json", "")) if last_turn else {}
    return {
        "experiment_id": experiment["id"],
        "experiment_name": experiment["name"],
        "session_id": session["id"],
        "session_title": session["title"],
        "conversation_log_path": str(conversation_log_path.resolve()),
        "turn_count": len(turns),
        "feedback_count": len(store.recent_feedback(session_id, limit=20)),
        "last_turn_id": last_turn["id"] if last_turn else None,
        "last_active_set_size": len(json.loads(last_turn.get("active_set_json") or "[]")) if last_turn else 0,
        "last_trace_size": len(json.loads(last_turn.get("trace_json") or "[]")) if last_turn else 0,
        "current_budget": metadata.get("budget"),
        "current_profile": metadata.get("inference_profile"),
    }


def hum_reference_matches(reference: dict[str, Any] | None, snapshot: dict[str, Any]) -> bool:
    if not isinstance(reference, dict):
        return False
    return (
        bool(reference.get("present")) == bool(snapshot.get("present"))
        and str(reference.get("markdown_path") or "") == str(snapshot.get("markdown_path") or "")
        and str(reference.get("json_path") or "") == str(snapshot.get("json_path") or "")
        and str(reference.get("artifact_version") or "") == str(snapshot.get("artifact_version") or "")
    )


def probe_hum_artifact(
    runtime: Any,
    *,
    experiment_id: str,
    session_id: str,
) -> dict[str, Any]:
    result = {
        "valid": False,
        "hum_snapshot": {},
        "session_snapshot_hum": {},
        "overview_hum": {},
        "transcript_hum": {},
        "markdown_exists": False,
        "json_exists": False,
        "json_parsed": False,
        "required_fields_present": False,
        "required_fields_missing": [],
        "cross_turn_recurrence_present": False,
        "seed_state_only": False,
        "markdown_path": None,
        "json_path": None,
        "json_payload": {},
    }
    hum_snapshot_callable = getattr(runtime, "hum_snapshot", None)
    if not callable(hum_snapshot_callable):
        return result
    hum_snapshot = hum_snapshot_callable(session_id)
    result["hum_snapshot"] = hum_snapshot
    markdown_path = Path(str(hum_snapshot.get("markdown_path") or ""))
    json_path = Path(str(hum_snapshot.get("json_path") or ""))
    result["markdown_path"] = str(markdown_path) if markdown_path else None
    result["json_path"] = str(json_path) if json_path else None
    result["markdown_exists"] = markdown_path.exists()
    result["json_exists"] = json_path.exists()

    json_payload: dict[str, Any] = {}
    if result["json_exists"]:
        try:
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))
            result["json_parsed"] = True
        except json.JSONDecodeError:
            result["json_parsed"] = False
    result["json_payload"] = json_payload
    missing_fields = sorted(HUM_JSON_REQUIRED_FIELDS - set(json_payload)) if json_payload else sorted(HUM_JSON_REQUIRED_FIELDS)
    result["required_fields_missing"] = missing_fields
    result["required_fields_present"] = not missing_fields

    session_snapshot = {}
    session_state_snapshot = getattr(runtime, "session_state_snapshot", None)
    if callable(session_state_snapshot):
        session_snapshot = session_state_snapshot(session_id)
    session_hum = session_snapshot.get("hum", {}) if isinstance(session_snapshot, dict) else {}
    result["session_snapshot_hum"] = session_hum

    service = getattr(runtime, "observatory_service", None)
    overview_hum: dict[str, Any] = {}
    transcript_hum: dict[str, Any] = {}
    if service is not None:
        experiment_overview = getattr(service, "experiment_overview", None)
        if callable(experiment_overview):
            overview_payload = experiment_overview(experiment_id=experiment_id, session_id=session_id)
            overview_hum = overview_payload.get("hum", {}) if isinstance(overview_payload, dict) else {}
        session_turns = getattr(service, "session_turns", None)
        if callable(session_turns):
            transcript_payload = session_turns(session_id=session_id)
            transcript_hum = transcript_payload.get("hum", {}) if isinstance(transcript_payload, dict) else {}
    result["overview_hum"] = overview_hum
    result["transcript_hum"] = transcript_hum

    recurrence_present = bool(json_payload.get("status", {}).get("cross_turn_recurrence_present")) if json_payload else False
    turn_window_size = int(json_payload.get("metrics", {}).get("turn_window_size", 0) or 0) if json_payload else 0
    result["cross_turn_recurrence_present"] = recurrence_present
    result["seed_state_only"] = turn_window_size < 2 or not recurrence_present
    result["valid"] = (
        bool(hum_snapshot.get("present"))
        and result["markdown_exists"]
        and result["json_exists"]
        and result["json_parsed"]
        and result["required_fields_present"]
        and hum_reference_matches(session_hum, hum_snapshot)
        and (hum_reference_matches(overview_hum, hum_snapshot) or hum_reference_matches(transcript_hum, hum_snapshot))
    )
    return result


def collect_runtime_log_hits(runtime_log_path: Path) -> list[dict[str, Any]]:
    if not runtime_log_path.exists():
        return []
    return scan_text_for_hum(safe_read_text(runtime_log_path), path_hint=repo_relative(runtime_log_path))


def parse_historical_hum(path: Path) -> dict[str, Any]:
    text = safe_read_text(path)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    hum_lines = [line for line in lines if "hum:" in line.lower()]
    motif_counts = Counter()
    for line in hum_lines:
        motif_counts.update(match.group(1).lower() for match in MOTIF_RE.finditer(line))
    return {
        "path": str(path.resolve()),
        "exists": path.exists(),
        "timestamp_count": len(TIMESTAMP_RE.findall(text)),
        "hum_line_count": len(hum_lines),
        "section_markers": [marker for marker in HISTORICAL_MARKERS if marker in text],
        "motif_counts": dict(sorted(motif_counts.items())),
        "sample_lines": hum_lines[:5],
    }


def compare_historical_to_current(historical: dict[str, Any], current_artifact_scan: dict[str, Any]) -> dict[str, Any]:
    current_probe = current_artifact_scan.get("artifact_probe", {})
    current_motifs = Counter()
    for text in current_artifact_scan.get("motif_text_surfaces", []):
        current_motifs.update(match.group(1).lower() for match in MOTIF_RE.finditer(text))
    return {
        "historical_hum_present": bool(historical.get("hum_line_count")),
        "current_analog_present": bool(current_probe.get("valid")),
        "historical_section_markers": historical.get("section_markers", []),
        "historical_motif_counts": historical.get("motif_counts", {}),
        "current_motif_counts": dict(sorted(current_motifs.items())),
    }


def gather_git_head() -> str | None:
    ok, result, _ = safe_call(
        subprocess.run,
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if not ok or result.returncode != 0:
        return None
    return result.stdout.strip() or None


def classify_path_state(
    claim_inventory: list[dict[str, Any]],
    runtime_hits: list[dict[str, Any]],
    historical_loaded: bool,
) -> dict[str, Any]:
    runtime_claims = [item for item in claim_inventory if item["classification"] == "runtime_code_path"]
    docs_claims = [item for item in claim_inventory if item["classification"] == "docs_spec_wording"]
    historical_claims = [item for item in claim_inventory if item["classification"] == "historical_artifact_reference"]
    stale_claims = [item for item in claim_inventory if item["classification"] == "stale_dead_residue"]

    if runtime_hits:
        outcome = "PASS"
    elif runtime_claims:
        outcome = "UNKNOWN"
    elif docs_claims and (historical_loaded or historical_claims):
        outcome = "DOCS_ONLY"
    elif historical_loaded or historical_claims:
        outcome = "HISTORICAL_ONLY"
    elif stale_claims:
        outcome = "STALE_RESIDUE"
    else:
        outcome = "NOT_PRESENT"

    path_classifications: list[dict[str, Any]] = []
    if docs_claims:
        path_classifications.append(
            {
                "surface": "docs/spec hum language",
                "classification": "conceptual",
                "evidence_count": len(docs_claims),
            }
        )
    if historical_loaded or historical_claims:
        path_classifications.append(
            {
                "surface": "historical hum artifact reference",
                "classification": "instrumented",
                "evidence_count": len(historical_claims),
            }
        )
    if runtime_hits:
        path_classifications.append(
            {
                "surface": "current runtime hum artifact",
                "classification": "implemented",
                "evidence_count": len(runtime_hits),
            }
        )
    if stale_claims:
        path_classifications.append(
            {
                "surface": "source-adjacent stale residue",
                "classification": "stale residue",
                "evidence_count": len(stale_claims),
            }
        )
    if not path_classifications:
        path_classifications.append(
            {
                "surface": "unresolved hum path",
                "classification": "unknown",
                "evidence_count": 0,
            }
        )
    return {"outcome": outcome, "path_classifications": path_classifications}


def build_final_status_register(runtime_hum_validated: bool) -> dict[str, str]:
    if not runtime_hum_validated:
        return dict(BASELINE_STATUS_REGISTER)
    return {
        "Implemented": "Current run produced a bounded persisted hum artifact (`current_hum.md` plus `current_hum.json`) and exposed it through read-only runtime and observatory reference surfaces.",
        "Instrumented": "Historical hum artifact evidence still exists in /Users/brianray/Desktop/adam_hum_ALL.md, and the current runtime now records bounded hum provenance and metrics in machine-readable form.",
        "Conceptual": "Anything richer than the current read-only bounded artifact remains conceptual, including prompt injection, membrane consumption, or a more expressive historical-style hum channel.",
        "Unknown": "Whether additional hum surfaces should exist beyond the bounded persisted artifact proved in this run.",
    }


def build_next_shortest_proof_paths(
    *,
    runtime_caps: dict[str, Any],
    observatory_caps: dict[str, Any],
    historical_path: Path | None,
    runtime_hum_validated: bool,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if not runtime_hum_validated:
        steps.append(
            {
                "target": "/Users/brianray/Adam/eden/runtime.py post-turn hum refresh plus a scratch artifact run",
                "reason": "The shortest path to live hum proof is a bounded current_hum.md/current_hum.json artifact written after a persisted turn and verifiable in scratch scope.",
                "mode": "automatable",
            }
        )
    if historical_path is None:
        steps.append(
            {
                "target": "--historical-hum /Users/brianray/Desktop/adam_hum_ALL.md",
                "reason": "A direct structural comparison against the historical artifact is still missing from this run.",
                "mode": "automatable",
            }
        )
    if not observatory_caps.get("capabilities", {}).get("service.session_turns", False):
        steps.append(
            {
                "target": "/Users/brianray/Adam/eden/observatory/service.py session_turns",
                "reason": "The shortest path to closing observatory-side uncertainty is a read-only session_turns payload that carries the hum reference block for the scratch session.",
                "mode": "automatable",
            }
        )
    if not runtime_caps.get("capabilities", {}).get("preview_turn", False):
        steps.append(
            {
                "target": "/Users/brianray/Adam/eden/runtime.py preview_turn",
                "reason": "Prompt assembly cannot be audited safely unless preview surfaces the assembled context without requiring a full TUI run.",
                "mode": "automatable",
            }
        )
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for step in steps:
        key = step["target"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(step)
    return deduped


def journey_result(
    journey_id: str,
    *,
    status: str,
    purpose: str,
    automated_check: str,
    expected_result: str,
    what_it_means: str,
    if_this_fails: str,
    manual_follow_up: str,
    artifacts_found: list[dict[str, Any]] | None = None,
    artifacts_missing: list[dict[str, Any]] | None = None,
    notes: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": journey_id,
        "title": JOURNEY_TITLES[journey_id],
        "status": status,
        "purpose": purpose,
        "automated_check": automated_check,
        "expected_result": expected_result,
        "what_this_means_for_the_hum": what_it_means,
        "if_this_fails": if_this_fails,
        "manual_follow_up_only_if_needed": manual_follow_up,
        "artifacts_found": artifacts_found or [],
        "artifacts_missing": artifacts_missing or [],
        "notes": notes or [],
        "details": details or {},
    }


def run_journeys(
    *,
    out_dir: Path,
    historical_hum_path: Path | None,
) -> dict[str, Any]:
    claim_inventory = scan_claims()
    hum_spec_path = REPO_ROOT / "docs" / "HUM_SPEC.md"
    hum_spec_exists = hum_spec_path.exists()
    anchors = import_runtime_anchors()
    runtime, scratch_context = create_scratch_runtime(out_dir, anchors)
    runtime_caps = probe_runtime_capabilities(runtime)
    observatory_caps = probe_observatory_capabilities(runtime)

    run_context = {
        "git_commit_sha": gather_git_head(),
        "audit_timestamp": now_utc(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "backend": DEFAULT_BACKEND,
        "scratch_db_path": scratch_context.get("scratch_db_path"),
        "scratch_runtime_log_path": scratch_context.get("scratch_runtime_log_path"),
        "scratch_export_root": scratch_context.get("scratch_export_root"),
        "scratch_conversation_root": scratch_context.get("scratch_conversation_root"),
        "scratch_hum_root": scratch_context.get("scratch_hum_root"),
        "repo_scan_roots": list(SCAN_ROOTS) + ["codex_notes_garden.md"],
        "scan_excluded_prefixes": list(SCAN_EXCLUDED_PREFIXES),
        "current_repo_data_scanned": True,
        "external_historical_hum_provided": bool(historical_hum_path),
        "runtime_capability_probe_succeeded": runtime is not None and runtime_caps.get("available", False),
        "runtime_import_errors": anchors.errors,
        "runtime_capabilities_available": runtime_caps.get("available_capabilities", []),
        "runtime_capabilities_missing": runtime_caps.get("missing_capabilities", []),
        "observatory_capabilities_available": observatory_caps.get("available_capabilities", []),
        "observatory_capabilities_missing": observatory_caps.get("missing_capabilities", []),
        "hum_spec_present": hum_spec_exists,
        "runtime_build_error": scratch_context.get("runtime_build_error"),
    }

    artifacts_found: list[dict[str, Any]] = []
    artifacts_missing: list[dict[str, Any]] = []
    journeys: list[dict[str, Any]] = []
    current_artifact_scan: dict[str, Any] = {
        "runtime_hum_hits": [],
        "runtime_log_hum_hits": [],
        "prompt_hum_hits": [],
        "turn_hum_hits": [],
        "export_hum_hits": [],
        "observatory_payload_hum_hits": [],
        "artifact_probe": {},
        "observatory_hum_probe": {},
        "motif_text_surfaces": [],
        "adjacent_surfaces": {},
    }
    historical_scan: dict[str, Any] | None = None
    comparison_scan: dict[str, Any] | None = None

    runtime_claims = [item for item in claim_inventory if item["classification"] == "runtime_code_path"]
    docs_claims = [item for item in claim_inventory if item["classification"] == "docs_spec_wording"]
    historical_claims = [item for item in claim_inventory if item["classification"] == "historical_artifact_reference"]
    stale_claims = [item for item in claim_inventory if item["classification"] == "stale_dead_residue"]
    tests_claims = [item for item in claim_inventory if item["classification"] == "tests_only"]

    hj01_status = "PASS" if runtime_claims else "DOCS_ONLY" if docs_claims else "HISTORICAL_ONLY" if historical_claims else "NOT_PRESENT"
    journeys.append(
        journey_result(
            "HJ01",
            status=hj01_status,
            purpose="Map every current hum claim in docs, code, tests, scripts, and notes.",
            automated_check="Scanned repo text surfaces for hum-specific strings, historical markers, and continuity-artifact wording; classified each hit by source surface.",
            expected_result="A claim inventory that separates runtime code paths from docs/spec wording, tests-only references, stale residue, and historical references.",
            what_it_means="This tells the operator whether the audit is chasing a live mechanism, documented language, or only historical residue.",
            if_this_fails="If the scan cannot build a claim inventory, the rest of the audit loses its spine and runtime absence becomes harder to interpret.",
            manual_follow_up="Inspect docs/HUM_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, and codex_notes_garden.md directly if the automated inventory fails.",
            artifacts_found=[
                {
                    "journey_id": "HJ01",
                    "name": "claim_inventory_count",
                    "path": str((out_dir / "hum_claim_inventory.json").resolve()),
                    "note": f"Captured {len(claim_inventory)} hum-related claim hits.",
                }
            ],
            notes=[
                f"runtime_code_path hits={len(runtime_claims)}",
                f"docs_spec_wording hits={len(docs_claims)}",
                f"historical_artifact_reference hits={len(historical_claims)}",
                f"tests_only hits={len(tests_claims)}",
                f"stale_dead_residue hits={len(stale_claims)}",
                f"docs/HUM_SPEC.md present={hum_spec_exists}",
            ],
            details={
                "hum_spec_present": hum_spec_exists,
                "runtime_claim_count": len(runtime_claims),
                "docs_claim_count": len(docs_claims),
                "historical_claim_count": len(historical_claims),
                "tests_claim_count": len(tests_claims),
                "stale_claim_count": len(stale_claims),
            },
        )
    )

    scratch_state: dict[str, Any] = {}
    if runtime is None or not runtime_caps.get("required_ready", False):
        journeys.append(
            journey_result(
                "HJ02",
                status="MANUAL_REQUIRED",
                purpose="Verify baseline continuity surfaces in a scratch runtime before any hum-specific interpretation.",
                automated_check="Attempted runtime import, capability probe, and scratch-runtime construction.",
                expected_result="A blank scratch experiment and session with transcript-capable, active-set-capable, and feedback-capable surfaces.",
                what_it_means="Without a safe scratch runtime, the audit can still classify docs and historical claims, but live continuity surfaces need manual proof.",
                if_this_fails="Treat runtime-interface drift as a tooling issue, not as evidence for or against a hum surface.",
                manual_follow_up="Inspect EdenRuntime, GraphStore, RuntimeLog, and RuntimeSettings anchors, then rerun the audit.",
                artifacts_missing=[{"journey_id": "HJ02", "name": "scratch_runtime", "path": "", "note": scratch_context.get("runtime_build_error") or "Scratch runtime unavailable."}],
                notes=[scratch_context.get("runtime_build_error") or "Runtime capability probe did not reach the required chat path."],
            )
        )
    else:
        ok, experiment, error = safe_call(runtime.initialize_experiment, "blank", name="Scratch Audit")
        if not ok:
            journeys.append(
                journey_result(
                    "HJ02",
                    status="MANUAL_REQUIRED",
                    purpose="Verify baseline continuity surfaces in a scratch runtime before any hum-specific interpretation.",
                    automated_check="Attempted scratch experiment initialization.",
                    expected_result="A blank scratch experiment and session.",
                    what_it_means="A runtime that cannot initialize scratch state cannot prove or disprove hum-adjacent surfaces safely.",
                    if_this_fails="Treat the initialization failure as audit infrastructure failure, not hum evidence.",
                    manual_follow_up="Inspect scratch runtime initialization and experiment creation directly.",
                    artifacts_missing=[{"journey_id": "HJ02", "name": "scratch_experiment", "path": "", "note": error or "Experiment creation failed."}],
                )
            )
        else:
            ok, session, error = safe_call(runtime.start_session, experiment["id"], title="Scratch Audit Session")
            if not ok:
                journeys.append(
                    journey_result(
                        "HJ02",
                        status="MANUAL_REQUIRED",
                        purpose="Verify baseline continuity surfaces in a scratch runtime before any hum-specific interpretation.",
                        automated_check="Attempted scratch session creation after experiment bootstrap.",
                        expected_result="A scratch session ready for preview, turn persistence, and feedback.",
                        what_it_means="Session creation is the baseline continuity shell. If it fails, later journeys cannot distinguish hum from ordinary persistence surfaces.",
                        if_this_fails="Treat it as runtime harness failure, not hum absence.",
                        manual_follow_up="Inspect start_session in the current runtime and rerun the audit.",
                        artifacts_missing=[{"journey_id": "HJ02", "name": "scratch_session", "path": "", "note": error or "Session creation failed."}],
                    )
                )
            else:
                scratch_state["experiment"] = experiment
                scratch_state["session"] = session
                conversation_path = Path(scratch_context["scratch_conversation_root"]) / f"{session['id']}.md"
                render_scratch_conversation_log(runtime, session["id"], conversation_path)
                artifacts_found.append(path_artifact("HJ02", "scratch_conversation_log", conversation_path, "Rendered scratch conversation-log artifact."))
                preview_items = 0
                preview_note = "preview_turn unavailable"
                if runtime_caps["capabilities"].get("preview_turn", False):
                    ok, preview, error = safe_call(
                        runtime.preview_turn,
                        session_id=session["id"],
                        user_text="Describe the current continuity surfaces without mysticism.",
                    )
                    if ok:
                        scratch_state["preview"] = preview
                        preview_items = len(getattr(preview, "active_set", []))
                        preview_note = f"preview_turn produced active_set size={preview_items}"
                    else:
                        preview_note = error or "preview_turn failed"
                current_artifact_scan["adjacent_surfaces"]["hj02"] = {
                    "conversation_log_path": str(conversation_path.resolve()),
                    "conversation_log_exists": conversation_path.exists(),
                    "preview_active_set_size": preview_items,
                    "feedback_capable": runtime_caps["capabilities"].get("apply_feedback", False),
                }
                journeys.append(
                    journey_result(
                        "HJ02",
                        status="PASS",
                        purpose="Verify baseline continuity surfaces in a safe scratch runtime before any hum-specific interpretation.",
                        automated_check="Created a blank scratch experiment and session, rendered a scratch conversation log, and probed preview/feedback capabilities without touching repo-global state.",
                        expected_result="Ordinary persistence surfaces work in scratch scope before any hum claim is made.",
                        what_it_means="These are hum-adjacent continuity surfaces. They matter because operators can easily misread them as hum when they are just normal session persistence, active-set preview, or explicit feedback plumbing.",
                        if_this_fails="If scratch continuity surfaces fail, later hum conclusions must be downgraded because the baseline runtime contract was not proved in this run.",
                        manual_follow_up="Inspect the scratch experiment, session, and preview path manually only if the script cannot create or preview a blank session.",
                        artifacts_found=[
                            path_artifact("HJ02", "scratch_conversation_log", conversation_path, "Rendered a local transcript artifact in scratch scope."),
                        ],
                        notes=[preview_note],
                        details=current_artifact_scan["adjacent_surfaces"]["hj02"],
                    )
                )

    if scratch_state:
        experiment = scratch_state["experiment"]
        session = scratch_state["session"]
        conversation_path = Path(scratch_context["scratch_conversation_root"]) / f"{session['id']}.md"
        prompt_hits: list[dict[str, Any]] = []
        prompt_note = "preview_turn unavailable; falling back to persisted prompt context after chat."
        preview = scratch_state.get("preview")
        if preview is not None:
            prompt_hits.extend(scan_text_for_hum(getattr(preview, "system_prompt", ""), path_hint="preview.system_prompt"))
            prompt_hits.extend(scan_text_for_hum(getattr(preview, "conversation_prompt", ""), path_hint="preview.conversation_prompt"))
            prompt_hits.extend(scan_text_for_hum(getattr(preview, "history_context", ""), path_hint="preview.history_context"))
            prompt_hits.extend(scan_text_for_hum(getattr(preview, "feedback_context", ""), path_hint="preview.feedback_context"))
            prompt_note = "Scanned preview_turn prompt assembly surfaces for hum-specific text."
        ok, outcome, error = safe_call(
            runtime.chat,
            session_id=session["id"],
            user_text="State the currently visible continuity surfaces in one short paragraph.",
        )
        if not ok:
            journeys.append(
                journey_result(
                    "HJ03",
                    status="MANUAL_REQUIRED",
                    purpose="Run one bounded turn and verify what gets persisted.",
                    automated_check="Attempted a scratch chat turn after the preview probe.",
                    expected_result="A persisted turn, transcript/log artifact, and active-set or trace data.",
                    what_it_means="Without a persisted turn, the audit cannot distinguish a live hum artifact from ordinary turn persistence surfaces.",
                    if_this_fails="Treat it as runtime harness failure, not hum absence.",
                    manual_follow_up="Inspect the chat path manually in the scratch runtime and rerun the audit.",
                    artifacts_missing=[{"journey_id": "HJ03", "name": "scratch_turn", "path": "", "note": error or "chat failed"}],
                    notes=[prompt_note],
                )
            )
        else:
            scratch_state["first_outcome"] = outcome
            render_scratch_conversation_log(runtime, session["id"], conversation_path)
            turn = outcome.turn
            metadata = parse_metadata_json(turn.get("metadata_json", ""))
            current_artifact_scan["motif_text_surfaces"].extend(
                [
                    turn.get("prompt_context", "") or "",
                    turn.get("membrane_text", "") or "",
                    safe_read_text(conversation_path),
                    safe_read_text(Path(scratch_context["scratch_runtime_log_path"])),
                ]
            )
            turn_hits = scan_object_for_hum(turn, path_hint="turn")
            turn_hits.extend(scan_object_for_hum(metadata, path_hint="turn.metadata"))
            current_artifact_scan["prompt_hum_hits"] = prompt_hits
            current_artifact_scan["turn_hum_hits"] = turn_hits
            runtime_log_hits = collect_runtime_log_hits(Path(scratch_context["scratch_runtime_log_path"]))
            current_artifact_scan["runtime_log_hum_hits"] = runtime_log_hits
            artifact_probe = probe_hum_artifact(
                runtime,
                experiment_id=experiment["id"],
                session_id=session["id"],
            )
            current_artifact_scan["artifact_probe"] = artifact_probe
            current_artifact_scan["runtime_hum_hits"] = (
                [
                    {
                        "path_hint": "hum_artifact",
                        "line": None,
                        "match": str(artifact_probe["json_path"]),
                    }
                ]
                if artifact_probe.get("valid")
                else []
            )
            current_artifact_scan["adjacent_surfaces"]["hj03"] = {
                "turn_id": turn["id"],
                "active_set_size": len(outcome.active_set),
                "trace_size": len(outcome.trace),
                "membrane_event_count": len(outcome.membrane_events),
                "conversation_log_path": str(conversation_path.resolve()),
                "hum_artifact_valid": artifact_probe.get("valid", False),
                "hum_json_path": artifact_probe.get("json_path"),
                "hum_markdown_path": artifact_probe.get("markdown_path"),
            }
            hj03_status = "PASS" if artifact_probe.get("valid") else "NOT_PRESENT"
            if artifact_probe.get("valid"):
                artifacts_found.extend(
                    [
                        path_artifact("HJ03", "hum_markdown", Path(str(artifact_probe["markdown_path"])), "Validated bounded hum markdown artifact after the first persisted turn."),
                        path_artifact("HJ03", "hum_json", Path(str(artifact_probe["json_path"])), "Validated bounded hum JSON artifact after the first persisted turn."),
                    ]
                )
            else:
                artifacts_missing.extend(
                    [
                        {
                            "journey_id": "HJ03",
                            "name": "hum_runtime_artifact",
                            "path": "",
                            "note": "No valid hum markdown/json artifact plus agreeing runtime/observatory references were emitted by the first persisted turn.",
                        },
                    ]
                )
            journeys.append(
                journey_result(
                    "HJ03",
                    status=hj03_status,
                    purpose="Run one bounded turn and verify what gets persisted.",
                    automated_check="Scanned preview prompt assembly when available, ran one scratch turn, re-rendered the conversation log, and then validated the hum markdown/json artifacts plus session snapshot and observatory reference blocks.",
                    expected_result="Either a valid hum artifact appears with provenance and agreeing references, or no such artifact appears in the first persisted turn.",
                    what_it_means="If the first persisted turn does not emit a valid hum artifact with matching runtime/export references, current live hum is not proved by the ordinary turn path.",
                    if_this_fails="If the turn cannot be persisted, the audit cannot separate hum absence from basic runtime failure.",
                    manual_follow_up="Inspect the persisted turn record and the session hum artifact paths manually only if the scratch chat path fails or the artifact probe disagrees.",
                    artifacts_found=[path_artifact("HJ03", "scratch_conversation_log", conversation_path, "Updated scratch conversation log after the first turn.")]
                    + (
                        [
                            path_artifact("HJ03", "hum_markdown", Path(str(artifact_probe["markdown_path"])), "Validated bounded hum markdown artifact."),
                            path_artifact("HJ03", "hum_json", Path(str(artifact_probe["json_path"])), "Validated bounded hum JSON artifact."),
                        ]
                        if artifact_probe.get("valid")
                        else []
                    ),
                    artifacts_missing=[
                        {
                            "journey_id": "HJ03",
                            "name": "hum_runtime_artifact",
                            "path": "",
                            "note": "No valid hum artifact found in the first persisted turn.",
                        }
                    ]
                    if not artifact_probe.get("valid")
                    else [],
                    notes=[prompt_note],
                    details={**current_artifact_scan["adjacent_surfaces"]["hj03"], "artifact_probe": artifact_probe},
                )
            )

    if scratch_state and scratch_state.get("first_outcome") is not None:
        session = scratch_state["session"]
        first_outcome = scratch_state["first_outcome"]
        turn_id = first_outcome.turn["id"]
        if runtime_caps["capabilities"].get("apply_feedback", False):
            ok, feedback, error = safe_call(
                runtime.apply_feedback,
                session_id=session["id"],
                turn_id=turn_id,
                verdict="edit",
                explanation="Keep continuity grounded in graph state and explicit feedback.",
                corrected_text="Adam persists by graph state, bounded retrieval, membrane discipline, and explicit feedback.",
            )
            if not ok:
                journeys.append(
                    journey_result(
                        "HJ04",
                        status="MANUAL_REQUIRED",
                        purpose="Test the explicit feedback path and separate it from hum claims.",
                        automated_check="Attempted one structured edit feedback event against the scratch turn.",
                        expected_result="Feedback persists through the existing explicit-feedback path.",
                        what_it_means="If explicit feedback cannot persist, continuity pressure itself is not proved in the current run.",
                        if_this_fails="Treat this as feedback-path failure, not hum evidence.",
                        manual_follow_up="Inspect apply_feedback and feedback_events persistence manually.",
                        artifacts_missing=[{"journey_id": "HJ04", "name": "feedback_event", "path": "", "note": error or "apply_feedback failed"}],
                    )
                )
            else:
                feedback_entries = runtime.store.list_feedback_for_turn(turn_id)
                retrieval_effect_state = "UNKNOWN"
                retrieval_note = "Retrieval influence was not inspected."
                retrieval_service = getattr(runtime, "retrieval_service", None)
                if retrieval_service is not None and callable(getattr(retrieval_service, "retrieve", None)):
                    ok, retrieval_payload, error = safe_call(
                        retrieval_service.retrieve,
                        experiment_id=scratch_state["experiment"]["id"],
                        session_id=session["id"],
                        query="graph state bounded retrieval membrane discipline explicit feedback",
                        settings=runtime.settings,
                    )
                    if ok:
                        items = retrieval_payload.get("items", [])
                        if any(item.get("source_kind") == "feedback" for item in items):
                            retrieval_effect_state = "PASS"
                            retrieval_note = "Current runtime surfaced feedback material through retrieval in the bounded scratch run."
                        else:
                            retrieval_effect_state = "UNKNOWN"
                            retrieval_note = "Feedback persistence was proved, but downstream retrieval influence was not deterministically exposed in this bounded run."
                    else:
                        retrieval_effect_state = "MANUAL_REQUIRED"
                        retrieval_note = error or "Retrieval path unavailable after feedback."
                current_artifact_scan["adjacent_surfaces"]["hj04"] = {
                    "feedback_count_for_turn": len(feedback_entries),
                    "retrieval_effect_state": retrieval_effect_state,
                }
                journeys.append(
                    journey_result(
                        "HJ04",
                        status="PASS",
                        purpose="Test the explicit-feedback path and separate it from hum claims.",
                        automated_check="Applied one structured edit feedback event, proved persistence through feedback_events, and inspected retrieval influence only if the current runtime exposed it deterministically.",
                        expected_result="Feedback persists as current architecture says it should, while any downstream retrieval effect remains optional evidence.",
                        what_it_means="This proves present-tense continuity pressure without pretending that explicit feedback, regard adjustment, or retrieval bias equals a hum surface.",
                        if_this_fails="If explicit feedback does not persist, the audit loses a real continuity surface and hum-adjacent interpretation becomes weaker.",
                        manual_follow_up="Inspect feedback_events and retrieval results manually only if the structured feedback event cannot be persisted or inspected.",
                        artifacts_found=[
                            {
                                "journey_id": "HJ04",
                                "name": "feedback_event_count",
                                "path": str(Path(scratch_context["scratch_db_path"]).resolve()),
                                "note": f"Persisted feedback events for first turn={len(feedback_entries)}.",
                            }
                        ],
                        notes=[retrieval_note],
                        details=current_artifact_scan["adjacent_surfaces"]["hj04"],
                    )
                )
        else:
            journeys.append(
                journey_result(
                    "HJ04",
                    status="MANUAL_REQUIRED",
                    purpose="Test the explicit-feedback path and separate it from hum claims.",
                    automated_check="Capability probe found no apply_feedback surface.",
                    expected_result="A structured feedback path that can be persisted and inspected.",
                    what_it_means="Without explicit feedback persistence, current continuity pressure is underproved.",
                    if_this_fails="Treat missing feedback capability as interface drift, not hum evidence.",
                    manual_follow_up="Inspect the runtime feedback path directly if the capability is missing.",
                )
            )

    if scratch_state and scratch_state.get("first_outcome") is not None and runtime_caps["capabilities"].get("chat", False):
        session = scratch_state["session"]
        conversation_path = Path(scratch_context["scratch_conversation_root"]) / f"{session['id']}.md"
        ok, second_outcome, error = safe_call(
            runtime.chat,
            session_id=session["id"],
            user_text="Continue from the same continuity state in one sentence.",
        )
        if not ok:
            journeys.append(
                journey_result(
                    "HJ05",
                    status="MANUAL_REQUIRED",
                    purpose="Check whether cross-turn recurrence yields a hum artifact or only normal persistence.",
                    automated_check="Attempted a second bounded scratch turn in the same session.",
                    expected_result="A second persisted turn for recurrence classification.",
                    what_it_means="Without a second turn, the audit cannot separate ordinary persistence from recurrence.",
                    if_this_fails="Treat it as a bounded runtime failure, not hum absence.",
                    manual_follow_up="Inspect the second-turn path manually if the scratch session cannot continue.",
                    artifacts_missing=[{"journey_id": "HJ05", "name": "second_turn", "path": "", "note": error or "Second turn failed."}],
                )
            )
        else:
            scratch_state["second_outcome"] = second_outcome
            render_scratch_conversation_log(runtime, session["id"], conversation_path)
            snapshot = build_local_session_snapshot(runtime, session["id"], conversation_path)
            first_ids = {item.get("node_id") for item in scratch_state["first_outcome"].active_set if item.get("node_id")}
            second_ids = {item.get("node_id") for item in second_outcome.active_set if item.get("node_id")}
            overlap = sorted(first_ids & second_ids)
            artifact_probe = probe_hum_artifact(
                runtime,
                experiment_id=scratch_state["experiment"]["id"],
                session_id=session["id"],
            )
            current_artifact_scan["artifact_probe"] = artifact_probe
            current_artifact_scan["runtime_hum_hits"] = (
                [
                    {
                        "path_hint": "hum_artifact",
                        "line": None,
                        "match": str(artifact_probe["json_path"]),
                    }
                ]
                if artifact_probe.get("valid")
                else []
            )
            if artifact_probe.get("valid"):
                continuity_classification = "hum artifact present"
            elif overlap:
                continuity_classification = "active-set recurrence only"
            elif snapshot["turn_count"] >= 2:
                continuity_classification = "ordinary persisted history only"
            else:
                continuity_classification = "unknown"
            current_artifact_scan["adjacent_surfaces"]["hj05"] = {
                "turn_count": snapshot["turn_count"],
                "feedback_count": snapshot["feedback_count"],
                "active_set_overlap_count": len(overlap),
                "continuity_classification": continuity_classification,
                "cross_turn_recurrence_present": artifact_probe.get("cross_turn_recurrence_present", False),
                "seed_state_only": artifact_probe.get("seed_state_only", False),
                "hum_json_path": artifact_probe.get("json_path"),
            }
            journeys.append(
                journey_result(
                    "HJ05",
                    status="PASS" if continuity_classification != "unknown" else "UNKNOWN",
                    purpose="Check whether cross-turn or cross-session recurrence yields a hum artifact or only normal persistence.",
                    automated_check="Ran a second bounded turn, rendered a fresh scratch conversation log, compared session history and active-set overlap, and inspected the refreshed hum JSON for recurrence versus seed-state.",
                    expected_result="Continuity can be classified as ordinary persisted history, active-set recurrence only, hum artifact present, or unknown, with the hum JSON stating whether recurrence is now present.",
                    what_it_means="This is where 'it feels continuous' must be separated from 'there is a live hum surface'.",
                    if_this_fails="If the second turn cannot persist, continuity classification remains incomplete.",
                    manual_follow_up="Inspect the second turn and session history manually only if the scratch session cannot continue.",
                    artifacts_found=[path_artifact("HJ05", "scratch_conversation_log", conversation_path, "Rendered a fresh scratch conversation log after the second turn.")]
                    + (
                        [
                            path_artifact("HJ05", "hum_json", Path(str(artifact_probe["json_path"])), "Refreshed hum JSON after the second turn.")
                        ]
                        if artifact_probe.get("valid")
                        else []
                    ),
                    notes=[
                        f"continuity_classification={continuity_classification}",
                        f"cross_turn_recurrence_present={artifact_probe.get('cross_turn_recurrence_present', False)}",
                        f"seed_state_only={artifact_probe.get('seed_state_only', False)}",
                    ],
                    details={**current_artifact_scan["adjacent_surfaces"]["hj05"], "artifact_probe": artifact_probe},
                )
            )

    if scratch_state and scratch_state.get("second_outcome") is not None:
        experiment = scratch_state["experiment"]
        session = scratch_state["session"]
        export_root = Path(scratch_context["scratch_export_root"])
        experiment_export_root = export_root / experiment["id"]
        payload_summaries: list[dict[str, Any]] = []
        observatory_hum_probe = {
            "index_hum": {},
            "overview_hum": {},
            "transcript_hum": {},
        }
        service = getattr(runtime, "observatory_service", None)
        exporter = getattr(runtime, "exporter", None)
        export_ok = False
        payload = {}
        if service is not None and callable(getattr(service, "refresh_exports", None)):
            ok, refresh_result, error = safe_call(service.refresh_exports, experiment_id=experiment["id"], session_id=session["id"])
            if ok:
                export_ok = True
                paths, payload = refresh_result
                payload_summaries.append({"surface": "refresh_exports", "keys": sorted(payload.keys())})
                observatory_hum_probe["index_hum"] = payload.get("index", {}).get("hum", {}) if isinstance(payload.get("index"), dict) else {}
            else:
                payload_summaries.append({"surface": "refresh_exports", "error": error})
        elif exporter is not None and callable(getattr(exporter, "export_all", None)):
            ok, paths, error = safe_call(
                exporter.export_all,
                experiment_id=experiment["id"],
                session_id=session["id"],
                out_dir=experiment_export_root,
            )
            if ok:
                export_ok = True
                payload_summaries.append({"surface": "exporter.export_all", "keys": sorted(paths.keys())})
            else:
                payload_summaries.append({"surface": "exporter.export_all", "error": error})

        if service is not None:
            for method_name in (
                "experiment_overview",
                "graph_payload",
                "basin_payload",
                "measurement_payload",
                "session_turns",
                "session_active_set",
            ):
                method = getattr(service, method_name, None)
                if not callable(method):
                    payload_summaries.append({"surface": method_name, "status": "missing"})
                    continue
                kwargs = {"experiment_id": experiment["id"], "session_id": session["id"]}
                if method_name.startswith("session_"):
                    kwargs = {"session_id": session["id"]}
                ok, method_payload, error = safe_call(method, **kwargs)
                if ok:
                    payload_summaries.append({"surface": method_name, "status": "ok"})
                    if method_name == "experiment_overview":
                        observatory_hum_probe["overview_hum"] = method_payload.get("hum", {}) if isinstance(method_payload, dict) else {}
                    if method_name == "session_turns":
                        observatory_hum_probe["transcript_hum"] = method_payload.get("hum", {}) if isinstance(method_payload, dict) else {}
                else:
                    payload_summaries.append({"surface": method_name, "status": "error", "error": error})

        index_path = experiment_export_root / "observatory_index.json"
        if index_path.exists() and not observatory_hum_probe["index_hum"]:
            try:
                observatory_hum_probe["index_hum"] = json.loads(index_path.read_text(encoding="utf-8")).get("hum", {})
            except json.JSONDecodeError:
                observatory_hum_probe["index_hum"] = {}

        artifact_probe = current_artifact_scan.get("artifact_probe", {})
        hum_surface_present = any(
            hum_reference_matches(reference, artifact_probe.get("hum_snapshot", {}))
            for reference in (
                observatory_hum_probe["index_hum"],
                observatory_hum_probe["overview_hum"],
                observatory_hum_probe["transcript_hum"],
            )
        )
        current_artifact_scan["export_hum_hits"] = (
            [{"path": str(index_path.resolve()), "line": None, "match": "observatory_index.hum", "relative_path": repo_relative(index_path)}]
            if hum_surface_present and index_path.exists()
            else []
        )
        current_artifact_scan["observatory_payload_hum_hits"] = (
            [{"path_hint": "observatory.hum", "line": None, "match": "hum reference block present"}] if hum_surface_present else []
        )
        current_artifact_scan["observatory_hum_probe"] = observatory_hum_probe
        current_artifact_scan["adjacent_surfaces"]["hj06"] = {
            "export_ok": export_ok,
            "export_root": str(experiment_export_root.resolve()),
            "payload_summaries": payload_summaries,
            "observatory_hum_probe": observatory_hum_probe,
        }
        journeys.append(
            journey_result(
                "HJ06",
                status="PASS" if hum_surface_present else "NOT_PRESENT" if export_ok else "MANUAL_REQUIRED",
                purpose="Check whether the export and observatory layer currently knows about hum.",
                automated_check="Refreshed scratch exports or exporter output without opening a browser, then inspected observatory_index.json plus direct overview/transcript payload blocks for matching hum references.",
                expected_result="Hum is either visible in exports/observatory/API reference surfaces or absent there.",
                what_it_means="Absence here matters because current EDEN already foregrounds observability elsewhere. If hum is live but not surfaced, that is a different claim from full absence.",
                if_this_fails="If exports or payload methods are unavailable, classify interface drift separately from hum absence.",
                manual_follow_up="Only inspect the browser/HTTP observatory manually if the scratch export surface or direct payload methods are unavailable.",
                artifacts_found=[path_artifact("HJ06", "scratch_export_root", experiment_export_root, "Scratch observability artifacts were emitted here.")],
                artifacts_missing=[
                    {"journey_id": "HJ06", "name": "hum_export_surface", "path": "", "note": "No matching hum reference block was found in observatory_index.json, experiment_overview(), or session_turns()."}
                ]
                if export_ok and not hum_surface_present
                else [],
                notes=[f"payload_methods_checked={len(payload_summaries)}"],
                details=current_artifact_scan["adjacent_surfaces"]["hj06"],
            )
        )

    if historical_hum_path is None:
        journeys.append(
            journey_result(
                "HJ07",
                status="MANUAL_REQUIRED",
                purpose="Use the historical artifact honestly without letting it masquerade as current proof.",
                automated_check="Historical comparison was skipped because --historical-hum was not provided.",
                expected_result="A structural comparison only when the external artifact is supplied.",
                what_it_means="Current runtime absence or docs-only status can still be classified, but historical-to-current structural comparison remains open.",
                if_this_fails="Treat missing external artifact input as an omitted optional enrichment, not as an audit failure.",
                manual_follow_up="Rerun the audit with --historical-hum /Users/brianray/Desktop/adam_hum_ALL.md to compare current artifacts against the historical hum file.",
            )
        )
    else:
        historical_scan = parse_historical_hum(historical_hum_path)
        comparison_scan = compare_historical_to_current(historical_scan, current_artifact_scan)
        journeys.append(
            journey_result(
                "HJ07",
                status="PASS" if comparison_scan["current_analog_present"] else "HISTORICAL_ONLY",
                purpose="Use the historical artifact honestly without letting it masquerade as current proof.",
                automated_check="Parsed historical timestamps and HUM_* markers, collected recurrent motifs, and compared them structurally against current runtime artifacts only.",
                expected_result="Historical hum artifact present, with current analog either present or absent without semantic overreach.",
                what_it_means="This distinguishes a real historical continuity artifact from any claim that the present build still emits a homologous live surface.",
                if_this_fails="If the historical file cannot be parsed, the audit loses the structural comparison but not the current-runtime classification.",
                manual_follow_up="Inspect the historical hum file directly only if parsing fails or if you want to read full motif recurrence by hand.",
                artifacts_found=[
                    {
                        "journey_id": "HJ07",
                        "name": "historical_hum_artifact",
                        "path": str(historical_hum_path.resolve()),
                        "note": f"Parsed hum_line_count={historical_scan['hum_line_count']} and timestamp_count={historical_scan['timestamp_count']}.",
                    }
                ],
                notes=[f"current_analog_present={comparison_scan['current_analog_present']}"],
                details=comparison_scan,
            )
        )

    runtime_hum_validated = bool(current_artifact_scan.get("artifact_probe", {}).get("valid"))
    path_state = classify_path_state(
        claim_inventory,
        current_artifact_scan["runtime_hum_hits"] + current_artifact_scan["export_hum_hits"] + current_artifact_scan["observatory_payload_hum_hits"],
        historical_hum_path is not None,
    )
    journeys.append(
        journey_result(
            "HJ08",
            status=path_state["outcome"],
            purpose="Determine whether hum is live code, dormant code, docs-only, historical-only, or missing entirely.",
            automated_check="Collapsed static claim inventory plus current runtime/export scans into a dead-path versus live-path classification.",
            expected_result="Each discovered hum-relevant path is classified by truth register rather than vibes.",
            what_it_means="This is the audit spine: it tells the operator whether the current repo exposes hum as runtime, history, docs, or stale residue.",
            if_this_fails="If the audit cannot classify paths, the repo needs a cleaner claim surface before hum can be troubleshot honestly.",
            manual_follow_up="Inspect the exact classified paths only if you need to verify why a surface landed in docs-only, historical-only, or stale-residue status.",
            notes=[f"path_classifications={len(path_state['path_classifications'])}"],
            details=path_state,
        )
    )

    status_register = build_final_status_register(runtime_hum_validated)
    journeys.append(
        journey_result(
            "HJ09",
            status="PASS",
            purpose="Produce the hum-specific truth register from current evidence.",
            automated_check="Collapsed journey evidence into Implemented, Instrumented, Conceptual, and Unknown hum-specific lines.",
            expected_result="One conservative hum status register for the current build.",
            what_it_means="This is the single compact register the operator should trust before doing any manual hum exploration.",
            if_this_fails="If the status register cannot be produced, the audit loses its operator-facing summary contract.",
            manual_follow_up="Read the generated STATUS_REGISTER in the markdown report and compare it against docs/HUM_SPEC.md only if the lines look suspicious.",
            details={"status_register": status_register},
        )
    )

    next_shortest_proof_paths = build_next_shortest_proof_paths(
        runtime_caps=runtime_caps,
        observatory_caps=observatory_caps,
        historical_path=historical_hum_path,
        runtime_hum_validated=runtime_hum_validated,
    )
    journeys.append(
        journey_result(
            "HJ10",
            status="PASS",
            purpose="For every unresolved unknown, name the exact artifact or code path needed next.",
            automated_check="Generated one bounded next proof path per remaining unknown or audit limit.",
            expected_result="A short follow-up list where each step names one exact artifact, one reason, and whether it is automatable or manual.",
            what_it_means="This keeps the audit from dissolving into fog. Every remaining uncertainty gets a shortest route out.",
            if_this_fails="If no next proof paths are produced, the audit is missing its operator handoff.",
            manual_follow_up="Use the generated list as the only follow-up queue; do not broaden scope until one of those proof paths lands.",
            details={"next_shortest_proof_paths": next_shortest_proof_paths},
        )
    )

    historical_status = "MANUAL_REQUIRED"
    if historical_hum_path is not None:
        historical_status = "PASS" if comparison_scan and comparison_scan.get("current_analog_present") else "HISTORICAL_ONLY"

    final_classification = {
        "current_live_hum": "PASS" if runtime_hum_validated else "NOT_PRESENT",
        "claim_surface": path_state["outcome"],
        "historical_comparison": historical_status,
        "summary": (
            "Current repo/runtime audit did not prove a live hum surface."
            if not runtime_hum_validated
            else "Current run produced explicit hum-specific runtime evidence."
        ),
    }

    unknowns = [step for step in next_shortest_proof_paths]
    artifact_scan = {
        "runtime_hum_hits": current_artifact_scan["runtime_hum_hits"],
        "prompt_hum_hits": current_artifact_scan["prompt_hum_hits"],
        "turn_hum_hits": current_artifact_scan["turn_hum_hits"],
        "runtime_log_hum_hits": current_artifact_scan["runtime_log_hum_hits"],
        "export_hum_hits": current_artifact_scan["export_hum_hits"],
        "observatory_payload_hum_hits": current_artifact_scan["observatory_payload_hum_hits"],
        "artifact_probe": current_artifact_scan["artifact_probe"],
        "observatory_hum_probe": current_artifact_scan["observatory_hum_probe"],
        "adjacent_surfaces": current_artifact_scan["adjacent_surfaces"],
        "historical_scan": historical_scan,
        "historical_comparison": comparison_scan,
    }

    all_artifacts_found = list(artifacts_found)
    all_artifacts_missing = list(artifacts_missing)
    for journey in journeys:
        all_artifacts_found.extend(journey.get("artifacts_found", []))
        all_artifacts_missing.extend(journey.get("artifacts_missing", []))
    close_runtime(runtime)

    return {
        "status_register": status_register,
        "run_context": run_context,
        "claim_inventory": claim_inventory,
        "journeys": journeys,
        "artifacts_found": all_artifacts_found,
        "artifacts_missing": all_artifacts_missing,
        "final_classification": final_classification,
        "unknowns": unknowns,
        "next_shortest_proof_paths": next_shortest_proof_paths,
        "hum_artifact_scan": artifact_scan,
    }


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# STATUS_REGISTER",
        "",
        f"- Implemented: {report['status_register']['Implemented']}",
        f"- Instrumented: {report['status_register']['Instrumented']}",
        f"- Conceptual: {report['status_register']['Conceptual']}",
        f"- Unknown: {report['status_register']['Unknown']}",
        "",
        "# RUN_CONTEXT",
        "",
    ]
    for key, value in report["run_context"].items():
        if isinstance(value, list):
            display = ", ".join(str(item) for item in value) if value else "none"
        elif isinstance(value, dict):
            display = json.dumps(value, indent=2, sort_keys=True)
        else:
            display = str(value)
        lines.append(f"- {key}: {display}")
    lines.extend(["", "# JOURNEY_RESULTS", ""])
    for journey in report["journeys"]:
        lines.extend(
            [
                f"## {journey['id']} - {journey['title']}",
                "",
                f"- Status: {journey['status']}",
                f"- Purpose: {journey['purpose']}",
                f"- Automated check: {journey['automated_check']}",
                f"- Expected result: {journey['expected_result']}",
                f"- What this means for the hum: {journey['what_this_means_for_the_hum']}",
                f"- If this fails: {journey['if_this_fails']}",
                f"- Manual follow-up only if needed: {journey['manual_follow_up_only_if_needed']}",
            ]
        )
        if journey["notes"]:
            lines.append("- Notes:")
            for note in journey["notes"]:
                lines.append(f"  - {note}")
        if journey["artifacts_found"]:
            lines.append("- Artifacts found:")
            for artifact in journey["artifacts_found"]:
                lines.append(f"  - {artifact['name']}: {artifact['note']}")
        if journey["artifacts_missing"]:
            lines.append("- Artifacts missing:")
            for artifact in journey["artifacts_missing"]:
                lines.append(f"  - {artifact['name']}: {artifact['note']}")
        if journey["details"]:
            lines.append("- Details:")
            details_json = json.dumps(journey["details"], indent=2, sort_keys=True)
            for detail_line in details_json.splitlines():
                lines.append(f"  {detail_line}")
        lines.append("")
    lines.extend(["# FAILURE_INTERPRETATION", ""])
    for status, explanation in FAILURE_INTERPRETATION.items():
        lines.append(f"- {status}: {explanation}")
    lines.extend(["", "# FINAL_CLASSIFICATION", ""])
    for key, value in report["final_classification"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "# NEXT_SHORTEST_PROOF_PATHS", ""])
    if report["next_shortest_proof_paths"]:
        for index, step in enumerate(report["next_shortest_proof_paths"], start=1):
            lines.append(f"{index}. target: {step['target']}")
            lines.append(f"   reason: {step['reason']}")
            lines.append(f"   mode: {step['mode']}")
    else:
        lines.append("1. None. The audit did not leave unresolved hum-specific unknowns.")
    lines.append("")
    return "\n".join(lines)


def render_next_shortest_proof_paths(paths: list[dict[str, Any]]) -> str:
    if not paths:
        return "# NEXT_SHORTEST_PROOF_PATHS\n\n1. None. The audit did not leave unresolved hum-specific unknowns.\n"
    lines = ["# NEXT_SHORTEST_PROOF_PATHS", ""]
    for index, step in enumerate(paths, start=1):
        lines.append(f"{index}. target: {step['target']}")
        lines.append(f"   reason: {step['reason']}")
        lines.append(f"   mode: {step['mode']}")
    lines.append("")
    return "\n".join(lines)


def write_report_bundle(report: dict[str, Any], out_dir: Path) -> dict[str, str]:
    ensure_dir(out_dir)
    report_json_path = out_dir / "hum_audit_report.json"
    report_md_path = out_dir / "hum_audit_report.md"
    claim_inventory_path = out_dir / "hum_claim_inventory.json"
    artifact_scan_path = out_dir / "hum_artifact_scan.json"
    journey_results_path = out_dir / "journey_results.json"
    next_paths_path = out_dir / "next_shortest_proof_paths.md"

    report_json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    report_md_path.write_text(render_markdown_report(report), encoding="utf-8")
    claim_inventory_path.write_text(json.dumps(report["claim_inventory"], indent=2, sort_keys=True), encoding="utf-8")
    artifact_scan_path.write_text(json.dumps(report["hum_artifact_scan"], indent=2, sort_keys=True), encoding="utf-8")
    journey_results_path.write_text(json.dumps(report["journeys"], indent=2, sort_keys=True), encoding="utf-8")
    next_paths_path.write_text(render_next_shortest_proof_paths(report["next_shortest_proof_paths"]), encoding="utf-8")
    return {
        "hum_audit_report_json": str(report_json_path.resolve()),
        "hum_audit_report_md": str(report_md_path.resolve()),
        "hum_claim_inventory_json": str(claim_inventory_path.resolve()),
        "hum_artifact_scan_json": str(artifact_scan_path.resolve()),
        "journey_results_json": str(journey_results_path.resolve()),
        "next_shortest_proof_paths_md": str(next_paths_path.resolve()),
    }


def build_partial_failure_report(out_dir: Path, error: Exception) -> dict[str, Any]:
    return {
        "status_register": dict(BASELINE_STATUS_REGISTER),
        "run_context": {
            "git_commit_sha": gather_git_head(),
            "audit_timestamp": now_utc(),
            "python_version": platform.python_version(),
            "backend": DEFAULT_BACKEND,
            "scratch_db_path": str((out_dir / "_scratch" / "eden.db").resolve()),
            "scratch_runtime_log_path": str((out_dir / "_scratch" / "runtime.jsonl").resolve()),
            "scratch_export_root": str((out_dir / "scratch_exports").resolve()),
            "scratch_hum_root": str((out_dir / "scratch_hum").resolve()),
            "current_repo_data_scanned": False,
            "external_historical_hum_provided": False,
            "runtime_capability_probe_succeeded": False,
            "failure": f"{type(error).__name__}: {error}",
        },
        "claim_inventory": [],
        "journeys": [
            journey_result(
                "HJ01",
                status="MANUAL_REQUIRED",
                purpose="Partial failure report.",
                automated_check="Audit infrastructure failed before journey execution completed.",
                expected_result="Partial report if possible.",
                what_it_means="The audit machinery failed before it could classify hum honestly.",
                if_this_fails="Inspect the traceback and rerun the script after fixing the infrastructure error.",
                manual_follow_up="Check the script traceback and the scratch output path.",
                details={"traceback": traceback.format_exc()},
            )
        ],
        "artifacts_found": [],
        "artifacts_missing": [{"journey_id": "HJ01", "name": "audit_infrastructure", "path": "", "note": f"{type(error).__name__}: {error}"}],
        "final_classification": {
            "current_live_hum": "UNKNOWN",
            "claim_surface": "UNKNOWN",
            "historical_comparison": "UNKNOWN",
            "summary": "Audit infrastructure failed before hum classification could complete.",
        },
        "unknowns": [],
        "next_shortest_proof_paths": [],
        "hum_artifact_scan": {},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the hum user-journey audit in scratch scope.")
    parser.add_argument("--out", required=True, help="Output bundle directory.")
    parser.add_argument("--historical-hum", default=None, help="Optional historical hum artifact to compare structurally.")
    args = parser.parse_args(argv)

    out_dir = Path(args.out).expanduser().resolve()
    historical_hum_path = Path(args.historical_hum).expanduser().resolve() if args.historical_hum else None
    if historical_hum_path is not None and not historical_hum_path.exists():
        print(json.dumps({"ok": False, "error": f"Historical hum artifact not found: {historical_hum_path}"}, indent=2), file=sys.stderr)
        return 2

    try:
        report = run_journeys(out_dir=out_dir, historical_hum_path=historical_hum_path)
        bundle = write_report_bundle(report, out_dir)
    except Exception as exc:  # pragma: no cover - exercised through script failure path
        try:
            partial_report = build_partial_failure_report(out_dir, exc)
            bundle = write_report_bundle(partial_report, out_dir)
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}", "bundle": bundle}, indent=2), file=sys.stderr)
        except Exception:
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "bundle": bundle, "final_classification": report["final_classification"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
