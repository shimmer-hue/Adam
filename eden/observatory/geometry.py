from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

import networkx as nx
import numpy as np


def compute_coordinate_sets(
    graph: nx.Graph,
    *,
    node_order: list[str] | None = None,
) -> dict[str, dict[str, dict[str, float]]]:
    nodes = list(graph.nodes())
    if not nodes:
        return {name: {} for name in ("force", "spectral", "pca", "circular_candidate", "temporal")}
    force = nx.spring_layout(graph, seed=42, iterations=80) if graph.number_of_edges() else nx.circular_layout(graph)
    spectral = _spectral_coords(graph, nodes)
    pca = _pca_coords(graph, nodes)
    circular = _circular_candidate_coords(nodes, spectral)
    temporal = _temporal_coords(nodes, node_order or nodes)
    return {
        "force": _coord_map(nodes, force),
        "spectral": _coord_map(nodes, spectral),
        "pca": _coord_map(nodes, pca),
        "circular_candidate": _coord_map(nodes, circular),
        "temporal": temporal,
    }


def compute_geometry_metrics(
    graph: nx.Graph,
    directed_graph: nx.DiGraph | None = None,
    *,
    coords: dict[str, dict[str, dict[str, float]]] | None = None,
    node_order: list[str] | None = None,
) -> dict[str, Any]:
    nodes = list(graph.nodes())
    if not nodes:
        return {
            "counts": {"nodes": 0, "edges": 0},
            "metrics": {},
            "communities": [],
            "projection_quality": {},
        }
    degree_values = np.array([graph.degree(node) for node in nodes], dtype=float)
    cycle_basis = nx.cycle_basis(graph)
    cycle_nodes = {node for cycle in cycle_basis for node in cycle}
    n = graph.number_of_nodes()
    m = graph.number_of_edges()
    clustering_mean = float(np.mean(list(nx.clustering(graph).values()))) if n else 0.0
    transitivity = float(nx.transitivity(graph) if n >= 3 else 0.0)
    triangle_density = float(sum(nx.triangles(graph).values()) / 3 / max(1, n))
    communities = list(nx.community.greedy_modularity_communities(graph)) if n >= 2 and m else [set(nodes)]
    modularity = float(nx.community.modularity(graph, communities)) if len(communities) > 1 and m else 0.0
    coords = coords or compute_coordinate_sets(graph, node_order=node_order)
    adjacency = nx.to_numpy_array(graph, nodelist=nodes, weight="weight", dtype=float)
    laplacian = np.diag(adjacency.sum(axis=1)) - adjacency
    adj_eigs = np.sort(np.linalg.eigvalsh(adjacency))[::-1]
    lap_eigs = np.sort(np.linalg.eigvalsh(laplacian))
    pca_summary = _pca_summary(adjacency)
    mirror = _mirror_symmetry(coords.get("pca", {}))
    chirality = _chirality_proxy(directed_graph or nx.DiGraph(graph), coords)
    translation = _translation_symmetry_proxy(adjacency, node_order=nodes if node_order is None else node_order, graph_nodes=nodes)
    return {
        "counts": {"nodes": n, "edges": m},
        "metrics": {
            "circularity": _metric(
                "OBSERVED",
                _ringness(graph, cycle_nodes),
                "cycle-basis ringness proxy",
                sample_size=n,
            ),
            "radiality": _metric(
                "OBSERVED",
                _radiality(graph, degree_values),
                "hub-and-spoke proxy from center dominance and leaf fraction",
                sample_size=n,
            ),
            "linearity": _metric(
                "OBSERVED",
                _linearity(graph, degree_values, cycle_nodes),
                "path-likeness proxy from endpoint structure and acyclicity",
                sample_size=n,
            ),
            "community_structure": _metric(
                "OBSERVED",
                modularity,
                "greedy modularity community score",
                sample_size=len(communities),
            ),
            "triadic_closure": _metric(
                "OBSERVED",
                (transitivity + clustering_mean + min(1.0, triangle_density)) / 3,
                "mean of transitivity, clustering, and triangle density",
                sample_size=n,
            ),
            "mirror_symmetry": _metric(
                "DERIVED",
                mirror,
                "reflection-match proxy on PCA coordinates",
                sample_size=n,
            ),
            "chirality": _metric(
                "DERIVED",
                chirality,
                "signed-area imbalance on directed temporal motifs",
                sample_size=max(0, (directed_graph or nx.DiGraph(graph)).number_of_edges()),
            ),
            "translation_symmetry": _metric(
                "DERIVED",
                translation["score"],
                translation["method"],
                sample_size=translation["sample_size"],
            ),
        },
        "communities": [
            {"community_id": index, "size": len(group), "members": sorted(group)}
            for index, group in enumerate(sorted(communities, key=len, reverse=True))
        ],
        "projection_quality": {
            "pca_explained_variance_top2": pca_summary["explained_variance_top2"],
            "adjacency_spectral_radius": float(adj_eigs[0]) if len(adj_eigs) else 0.0,
            "laplacian_algebraic_connectivity": float(lap_eigs[1]) if len(lap_eigs) > 1 else 0.0,
            "laplacian_eigengap": float(lap_eigs[2] - lap_eigs[1]) if len(lap_eigs) > 2 else 0.0,
            "adjacency_top_eigengap": float(adj_eigs[0] - adj_eigs[1]) if len(adj_eigs) > 1 else float(adj_eigs[0]) if len(adj_eigs) else 0.0,
        },
    }


