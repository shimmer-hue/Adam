from __future__ import annotations

import copy
import json

import pytest

from eden.config import RuntimeSettings
from eden.logging import RuntimeLog
from eden.observatory import clustering as observatory_clustering
from eden.observatory.contracts import MEMODE_SUPPORT_EDGE_ALLOWLIST
from eden.runtime import EdenRuntime
from eden.storage.graph_store import GraphStore


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


def _connected_meme_pair(runtime, experiment_id: str) -> tuple[str, str]:
    for edge in runtime.store.list_edges(experiment_id):
        if edge["src_kind"] == "meme" and edge["dst_kind"] == "meme" and edge["edge_type"] in MEMODE_SUPPORT_EDGE_ALLOWLIST:
            return edge["src_id"], edge["dst_id"]
    raise AssertionError("Expected at least one qualifying semantic meme edge in the persistent graph.")


def _isolated_meme(runtime, experiment_id: str, label: str) -> dict[str, str]:
    return runtime.store.upsert_meme(
        experiment_id=experiment_id,
        label=label,
        text=f"{label} should stay disconnected from the qualifying semantic subgraph.",
        domain="knowledge",
        source_kind="operator_test",
        metadata={"origin": "pytest"},
    )


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
    left_id, right_id = _connected_meme_pair(runtime, experiment["id"])
    action = {
        "action_type": "memode_assert",
        "selected_node_ids": [left_id, right_id],
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
    assert metadata["member_ids"] == sorted([left_id, right_id])
    assert metadata["supporting_edge_ids"]

    runtime.store.set_edge(
        experiment_id=experiment["id"],
        src_kind="meme",
        src_id=right_id,
        dst_kind="meme",
        dst_id=memes[2]["id"],
        edge_type="SUPPORTS",
        provenance={"assertion_origin": "operator_asserted", "evidence_label": "OPERATOR_ASSERTED", "confidence": 0.9},
    )

    update = runtime.commit_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        action={
            "action_type": "memode_update_membership",
            "memode_id": memode["id"],
            "member_ids": [left_id, right_id, memes[2]["id"]],
            "summary": "Expanded motif membership",
            "confidence": 0.86,
            "operator_label": "test_operator",
            "evidence_label": "OPERATOR_REFINED",
            "rationale": "third meme belongs in this motif",
        },
    )
    updated_memode = runtime.store.get_memode(memode["id"])
    updated_metadata = json.loads(updated_memode["metadata_json"])
    assert updated_metadata["member_ids"] == sorted([left_id, right_id, memes[2]["id"]])
    assert len(updated_metadata["supporting_edge_ids"]) >= 2
    assert update["event"]["action_type"] == "memode_update_membership"


def test_memode_audit_plane_distinguishes_support_from_informational_relations(tmp_path, runtime) -> None:
    experiment, session, memes = _seed_session(runtime, tmp_path)
    left_id, right_id = _connected_meme_pair(runtime, experiment["id"])
    informational_target = _isolated_meme(runtime, experiment["id"], "Observatory informational target")

    runtime.commit_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        action={
            "action_type": "memode_assert",
            "selected_node_ids": [left_id, right_id],
            "label": "Audit persistence motif",
            "summary": "Memode used to verify the observatory audit plane.",
            "domain": "behavior",
            "confidence": 0.88,
            "operator_label": "test_operator",
            "evidence_label": "OPERATOR_ASSERTED",
            "rationale": "build a known memode before checking audit output",
        },
    )

    runtime.store.set_edge(
        experiment_id=experiment["id"],
        src_kind="meme",
        src_id=right_id,
        dst_kind="meme",
        dst_id=informational_target["id"],
        edge_type="REFERENCES",
        provenance={"assertion_origin": "operator_asserted", "evidence_label": "OPERATOR_ASSERTED", "confidence": 0.73},
    )

    payload = runtime.observatory_service.graph_payload(experiment_id=experiment["id"], session_id=session["id"])
    audit = payload["memode_audit"]
    assert audit["summary"]["memodes"] >= 1
    assert audit["summary"]["materialized_support_edges"] >= 1
    assert any(row["admissibility"]["passes"] for row in audit["memodes"])
    assert any(edge["relation_class"] == "materialized_support" for row in audit["memodes"] for edge in row["support_edges"])
    assert any(edge["relation_class"] == "knowledge_informational" for edge in audit["informational_relations"])


