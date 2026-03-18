from __future__ import annotations

import json
from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any

from ..ontology_projection import memode_members_are_behavioral
from ..semantic_relations import MEMODE_MEMBERSHIP_EDGE_TYPE
from .clustering import build_cluster_summaries
from .contracts import ASSEMBLY_RENDER_MODES, MEMODE_SUPPORT_EDGE_ALLOWLIST


def _edge_identity(edge: dict[str, Any]) -> str:
    explicit = edge.get("id")
    if explicit:
        return str(explicit)
    return f"{edge.get('source', '')}::{edge.get('target', '')}::{edge.get('type', '')}"


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _connected_support_graph(member_ids: list[str], support_edges: list[dict[str, Any]]) -> bool:
    if len(member_ids) < 2 or not support_edges:
        return False
    adjacency: dict[str, set[str]] = {member_id: set() for member_id in member_ids}
    for edge in support_edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source in adjacency and target in adjacency:
            adjacency[source].add(target)
            adjacency[target].add(source)
    start = next((member_id for member_id in member_ids if adjacency.get(member_id)), None)
    if start is None:
        return False
    visited: set[str] = set()
    queue = [start]
    while queue:
        node_id = queue.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        queue.extend(sorted(adjacency.get(node_id, set()) - visited))
    return len(visited) == len(member_ids)


def _edge_audit_payload(edge: dict[str, Any], node_lookup: dict[str, dict[str, Any]], *, relation_class: str, overlapping_memode_ids: list[str] | None = None) -> dict[str, Any]:
    source = node_lookup.get(str(edge.get("source") or ""), {})
    target = node_lookup.get(str(edge.get("target") or ""), {})
    return {
        "id": str(edge.get("id") or ""),
        "identity": _edge_identity(edge),
        "source": str(edge.get("source") or ""),
        "target": str(edge.get("target") or ""),
        "type": str(edge.get("type") or ""),
        "weight": float(edge.get("weight", 0.0) or 0.0),
        "evidence_label": str(edge.get("evidence_label") or ""),
        "assertion_origin": str(edge.get("assertion_origin") or edge.get("provenance", {}).get("assertion_origin", "")),
        "operator_label": str(edge.get("operator_label") or ""),
        "confidence": float(edge.get("confidence", 0.0) or 0.0),
        "source_label": str(source.get("label") or source.get("id") or edge.get("source") or ""),
        "target_label": str(target.get("label") or target.get("id") or edge.get("target") or ""),
        "source_domain": str(source.get("domain") or ""),
        "target_domain": str(target.get("domain") or ""),
        "relation_class": relation_class,
        "overlapping_memode_ids": list(overlapping_memode_ids or []),
    }


