from __future__ import annotations

import json


def test_blank_bootstrap_chat_feedback_and_exports(runtime, tmp_path) -> None:
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(experiment["id"], title="E2E")
    counts_before = runtime.store.graph_counts(experiment["id"])

    outcome = runtime.chat(session_id=session["id"], user_text="How does Adam remain the same persona over time?")
    counts_after = runtime.store.graph_counts(experiment["id"])

    assert outcome.turn["turn_index"] == 0
    assert counts_after["turns"] == counts_before["turns"] + 1
    assert counts_after["memes"] > counts_before["memes"]
    assert len(outcome.active_set) > 0
    assert outcome.profile["requested_mode"] == "manual"
    assert outcome.budget["prompt_budget_tokens"] > 0

    turn_metadata = json.loads(outcome.turn["metadata_json"])
    assert turn_metadata["budget"]["remaining_input_tokens"] >= 0
    assert turn_metadata["inference_profile"]["profile_name"].startswith("manual:")

    feedback = runtime.apply_feedback(
        session_id=session["id"],
        turn_id=outcome.turn["id"],
        verdict="edit",
        explanation="Mention the persistent graph explicitly.",
        corrected_text="Adam persists through graph state, regard updates, and retrieval selection.",
    )
    assert feedback["corrected_text"].startswith("Adam persists through graph state")

    retrieval = runtime.retrieval_service.retrieve(
        experiment_id=experiment["id"],
        session_id=session["id"],
        query="persistent graph state regard retrieval selection",
        settings=runtime.settings,
    )
    assert any(item["source_kind"] == "feedback" or "graph state" in item["text"].lower() for item in retrieval["items"])

    export_paths = runtime.exporter.export_all(
        experiment_id=experiment["id"],
        session_id=session["id"],
        out_dir=tmp_path / "exports",
    )
    assert (tmp_path / "exports" / "graph_knowledge_base.html").exists()
    assert (tmp_path / "exports" / "behavioral_attractor_basin.html").exists()
    assert (tmp_path / "exports" / "geometry_lab.html").exists()
    assert (tmp_path / "exports" / "measurement_ledger.html").exists()
    assert (tmp_path / "exports" / "observatory_index.html").exists()
    assert export_paths["graph_html"].endswith(".html")
    geometry_payload = json.loads((tmp_path / "exports" / "geometry_diagnostics.json").read_text())
    assert "local_reports" in geometry_payload