def test_graph_payload_tolerates_null_labels_in_snapshot(tmp_path, runtime, monkeypatch) -> None:
    experiment, session, _ = _seed_session(runtime, tmp_path)
    snapshot = copy.deepcopy(runtime.store.graph_snapshot(experiment["id"]))
    target = snapshot["memes"][0]
    target["label"] = None

    original_graph_snapshot = runtime.exporter.store.graph_snapshot

    def _patched_graph_snapshot(experiment_id: str):
        if experiment_id == experiment["id"]:
            return snapshot
        return original_graph_snapshot(experiment_id)

    monkeypatch.setattr(runtime.exporter.store, "graph_snapshot", _patched_graph_snapshot)

    payload = runtime.observatory_service.graph_payload(experiment_id=experiment["id"], session_id=session["id"])
    rendered = next(node for node in payload["semantic_nodes"] if node["id"] == target["id"])
    assert isinstance(rendered["label"], str)
    assert rendered["label"]


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


def test_preview_graph_patch_reports_edge_add_selection_and_delta(tmp_path, runtime) -> None:
    experiment, session, memes = _seed_session(runtime, tmp_path)
    connected_pairs = {
        frozenset((edge["src_id"], edge["dst_id"]))
        for edge in runtime.store.list_edges(experiment["id"])
        if edge["src_kind"] == "meme" and edge["dst_kind"] == "meme"
    }
    source_id = target_id = None
    for index, left in enumerate(memes):
        for right in memes[index + 1 :]:
            if frozenset((left["id"], right["id"])) not in connected_pairs:
                source_id = left["id"]
                target_id = right["id"]
                break
        if source_id and target_id:
            break
    assert source_id is not None and target_id is not None

    action = {
        "action_type": "edge_add",
        "source_id": source_id,
        "target_id": target_id,
        "source_kind": "meme",
        "target_kind": "meme",
        "edge_type": "TEST_PREVIEW_EDGE",
        "weight": 1.25,
        "confidence": 0.81,
        "operator_label": "test_operator",
        "evidence_label": "OPERATOR_ASSERTED",
        "measurement_method": "local_geometry_preview",
        "rationale": "preview edge add for compare rendering",
    }
    preview = runtime.preview_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        action=action,
    )

    patch = preview["preview_graph_patch"]
    assert patch["graph_changed"] is True
    assert patch["modified_counts"]["edges"] == patch["baseline_counts"]["edges"] + 1
    assert patch["added_edges"]
    assert patch["added_edges"][0]["source"] == source_id
    assert patch["added_edges"][0]["target"] == target_id
    assert preview["compare_selection"]["baseline_node_ids"] == [source_id, target_id]
    assert preview["compare_selection"]["modified_node_ids"] == [source_id, target_id]


def test_memode_assert_rejects_missing_support_edges(tmp_path, runtime) -> None:
    experiment, session, memes = _seed_session(runtime, tmp_path)
    isolated = _isolated_meme(runtime, experiment["id"], "Disconnected observatory meme")
    with pytest.raises(ValueError, match="qualifying semantic support edge"):
        runtime.commit_observatory_action(
            experiment_id=experiment["id"],
            session_id=session["id"],
            turn_id=None,
            action={
                "action_type": "memode_assert",
                "selected_node_ids": [memes[0]["id"], isolated["id"]],
                "label": "Invalid disconnected memode",
                "summary": "This should fail because there is no qualifying support edge.",
                "domain": "knowledge",
                "confidence": 0.7,
                "operator_label": "test_operator",
                "evidence_label": "OPERATOR_ASSERTED",
                "rationale": "negative test for support-edge floor",
            },
        )


def test_memode_support_allowlist_and_passenger_rejection(tmp_path, runtime) -> None:
    experiment, session, _ = _seed_session(runtime, tmp_path)
    left = _isolated_meme(runtime, experiment["id"], "Left support test meme")
    right = _isolated_meme(runtime, experiment["id"], "Right support test meme")
    passenger = _isolated_meme(runtime, experiment["id"], "Passenger meme")
    base_action = {
        "action_type": "memode_assert",
        "selected_node_ids": [left["id"], right["id"]],
        "label": "Support check memode",
        "summary": "Used to verify the qualifying-edge allowlist and denylist.",
        "domain": "knowledge",
        "confidence": 0.72,
        "operator_label": "test_operator",
        "evidence_label": "OPERATOR_ASSERTED",
        "rationale": "support check",
    }

    runtime.store.set_edge(
        experiment_id=experiment["id"],
        src_kind="meme",
        src_id=left["id"],
        dst_kind="meme",
        dst_id=right["id"],
        edge_type="BELONGS_TO_SESSION",
        provenance={"assertion_origin": "operator_asserted"},
    )
    with pytest.raises(ValueError, match="qualifying semantic support edge"):
        runtime.preview_observatory_action(
            experiment_id=experiment["id"],
            session_id=session["id"],
            turn_id=None,
            action=base_action,
        )

    runtime.store.set_edge(
        experiment_id=experiment["id"],
        src_kind="meme",
        src_id=left["id"],
        dst_kind="meme",
        dst_id=right["id"],
        edge_type="UNKNOWN_RELATION",
        provenance={"assertion_origin": "operator_asserted"},
    )
    with pytest.raises(ValueError, match="qualifying semantic support edge"):
        runtime.preview_observatory_action(
            experiment_id=experiment["id"],
            session_id=session["id"],
            turn_id=None,
            action=base_action,
        )

    runtime.store.set_edge(
        experiment_id=experiment["id"],
        src_kind="meme",
        src_id=left["id"],
        dst_kind="meme",
        dst_id=right["id"],
        edge_type="SUPPORTS",
        provenance={"assertion_origin": "operator_asserted", "evidence_label": "OPERATOR_ASSERTED", "confidence": 0.81},
    )
    committed = runtime.commit_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        action=base_action,
    )
    committed_metadata = json.loads(committed["committed_state"]["memode"]["metadata_json"])
    assert committed_metadata["supporting_edge_ids"]

    with pytest.raises(ValueError, match="disconnected passenger memes"):
        runtime.preview_observatory_action(
            experiment_id=experiment["id"],
            session_id=session["id"],
            turn_id=None,
            action={**base_action, "selected_node_ids": [left["id"], right["id"], passenger["id"]]},
        )


