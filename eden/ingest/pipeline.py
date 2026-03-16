from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..logging import RuntimeLog
from ..utils import safe_excerpt, sentence_chunks, sha256_file, top_phrases
from .extractors import iter_extract_document


@dataclass(slots=True)
class IngestResult:
    document_id: str
    chunk_count: int
    meme_count: int
    memode_count: int
    status: str
    notes: list[str]


class IngestService:
    def __init__(self, store, runtime_log: RuntimeLog) -> None:
        self.store = store
        self.runtime_log = runtime_log

    def _domain_for_source(self, source_kind: str, path: Path) -> str:
        if source_kind in {"constitution", "feedback"}:
            return "behavior"
        if path.name.lower().startswith("eden_whitepaper"):
            return "behavior"
        return "knowledge"

    def ingest_path(
        self,
        *,
        experiment_id: str,
        path: Path,
        source_kind: str = "document",
        briefing: str | None = None,
    ) -> IngestResult:
        path = path.expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        domain = self._domain_for_source(source_kind, path)
        briefing_text = (briefing or "").strip()
        digest = sha256_file(path)
        existing_doc = self.store.get_document_by_sha(experiment_id, digest)
        if existing_doc is not None:
            existing_chunk_count = self.store.document_chunk_count(existing_doc["id"])
            if existing_doc.get("status") == "ingested" and existing_chunk_count > 0:
                return IngestResult(
                    document_id=existing_doc["id"],
                    chunk_count=existing_chunk_count,
                    meme_count=0,
                    memode_count=0,
                    status="ingested",
                    notes=["existing ingest reused"],
                )
        doc = self.store.upsert_document(
            experiment_id=experiment_id,
            path=path,
            kind=path.suffix.lower().lstrip("."),
            title=path.name,
            status="processing",
            metadata={
                "source_kind": source_kind,
                "source_path": str(path),
                "briefing": briefing_text,
                "briefing_excerpt": safe_excerpt(briefing_text, limit=240) if briefing_text else "",
            },
        )
        notes: list[str] = []
        self.runtime_log.emit("INFO", "ingest_start", "Started document ingest.", experiment_id=experiment_id, path=str(path))
        self.store.record_trace_event(
            experiment_id=experiment_id,
            session_id=None,
            turn_id=None,
            event_type="INGEST",
            level="INFO",
            message=f"Started ingest for {path.name}",
            payload={"path": str(path)},
        )

        meme_count = 0
        memode_count = 0
        page_like_units = 0
        try:
            for page in iter_extract_document(path):
                page_like_units += 1
                parser = str(page["parser"])
                page_number = page["page_number"]
                text = str(page["text"]).strip()
                if not text:
                    continue
                for idx, chunk in enumerate(sentence_chunks(text, max_chars=1000) or [text]):
                    chunk_id = self.store.add_document_chunk(
                        experiment_id=experiment_id,
                        document_id=doc["id"],
                        chunk_index=(page_number or 0) * 1000 + idx,
                        text=chunk,
                        page_number=page_number if isinstance(page_number, int) else None,
                        metadata={"parser": parser, "page_number": page_number},
                        title=path.name,
                    )
                    phrase_candidates = top_phrases(chunk, limit=6)
                    member_ids: list[str] = []
                    for phrase, score in phrase_candidates:
                        meme = self.store.upsert_meme(
                            experiment_id=experiment_id,
                            label=phrase,
                            text=chunk,
                            domain=domain,
                            source_kind=source_kind,
                            scope="global",
                            evidence_inc=score,
                            metadata={
                                "document_id": doc["id"],
                                "chunk_id": chunk_id,
                                "source_path": str(path),
                                "page_number": page_number,
                                "title": path.name,
                            },
                        )
                        member_ids.append(meme["id"])
                        meme_count += 1
                        self.store.add_edge(
                            experiment_id=experiment_id,
                            src_kind="document",
                            src_id=doc["id"],
                            dst_kind="meme",
                            dst_id=meme["id"],
                            edge_type="DERIVED_FROM",
                            provenance={"chunk_id": chunk_id, "page_number": page_number},
                        )
                    for idx, left in enumerate(member_ids):
                        for right in member_ids[idx + 1 :]:
                            self.store.add_edge(
                                experiment_id=experiment_id,
                                src_kind="meme",
                                src_id=left,
                                dst_kind="meme",
                                dst_id=right,
                                edge_type="CO_OCCURS_WITH",
                                provenance={"document_id": doc["id"], "chunk_id": chunk_id},
                            )
                    if len(member_ids) >= 2:
                        label = " / ".join(self.store.get_meme(member_id)["label"] for member_id in member_ids[:3])
                        memode = self.store.upsert_memode(
                            experiment_id=experiment_id,
                            label=label,
                            member_ids=member_ids[: min(4, len(member_ids))],
                            summary=safe_excerpt(chunk, limit=320),
                            domain=domain,
                            metadata={"document_id": doc["id"], "chunk_id": chunk_id, "title": path.name},
                        )
                        memode_count += 1
                        self.store.add_edge(
                            experiment_id=experiment_id,
                            src_kind="document",
                            src_id=doc["id"],
                            dst_kind="memode",
                            dst_id=memode["id"],
                            edge_type="MATERIALIZES_AS_MEMODE",
                            provenance={"chunk_id": chunk_id},
                        )
                        for member_id in member_ids[: min(4, len(member_ids))]:
                            self.store.add_edge(
                                experiment_id=experiment_id,
                                src_kind="memode",
                                src_id=memode["id"],
                                dst_kind="meme",
                                dst_id=member_id,
                                edge_type="MATERIALIZES_AS_MEMODE",
                                provenance={"document_id": doc["id"], "chunk_id": chunk_id},
                            )
                notes.append(f"page={page_number or '-'} parser={parser}")
        except Exception as exc:
            self.store.upsert_document(
                experiment_id=experiment_id,
                path=path,
                kind=path.suffix.lower().lstrip("."),
                title=path.name,
                status="failed",
                metadata={
                    "source_kind": source_kind,
                    "source_path": str(path),
                    "briefing": briefing_text,
                    "briefing_excerpt": safe_excerpt(briefing_text, limit=240) if briefing_text else "",
                    "page_like_units": page_like_units,
                    "processed_pages": page_like_units,
                    "notes": notes[:20],
                    "error": str(exc),
                },
            )
            self.runtime_log.emit(
                "ERROR",
                "ingest_failed",
                "Document ingest failed.",
                experiment_id=experiment_id,
                path=str(path),
                processed_pages=page_like_units,
                error=str(exc),
            )
            self.store.record_trace_event(
                experiment_id=experiment_id,
                session_id=None,
                turn_id=None,
                event_type="INGEST",
                level="ERROR",
                message=f"Failed ingest for {path.name}",
                payload={
                    "document_id": doc["id"],
                    "path": str(path),
                    "processed_pages": page_like_units,
                    "error": str(exc),
                },
            )
            raise

        updated_doc = self.store.upsert_document(
            experiment_id=experiment_id,
            path=path,
            kind=path.suffix.lower().lstrip("."),
            title=path.name,
            status="ingested",
            metadata={
                "source_kind": source_kind,
                "source_path": str(path),
                "page_like_units": page_like_units,
                "notes": notes[:20],
                "briefing": briefing_text,
                "briefing_excerpt": safe_excerpt(briefing_text, limit=240) if briefing_text else "",
            },
        )
        self.runtime_log.emit(
            "INFO",
            "ingest_complete",
            "Completed document ingest.",
            experiment_id=experiment_id,
            path=str(path),
            chunk_count=page_like_units,
            meme_count=meme_count,
            memode_count=memode_count,
        )
        self.store.record_trace_event(
            experiment_id=experiment_id,
            session_id=None,
            turn_id=None,
            event_type="INGEST",
            level="INFO",
            message=f"Completed ingest for {path.name}",
                payload={
                    "document_id": updated_doc["id"],
                    "page_like_units": page_like_units,
                    "meme_count": meme_count,
                    "memode_count": memode_count,
                },
            )
        return IngestResult(
            document_id=updated_doc["id"],
            chunk_count=page_like_units,
            meme_count=meme_count,
            memode_count=memode_count,
            status="ingested",
            notes=notes,
        )

    def ingest_many(self, *, experiment_id: str, paths: list[Path], source_kind: str = "document") -> list[IngestResult]:
        results = []
        for path in paths:
            results.append(self.ingest_path(experiment_id=experiment_id, path=path, source_kind=source_kind))
        return results
