from __future__ import annotations

import json

import eden.runtime as runtime_module
from eden.config import DEFAULT_MLX_MODEL_DIR


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
    assert outcome.turn["user_text"].startswith("Brian the operator:")
    assert "Answer:" not in outcome.turn["membrane_text"]
    assert "Basis:" not in outcome.turn["membrane_text"]
    assert "Next Step:" not in outcome.turn["membrane_text"]

    turn_metadata = json.loads(outcome.turn["metadata_json"])
    assert turn_metadata["budget"]["remaining_input_tokens"] >= 0
    assert turn_metadata["inference_profile"]["profile_name"].startswith("manual:")
    assert turn_metadata["operator_input_raw"] == "How does Adam remain the same persona over time?"

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


def test_runtime_launch_profile_and_session_snapshot(runtime) -> None:
    updated = runtime.update_runtime_launch_profile(backend="mlx", model_path=None)
    assert updated["backend"] == "mlx"
    assert updated["model_path"] == str(DEFAULT_MLX_MODEL_DIR)
    assert runtime.runtime_launch_profile()["backend"] == "mlx"
    model_status = runtime.mlx_model_status()
    assert model_status["local_dir"] == str(DEFAULT_MLX_MODEL_DIR)
    assert model_status["repo_id"].endswith("Qwen3.5-35B-A3B-mlx-lm-mxfp4")
    runtime.update_runtime_launch_profile(backend="mock", model_path=None)

    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(experiment["id"], title="Resume Me")
    outcome = runtime.chat(session_id=session["id"], user_text="Summarize the current persistent persona state.")

    snapshot = runtime.session_state_snapshot(session["id"])

    assert snapshot["experiment_id"] == experiment["id"]
    assert snapshot["experiment_name"] == experiment["name"]
    assert snapshot["session_id"] == session["id"]
    assert snapshot["session_title"] == "Resume Me"
    assert snapshot["last_turn_id"] == outcome.turn["id"]
    assert snapshot["last_response"] == outcome.turn["membrane_text"]
    assert "Answer:" not in snapshot["last_response"]
    assert snapshot["last_active_set"]
    assert snapshot["last_trace"]
    assert snapshot["current_budget"]["prompt_budget_tokens"] > 0
    assert snapshot["current_profile"]["profile_name"].startswith("manual:")
    assert snapshot["conversation_log_path"].endswith(".md")


def test_conversation_archive_records_and_taxonomy(runtime) -> None:
    first_experiment = runtime.initialize_experiment("blank")
    first_session = runtime.start_session(first_experiment["id"], title="Archive One")
    runtime.chat(session_id=first_session["id"], user_text="Describe the archive surface.")

    second_experiment = runtime.initialize_experiment("blank")
    second_session = runtime.start_session(second_experiment["id"], title="Archive Two")
    runtime.chat(session_id=second_session["id"], user_text="Describe the seeded archive surface.")

    updated = runtime.update_conversation_archive(
        first_session["id"],
        folder="projects/archive",
        tags="memory, atlas, memory",
    )
    assert updated["archive"]["folder"] == "projects/archive"
    assert updated["archive"]["tags"] == ["memory", "atlas"]

    records = runtime.conversation_archive_records()
    assert len(records) == 2
    first_record = next(record for record in records if record["id"] == first_session["id"])
    second_record = next(record for record in records if record["id"] == second_session["id"])

    assert first_record["folder"] == "projects/archive"
    assert first_record["tags"] == ["memory", "atlas"]
    assert "all_texts" in first_record["projection_paths"]
    assert first_record["requested_mode"] == "manual"
    assert first_record["conversation_log_exists"] is False
    assert second_record["folder"] == "inbox"
    assert second_record["tags"] == []

    preview = runtime.conversation_archive_preview(first_session["id"])
    assert preview["archive"]["folder"] == "projects/archive"
    assert preview["archive"]["tags"] == ["memory", "atlas"]
    assert preview["recent_turns"]
    assert preview["conversation_log_exists"] is False

    log_path = runtime.write_conversation_log(first_session["id"])
    assert log_path.exists()
    refreshed_preview = runtime.conversation_archive_preview(first_session["id"])
    assert refreshed_preview["conversation_log_exists"] is True


def test_index_text_into_graph_builds_memode_label_without_refetching_memes(runtime, monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_module,
        "top_phrases",
        lambda text, limit=6: [("alpha", 1.0), ("beta", 0.8), ("gamma", 0.6)],
    )

    class FakeStore:
        def __init__(self) -> None:
            self._count = 0
            self.memode_payload: dict[str, object] | None = None

        def upsert_meme(self, **kwargs):
            self._count += 1
            return {"id": f"meme-{self._count}", "label": kwargs["label"]}

        def add_edge(self, **kwargs) -> None:
            return None

        def upsert_memode(self, **kwargs):
            self.memode_payload = kwargs
            return {"id": "memode-1"}

        def get_meme(self, meme_id: str):
            raise AssertionError(f"unexpected redundant get_meme({meme_id}) during memode label construction")

    fake_store = FakeStore()
    runtime.store = fake_store

    indexed = runtime._index_text_into_graph(
        experiment_id="exp-1",
        turn_id="turn-1",
        session_id="session-1",
        text="alpha beta gamma delta",
        domain="knowledge",
        source_kind="turn_user",
        actor="brian_operator",
    )

    assert indexed["meme_ids"] == ["meme-1", "meme-2", "meme-3"]
    assert indexed["memode_ids"] == ["memode-1"]
    assert fake_store.memode_payload is not None
    assert fake_store.memode_payload["label"] == "alpha / beta / gamma"
    assert fake_store.memode_payload["member_ids"] == ["meme-1", "meme-2", "meme-3"]