def test_cluster_summaries_are_deterministic_and_versioned(tmp_path, runtime, monkeypatch) -> None:
    experiment, session, _ = _seed_session(runtime, tmp_path)
    payload_one = runtime.observatory_service.graph_payload(experiment_id=experiment["id"], session_id=session["id"])
    payload_two = runtime.observatory_service.graph_payload(experiment_id=experiment["id"], session_id=session["id"])
    signatures_one = [item["cluster_signature"] for item in payload_one["cluster_summaries"]]
    signatures_two = [item["cluster_signature"] for item in payload_two["cluster_summaries"]]
    assert signatures_one == signatures_two
    assert [item["algorithm_version"] for item in payload_one["cluster_summaries"]] == [
        item["algorithm_version"] for item in payload_two["cluster_summaries"]
    ]

    coord_lookup = {
        node["id"]: node.get("render_coords", {}).get("force", {"x": 0.0, "y": 0.0})
        for node in payload_one["semantic_nodes"]
    }
    baseline_summaries, _ = observatory_clustering.build_cluster_summaries(
        semantic_nodes=payload_one["semantic_nodes"],
        semantic_edges=payload_one["semantic_edges"],
        coord_lookup=coord_lookup,
        measurement_events=payload_one["measurement_events"],
    )
    monkeypatch.setattr(
        observatory_clustering,
        "OBSERVATORY_CLUSTER_ALGORITHM_VERSION",
        "deterministic_louvain:seed=1729:tokenizer=v99:weights=v99",
    )
    changed_summaries, _ = observatory_clustering.build_cluster_summaries(
        semantic_nodes=payload_one["semantic_nodes"],
        semantic_edges=payload_one["semantic_edges"],
        coord_lookup=coord_lookup,
        measurement_events=payload_one["measurement_events"],
    )
    assert baseline_summaries[0]["algorithm_version"] != changed_summaries[0]["algorithm_version"]
    assert baseline_summaries[0]["cluster_signature"] != changed_summaries[0]["cluster_signature"]


def test_manual_cluster_label_persists_without_mutating_topology(tmp_path, runtime) -> None:
    experiment, session, _ = _seed_session(runtime, tmp_path)
    before = runtime.observatory_service.graph_payload(experiment_id=experiment["id"], session_id=session["id"])
    cluster = before["cluster_summaries"][0]
    semantic_labels_before = {node["id"]: node["label"] for node in before["semantic_nodes"]}

    runtime.commit_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        action={
            "action_type": "motif_annotation",
            "target": {
                "kind": "cluster",
                "cluster_signature": cluster["cluster_signature"],
                "member_meme_ids": cluster["member_meme_ids"],
                "dominant_domain": max(cluster["domain_mix"], key=cluster["domain_mix"].get),
            },
            "cluster_signature": cluster["cluster_signature"],
            "source_graph_hash": cluster["source_graph_hash"],
            "algorithm_version": cluster["algorithm_version"],
            "manual_label": "Persistence script",
            "manual_summary": "Operator-defined semantic neighborhood label.",
            "operator_label": "test_operator",
            "evidence_label": "OPERATOR_ASSERTED",
            "confidence": 0.83,
            "rationale": "manual cluster naming",
        },
    )

    after = runtime.observatory_service.graph_payload(experiment_id=experiment["id"], session_id=session["id"])
    cluster_after = next(item for item in after["cluster_summaries"] if item["cluster_signature"] == cluster["cluster_signature"])
    assert cluster_after["manual_label"] == "Persistence script"
    assert cluster_after["display_label"] == "Persistence script"
    assert cluster_after["transfer_status"] == "exact"
    assert {node["id"]: node["label"] for node in after["semantic_nodes"]} == semantic_labels_before
    assert "view_presets" not in after
    assert after["semantic_nodes"]
    assert after["runtime_nodes"]
    assert after["assemblies"] is not None