def compute_ablation_report(
    graph: nx.Graph,
    directed_graph: nx.DiGraph,
    *,
    edge_types: dict[tuple[str, str], str],
    node_order: list[str] | None = None,
    drop_community: list[str] | None = None,
) -> list[dict[str, Any]]:
    base_coords = compute_coordinate_sets(graph, node_order=node_order)
    base = compute_geometry_metrics(graph, directed_graph, coords=base_coords, node_order=node_order)
    reports: list[dict[str, Any]] = []
    variants: list[tuple[str, nx.Graph, nx.DiGraph, str]] = []
    filtered = nx.Graph()
    filtered.add_nodes_from(graph.nodes(data=True))
    filtered_d = nx.DiGraph()
    filtered_d.add_nodes_from(directed_graph.nodes(data=True))
    for source, target, data in graph.edges(data=True):
        if edge_types.get((source, target)) == "CO_OCCURS_WITH" or edge_types.get((target, source)) == "CO_OCCURS_WITH":
            continue
        filtered.add_edge(source, target, **data)
    for source, target, data in directed_graph.edges(data=True):
        if edge_types.get((source, target)) == "CO_OCCURS_WITH":
            continue
        filtered_d.add_edge(source, target, **data)
    variants.append(("mask_co_occurs", filtered, filtered_d, "Removed direct CO_OCCURS_WITH edges."))
    if drop_community:
        pruned = graph.copy()
        pruned.remove_nodes_from(drop_community)
        pruned_d = directed_graph.copy()
        pruned_d.remove_nodes_from(drop_community)
        variants.append(("drop_dominant_cluster", pruned, pruned_d, "Removed the dominant detected community."))
    for name, variant, variant_d, detail in variants:
        coords = compute_coordinate_sets(variant, node_order=node_order)
        metrics = compute_geometry_metrics(variant, variant_d, coords=coords, node_order=node_order)
        reports.append(
            {
                "ablation": name,
                "detail": detail,
                "before": _metric_scores(base),
                "after": _metric_scores(metrics),
                "persistence": _persistence(base, metrics),
            }
        )
    return reports


def compute_selection_geometry(
    graph: nx.Graph,
    directed_graph: nx.DiGraph,
    *,
    selected_node_ids: list[str],
    radius: int = 1,
    node_order: list[str] | None = None,
) -> dict[str, Any]:
    selected = [node_id for node_id in selected_node_ids if node_id in graph]
    if not selected:
        return {
            "selected_node_ids": [],
            "neighborhood_node_ids": [],
            "radius": radius,
            "metrics": {
                "counts": {"nodes": 0, "edges": 0},
                "metrics": {},
                "communities": [],
                "projection_quality": {},
            },
        }
    neighborhood = set(selected)
    frontier = set(selected)
    for _ in range(max(0, radius)):
        expanded: set[str] = set()
        for node_id in frontier:
            expanded.update(graph.neighbors(node_id))
        frontier = expanded - neighborhood
        neighborhood.update(expanded)
    ordered_ids = _ordered_subset(node_order or list(graph.nodes()), neighborhood)
    subgraph = graph.subgraph(ordered_ids).copy()
    directed_subgraph = directed_graph.subgraph(ordered_ids).copy()
    coords = compute_coordinate_sets(subgraph, node_order=ordered_ids)
    metrics = compute_geometry_metrics(subgraph, directed_subgraph, coords=coords, node_order=ordered_ids)
    return {
        "selected_node_ids": selected,
        "neighborhood_node_ids": ordered_ids,
        "radius": radius,
        "metrics": metrics,
    }


def metric_deltas(before: dict[str, Any], after: dict[str, Any]) -> dict[str, float]:
    before_scores = _metric_scores(before)
    after_scores = _metric_scores(after)
    keys = sorted(set(before_scores) | set(after_scores))
    return {
        key: round(float(after_scores.get(key, 0.0) - before_scores.get(key, 0.0)), 4)
        for key in keys
    }


