from __future__ import annotations

import json
import socket
import threading
import time
import urllib.request

from eden.observatory.server import ObservatoryServer


def test_observatory_server_starts_on_requested_free_port(tmp_path) -> None:
    root = tmp_path / "exports"
    server = ObservatoryServer(root, 8861)
    status = server.start()
    try:
        assert status.port == 8861
        assert status.owned_by_process is True
        assert status.reused_existing is False
    finally:
        server.stop()


def test_observatory_server_chooses_next_free_port_when_requested_port_is_busy(tmp_path) -> None:
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", 8862))
    blocker.listen(1)
    root = tmp_path / "exports"
    server = ObservatoryServer(root, 8862)
    try:
        status = server.start()
        assert status.port != 8862
        assert status.port >= 8863
    finally:
        server.stop()
        blocker.close()


def test_observatory_server_reuses_existing_same_root(tmp_path) -> None:
    root = tmp_path / "exports"
    server1 = ObservatoryServer(root, 8864)
    status1 = server1.start()
    server2 = ObservatoryServer(root, 8864)
    try:
        status2 = server2.start()
        assert status1.port == status2.port
        assert status2.reused_existing is True
        assert status2.owned_by_process is False
    finally:
        server2.stop()
        server1.stop()


def test_observatory_server_start_is_idempotent(tmp_path) -> None:
    root = tmp_path / "exports"
    server = ObservatoryServer(root, 8865)
    try:
        status1 = server.start()
        status2 = server.start()
        assert status1.port == status2.port
        assert status2.owned_by_process is True
    finally:
        server.stop()


def test_observatory_server_exposes_live_api(runtime, tmp_path) -> None:
    export_root = (tmp_path / "exports").resolve()
    runtime.observatory_service.export_root = export_root
    runtime.observatory_server.root = export_root
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(experiment["id"], title="API")
    runtime.chat(session_id=session["id"], user_text="Seed the graph for observatory api testing.")
    memes = runtime.store.list_memes(experiment["id"])
    status = runtime.start_observatory(host="127.0.0.1", port=8891, reuse_existing=False)
    try:
        with urllib.request.urlopen(f"{status['url']}api/status") as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["ok"] is True
        assert payload["status"]["capabilities"]["preview"] is True
        assert payload["status"]["capabilities"]["tanakh"] is True
        assert "frontend_build" in payload["status"]

        with urllib.request.urlopen(f"{status['url']}api/experiments") as response:
            experiments_payload = json.loads(response.read().decode("utf-8"))
        assert experiments_payload["experiments"]

        with urllib.request.urlopen(f"{status['url']}api/runtime/status") as response:
            runtime_status = json.loads(response.read().decode("utf-8"))
        assert runtime_status["available"] is True

        with urllib.request.urlopen(f"{status['url']}api/runtime/model") as response:
            runtime_model = json.loads(response.read().decode("utf-8"))
        assert runtime_model["available"] is True

        with urllib.request.urlopen(f"{status['url']}api/experiments/{experiment['id']}/overview?session_id={session['id']}") as response:
            overview = json.loads(response.read().decode("utf-8"))
        assert "graph_counts" in overview

        with urllib.request.urlopen(f"{status['url']}api/experiments/{experiment['id']}/graph?session_id={session['id']}") as response:
            graph_payload = json.loads(response.read().decode("utf-8"))
        assert graph_payload["semantic_nodes"]
        assert any(node.get("export_label") and node["export_label"] != node["id"] for node in graph_payload["semantic_nodes"])
        assert any(edge.get("export_label") for edge in graph_payload["semantic_edges"])
        assert "cluster_summaries" in graph_payload
        assert graph_payload["layout_families"][0]["label"] == "1. Force-Directed Layout Algorithms"
        assert graph_payload["layout_catalog"]["kamada_kawai"]["familyId"] == "force_directed"
        assert graph_payload["layout_catalog"]["sugiyama_layered"]["familyId"] == "hierarchical"
        assert graph_payload["layout_defaults"]["community_clusters"]["orderBy"] == "cluster_size"

        with urllib.request.urlopen(f"{status['url']}api/experiments/{experiment['id']}/basin?session_id={session['id']}") as response:
            basin_payload = json.loads(response.read().decode("utf-8"))
        assert basin_payload["projection_method"] == "svd_on_turn_features"

        with urllib.request.urlopen(f"{status['url']}api/experiments/{experiment['id']}/tanakh?session_id={session['id']}") as response:
            tanakh_payload = json.loads(response.read().decode("utf-8"))
        assert tanakh_payload["current_ref"] == "Ezek 1"
        assert tanakh_payload["bundle"]["manifest"]["text_version"] == "UXLC 2.4"

        with urllib.request.urlopen(f"{status['url']}api/experiments/{experiment['id']}/sessions") as response:
            sessions_payload = json.loads(response.read().decode("utf-8"))
        assert any(item["id"] == session["id"] for item in sessions_payload["sessions"])

        with urllib.request.urlopen(f"{status['url']}api/sessions/{session['id']}/turns") as response:
            turns_payload = json.loads(response.read().decode("utf-8"))
        assert turns_payload["turns"]

        with urllib.request.urlopen(f"{status['url']}api/sessions/{session['id']}/active-set") as response:
            active_set_payload = json.loads(response.read().decode("utf-8"))
        assert active_set_payload["turns"]

        preview_request = urllib.request.Request(
            f"{status['url']}api/experiments/{experiment['id']}/preview",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {
                    "session_id": session["id"],
                    "action": {
                        "action_type": "geometry_measurement_run",
                        "selected_node_ids": [memes[0]["id"], memes[1]["id"]],
                        "operator_label": "api_test",
                        "evidence_label": "DERIVED",
                        "confidence": 0.8,
                        "rationale": "preview local geometry",
                    },
                }
            ).encode("utf-8"),
        )
        with urllib.request.urlopen(preview_request) as response:
            preview_payload = json.loads(response.read().decode("utf-8"))
        assert preview_payload["action_type"] == "geometry_measurement_run"
        assert preview_payload["compare_selection"]["baseline_node_ids"] == [memes[0]["id"], memes[1]["id"]]
        assert preview_payload["preview_graph_patch"]["graph_changed"] is False

        commit_request = urllib.request.Request(
            f"{status['url']}api/experiments/{experiment['id']}/commit",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {
                    "session_id": session["id"],
                    "action": {
                        "action_type": "edge_add",
                        "source_id": memes[0]["id"],
                        "target_id": memes[1]["id"],
                        "source_kind": "meme",
                        "target_kind": "meme",
                        "edge_type": "REINFORCES",
                        "weight": 1.1,
                        "operator_label": "api_test",
                        "evidence_label": "OPERATOR_ASSERTED",
                        "confidence": 0.7,
                        "rationale": "commit from api",
                    },
                }
            ).encode("utf-8"),
        )
        with urllib.request.urlopen(commit_request) as response:
            commit_payload = json.loads(response.read().decode("utf-8"))
        assert commit_payload["event"]["action_type"] == "edge_add"

        with urllib.request.urlopen(f"{status['url']}api/sessions/{session['id']}/trace") as response:
            trace_payload = json.loads(response.read().decode("utf-8"))
        assert trace_payload["session_id"] == session["id"]
        assert trace_payload["trace_events"]
        assert any(
            row["payload"].get("measurement_event_id") == commit_payload["event"]["id"]
            for row in trace_payload["trace_events"]
        )

        tanakh_run_request = urllib.request.Request(
            f"{status['url']}api/experiments/{experiment['id']}/tanakh-run",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {
                    "session_id": session["id"],
                    "ref": "Ezek 1:1-3",
                    "params": {
                        "preprocess": "keep_cantillation",
                        "gematria_scheme": "mispar_hechrechi",
                        "notarikon_mode": "first_letter",
                        "temurah_mapping": "atbash",
                        "scene": {"theme": "amber", "seed": 5},
                    },
                }
            ).encode("utf-8"),
        )
        with urllib.request.urlopen(tanakh_run_request) as response:
            tanakh_run_payload = json.loads(response.read().decode("utf-8"))
        assert tanakh_run_payload["current_ref"] == "Ezek 1:1-3"
        assert tanakh_run_payload["bundle"]["scene"]["ref"] == "Ezek 1:1-3"

        with urllib.request.urlopen(f"{status['url']}api/experiments/{experiment['id']}/measurement-events?session_id={session['id']}") as response:
            ledger = json.loads(response.read().decode("utf-8"))
        assert ledger["counts"]["events"] >= 1
    finally:
        runtime.stop_observatory()


