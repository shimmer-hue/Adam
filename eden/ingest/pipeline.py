from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..logging import RuntimeLog
from ..semantic_relations import MEMODE_MEMBERSHIP_EDGE_TYPE, extract_semantic_candidates
from ..utils import safe_excerpt, sentence_chunks, sha256_file, slugify
from .extractors import iter_extract_document


@dataclass(slots=True)
class IngestResult:
    document_id: str
    chunk_count: int
    meme_count: int
    memode_count: int
    status: str
    notes: list[str]
    parser_strategy: str
    quality_score: float
    quality_state: str
    quality_flags: list[str]
    selected_parser_counts: dict[str, int]


def _parser_strategy_for_path(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return "page_scored_pdf_extract_v1"
    return "direct_extract_v1"


def _quality_state_for(score: float, flags: set[str]) -> str:
    severe = {"replacement_glyphs", "fragmented_lines", "sparse_text"}
    if score < 0.28:
        return "failed"
    if score < 0.72 or any(flag in severe for flag in flags):
        return "degraded"
    return "clean"


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
        parser_strategy = _parser_strategy_for_path(path)
        if existing_doc is not None:
            existing_chunk_count = self.store.document_chunk_count(existing_doc["id"])
            if existing_doc.get("status") == "ingested" and existing_chunk_count > 0:
                existing_metadata = json.loads(existing_doc.get("metadata_json") or "{}")
                merged_metadata = {
                    **existing_metadata,
                    "source_kind": source_kind,
                    "source_path": str(path),
                    "briefing": briefing_text,
                    "briefing_excerpt": safe_excerpt(briefing_text, limit=240) if briefing_text else "",
                    "parser_strategy": existing_metadata.get("parser_strategy", parser_strategy),
                }
                canonical_doc = self.store.upsert_document(
                    experiment_id=experiment_id,
                    path=path,
                    kind=path.suffix.lower().lstrip("."),
                    title=path.name,
                    status="ingested",
                    metadata=merged_metadata,
                )
                self.runtime_log.emit(
                    "INFO",
                    "ingest_reused",
                    "Reused canonical document ingest.",
                    experiment_id=experiment_id,
                    path=str(path),
                    document_id=canonical_doc["id"],
                )
                self.store.record_trace_event(
                    experiment_id=experiment_id,
                    session_id=None,
                    turn_id=None,
                    event_type="INGEST",
                    level="INFO",
                    message=f"Reused ingest for {path.name}",
                    payload={
                        "document_id": canonical_doc["id"],
                        "path": str(path),
                        "quality_score": float(existing_metadata.get("quality_score", 1.0)),
                        "quality_state": str(existing_metadata.get("quality_state", "clean")),
                        "quality_flags": list(existing_metadata.get("quality_flags", [])),
                        "selected_parser_counts": dict(existing_metadata.get("selected_parser_counts", {})),
                    },
                )
                return IngestResult(
                    document_id=canonical_doc["id"],
                    chunk_count=existing_chunk_count,
                    meme_count=0,
                    memode_count=0,
                    status="ingested",
                    notes=["existing ingest reused"],
                    parser_strategy=str(existing_metadata.get("parser_strategy", parser_strategy)),
                    quality_score=float(existing_metadata.get("quality_score", 1.0)),
                    quality_state=str(existing_metadata.get("quality_state", "clean")),
                    quality_flags=list(existing_metadata.get("quality_flags", [])),
                    selected_parser_counts=dict(existing_metadata.get("selected_parser_counts", {})),
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
                "parser_strategy": parser_strategy,
            },
        )
        if existing_doc is not None:
            self.store.reset_document_chunks(doc["id"])
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
        quality_scores: list[float] = []
        quality_flags: set[str] = set()
        selected_parser_counts: dict[str, int] = {}
        aggregate_quality_score = 0.0
        aggregate_quality_state = "failed"
        try:
            for page in iter_extract_document(path):
                page_like_units += 1
                unit_index = page_like_units - 1
                parser = str(page["parser"])
                page_number = page["page_number"]
                text = str(page["text"]).strip()
                page_quality_score = float(page.get("quality_score", 1.0))
                page_quality_flags = list(page.get("quality_flags", []))
                quality_scores.append(page_quality_score)
                quality_flags.update(page_quality_flags)
                selected_parser_counts[parser] = selected_parser_counts.get(parser, 0) + 1
                if not text:
                    continue
                chunk_slot = (page_number - 1) if isinstance(page_number, int) and page_number > 0 else unit_index
                for idx, chunk in enumerate(sentence_chunks(text, max_chars=1000) or [text]):
                    chunk_id = self.store.add_document_chunk(
                        experiment_id=experiment_id,
                        document_id=doc["id"],
                        chunk_index=chunk_slot * 1000 + idx,
                        text=chunk,
                        page_number=page_number if isinstance(page_number, int) else None,
                        metadata={
                            "parser": parser,
                            "page_number": page_number,
                            "quality_score": page_quality_score,
                            "quality_flags": page_quality_flags,
                        },
                        title=path.name,
                    )
                    semantic_candidates = extract_semantic_candidates(chunk, limit=6)
                    member_ids: list[str] = []
                    member_ids_by_label: dict[str, str] = {}
                    for candidate in semantic_candidates["meme_candidates"]:
                        meme = self.store.upsert_meme(
                            experiment_id=experiment_id,
                            label=str(candidate["label"]),
                            text=chunk,
                            domain=domain,
                            source_kind=source_kind,
                            scope="global",
                            evidence_inc=float(candidate["score"]),
                            metadata={
                                "document_id": doc["id"],
                                "chunk_id": chunk_id,
                                "source_path": str(path),
                                "page_number": page_number,
                                "title": path.name,
                                "parser": parser,
                                "quality_score": page_quality_score,
                                "quality_flags": page_quality_flags,
                            },
                        )
                        member_id = str(meme["id"])
                        member_ids.append(member_id)
                        member_ids_by_label.setdefault(slugify(str(meme.get("label") or candidate["label"])), member_id)
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
                    for relation in semantic_candidates["relation_candidates"]:
                        source_id = member_ids_by_label.get(slugify(relation["source_label"]))
                        target_id = member_ids_by_label.get(slugify(relation["target_label"]))
                        if not source_id or not target_id or source_id == target_id:
                            continue
                        self.store.add_edge(
                            experiment_id=experiment_id,
                            src_kind="meme",
                            src_id=source_id,
                            dst_kind="meme",
                            dst_id=target_id,
                            edge_type=relation["edge_type"],
                            provenance={
                                "document_id": doc["id"],
                                "chunk_id": chunk_id,
                                "page_number": page_number,
                                "assertion_origin": "auto_derived",
                                "evidence_label": "AUTO_DERIVED",
                                "confidence": relation["confidence"],
                                "relation_rule": relation["rule"],
                                "sentence_excerpt": relation["sentence_excerpt"],
                            },
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
                                provenance={
                                    "document_id": doc["id"],
                                    "chunk_id": chunk_id,
                                    "assertion_origin": "auto_derived",
                                    "evidence_label": "AUTO_DERIVED",
                                    "confidence": 1.0,
                                },
                            )
                    if len(member_ids) >= 2:
                        label = " / ".join(self.store.get_meme(member_id)["label"] for member_id in member_ids[:3])
                        memode = self.store.upsert_memode(
                            experiment_id=experiment_id,
                            label=label,
                            member_ids=member_ids[: min(4, len(member_ids))],
                            summary=safe_excerpt(chunk, limit=320),
                            domain=domain,
                            metadata={
                                "document_id": doc["id"],
                                "chunk_id": chunk_id,
                                "title": path.name,
                                "source_path": str(path),
                                "page_number": page_number,
                                "parser": parser,
                                "quality_score": page_quality_score,
                                "quality_flags": page_quality_flags,
                            },
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
                                edge_type=MEMODE_MEMBERSHIP_EDGE_TYPE,
                                provenance={"document_id": doc["id"], "chunk_id": chunk_id},
                            )
                notes.append(f"page={page_number or '-'} parser={parser} quality={page_quality_score:.3f}")
            if len(selected_parser_counts) > 1:
                quality_flags.add("mixed_parser_selection")
            aggregate_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            aggregate_quality_state = _quality_state_for(aggregate_quality_score, quality_flags)
            if aggregate_quality_state == "failed":
                raise RuntimeError(
                    f"Document extraction unusable after normalization/scoring (quality_score={aggregate_quality_score:.3f})"
                )
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
                    "parser_strategy": parser_strategy,
                    "quality_score": round(aggregate_quality_score, 4),
                    "quality_state": aggregate_quality_state,
                    "quality_flags": sorted(quality_flags),
                    "selected_parser_counts": dict(sorted(selected_parser_counts.items())),
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
                    "parser_strategy": parser_strategy,
                    "quality_score": round(aggregate_quality_score, 4),
                    "quality_state": aggregate_quality_state,
                    "quality_flags": sorted(quality_flags),
                    "selected_parser_counts": dict(sorted(selected_parser_counts.items())),
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
                "parser_strategy": parser_strategy,
                "quality_score": round(aggregate_quality_score, 4),
                "quality_state": aggregate_quality_state,
                "quality_flags": sorted(quality_flags),
                "selected_parser_counts": dict(sorted(selected_parser_counts.items())),
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
            quality_score=round(aggregate_quality_score, 4),
            quality_state=aggregate_quality_state,
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
                    "parser_strategy": parser_strategy,
                    "quality_score": round(aggregate_quality_score, 4),
                    "quality_state": aggregate_quality_state,
                    "quality_flags": sorted(quality_flags),
                    "selected_parser_counts": dict(sorted(selected_parser_counts.items())),
                },
            )
        return IngestResult(
            document_id=updated_doc["id"],
            chunk_count=page_like_units,
            meme_count=meme_count,
            memode_count=memode_count,
            status="ingested",
            notes=notes,
            parser_strategy=parser_strategy,
            quality_score=round(aggregate_quality_score, 4),
            quality_state=aggregate_quality_state,
            quality_flags=sorted(quality_flags),
            selected_parser_counts=dict(sorted(selected_parser_counts.items())),
        )

    def ingest_many(self, *, experiment_id: str, paths: list[Path], source_kind: str = "document") -> list[IngestResult]:
        results = []
        for path in paths:
            results.append(self.ingest_path(experiment_id=experiment_id, path=path, source_kind=source_kind))
        return results
