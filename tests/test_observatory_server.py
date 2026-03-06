from __future__ import annotations

import json
import socket
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

        with urllib.request.urlopen(f"{status['url']}api/experiments/{experiment['id']}/measurement-events?session_id={session['id']}") as response:
            ledger = json.loads(response.read().decode("utf-8"))
        assert ledger["counts"]["events"] >= 1
    finally:
        runtime.stop_observatory()
