from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from eden.ingest.extractors import extract_pdf, iter_extract_document, normalize_pdf_text, score_pdf_text_quality
from eden.storage.graph_store import GraphStore
from eden.storage.schema import SCHEMA_SQL
from eden.utils import now_utc, sha256_file


PAGES_MEMOIR_PATH = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "cannonical_secondary_sources"
    / "bad_trip_with_jesus_theory_memoir.pdf"
)


def test_ingest_supported_formats(runtime, sample_files) -> None:
    experiment = runtime.initialize_experiment("blank")
    for path in sample_files.values():
        result = runtime.ingest_document(experiment_id=experiment["id"], path=str(path))
        assert result["status"] == "ingested"
        assert result["chunk_count"] >= 1
        assert result["quality_state"] in {"clean", "degraded"}
        assert result["quality_score"] > 0
    counts = runtime.store.graph_counts(experiment["id"])
    assert counts["documents"] == 4
    assert counts["memes"] > 6
    assert counts["memodes"] >= 1


def test_ingest_reuses_existing_document_without_duplicate_rows(runtime, sample_files) -> None:
    experiment = runtime.initialize_experiment("blank")
    path = sample_files["pdf"]

    first = runtime.ingest_document(experiment_id=experiment["id"], path=str(path))
    second = runtime.ingest_document(experiment_id=experiment["id"], path=str(path))

    assert second["status"] == "ingested"
    assert second["document_id"] == first["document_id"]
    assert "existing ingest reused" in second["notes"]
    assert runtime.store.document_chunk_count(first["document_id"]) == first["chunk_count"]

    digest = sha256_file(path)
    rows = runtime.store._fetchall(
        "SELECT id, status FROM documents WHERE experiment_id = ? AND sha256 = ?",
        (experiment["id"], digest),
    )
    assert len(rows) == 1
    assert rows[0]["id"] == first["document_id"]
    assert rows[0]["status"] == "ingested"


def test_markdown_ingest_persists_all_extracted_units(runtime, tmp_path: Path) -> None:
    experiment = runtime.initialize_experiment("blank")
    md_path = tmp_path / "memoir_excerpt.md"
    md_path.write_text(
        "# Memoir Excerpt\n\n"
        + " ".join(["EDEN remembers through external graph state."] * 180),
        encoding="utf-8",
    )

    extracted_units = list(iter_extract_document(md_path))
    assert len(extracted_units) >= 3

    result = runtime.ingest_document(experiment_id=experiment["id"], path=str(md_path))
    assert result["status"] == "ingested"
    assert result["chunk_count"] == len(extracted_units)
    assert runtime.store.document_chunk_count(result["document_id"]) >= len(extracted_units)

    chunk_indexes = runtime.store._fetchall(
        "SELECT chunk_index FROM document_chunks WHERE document_id = ? ORDER BY chunk_index ASC",
        (result["document_id"],),
    )
    assert len(chunk_indexes) >= len(extracted_units)
    assert len({int(row["chunk_index"]) for row in chunk_indexes}) == len(chunk_indexes)


def test_ingest_failure_marks_document_failed(runtime, sample_files, monkeypatch) -> None:
    experiment = runtime.initialize_experiment("blank")
    path = sample_files["pdf"]

    def explode(_path):
        raise RuntimeError("synthetic extractor failure")
        yield  # pragma: no cover

    monkeypatch.setattr("eden.ingest.pipeline.iter_extract_document", explode)

    with pytest.raises(RuntimeError, match="synthetic extractor failure"):
        runtime.ingest_document(experiment_id=experiment["id"], path=str(path))

    digest = sha256_file(path)
    document = runtime.store.get_document_by_sha(experiment["id"], digest)
    assert document is not None
    assert document["status"] == "failed"


def test_normalize_pdf_text_repairs_ligatures_artifacts_and_hyphenation() -> None:
    raw = "Kay Red\ufb01eld Jamison\nfi\nCrossroads Bap-\ntist Church\n"
    normalized, cleanup_flags = normalize_pdf_text(raw)
    score, quality_flags, _ = score_pdf_text_quality(raw, normalized, cleanup_flags)

    assert "Kay Redfield Jamison" in normalized
    assert "Crossroads Baptist Church" in normalized
    assert "\nfi\n" not in f"\n{normalized}\n"
    assert "ligatures_normalized" in cleanup_flags
    assert "artifact_lines_removed" in cleanup_flags
    assert "hyphenated_linebreaks_repaired" in cleanup_flags
    assert "replacement_glyphs" not in quality_flags
    assert score > 0.45


def test_pages_pdf_fixture_extracts_readable_text() -> None:
    pages = extract_pdf(PAGES_MEMOIR_PATH)

    assert len(pages) == 138
    first_page = str(pages[0]["text"])
    second_page = str(pages[1]["text"])
    first_flags = list(pages[0]["quality_flags"])

    assert "Set and Setting" in first_page
    assert "I didn’t think I’d ever turn thirty years old." in first_page
    assert "\ufb01" not in first_page + second_page
    assert "\nfi\n" not in f"\n{first_page}\n"
    assert pages[0]["quality_score"] > 0.2
    assert isinstance(first_flags, list)


