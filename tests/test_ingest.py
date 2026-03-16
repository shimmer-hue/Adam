from __future__ import annotations

import pytest

from eden.utils import sha256_file


def test_ingest_supported_formats(runtime, sample_files) -> None:
    experiment = runtime.initialize_experiment("blank")
    for path in sample_files.values():
        result = runtime.ingest_document(experiment_id=experiment["id"], path=str(path))
        assert result["status"] == "ingested"
        assert result["chunk_count"] >= 1
    counts = runtime.store.graph_counts(experiment["id"])
    assert counts["documents"] == 4
    assert counts["memes"] > 6
    assert counts["memodes"] >= 1


def test_ingest_reuses_existing_document(runtime, sample_files) -> None:
    experiment = runtime.initialize_experiment("blank")
    path = sample_files["pdf"]

    first = runtime.ingest_document(experiment_id=experiment["id"], path=str(path))
    second = runtime.ingest_document(experiment_id=experiment["id"], path=str(path))

    assert second["status"] == "ingested"
    assert second["document_id"] == first["document_id"]
    assert "existing ingest reused" in second["notes"]
    assert runtime.store.document_chunk_count(first["document_id"]) == first["chunk_count"]


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
