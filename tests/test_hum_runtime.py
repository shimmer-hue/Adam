from __future__ import annotations

import json
from pathlib import Path


HUM_REQUIRED_FIELDS = {
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
    "surface_lines",
    "surface_stats",
    "token_table",
}


def _load_hum_payload(runtime, session_id: str) -> tuple[dict[str, object], Path, Path]:
    snapshot = runtime.hum_snapshot(session_id)
    markdown_path = Path(str(snapshot["markdown_path"]))
    json_path = Path(str(snapshot["json_path"]))
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return payload, markdown_path, json_path


def test_first_turn_emits_bounded_session_scoped_hum_artifacts(runtime) -> None:
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(experiment["id"], title="Hum Seed")

    runtime.chat(session_id=session["id"], user_text="Describe the current continuity surfaces briefly.")

    hum_snapshot = runtime.hum_snapshot(session["id"])
    payload, markdown_path, json_path = _load_hum_payload(runtime, session["id"])

    assert hum_snapshot["present"] is True
    assert markdown_path.exists()
    assert json_path.exists()
    assert experiment["id"] in markdown_path.parts
    assert session["id"] in markdown_path.parts
    assert experiment["id"] in json_path.parts
    assert session["id"] in json_path.parts
    assert HUM_REQUIRED_FIELDS.issubset(payload)
    assert payload["artifact_version"] == "hum.v1"
    assert payload["derived_from"] == ["turns.active_set_json", "feedback_events", "membrane_events"]
    assert payload["metrics"]["char_count"] <= payload["boundedness"]["max_text_chars"]
    assert payload["metrics"]["line_count"] <= payload["boundedness"]["max_lines"]
    assert payload["metrics"]["turn_window_size"] == 1
    assert payload["status"]["cross_turn_recurrence_present"] is False
    assert payload["surface_lines"]
    assert payload["surface_lines"][0].startswith("[T0] hum:")
    assert payload["surface_stats"]["entries"] == 1
    assert payload["surface_stats"]["words"] >= 2
    assert payload["token_table"]
    assert payload["text_surface"].startswith("[T0] hum:")

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "[T0] hum:" in markdown
    assert "[HUM_STATS]" in markdown
    assert "[HUM_METRICS]" in markdown
    assert "[HUM_TABLE]" in markdown


def test_second_turn_updates_overlap_and_recurrence_metrics(runtime) -> None:
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(experiment["id"], title="Hum Continuity")

    runtime.chat(session_id=session["id"], user_text="Describe continuity surfaces briefly.")
    runtime.chat(session_id=session["id"], user_text="Continue from the same continuity state.")

    payload, _, _ = _load_hum_payload(runtime, session["id"])
    overlap = payload["continuity"]["active_set_overlap"]

    assert payload["metrics"]["turn_window_size"] == 2
    assert payload["latest_turn_id"] == payload["turn_ids"][-1]
    assert overlap["latest_turn_id"] == payload["turn_ids"][-1]
    assert overlap["previous_turn_id"] == payload["turn_ids"][-2]
    assert isinstance(overlap["count"], int)
    assert isinstance(payload["status"]["cross_turn_recurrence_present"], bool)
    assert payload["surface_stats"]["entries"] == 2
    assert payload["text_surface"].count("[T") >= 2


def test_feedback_refreshes_hum_without_prompt_injection(runtime) -> None:
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(experiment["id"], title="Hum Feedback")

    first = runtime.chat(session_id=session["id"], user_text="Describe continuity surfaces briefly.")
    runtime.apply_feedback(
        session_id=session["id"],
        turn_id=first.turn["id"],
        verdict="edit",
        explanation="Ground the reply in graph state and explicit feedback.",
        corrected_text="Continuity is grounded in graph state, bounded retrieval, membrane discipline, and explicit feedback.",
    )

    payload, _, json_path = _load_hum_payload(runtime, session["id"])
    preview = runtime.preview_turn(session_id=session["id"], user_text="Continue the same continuity state.")
    combined_prompt = "\n".join(
        [
            preview.system_prompt,
            preview.conversation_prompt,
            preview.history_context,
            preview.feedback_context,
        ]
    )

    assert payload["status"]["feedback_present"] is True
    assert payload["metrics"]["feedback_event_count"] >= 1
    assert payload["continuity"]["feedback_summary"]["counts"]["edit"] >= 1
    assert str(json_path) not in combined_prompt
    assert "current_hum.md" not in combined_prompt
    assert "current_hum.json" not in combined_prompt


def test_session_snapshot_and_observatory_surfaces_reference_hum(runtime, tmp_path) -> None:
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(experiment["id"], title="Hum Snapshot")

    runtime.chat(session_id=session["id"], user_text="Describe continuity surfaces briefly.")

    snapshot = runtime.session_state_snapshot(session["id"])
    overview = runtime.observatory_service.experiment_overview(experiment_id=experiment["id"], session_id=session["id"])
    turns = runtime.observatory_service.session_turns(session_id=session["id"])

    export_root = tmp_path / "exports"
    runtime.exporter.export_all(experiment_id=experiment["id"], session_id=session["id"], out_dir=export_root)
    observatory_index = json.loads((export_root / "observatory_index.json").read_text(encoding="utf-8"))
    conversation_log = Path(snapshot["conversation_log_path"]).read_text(encoding="utf-8")

    assert snapshot["hum"]["present"] is True
    assert overview["hum"]["present"] is True
    assert turns["hum"]["present"] is True
    assert overview["hum"]["json_path"] == snapshot["hum"]["json_path"]
    assert turns["hum"]["json_path"] == snapshot["hum"]["json_path"]
    assert observatory_index["hum"]["present"] is True
    assert observatory_index["hum"]["json_path"] == snapshot["hum"]["json_path"]
    assert "### Hum" in conversation_log
    assert snapshot["hum"]["artifact_version"] == "hum.v1"
    assert snapshot["hum"]["surface_lines"]
