from __future__ import annotations

import networkx as nx

from eden.observatory.geometry import (
    compute_ablation_report,
    compute_coordinate_sets,
    compute_geometry_metrics,
    compute_selection_geometry,
    metric_deltas,
)


def _rename(graph):
    return nx.relabel_nodes(graph, lambda node: f"n{node}")


def test_cycle_graph_scores_high_on_circularity() -> None:
    graph = _rename(nx.cycle_graph(8))
    coords = compute_coordinate_sets(graph, node_order=list(graph.nodes()))
    metrics = compute_geometry_metrics(graph, nx.DiGraph(graph), coords=coords, node_order=list(graph.nodes()))
    assert metrics["metrics"]["circularity"]["score"] > 0.8


def test_star_graph_scores_high_on_radiality() -> None:
    graph = _rename(nx.star_graph(7))
    coords = compute_coordinate_sets(graph, node_order=list(graph.nodes()))
    metrics = compute_geometry_metrics(graph, nx.DiGraph(graph), coords=coords, node_order=list(graph.nodes()))
    assert metrics["metrics"]["radiality"]["score"] > 0.7


def test_line_graph_scores_high_on_linearity() -> None:
    graph = _rename(nx.path_graph(7))
    coords = compute_coordinate_sets(graph, node_order=list(graph.nodes()))
    metrics = compute_geometry_metrics(graph, nx.DiGraph(graph), coords=coords, node_order=list(graph.nodes()))
    assert metrics["metrics"]["linearity"]["score"] > 0.7


def test_cluster_graph_shows_community_structure() -> None:
    left = nx.complete_graph(5)
    right = nx.complete_graph(range(5, 10))
    graph = nx.union(left, right)
    graph.add_edge(0, 5)
    graph = _rename(graph)
    coords = compute_coordinate_sets(graph, node_order=list(graph.nodes()))
    metrics = compute_geometry_metrics(graph, nx.DiGraph(graph), coords=coords, node_order=list(graph.nodes()))
    assert metrics["metrics"]["community_structure"]["score"] > 0.2


def test_directed_cycle_has_nontrivial_chirality_and_ablation_changes_scores() -> None:
    graph = _rename(nx.cycle_graph(6))
    directed = nx.DiGraph()
    directed.add_nodes_from(graph.nodes())
    ordered_nodes = list(graph.nodes())
    for left, right in zip(ordered_nodes, ordered_nodes[1:] + ordered_nodes[:1], strict=False):
        directed.add_edge(left, right)
    coords = compute_coordinate_sets(graph, node_order=ordered_nodes)
    metrics = compute_geometry_metrics(graph, directed, coords=coords, node_order=ordered_nodes)
    assert metrics["metrics"]["chirality"]["score"] > 0.05

    edge_types = {}
    for left, right in graph.edges():
        edge_types[(left, right)] = "CO_OCCURS_WITH"
        edge_types[(right, left)] = "CO_OCCURS_WITH"
    report = compute_ablation_report(graph, directed, edge_types=edge_types, node_order=ordered_nodes)
    assert report
    assert report[0]["persistence"] < 1.0


def test_local_selection_geometry_and_edge_change_delta() -> None:
    graph = _rename(nx.path_graph(5))
    directed = nx.DiGraph(graph)
    local_before = compute_selection_geometry(graph, directed, selected_node_ids=["n1", "n2"], radius=1, node_order=list(graph.nodes()))
    graph.add_edge("n1", "n3", weight=1.0)
    directed.add_edge("n1", "n3", weight=1.0)
    local_after = compute_selection_geometry(graph, directed, selected_node_ids=["n1", "n2"], radius=1, node_order=list(graph.nodes()))
    delta = metric_deltas(local_before["metrics"], local_after["metrics"])
    assert local_before["metrics"]["counts"]["nodes"] >= 2
    assert any(abs(value) > 0 for value in delta.values())
