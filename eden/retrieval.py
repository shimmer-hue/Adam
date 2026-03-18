from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any

import networkx as nx

from .config import RuntimeSettings
from .ontology_projection import project_node_ontology
from .regard import explicit_feedback_relevance, regard_breakdown, selection_score
from .utils import cosine_similarity, now_utc, safe_excerpt


@dataclass(slots=True)
class CandidateScore:
    node_kind: str
    display_kind: str
    node_id: str
    label: str
    domain: str
    scope: str
    source_kind: str
    entity_type: str
    speech_act_mode: str
    semantic_similarity: float
    activation: float
    regard: float
    session_bias: float
    explicit_feedback: float
    scope_penalty: float
    membrane_penalty: float
    selection: float
    breakdown: dict[str, float]
    text: str
    provenance: str
    document_id: str | None = None
    document_title: str | None = None
    page_number: int | None = None
    evidence_excerpt: str = ""
    quality_score: float | None = None
    quality_flags: list[str] = field(default_factory=list)


class RetrievalService:
    def __init__(self, store) -> None:
        self.store = store

    def _document_group_key(self, item: CandidateScore) -> str | None:
        if item.document_id:
            return item.document_id
        if item.provenance.lower().endswith((".pdf", ".txt", ".md", ".markdown", ".csv")):
            return item.provenance
        return None

    def _format_candidate_block(self, item: CandidateScore) -> str:
        lines = [
            f"[{item.domain.upper()}:{item.display_kind}] {item.label}",
            f"selection={item.selection:.3f} regard={item.regard:.3f} activation={item.activation:.3f}",
            f"provenance={item.provenance}",
        ]
        if item.page_number is not None:
            lines.append(f"page={item.page_number}")
        if item.quality_score is not None:
            lines.append(f"quality={item.quality_score:.3f}")
        if item.quality_flags:
            lines.append(f"quality_flags={','.join(item.quality_flags[:4])}")
        lines.append(safe_excerpt(item.evidence_excerpt or item.text, limit=280))
        return "\n".join(lines)

    def _format_document_group(self, items: list[CandidateScore]) -> str:
        lead = items[0]
        lines = [
            f"[{lead.domain.upper()}:document] {lead.document_title or lead.provenance}",
            f"provenance={lead.provenance}",
            f"evidence_items={len(items)}",
        ]
        for item in items:
            summary = f"- [{item.display_kind}] {item.label} selection={item.selection:.3f}"
            if item.page_number is not None:
                summary += f" page={item.page_number}"
            if item.quality_score is not None:
                summary += f" quality={item.quality_score:.3f}"
            lines.append(summary)
            if item.quality_flags:
                lines.append(f"  quality_flags={','.join(item.quality_flags[:4])}")
            lines.append(f"  excerpt={safe_excerpt(item.evidence_excerpt or item.text, limit=180)}")
        return "\n".join(lines)

    def build_graph_metrics(self, experiment_id: str) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
        memes = self.store.list_memes(experiment_id)
        memodes = self.store.list_memodes(experiment_id)
        edges = self.store.list_edges(experiment_id)
        graph = nx.Graph()
        for meme in memes:
            graph.add_node(meme["id"], kind="meme")
        memode_member_counts: dict[str, int] = {meme["id"]: 0 for meme in memes}
        for memode in memodes:
            metadata = json.loads(memode["metadata_json"] or "{}")
            members = metadata.get("member_ids", [])
            unique_members = [member for member in dict.fromkeys(members) if graph.has_node(member)]
            for member in unique_members:
                memode_member_counts[member] = memode_member_counts.get(member, 0) + 1
            for idx, left in enumerate(unique_members):
                for right in unique_members[idx + 1 :]:
                    if left != right:
                        graph.add_edge(left, right, weight=graph.get_edge_data(left, right, {}).get("weight", 0.0) + 1.0)
        for edge in edges:
            if edge["src_kind"] == "meme" and edge["dst_kind"] == "meme":
                graph.add_edge(
                    edge["src_id"],
                    edge["dst_id"],
                    weight=graph.get_edge_data(edge["src_id"], edge["dst_id"], {}).get("weight", 0.0) + float(edge["weight"]),
                )
        clustering = nx.clustering(graph)
        triangles = nx.triangles(graph)
        component_sizes: dict[str, int] = {}
        for component in nx.connected_components(graph):
            size = len(component)
            for node_id in component:
                component_sizes[node_id] = size
        metrics: dict[str, dict[str, float]] = {}
        for node_id in graph.nodes:
            metrics[node_id] = {
                "degree": float(graph.degree(node_id)),
                "clustering": float(clustering.get(node_id, 0.0)),
                "triangles": float(triangles.get(node_id, 0.0)),
                "component_size": float(component_sizes.get(node_id, 1)),
                "memode_count": float(memode_member_counts.get(node_id, 0)),
            }
        isolated_count = sum(1 for node_id in graph.nodes if graph.degree(node_id) == 0)
        dyad_components = sum(1 for component in nx.connected_components(graph) if len(component) == 2)
        memode_coverage = 0.0
        if memes:
            covered = sum(1 for meme in memes if memode_member_counts.get(meme["id"], 0) > 0)
            memode_coverage = covered / len(memes)
        global_metrics = {
            "node_count": float(graph.number_of_nodes()),
            "edge_count": float(graph.number_of_edges()),
            "isolated_count": float(isolated_count),
            "dyad_ratio": float(dyad_components / max(1, graph.number_of_nodes())),
            "triadic_closure": float(nx.transitivity(graph) if graph.number_of_nodes() >= 3 else 0.0),
            "memode_coverage": float(memode_coverage),
        }
        return metrics, global_metrics

    def _expand_node(self, node: dict[str, Any]) -> dict[str, Any]:
        expanded = dict(node)
        metadata_json = expanded.get("metadata_json")
        if isinstance(metadata_json, str):
            try:
                expanded["metadata"] = json.loads(metadata_json)
            except json.JSONDecodeError:
                expanded["metadata"] = {}
        else:
            expanded["metadata"] = metadata_json or {}
        return expanded

    def _fallback_candidates(self, experiment_id: str) -> list[dict[str, Any]]:
        memes = [self._expand_node(node) for node in self.store.list_memes(experiment_id)[:50]]
        memodes = [self._expand_node(node) for node in self.store.list_memodes(experiment_id)[:30]]
        for node in memes:
            node["_kind"] = "meme"
        for node in memodes:
            node["_kind"] = "memode"
        return memes + memodes

    def retrieve(
        self,
        *,
        experiment_id: str,
        session_id: str,
        query: str,
        settings: RuntimeSettings,
    ) -> dict[str, Any]:
        graph_metrics, health_metrics = self.build_graph_metrics(experiment_id)
        raw_memes = [self._expand_node(node) for node in self.store.search_memes(experiment_id, query, limit=settings.retrieval_depth)]
        raw_memodes = [self._expand_node(node) for node in self.store.search_memodes(experiment_id, query, limit=settings.retrieval_depth)]
        for node in raw_memes:
            node["_kind"] = "meme"
        for node in raw_memodes:
            node["_kind"] = "memode"
        raw_candidates = raw_memes + raw_memodes
        if not raw_candidates:
            raw_candidates = self._fallback_candidates(experiment_id)

        now = now_utc()
        scored: list[CandidateScore] = []
        for node in raw_candidates:
            node_kind = node["_kind"]
            content = node.get("text") or node.get("summary") or node.get("label") or ""
            semantic = cosine_similarity(query, f"{node.get('label', '')} {content}")
            metrics = graph_metrics.get(node["id"], {"degree": 0.0, "clustering": 0.0, "triangles": 0.0, "component_size": 1.0, "memode_count": 0.0})
            regard = regard_breakdown(node, metrics, now, settings.regard_weights)
            metadata = node.get("metadata", {})
            projection = project_node_ontology(
                storage_kind=node_kind,
                domain=str(node.get("domain", "knowledge")),
                label=str(node.get("label", "untitled")),
                metadata=metadata,
            )
            source_session = metadata.get("session_id")
            session_bias = 1.0 if source_session and source_session == session_id else 0.0
            scope = node.get("scope", "global")
            scope_penalty = 0.0
            if scope.startswith("session:") and scope != f"session:{session_id}":
                scope_penalty = 1.0
            membrane_penalty = min(1.5, float(node.get("membrane_conflicts", 0.0)) / 2.0)
            feedback_value = explicit_feedback_relevance(node)
            selection = selection_score(
                semantic_similarity=semantic,
                activation_value=regard.activation,
                regard_value=regard.total,
                session_bias=session_bias,
                explicit_feedback_value=feedback_value,
                scope_penalty=scope_penalty,
                membrane_penalty=membrane_penalty,
                weights=settings.selection_weights,
            )
            document_id = str(metadata["document_id"]) if metadata.get("document_id") else None
            document_title = str(metadata["title"]) if metadata.get("title") else None
            if document_id and metadata.get("source_path"):
                provenance = metadata.get("source_path")
            else:
                provenance = metadata.get("title") or metadata.get("source_path") or metadata.get("origin") or node.get("source_kind", "unknown")
            page_number_raw = metadata.get("page_number")
            try:
                page_number = int(page_number_raw) if page_number_raw is not None else None
            except (TypeError, ValueError):
                page_number = None
            quality_score_raw = metadata.get("quality_score")
            try:
                quality_score = float(quality_score_raw) if quality_score_raw is not None else None
            except (TypeError, ValueError):
                quality_score = None
            quality_flags = [str(flag) for flag in metadata.get("quality_flags", []) if str(flag).strip()]
            scored.append(
                CandidateScore(
                    node_kind=node_kind,
                    display_kind=str(projection["kind"]),
                    node_id=node["id"],
                    label=node.get("label", "untitled"),
                    domain=node.get("domain", "knowledge"),
                    scope=scope,
                    source_kind=node.get("source_kind", "unknown"),
                    entity_type=str(projection["entity_type"]),
                    speech_act_mode=str(projection["speech_act_mode"]),
                    semantic_similarity=semantic,
                    activation=regard.activation,
                    regard=regard.total,
                    session_bias=session_bias,
                    explicit_feedback=feedback_value,
                    scope_penalty=scope_penalty,
                    membrane_penalty=membrane_penalty,
                    selection=selection,
                    breakdown={
                        "reward": regard.reward,
                        "evidence": regard.evidence,
                        "coherence": regard.coherence,
                        "persistence": regard.persistence,
                        "decay": regard.decay,
                        "isolation_penalty": regard.isolation_penalty,
                        "risk": regard.risk,
                        "bm25_score": float(node.get("bm25_score", 0.0)),
                    },
                    text=content,
                    provenance=str(provenance),
                    document_id=document_id,
                    document_title=document_title,
                    page_number=page_number,
                    evidence_excerpt=safe_excerpt(content, limit=220),
                    quality_score=quality_score,
                    quality_flags=quality_flags,
                )
            )

        scored.sort(key=lambda item: item.selection, reverse=True)
        behavior = [item for item in scored if item.domain == "behavior"]
        knowledge = [item for item in scored if item.domain != "behavior"]
        selected: list[CandidateScore] = []
        behavior_target = max(2, math.ceil(settings.max_context_items / 3))
        selected.extend(behavior[:behavior_target])
        remaining_slots = settings.max_context_items - len(selected)
        selected.extend(knowledge[:remaining_slots])
        if len(selected) < settings.max_context_items:
            selected.extend(scored[len(selected) : settings.max_context_items])
        deduped: list[CandidateScore] = []
        seen_ids: set[str] = set()
        for item in selected:
            if item.node_id in seen_ids:
                continue
            seen_ids.add(item.node_id)
            deduped.append(item)

        items = [asdict(item) for item in deduped]
        prompt_context_parts: list[str] = []
        document_groups: dict[str, list[CandidateScore]] = {}
        prompt_entries: list[tuple[str, CandidateScore | str]] = []
        seen_document_groups: set[str] = set()
        for item in deduped:
            document_group_key = self._document_group_key(item)
            if document_group_key is None:
                prompt_entries.append(("item", item))
                continue
            document_groups.setdefault(document_group_key, []).append(item)
            if document_group_key in seen_document_groups:
                continue
            seen_document_groups.add(document_group_key)
            prompt_entries.append(("document", document_group_key))

        for kind, value in prompt_entries:
            if kind == "item":
                prompt_context_parts.append(self._format_candidate_block(value))  # type: ignore[arg-type]
                continue
            prompt_context_parts.append(self._format_document_group(document_groups[str(value)]))

        trace = []
        for candidate in scored[: min(10, len(scored))]:
            trace.append(
                {
                    "label": candidate.label,
                    "kind": candidate.node_kind,
                    "display_kind": candidate.display_kind,
                    "domain": candidate.domain,
                    "entity_type": candidate.entity_type,
                    "selection": round(candidate.selection, 4),
                    "semantic_similarity": round(candidate.semantic_similarity, 4),
                    "activation": round(candidate.activation, 4),
                    "regard": round(candidate.regard, 4),
                    "session_bias": round(candidate.session_bias, 4),
                    "explicit_feedback": round(candidate.explicit_feedback, 4),
                    "scope_penalty": round(candidate.scope_penalty, 4),
                    "membrane_penalty": round(candidate.membrane_penalty, 4),
                    "breakdown": candidate.breakdown,
                    "provenance": candidate.provenance,
                }
            )

        return {
            "items": items,
            "prompt_context": "\n\n".join(prompt_context_parts),
            "trace": trace,
            "health_metrics": health_metrics,
        }
