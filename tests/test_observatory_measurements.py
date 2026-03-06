from __future__ import annotations

import json


def _isolated_observatory(runtime, tmp_path) -> None:
    export_root = (tmp_path / "exports").resolve()
    runtime.observatory_service.export_root = export_root
    runtime.observatory_server.root = export_root


def _seed_session(runtime, tmp_path):
    _isolated_observatory(runtime, tmp_path)
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(experiment["id"], title="Observatory")
    runtime.chat(session_id=session["id"], user_text="Describe the graph-conditioned persistence loop.")
    memes = runtime.store.list_memes(experiment["id"])
    assert len(memes) >= 2
    return experiment, session, memes


def test_edge_measurement_commit_and_revert_persist(tmp_path, runtime) -> None:
    experiment, session, memes = _seed_session(runtime, tmp_path)
    left, right = memes[:2]
    action = {
        "action_type": "edge_add",
        "source_id": left["id"],
        "target_id": right["id"],
        "source_kind": "meme",
        "target_kind": "meme",
        "edge_type": "REINFORCES",
        "weight": 1.35,
        "confidence": 0.82,
        "operator_label": "test_operator",
        "evidence_label": "OPERATOR_ASSERTED",
        "measurement_method": "local_geometry_preview",
        "rationale": "manual bridge between two persistent meme nodes",
    }
    preview = runtime.preview_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        action=action,
    )
    assert preview["topology_change"]["graph_changed"] is True
    assert preview["measurement_only"] is False

    committed = runtime.commit_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        action=action,
    )
    event = committed["event"]
    assert event["action_type"] == "edge_add"
    assert runtime.store.get_edge(
        experiment_id=experiment["id"],
        src_kind="meme",
        src_id=left["id"],
        dst_kind="meme",
        dst_id=right["id"],
        edge_type="REINFORCES",
    )

    reverted = runtime.revert_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        event_id=event["id"],
    )
    assert reverted["event"]["action_type"] == "revert"
    assert runtime.store.get_edge(
        experiment_id=experiment["id"],
        src_kind="meme",
        src_id=left["id"],
        dst_kind="meme",
        dst_id=right["id"],
        edge_type="REINFORCES",
    ) is None


def test_memode_assert_and_membership_update_persist(tmp_path, runtime) -> None:
    experiment, session, memes = _seed_session(runtime, tmp_path)
    action = {
        "action_type": "memode_assert",
        "selected_node_ids": [memes[0]["id"], memes[1]["id"]],
        "label": "Known persistence motif",
        "summary": "Operator-asserted reusable motif for persistence and retrieval.",
        "domain": "behavior",
        "confidence": 0.9,
        "operator_label": "test_operator",
        "evidence_label": "OPERATOR_ASSERTED",
        "rationale": "known memode captured from observation",
    }
    committed = runtime.commit_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        action=action,
    )
    memode = committed["committed_state"]["memode"]
    metadata = json.loads(memode["metadata_json"])
    assert metadata["member_ids"] == sorted([memes[0]["id"], memes[1]["id"]])

    update = runtime.commit_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        action={
            "action_type": "memode_update_membership",
            "memode_id": memode["id"],
            "member_ids": [memes[0]["id"], memes[1]["id"], memes[2]["id"]],
            "summary": "Expanded motif membership",
            "confidence": 0.86,
            "operator_label": "test_operator",
            "evidence_label": "OPERATOR_REFINED",
            "rationale": "third meme belongs in this motif",
        },
    )
    updated_memode = runtime.store.get_memode(memode["id"])
    updated_metadata = json.loads(updated_memode["metadata_json"])
    assert updated_metadata["member_ids"] == sorted([memes[0]["id"], memes[1]["id"], memes[2]["id"]])
    assert update["event"]["action_type"] == "memode_update_membership"


def test_measurement_only_action_persists_without_topology_mutation(tmp_path, runtime) -> None:
    experiment, session, memes = _seed_session(runtime, tmp_path)
    counts_before = runtime.store.graph_counts(experiment["id"])
    result = runtime.commit_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        action={
            "action_type": "geometry_measurement_run",
            "selected_node_ids": [memes[0]["id"], memes[1]["id"]],
            "operator_label": "test_operator",
            "evidence_label": "DERIVED",
            "confidence": 0.75,
            "rationale": "measure local geometry only",
        },
    )
    counts_after = runtime.store.graph_counts(experiment["id"])
    assert counts_after["edges"] == counts_before["edges"]
    assert counts_after["measurement_events"] == counts_before["measurement_events"] + 1
    assert result["event"]["action_type"] == "geometry_measurement_run"
