from __future__ import annotations

from eden.storage.graph_store import GraphStore


class _ConnectionProxy:
    def __init__(self, inner, store: GraphStore) -> None:
        self._inner = inner
        self._store = store

    def execute(self, sql, params=()):
        if sql.lstrip().upper().startswith("SELECT"):
            assert self._store._lock._is_owned(), f"SELECT executed without store lock: {sql}"
        return self._inner.execute(sql, params)

    def executescript(self, sql):
        return self._inner.executescript(sql)

    def commit(self):
        return self._inner.commit()

    def rollback(self):
        return self._inner.rollback()

    def close(self):
        return self._inner.close()


def test_graph_store_serializes_read_queries(tmp_path) -> None:
    store = GraphStore(tmp_path / "eden.db")
    agent_id = store.upsert_agent("adam", "Adam", {"kind": "agent"})
    experiment = store.create_experiment("Lock Test", "blank")
    session = store.create_session(experiment["id"], agent_id, "Lock Session")
    turn = store.record_turn(
        experiment_id=experiment["id"],
        session_id=session["id"],
        user_text="hello",
        prompt_context="ctx",
        response_text="response",
        membrane_text="membrane",
        active_set=[],
        trace=[],
    )
    store.record_feedback(
        experiment_id=experiment["id"],
        session_id=session["id"],
        turn_id=turn["id"],
        verdict="accept",
        explanation="ok",
        corrected_text="",
        signal={},
    )

    store._conn = _ConnectionProxy(store._conn, store)

    assert store.get_latest_experiment() is not None
    assert store.get_session(session["id"])["id"] == session["id"]
    assert len(store.list_turns(session["id"])) == 1
    assert len(store.recent_feedback(session["id"])) == 1
    snapshot = store.graph_snapshot(experiment["id"])
    assert len(snapshot["turns"]) == 1
    assert store.graph_counts(experiment["id"])["turns"] == 1


def test_get_latest_session_prefers_newest_insert_when_timestamps_tie(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("eden.storage.graph_store.now_utc", lambda: "2026-03-19T12:00:00+00:00")

    store = GraphStore(tmp_path / "eden.db")
    agent_id = store.upsert_agent("adam", "Adam", {"kind": "agent"})
    experiment = store.create_experiment("Tie Test", "blank")
    store.create_session(experiment["id"], agent_id, "First Session")
    second = store.create_session(experiment["id"], agent_id, "Second Session")

    assert store.get_latest_session(experiment["id"])["id"] == second["id"]
    assert store.get_latest_session(experiment["id"])["title"] == "Second Session"