def test_observatory_server_sse_emits_small_invalidation_events(runtime, tmp_path) -> None:
    export_root = (tmp_path / "exports").resolve()
    runtime.observatory_service.export_root = export_root
    runtime.observatory_server.root = export_root
    experiment = runtime.initialize_experiment("blank")
    session = runtime.start_session(experiment["id"], title="SSE")
    runtime.chat(session_id=session["id"], user_text="Seed the graph for SSE testing.")
    memes = runtime.store.list_memes(experiment["id"])
    status = runtime.start_observatory(host="127.0.0.1", port=8892, reuse_existing=False)
    try:
        events_url = f"{status['url']}api/experiments/{experiment['id']}/events?session_id={session['id']}"
        with urllib.request.urlopen(events_url, timeout=10) as response:
            observed: dict[str, object] = {}

            def _commit_event() -> None:
                time.sleep(0.2)
                commit_request = urllib.request.Request(
                    f"{status['url']}api/experiments/{experiment['id']}/commit",
                    method="POST",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(
                        {
                            "session_id": session["id"],
                            "action": {
                                "action_type": "edge_add",
                                "source_id": memes[0]["id"],
                                "target_id": memes[1]["id"],
                                "source_kind": "meme",
                                "target_kind": "meme",
                                "edge_type": "REINFORCES",
                                "weight": 1.15,
                                "operator_label": "api_test",
                                "evidence_label": "OPERATOR_ASSERTED",
                                "confidence": 0.74,
                                "rationale": "commit from api",
                            },
                        }
                    ).encode("utf-8"),
                )
                with urllib.request.urlopen(commit_request) as commit_response:
                    observed["commit"] = json.loads(commit_response.read().decode("utf-8"))

            worker = threading.Thread(target=_commit_event, daemon=True)
            worker.start()

            deadline = time.time() + 10
            event_payload = None
            while time.time() < deadline:
                line = response.readline().decode("utf-8").strip()
                if not line or line.startswith(":"):
                    continue
                if line.startswith("data: "):
                    event_payload = json.loads(line.removeprefix("data: "))
                    break
            worker.join(timeout=2)

        assert observed["commit"]["event"]["action_type"] == "edge_add"
        assert event_payload is not None
        assert event_payload["experiment_id"] == experiment["id"]
        assert event_payload["session_id"] == session["id"]
        assert event_payload["reason"] == "measurement_committed"
        assert "graph" in event_payload["kinds"]
        assert "measurements" in event_payload["kinds"]
        assert "payload" not in event_payload
    finally:
        runtime.stop_observatory()
