from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "run_hum_user_journey_audit.py"


def load_audit_module():
    spec = importlib.util.spec_from_file_location("hum_user_journey_audit", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def audit_module():
    return load_audit_module()


def test_scan_claims_finds_repo_hum_surfaces(audit_module) -> None:
    inventory = audit_module.scan_claims()

    assert inventory
    assert any(item["relative_path"] == "docs/HUM_SPEC.md" for item in inventory)
    assert any(item["classification"] == "docs_spec_wording" for item in inventory)


def test_probe_runtime_capabilities_downgrades_missing_hooks(audit_module) -> None:
    class DummyRuntime:
        def chat(self) -> None:
            return None

    caps = audit_module.probe_runtime_capabilities(DummyRuntime())
    observatory_caps = audit_module.probe_observatory_capabilities(DummyRuntime())

    assert caps["required_ready"] is False
    assert "initialize_experiment" in caps["missing_capabilities"]
    assert "preview_turn" in caps["missing_capabilities"]
    assert "service.refresh_exports" in observatory_caps["missing_capabilities"]


def test_parse_historical_hum_extracts_markers_and_motifs(tmp_path: Path, audit_module) -> None:
    historical_path = tmp_path / "adam_hum_ALL.md"
    historical_path.write_text(
        "\n".join(
            [
                "[2026-01-26 12:09:18 EST] hum: glmmr mrmr hush",
                "[HUM_STATS]",
                "lines=2",
                "[2026-01-26 12:20:33 EST] hum: pulse thread bloom glmmr",
                "[HUM_METRICS]",
                "motifs=6",
                "[HUM_TABLE]",
                "glmmr | 2",
            ]
        ),
        encoding="utf-8",
    )

    parsed = audit_module.parse_historical_hum(historical_path)

    assert parsed["timestamp_count"] == 2
    assert parsed["hum_line_count"] == 2
    assert parsed["section_markers"] == ["[HUM_STATS]", "[HUM_METRICS]", "[HUM_TABLE]"]
    assert parsed["motif_counts"]["glmmr"] == 2
    assert parsed["motif_counts"]["bloom"] == 1


def test_run_journeys_validates_live_hum_and_emits_reports(tmp_path: Path, audit_module) -> None:
    out_dir = tmp_path / "hum_audit"
    report = audit_module.run_journeys(out_dir=out_dir, historical_hum_path=None)
    bundle = audit_module.write_report_bundle(report, out_dir)

    assert report["final_classification"]["current_live_hum"] == "PASS"
    assert report["final_classification"]["historical_comparison"] == "MANUAL_REQUIRED"
    assert report["status_register"]["Implemented"].startswith("Current run produced a bounded persisted hum artifact")
    assert Path(bundle["hum_audit_report_json"]).exists()
    assert Path(bundle["hum_audit_report_md"]).exists()
    assert Path(bundle["hum_claim_inventory_json"]).exists()
    assert Path(bundle["hum_artifact_scan_json"]).exists()
    assert Path(bundle["journey_results_json"]).exists()
    assert Path(bundle["next_shortest_proof_paths_md"]).exists()

    markdown = Path(bundle["hum_audit_report_md"]).read_text(encoding="utf-8")
    status_idx = markdown.index("# STATUS_REGISTER")
    context_idx = markdown.index("# RUN_CONTEXT")
    journeys_idx = markdown.index("# JOURNEY_RESULTS")
    failure_idx = markdown.index("# FAILURE_INTERPRETATION")
    final_idx = markdown.index("# FINAL_CLASSIFICATION")
    next_idx = markdown.index("# NEXT_SHORTEST_PROOF_PATHS")

    assert [status_idx, context_idx, journeys_idx, failure_idx, final_idx, next_idx] == sorted(
        [status_idx, context_idx, journeys_idx, failure_idx, final_idx, next_idx]
    )

    journey_map = {journey["id"]: journey for journey in report["journeys"]}
    assert journey_map["HJ01"]["status"] == "PASS"
    assert journey_map["HJ03"]["status"] == "PASS"
    assert journey_map["HJ06"]["status"] == "PASS"
    artifact_probe = report["hum_artifact_scan"]["artifact_probe"]
    assert artifact_probe["valid"] is True
    assert artifact_probe["markdown_exists"] is True
    assert artifact_probe["json_exists"] is True
    assert artifact_probe["required_fields_present"] is True


def test_run_journeys_forced_no_hum_still_classifies_absence_cleanly(
    tmp_path: Path,
    audit_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_probe = audit_module.probe_hum_artifact

    def forced_probe(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = original_probe(*args, **kwargs)
        result.update(
            {
                "valid": False,
                "hum_snapshot": {
                    "present": False,
                    "artifact_version": "hum.v1",
                    "generated_at": None,
                    "markdown_path": result.get("markdown_path"),
                    "json_path": result.get("json_path"),
                    "latest_turn_id": None,
                    "turn_window_size": 0,
                    "cross_turn_recurrence_present": False,
                },
                "session_snapshot_hum": {},
                "overview_hum": {},
                "transcript_hum": {},
                "cross_turn_recurrence_present": False,
                "seed_state_only": False,
            }
        )
        return result

    monkeypatch.setattr(audit_module, "probe_hum_artifact", forced_probe)

    out_dir = tmp_path / "forced_no_hum"
    report = audit_module.run_journeys(out_dir=out_dir, historical_hum_path=None)

    assert report["final_classification"]["current_live_hum"] == "NOT_PRESENT"
    assert report["status_register"]["Implemented"].startswith("No current repo-tracked first-class hum runtime surface")
    journey_map = {journey["id"]: journey for journey in report["journeys"]}
    assert journey_map["HJ03"]["status"] == "NOT_PRESENT"
    assert journey_map["HJ06"]["status"] in {"NOT_PRESENT", "MANUAL_REQUIRED"}


def test_main_returns_zero_for_completed_audit_with_live_hum(tmp_path: Path, audit_module) -> None:
    out_dir = tmp_path / "main_ok"
    exit_code = audit_module.main(["--out", str(out_dir)])

    assert exit_code == 0
    report = json.loads((out_dir / "hum_audit_report.json").read_text(encoding="utf-8"))
    assert report["final_classification"]["current_live_hum"] == "PASS"


def test_main_returns_zero_for_forced_no_hum_audit(
    tmp_path: Path,
    audit_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_run_journeys = audit_module.run_journeys

    def forced_no_hum(*args: Any, **kwargs: Any) -> dict[str, Any]:
        report = original_run_journeys(*args, **kwargs)
        report["status_register"] = dict(audit_module.BASELINE_STATUS_REGISTER)
        report["final_classification"] = {
            "current_live_hum": "NOT_PRESENT",
            "claim_surface": report["final_classification"]["claim_surface"],
            "historical_comparison": report["final_classification"]["historical_comparison"],
            "summary": "Forced no-hum audit path for exit-code verification.",
        }
        return report

    monkeypatch.setattr(audit_module, "run_journeys", forced_no_hum)

    out_dir = tmp_path / "main_forced_no_hum"
    exit_code = audit_module.main(["--out", str(out_dir)])

    assert exit_code == 0
    report = json.loads((out_dir / "hum_audit_report.json").read_text(encoding="utf-8"))
    assert report["final_classification"]["current_live_hum"] == "NOT_PRESENT"


def test_main_returns_nonzero_for_infrastructure_failure(tmp_path: Path, audit_module, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise OSError("forced bundle failure")

    monkeypatch.setattr(audit_module, "write_report_bundle", boom)

    exit_code = audit_module.main(["--out", str(tmp_path / "main_fail")])

    assert exit_code == 1