def build_memode_audit_plane(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    assemblies: list[dict[str, Any]],
) -> dict[str, Any]:
    node_lookup = {node["id"]: node for node in nodes}
    meme_lookup = {node["id"]: node for node in nodes if node.get("kind") == "meme"}
    meme_edges = [
        deepcopy(edge)
        for edge in edges
        if edge.get("source") in meme_lookup and edge.get("target") in meme_lookup
    ]
    relation_edges = [
        deepcopy(edge)
        for edge in edges
        if edge.get("type") not in {"MATERIALIZES_AS_MEMODE", MEMODE_MEMBERSHIP_EDGE_TYPE}
    ]
    edge_lookup = {_edge_identity(edge): edge for edge in meme_edges}
    materialized_support_edge_ids: set[str] = set()
    memode_rows: list[dict[str, Any]] = []
    meme_memberships: dict[str, list[str]] = defaultdict(list)

    for assembly in assemblies:
        member_ids = _dedupe_preserve_order(
            list(assembly.get("member_order") or []) + list(assembly.get("member_meme_ids") or [])
        )
        member_ids = [member_id for member_id in member_ids if member_id in meme_lookup]
        member_set = set(member_ids)
        declared_support_edge_ids = _dedupe_preserve_order([str(edge_id) for edge_id in assembly.get("supporting_edge_ids") or []])
        member_edges = [
            edge
            for edge in meme_edges
            if str(edge.get("source") or "") in member_set and str(edge.get("target") or "") in member_set
        ]
        incident_member_edges = [
            edge
            for edge in relation_edges
            if (
                str(edge.get("source") or "") in member_set
                or str(edge.get("target") or "") in member_set
            )
        ]
        candidate_support_edges = [
            edge
            for edge in member_edges
            if str(edge.get("type") or "") in MEMODE_SUPPORT_EDGE_ALLOWLIST
        ]
        declared_support_edges = [
            deepcopy(edge_lookup[edge_id])
            for edge_id in declared_support_edge_ids
            if edge_id in edge_lookup
            and str(edge_lookup[edge_id].get("source") or "") in member_set
            and str(edge_lookup[edge_id].get("target") or "") in member_set
        ]
        support_edge_keys = {_edge_identity(edge) for edge in candidate_support_edges}
        materialized_support_edge_ids.update(support_edge_keys)
        supported_member_ids = {
            str(edge.get("source") or "")
            for edge in candidate_support_edges
        } | {
            str(edge.get("target") or "")
            for edge in candidate_support_edges
        }
        unsupported_member_ids = [member_id for member_id in member_ids if member_id not in supported_member_ids]
        informational_edges = [
            edge
            for edge in incident_member_edges
            if _edge_identity(edge) not in support_edge_keys
        ]
        knowledge_informational_edges = [
            edge
            for edge in informational_edges
            if node_lookup.get(str(edge.get("source") or ""), {}).get("domain") == "knowledge"
            and node_lookup.get(str(edge.get("target") or ""), {}).get("domain") == "knowledge"
        ]
        passes = (
            len(member_ids) >= 2
            and bool(candidate_support_edges)
            and not unsupported_member_ids
            and _connected_support_graph(member_ids, candidate_support_edges)
        )
        for member_id in member_ids:
            meme_memberships[member_id].append(str(assembly.get("id") or ""))
        memode_rows.append(
            {
                "id": str(assembly.get("id") or ""),
                "label": str(assembly.get("label") or ""),
                "summary": str(assembly.get("summary") or ""),
                "domain": str(assembly.get("domain") or ""),
                "evidence_label": str(assembly.get("evidence_label") or ""),
                "operator_label": str(assembly.get("operator_label") or ""),
                "confidence": float(assembly.get("confidence", 0.0) or 0.0),
                "created_at": assembly.get("created_at"),
                "updated_at": assembly.get("updated_at"),
                "member_meme_ids": member_ids,
                "member_memes": [
                    {
                        "id": member_id,
                        "label": str(meme_lookup[member_id].get("label") or member_id),
                        "domain": str(meme_lookup[member_id].get("domain") or ""),
                        "evidence_label": str(meme_lookup[member_id].get("evidence_label") or ""),
                        "recent_active_set_presence": int(meme_lookup[member_id].get("recent_active_set_presence", 0) or 0),
                        "usage_count": int(meme_lookup[member_id].get("usage_count", 0) or 0),
                        "feedback_count": int(meme_lookup[member_id].get("feedback_count", 0) or 0),
                    }
                    for member_id in member_ids
                ],
                "declared_support_edge_ids": declared_support_edge_ids,
                "declared_support_edges": [
                    _edge_audit_payload(edge, node_lookup, relation_class="declared_support")
                    for edge in declared_support_edges
                ],
                "support_edge_ids": sorted(support_edge_keys),
                "support_edges": [
                    _edge_audit_payload(edge, node_lookup, relation_class="materialized_support", overlapping_memode_ids=[str(assembly.get("id") or "")])
                    for edge in sorted(candidate_support_edges, key=lambda item: (_edge_identity(item), str(item.get("type") or "")))
                ],
                "informational_edge_ids": sorted(_edge_identity(edge) for edge in informational_edges),
                "informational_edges": [
                    _edge_audit_payload(
                        edge,
                        node_lookup,
                        relation_class="knowledge_informational"
                        if edge in knowledge_informational_edges
                        else "member_informational",
                        overlapping_memode_ids=[str(assembly.get("id") or "")],
                    )
                    for edge in sorted(informational_edges, key=lambda item: (_edge_identity(item), str(item.get("type") or "")))
                ],
                "admissibility": {
                    "minimum_members": len(member_ids) >= 2,
                    "support_edges_present": bool(candidate_support_edges),
                    "all_members_supported": not unsupported_member_ids,
                    "connected_support_graph": _connected_support_graph(member_ids, candidate_support_edges),
                    "passes": passes,
                    "unsupported_member_ids": unsupported_member_ids,
                },
            }
        )

    informational_relations: list[dict[str, Any]] = []
    for edge in relation_edges:
        identity = _edge_identity(edge)
        if identity in materialized_support_edge_ids:
            continue
        source_id = str(edge.get("source") or "")
        target_id = str(edge.get("target") or "")
        overlapping_memodes = sorted(
            set(meme_memberships.get(source_id, [])) & set(meme_memberships.get(target_id, []))
        )
        source_node = node_lookup.get(source_id, {})
        target_node = node_lookup.get(target_id, {})
        if source_node.get("kind") == "meme" and target_node.get("kind") == "meme" and str(edge.get("type") or "") in MEMODE_SUPPORT_EDGE_ALLOWLIST:
            relation_class = "unmaterialized_support_candidate"
        elif source_node.get("domain") == "knowledge" and target_node.get("domain") == "knowledge":
            relation_class = "knowledge_informational"
        elif source_node.get("kind") == "information" or target_node.get("kind") == "information":
            relation_class = "member_informational"
        else:
            relation_class = "non_memetic_relation"
        informational_relations.append(
            _edge_audit_payload(
                edge,
                node_lookup,
                relation_class=relation_class,
                overlapping_memode_ids=overlapping_memodes,
            )
        )

    admissible_count = sum(1 for row in memode_rows if row["admissibility"]["passes"])
    knowledge_informational_count = sum(1 for row in informational_relations if row["relation_class"] == "knowledge_informational")
    unmaterialized_support_count = sum(1 for row in informational_relations if row["relation_class"] == "unmaterialized_support_candidate")
    return {
        "summary": {
            "memodes": len(memode_rows),
            "admissible_memodes": admissible_count,
            "flagged_memodes": len(memode_rows) - admissible_count,
            "materialized_support_edges": len(materialized_support_edge_ids),
            "informational_relations": len(informational_relations),
            "knowledge_informational_relations": knowledge_informational_count,
            "unmaterialized_support_candidates": unmaterialized_support_count,
        },
        "memodes": sorted(memode_rows, key=lambda item: item["id"]),
        "informational_relations": sorted(
            informational_relations,
            key=lambda item: (
                item["relation_class"],
                item["source_label"],
                item["target_label"],
                item["type"],
                item["identity"],
            ),
        ),
    }