def _metric_scores(report: dict[str, Any]) -> dict[str, float]:
    return {name: float(metric["score"]) for name, metric in report["metrics"].items()}


def _persistence(before: dict[str, Any], after: dict[str, Any]) -> float:
    before_scores = _metric_scores(before)
    after_scores = _metric_scores(after)
    if not before_scores:
        return 0.0
    deltas = [abs(before_scores[name] - after_scores.get(name, 0.0)) for name in before_scores]
    return float(max(0.0, 1.0 - np.mean(deltas)))


def _metric(label: str, score: float, method: str, *, sample_size: int) -> dict[str, Any]:
    return {
        "label": label,
        "score": round(float(max(0.0, min(1.0, score))), 4),
        "method": method,
        "sample_size": sample_size,
    }


def _ordered_subset(node_order: list[str], selected_ids: set[str]) -> list[str]:
    ordered = [node_id for node_id in node_order if node_id in selected_ids]
    if ordered:
        return ordered
    return sorted(selected_ids)


def _coord_map(nodes: list[str], coords: dict[str, Any]) -> dict[str, dict[str, float]]:
    payload: dict[str, dict[str, float]] = {}
    for node in nodes:
        point = coords[node]
        payload[node] = {"x": float(point[0]), "y": float(point[1])}
    return payload


def _spectral_coords(graph: nx.Graph, nodes: list[str]) -> dict[str, np.ndarray]:
    if len(nodes) == 1:
        return {nodes[0]: np.array([0.0, 0.0])}
    adjacency = nx.to_numpy_array(graph, nodelist=nodes, weight="weight", dtype=float)
    laplacian = np.diag(adjacency.sum(axis=1)) - adjacency
    eigvals, eigvecs = np.linalg.eigh(laplacian)
    basis = eigvecs[:, 1:3] if eigvecs.shape[1] >= 3 else np.column_stack((eigvecs[:, 1], np.zeros(len(nodes))))
    return {node: basis[index] for index, node in enumerate(nodes)}


def _pca_coords(graph: nx.Graph, nodes: list[str]) -> dict[str, np.ndarray]:
    if len(nodes) == 1:
        return {nodes[0]: np.array([0.0, 0.0])}
    adjacency = nx.to_numpy_array(graph, nodelist=nodes, weight="weight", dtype=float)
    centered = adjacency - adjacency.mean(axis=0, keepdims=True)
    u, s, _ = np.linalg.svd(centered, full_matrices=False)
    if centered.shape[1] == 1:
        coords = np.column_stack((u[:, 0] * s[0], np.zeros(len(nodes))))
    else:
        coords = u[:, :2] * s[:2]
    return {node: coords[index] for index, node in enumerate(nodes)}


