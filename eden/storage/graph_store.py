from __future__ import annotations

import json
import re
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from ..utils import compact_json, now_utc, safe_excerpt, sha256_file, slugify, tokenize
from .schema import SCHEMA_SQL


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


class GraphStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self.initialize()

    def initialize(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA_SQL)
            self._apply_additive_migrations()
            self._conn.commit()

    def _apply_additive_migrations(self) -> None:
        self._ensure_column("turns", "metadata_json", "TEXT NOT NULL DEFAULT '{}'")
        self._dedupe_documents_by_sha()
        self._cleanup_orphan_chunk_fts()
        self._backfill_document_quality_metadata()
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_experiment_sha ON documents(experiment_id, sha256)"
        )

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        row = self._conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {item["name"] for item in row}
        if column in existing:
            return
        self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _dedupe_documents_by_sha(self) -> None:
        duplicate_groups = self._conn.execute(
            """
            SELECT experiment_id, sha256
            FROM documents
            GROUP BY experiment_id, sha256
            HAVING COUNT(*) > 1
            """
        ).fetchall()
        for group in duplicate_groups:
            experiment_id = str(group["experiment_id"])
            sha256 = str(group["sha256"])
            documents = self._conn.execute(
                """
                SELECT d.*, COALESCE(ch.chunk_count, 0) AS chunk_count
                FROM documents d
                LEFT JOIN (
                    SELECT document_id, COUNT(*) AS chunk_count
                    FROM document_chunks
                    GROUP BY document_id
                ) ch ON ch.document_id = d.id
                WHERE d.experiment_id = ? AND d.sha256 = ?
                ORDER BY
                    CASE d.status
                        WHEN 'ingested' THEN 2
                        WHEN 'processing' THEN 1
                        ELSE 0
                    END DESC,
                    COALESCE(ch.chunk_count, 0) DESC,
                    d.created_at DESC,
                    d.id DESC
                """,
                (experiment_id, sha256),
            ).fetchall()
            if len(documents) < 2:
                continue
            survivor = documents[0]
            survivor_id = str(survivor["id"])
            survivor_title = str(survivor["title"])

            for duplicate in documents[1:]:
                duplicate_id = str(duplicate["id"])
                duplicate_chunks = self._conn.execute(
                    "SELECT * FROM document_chunks WHERE document_id = ? ORDER BY chunk_index ASC, created_at ASC",
                    (duplicate_id,),
                ).fetchall()
                for chunk in duplicate_chunks:
                    transferred_chunk_id = str(uuid4())
                    inserted = self._conn.execute(
                        """
                        INSERT OR IGNORE INTO document_chunks(
                            id, experiment_id, document_id, chunk_index, page_number, text, metadata_json, created_at
                        )
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            transferred_chunk_id,
                            str(chunk["experiment_id"]),
                            survivor_id,
                            int(chunk["chunk_index"]),
                            chunk["page_number"],
                            str(chunk["text"]),
                            str(chunk["metadata_json"]),
                            str(chunk["created_at"]),
                        ),
                    )
                    if inserted.rowcount:
                        self._conn.execute(
                            "INSERT INTO chunk_fts(chunk_id, title, text) VALUES(?, ?, ?)",
                            (transferred_chunk_id, survivor_title, str(chunk["text"])),
                        )
                if duplicate_chunks:
                    self._conn.executemany(
                        "DELETE FROM chunk_fts WHERE chunk_id = ?",
                        [(str(chunk["id"]),) for chunk in duplicate_chunks],
                    )
                self._conn.execute("DELETE FROM documents WHERE id = ?", (duplicate_id,))

    def _cleanup_orphan_chunk_fts(self) -> None:
        self._conn.execute(
            "DELETE FROM chunk_fts WHERE chunk_id NOT IN (SELECT id FROM document_chunks)"
        )

    def _backfill_document_quality_metadata(self) -> None:
        rows = self._conn.execute("SELECT * FROM documents").fetchall()
        for row in rows:
            metadata = json.loads(row["metadata_json"] or "{}")
            missing_quality = any(
                key not in metadata
                for key in ("parser_strategy", "quality_score", "quality_state", "quality_flags", "selected_parser_counts")
            )
            if not missing_quality:
                continue

            parser_counts: dict[str, int] = {}
            chunk_rows = self._conn.execute(
                "SELECT metadata_json FROM document_chunks WHERE document_id = ?",
                (str(row["id"]),),
            ).fetchall()
            for chunk in chunk_rows:
                try:
                    chunk_metadata = json.loads(chunk["metadata_json"] or "{}")
                except json.JSONDecodeError:
                    continue
                parser = chunk_metadata.get("parser")
                if parser:
                    parser_key = str(parser)
                    parser_counts[parser_key] = parser_counts.get(parser_key, 0) + 1
            if not parser_counts:
                for note in metadata.get("notes", []):
                    if not isinstance(note, str):
                        continue
                    match = re.search(r"parser=([A-Za-z0-9_:-]+)", note)
                    if not match:
                        continue
                    parser_key = match.group(1)
                    parser_counts[parser_key] = parser_counts.get(parser_key, 0) + 1

            if "parser_strategy" not in metadata:
                metadata["parser_strategy"] = "legacy_ingest_unscored"
            if "quality_score" not in metadata:
                metadata["quality_score"] = 0.0
            if "quality_state" not in metadata or metadata.get("quality_state") in {"clean", "degraded", "failed"}:
                metadata["quality_state"] = "legacy_unscored"
            flags = {str(flag) for flag in metadata.get("quality_flags", []) if str(flag).strip()}
            if str(row["kind"]).lower() == "pdf":
                flags.add("legacy_unscored_pdf")
            else:
                flags.add("legacy_unscored_document")
            metadata["quality_flags"] = sorted(flags)
            metadata.setdefault("selected_parser_counts", dict(sorted(parser_counts.items())))

            self._conn.execute(
                "UPDATE documents SET metadata_json = ? WHERE id = ?",
                (compact_json(metadata), str(row["id"])),
            )

    @contextmanager
    def transaction(self) -> Iterable[sqlite3.Connection]:
        with self._lock:
            try:
                yield self._conn
            except Exception:
                self._conn.rollback()
                raise
            else:
                self._conn.commit()

    def _fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        with self._lock:
            return self._conn.execute(sql, params).fetchone()

    def _fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def upsert_config(self, key: str, value: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO config_store(key, value_json)
                VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json
                """,
                (key, compact_json(value)),
            )

    def read_config(self, key: str) -> dict[str, Any] | None:
        row = self._fetchone("SELECT value_json FROM config_store WHERE key = ?", (key,))
        if not row:
            return None
        return json.loads(row["value_json"])

    def upsert_agent(self, slug: str, name: str, profile: dict[str, Any]) -> str:
        existing = self._fetchone("SELECT id FROM agents WHERE slug = ?", (slug,))
        if existing:
            return str(existing["id"])
        agent_id = str(uuid4())
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO agents(id, slug, name, profile_json, created_at) VALUES(?, ?, ?, ?, ?)",
                (agent_id, slug, name, compact_json(profile), now_utc()),
            )
        return agent_id

    def create_experiment(self, name: str, mode: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        experiment_id = str(uuid4())
        slug = slugify(name) + "-" + experiment_id[:8]
        created_at = now_utc()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO experiments(id, name, slug, mode, status, created_at, updated_at, metadata_json)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    name,
                    slug,
                    mode,
                    "ready",
                    created_at,
                    created_at,
                    compact_json(metadata or {}),
                ),
            )
        return self.get_experiment(experiment_id)

    def update_experiment_status(self, experiment_id: str, status: str, metadata: dict[str, Any] | None = None) -> None:
        with self.transaction() as conn:
            if metadata is None:
                conn.execute(
                    "UPDATE experiments SET status = ?, updated_at = ? WHERE id = ?",
                    (status, now_utc(), experiment_id),
                )
            else:
                conn.execute(
                    "UPDATE experiments SET status = ?, updated_at = ?, metadata_json = ? WHERE id = ?",
                    (status, now_utc(), compact_json(metadata), experiment_id),
                )

    def update_experiment_identity(
        self,
        experiment_id: str,
        *,
        name: str | None = None,
        mode: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        experiment = self.get_experiment(experiment_id)
        next_name = (name or experiment["name"]).strip() or experiment["name"]
        next_mode = (mode or experiment["mode"]).strip() or experiment["mode"]
        next_slug = slugify(next_name) + "-" + experiment_id[:8]
        merged_metadata = json.loads(experiment["metadata_json"] or "{}")
        if metadata:
            merged_metadata.update(metadata)
        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE experiments
                SET name = ?, slug = ?, mode = ?, updated_at = ?, metadata_json = ?
                WHERE id = ?
                """,
                (next_name, next_slug, next_mode, now_utc(), compact_json(merged_metadata), experiment_id),
            )
        return self.get_experiment(experiment_id)

    def list_experiments(self) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM experiments ORDER BY created_at DESC LIMIT 25"
        )
        return [_row_to_dict(row) for row in rows if row is not None]

    def get_experiment(self, experiment_id: str) -> dict[str, Any]:
        row = self._fetchone("SELECT * FROM experiments WHERE id = ?", (experiment_id,))
        if row is None:
            raise KeyError(f"Unknown experiment: {experiment_id}")
        return _row_to_dict(row) or {}

    def get_latest_experiment(self) -> dict[str, Any] | None:
        row = self._fetchone("SELECT * FROM experiments ORDER BY created_at DESC LIMIT 1")
        return _row_to_dict(row)

    def reassign_runtime_records_to_experiment(self, source_experiment_id: str, target_experiment_id: str) -> None:
        if source_experiment_id == target_experiment_id:
            return
        tables = (
            "sessions",
            "turns",
            "feedback_events",
            "documents",
            "document_chunks",
            "active_sets",
            "trace_events",
            "membrane_events",
            "export_artifacts",
            "measurement_events",
        )
        with self.transaction() as conn:
            for table in tables:
                conn.execute(
                    f"UPDATE {table} SET experiment_id = ? WHERE experiment_id = ?",
                    (target_experiment_id, source_experiment_id),
                )

    def create_session(self, experiment_id: str, agent_id: str, title: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        session_id = str(uuid4())
        created_at = now_utc()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO sessions(id, experiment_id, agent_id, title, created_at, updated_at, metadata_json)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, experiment_id, agent_id, title, created_at, created_at, compact_json(metadata or {})),
            )
        return self.get_session(session_id)

    def update_session_metadata(self, session_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        session = self.get_session(session_id)
        merged = json.loads(session["metadata_json"] or "{}")
        merged.update(metadata)
        with self.transaction() as conn:
            conn.execute(
                "UPDATE sessions SET metadata_json = ?, updated_at = ? WHERE id = ?",
                (compact_json(merged), now_utc(), session_id),
            )
        return self.get_session(session_id)

    def update_session_title(self, session_id: str, title: str) -> dict[str, Any]:
        normalized = title.strip() or "Operator Session"
        with self.transaction() as conn:
            conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (normalized, now_utc(), session_id),
            )
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> dict[str, Any]:
        row = self._fetchone("SELECT * FROM sessions WHERE id = ?", (session_id,))
        if row is None:
            raise KeyError(f"Unknown session: {session_id}")
        return _row_to_dict(row) or {}

    def get_latest_session(self, experiment_id: str) -> dict[str, Any] | None:
        row = self._fetchone(
            "SELECT * FROM sessions WHERE experiment_id = ? ORDER BY updated_at DESC, created_at DESC, rowid DESC LIMIT 1",
            (experiment_id,),
        )
        return _row_to_dict(row)

    def list_session_catalog(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        sql = """
            SELECT
                s.*,
                e.name AS experiment_name,
                e.slug AS experiment_slug,
                e.mode AS experiment_mode,
                (
                    SELECT COUNT(*)
                    FROM turns t
                    WHERE t.session_id = s.id
                ) AS turn_count,
                (
                    SELECT COUNT(*)
                    FROM feedback_events f
                    WHERE f.session_id = s.id
                ) AS feedback_count,
                COALESCE(
                    (
                        SELECT MAX(t.created_at)
                        FROM turns t
                        WHERE t.session_id = s.id
                    ),
                    s.updated_at
                ) AS last_turn_at,
                (
                    SELECT t.user_text
                    FROM turns t
                    WHERE t.session_id = s.id
                    ORDER BY t.turn_index DESC
                    LIMIT 1
                ) AS last_user_text,
                (
                    SELECT COALESCE(t.membrane_text, t.response_text, '')
                    FROM turns t
                    WHERE t.session_id = s.id
                    ORDER BY t.turn_index DESC
                    LIMIT 1
                ) AS last_response_text
            FROM sessions s
            JOIN experiments e ON e.id = s.experiment_id
            ORDER BY s.updated_at DESC, s.created_at DESC
        """
        params: list[Any] = []
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        rows = self._fetchall(sql, tuple(params))
        return [_row_to_dict(row) for row in rows if row is not None]

    def get_next_turn_index(self, session_id: str) -> int:
        row = self._fetchone(
            "SELECT COALESCE(MAX(turn_index), -1) + 1 AS turn_index FROM turns WHERE session_id = ?",
            (session_id,),
        )
        return int(row["turn_index"]) if row is not None else 0

    def record_turn(
        self,
        *,
        experiment_id: str,
        session_id: str,
        user_text: str,
        prompt_context: str,
        response_text: str,
        membrane_text: str,
        active_set: list[dict[str, Any]],
        trace: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        turn_id = str(uuid4())
        turn_index = self.get_next_turn_index(session_id)
        created_at = now_utc()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO turns(
                    id, experiment_id, session_id, turn_index, user_text, prompt_context,
                    response_text, membrane_text, active_set_json, trace_json, metadata_json, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    turn_id,
                    experiment_id,
                    session_id,
                    turn_index,
                    user_text,
                    prompt_context,
                    response_text,
                    membrane_text,
                    compact_json(active_set),
                    compact_json(trace),
                    compact_json(metadata or {}),
                    created_at,
                ),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (created_at, session_id),
            )
        return self.get_turn(turn_id)

    def get_turn(self, turn_id: str) -> dict[str, Any]:
        row = self._fetchone("SELECT * FROM turns WHERE id = ?", (turn_id,))
        if row is None:
            raise KeyError(f"Unknown turn: {turn_id}")
        return _row_to_dict(row) or {}

    def list_turns(self, session_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_index DESC LIMIT ?",
            (session_id, limit),
        )
        return [_row_to_dict(row) for row in rows if row is not None]

    def list_all_turns(self, session_id: str) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_index ASC",
            (session_id,),
        )
        return [_row_to_dict(row) for row in rows if row is not None]

    def record_feedback(
        self,
        *,
        experiment_id: str,
        session_id: str,
        turn_id: str,
        verdict: str,
        explanation: str,
        corrected_text: str,
        signal: dict[str, Any],
    ) -> dict[str, Any]:
        feedback_id = str(uuid4())
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO feedback_events(
                    id, experiment_id, session_id, turn_id, verdict, explanation, corrected_text, created_at, signal_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback_id,
                    experiment_id,
                    session_id,
                    turn_id,
                    verdict,
                    explanation,
                    corrected_text,
                    now_utc(),
                    compact_json(signal),
                ),
            )
        return self.get_feedback(feedback_id)

    def get_feedback(self, feedback_id: str) -> dict[str, Any]:
        row = self._fetchone("SELECT * FROM feedback_events WHERE id = ?", (feedback_id,))
        if row is None:
            raise KeyError(f"Unknown feedback event: {feedback_id}")
        return _row_to_dict(row) or {}

    def list_feedback_for_turn(self, turn_id: str) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM feedback_events WHERE turn_id = ? ORDER BY created_at ASC",
            (turn_id,),
        )
        return [_row_to_dict(row) for row in rows if row is not None]

    def upsert_document(
        self,
        *,
        experiment_id: str,
        path: Path,
        kind: str,
        title: str,
        status: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        digest = sha256_file(path)
        row = self._fetchone(
            "SELECT id FROM documents WHERE experiment_id = ? AND sha256 = ?",
            (experiment_id, digest),
        )
        if row is not None:
            doc_id = str(row["id"])
            with self.transaction() as conn:
                conn.execute(
                    """
                    UPDATE documents
                    SET path = ?, kind = ?, title = ?, status = ?, metadata_json = ?
                    WHERE id = ?
                    """,
                    (str(path), kind, title, status, compact_json(metadata), doc_id),
                )
            return self.get_document(doc_id)
        doc_id = str(uuid4())
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO documents(id, experiment_id, path, kind, title, sha256, status, created_at, metadata_json)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    experiment_id,
                    str(path),
                    kind,
                    title,
                    digest,
                    status,
                    now_utc(),
                    compact_json(metadata),
                ),
            )
        return self.get_document(doc_id)

    def get_document(self, document_id: str) -> dict[str, Any]:
        row = self._fetchone("SELECT * FROM documents WHERE id = ?", (document_id,))
        if row is None:
            raise KeyError(f"Unknown document: {document_id}")
        return _row_to_dict(row) or {}

    def get_document_by_sha(self, experiment_id: str, sha256: str) -> dict[str, Any] | None:
        row = self._fetchone(
            """
            SELECT d.*
            FROM documents d
            LEFT JOIN (
                SELECT document_id, COUNT(*) AS chunk_count
                FROM document_chunks
                GROUP BY document_id
            ) ch ON ch.document_id = d.id
            WHERE d.experiment_id = ? AND d.sha256 = ?
            ORDER BY
                CASE d.status
                    WHEN 'ingested' THEN 2
                    WHEN 'processing' THEN 1
                    ELSE 0
                END DESC,
                COALESCE(ch.chunk_count, 0) DESC,
                d.created_at DESC,
                d.id DESC
            LIMIT 1
            """,
            (experiment_id, sha256),
        )
        return _row_to_dict(row) if row is not None else None

    def document_chunk_count(self, document_id: str) -> int:
        row = self._fetchone(
            "SELECT COUNT(*) AS count FROM document_chunks WHERE document_id = ?",
            (document_id,),
        )
        return int(row["count"]) if row is not None else 0

    def reset_document_chunks(self, document_id: str) -> None:
        chunk_rows = self._fetchall("SELECT id FROM document_chunks WHERE document_id = ?", (document_id,))
        with self.transaction() as conn:
            if chunk_rows:
                conn.executemany(
                    "DELETE FROM chunk_fts WHERE chunk_id = ?",
                    [(str(row["id"]),) for row in chunk_rows],
                )
            conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))

    def add_document_chunk(
        self,
        *,
        experiment_id: str,
        document_id: str,
        chunk_index: int,
        text: str,
        page_number: int | None,
        metadata: dict[str, Any],
        title: str,
    ) -> str:
        chunk_id = str(uuid4())
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO document_chunks(
                    id, experiment_id, document_id, chunk_index, page_number, text, metadata_json, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (chunk_id, experiment_id, document_id, chunk_index, page_number, text, compact_json(metadata), now_utc()),
            )
            conn.execute(
                "INSERT INTO chunk_fts(chunk_id, title, text) VALUES(?, ?, ?)",
                (chunk_id, title, text),
            )
        return chunk_id

    def upsert_meme(
        self,
        *,
        experiment_id: str,
        label: str,
        text: str,
        domain: str,
        source_kind: str,
        scope: str = "global",
        evidence_inc: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        canonical_label = slugify(label)
        existing = self._fetchone(
            """
            SELECT * FROM memes WHERE experiment_id = ? AND canonical_label = ? AND domain = ?
            """,
            (experiment_id, canonical_label, domain),
        )
        if existing is not None:
            meme_id = str(existing["id"])
            merged_metadata = json.loads(existing["metadata_json"] or "{}")
            merged_metadata.update(metadata or {})
            with self.transaction() as conn:
                conn.execute(
                    """
                    UPDATE memes
                    SET text = ?, evidence_n = evidence_n + ?, updated_at = ?, metadata_json = ?, source_kind = ?, scope = ?
                    WHERE id = ?
                    """,
                    (text, evidence_inc, now_utc(), compact_json(merged_metadata), source_kind, scope, meme_id),
                )
                conn.execute("DELETE FROM meme_fts WHERE meme_id = ?", (meme_id,))
                conn.execute(
                    "INSERT INTO meme_fts(meme_id, label, text, domain) VALUES(?, ?, ?, ?)",
                    (meme_id, label, text, domain),
                )
            return self.get_meme(meme_id)
        meme_id = str(uuid4())
        created_at = now_utc()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO memes(
                    id, experiment_id, label, canonical_label, text, domain, source_kind, scope,
                    evidence_n, last_active_at, metadata_json, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meme_id,
                    experiment_id,
                    label,
                    canonical_label,
                    text,
                    domain,
                    source_kind,
                    scope,
                    evidence_inc,
                    created_at,
                    compact_json(metadata or {}),
                    created_at,
                    created_at,
                ),
            )
            conn.execute(
                "INSERT INTO meme_fts(meme_id, label, text, domain) VALUES(?, ?, ?, ?)",
                (meme_id, label, text, domain),
            )
        return self.get_meme(meme_id)

    def get_meme(self, meme_id: str) -> dict[str, Any]:
        row = self._fetchone("SELECT * FROM memes WHERE id = ?", (meme_id,))
        if row is None:
            raise KeyError(f"Unknown meme: {meme_id}")
        return _row_to_dict(row) or {}

    def list_memes(self, experiment_id: str) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM memes WHERE experiment_id = ? ORDER BY evidence_n DESC, updated_at DESC",
            (experiment_id,),
        )
        return [_row_to_dict(row) for row in rows if row is not None]

    def upsert_memode(
        self,
        *,
        experiment_id: str,
        label: str,
        member_ids: list[str],
        summary: str,
        domain: str,
        scope: str = "global",
        evidence_inc: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        member_ids = sorted(dict.fromkeys(member_ids))
        if len(member_ids) < 2:
            raise ValueError("Memodes require at least two member memes.")
        member_hash = slugify("-".join(member_ids))
        existing = self._fetchone(
            "SELECT * FROM memodes WHERE experiment_id = ? AND member_hash = ? AND domain = ?",
            (experiment_id, member_hash, domain),
        )
        if existing is not None:
            memode_id = str(existing["id"])
            merged_metadata = json.loads(existing["metadata_json"] or "{}")
            merged_metadata.update(metadata or {})
            with self.transaction() as conn:
                conn.execute(
                    """
                    UPDATE memodes
                    SET label = ?, summary = ?, evidence_n = evidence_n + ?, updated_at = ?, metadata_json = ?, scope = ?
                    WHERE id = ?
                    """,
                    (label, summary, evidence_inc, now_utc(), compact_json(merged_metadata), scope, memode_id),
                )
                conn.execute("DELETE FROM memode_fts WHERE memode_id = ?", (memode_id,))
                conn.execute(
                    "INSERT INTO memode_fts(memode_id, label, summary, domain) VALUES(?, ?, ?, ?)",
                    (memode_id, label, summary, domain),
                )
            return self.get_memode(memode_id)
        memode_id = str(uuid4())
        created_at = now_utc()
        payload = {"member_ids": member_ids}
        if metadata:
            payload.update(metadata)
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO memodes(
                    id, experiment_id, label, member_hash, summary, domain, scope, evidence_n,
                    last_active_at, metadata_json, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memode_id,
                    experiment_id,
                    label,
                    member_hash,
                    summary,
                    domain,
                    scope,
                    evidence_inc,
                    created_at,
                    compact_json(payload),
                    created_at,
                    created_at,
                ),
            )
            conn.execute(
                "INSERT INTO memode_fts(memode_id, label, summary, domain) VALUES(?, ?, ?, ?)",
                (memode_id, label, summary, domain),
            )
        return self.get_memode(memode_id)

    def get_memode(self, memode_id: str) -> dict[str, Any]:
        row = self._fetchone("SELECT * FROM memodes WHERE id = ?", (memode_id,))
        if row is None:
            raise KeyError(f"Unknown memode: {memode_id}")
        return _row_to_dict(row) or {}

    def list_memodes(self, experiment_id: str) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM memodes WHERE experiment_id = ? ORDER BY evidence_n DESC, updated_at DESC",
            (experiment_id,),
        )
        return [_row_to_dict(row) for row in rows if row is not None]

    def update_memode(
        self,
        *,
        memode_id: str,
        label: str | None = None,
        member_ids: list[str] | None = None,
        summary: str | None = None,
        domain: str | None = None,
        scope: str | None = None,
        metadata_updates: dict[str, Any] | None = None,
        evidence_inc: float = 0.0,
    ) -> dict[str, Any]:
        existing = self.get_memode(memode_id)
        metadata = json.loads(existing["metadata_json"] or "{}")
        next_member_ids = sorted(dict.fromkeys(member_ids or metadata.get("member_ids", [])))
        if len(next_member_ids) < 2:
            raise ValueError("Memodes require at least two member memes.")
        next_domain = domain or existing["domain"]
        next_member_hash = slugify("-".join(next_member_ids))
        duplicate = self._fetchone(
            """
            SELECT id FROM memodes
            WHERE experiment_id = ? AND member_hash = ? AND domain = ? AND id != ?
            """,
            (existing["experiment_id"], next_member_hash, next_domain, memode_id),
        )
        if duplicate is not None:
            raise ValueError("A memode with the requested membership already exists.")
        metadata["member_ids"] = next_member_ids
        if metadata_updates:
            metadata.update(metadata_updates)
        with self.transaction() as conn:
            conn.execute(
                """
                UPDATE memodes
                SET label = ?, member_hash = ?, summary = ?, domain = ?, scope = ?,
                    evidence_n = evidence_n + ?, updated_at = ?, metadata_json = ?
                WHERE id = ?
                """,
                (
                    label or existing["label"],
                    next_member_hash,
                    summary or existing["summary"],
                    next_domain,
                    scope or existing["scope"],
                    evidence_inc,
                    now_utc(),
                    compact_json(metadata),
                    memode_id,
                ),
            )
            conn.execute("DELETE FROM memode_fts WHERE memode_id = ?", (memode_id,))
            conn.execute(
                "INSERT INTO memode_fts(memode_id, label, summary, domain) VALUES(?, ?, ?, ?)",
                (memode_id, label or existing["label"], summary or existing["summary"], next_domain),
            )
        return self.get_memode(memode_id)

    def delete_memode(self, memode_id: str) -> dict[str, Any]:
        existing = self.get_memode(memode_id)
        with self.transaction() as conn:
            conn.execute("DELETE FROM memode_fts WHERE memode_id = ?", (memode_id,))
            conn.execute(
                """
                DELETE FROM edges
                WHERE (src_kind = 'memode' AND src_id = ?) OR (dst_kind = 'memode' AND dst_id = ?)
                """,
                (memode_id, memode_id),
            )
            conn.execute("DELETE FROM memodes WHERE id = ?", (memode_id,))
        return existing

    def add_edge(
        self,
        *,
        experiment_id: str,
        src_kind: str,
        src_id: str,
        dst_kind: str,
        dst_id: str,
        edge_type: str,
        weight: float = 1.0,
        provenance: dict[str, Any] | None = None,
    ) -> None:
        edge_id = str(uuid4())
        created_at = now_utc()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO edges(
                    id, experiment_id, src_kind, src_id, dst_kind, dst_id, edge_type, weight,
                    provenance_json, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(experiment_id, src_kind, src_id, dst_kind, dst_id, edge_type)
                DO UPDATE SET
                    weight = edges.weight + excluded.weight,
                    provenance_json = excluded.provenance_json,
                    updated_at = excluded.updated_at
                """,
                (
                    edge_id,
                    experiment_id,
                    src_kind,
                    src_id,
                    dst_kind,
                    dst_id,
                    edge_type,
                    weight,
                    compact_json(provenance or {}),
                    created_at,
                    created_at,
                ),
            )

    def set_edge(
        self,
        *,
        experiment_id: str,
        src_kind: str,
        src_id: str,
        dst_kind: str,
        dst_id: str,
        edge_type: str,
        weight: float = 1.0,
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = self.get_edge(
            experiment_id=experiment_id,
            src_kind=src_kind,
            src_id=src_id,
            dst_kind=dst_kind,
            dst_id=dst_id,
            edge_type=edge_type,
        )
        edge_id = existing["id"] if existing is not None else str(uuid4())
        created_at = existing["created_at"] if existing is not None else now_utc()
        updated_at = now_utc()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO edges(
                    id, experiment_id, src_kind, src_id, dst_kind, dst_id, edge_type, weight,
                    provenance_json, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(experiment_id, src_kind, src_id, dst_kind, dst_id, edge_type)
                DO UPDATE SET
                    weight = excluded.weight,
                    provenance_json = excluded.provenance_json,
                    updated_at = excluded.updated_at
                """,
                (
                    edge_id,
                    experiment_id,
                    src_kind,
                    src_id,
                    dst_kind,
                    dst_id,
                    edge_type,
                    weight,
                    compact_json(provenance or {}),
                    created_at,
                    updated_at,
                ),
            )
        row = self.get_edge(
            experiment_id=experiment_id,
            src_kind=src_kind,
            src_id=src_id,
            dst_kind=dst_kind,
            dst_id=dst_id,
            edge_type=edge_type,
        )
        if row is None:
            raise KeyError("Failed to persist edge.")
        return row

    def get_edge(
        self,
        *,
        experiment_id: str,
        src_kind: str,
        src_id: str,
        dst_kind: str,
        dst_id: str,
        edge_type: str,
    ) -> dict[str, Any] | None:
        row = self._fetchone(
            """
            SELECT * FROM edges
            WHERE experiment_id = ? AND src_kind = ? AND src_id = ? AND dst_kind = ? AND dst_id = ? AND edge_type = ?
            """,
            (experiment_id, src_kind, src_id, dst_kind, dst_id, edge_type),
        )
        return _row_to_dict(row)

    def delete_edge(
        self,
        *,
        experiment_id: str,
        src_kind: str,
        src_id: str,
        dst_kind: str,
        dst_id: str,
        edge_type: str,
    ) -> dict[str, Any] | None:
        existing = self.get_edge(
            experiment_id=experiment_id,
            src_kind=src_kind,
            src_id=src_id,
            dst_kind=dst_kind,
            dst_id=dst_id,
            edge_type=edge_type,
        )
        if existing is None:
            return None
        with self.transaction() as conn:
            conn.execute(
                """
                DELETE FROM edges
                WHERE experiment_id = ? AND src_kind = ? AND src_id = ? AND dst_kind = ? AND dst_id = ? AND edge_type = ?
                """,
                (experiment_id, src_kind, src_id, dst_kind, dst_id, edge_type),
            )
        return existing

    def list_edges(self, experiment_id: str) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM edges WHERE experiment_id = ? ORDER BY weight DESC, updated_at DESC",
            (experiment_id,),
        )
        return [_row_to_dict(row) for row in rows if row is not None]

    def list_edges_for_node(
        self,
        experiment_id: str,
        *,
        node_kind: str,
        node_id: str,
        edge_type: str | None = None,
    ) -> list[dict[str, Any]]:
        if edge_type:
            rows = self._fetchall(
                """
                SELECT * FROM edges
                WHERE experiment_id = ?
                  AND ((src_kind = ? AND src_id = ?) OR (dst_kind = ? AND dst_id = ?))
                  AND edge_type = ?
                ORDER BY updated_at DESC
                """,
                (experiment_id, node_kind, node_id, node_kind, node_id, edge_type),
            )
        else:
            rows = self._fetchall(
                """
                SELECT * FROM edges
                WHERE experiment_id = ?
                  AND ((src_kind = ? AND src_id = ?) OR (dst_kind = ? AND dst_id = ?))
                ORDER BY updated_at DESC
                """,
                (experiment_id, node_kind, node_id, node_kind, node_id),
            )
        return [_row_to_dict(row) for row in rows if row is not None]

    def touch_nodes(self, node_kind: str, node_ids: list[str]) -> None:
        if not node_ids:
            return
        placeholder = ",".join("?" for _ in node_ids)
        table = "memes" if node_kind == "meme" else "memodes"
        with self.transaction() as conn:
            conn.execute(
                f"UPDATE {table} SET usage_count = usage_count + 1, last_active_at = ?, updated_at = ? WHERE id IN ({placeholder})",
                [now_utc(), now_utc(), *node_ids],
            )

    def update_feedback_channels(self, node_kind: str, node_id: str, *, reward: float, risk: float, edit: float) -> None:
        table = "memes" if node_kind == "meme" else "memodes"
        with self.transaction() as conn:
            conn.execute(
                f"""
                UPDATE {table}
                SET reward_ema = ?, risk_ema = ?, edit_ema = ?, feedback_count = feedback_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (reward, risk, edit, now_utc(), node_id),
            )

    def bump_skip_count(self, node_kind: str, node_id: str) -> None:
        table = "memes" if node_kind == "meme" else "memodes"
        with self.transaction() as conn:
            conn.execute(
                f"UPDATE {table} SET skip_count = skip_count + 1, updated_at = ? WHERE id = ?",
                (now_utc(), node_id),
            )

    def increment_membrane_conflict(self, node_kind: str, node_id: str) -> None:
        table = "memes" if node_kind == "meme" else "memodes"
        with self.transaction() as conn:
            conn.execute(
                f"UPDATE {table} SET membrane_conflicts = membrane_conflicts + 1, updated_at = ? WHERE id = ?",
                (now_utc(), node_id),
            )

    def store_active_set(
        self,
        *,
        experiment_id: str,
        session_id: str,
        turn_id: str,
        query_text: str,
        items: list[dict[str, Any]],
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO active_sets(id, experiment_id, session_id, turn_id, query_text, items_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid4()), experiment_id, session_id, turn_id, query_text, compact_json(items), now_utc()),
            )

    def record_trace_event(
        self,
        *,
        experiment_id: str | None,
        session_id: str | None,
        turn_id: str | None,
        event_type: str,
        level: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO trace_events(id, experiment_id, session_id, turn_id, event_type, level, message, payload_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    experiment_id,
                    session_id,
                    turn_id,
                    event_type,
                    level,
                    message,
                    compact_json(payload or {}),
                    now_utc(),
                ),
            )

    def record_membrane_event(
        self,
        *,
        experiment_id: str,
        session_id: str,
        turn_id: str | None,
        event_type: str,
        detail: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO membrane_events(id, experiment_id, session_id, turn_id, event_type, detail, payload_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    experiment_id,
                    session_id,
                    turn_id,
                    event_type,
                    detail,
                    compact_json(payload or {}),
                    now_utc(),
                ),
            )

    def list_trace_events(self, experiment_id: str, *, limit: int = 100, session_id: str | None = None) -> list[dict[str, Any]]:
        if session_id:
            rows = self._fetchall(
                """
                SELECT * FROM trace_events
                WHERE experiment_id = ? AND session_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (experiment_id, session_id, limit),
            )
        else:
            rows = self._fetchall(
                "SELECT * FROM trace_events WHERE experiment_id = ? ORDER BY created_at DESC LIMIT ?",
                (experiment_id, limit),
            )
        return [_row_to_dict(row) for row in rows if row is not None]

    def list_membrane_events(self, experiment_id: str, *, limit: int = 60, session_id: str | None = None) -> list[dict[str, Any]]:
        if session_id:
            rows = self._fetchall(
                """
                SELECT * FROM membrane_events
                WHERE experiment_id = ? AND session_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (experiment_id, session_id, limit),
            )
        else:
            rows = self._fetchall(
                "SELECT * FROM membrane_events WHERE experiment_id = ? ORDER BY created_at DESC LIMIT ?",
                (experiment_id, limit),
            )
        return [_row_to_dict(row) for row in rows if row is not None]

    def record_export_artifact(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        artifact_type: str,
        path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO export_artifacts(id, experiment_id, session_id, artifact_type, path, metadata_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid4()), experiment_id, session_id, artifact_type, str(path), compact_json(metadata or {}), now_utc()),
            )

    def record_measurement_event(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        turn_id: str | None,
        action_type: str,
        target_ids: list[dict[str, Any]],
        before_state: dict[str, Any],
        proposed_state: dict[str, Any],
        committed_state: dict[str, Any],
        rationale: str,
        operator_label: str,
        evidence_label: str,
        measurement_method: str,
        confidence: float,
        reverted_from_event_id: str | None = None,
    ) -> dict[str, Any]:
        event_id = str(uuid4())
        created_at = now_utc()
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO measurement_events(
                    id, experiment_id, session_id, turn_id, action_type, target_ids_json,
                    before_state_json, proposed_state_json, committed_state_json,
                    rationale, operator_label, evidence_label, measurement_method,
                    confidence, created_at, reverted_from_event_id
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    experiment_id,
                    session_id,
                    turn_id,
                    action_type,
                    compact_json(target_ids),
                    compact_json(before_state),
                    compact_json(proposed_state),
                    compact_json(committed_state),
                    rationale,
                    operator_label,
                    evidence_label,
                    measurement_method,
                    confidence,
                    created_at,
                    reverted_from_event_id,
                ),
            )
        return self.get_measurement_event(event_id)

    def get_measurement_event(self, event_id: str) -> dict[str, Any]:
        row = self._fetchone("SELECT * FROM measurement_events WHERE id = ?", (event_id,))
        if row is None:
            raise KeyError(f"Unknown measurement event: {event_id}")
        return _row_to_dict(row) or {}

    def list_measurement_events(
        self,
        experiment_id: str,
        *,
        limit: int = 250,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if session_id:
            rows = self._fetchall(
                """
                SELECT * FROM measurement_events
                WHERE experiment_id = ? AND session_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (experiment_id, session_id, limit),
            )
        else:
            rows = self._fetchall(
                "SELECT * FROM measurement_events WHERE experiment_id = ? ORDER BY created_at DESC LIMIT ?",
                (experiment_id, limit),
            )
        return [_row_to_dict(row) for row in rows if row is not None]

    def list_export_artifacts(self, experiment_id: str) -> list[dict[str, Any]]:
        rows = self._fetchall(
            "SELECT * FROM export_artifacts WHERE experiment_id = ? ORDER BY created_at DESC",
            (experiment_id,),
        )
        return [_row_to_dict(row) for row in rows if row is not None]

    def search_memes(self, experiment_id: str, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        tokens = tokenize(query)[:8]
        if not tokens:
            return []
        safe_query = " OR ".join(f'"{token}"' for token in tokens)
        rows = self._fetchall(
            """
            SELECT m.*, bm25(meme_fts) AS bm25_score
            FROM meme_fts
            JOIN memes m ON m.id = meme_fts.meme_id
            WHERE m.experiment_id = ? AND meme_fts MATCH ?
            ORDER BY bm25_score LIMIT ?
            """,
            (experiment_id, safe_query, limit),
        )
        return [_row_to_dict(row) for row in rows if row is not None]

    def search_memodes(self, experiment_id: str, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        tokens = tokenize(query)[:8]
        if not tokens:
            return []
        safe_query = " OR ".join(f'"{token}"' for token in tokens)
        rows = self._fetchall(
            """
            SELECT md.*, bm25(memode_fts) AS bm25_score
            FROM memode_fts
            JOIN memodes md ON md.id = memode_fts.memode_id
            WHERE md.experiment_id = ? AND memode_fts MATCH ?
            ORDER BY bm25_score LIMIT ?
            """,
            (experiment_id, safe_query, limit),
        )
        return [_row_to_dict(row) for row in rows if row is not None]

    def recent_feedback(self, session_id: str, *, limit: int = 8) -> list[dict[str, Any]]:
        rows = self._fetchall(
            """
            SELECT f.*, t.turn_index, t.user_text, t.response_text
            FROM feedback_events f
            JOIN turns t ON t.id = f.turn_id
            WHERE f.session_id = ?
            ORDER BY f.created_at DESC LIMIT ?
            """,
            (session_id, limit),
        )
        return [_row_to_dict(row) for row in rows if row is not None]

    def graph_snapshot(self, experiment_id: str) -> dict[str, Any]:
        memes = self.list_memes(experiment_id)
        memodes = self.list_memodes(experiment_id)
        edges = self.list_edges(experiment_id)
        agents = self._fetchall("SELECT * FROM agents ORDER BY created_at ASC")
        sessions = self._fetchall(
            "SELECT * FROM sessions WHERE experiment_id = ? ORDER BY created_at DESC",
            (experiment_id,),
        )
        turns = self._fetchall(
            "SELECT * FROM turns WHERE experiment_id = ? ORDER BY created_at ASC",
            (experiment_id,),
        )
        docs = self._fetchall(
            "SELECT * FROM documents WHERE experiment_id = ? ORDER BY created_at ASC",
            (experiment_id,),
        )
        feedback_rows = self._fetchall(
            "SELECT * FROM feedback_events WHERE experiment_id = ? ORDER BY created_at ASC",
            (experiment_id,),
        )
        trace_rows = self._fetchall(
            "SELECT * FROM trace_events WHERE experiment_id = ? ORDER BY created_at ASC",
            (experiment_id,),
        )
        membrane_rows = self._fetchall(
            "SELECT * FROM membrane_events WHERE experiment_id = ? ORDER BY created_at ASC",
            (experiment_id,),
        )
        export_rows = self._fetchall(
            "SELECT * FROM export_artifacts WHERE experiment_id = ? ORDER BY created_at ASC",
            (experiment_id,),
        )
        measurement_rows = self._fetchall(
            "SELECT * FROM measurement_events WHERE experiment_id = ? ORDER BY created_at ASC",
            (experiment_id,),
        )
        return {
            "agents": [_row_to_dict(row) for row in agents if row is not None],
            "memes": memes,
            "memodes": memodes,
            "edges": edges,
            "sessions": [_row_to_dict(row) for row in sessions if row is not None],
            "turns": [_row_to_dict(row) for row in turns if row is not None],
            "documents": [_row_to_dict(row) for row in docs if row is not None],
            "feedback": [_row_to_dict(row) for row in feedback_rows if row is not None],
            "trace_events": [_row_to_dict(row) for row in trace_rows if row is not None],
            "membrane_events": [_row_to_dict(row) for row in membrane_rows if row is not None],
            "export_artifacts": [_row_to_dict(row) for row in export_rows if row is not None],
            "measurement_events": [_row_to_dict(row) for row in measurement_rows if row is not None],
        }

    def graph_counts(self, experiment_id: str) -> dict[str, int]:
        def count(table: str) -> int:
            row = self._fetchone(f"SELECT COUNT(*) AS n FROM {table} WHERE experiment_id = ?", (experiment_id,))
            return int(row["n"]) if row is not None else 0

        return {
            "sessions": count("sessions"),
            "turns": count("turns"),
            "documents": count("documents"),
            "memes": count("memes"),
            "memodes": count("memodes"),
            "edges": count("edges"),
            "feedback": count("feedback_events"),
            "measurement_events": count("measurement_events"),
        }

    def summarize_history(self, session_id: str, *, limit: int = 5) -> list[str]:
        turns = self.list_turns(session_id, limit=limit)
        summary: list[str] = []
        for turn in reversed(turns):
            summary.append(
                f"T{turn['turn_index']} user={safe_excerpt(turn['user_text'], limit=72)} | adam={safe_excerpt(turn['response_text'], limit=72)}"
            )
        return summary