def test_degraded_ingest_persists_quality_metadata_and_trace(runtime, sample_files, monkeypatch) -> None:
    experiment = runtime.initialize_experiment("blank")
    path = sample_files["pdf"]

    def degraded(_path):
        yield {
            "page_number": 1,
            "text": "EDEN graph memory remains available, but this extraction is visibly fragmented.",
            "parser": "pdfplumber",
            "quality_score": 0.55,
            "quality_flags": ["fragmented_lines"],
        }

    monkeypatch.setattr("eden.ingest.pipeline.iter_extract_document", degraded)

    result = runtime.ingest_document(experiment_id=experiment["id"], path=str(path))
    assert result["status"] == "ingested"
    assert result["quality_state"] == "degraded"
    assert "fragmented_lines" in result["quality_flags"]

    document = runtime.store.get_document(result["document_id"])
    metadata = json.loads(document["metadata_json"])
    assert metadata["quality_state"] == "degraded"
    assert metadata["quality_score"] == pytest.approx(0.55)
    assert "fragmented_lines" in metadata["quality_flags"]
    assert metadata["selected_parser_counts"] == {"pdfplumber": 1}

    chunk = runtime.store._fetchone("SELECT metadata_json FROM document_chunks WHERE document_id = ?", (result["document_id"],))
    assert chunk is not None
    chunk_metadata = json.loads(chunk["metadata_json"])
    assert chunk_metadata["quality_score"] == pytest.approx(0.55)
    assert "fragmented_lines" in chunk_metadata["quality_flags"]

    trace = runtime.store._fetchone(
        """
        SELECT payload_json
        FROM trace_events
        WHERE experiment_id = ? AND event_type = 'INGEST' AND message LIKE 'Completed ingest%'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (experiment["id"],),
    )
    assert trace is not None
    payload = json.loads(trace["payload_json"])
    assert payload["quality_state"] == "degraded"
    assert "fragmented_lines" in payload["quality_flags"]
    assert payload["selected_parser_counts"] == {"pdfplumber": 1}


def test_retrieval_prompt_context_groups_document_evidence(runtime, sample_files) -> None:
    experiment = runtime.initialize_experiment("blank")
    runtime.ingest_document(experiment_id=experiment["id"], path=str(sample_files["pdf"]))
    session = runtime.start_session(experiment["id"], title="Document Proof")

    retrieval = runtime.retrieval_service.retrieve(
        experiment_id=experiment["id"],
        session_id=session["id"],
        query="EDEN PDF memory graph",
        settings=runtime.settings,
    )

    assert "[KNOWLEDGE:document] sample.pdf" in retrieval["prompt_context"]
    assert f"provenance={sample_files['pdf']}" in retrieval["prompt_context"]
    assert "page=1" in retrieval["prompt_context"]
    assert "excerpt=" in retrieval["prompt_context"]


def test_document_sha_dedupe_migration_merges_duplicate_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "eden.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    now = now_utc()
    experiment_id = "exp-1"
    conn.execute(
        "INSERT INTO experiments(id, name, slug, mode, status, created_at, updated_at, metadata_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        (experiment_id, "Adam Graph", "adam-graph", "persistent", "ready", now, now, "{}"),
    )
    ingested_id = "doc-ingested"
    processing_id = "doc-processing"
    sha = "same-sha"
    conn.execute(
        "INSERT INTO documents(id, experiment_id, path, kind, title, sha256, status, created_at, metadata_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ingested_id,
            experiment_id,
            "/tmp/whitepaper.pdf",
            "pdf",
            "whitepaper.pdf",
            sha,
            "ingested",
            "2026-03-16T10:00:00+00:00",
            json.dumps({"quality_state": "clean"}),
        ),
    )
    conn.execute(
        "INSERT INTO documents(id, experiment_id, path, kind, title, sha256, status, created_at, metadata_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            processing_id,
            experiment_id,
            "/tmp/whitepaper-copy.pdf",
            "pdf",
            "whitepaper-copy.pdf",
            sha,
            "processing",
            "2026-03-16T11:00:00+00:00",
            json.dumps({"quality_state": "degraded"}),
        ),
    )
    conn.execute(
        "INSERT INTO document_chunks(id, experiment_id, document_id, chunk_index, page_number, text, metadata_json, created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        ("chunk-a", experiment_id, ingested_id, 1000, 1, "alpha text", "{}", now),
    )
    conn.execute("INSERT INTO chunk_fts(chunk_id, title, text) VALUES(?, ?, ?)", ("chunk-a", "whitepaper.pdf", "alpha text"))
    conn.execute(
        "INSERT INTO document_chunks(id, experiment_id, document_id, chunk_index, page_number, text, metadata_json, created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        ("chunk-b", experiment_id, processing_id, 2000, 2, "beta text", "{}", now),
    )
    conn.execute("INSERT INTO chunk_fts(chunk_id, title, text) VALUES(?, ?, ?)", ("chunk-b", "whitepaper-copy.pdf", "beta text"))
    conn.commit()
    conn.close()

    store = GraphStore(db_path)
    rows = store._fetchall(
        "SELECT id, status FROM documents WHERE experiment_id = ? AND sha256 = ? ORDER BY id",
        (experiment_id, sha),
    )
    assert len(rows) == 1
    assert rows[0]["id"] == ingested_id
    assert rows[0]["status"] == "ingested"
    migrated_document = store.get_document(ingested_id)
    migrated_metadata = json.loads(migrated_document["metadata_json"])
    assert migrated_metadata["quality_state"] == "legacy_unscored"
    assert "legacy_unscored_pdf" in migrated_metadata["quality_flags"]
    assert store.document_chunk_count(ingested_id) == 2
    orphaned = store._fetchone("SELECT chunk_id FROM chunk_fts WHERE chunk_id = 'chunk-b'")
    assert orphaned is None
    with pytest.raises(sqlite3.IntegrityError):
        with store.transaction() as migrated:
            migrated.execute(
                "INSERT INTO documents(id, experiment_id, path, kind, title, sha256, status, created_at, metadata_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "doc-duplicate",
                    experiment_id,
                    "/tmp/whitepaper-third.pdf",
                    "pdf",
                    "whitepaper-third.pdf",
                    sha,
                    "processing",
                    now,
                    "{}",
                ),
            )