def _circular_candidate_coords(nodes: list[str], spectral: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    ordered = sorted(nodes, key=lambda node: math.atan2(float(spectral[node][1]), float(spectral[node][0])) if node in spectral else 0.0)
    total = max(1, len(ordered))
    coords: dict[str, np.ndarray] = {}
    for index, node in enumerate(ordered):
        angle = (2 * math.pi * index) / total
        coords[node] = np.array([math.cos(angle), math.sin(angle)])
    return coords


def _temporal_coords(nodes: list[str], node_order: list[str]) -> dict[str, dict[str, float]]:
    positions = {node: index for index, node in enumerate(node_order) if node in nodes}
    span = max(1, len(positions) - 1)
    return {
        node: {
            "x": float(positions.get(node, index) / span),
            "y": float((index % 5) / 4 if len(nodes) > 1 else 0.0),
        }
        for index, node in enumerate(nodes)
    }


def _ringness(graph: nx.Graph, cycle_nodes: set[str]) -> float:
    n = graph.number_of_nodes()
    if n < 3:
        return 0.0
    m = graph.number_of_edges()
    degree_vals = np.array([graph.degree(node) for node in graph.nodes()], dtype=float)
    degree_two_fraction = float(np.mean(degree_vals == 2))
    cycle_fraction = len(cycle_nodes) / n
    edge_balance = max(0.0, 1.0 - abs(m - n) / max(1, n))
    return float((max(1e-6, degree_two_fraction * cycle_fraction * edge_balance)) ** (1 / 3))


def _radiality(graph: nx.Graph, degree_values: np.ndarray) -> float:
    n = graph.number_of_nodes()
    if n < 3:
        return 0.0
    sorted_deg = sorted((int(value) for value in degree_values), reverse=True)
    max_degree = sorted_deg[0]
    second = sorted_deg[1] if len(sorted_deg) > 1 else 0
    center_dominance = max_degree / max(1, n - 1)
    leaf_fraction = float(np.mean(degree_values == 1))
    hub_gap = max(0.0, (max_degree - second) / max(1, n - 1))
    clustering_penalty = 1.0 - float(nx.transitivity(graph) if n >= 3 else 0.0)
    return float(max(0.0, min(1.0, (0.45 * center_dominance) + (0.35 * leaf_fraction) + (0.2 * hub_gap))) * clustering_penalty)


def _linearity(graph: nx.Graph, degree_values: np.ndarray, cycle_nodes: set[str]) -> float:
    n = graph.number_of_nodes()
    if n < 2:
        return 0.0
    endpoint_count = int(np.sum(degree_values == 1))
    endpoint_score = 1.0 if endpoint_count == 2 else max(0.0, 1.0 - abs(endpoint_count - 2) / max(2, n))
    path_fraction = float(np.mean(degree_values <= 2))
    acyclic_score = 1.0 - (len(cycle_nodes) / n)
    return float((max(1e-6, endpoint_score * path_fraction * max(acyclic_score, 1e-6))) ** (1 / 3))


def _pca_summary(matrix: np.ndarray) -> dict[str, float]:
    if matrix.size == 0:
        return {"explained_variance_top2": 0.0}
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    _, s, _ = np.linalg.svd(centered, full_matrices=False)
    power = np.square(s)
    total = float(power.sum()) or 1.0
    return {"explained_variance_top2": float(power[:2].sum() / total)}


def _mirror_symmetry(coords: dict[str, dict[str, float]]) -> float:
    if len(coords) < 3:
        return 0.0
    points = np.array([[point["x"], point["y"]] for point in coords.values()], dtype=float)
    spread = float(np.max(np.linalg.norm(points - points.mean(axis=0), axis=1))) or 1.0
    reflected_sets = [points * np.array([-1.0, 1.0]), points * np.array([1.0, -1.0])]
    scores = []
    for reflected in reflected_sets:
        distances = []
        for point in reflected:
            distances.append(float(np.min(np.linalg.norm(points - point, axis=1))))
        scores.append(max(0.0, 1.0 - (np.mean(distances) / spread)))
    return float(max(scores))


def _chirality_proxy(directed_graph: nx.DiGraph, coord_sets: dict[str, dict[str, dict[str, float]]]) -> float:
    candidate_sets = [
        coord_sets.get("circular_candidate", {}),
        coord_sets.get("spectral", {}),
        coord_sets.get("pca", {}),
    ]
    if directed_graph.number_of_edges() < 3:
        return 0.0
    scores: list[float] = []
    for coords in candidate_sets:
        if len(coords) < 3:
            continue
        signed_areas: list[float] = []
        for source in directed_graph.nodes():
            for middle in directed_graph.successors(source):
                for target in directed_graph.successors(middle):
                    if len({source, middle, target}) < 3:
                        continue
                    if source not in coords or middle not in coords or target not in coords:
                        continue
                    a = np.array([coords[source]["x"], coords[source]["y"]], dtype=float)
                    b = np.array([coords[middle]["x"], coords[middle]["y"]], dtype=float)
                    c = np.array([coords[target]["x"], coords[target]["y"]], dtype=float)
                    signed_areas.append(float((((b[0] - a[0]) * (c[1] - a[1])) - ((b[1] - a[1]) * (c[0] - a[0]))) / 2))
        if not signed_areas:
            continue
        mean_abs = float(np.mean(np.abs(signed_areas))) or 1.0
        scores.append(float(abs(np.mean(signed_areas)) / mean_abs))
    return max(scores) if scores else 0.0


def _translation_symmetry_proxy(adjacency: np.ndarray, *, node_order: list[str], graph_nodes: list[str]) -> dict[str, Any]:
    if adjacency.shape[0] < 4 or len(node_order) != len(graph_nodes):
        return {"score": 0.0, "method": "ordered-offset proxy unavailable for this slice", "sample_size": 0}
    by_offset: dict[int, list[float]] = defaultdict(list)
    for i in range(adjacency.shape[0]):
        for j in range(adjacency.shape[1]):
            if i == j:
                continue
            by_offset[abs(i - j)].append(float(adjacency[i, j]))
    means = {offset: float(np.mean(values)) for offset, values in by_offset.items()}
    residuals: list[float] = []
    values: list[float] = []
    for offset, bucket in by_offset.items():
        for value in bucket:
            values.append(value)
            residuals.append(value - means[offset])
    total_var = float(np.var(values))
    residual_var = float(np.var(residuals))
    if total_var == 0.0:
        return {"score": 0.0, "method": "ordered-offset proxy had zero variance", "sample_size": len(values)}
    return {
        "score": max(0.0, min(1.0, 1.0 - (residual_var / total_var))),
        "method": "variance explained by edge-distance offset bins",
        "sample_size": len(values),
    }