def build_graph_planes(
    *,
    snapshot: dict[str, Any],
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    measurement_events: list[dict[str, Any]],
    semantic_coord_lookup: dict[str, dict[str, float]],
) -> dict[str, Any]:
    node_lookup = {node["id"]: node for node in nodes}
    semantic_nodes = []
    assemblies = []
    runtime_nodes = []
    projected_node_lookup = {node["id"]: node for node in nodes}
    for node in nodes:
        if node.get("kind") == "meme":
            semantic = deepcopy(node)
            semantic["render_coords"] = {"force": semantic_coord_lookup.get(node["id"], {"x": 0.0, "y": 0.0})}
            semantic_nodes.append(semantic)
        elif node.get("kind") == "memode":
            if not bool(node.get("projectable_in_assemblies", False)):
                runtime_nodes.append(deepcopy(node))
                continue
            metadata = json.loads(node.get("metadata_json") or "{}") if node.get("metadata_json") else {}
            member_ids = list(node.get("member_ids") or metadata.get("member_ids") or [])
            if not memode_members_are_behavioral(member_ids, projected_node_lookup):
                runtime_nodes.append(deepcopy(node))
                continue
            assemblies.append(
                {
                    "id": node["id"],
                    "label": node.get("label", ""),
                    "summary": node.get("summary", ""),
                    "domain": node.get("domain", ""),
                    "member_meme_ids": member_ids,
                    "supporting_edge_ids": list(node.get("supporting_edge_ids") or metadata.get("supporting_edge_ids") or []),
                    "member_order": list(node.get("member_order") or metadata.get("member_order") or []),
                    "invariance_summary": str(node.get("invariance_summary") or metadata.get("invariance_summary") or node.get("summary", "")),
                    "occurrence_examples": list(node.get("occurrence_examples") or metadata.get("occurrence_examples") or []),
                    "evidence_label": str(node.get("evidence_label") or metadata.get("evidence_label") or "AUTO_DERIVED"),
                    "operator_label": str(node.get("operator_label") or metadata.get("operator_label") or ""),
                    "confidence": float(node.get("confidence", metadata.get("confidence", 0.0)) or 0.0),
                    "created_at": node.get("created_at"),
                    "updated_at": node.get("updated_at", node.get("created_at")),
                    "render_mode_default": ASSEMBLY_RENDER_MODES[0],
                    "measurement_history": deepcopy(node.get("measurement_history") or []),
                }
            )
        else:
            runtime_nodes.append(deepcopy(node))

    semantic_edges = []
    assembly_nodes = [
        deepcopy(node)
        for node in nodes
        if node.get("kind") in {"meme", "information"}
        or (node.get("kind") == "memode" and bool(node.get("projectable_in_assemblies", False)))
    ]
    assembly_node_ids = {node["id"] for node in assembly_nodes}
    assembly_edges = []
    runtime_edges = []
    semantic_edge_ids: set[str] = set()
    for edge in edges:
        source = node_lookup.get(edge["source"])
        target = node_lookup.get(edge["target"])
        if source and target and source.get("id") in assembly_node_ids and target.get("id") in assembly_node_ids:
            assembly_edges.append(deepcopy(edge))
        if source and target and source.get("kind") == "meme" and target.get("kind") == "meme" and edge.get("type") in MEMODE_SUPPORT_EDGE_ALLOWLIST:
            semantic_edges.append(deepcopy(edge))
            if edge.get("id"):
                semantic_edge_ids.add(str(edge["id"]))
        elif source and target and source.get("id") in assembly_node_ids and target.get("id") in assembly_node_ids:
            continue
        elif edge.get("type") not in {"MATERIALIZES_AS_MEMODE", MEMODE_MEMBERSHIP_EDGE_TYPE}:
            runtime_edges.append(deepcopy(edge))

    cluster_summaries, cluster_lookup = build_cluster_summaries(
        semantic_nodes=semantic_nodes,
        semantic_edges=semantic_edges,
        coord_lookup=semantic_coord_lookup,
        measurement_events=measurement_events,
    )
    for node in semantic_nodes:
        cluster = cluster_lookup.get(node["id"], {})
        node["cluster_signature"] = cluster.get("cluster_signature", "")
        node["cluster_label"] = cluster.get("display_label", "")
    active_set_slices = []
    latest_by_session: dict[str, dict[str, Any]] = {}
    for turn in sorted(snapshot.get("turns", []), key=lambda item: (item.get("session_id", ""), item.get("turn_index", 0))):
        active_items = json.loads(turn.get("active_set_json") or "[]")
        slice_payload = {
            "turn_id": turn["id"],
            "session_id": turn["session_id"],
            "turn_index": int(turn.get("turn_index", 0) or 0),
            "created_at": turn.get("created_at"),
            "node_ids": [item.get("node_id") for item in active_items if item.get("node_id")],
            "meme_ids": [item.get("node_id") for item in active_items if item.get("node_kind") == "meme" and item.get("node_id")],
            "memode_ids": [item.get("node_id") for item in active_items if item.get("node_kind") == "memode" and item.get("node_id")],
            "domain_mix": dict(sorted(Counter(str(item.get("domain", "unknown")) for item in active_items).items())),
            "size": len(active_items),
        }
        active_set_slices.append(slice_payload)
        latest_by_session[turn["session_id"]] = slice_payload
    return {
        "semantic_nodes": sorted(semantic_nodes, key=lambda item: item["id"]),
        "semantic_edges": sorted(semantic_edges, key=lambda item: (item["source"], item["target"], item.get("type", ""), item.get("id", ""))),
        "assembly_nodes": sorted(assembly_nodes, key=lambda item: (item.get("kind", ""), item["id"])),
        "assembly_edges": sorted(assembly_edges, key=lambda item: (item["source"], item["target"], item.get("type", ""), item.get("id", ""))),
        "runtime_nodes": sorted(runtime_nodes, key=lambda item: (item.get("kind", ""), item["id"])),
        "runtime_edges": sorted(runtime_edges, key=lambda item: (item["source"], item["target"], item.get("type", ""), item.get("id", ""))),
        "assemblies": sorted(assemblies, key=lambda item: item["id"]),
        "memode_audit": build_memode_audit_plane(nodes=nodes, edges=edges, assemblies=assemblies),
        "cluster_summaries": cluster_summaries,
        "cluster_lookup": cluster_lookup,
        "active_set_slices": active_set_slices,
        "latest_active_by_session": latest_by_session,
        "semantic_edge_ids": semantic_edge_ids,
    }