def test_ablation_and_motif_actions_emit_trace_and_revertible_events(tmp_path, runtime) -> None:
    experiment, session, memes = _seed_session(runtime, tmp_path)
    graph_payload = runtime.observatory_service.graph_payload(experiment_id=experiment["id"], session_id=session["id"])
    cluster = graph_payload["cluster_summaries"][0]
    support_edge = next(
        edge
        for edge in runtime.store.list_edges(experiment["id"])
        if edge["src_kind"] == "meme" and edge["dst_kind"] == "meme" and edge["edge_type"] in MEMODE_SUPPORT_EDGE_ALLOWLIST
    )

    ablation = runtime.commit_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        action={
            "action_type": "ablation_measurement_run",
            "selected_node_ids": [memes[0]["id"], memes[1]["id"]],
            "mask_relation_type": support_edge["edge_type"],
            "operator_label": "test_operator",
            "evidence_label": "DERIVED",
            "confidence": 0.77,
            "rationale": "mask one relation class for observatory compare",
        },
    )
    motif = runtime.commit_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        action={
            "action_type": "motif_annotation",
            "target": {
                "kind": "cluster",
                "cluster_signature": cluster["cluster_signature"],
                "member_meme_ids": cluster["member_meme_ids"],
                "dominant_domain": max(cluster["domain_mix"], key=cluster["domain_mix"].get),
            },
            "cluster_signature": cluster["cluster_signature"],
            "source_graph_hash": cluster["source_graph_hash"],
            "algorithm_version": cluster["algorithm_version"],
            "manual_label": "Ablated persistence motif",
            "manual_summary": "Operator-defined cluster after ablation pass.",
            "operator_label": "test_operator",
            "evidence_label": "OPERATOR_ASSERTED",
            "confidence": 0.83,
            "rationale": "manual cluster naming",
        },
    )

    trace = runtime.observatory_service.session_trace(session_id=session["id"])
    measurement_event_ids = {
        row["payload"].get("measurement_event_id")
        for row in trace["trace_events"]
        if row["payload"].get("measurement_event_id")
    }
    assert ablation["event"]["id"] in measurement_event_ids
    assert motif["event"]["id"] in measurement_event_ids
    assert any(row["event_type"] == "OBSERVATORY_MEASUREMENT" for row in trace["trace_events"])
    assert trace["membrane_events"]

    reverted = runtime.revert_observatory_action(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=None,
        event_id=ablation["event"]["id"],
    )
    assert reverted["event"]["action_type"] == "revert"

    trace_after_revert = runtime.observatory_service.session_trace(session_id=session["id"])
    revert_ids = {
        row["payload"].get("measurement_event_id")
        for row in trace_after_revert["trace_events"]
        if row["event_type"] == "OBSERVATORY_REVERT"
    }
    assert reverted["event"]["id"] in revert_ids


def test_basin_payload_exposes_projection_metadata_and_sparse_diagnostics(tmp_path, runtime) -> None:
    experiment, session, _ = _seed_session(runtime, tmp_path)
    basin = runtime.observatory_service.basin_payload(experiment_id=experiment["id"], session_id=session["id"])
    assert basin["projection_method"] == "svd_on_turn_features"
    assert basin["projection_version"]
    assert basin["projection_input_hash"]
    assert basin["source_turn_count"] >= basin["filtered_turn_count"] >= 1
    assert basin["turns"][0]["dominant_node_id"]
    assert "dominant_cluster_signature" in basin["turns"][0]
    assert "display_attractor_label" in basin["turns"][0]
    assert "cluster_signature" in basin["attractors"][0]
    assert "display_label" in basin["attractors"][0]

    sparse_runtime = EdenRuntime(
        store=GraphStore(tmp_path / "sparse_runtime.db"),
        settings=RuntimeSettings(model_backend="mock"),
        runtime_log=RuntimeLog(tmp_path / "sparse_runtime.jsonl"),
    )
    _isolated_observatory(sparse_runtime, tmp_path / "sparse")
    sparse_experiment = sparse_runtime.initialize_experiment("blank")
    sparse_session = sparse_runtime.start_session(sparse_experiment["id"], title="Sparse")
    sparse_basin = sparse_runtime.observatory_service.basin_payload(
        experiment_id=sparse_experiment["id"],
        session_id=sparse_session["id"],
    )
    assert sparse_basin["filtered_turn_count"] == 0
    assert sparse_basin["diagnostics"]["empty_state"] is True
    assert "Not enough turns" in sparse_basin["diagnostics"]["reason"]
