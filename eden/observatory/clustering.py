from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from typing import Any

import networkx as nx

from ..utils import compact_json, sha256_text, tokenize
from .contracts import (
    DETACHED_TRANSFER_STATUS,
    EXACT_TRANSFER_STATUS,
    NONE_TRANSFER_STATUS,
    OBSERVATORY_CLUSTER_ALGORITHM,
    OBSERVATORY_CLUSTER_ALGORITHM_VERSION,
    OBSERVATORY_CLUSTER_RESOLUTION,
    OBSERVATORY_CLUSTER_SEED,
    TRANSFERRED_TRANSFER_STATUS,
)

TRANSFER_THRESHOLD = 0.70
DETACHED_HINT_THRESHOLD = 0.35


def semantic_graph_hash(*, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    payload = {
        "nodes": [
            {
                "id": node["id"],
                "label": node.get("label", ""),
                "summary": node.get("summary", ""),
                "domain": node.get("domain", ""),
            }
            for node in sorted(nodes, key=lambda item: item["id"])
        ],
        "edges": [
            {
                "id": edge.get("id", ""),
                "source": min(edge["source"], edge["target"]),
                "target": max(edge["source"], edge["target"]),
                "type": edge.get("type", ""),
                "weight": round(float(edge.get("weight", 1.0)), 6),
            }
            for edge in sorted(edges, key=lambda item: (min(item["source"], item["target"]), max(item["source"], item["target"]), item.get("type", ""), item.get("id", "")))
        ],
    }
    return sha256_text(compact_json(payload))[:16]


def build_cluster_summaries(
    *,
    semantic_nodes: list[dict[str, Any]],
    semantic_edges: list[dict[str, Any]],
    coord_lookup: dict[str, dict[str, float]],
    measurement_events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    graph = nx.Graph()
    ordered_nodes = sorted(semantic_nodes, key=lambda item: item["id"])
    for node in ordered_nodes:
        graph.add_node(node["id"], **node)
    for edge in sorted(semantic_edges, key=lambda item: (min(item["source"], item["target"]), max(item["source"], item["target"]), item.get("type", ""), item.get("id", ""))):
        graph.add_edge(edge["source"], edge["target"], **edge)

    graph_hash = semantic_graph_hash(nodes=semantic_nodes, edges=semantic_edges)
    communities = _detect_communities(graph)
    node_terms = {node["id"]: _node_terms(node) for node in ordered_nodes}
    term_df = Counter()
    for terms in node_terms.values():
        for term in set(terms):
            term_df[term] += 1
    annotations = _active_cluster_annotations(measurement_events)
    cluster_lookup: dict[str, dict[str, Any]] = {}
    summaries: list[dict[str, Any]] = []
    centrality = dict(graph.degree())

    for community_index, member_ids in enumerate(communities):
        member_nodes = [graph.nodes[node_id] for node_id in member_ids]
        dominant_domain = Counter(str(node.get("domain", "unknown")) for node in member_nodes).most_common(1)[0][0]
        auto_label_terms = _label_terms(member_ids=member_ids, node_terms=node_terms, term_df=term_df, centrality=centrality)
        auto_label_short = auto_label_terms[0] if auto_label_terms else f"cluster {community_index + 1}"
        auto_label_long = ", ".join(auto_label_terms[:4]) if auto_label_terms else auto_label_short
        cluster_signature = _cluster_signature(graph_hash=graph_hash, member_ids=member_ids)
        centroid = _centroid(member_ids, coord_lookup)
        hull_points = _hull_points(member_ids, coord_lookup)
        summary = {
            "cluster_signature": cluster_signature,
            "source_graph_hash": graph_hash,
            "algorithm": OBSERVATORY_CLUSTER_ALGORITHM,
            "algorithm_version": OBSERVATORY_CLUSTER_ALGORITHM_VERSION,
            "resolution": OBSERVATORY_CLUSTER_RESOLUTION,
            "member_meme_ids": member_ids,
            "auto_label_short": auto_label_short,
            "auto_label_long": auto_label_long,
            "auto_label_terms": auto_label_terms[:8],
            "manual_label": "",
            "manual_summary": "",
            "display_label": auto_label_short,
            "centroid": centroid,
            "hull_points": hull_points,
            "domain_mix": dict(sorted(Counter(str(node.get("domain", "unknown")) for node in member_nodes).items())),
            "confidence": round(_cluster_confidence(member_ids, auto_label_terms), 4),
            "method": "deterministic_louvain_labeler",
            "top_meme_ids": sorted(member_ids, key=lambda node_id: (-centrality.get(node_id, 0), node_id))[:5],
            "transfer_status": NONE_TRANSFER_STATUS,
            "transferred_from_cluster_signature": "",
            "transfer_score": 0.0,
            "reattach_candidate": None,
        }
        _apply_annotation(summary=summary, annotations=annotations, dominant_domain=dominant_domain)
        summaries.append(summary)
        for member_id in member_ids:
            cluster_lookup[member_id] = {
                "cluster_signature": cluster_signature,
                "display_label": summary["display_label"],
                "auto_label_short": auto_label_short,
                "manual_label": summary["manual_label"],
            }
    summaries.sort(key=lambda item: (-len(item["member_meme_ids"]), item["cluster_signature"]))
    return summaries, cluster_lookup


def _detect_communities(graph: nx.Graph) -> list[list[str]]:
    if graph.number_of_nodes() == 0:
        return []
    if graph.number_of_edges() == 0:
        return [[node_id] for node_id in sorted(graph.nodes())]
    communities = nx.community.louvain_communities(
        graph,
        seed=OBSERVATORY_CLUSTER_SEED,
        resolution=OBSERVATORY_CLUSTER_RESOLUTION,
    )
    normalized = [sorted(list(community)) for community in communities]
    normalized.sort(key=lambda member_ids: (-len(member_ids), member_ids[0]))
    return normalized


def _node_terms(node: dict[str, Any]) -> list[str]:
    text = f"{node.get('label', '')} {node.get('summary', '')}"
    return [token for token in tokenize(text) if len(token) > 2]


def _label_terms(*, member_ids: list[str], node_terms: dict[str, list[str]], term_df: Counter[str], centrality: dict[str, int]) -> list[str]:
    cluster_counts: Counter[str] = Counter()
    total_docs = max(len(node_terms), 1)
    for node_id in member_ids:
        weight = max(1.0, float(centrality.get(node_id, 0) or 0))
        for term in node_terms.get(node_id, []):
            cluster_counts[term] += weight
    scored: list[tuple[float, str]] = []
    for term, freq in cluster_counts.items():
        distinctiveness = math.log((1 + total_docs) / (1 + term_df.get(term, 0))) + 1.0
        scored.append((freq * distinctiveness, term))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [term for _, term in scored[:8]]


def _cluster_signature(*, graph_hash: str, member_ids: list[str]) -> str:
    return sha256_text(f"{graph_hash}:{OBSERVATORY_CLUSTER_ALGORITHM_VERSION}:{'|'.join(member_ids)}")[:16]


def _centroid(member_ids: list[str], coord_lookup: dict[str, dict[str, float]]) -> dict[str, float]:
    coords = [coord_lookup.get(node_id, {"x": 0.0, "y": 0.0}) for node_id in member_ids]
    if not coords:
        return {"x": 0.0, "y": 0.0}
    return {
        "x": round(sum(float(item.get("x", 0.0)) for item in coords) / len(coords), 6),
        "y": round(sum(float(item.get("y", 0.0)) for item in coords) / len(coords), 6),
    }


def _hull_points(member_ids: list[str], coord_lookup: dict[str, dict[str, float]]) -> list[dict[str, float]]:
    points = sorted({(round(float(coord_lookup.get(node_id, {}).get("x", 0.0)), 6), round(float(coord_lookup.get(node_id, {}).get("y", 0.0)), 6)) for node_id in member_ids})
    if len(points) <= 2:
        return [{"x": point[0], "y": point[1]} for point in points]

    def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    return [{"x": point[0], "y": point[1]} for point in hull]


def _cluster_confidence(member_ids: list[str], auto_label_terms: list[str]) -> float:
    size_score = min(1.0, len(member_ids) / 6.0)
    label_score = min(1.0, len(auto_label_terms) / 4.0)
    return 0.45 + (0.35 * size_score) + (0.20 * label_score)


def _active_cluster_annotations(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reverted_ids = {str(item.get("reverted_from_event_id")) for item in events if item.get("reverted_from_event_id")}
    annotations: list[dict[str, Any]] = []
    for event in events:
        if str(event.get("id")) in reverted_ids:
            continue
        if event.get("action_type") != "motif_annotation":
            continue
        committed = event.get("committed_state")
        if committed is None and event.get("committed_state_json"):
            committed = json.loads(event["committed_state_json"] or "{}")
        if not isinstance(committed, dict):
            continue
        annotation = committed.get("annotation") or {}
        target = annotation.get("target") or {}
        if target.get("kind") != "cluster":
            continue
        annotations.append({
            "event_id": str(event.get("id", "")),
            "created_at": str(event.get("created_at", "")),
            **annotation,
        })
    annotations.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return annotations


def _apply_annotation(*, summary: dict[str, Any], annotations: list[dict[str, Any]], dominant_domain: str) -> None:
    exact = next((item for item in annotations if item.get("cluster_signature") == summary["cluster_signature"]), None)
    if exact is not None:
        summary["manual_label"] = exact.get("manual_label", "")
        summary["manual_summary"] = exact.get("manual_summary", "")
        summary["display_label"] = summary["manual_label"] or summary["auto_label_short"]
        summary["transfer_status"] = EXACT_TRANSFER_STATUS
        summary["transfer_score"] = 1.0
        return

    best: dict[str, Any] | None = None
    best_score = 0.0
    score_tie = False
    member_ids = set(summary["member_meme_ids"])
    for annotation in annotations:
        annotation_members = set(annotation.get("target", {}).get("member_meme_ids") or annotation.get("member_meme_ids") or [])
        if not annotation_members:
            continue
        annotation_domain = str(annotation.get("target", {}).get("dominant_domain") or annotation.get("dominant_domain") or dominant_domain)
        if annotation_domain != dominant_domain:
            continue
        score = len(member_ids & annotation_members) / max(1, len(member_ids | annotation_members))
        if score > best_score:
            best = annotation
            best_score = score
            score_tie = False
        elif score == best_score and score > 0:
            score_tie = True
    if best is None:
        return
    summary["transfer_score"] = round(best_score, 4)
    summary["transferred_from_cluster_signature"] = str(best.get("cluster_signature", ""))
    candidate = {
        "cluster_signature": str(best.get("cluster_signature", "")),
        "manual_label": str(best.get("manual_label", "")),
        "manual_summary": str(best.get("manual_summary", "")),
        "transfer_score": round(best_score, 4),
    }
    if best_score >= TRANSFER_THRESHOLD and not score_tie:
        summary["manual_label"] = candidate["manual_label"]
        summary["manual_summary"] = candidate["manual_summary"]
        summary["display_label"] = summary["manual_label"] or summary["auto_label_short"]
        summary["transfer_status"] = TRANSFERRED_TRANSFER_STATUS
        summary["reattach_candidate"] = candidate
        return
    if best_score >= DETACHED_HINT_THRESHOLD:
        summary["transfer_status"] = DETACHED_TRANSFER_STATUS
        summary["reattach_candidate"] = candidate
