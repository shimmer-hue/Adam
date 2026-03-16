from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np

from ..utils import now_utc, safe_excerpt, sha256_text
from ..tanakh import DEFAULT_TANAKH_REF
from .contracts import (
    ASSEMBLY_RENDER_MODES,
    BASIN_LIFT_MODES,
    GRAPH_UI_MODES,
    MEMODE_SUPPORT_EDGE_ALLOWLIST,
    OBSERVATORY_BASIN_SCHEMA_VERSION,
    OBSERVATORY_GRAPH_SCHEMA_VERSION,
)
from .frontend_assets import copy_frontend_assets
from .geometry import compute_ablation_report, compute_coordinate_sets, compute_geometry_metrics, compute_selection_geometry
from .graph_planes import build_graph_planes


NODE_TOPOLOGY_EXACT_LIMIT = 1200
LOCAL_GEOMETRY_REPORT_LIMIT = 24

OBSERVATORY_EXPORT_FORMATS = [
    "gexf",
    "graphml",
    "gdf",
    "gml",
    "graphviz_dot",
    "pajek_net",
    "netdraw_vna",
    "ucinet_dl",
    "tulip_tlp",
    "tgf",
    "nodes_csv",
    "edges_csv",
    "selection_json",
]


def _uuid_like(value: str) -> bool:
    parts = value.strip().split("-")
    if len(parts) != 5:
        return False
    lengths = [8, 4, 4, 4, 12]
    return all(len(part) == expected and all(char in "0123456789abcdefABCDEF" for char in part) for part, expected in zip(parts, lengths))


def _semantic_export_label(*candidates: Any, fallback: str, limit: int = 140) -> str:
    for candidate in candidates:
        text = str(candidate or "").strip()
        if not text or _uuid_like(text):
            continue
        return safe_excerpt(text, limit=limit)
    return fallback


OBSERVATORY_LAYOUT_FAMILIES = [
    {
        "id": "force_directed",
        "order": 1,
        "label": "1. Force-Directed Layout Algorithms",
        "description": "Nodes repel while edges pull related nodes together. This is the default exploratory family for network structure.",
        "bestFor": ["community detection visuals", "social networks", "exploratory graph interfaces"],
    },
    {
        "id": "hierarchical",
        "order": 2,
        "label": "2. Hierarchical / Layered Layouts",
        "description": "Directional structure is arranged into layers so operators can read pipelines, dependencies, or staged flow.",
        "bestFor": ["flowcharts", "DAG visualizations", "dependency graphs"],
    },
    {
        "id": "tree",
        "order": 3,
        "label": "3. Tree Layout Algorithms",
        "description": "Specialized hierarchical layouts for acyclic structures where ancestry and branching depth matter more than cluster density.",
        "bestFor": ["trees", "taxonomies", "branching provenance"],
    },
    {
        "id": "circular",
        "order": 4,
        "label": "4. Circular Layout Algorithms",
        "description": "Nodes are placed on one or more circles to expose order, groups, and dense adjacency around a ring.",
        "bestFor": ["cluster inspection", "adjacency circles", "connectome-style inspection"],
    },
    {
        "id": "spectral",
        "order": 5,
        "label": "5. Spectral Layout Algorithms",
        "description": "Graph matrices are decomposed so global structure emerges from eigenvectors, stress minimization, or embedding distance.",
        "bestFor": ["global structure", "dimensionality reduction", "coarse topology reading"],
    },
    {
        "id": "multilevel",
        "order": 6,
        "label": "6. Multilevel / Coarsening Layout Algorithms",
        "description": "Large graphs are coarsened, laid out, and expanded again so scale stays tractable without pretending every node can be optimized at once.",
        "bestFor": ["very large graphs", "performance scaling", "coarse-to-fine layout"],
    },
    {
        "id": "constraint",
        "order": 7,
        "label": "7. Constraint-Based Layout Algorithms",
        "description": "Geometric rules and optimization constraints shape the result, which is useful when readability depends on obeying specific structure.",
        "bestFor": ["diagramming", "layout constraints", "overlap control"],
    },
    {
        "id": "orthogonal",
        "order": 8,
        "label": "8. Orthogonal / Grid Layout Algorithms",
        "description": "Edges run in horizontal and vertical channels for engineering-style diagrams.",
        "bestFor": ["circuit diagrams", "UML", "box-and-arrow schematics"],
    },
    {
        "id": "planar",
        "order": 9,
        "label": "9. Planar Graph Layout Algorithms",
        "description": "These specialize in planar graphs where crossings can be avoided or heavily constrained.",
        "bestFor": ["planar graphs", "embedding studies", "crossing minimization"],
    },
    {
        "id": "geographic",
        "order": 10,
        "label": "10. Geographic / Coordinate-Anchored Layouts",
        "description": "Real coordinates or fixed anchors dominate the placement, so layout respects external geography or measured positions.",
        "bestFor": ["transport", "telecom maps", "anchored infrastructure"],
    },
    {
        "id": "community",
        "order": 11,
        "label": "11. Community / Cluster Layout Algorithms",
        "description": "Cluster structure guides placement so modularity and neighborhoods remain legible even before detailed inspection.",
        "bestFor": ["Louvain / Leiden overlays", "cluster inspection", "group-first reading"],
    },
    {
        "id": "edge_bundling",
        "order": 12,
        "label": "12. Edge Bundling Techniques",
        "description": "Not layouts by themselves, but clutter-reduction passes layered on top of an existing layout.",
        "bestFor": ["dense edges", "readability cleanup", "flow corridors"],
    },
]


OBSERVATORY_LAYOUT_DEFAULTS = {
    "coordinate_mode": "force",
    "heavy_graph_node_cap": 320,
    "forceatlas2": {
        "iterations": 160,
        "scalingRatio": 8.0,
        "gravity": 1.0,
        "strongGravityMode": False,
        "barnesHutOptimize": True,
        "barnesHutTheta": 1.2,
        "linLogMode": False,
        "outboundAttractionDistribution": False,
        "edgeWeightInfluence": 1.0,
        "adjustSizes": False,
        "preventOverlap": False,
    },
    "fruchterman_reingold": {
        "iterations": 120,
        "gravity": 0.08,
        "speed": 0.18,
        "cooling": 0.95,
        "preventOverlap": False,
    },
    "kamada_kawai": {
        "iterations": 80,
        "springLength": 1.4,
        "springStrength": 0.08,
        "cooling": 0.18,
    },
    "linlog": {
        "iterations": 140,
        "scalingRatio": 6.0,
        "gravity": 0.6,
        "edgeWeightInfluence": 1.0,
        "adjustSizes": False,
        "preventOverlap": False,
    },
    "sugiyama_layered": {
        "orientation": "top_down",
        "layerSpacing": 1.6,
        "nodeSpacing": 1.2,
    },
    "radial_tree": {
        "rootStrategy": "highest_degree",
        "ringSpacing": 1.2,
        "spread": 6.28,
        "rootNodeId": "",
    },
    "simple_circular": {
        "radius": 1.2,
        "startAngle": 0.0,
    },
    "circular_degree": {
        "radius": 1.2,
        "startAngle": 0.0,
    },
    "circular_community": {
        "clusterSpacing": 2.4,
        "intraClusterRadius": 0.45,
        "startAngle": 0.0,
    },
    "radial": {
        "rootStrategy": "highest_degree",
        "rootNodeId": "",
        "ringSpacing": 1.0,
    },
    "noverlap": {
        "maxIterations": 160,
        "margin": 4,
        "ratio": 1.2,
        "speed": 3,
        "gridSize": 20,
    },
    "fixed_coordinate": {
        "respectGeoAnchors": True,
        "fallbackToInitial": True,
    },
    "community_clusters": {
        "clusterSpacing": 2.8,
        "intraClusterRadius": 0.5,
        "orderBy": "cluster_size",
    },
}


class ObservatoryExporter:
    def __init__(self, store, retrieval_service, runtime_log, tanakh_service=None, hum_provider=None) -> None:
        self.store = store
        self.retrieval_service = retrieval_service
        self.runtime_log = runtime_log
        self.tanakh_service = tanakh_service
        self.hum_provider = hum_provider

    def export_all(self, *, experiment_id: str, session_id: str | None, out_dir: Path) -> dict[str, str]:
        out_dir.mkdir(parents=True, exist_ok=True)
        copy_frontend_assets(out_dir)
        snapshot = self.store.graph_snapshot(experiment_id)
        basin_paths, basin_payload = self.export_behavioral_basin(
            experiment_id=experiment_id,
            session_id=session_id,
            out_dir=out_dir,
            snapshot=snapshot,
        )
        graph_model = self._build_graph_model(snapshot=snapshot, session_id=session_id, basin_payload=basin_payload)
        basin_paths, basin_payload = self._enrich_basin_payload(
            experiment_id=experiment_id,
            session_id=session_id,
            out_dir=out_dir,
            basin_paths=basin_paths,
            basin_payload=basin_payload,
            graph_model=graph_model,
        )
        graph_paths, graph_payload = self.export_graph_knowledge_base(
            experiment_id=experiment_id,
            session_id=session_id,
            out_dir=out_dir,
            graph_model=graph_model,
        )
        geometry_paths = self.export_geometry_lab(
            experiment_id=experiment_id,
            session_id=session_id,
            out_dir=out_dir,
            graph_model=graph_model,
        )
        measurement_paths, measurement_payload = self.export_measurement_ledger(
            experiment_id=experiment_id,
            session_id=session_id,
            out_dir=out_dir,
            snapshot=snapshot,
        )
        tanakh_paths: dict[str, str] = {}
        tanakh_payload: dict[str, Any] | None = None
        if self.tanakh_service is not None:
            tanakh_paths, tanakh_payload = self.export_tanakh_surface(
                experiment_id=experiment_id,
                session_id=session_id,
                out_dir=out_dir,
            )
        index_paths = self.export_observatory_index(
            experiment_id=experiment_id,
            session_id=session_id,
            out_dir=out_dir,
            graph_payload=graph_payload,
            basin_payload=basin_payload,
            measurement_payload=measurement_payload,
            graph_paths=graph_paths,
            basin_paths=basin_paths,
            geometry_paths=geometry_paths,
            measurement_paths=measurement_paths,
            tanakh_paths=tanakh_paths,
            tanakh_payload=tanakh_payload,
        )
        return {**graph_paths, **basin_paths, **geometry_paths, **measurement_paths, **tanakh_paths, **index_paths}

    def export_graph_knowledge_base(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        out_dir: Path,
        graph_model: dict[str, Any],
    ) -> tuple[dict[str, str], dict[str, Any]]:
        _, health_metrics = self.retrieval_service.build_graph_metrics(experiment_id)
        export_manifest_id = sha256_text(f"graph:{experiment_id}:{session_id}:{now_utc()}")[:12]
        payload = {
            "schema_version": OBSERVATORY_GRAPH_SCHEMA_VERSION,
            "export_manifest_id": export_manifest_id,
            "generated_at": now_utc(),
            "experiment_id": experiment_id,
            "session_id": session_id,
            "health_metrics": health_metrics,
            "counts": self.store.graph_counts(experiment_id),
            "nodes": graph_model["nodes"],
            "edges": graph_model["edges"],
            "semantic_nodes": graph_model["semantic_nodes"],
            "semantic_edges": graph_model["semantic_edges"],
            "runtime_nodes": graph_model["runtime_nodes"],
            "runtime_edges": graph_model["runtime_edges"],
            "assemblies": graph_model["assemblies"],
            "cluster_summaries": graph_model["cluster_summaries"],
            "active_set_slices": graph_model["active_set_slices"],
            "source_graph_hash": graph_model["source_graph_hash"],
            "measurement_events": graph_model["measurement_events"],
            "latest_active_ids": graph_model["latest_active_ids"],
            "evidence_legend": {
                "OBSERVED": "Directly computed from graph topology or explicit recurrence counts.",
                "DERIVED": "Computed from transforms and projections.",
                "SPECULATIVE": "Visual or operator hypothesis only.",
                "OPERATOR_ASSERTED": "Manual graph assertion with provenance.",
                "OPERATOR_REFINED": "Manual refinement of an existing graph fact.",
                "AUTO_DERIVED": "Graph fact produced by EDEN-side derivation or ingest.",
            },
            "interaction_modes": ["INSPECT", "MEASURE", "EDIT", "ABLATE", "COMPARE"],
            "graph_modes": GRAPH_UI_MODES,
            "assembly_render_modes": ASSEMBLY_RENDER_MODES,
            "layout_families": OBSERVATORY_LAYOUT_FAMILIES,
            "layout_catalog": {
                "force": {
                    "kind": "exported_coordinate",
                    "label": "Force",
                    "source": "render_coords.force",
                    "mutable": False,
                },
                "spectral": {
                    "kind": "exported_coordinate",
                    "label": "Spectral",
                    "source": "derived_coords.spectral",
                    "mutable": False,
                },
                "circular_candidate": {
                    "kind": "exported_coordinate",
                    "label": "Circular Candidate",
                    "source": "derived_coords.circular_candidate",
                    "mutable": False,
                },
                "temporal": {
                    "kind": "exported_coordinate",
                    "label": "Temporal",
                    "source": "derived_coords.temporal",
                    "mutable": False,
                },
                "symmetry": {
                    "kind": "exported_coordinate",
                    "label": "Symmetry",
                    "source": "derived_coords.pca",
                    "mutable": False,
                },
                "basin_linked": {
                    "kind": "exported_coordinate",
                    "label": "Basin Linked",
                    "source": "derived_coords.basin_linked",
                    "mutable": False,
                },
                "forceatlas2": {
                    "kind": "browser_local_layout",
                    "label": "ForceAtlas2",
                    "status": "runnable",
                    "familyId": "force_directed",
                    "subgroupLabel": "Modern / scalable variants",
                    "summary": "Gephi's best-known force layout, balancing readability, scale, and cluster separation.",
                    "usedFor": "Use it as the default exploratory layout for medium and large networks where community shape matters.",
                    "bestFor": ["community detection visuals", "social networks", "exploratory graph interfaces"],
                    "worker": True,
                    "parameters": [
                        "iterations",
                        "scalingRatio",
                        "gravity",
                        "strongGravityMode",
                        "barnesHutOptimize",
                        "barnesHutTheta",
                        "linLogMode",
                        "outboundAttractionDistribution",
                        "edgeWeightInfluence",
                        "adjustSizes",
                        "preventOverlap",
                    ],
                },
                "fruchterman_reingold": {
                    "kind": "browser_local_layout",
                    "label": "Fruchterman-Reingold",
                    "status": "runnable",
                    "familyId": "force_directed",
                    "subgroupLabel": "Classic algorithms",
                    "summary": "Classic spring-electrical layout that spreads nodes evenly while pulling connected nodes together.",
                    "usedFor": "Use it when you want a readable, medium-scale exploratory view with simple spring semantics.",
                    "bestFor": ["community detection visuals", "social networks", "exploratory graph interfaces"],
                    "worker": True,
                    "parameters": ["iterations", "gravity", "speed", "cooling", "preventOverlap"],
                },
                "kamada_kawai": {
                    "kind": "browser_local_layout",
                    "label": "Kamada-Kawai",
                    "status": "runnable",
                    "familyId": "force_directed",
                    "subgroupLabel": "Classic algorithms",
                    "summary": "Stress-minimization spring layout that tries to preserve graph-theoretic distances in the drawing.",
                    "usedFor": "Use it when distance fidelity matters more than raw scale, especially for smaller graphs or path-heavy structure.",
                    "bestFor": ["distance-preserving views", "path structure", "small-to-medium graphs"],
                    "worker": True,
                    "parameters": ["iterations", "springLength", "springStrength", "cooling"],
                },
                "linlog": {
                    "kind": "browser_local_layout",
                    "label": "LinLog / r-PolyLog",
                    "status": "runnable",
                    "familyId": "force_directed",
                    "subgroupLabel": "Modern / scalable variants",
                    "summary": "A force-energy model that exaggerates separation between communities by favoring cluster structure.",
                    "usedFor": "Use it when community boundaries are more important than smooth global spacing.",
                    "bestFor": ["community detection visuals", "cluster-first reading"],
                    "worker": True,
                    "parameters": ["iterations", "scalingRatio", "gravity", "edgeWeightInfluence", "adjustSizes", "preventOverlap"],
                },
                "sugiyama_layered": {
                    "kind": "browser_local_layout",
                    "label": "Sugiyama layout",
                    "status": "runnable",
                    "familyId": "hierarchical",
                    "subgroupLabel": "Sugiyama framework family",
                    "summary": "A layered DAG-style view that assigns ranks and spaces nodes so direction reads clearly.",
                    "usedFor": "Use it for flows, dependencies, or turn-to-turn causality where vertical or horizontal stage order matters.",
                    "bestFor": ["flowcharts", "DAG visualizations", "dependency graphs"],
                    "worker": True,
                    "parameters": ["orientation", "layerSpacing", "nodeSpacing"],
                },
                "radial_tree": {
                    "kind": "browser_local_layout",
                    "label": "Radial tree layout",
                    "status": "runnable",
                    "familyId": "tree",
                    "subgroupLabel": "Common tree layouts",
                    "summary": "Tree-like breadth layers are wrapped around a root so depth expands in rings.",
                    "usedFor": "Use it when you want rooted hierarchy without consuming the full width of the canvas.",
                    "bestFor": ["acyclic hierarchies", "rooted neighborhoods", "radial ancestry"],
                    "worker": True,
                    "parameters": ["rootStrategy", "rootNodeId", "ringSpacing", "spread"],
                },
                "simple_circular": {
                    "kind": "browser_local_layout",
                    "label": "Simple circular layout",
                    "status": "runnable",
                    "familyId": "circular",
                    "subgroupLabel": "Common versions",
                    "summary": "Places all nodes on a single circle in deterministic order.",
                    "usedFor": "Use it as the baseline ring view when you want equal spacing and a fast sanity check.",
                    "bestFor": ["baseline circular views", "adjacency circles"],
                    "worker": True,
                    "parameters": ["radius", "startAngle"],
                },
                "circular_degree": {
                    "kind": "browser_local_layout",
                    "label": "Circular by degree",
                    "status": "runnable",
                    "familyId": "circular",
                    "subgroupLabel": "Common versions",
                    "summary": "Higher-degree nodes are ordered to stand out earlier around the circle.",
                    "usedFor": "Use it to inspect hubs, spokes, and role imbalance while keeping a ring-based view.",
                    "bestFor": ["hub inspection", "degree ordering"],
                    "worker": True,
                    "parameters": ["radius", "startAngle"],
                },
                "circular_community": {
                    "kind": "browser_local_layout",
                    "label": "Circular by community",
                    "status": "runnable",
                    "familyId": "circular",
                    "subgroupLabel": "Common versions",
                    "summary": "Communities occupy ring sectors so clusters remain visually grouped around the circle.",
                    "usedFor": "Use it when a ring view should still preserve cluster boundaries.",
                    "bestFor": ["cluster inspection", "adjacency circle diagrams"],
                    "worker": True,
                    "parameters": ["clusterSpacing", "intraClusterRadius", "startAngle"],
                },
                "noverlap": {
                    "kind": "browser_local_layout",
                    "label": "Noverlap",
                    "status": "runnable",
                    "familyId": "constraint",
                    "subgroupLabel": "Examples",
                    "summary": "Post-force overlap removal pass that pushes nodes apart while preserving the existing structure as much as possible.",
                    "usedFor": "Use it after another layout when the main issue is node collision rather than global structure.",
                    "bestFor": ["overlap control", "post-processing cleanup"],
                    "worker": True,
                    "parameters": ["maxIterations", "margin", "ratio", "speed", "gridSize"],
                },
                "radial": {
                    "kind": "browser_local_layout",
                    "label": "Radial",
                    "status": "runnable",
                    "familyId": "circular",
                    "subgroupLabel": "Common versions",
                    "summary": "A breadth-oriented radial layout centered on a chosen root.",
                    "usedFor": "Use it for neighborhood inspection when one root should stay central and rings should show distance.",
                    "bestFor": ["ego networks", "rooted neighborhoods"],
                    "worker": True,
                    "parameters": ["rootStrategy", "rootNodeId", "ringSpacing"],
                },
                "fixed_coordinate": {
                    "kind": "browser_local_layout",
                    "label": "Fixed coordinate layout",
                    "status": "runnable",
                    "familyId": "geographic",
                    "subgroupLabel": "Examples",
                    "summary": "Keeps provided coordinate anchors and otherwise respects the current positions.",
                    "usedFor": "Use it when positions come from geography, measurement, or an earlier authoritative export and should not be re-simulated.",
                    "bestFor": ["anchored coordinates", "fixed maps", "operator-preserved positions"],
                    "worker": True,
                    "parameters": ["respectGeoAnchors", "fallbackToInitial"],
                },
                "community_clusters": {
                    "kind": "browser_local_layout",
                    "label": "Cluster-based layout",
                    "status": "runnable",
                    "familyId": "community",
                    "subgroupLabel": "Examples",
                    "summary": "Cluster centroids are spaced apart first, then members are arranged inside each cluster.",
                    "usedFor": "Use it when group boundaries should dominate the picture before individual edge geometry.",
                    "bestFor": ["cluster inspection", "community-first reading"],
                    "worker": True,
                    "parameters": ["clusterSpacing", "intraClusterRadius", "orderBy"],
                },
            },
            "layout_defaults": OBSERVATORY_LAYOUT_DEFAULTS,
            "appearance_dimensions": {
                "node_color": ["kind", "domain", "cluster", "evidence_label", "active_set_presence", "regard_balance"],
                "node_size": ["uniform", "degree", "recent_active_set_presence", "evidence", "reward", "risk"],
                "edge_color": ["type", "evidence_label", "assertion_origin", "selection_state"],
                "edge_opacity": ["uniform", "weight", "measurement_history", "assertion_origin"],
                "label_modes": ["selection", "cluster", "importance", "all", "none"],
            },
            "filter_dimensions": {
                "node_attributes": ["session_id", "kind", "domain", "source_kind", "evidence_label", "cluster_signature", "recent_active_set_presence", "degree", "created_at"],
                "edge_attributes": ["type", "weight", "assertion_origin", "evidence_label"],
                "toggles": ["hide_isolated", "component_largest", "selection_ego"],
                "component_modes": ["all", "largest", "selection"],
                "saved_presets_local_only": True,
            },
            "statistics_capabilities": {
                "worker": True,
                "on_demand_metrics": [
                    "degree",
                    "weighted_degree",
                    "pagerank",
                    "betweenness",
                    "clustering_coefficient",
                    "components",
                    "density",
                    "reciprocity",
                    "modularity",
                    "shortest_path_sample",
                ],
                "heavy_graph_node_cap": 320,
            },
            "export_formats": OBSERVATORY_EXPORT_FORMATS,
            "live_api": {
                "preview": f"/api/experiments/{experiment_id}/preview",
                "commit": f"/api/experiments/{experiment_id}/commit",
                "revert": f"/api/experiments/{experiment_id}/revert",
                "measurements": f"/api/experiments/{experiment_id}/measurement-events",
                "graph": f"/api/experiments/{experiment_id}/graph",
                "basin": f"/api/experiments/{experiment_id}/basin",
                "overview": f"/api/experiments/{experiment_id}/overview",
                "sessions": f"/api/experiments/{experiment_id}/sessions",
                "events": f"/api/experiments/{experiment_id}/events",
            },
            "view_modes": {
                "force": "render_coords.force",
                "spectral": "derived_coords.spectral",
                "circular_candidate": "derived_coords.circular_candidate",
                "temporal": "derived_coords.temporal",
                "symmetry": "derived_coords.pca",
                "basin_linked": "derived_coords.basin_linked",
            },
            "filters": graph_model["filters"],
        }
        json_path = out_dir / "graph_knowledge_base.json"
        html_path = out_dir / "graph_knowledge_base.html"
        manifest_path = out_dir / "graph_knowledge_base.manifest.json"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        manifest_path.write_text(
            json.dumps(
                {
                    "artifact_type": "graph_knowledge_base",
                    "generated_at": payload["generated_at"],
                    "json_path": str(json_path),
                    "html_path": str(html_path),
                    "counts": payload["counts"],
                    "health_metrics": payload["health_metrics"],
                    "view_modes": list(payload["view_modes"].keys()),
                    "export_manifest_id": export_manifest_id,
                    "source_graph_hash": graph_model["source_graph_hash"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        html_path.write_text(
            self._shell_html(
                title="EDEN Observatory Graph",
                bootstrap=self._shell_bootstrap(
                    experiment_id=experiment_id,
                    session_id=session_id,
                    initial_surface="graph",
                    export_manifest_id=export_manifest_id,
                    source_graph_hash=graph_model["source_graph_hash"],
                ),
            ),
            encoding="utf-8",
        )
        self.store.record_export_artifact(experiment_id=experiment_id, session_id=session_id, artifact_type="graph_knowledge_base_html", path=html_path)
        self.store.record_export_artifact(experiment_id=experiment_id, session_id=session_id, artifact_type="graph_knowledge_base_json", path=json_path)
        self.runtime_log.emit("INFO", "export_graph", "Generated graph knowledge-base export.", experiment_id=experiment_id, path=str(html_path))
        return (
            {
                "graph_html": str(html_path),
                "graph_json": str(json_path),
                "graph_manifest": str(manifest_path),
            },
            payload,
        )

    def export_behavioral_basin(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        out_dir: Path,
        snapshot: dict[str, Any] | None = None,
    ) -> tuple[dict[str, str], dict[str, Any]]:
        snapshot = snapshot or self.store.graph_snapshot(experiment_id)
        turns = sorted(snapshot["turns"], key=lambda item: (item["session_id"], item["turn_index"]))
        feedback_by_turn: dict[str, list[dict[str, Any]]] = defaultdict(list)
        membrane_by_turn: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for feedback in snapshot["feedback"]:
            feedback_by_turn[feedback["turn_id"]].append(feedback)
        for event in snapshot["membrane_events"]:
            if event["turn_id"]:
                membrane_by_turn[event["turn_id"]].append(event)

        features: list[list[float]] = []
        rendered_turns: list[dict[str, Any]] = []
        previous_active_labels: set[str] = set()
        previous_profile_name = ""
        previous_pressure = ""
        for turn in turns:
            active_set = json.loads(turn["active_set_json"] or "[]")
            metadata = json.loads(turn.get("metadata_json") or "{}")
            inference = metadata.get("inference_profile", {})
            budget = metadata.get("budget", {})
            if not active_set:
                continue
            knowledge_mass = sum(max(0.0, item["selection"]) for item in active_set if item["domain"] != "behavior")
            behavior_mass = sum(max(0.0, item["selection"]) for item in active_set if item["domain"] == "behavior")
            avg_regard = float(np.mean([item["regard"] for item in active_set])) if active_set else 0.0
            avg_activation = float(np.mean([item["activation"] for item in active_set])) if active_set else 0.0
            memode_fraction = sum(1 for item in active_set if item["node_kind"] == "memode") / max(1, len(active_set))
            feedback_verdicts = [entry["verdict"] for entry in feedback_by_turn.get(turn["id"], [])]
            score_map = {"accept": 1.0, "edit": 0.4, "reject": -1.0, "skip": 0.0}
            feedback_balance = (
                sum(score_map.get(verdict, 0.0) for verdict in feedback_verdicts) / len(feedback_verdicts)
                if feedback_verdicts
                else 0.0
            )
            dominant = max(active_set, key=lambda item: item["selection"])
            active_labels = {item["label"] for item in active_set[:8]}
            overlap = len(active_labels & previous_active_labels) / max(1, len(active_labels | previous_active_labels)) if previous_active_labels else 0.0
            profile_name = str(inference.get("profile_name", "unknown"))
            pressure = str(budget.get("pressure_level", "LOW"))
            phase_transition = bool(
                previous_profile_name
                and (
                    previous_profile_name != profile_name
                    or previous_pressure != pressure
                    or abs(feedback_balance) >= 0.9
                )
            )
            features.append(
                [
                    knowledge_mass,
                    behavior_mass,
                    avg_regard,
                    avg_activation,
                    memode_fraction,
                    feedback_balance,
                    float(budget.get("pressure_ratio", 0.0)),
                    overlap,
                ]
            )
            rendered_turns.append(
                {
                    "turn_id": turn["id"],
                    "session_id": turn["session_id"],
                    "turn_index": turn["turn_index"],
                    "created_at": turn["created_at"],
                    "knowledge_mass": knowledge_mass,
                    "behavior_mass": behavior_mass,
                    "avg_regard": avg_regard,
                    "avg_activation": avg_activation,
                    "memode_fraction": memode_fraction,
                    "feedback_balance": feedback_balance,
                    "dominant_label": dominant["label"],
                    "dominant_domain": dominant["domain"],
                    "dominant_node_id": dominant.get("node_id", ""),
                    "dominant_memode_id": dominant.get("node_id", "") if dominant.get("node_kind") == "memode" else "",
                    "dominant_cluster_signature": "",
                    "display_attractor_label": dominant["label"],
                    "active_set_node_ids": [item.get("node_id") for item in active_set if item.get("node_id")],
                    "sequence_z": 0.0,
                    "transition_kind": "phase_transition" if phase_transition else "continuity",
                    "feedback_verdicts": feedback_verdicts,
                    "active_set_labels": sorted(active_labels),
                    "active_set_overlap": round(float(overlap), 4),
                    "profile_name": profile_name,
                    "requested_mode": inference.get("requested_mode", "unknown"),
                    "effective_mode": inference.get("effective_mode", "unknown"),
                    "budget_pressure": pressure,
                    "remaining_input_tokens": budget.get("remaining_input_tokens", 0),
                    "reserved_output_tokens": budget.get("reserved_output_tokens", 0),
                    "response_char_cap": inference.get("response_char_cap", 0),
                    "count_method": budget.get("count_method", "unknown"),
                    "membrane_event_count": len(membrane_by_turn.get(turn["id"], [])),
                    "phase_transition": phase_transition,
                }
            )
            previous_active_labels = active_labels
            previous_profile_name = profile_name
            previous_pressure = pressure

        projection = {"method": "svd_on_turn_features", "explained_variance_top2": 0.0}
        if features:
            matrix = np.array(features, dtype=float)
            centered = matrix - matrix.mean(axis=0, keepdims=True)
            if len(rendered_turns) >= 2:
                u, s, vt = np.linalg.svd(centered, full_matrices=False)
                components = vt[:2]
                coords = centered @ components.T
                power = np.square(s)
                projection["explained_variance_top2"] = float(power[:2].sum() / max(1e-9, power.sum()))
            else:
                coords = np.column_stack((centered[:, 0], np.zeros(len(centered))))
            for turn, coord in zip(rendered_turns, coords, strict=True):
                turn["x"] = float(coord[0])
                turn["y"] = float(coord[1])
        attractor_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for turn in rendered_turns:
            attractor_groups[turn["dominant_label"]].append(turn)
        attractors = []
        for label, group in attractor_groups.items():
            attractors.append(
                {
                    "label": label,
                    "count": len(group),
                    "x": float(np.mean([item["x"] for item in group])) if group else 0.0,
                    "y": float(np.mean([item["y"] for item in group])) if group else 0.0,
                    "domain": Counter(item["dominant_domain"] for item in group).most_common(1)[0][0],
                    "session_count": len({item["session_id"] for item in group}),
                }
            )
        transitions: Counter[tuple[str, str]] = Counter()
        for left, right in zip(rendered_turns, rendered_turns[1:], strict=False):
            transitions[(left["dominant_label"], right["dominant_label"])] += 1
        export_manifest_id = sha256_text(f"basin:{experiment_id}:{session_id}:{now_utc()}")[:12]
        payload = {
            "schema_version": OBSERVATORY_BASIN_SCHEMA_VERSION,
            "export_manifest_id": export_manifest_id,
            "generated_at": now_utc(),
            "experiment_id": experiment_id,
            "session_id": session_id,
            "turn_count": len(rendered_turns),
            "source_turn_count": len(turns),
            "filtered_turn_count": len(rendered_turns),
            "session_count": len({turn["session_id"] for turn in rendered_turns}),
            "projection": projection,
            "projection_method": projection["method"],
            "projection_version": "svd_on_turn_features:v2",
            "projection_input_hash": sha256_text(json.dumps(features, sort_keys=True))[:16] if features else "empty",
            "feature_columns": ["knowledge_mass", "behavior_mass", "avg_regard", "avg_activation", "memode_fraction", "feedback_balance", "budget_pressure_ratio", "active_set_overlap"],
            "lift_modes": BASIN_LIFT_MODES,
            "turns": rendered_turns,
            "attractors": sorted(attractors, key=lambda item: item["count"], reverse=True),
            "transitions": [
                {"from": left, "to": right, "count": count}
                for (left, right), count in transitions.most_common()
            ],
            "diagnostics": {
                "source_turn_count": len(turns),
                "filtered_turn_count": len(rendered_turns),
                "skipped_turn_count": max(0, len(turns) - len(rendered_turns)),
                "empty_state": len(rendered_turns) < 2,
                "reason": "Not enough turns with non-empty active sets for basin playback." if len(rendered_turns) < 2 else "ok",
            },
            "continuity": {
                "revisitation_ratio": float(
                    sum(count for count in Counter(turn["dominant_label"] for turn in rendered_turns).values() if count > 1)
                    / max(1, len(rendered_turns))
                ),
                "mean_step_distance": float(
                    np.mean(
                        [
                            np.linalg.norm(np.array([right["x"], right["y"]]) - np.array([left["x"], left["y"]]))
                            for left, right in zip(rendered_turns, rendered_turns[1:], strict=False)
                        ]
                    )
                    if len(rendered_turns) > 1
                    else 0.0
                ),
                "phase_transition_count": sum(1 for turn in rendered_turns if turn["phase_transition"]),
            },
        }
        json_path = out_dir / "behavioral_attractor_basin.json"
        html_path = out_dir / "behavioral_attractor_basin.html"
        manifest_path = out_dir / "behavioral_attractor_basin.manifest.json"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        manifest_path.write_text(
            json.dumps(
                {
                    "artifact_type": "behavioral_attractor_basin",
                    "generated_at": payload["generated_at"],
                    "json_path": str(json_path),
                    "html_path": str(html_path),
                    "turn_count": payload["turn_count"],
                    "session_count": payload["session_count"],
                    "projection": payload["projection"],
                    "export_manifest_id": export_manifest_id,
                    "projection_method": payload["projection_method"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        html_path.write_text(
            self._shell_html(
                title="EDEN Observatory Basin",
                bootstrap=self._shell_bootstrap(
                    experiment_id=experiment_id,
                    session_id=session_id,
                    initial_surface="basin",
                    export_manifest_id=export_manifest_id,
                    source_graph_hash="",
                    projection_method=payload["projection_method"],
                ),
            ),
            encoding="utf-8",
        )
        self.store.record_export_artifact(experiment_id=experiment_id, session_id=session_id, artifact_type="behavioral_attractor_basin_html", path=html_path)
        self.store.record_export_artifact(experiment_id=experiment_id, session_id=session_id, artifact_type="behavioral_attractor_basin_json", path=json_path)
        self.runtime_log.emit("INFO", "export_basin", "Generated behavioral attractor basin export.", experiment_id=experiment_id, path=str(html_path))
        return (
            {
                "basin_html": str(html_path),
                "basin_json": str(json_path),
                "basin_manifest": str(manifest_path),
            },
            payload,
        )

    def _enrich_basin_payload(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        out_dir: Path,
        basin_paths: dict[str, str],
        basin_payload: dict[str, Any],
        graph_model: dict[str, Any],
    ) -> tuple[dict[str, str], dict[str, Any]]:
        cluster_lookup = graph_model.get("cluster_lookup", {})
        assembly_lookup = {assembly["id"]: assembly for assembly in graph_model.get("assemblies", [])}
        label_by_cluster = {summary["cluster_signature"]: summary["display_label"] for summary in graph_model.get("cluster_summaries", [])}
        for turn in basin_payload.get("turns", []):
            dominant_node_id = str(turn.get("dominant_node_id") or "")
            cluster_signature = cluster_lookup.get(dominant_node_id, {}).get("cluster_signature", "") if dominant_node_id else ""
            dominant_memode_id = str(turn.get("dominant_memode_id") or "")
            memode_label = assembly_lookup.get(dominant_memode_id, {}).get("label", "") if dominant_memode_id else ""
            turn["dominant_cluster_signature"] = cluster_signature
            if not dominant_memode_id and dominant_node_id in assembly_lookup:
                turn["dominant_memode_id"] = dominant_node_id
                dominant_memode_id = dominant_node_id
                memode_label = assembly_lookup.get(dominant_memode_id, {}).get("label", "")
            turn["display_attractor_label"] = label_by_cluster.get(cluster_signature) or memode_label or turn.get("dominant_label", "")
        for attractor in basin_payload.get("attractors", []):
            matching_turns = [turn for turn in basin_payload.get("turns", []) if turn.get("dominant_label") == attractor.get("label")]
            cluster_counts = Counter(turn.get("dominant_cluster_signature", "") for turn in matching_turns if turn.get("dominant_cluster_signature"))
            attractor["cluster_signature"] = cluster_counts.most_common(1)[0][0] if cluster_counts else ""
            attractor["display_label"] = label_by_cluster.get(attractor["cluster_signature"], attractor.get("label", ""))
            attractor["member_turn_ids"] = [turn.get("turn_id") for turn in matching_turns]
        json_path = out_dir / "behavioral_attractor_basin.json"
        html_path = out_dir / "behavioral_attractor_basin.html"
        manifest_path = out_dir / "behavioral_attractor_basin.manifest.json"
        json_path.write_text(json.dumps(basin_payload, indent=2), encoding="utf-8")
        manifest_path.write_text(
            json.dumps(
                {
                    "artifact_type": "behavioral_attractor_basin",
                    "generated_at": basin_payload["generated_at"],
                    "json_path": str(json_path),
                    "html_path": str(html_path),
                    "turn_count": basin_payload["turn_count"],
                    "session_count": basin_payload["session_count"],
                    "projection": basin_payload["projection"],
                    "export_manifest_id": basin_payload.get("export_manifest_id"),
                    "projection_method": basin_payload.get("projection_method"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        html_path.write_text(
            self._shell_html(
                title="EDEN Observatory Basin",
                bootstrap=self._shell_bootstrap(
                    experiment_id=experiment_id,
                    session_id=session_id,
                    initial_surface="basin",
                    export_manifest_id=basin_payload.get("export_manifest_id"),
                    source_graph_hash=graph_model.get("source_graph_hash", ""),
                    projection_method=basin_payload.get("projection_method"),
                ),
            ),
            encoding="utf-8",
        )
        return basin_paths, basin_payload

    def export_geometry_lab(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        out_dir: Path,
        graph_model: dict[str, Any],
    ) -> dict[str, str]:
        graph = graph_model["graph"]
        directed = graph_model["directed_graph"]
        edge_types = graph_model["edge_types"]
        node_order = graph_model["node_order"]
        base_metrics = compute_geometry_metrics(graph, directed, coords=graph_model["coords"], node_order=node_order)
        dominant = base_metrics["communities"][0]["members"] if base_metrics["communities"] else []
        ablations = compute_ablation_report(
            graph,
            directed,
            edge_types=edge_types,
            node_order=node_order,
            drop_community=dominant,
        )
        slices = self._geometry_slices(graph_model, session_id=session_id)
        payload = {
            "generated_at": now_utc(),
            "experiment_id": experiment_id,
            "session_id": session_id,
            "legend": {
                "OBSERVED": "Directly computed from graph topology or explicit recurrence counts.",
                "DERIVED": "Computed from transforms, projections, or ordered-structure proxies.",
                "SPECULATIVE": "Operator-facing hypothesis layer only. Not used for any current score.",
            },
            "nodes": graph_model["nodes"],
            "edges": graph_model["edges"],
            "measurement_events": graph_model["measurement_events"],
            "coordinate_methods": {
                "force": "Render layout only.",
                "spectral": "Laplacian eigenvectors.",
                "pca": "PCA on adjacency rows.",
                "circular_candidate": "Evenly spaced circle using spectral-order angles.",
                "temporal": "Ordered chronology projection.",
            },
            "full_graph": {
                "metrics": base_metrics,
                "ablations": ablations,
            },
            "slices": slices,
            "local_reports": self._local_geometry_reports(graph_model, session_id=session_id),
        }
        json_path = out_dir / "geometry_diagnostics.json"
        html_path = out_dir / "geometry_lab.html"
        manifest_path = out_dir / "geometry_manifest.json"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        manifest_path.write_text(
            json.dumps(
                {
                    "artifact_type": "geometry_lab",
                    "generated_at": payload["generated_at"],
                    "json_path": str(json_path),
                    "html_path": str(html_path),
                    "slice_names": list(payload["slices"].keys()),
                    "coordinate_methods": list(payload["coordinate_methods"].keys()),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        html_path.write_text(
            self._shell_html(
                title="EDEN Observatory Geometry",
                bootstrap=self._shell_bootstrap(
                    experiment_id=experiment_id,
                    session_id=session_id,
                    initial_surface="geometry",
                ),
            ),
            encoding="utf-8",
        )
        self.store.record_export_artifact(experiment_id=experiment_id, session_id=session_id, artifact_type="geometry_lab_html", path=html_path)
        self.store.record_export_artifact(experiment_id=experiment_id, session_id=session_id, artifact_type="geometry_diagnostics_json", path=json_path)
        self.runtime_log.emit("INFO", "export_geometry", "Generated geometry diagnostics export.", experiment_id=experiment_id, path=str(html_path))
        return {
            "geometry_html": str(html_path),
            "geometry_json": str(json_path),
            "geometry_manifest": str(manifest_path),
        }

    def export_measurement_ledger(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        out_dir: Path,
        snapshot: dict[str, Any],
    ) -> tuple[dict[str, str], dict[str, Any]]:
        rows = [self._measurement_event_payload(item) for item in snapshot.get("measurement_events", [])]
        if session_id:
            rows = [item for item in rows if item.get("session_id") in {session_id, None, ""}]
        payload = {
            "generated_at": now_utc(),
            "experiment_id": experiment_id,
            "session_id": session_id,
            "counts": {
                "events": len(rows),
                "action_types": dict(Counter(item["action_type"] for item in rows)),
                "evidence_labels": dict(Counter(item["evidence_label"] for item in rows)),
            },
            "events": rows,
        }
        json_path = out_dir / "measurement_events.json"
        html_path = out_dir / "measurement_ledger.html"
        manifest_path = out_dir / "measurement_events.manifest.json"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        manifest_path.write_text(
            json.dumps(
                {
                    "artifact_type": "measurement_ledger",
                    "generated_at": payload["generated_at"],
                    "json_path": str(json_path),
                    "html_path": str(html_path),
                    "event_count": payload["counts"]["events"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        html_path.write_text(
            self._shell_html(
                title="EDEN Observatory Measurements",
                bootstrap=self._shell_bootstrap(
                    experiment_id=experiment_id,
                    session_id=session_id,
                    initial_surface="measurements",
                ),
            ),
            encoding="utf-8",
        )
        self.store.record_export_artifact(experiment_id=experiment_id, session_id=session_id, artifact_type="measurement_ledger_html", path=html_path)
        self.store.record_export_artifact(experiment_id=experiment_id, session_id=session_id, artifact_type="measurement_events_json", path=json_path)
        self.runtime_log.emit("INFO", "export_measurements", "Generated measurement ledger export.", experiment_id=experiment_id, path=str(html_path))
        return (
            {
                "measurement_html": str(html_path),
                "measurement_json": str(json_path),
                "measurement_manifest": str(manifest_path),
            },
            payload,
        )

    def export_observatory_index(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        out_dir: Path,
        graph_payload: dict[str, Any],
        basin_payload: dict[str, Any],
        measurement_payload: dict[str, Any],
        graph_paths: dict[str, str],
        basin_paths: dict[str, str],
        geometry_paths: dict[str, str],
        measurement_paths: dict[str, str],
        tanakh_paths: dict[str, str],
        tanakh_payload: dict[str, Any] | None,
    ) -> dict[str, str]:
        hum = self._hum_summary(session_id)
        payload = {
            "generated_at": now_utc(),
            "experiment_id": experiment_id,
            "session_id": session_id,
            "hum": hum,
            "artifacts": {
                "graph": graph_paths,
                "basin": basin_paths,
                "geometry": geometry_paths,
                "measurement": measurement_paths,
                "tanakh": tanakh_paths,
            },
            "summary": {
                "nodes": len(graph_payload["nodes"]),
                "edges": len(graph_payload["edges"]),
                "turns": basin_payload["turn_count"],
                "sessions": basin_payload["session_count"],
                "measurement_events": measurement_payload["counts"]["events"],
                "tanakh_ref": (tanakh_payload or {}).get("current_ref"),
            },
        }
        html_path = out_dir / "observatory_index.html"
        json_path = out_dir / "observatory_index.json"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        html_path.write_text(
            self._shell_html(
                title="EDEN Observatory",
                bootstrap=self._shell_bootstrap(
                    experiment_id=experiment_id,
                    session_id=session_id,
                    initial_surface="overview",
                ),
            ),
            encoding="utf-8",
        )
        self.store.record_export_artifact(experiment_id=experiment_id, session_id=session_id, artifact_type="observatory_index_html", path=html_path)
        return {
            "observatory_index_html": str(html_path),
            "observatory_index_json": str(json_path),
        }

    def _hum_summary(self, session_id: str | None) -> dict[str, Any]:
        if not session_id or self.hum_provider is None:
            return {
                "present": False,
                "artifact_version": None,
                "generated_at": None,
                "markdown_path": None,
                "json_path": None,
                "latest_turn_id": None,
                "turn_window_size": 0,
                "cross_turn_recurrence_present": False,
            }
        try:
            return dict(self.hum_provider(session_id))
        except Exception as exc:
            return {
                "present": False,
                "artifact_version": None,
                "generated_at": None,
                "markdown_path": None,
                "json_path": None,
                "latest_turn_id": None,
                "turn_window_size": 0,
                "cross_turn_recurrence_present": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def _build_graph_model(self, *, snapshot: dict[str, Any], session_id: str | None, basin_payload: dict[str, Any]) -> dict[str, Any]:
        graph = nx.Graph()
        directed = nx.DiGraph()
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        edge_types: dict[tuple[str, str], str] = {}
        feedback_by_turn: dict[str, list[dict[str, Any]]] = defaultdict(list)
        basin_coords = {turn["turn_id"]: {"x": turn.get("x", 0.0), "y": turn.get("y", 0.0)} for turn in basin_payload["turns"]}
        turn_session_map = {turn["id"]: turn["session_id"] for turn in snapshot["turns"]}
        session_meta = {item["id"]: json.loads(item["metadata_json"] or "{}") for item in snapshot["sessions"]}
        turn_meta = {item["id"]: json.loads(item.get("metadata_json") or "{}") for item in snapshot["turns"]}
        document_ids = {item["id"] for item in snapshot["documents"]}
        measurement_events = [self._measurement_event_payload(item) for item in snapshot.get("measurement_events", [])]
        for feedback in snapshot["feedback"]:
            feedback_by_turn[feedback["turn_id"]].append(feedback)

        def add_node(node_id: str, label: str, kind: str, **extra: Any) -> None:
            export_label = str(extra.pop("export_label", "") or "").strip() or label
            node = {"id": node_id, "label": label, "export_label": export_label, "kind": kind, **extra}
            nodes.append(node)
            graph.add_node(node_id, **node)
            directed.add_node(node_id, **node)

        for agent in snapshot["agents"]:
            add_node(
                agent["id"],
                agent["name"],
                "agent",
                domain="behavior",
                source_kind="agent",
                summary=agent["name"],
                export_label=_semantic_export_label(agent["name"], fallback=agent["name"], limit=96),
                session_id="",
            )
        for session in snapshot["sessions"]:
            meta = session_meta.get(session["id"], {})
            add_node(
                session["id"],
                session["title"],
                "session",
                domain="behavior",
                source_kind="session",
                summary=session["title"],
                export_label=_semantic_export_label(session["title"], fallback=session["title"], limit=110),
                session_id=session["id"],
                created_at=session["created_at"],
                requested_mode=meta.get("requested_mode", ""),
                verdicts=[],
            )
            implicit_provenance = {"assertion_origin": "auto_derived", "evidence_label": "AUTO_DERIVED", "confidence": 1.0}
            graph.add_edge(session["agent_id"], session["id"], weight=1.0, edge_type="BELONGS_TO_AGENT", provenance=implicit_provenance)
            directed.add_edge(session["agent_id"], session["id"], weight=1.0, edge_type="BELONGS_TO_AGENT", provenance=implicit_provenance)
            edges.append({"id": f"implicit::{session['agent_id']}::{session['id']}::BELONGS_TO_AGENT", "source": session["agent_id"], "target": session["id"], "type": "BELONGS_TO_AGENT", "weight": 1.0, "provenance": implicit_provenance})
            edge_types[(session["agent_id"], session["id"])] = "BELONGS_TO_AGENT"
        for document in snapshot["documents"]:
            metadata = json.loads(document["metadata_json"] or "{}")
            add_node(
                document["id"],
                document["title"],
                "document",
                domain="knowledge",
                source_kind=document["kind"],
                summary=document["path"],
                export_label=_semantic_export_label(document["title"], metadata.get("source_path"), document["path"], fallback=document["title"], limit=120),
                session_id="",
                created_at=document["created_at"],
                provenance=metadata.get("source_path", document["path"]),
                verdicts=[],
            )
        for turn in snapshot["turns"]:
            metadata = turn_meta.get(turn["id"], {})
            inference = metadata.get("inference_profile", {})
            budget = metadata.get("budget", {})
            verdicts = [item["verdict"] for item in feedback_by_turn.get(turn["id"], [])]
            add_node(
                turn["id"],
                f"T{turn['turn_index']}",
                "turn",
                domain="behavior",
                source_kind="turn",
                summary=safe_excerpt(turn["user_text"], limit=140),
                export_label=_semantic_export_label(
                    safe_excerpt(turn["user_text"], limit=140),
                    safe_excerpt(turn.get("membrane_text") or turn.get("response_text") or "", limit=140),
                    fallback=f"T{turn['turn_index']}",
                    limit=140,
                ),
                session_id=turn["session_id"],
                created_at=turn["created_at"],
                requested_mode=inference.get("requested_mode", ""),
                effective_mode=inference.get("effective_mode", ""),
                profile_name=inference.get("profile_name", ""),
                budget_pressure=budget.get("pressure_level", ""),
                verdicts=verdicts,
                time_order=turn["turn_index"],
            )
            implicit_provenance = {"assertion_origin": "auto_derived", "evidence_label": "AUTO_DERIVED", "confidence": 1.0}
            graph.add_edge(turn["session_id"], turn["id"], weight=1.0, edge_type="BELONGS_TO_SESSION", provenance=implicit_provenance)
            directed.add_edge(turn["session_id"], turn["id"], weight=1.0, edge_type="BELONGS_TO_SESSION", provenance=implicit_provenance)
            edges.append({"id": f"implicit::{turn['session_id']}::{turn['id']}::BELONGS_TO_SESSION", "source": turn["session_id"], "target": turn["id"], "type": "BELONGS_TO_SESSION", "weight": 1.0, "provenance": implicit_provenance})
            edge_types[(turn["session_id"], turn["id"])] = "BELONGS_TO_SESSION"
        for feedback in snapshot["feedback"]:
            add_node(
                feedback["id"],
                feedback["verdict"].upper(),
                "feedback",
                domain="behavior",
                source_kind="feedback",
                summary=safe_excerpt(feedback["explanation"], limit=140),
                export_label=_semantic_export_label(
                    safe_excerpt(feedback["explanation"], limit=140),
                    feedback["verdict"].upper(),
                    fallback=feedback["verdict"].upper(),
                    limit=140,
                ),
                session_id=feedback["session_id"],
                created_at=feedback["created_at"],
                verdicts=[feedback["verdict"]],
            )
            implicit_provenance = {"assertion_origin": "feedback_derived", "evidence_label": "OBSERVED", "confidence": 1.0}
            graph.add_edge(feedback["turn_id"], feedback["id"], weight=1.0, edge_type="FED_BACK_BY", provenance=implicit_provenance)
            directed.add_edge(feedback["turn_id"], feedback["id"], weight=1.0, edge_type="FED_BACK_BY", provenance=implicit_provenance)
            edges.append({"id": f"implicit::{feedback['turn_id']}::{feedback['id']}::FED_BACK_BY", "source": feedback["turn_id"], "target": feedback["id"], "type": "FED_BACK_BY", "weight": 1.0, "provenance": implicit_provenance})
            edge_types[(feedback["turn_id"], feedback["id"])] = "FED_BACK_BY"
        for meme in snapshot["memes"]:
            metadata = json.loads(meme["metadata_json"] or "{}")
            turn_id = metadata.get("turn_id", "")
            add_node(
                meme["id"],
                meme["label"],
                "meme",
                domain=meme["domain"],
                source_kind=meme["source_kind"],
                scope=meme["scope"],
                summary=safe_excerpt(meme["text"], limit=160),
                export_label=_semantic_export_label(
                    safe_excerpt(meme["text"], limit=160),
                    meme["label"],
                    metadata.get("title"),
                    fallback=meme["label"],
                    limit=160,
                ),
                evidence=float(meme["evidence_n"]),
                reward=float(meme["reward_ema"]),
                risk=float(meme["risk_ema"]),
                usage_count=int(meme["usage_count"]),
                feedback_count=int(meme["feedback_count"]),
                skip_count=int(meme["skip_count"]),
                membrane_conflicts=int(meme["membrane_conflicts"]),
                provenance=metadata.get("title") or metadata.get("source_path") or metadata.get("origin", ""),
                session_id=metadata.get("session_id", ""),
                created_at=meme["created_at"],
                verdicts=[item["verdict"] for item in feedback_by_turn.get(turn_id, [])],
            )
        for memode in snapshot["memodes"]:
            metadata = json.loads(memode["metadata_json"] or "{}")
            turn_id = metadata.get("turn_id", "")
            add_node(
                memode["id"],
                memode["label"],
                "memode",
                domain=memode["domain"],
                source_kind="memode",
                scope=memode["scope"],
                summary=safe_excerpt(memode["summary"], limit=160),
                export_label=_semantic_export_label(
                    safe_excerpt(memode["summary"], limit=160),
                    memode["label"],
                    metadata.get("invariance_summary"),
                    fallback=memode["label"],
                    limit=160,
                ),
                evidence=float(memode["evidence_n"]),
                reward=float(memode["reward_ema"]),
                risk=float(memode["risk_ema"]),
                usage_count=int(memode["usage_count"]),
                feedback_count=int(memode["feedback_count"]),
                member_ids=metadata.get("member_ids", []),
                supporting_edge_ids=metadata.get("supporting_edge_ids", []),
                invariance_summary=metadata.get("invariance_summary", memode["summary"]),
                member_order=metadata.get("member_order", []),
                occurrence_examples=metadata.get("occurrence_examples", []),
                evidence_label=metadata.get("evidence_label", metadata.get("assertion_origin", "AUTO_DERIVED")),
                operator_label=metadata.get("operator_label", ""),
                confidence=float(metadata.get("confidence", 0.0) or 0.0),
                provenance=metadata.get("title") or metadata.get("origin", ""),
                session_id=metadata.get("session_id", ""),
                created_at=memode["created_at"],
                verdicts=[item["verdict"] for item in feedback_by_turn.get(turn_id, [])],
            )
        node_by_id = {node["id"]: node for node in nodes}
        for edge in snapshot["edges"]:
            if edge["src_id"] not in graph or edge["dst_id"] not in graph:
                continue
            provenance = json.loads(edge["provenance_json"] or "{}")
            graph.add_edge(edge["src_id"], edge["dst_id"], weight=float(edge["weight"]), edge_type=edge["edge_type"], provenance=provenance)
            directed.add_edge(edge["src_id"], edge["dst_id"], weight=float(edge["weight"]), edge_type=edge["edge_type"], provenance=provenance)
            edge_payload = {
                "id": edge["id"],
                "source": edge["src_id"],
                "target": edge["dst_id"],
                "type": edge["edge_type"],
                "weight": float(edge["weight"]),
                "provenance": provenance,
            }
            edges.append(edge_payload)
            edge_types[(edge["src_id"], edge["dst_id"])] = edge["edge_type"]

        node_order = [
            node["id"]
            for node in sorted(
                nodes,
                key=lambda item: (
                    0 if item["kind"] == "turn" else 1 if item["kind"] == "feedback" else 2,
                    item.get("session_id", ""),
                    item.get("time_order", 999999),
                    item.get("created_at", ""),
                    item["label"],
                ),
            )
        ]
        coords = compute_coordinate_sets(graph, node_order=node_order)
        geometry = compute_geometry_metrics(graph, directed, coords=coords, node_order=node_order)
        community_lookup: dict[str, int] = {}
        for item in geometry["communities"]:
            for member in item["members"]:
                community_lookup[member] = item["community_id"]
        if graph.number_of_nodes() <= NODE_TOPOLOGY_EXACT_LIMIT:
            clustering = nx.clustering(graph)
            triangles = nx.triangles(graph)
        else:
            clustering = {node_id: 0.0 for node_id in graph.nodes()}
            triangles = {node_id: 0 for node_id in graph.nodes()}
        active_set_counts: Counter[str] = Counter()
        for turn in snapshot["turns"]:
            for item in json.loads(turn["active_set_json"] or "[]"):
                if item.get("node_id"):
                    active_set_counts[item["node_id"]] += 1
        memode_memberships: dict[str, list[str]] = defaultdict(list)
        for memode in snapshot["memodes"]:
            metadata = json.loads(memode["metadata_json"] or "{}")
            for member_id in metadata.get("member_ids", []):
                memode_memberships[member_id].append(memode["id"])
        node_measurements: dict[str, list[dict[str, Any]]] = defaultdict(list)
        edge_measurements: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        reverted_event_ids = {
            item["reverted_from_event_id"]
            for item in measurement_events
            if item.get("reverted_from_event_id")
        }
        for event in measurement_events:
            for target in event["target_ids"]:
                if target.get("kind") == "edge":
                    key = (str(target.get("source_id")), str(target.get("target_id")), str(target.get("edge_type")))
                    edge_measurements[key].append(event)
                elif target.get("kind") == "memode" and target.get("memode_id"):
                    node_measurements[str(target["memode_id"])].append(event)
                    for member_id in target.get("member_ids", []):
                        node_measurements[str(member_id)].append(event)
        for node in nodes:
            node["cluster_id"] = community_lookup.get(node["id"], -1)
            node["degree"] = int(graph.degree(node["id"]))
            node["clustering"] = round(float(clustering.get(node["id"], 0.0)), 4)
            node["triangle_participation"] = int(triangles.get(node["id"], 0))
            node["community"] = node["cluster_id"]
            node["memode_membership"] = sorted(memode_memberships.get(node["id"], []))
            node["recent_active_set_presence"] = int(active_set_counts.get(node["id"], 0))
            node["measurement_history"] = node_measurements.get(node["id"], [])
            node["measurement_event_ids"] = [item["id"] for item in node["measurement_history"]]
            node["regard_breakdown"] = {
                "evidence": round(float(node.get("evidence", 0.0) or 0.0), 4),
                "reward": round(float(node.get("reward", 0.0) or 0.0), 4),
                "risk": round(float(node.get("risk", 0.0) or 0.0), 4),
                "usage_count": int(node.get("usage_count", 0) or 0),
                "feedback_count": int(node.get("feedback_count", 0) or 0),
            }
            node["render_coords"] = {"force": coords["force"].get(node["id"], {"x": 0.0, "y": 0.0})}
            node["derived_coords"] = {
                "spectral": coords["spectral"].get(node["id"], {"x": 0.0, "y": 0.0}),
                "pca": coords["pca"].get(node["id"], {"x": 0.0, "y": 0.0}),
                "circular_candidate": coords["circular_candidate"].get(node["id"], {"x": 0.0, "y": 0.0}),
                "temporal": coords["temporal"].get(node["id"], {"x": 0.0, "y": 0.0}),
                "basin_linked": basin_coords.get(node["id"], coords["spectral"].get(node["id"], {"x": 0.0, "y": 0.0})),
            }
        for edge in edges:
            history = edge_measurements.get((edge["source"], edge["target"], edge["type"]), [])
            edge["measurement_history"] = history
            edge["measurement_event_ids"] = [item["id"] for item in history]
            edge["reverted"] = any(item["id"] in reverted_event_ids for item in history)
            provenance = edge.get("provenance", {})
            edge["assertion_origin"] = provenance.get("assertion_origin", "auto_derived")
            edge["evidence_label"] = provenance.get("evidence_label", "AUTO_DERIVED")
            edge["operator_label"] = provenance.get("operator_label", "")
            edge["confidence"] = float(provenance.get("confidence", 1.0 if edge["assertion_origin"] == "auto_derived" else 0.6) or 0.0)
            source_node = node_by_id.get(edge["source"])
            target_node = node_by_id.get(edge["target"])
            edge["export_label"] = _semantic_export_label(
                provenance.get("operator_label"),
                f"{edge['type']}: {(source_node or {}).get('export_label') or (source_node or {}).get('label') or edge['source']} -> {(target_node or {}).get('export_label') or (target_node or {}).get('label') or edge['target']}",
                edge["type"],
                fallback=edge["type"],
                limit=200,
            )
        filters = {
            "sessions": sorted({node.get("session_id", "") for node in nodes if node.get("session_id")}),
            "kinds": sorted({node["kind"] for node in nodes}),
            "domains": sorted({node.get("domain", "") for node in nodes if node.get("domain")}),
            "sources": sorted({node.get("source_kind", "") for node in nodes if node.get("source_kind")}),
            "verdicts": sorted({verdict for node in nodes for verdict in node.get("verdicts", [])}),
            "evidence_labels": sorted({node.get("evidence_label", "") for node in nodes if node.get("evidence_label")}),
        }
        latest_active_ids: list[str] = []
        if session_id:
            turns = [turn for turn in snapshot["turns"] if turn["session_id"] == session_id]
            if turns:
                latest_turn = sorted(turns, key=lambda item: item["turn_index"])[-1]
                latest_active_ids = [item["node_id"] for item in json.loads(latest_turn["active_set_json"] or "[]")]
        semantic_graph = nx.Graph()
        semantic_node_order = sorted(node["id"] for node in nodes if node.get("kind") == "meme")
        for node in nodes:
            if node.get("kind") == "meme":
                semantic_graph.add_node(node["id"], **node)
        for edge in edges:
            source = next((node for node in nodes if node["id"] == edge["source"]), None)
            target = next((node for node in nodes if node["id"] == edge["target"]), None)
            if source and target and source.get("kind") == "meme" and target.get("kind") == "meme" and edge.get("type") in MEMODE_SUPPORT_EDGE_ALLOWLIST:
                semantic_graph.add_edge(edge["source"], edge["target"], **edge)
        semantic_coords = compute_coordinate_sets(semantic_graph, node_order=semantic_node_order)
        planes = build_graph_planes(
            snapshot=snapshot,
            nodes=nodes,
            edges=edges,
            measurement_events=measurement_events,
            semantic_coord_lookup=semantic_coords.get("force", {}),
        )
        for node in nodes:
            cluster = planes["cluster_lookup"].get(node["id"], {})
            if cluster:
                node["cluster_signature"] = cluster.get("cluster_signature", "")
                node["cluster_label"] = cluster.get("display_label", "")
        return {
            "nodes": nodes,
            "edges": edges,
            "graph": graph,
            "directed_graph": directed,
            "edge_types": edge_types,
            "coords": coords,
            "node_order": node_order,
            "filters": filters,
            "latest_active_ids": latest_active_ids,
            "measurement_events": measurement_events,
            "semantic_nodes": planes["semantic_nodes"],
            "semantic_edges": planes["semantic_edges"],
            "runtime_nodes": planes["runtime_nodes"],
            "runtime_edges": planes["runtime_edges"],
            "assemblies": planes["assemblies"],
            "cluster_summaries": planes["cluster_summaries"],
            "cluster_lookup": planes["cluster_lookup"],
            "active_set_slices": planes["active_set_slices"],
            "source_graph_hash": planes["cluster_summaries"][0]["source_graph_hash"] if planes["cluster_summaries"] else "empty",
        }

    def _geometry_slices(self, graph_model: dict[str, Any], *, session_id: str | None) -> dict[str, Any]:
        nodes = graph_model["nodes"]
        graph = graph_model["graph"]
        directed = graph_model["directed_graph"]
        slices: dict[str, Any] = {}
        slices["full_graph"] = self._slice_payload("full_graph", graph, directed, graph_model["coords"], graph_model["node_order"])
        if session_id:
            session_nodes = {node["id"] for node in nodes if node.get("session_id") == session_id or node["id"] == session_id}
            if len(session_nodes) >= 2:
                slices["current_session"] = self._slice_payload("current_session", *self._subgraphs(graph, directed, session_nodes))
        active_nodes = set(graph_model["latest_active_ids"])
        if len(active_nodes) >= 2:
            slices["current_active_set"] = self._slice_payload("current_active_set", *self._subgraphs(graph, directed, active_nodes))
        for verdict in ("accept", "edit", "reject", "skip"):
            verdict_nodes = {node["id"] for node in nodes if verdict in node.get("verdicts", [])}
            if len(verdict_nodes) >= 2:
                slices[f"verdict_{verdict}"] = self._slice_payload(f"verdict_{verdict}", *self._subgraphs(graph, directed, verdict_nodes))
        return slices

    def _local_geometry_reports(self, graph_model: dict[str, Any], *, session_id: str | None) -> dict[str, Any]:
        graph = graph_model["graph"]
        directed = graph_model["directed_graph"]
        reports: dict[str, Any] = {}
        active_ids = [node_id for node_id in graph_model["latest_active_ids"] if node_id in graph]
        if len(active_ids) >= 2:
            reports["latest_active_set"] = compute_selection_geometry(
                graph,
                directed,
                selected_node_ids=active_ids,
                radius=1,
                node_order=graph_model["node_order"],
            )
        memode_nodes = [node for node in graph_model["nodes"] if node["kind"] == "memode"]
        memode_nodes.sort(
            key=lambda node: (
                0 if session_id and node.get("session_id") == session_id else 1,
                -int(node.get("recent_active_set_presence", 0) or 0),
                -float(node.get("evidence", 0.0) or 0.0),
                -int(node.get("usage_count", 0) or 0),
                -int(node.get("feedback_count", 0) or 0),
                node["label"],
            )
        )
        for node in memode_nodes[:LOCAL_GEOMETRY_REPORT_LIMIT]:
            member_ids = [member_id for member_id in node.get("member_ids", []) if member_id in graph]
            if len(member_ids) < 2:
                continue
            reports[f"memode::{node['id']}"] = {
                "label": node["label"],
                **compute_selection_geometry(
                    graph,
                    directed,
                    selected_node_ids=member_ids,
                    radius=1,
                    node_order=graph_model["node_order"],
                ),
            }
        return reports

    def _slice_payload(
        self,
        name: str,
        graph: nx.Graph,
        directed: nx.DiGraph,
        coords: dict[str, dict[str, dict[str, float]]] | None = None,
        node_order: list[str] | None = None,
    ) -> dict[str, Any]:
        coords = coords or compute_coordinate_sets(graph, node_order=node_order)
        metrics = compute_geometry_metrics(graph, directed, coords=coords, node_order=node_order)
        return {
            "name": name,
            "counts": metrics["counts"],
            "metrics": metrics["metrics"],
            "communities": metrics["communities"],
            "projection_quality": metrics["projection_quality"],
        }

    def _subgraphs(self, graph: nx.Graph, directed: nx.DiGraph, node_ids: set[str]):
        subgraph = graph.subgraph(node_ids).copy()
        subdirected = directed.subgraph(node_ids).copy()
        order = [node for node in graph.nodes() if node in node_ids]
        coords = compute_coordinate_sets(subgraph, node_order=order)
        return subgraph, subdirected, coords, order

    def _measurement_event_payload(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        payload["target_ids"] = json.loads(row.get("target_ids_json") or "[]")
        payload["before_state"] = json.loads(row.get("before_state_json") or "{}")
        payload["proposed_state"] = json.loads(row.get("proposed_state_json") or "{}")
        payload["committed_state"] = json.loads(row.get("committed_state_json") or "{}")
        payload["summary"] = safe_excerpt(
            payload.get("rationale")
            or payload["committed_state"].get("summary")
            or payload["proposed_state"].get("action_type", ""),
            limit=160,
        )
        return payload

    def _graph_html(self, payload: dict[str, Any]) -> str:
        data = json.dumps(payload, ensure_ascii=True)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>EDEN Graph Knowledge Base</title>
  <style>
    :root {{
      --bg: #090603;
      --panel: rgba(27, 15, 4, 0.88);
      --amber: #ffbf66;
      --amber-soft: #d79a43;
      --grid: rgba(255, 191, 102, 0.08);
      --text: #ffe2af;
      --muted: #c08b45;
      --edge: rgba(255, 191, 102, 0.16);
      --cyan: #7de3ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Menlo, SFMono-Regular, monospace;
      background:
        radial-gradient(circle at 20% 20%, rgba(255, 180, 70, 0.18), transparent 28%),
        radial-gradient(circle at 80% 30%, rgba(255, 120, 40, 0.14), transparent 24%),
        linear-gradient(180deg, #050403 0%, #0b0603 100%);
      color: var(--text);
      min-height: 100vh;
    }}
    header {{
      padding: 18px 22px 12px;
      border-bottom: 1px solid rgba(255, 191, 102, 0.25);
      display: flex;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }}
    main {{
      display: grid;
      grid-template-columns: 330px 1fr 340px;
      gap: 14px;
      padding: 14px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid rgba(255, 191, 102, 0.25);
      border-radius: 14px;
      box-shadow: 0 0 24px rgba(0, 0, 0, 0.34);
      overflow: hidden;
    }}
    .panel h2, .panel h3 {{
      margin: 0;
      padding: 12px 14px;
      border-bottom: 1px solid rgba(255, 191, 102, 0.18);
      font-size: 14px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--amber);
    }}
    .panel .body {{
      padding: 12px 14px;
    }}
    .controls {{
      display: grid;
      gap: 10px;
    }}
    select, input {{
      width: 100%;
      background: #120b04;
      border: 1px solid rgba(255, 191, 102, 0.3);
      color: var(--text);
      border-radius: 10px;
      padding: 8px 10px;
    }}
    canvas {{
      width: 100%;
      height: 70vh;
      display: block;
      background:
        radial-gradient(circle at center, rgba(255, 191, 102, 0.03), transparent 45%),
        linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0));
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 10px;
    }}
    .card {{
      background: rgba(255, 191, 102, 0.05);
      border: 1px solid rgba(255, 191, 102, 0.14);
      border-radius: 10px;
      padding: 10px;
    }}
    .muted {{ color: var(--muted); }}
    .legend span {{
      display: inline-block;
      margin-right: 10px;
    }}
    pre {{
      white-space: pre-wrap;
      font-family: inherit;
      margin: 0;
    }}
    @media (max-width: 1100px) {{
      main {{ grid-template-columns: 1fr; }}
      canvas {{ height: 50vh; }}
    }}
  </style>
</head>
<body>
  <script>const payload = {data};</script>
  <header>
    <div>
      <div style="color: var(--amber); font-size: 28px; letter-spacing: 0.14em;">EDEN / GRAPH KNOWLEDGE BASE</div>
      <div class="muted">Render coordinates and derived coordinates are separated. A circle on-screen is not evidence by itself.</div>
    </div>
    <div class="legend">
      <span>modes: force / spectral / circular / temporal / symmetry / basin-linked</span>
    </div>
  </header>
  <main>
    <section class="panel">
      <h2>Filters</h2>
      <div class="body controls">
        <input id="search" placeholder="search label / summary / provenance" />
        <select id="mode"></select>
        <select id="sessionFilter"></select>
        <select id="kindFilter"></select>
        <select id="domainFilter"></select>
        <select id="sourceFilter"></select>
        <select id="verdictFilter"></select>
        <input id="timeFilter" placeholder="created_at contains (e.g. 2026-03-06)" />
      </div>
      <h2>Health</h2>
      <div class="body" id="health"></div>
    </section>
    <section class="panel">
      <h2>Graph View</h2>
      <canvas id="canvas" width="1200" height="760"></canvas>
      <div class="body muted">Hover for inspection. Click to pin. Coordinate mode only changes the view surface; it does not change the underlying graph.</div>
    </section>
    <section class="panel">
      <h2>Inspector</h2>
      <div class="body">
        <pre id="inspector">Hover a node to inspect provenance, verdicts, and budget-linked turn data.</pre>
      </div>
    </section>
  </main>
  <script>
    const nodes = payload.nodes;
    const edges = payload.edges;
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");
    const inspector = document.getElementById("inspector");
    const mode = document.getElementById("mode");
    const search = document.getElementById("search");
    const sessionFilter = document.getElementById("sessionFilter");
    const kindFilter = document.getElementById("kindFilter");
    const domainFilter = document.getElementById("domainFilter");
    const sourceFilter = document.getElementById("sourceFilter");
    const verdictFilter = document.getElementById("verdictFilter");
    const timeFilter = document.getElementById("timeFilter");
    const state = {{ pinned: null, hover: null }};

    const optionize = (element, label, values) => {{
      element.innerHTML = `<option value="">${{label}}</option>` + values.map(v => `<option value="${{v}}">${{v}}</option>`).join("");
    }};
    optionize(mode, "coord mode", Object.keys(payload.view_modes));
    optionize(sessionFilter, "all sessions", payload.filters.sessions);
    optionize(kindFilter, "all kinds", payload.filters.kinds);
    optionize(domainFilter, "all domains", payload.filters.domains);
    optionize(sourceFilter, "all sources", payload.filters.sources);
    optionize(verdictFilter, "all verdicts", payload.filters.verdicts);
    mode.value = "force";

    document.getElementById("health").innerHTML = `
      <div class="cards">
        <div class="card"><div class="muted">nodes</div><div>${{payload.counts.memes + payload.counts.memodes + payload.counts.turns + payload.counts.documents + payload.counts.feedback + payload.counts.sessions + 1}}</div></div>
        <div class="card"><div class="muted">edges</div><div>${{payload.health_metrics.edge_count.toFixed(0)}}</div></div>
        <div class="card"><div class="muted">triadic closure</div><div>${{payload.health_metrics.triadic_closure.toFixed(3)}}</div></div>
        <div class="card"><div class="muted">memode coverage</div><div>${{payload.health_metrics.memode_coverage.toFixed(3)}}</div></div>
      </div>`;

    function filteredNodes() {{
      const text = search.value.trim().toLowerCase();
      const session = sessionFilter.value;
      const kind = kindFilter.value;
      const domain = domainFilter.value;
      const source = sourceFilter.value;
      const verdict = verdictFilter.value;
      const time = timeFilter.value.trim();
      return nodes.filter(node => {{
        if (session && node.session_id !== session) return false;
        if (kind && node.kind !== kind) return false;
        if (domain && node.domain !== domain) return false;
        if (source && node.source_kind !== source) return false;
        if (verdict && !(node.verdicts || []).includes(verdict)) return false;
        if (time && !(node.created_at || "").includes(time)) return false;
        if (!text) return true;
        const haystack = [node.label, node.summary, node.provenance, node.profile_name, node.requested_mode].join(" ").toLowerCase();
        return haystack.includes(text);
      }});
    }}

    function coord(node) {{
      const selected = mode.value;
      const source = selected === "force" ? node.render_coords.force : (node.derived_coords[selected] || node.render_coords.force);
      return source || {{ x: 0, y: 0 }};
    }}

    function scale(points) {{
      const xs = points.map(p => p.x);
      const ys = points.map(p => p.y);
      const minX = Math.min(...xs), maxX = Math.max(...xs);
      const minY = Math.min(...ys), maxY = Math.max(...ys);
      return point => {{
        const px = 60 + ((point.x - minX) / Math.max(1e-9, maxX - minX)) * (canvas.width - 120);
        const py = 60 + ((point.y - minY) / Math.max(1e-9, maxY - minY)) * (canvas.height - 120);
        return {{ x: px, y: py }};
      }};
    }}

    function color(node) {{
      if (node.kind === "memode") return "#7de3ff";
      if (node.kind === "feedback") return "#ff7b72";
      if (node.kind === "turn") return "#fff27d";
      if (node.kind === "document") return "#8effa0";
      return "#ffbf66";
    }}

    function draw() {{
      const visibleNodes = filteredNodes();
      const visibleIds = new Set(visibleNodes.map(node => node.id));
      const mapped = visibleNodes.map(node => ({{ node, raw: coord(node) }}));
      if (!mapped.length) {{
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        inspector.textContent = "No nodes match the current filters.";
        return;
      }}
      const transform = scale(mapped.map(item => item.raw));
      mapped.forEach(item => item.screen = transform(item.raw));
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "rgba(255,255,255,0.02)";
      for (let x = 0; x < canvas.width; x += 60) ctx.fillRect(x, 0, 1, canvas.height);
      for (let y = 0; y < canvas.height; y += 60) ctx.fillRect(0, y, canvas.width, 1);
      ctx.strokeStyle = "rgba(255, 191, 102, 0.16)";
      edges.forEach(edge => {{
        if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) return;
        const left = mapped.find(item => item.node.id === edge.source);
        const right = mapped.find(item => item.node.id === edge.target);
        if (!left || !right) return;
        ctx.lineWidth = Math.max(0.5, Math.min(2.5, edge.weight));
        ctx.beginPath();
        ctx.moveTo(left.screen.x, left.screen.y);
        ctx.lineTo(right.screen.x, right.screen.y);
        ctx.stroke();
      }});
      mapped.forEach(item => {{
        ctx.fillStyle = color(item.node);
        const radius = item.node.id === state.pinned?.id ? 8 : 5;
        ctx.beginPath();
        ctx.arc(item.screen.x, item.screen.y, radius, 0, Math.PI * 2);
        ctx.fill();
      }});
      const focused = state.pinned || state.hover;
      if (focused) {{
        inspector.textContent = JSON.stringify(focused, null, 2);
      }}
      canvas._mapped = mapped;
    }}

    function nearest(event) {{
      const rect = canvas.getBoundingClientRect();
      const x = (event.clientX - rect.left) * (canvas.width / rect.width);
      const y = (event.clientY - rect.top) * (canvas.height / rect.height);
      const mapped = canvas._mapped || [];
      let best = null;
      let bestDist = 999999;
      mapped.forEach(item => {{
        const dist = Math.hypot(item.screen.x - x, item.screen.y - y);
        if (dist < bestDist && dist < 12) {{
          bestDist = dist;
          best = item.node;
        }}
      }});
      return best;
    }}

    [mode, search, sessionFilter, kindFilter, domainFilter, sourceFilter, verdictFilter, timeFilter].forEach(el => el.addEventListener("input", draw));
    canvas.addEventListener("mousemove", event => {{ state.hover = nearest(event); draw(); }});
    canvas.addEventListener("mouseleave", () => {{ state.hover = null; draw(); }});
    canvas.addEventListener("click", event => {{ state.pinned = nearest(event); draw(); }});
    draw();
  </script>
</body>
</html>"""

    def _shell_html(self, *, title: str, bootstrap: dict[str, Any]) -> str:
        bootstrap_json = json.dumps(bootstrap, ensure_ascii=True)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="{bootstrap.get('asset_base', './_observatory_app')}/style.css" />
</head>
<body>
  <div id="observatory-root"></div>
  <script>window.__EDEN_BOOTSTRAP__ = {bootstrap_json};</script>
  <script type="module" src="{bootstrap.get('asset_base', './_observatory_app')}/index.js"></script>
</body>
</html>"""

    def _shell_bootstrap(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        initial_surface: str,
        export_manifest_id: str | None = None,
        source_graph_hash: str | None = None,
        projection_method: str | None = None,
    ) -> dict[str, Any]:
        live_api = {
            "status": "/api/status",
            "runtime_status": "/api/runtime/status",
            "runtime_model": "/api/runtime/model",
            "events": f"/api/experiments/{experiment_id}/events",
            "overview": f"/api/experiments/{experiment_id}/overview",
            "graph": f"/api/experiments/{experiment_id}/graph",
            "basin": f"/api/experiments/{experiment_id}/basin",
            "measurements": f"/api/experiments/{experiment_id}/measurement-events",
            "geometry": f"/api/experiments/{experiment_id}/geometry",
            "sessions": f"/api/experiments/{experiment_id}/sessions",
        }
        if session_id:
            live_api["session_turns"] = f"/api/sessions/{session_id}/turns"
            live_api["session_active_set"] = f"/api/sessions/{session_id}/active-set"
            live_api["session_trace"] = f"/api/sessions/{session_id}/trace"
        live_api["tanakh"] = f"/api/experiments/{experiment_id}/tanakh"
        live_api["tanakh_run"] = f"/api/experiments/{experiment_id}/tanakh-run"
        return {
            "mode": "hybrid",
            "asset_base": "./_observatory_app",
            "initial_surface": initial_surface,
            "experiment_id": experiment_id,
            "session_id": session_id,
            "export_manifest_id": export_manifest_id,
            "source_graph_hash": source_graph_hash,
            "projection_method": projection_method,
            "payload_urls": {
                "graph": "./graph_knowledge_base.json",
                "basin": "./behavioral_attractor_basin.json",
                "measurements": "./measurement_events.json",
                "overview": "./observatory_index.json",
                "geometry": "./geometry_diagnostics.json",
                "tanakh": "./tanakh_surface.json",
            },
            "live_api": live_api,
        }

    def export_tanakh_surface(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        out_dir: Path,
        ref: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> tuple[dict[str, str], dict[str, Any]]:
        if self.tanakh_service is None:
            return {}, {}
        paths, payload = self.tanakh_service.export_surface_bundle(
            experiment_id=experiment_id,
            session_id=session_id,
            out_dir=out_dir,
            ref=ref or DEFAULT_TANAKH_REF,
            params=params,
        )
        for artifact_type, path in (
            ("tanakh_surface_json", paths["tanakh_surface_json"]),
            ("tanakh_manifest_json", paths["tanakh_manifest"]),
            ("tanakh_index_json", paths["tanakh_index"]),
            ("tanakh_measurements_json", paths["tanakh_measurements"]),
            ("tanakh_scene_json", paths["tanakh_scene"]),
            ("tanakh_passage_json", paths["tanakh_passage"]),
            ("tanakh_render_validation_json", paths["tanakh_render_validation"]),
            ("tanakh_render_validation_html", paths["tanakh_render_validation_html"]),
        ):
            self.store.record_export_artifact(
                experiment_id=experiment_id,
                session_id=session_id,
                artifact_type=artifact_type,
                path=Path(path),
            )
        self.runtime_log.emit("INFO", "export_tanakh", "Generated Tanakh tool-surface payload.", experiment_id=experiment_id, path=paths["tanakh_surface_json"])
        return paths, payload

    def _graph_html_v12(self, payload: dict[str, Any]) -> str:
        data = json.dumps(payload, ensure_ascii=True)
        template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>EDEN Graph Knowledge Base</title>
  <style>
    :root {
      --bg: #070401;
      --panel: rgba(22, 12, 3, 0.9);
      --panel-strong: rgba(30, 15, 4, 0.96);
      --amber-dim: #b27a34;
      --amber: #ffbf66;
      --amber-hot: #ffd989;
      --gold: #fff0c0;
      --bronze: #6e4419;
      --cyan: #8fe8ff;
      --green: #9dffb0;
      --red: #ff8f78;
      --text: #ffe7bd;
      --muted: #c4924d;
      --grid: rgba(255, 191, 102, 0.08);
      --shadow: 0 0 18px rgba(255, 191, 102, 0.12), 0 0 42px rgba(0, 0, 0, 0.45);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: Menlo, SFMono-Regular, monospace;
      color: var(--text);
      background:
        radial-gradient(circle at 15% 18%, rgba(255, 191, 102, 0.14), transparent 24%),
        radial-gradient(circle at 82% 16%, rgba(255, 214, 138, 0.12), transparent 22%),
        linear-gradient(180deg, #050301 0%, #090603 46%, #120803 100%);
    }
    header {
      padding: 18px 22px 10px;
      border-bottom: 1px solid rgba(255, 191, 102, 0.22);
      display: flex;
      justify-content: space-between;
      gap: 18px;
      flex-wrap: wrap;
      box-shadow: inset 0 -1px 0 rgba(255, 191, 102, 0.08);
    }
    .title {
      font-size: 28px;
      letter-spacing: 0.16em;
      color: var(--amber-hot);
      text-shadow: 0 0 10px rgba(255, 191, 102, 0.3);
    }
    .subtle { color: var(--muted); }
    .chips { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    .chip {
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(255, 191, 102, 0.22);
      background: rgba(255, 191, 102, 0.08);
      color: var(--gold);
      box-shadow: 0 0 8px rgba(255, 191, 102, 0.08);
      font-size: 12px;
    }
    main {
      display: grid;
      grid-template-columns: 318px 1fr 360px;
      gap: 14px;
      padding: 14px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid rgba(255, 191, 102, 0.24);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: var(--shadow);
      position: relative;
    }
    .panel::before {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(255,255,255,0.02), transparent 22%);
      pointer-events: none;
    }
    .panel h2, .panel h3 {
      margin: 0;
      padding: 12px 14px;
      border-bottom: 1px solid rgba(255, 191, 102, 0.16);
      font-size: 13px;
      letter-spacing: 0.09em;
      text-transform: uppercase;
      color: var(--amber-hot);
      background: rgba(255, 191, 102, 0.04);
      text-shadow: 0 0 8px rgba(255, 191, 102, 0.18);
    }
    .body { padding: 12px 14px; }
    .stack { display: grid; gap: 12px; }
    .toolbar, .modebar { display: flex; gap: 8px; flex-wrap: wrap; }
    button, select, input, textarea {
      width: 100%;
      background: rgba(17, 9, 3, 0.96);
      color: var(--text);
      border: 1px solid rgba(255, 191, 102, 0.24);
      border-radius: 10px;
      padding: 9px 10px;
      font: inherit;
      box-shadow: inset 0 0 18px rgba(255, 191, 102, 0.03);
    }
    textarea { min-height: 74px; resize: vertical; }
    button {
      width: auto;
      cursor: pointer;
      transition: 120ms ease;
    }
    button:hover, .modebar button.active {
      border-color: rgba(255, 217, 137, 0.5);
      color: var(--gold);
      box-shadow: 0 0 14px rgba(255, 191, 102, 0.16), inset 0 0 14px rgba(255, 191, 102, 0.06);
    }
    button.primary {
      background: linear-gradient(180deg, rgba(255, 191, 102, 0.16), rgba(255, 191, 102, 0.08));
    }
    .modebar button { min-width: 90px; }
    .row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .graph-shell { position: relative; }
    canvas {
      width: 100%;
      height: 74vh;
      display: block;
      background:
        radial-gradient(circle at center, rgba(255, 191, 102, 0.05), transparent 44%),
        linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0));
    }
    .footer-note {
      padding: 10px 14px 14px;
      border-top: 1px solid rgba(255, 191, 102, 0.12);
      color: var(--muted);
      font-size: 12px;
    }
    .cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .card {
      background: rgba(255, 191, 102, 0.05);
      border: 1px solid rgba(255, 191, 102, 0.14);
      border-radius: 12px;
      padding: 10px;
      box-shadow: inset 0 0 22px rgba(255, 191, 102, 0.025);
    }
    .metric-grid { display: grid; gap: 8px; }
    .metric {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 191, 102, 0.1);
    }
    .metric:last-child { border-bottom: none; }
    .good { color: var(--green); }
    .warn { color: var(--red); }
    .cyan { color: var(--cyan); }
    .history-list {
      display: grid;
      gap: 8px;
      max-height: 220px;
      overflow: auto;
    }
    .history-item {
      padding: 8px;
      border-radius: 10px;
      border: 1px solid rgba(255, 191, 102, 0.14);
      background: rgba(255, 191, 102, 0.035);
    }
    .tiny { font-size: 11px; color: var(--muted); }
    pre {
      margin: 0;
      white-space: pre-wrap;
      font-family: inherit;
      line-height: 1.45;
    }
    @media (max-width: 1260px) {
      main { grid-template-columns: 1fr; }
      canvas { height: 54vh; }
    }
  </style>
</head>
<body>
  <script>let payload = __DATA__;</script>
  <header>
    <div>
      <div class="title">EDEN / GRAPH INSTRUMENT</div>
      <div class="subtle">Observation is measurement-bearing here. Preview first, mutate second, revert explicitly.</div>
    </div>
    <div class="chips">
      <span class="chip">modes: inspect / measure / edit / ablate / compare</span>
      <span class="chip">layout != evidence</span>
      <span class="chip" id="liveStatus">live api: probing</span>
    </div>
  </header>
  <main>
    <section class="panel">
      <h2>Left Rail Filters</h2>
      <div class="body stack">
        <div class="modebar" id="modebar"></div>
        <input id="search" placeholder="search label / summary / provenance" />
        <select id="viewMode"></select>
        <select id="sessionFilter"></select>
        <select id="kindFilter"></select>
        <select id="domainFilter"></select>
        <select id="sourceFilter"></select>
        <select id="verdictFilter"></select>
        <select id="evidenceFilter"></select>
        <input id="timeFilter" placeholder="created_at contains (e.g. 2026-03-06)" />
      </div>
      <h2>Health Cards</h2>
      <div class="body cards" id="healthCards"></div>
      <h2>Selection</h2>
      <div class="body">
        <pre id="selectionSummary">No active selection.</pre>
      </div>
    </section>
    <section class="panel">
      <h2>Graph Surface</h2>
      <div class="body graph-shell">
        <div class="toolbar">
          <button class="primary" id="previewBtn">Preview</button>
          <button class="primary" id="commitBtn">Commit</button>
          <button id="clearSelectionBtn">Clear Selection</button>
        </div>
        <canvas id="canvas" width="1400" height="900"></canvas>
      </div>
      <div class="footer-note">Coordinate mode only changes the rendered surface. Measurement overlays and committed graph edits are stored separately and visibly.</div>
    </section>
    <section class="panel">
      <h2>Precision Drawer</h2>
      <div class="body stack">
        <div class="row2">
          <input id="edgeTypeInput" value="CO_OCCURS_WITH" placeholder="edge type" />
          <input id="weightInput" value="1.0" placeholder="edge weight" />
        </div>
        <div class="row2">
          <input id="confidenceInput" value="0.7" placeholder="confidence" />
          <select id="evidenceLabelSelect"></select>
        </div>
        <input id="operatorLabelInput" value="local_operator" placeholder="operator label" />
        <input id="memodeIdInput" placeholder="memode id (for membership refinement)" />
        <input id="memodeLabelInput" placeholder="known memode label" />
        <input id="memodeDomainInput" value="behavior" placeholder="memode domain" />
        <textarea id="memodeSummaryInput" placeholder="known memode summary / annotation"></textarea>
        <textarea id="rationaleInput" placeholder="rationale / note"></textarea>
        <select id="editActionSelect"></select>
        <select id="ablationRelationSelect"></select>
        <h3>Inspector</h3>
        <pre id="inspector">Hover a node or edge to inspect precise provenance and measurement history.</pre>
        <h3>Preview Diff</h3>
        <pre id="previewPanel">No preview yet.</pre>
        <h3>Measurement Ledger</h3>
        <div class="history-list" id="eventLedger"></div>
      </div>
    </section>
  </main>
  <script>
    const state = {
      mode: "INSPECT",
      hoverNode: null,
      hoverEdge: null,
      pinnedNode: null,
      pinnedEdge: null,
      selectedIds: new Set(),
      preview: null,
      live: false,
      compareView: "spectral",
    };
    const modeBar = document.getElementById("modebar");
    const viewMode = document.getElementById("viewMode");
    const search = document.getElementById("search");
    const sessionFilter = document.getElementById("sessionFilter");
    const kindFilter = document.getElementById("kindFilter");
    const domainFilter = document.getElementById("domainFilter");
    const sourceFilter = document.getElementById("sourceFilter");
    const verdictFilter = document.getElementById("verdictFilter");
    const evidenceFilter = document.getElementById("evidenceFilter");
    const timeFilter = document.getElementById("timeFilter");
    const healthCards = document.getElementById("healthCards");
    const selectionSummary = document.getElementById("selectionSummary");
    const inspector = document.getElementById("inspector");
    const previewPanel = document.getElementById("previewPanel");
    const eventLedger = document.getElementById("eventLedger");
    const liveStatus = document.getElementById("liveStatus");
    const editActionSelect = document.getElementById("editActionSelect");
    const ablationRelationSelect = document.getElementById("ablationRelationSelect");
    const evidenceLabelSelect = document.getElementById("evidenceLabelSelect");
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");
    const modeOptions = payload.interaction_modes || ["INSPECT", "MEASURE", "EDIT", "ABLATE", "COMPARE"];
    const evidenceLabels = Object.keys(payload.evidence_legend || {});

    function optionize(element, label, values) {
      element.innerHTML = `<option value="">${label}</option>` + values.map(v => `<option value="${v}">${v}</option>`).join("");
    }
    function literalOptionize(element, values, selected) {
      element.innerHTML = values.map(v => `<option value="${v}" ${selected === v ? "selected" : ""}>${v}</option>`).join("");
    }
    function refreshModeBar() {
      modeBar.innerHTML = "";
      modeOptions.forEach(mode => {
        const button = document.createElement("button");
        button.textContent = mode;
        if (state.mode === mode) button.classList.add("active");
        button.addEventListener("click", () => {
          state.mode = mode;
          state.preview = null;
          refreshModeBar();
          draw();
          renderInspector();
        });
        modeBar.appendChild(button);
      });
    }
    refreshModeBar();
    optionize(viewMode, "coord mode", Object.keys(payload.view_modes || {}));
    viewMode.value = "force";
    optionize(sessionFilter, "all sessions", payload.filters.sessions || []);
    optionize(kindFilter, "all kinds", payload.filters.kinds || []);
    optionize(domainFilter, "all domains", payload.filters.domains || []);
    optionize(sourceFilter, "all sources", payload.filters.sources || []);
    optionize(verdictFilter, "all verdicts", payload.filters.verdicts || []);
    optionize(evidenceFilter, "all evidence", payload.filters.evidence_labels || evidenceLabels);
    literalOptionize(editActionSelect, ["edge_add", "edge_update", "edge_remove", "memode_assert", "memode_update_membership", "geometry_measurement_run", "motif_annotation"], "edge_add");
    literalOptionize(ablationRelationSelect, ["CO_OCCURS_WITH", "MATERIALIZES_AS_MEMODE", "FED_BACK_BY"], "CO_OCCURS_WITH");
    literalOptionize(evidenceLabelSelect, evidenceLabels, "OPERATOR_ASSERTED");

    function renderHealth() {
      const counts = payload.counts || {};
      const metrics = payload.health_metrics || {};
      const cards = [
        ["nodes", payload.nodes.length],
        ["edges", payload.edges.length],
        ["triadic closure", (metrics.triadic_closure || 0).toFixed(3)],
        ["memode coverage", (metrics.memode_coverage || 0).toFixed(3)],
        ["measurement events", counts.measurement_events || (payload.measurement_events || []).length],
        ["dyad ratio", (metrics.dyad_ratio || 0).toFixed(3)],
      ];
      healthCards.innerHTML = cards.map(([label, value]) => `<div class="card"><div class="tiny">${label}</div><div>${value}</div></div>`).join("");
    }
    renderHealth();

    function filteredNodes() {
      const text = search.value.trim().toLowerCase();
      return (payload.nodes || []).filter(node => {
        if (sessionFilter.value && node.session_id !== sessionFilter.value) return false;
        if (kindFilter.value && node.kind !== kindFilter.value) return false;
        if (domainFilter.value && node.domain !== domainFilter.value) return false;
        if (sourceFilter.value && node.source_kind !== sourceFilter.value) return false;
        if (verdictFilter.value && !(node.verdicts || []).includes(verdictFilter.value)) return false;
        if (evidenceFilter.value && (node.evidence_label || "") !== evidenceFilter.value) return false;
        if (timeFilter.value && !(node.created_at || "").includes(timeFilter.value.trim())) return false;
        if (!text) return true;
        const hay = [node.label, node.summary, node.provenance, node.operator_label].join(" ").toLowerCase();
        return hay.includes(text);
      });
    }
    function coordsFor(node) {
      const mode = viewMode.value || "force";
      if (mode === "force") return node.render_coords.force;
      return (node.derived_coords && node.derived_coords[mode]) || node.render_coords.force;
    }
    function scale(points) {
      const xs = points.map(p => p.x), ys = points.map(p => p.y);
      const minX = Math.min(...xs), maxX = Math.max(...xs);
      const minY = Math.min(...ys), maxY = Math.max(...ys);
      return point => ({
        x: 70 + ((point.x - minX) / Math.max(1e-9, maxX - minX)) * (canvas.width - 140),
        y: 70 + ((point.y - minY) / Math.max(1e-9, maxY - minY)) * (canvas.height - 140),
      });
    }
    function visibleEdges(visibleIds) {
      return (payload.edges || []).filter(edge => visibleIds.has(edge.source) && visibleIds.has(edge.target));
    }
    function nodeColor(node) {
      if ((payload.latest_active_ids || []).includes(node.id)) return "#fff0c0";
      if (node.kind === "memode") return "#8fe8ff";
      if (node.kind === "feedback") return "#ff8f78";
      if (node.kind === "turn") return "#ffe18d";
      if (node.kind === "document") return "#9dffb0";
      return "#ffbf66";
    }
    function edgeStroke(edge) {
      if (edge.assertion_origin === "operator_asserted" || edge.assertion_origin === "operator_refined") return "rgba(255, 220, 146, 0.75)";
      if (edge.evidence_label === "OBSERVED") return "rgba(157, 255, 176, 0.48)";
      return "rgba(255, 191, 102, 0.18)";
    }
    function draw() {
      const visibleNodes = filteredNodes();
      const visibleIds = new Set(visibleNodes.map(node => node.id));
      const mapped = visibleNodes.map(node => ({ node, raw: coordsFor(node) || { x: 0, y: 0 } }));
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!mapped.length) {
        inspector.textContent = "No nodes match the current filters.";
        eventLedger.innerHTML = "";
        return;
      }
      const projector = scale(mapped.map(item => item.raw));
      mapped.forEach(item => item.screen = projector(item.raw));
      for (let x = 0; x < canvas.width; x += 58) {
        ctx.fillStyle = "rgba(255, 191, 102, 0.05)";
        ctx.fillRect(x, 0, 1, canvas.height);
      }
      for (let y = 0; y < canvas.height; y += 58) {
        ctx.fillStyle = "rgba(255, 191, 102, 0.05)";
        ctx.fillRect(0, y, canvas.width, 1);
      }
      const edgeSegments = [];
      visibleEdges(visibleIds).forEach(edge => {
        const left = mapped.find(item => item.node.id === edge.source);
        const right = mapped.find(item => item.node.id === edge.target);
        if (!left || !right) return;
        edgeSegments.push({ edge, left: left.screen, right: right.screen });
        ctx.save();
        ctx.strokeStyle = edgeStroke(edge);
        ctx.lineWidth = Math.max(0.8, Math.min(3.4, Number(edge.weight || 1)));
        ctx.shadowBlur = edge.assertion_origin === "operator_asserted" ? 12 : 5;
        ctx.shadowColor = edge.assertion_origin === "operator_asserted" ? "rgba(255, 220, 146, 0.55)" : "rgba(255, 191, 102, 0.15)";
        ctx.beginPath();
        ctx.moveTo(left.screen.x, left.screen.y);
        ctx.lineTo(right.screen.x, right.screen.y);
        ctx.stroke();
        ctx.restore();
      });
      mapped.forEach(item => {
        const selected = state.selectedIds.has(item.node.id);
        const pinned = state.pinnedNode && state.pinnedNode.id === item.node.id;
        const activeGlow = (item.node.recent_active_set_presence || 0) > 0;
        const radius = pinned ? 10 : selected ? 8 : 5.8;
        ctx.save();
        ctx.fillStyle = nodeColor(item.node);
        ctx.shadowBlur = selected || pinned ? 20 : activeGlow ? 12 : 6;
        ctx.shadowColor = selected || pinned ? "rgba(255, 217, 137, 0.62)" : "rgba(255, 191, 102, 0.22)";
        ctx.beginPath();
        ctx.arc(item.screen.x, item.screen.y, radius, 0, Math.PI * 2);
        ctx.fill();
        if (selected || pinned) {
          ctx.strokeStyle = "rgba(255, 240, 192, 0.9)";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(item.screen.x, item.screen.y, radius + 6, 0, Math.PI * 2);
          ctx.stroke();
        }
        ctx.restore();
      });
      canvas._mapped = mapped;
      canvas._edgeSegments = edgeSegments;
      renderInspector();
      renderSelection();
      renderLedger();
    }
    function nearestNode(event) {
      const rect = canvas.getBoundingClientRect();
      const x = (event.clientX - rect.left) * (canvas.width / rect.width);
      const y = (event.clientY - rect.top) * (canvas.height / rect.height);
      let best = null, bestDist = 999999;
      (canvas._mapped || []).forEach(item => {
        const dist = Math.hypot(item.screen.x - x, item.screen.y - y);
        if (dist < bestDist && dist < 14) {
          bestDist = dist;
          best = item.node;
        }
      });
      return best;
    }
    function pointToSegmentDistance(px, py, ax, ay, bx, by) {
      const dx = bx - ax, dy = by - ay;
      const length2 = dx * dx + dy * dy;
      const t = length2 === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / length2));
      const x = ax + t * dx, y = ay + t * dy;
      return Math.hypot(px - x, py - y);
    }
    function nearestEdge(event) {
      const rect = canvas.getBoundingClientRect();
      const x = (event.clientX - rect.left) * (canvas.width / rect.width);
      const y = (event.clientY - rect.top) * (canvas.height / rect.height);
      let best = null, bestDist = 999999;
      (canvas._edgeSegments || []).forEach(segment => {
        const dist = pointToSegmentDistance(x, y, segment.left.x, segment.left.y, segment.right.x, segment.right.y);
        if (dist < bestDist && dist < 8) {
          bestDist = dist;
          best = segment.edge;
        }
      });
      return best;
    }
    function renderInspector() {
      const focus = state.pinnedEdge || state.pinnedNode || state.hoverEdge || state.hoverNode;
      if (!focus) {
        inspector.textContent = "Hover a node or edge to inspect precise provenance and measurement history.";
        return;
      }
      inspector.textContent = JSON.stringify(focus, null, 2);
    }
    function renderSelection() {
      const selected = [...state.selectedIds].map(id => (payload.nodes || []).find(node => node.id === id)).filter(Boolean);
      selectionSummary.textContent = selected.length
        ? JSON.stringify(selected.map(node => ({ id: node.id, kind: node.kind, label: node.label, community: node.community })), null, 2)
        : "No active selection.";
    }
    function renderPreview() {
      if (!state.preview) {
        previewPanel.textContent = "No preview yet.";
        return;
      }
      const delta = state.preview.global_metrics?.delta || {};
      const local = state.preview.local_metrics?.delta || {};
      previewPanel.textContent = JSON.stringify({
        action_type: state.preview.action_type,
        measurement_only: state.preview.measurement_only,
        topology_change: state.preview.topology_change,
        global_delta: delta,
        local_delta: local,
      }, null, 2);
    }
    function renderLedger() {
      const rows = [...(payload.measurement_events || [])].sort((a, b) => (a.created_at < b.created_at ? 1 : -1)).slice(0, 12);
      eventLedger.innerHTML = rows.map(row => `
        <div class="history-item">
          <div><strong>${row.action_type}</strong> <span class="tiny">${row.evidence_label} · ${row.created_at}</span></div>
          <div class="tiny">${row.summary || ""}</div>
          <div class="toolbar" style="margin-top:8px;">
            ${state.live ? `<button data-revert="${row.id}">revert</button>` : ``}
          </div>
        </div>
      `).join("");
      [...eventLedger.querySelectorAll("[data-revert]")].forEach(button => {
        button.addEventListener("click", async () => {
          if (!state.live) return;
          const res = await fetch(payload.live_api.revert, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ event_id: button.dataset.revert, session_id: payload.session_id }),
          });
          const data = await res.json();
          if (!res.ok) {
            previewPanel.textContent = JSON.stringify(data, null, 2);
            return;
          }
          payload = data.payload.graph;
          payload.measurement_events = data.payload.measurements.events;
          renderHealth();
          state.preview = data;
          renderPreview();
          draw();
        });
      });
    }
    function buildAction() {
      const ids = [...state.selectedIds];
      const actionType = state.mode === "MEASURE" ? "geometry_measurement_run"
        : state.mode === "ABLATE" ? "ablation_measurement_run"
        : state.mode === "COMPARE" ? "geometry_measurement_run"
        : editActionSelect.value;
        const action = {
          action_type: actionType,
          selected_node_ids: ids,
          source_id: state.pinnedEdge ? state.pinnedEdge.source : (ids[0] || null),
          target_id: state.pinnedEdge ? state.pinnedEdge.target : (ids[1] || null),
          current_edge_type: state.pinnedEdge ? state.pinnedEdge.type : document.getElementById("edgeTypeInput").value.trim(),
          edge_type: document.getElementById("edgeTypeInput").value.trim(),
          weight: Number(document.getElementById("weightInput").value || "1"),
        confidence: Number(document.getElementById("confidenceInput").value || "0.7"),
        operator_label: document.getElementById("operatorLabelInput").value.trim() || "local_operator",
        evidence_label: evidenceLabelSelect.value || "OPERATOR_ASSERTED",
        measurement_method: state.mode === "ABLATE" ? "local_ablation_preview" : "local_geometry_preview",
        rationale: document.getElementById("rationaleInput").value.trim(),
        label: document.getElementById("memodeLabelInput").value.trim(),
        summary: document.getElementById("memodeSummaryInput").value.trim(),
        domain: document.getElementById("memodeDomainInput").value.trim() || "behavior",
        memode_id: document.getElementById("memodeIdInput").value.trim(),
        member_ids: ids,
        mask_relation_type: document.getElementById("ablationRelationSelect").value,
      };
      return action;
    }
    async function runPreview() {
      if (!state.live) {
        previewPanel.textContent = "Live API unavailable. Start the local observatory server to enable preview / commit / revert.";
        return;
      }
      const response = await fetch(payload.live_api.preview, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: payload.session_id, action: buildAction() }),
      });
      const data = await response.json();
      state.preview = data;
      renderPreview();
    }
    async function commitAction() {
      if (!state.live) {
        previewPanel.textContent = "Live API unavailable. Commit requires the local observatory server.";
        return;
      }
      const response = await fetch(payload.live_api.commit, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: payload.session_id, action: buildAction() }),
      });
      const data = await response.json();
      if (!response.ok) {
        previewPanel.textContent = JSON.stringify(data, null, 2);
        return;
      }
      payload = data.payload.graph;
      payload.measurement_events = data.payload.measurements.events;
      state.preview = data.preview;
      renderHealth();
      renderPreview();
      draw();
    }
    async function detectLive() {
      try {
        const response = await fetch("/api/status");
        const data = await response.json();
        state.live = Boolean(data.ok && data.status && data.status.capabilities && data.status.capabilities.preview);
      } catch (_error) {
        state.live = false;
      }
      liveStatus.textContent = state.live ? "live api: online" : "live api: static export mode";
    }
    [viewMode, search, sessionFilter, kindFilter, domainFilter, sourceFilter, verdictFilter, evidenceFilter, timeFilter].forEach(el => el.addEventListener("input", draw));
    document.getElementById("previewBtn").addEventListener("click", runPreview);
    document.getElementById("commitBtn").addEventListener("click", commitAction);
    document.getElementById("clearSelectionBtn").addEventListener("click", () => { state.selectedIds = new Set(); state.preview = null; draw(); renderPreview(); });
    canvas.addEventListener("mousemove", event => {
      state.hoverNode = nearestNode(event);
      state.hoverEdge = state.hoverNode ? null : nearestEdge(event);
      renderInspector();
    });
    canvas.addEventListener("mouseleave", () => {
      state.hoverNode = null;
      state.hoverEdge = null;
      renderInspector();
    });
    canvas.addEventListener("click", event => {
      if (state.mode === "INSPECT") {
        state.pinnedNode = nearestNode(event);
        state.pinnedEdge = state.pinnedNode ? null : nearestEdge(event);
      } else {
        const node = nearestNode(event);
        if (!node) return;
        if (!event.shiftKey) {
          state.selectedIds = new Set(state.selectedIds.has(node.id) && state.selectedIds.size === 1 ? [] : [node.id]);
        } else {
          if (state.selectedIds.has(node.id)) state.selectedIds.delete(node.id);
          else state.selectedIds.add(node.id);
        }
      }
      draw();
    });
    detectLive();
    renderPreview();
    draw();
  </script>
</body>
</html>""";
        return template.replace("__DATA__", data)

    def _geometry_html_v12(self, payload: dict[str, Any]) -> str:
        data = json.dumps(payload, ensure_ascii=True)
        template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>EDEN Geometry Lab</title>
  <style>
    :root {
      --bg: #060301;
      --panel: rgba(20, 11, 3, 0.92);
      --amber: #ffbf66;
      --amber-hot: #ffe09c;
      --text: #ffe8c0;
      --muted: #c5924a;
      --cyan: #8fe8ff;
      --green: #9dffb0;
      --rose: #ffb0c8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: Menlo, SFMono-Regular, monospace;
      background:
        radial-gradient(circle at 18% 18%, rgba(255,191,102,0.14), transparent 22%),
        radial-gradient(circle at 80% 20%, rgba(143,232,255,0.12), transparent 20%),
        linear-gradient(180deg, #040200, #0e0602 54%, #130803 100%);
      color: var(--text);
    }
    header {
      padding: 18px 22px 12px;
      border-bottom: 1px solid rgba(255,191,102,0.22);
    }
    .title {
      font-size: 28px;
      letter-spacing: 0.16em;
      color: var(--amber-hot);
      text-shadow: 0 0 10px rgba(255,191,102,0.3);
    }
    main {
      display: grid;
      grid-template-columns: 320px 1fr 360px;
      gap: 14px;
      padding: 14px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid rgba(255,191,102,0.22);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 0 16px rgba(255,191,102,0.1), 0 0 38px rgba(0,0,0,0.42);
    }
    .panel h2 { margin: 0; padding: 12px 14px; border-bottom: 1px solid rgba(255,191,102,0.14); font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--amber-hot); }
    .body { padding: 12px 14px; }
    select, textarea, input {
      width: 100%;
      padding: 9px 10px;
      margin-bottom: 10px;
      background: rgba(15,8,2,0.95);
      border: 1px solid rgba(255,191,102,0.22);
      border-radius: 10px;
      color: var(--text);
      font: inherit;
    }
    textarea { min-height: 84px; resize: vertical; }
    button {
      width: auto;
      padding: 9px 12px;
      background: rgba(255,191,102,0.08);
      border: 1px solid rgba(255,191,102,0.22);
      border-radius: 10px;
      color: var(--text);
      cursor: pointer;
      margin-right: 8px;
    }
    .metric { padding: 8px 0; border-bottom: 1px solid rgba(255,191,102,0.1); display: flex; justify-content: space-between; gap: 12px; }
    .metric:last-child { border-bottom: none; }
    .obs { color: var(--green); }
    .drv { color: var(--cyan); }
    .spc { color: var(--rose); }
    pre { margin: 0; white-space: pre-wrap; }
    .tiny { color: var(--muted); font-size: 12px; }
    @media (max-width: 1200px) { main { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <script>let payload = __DATA__;</script>
  <header>
    <div class="title">EDEN / GEOMETRY LAB</div>
    <div class="tiny">OBSERVED metrics come from topology and recurrence counts. DERIVED metrics come from transforms and ordered-structure proxies. SPECULATIVE stays outside scoring.</div>
  </header>
  <main>
    <section class="panel">
      <h2>Controls</h2>
      <div class="body">
        <select id="reportSelect"></select>
        <textarea id="selectionInput" placeholder="optional live measurement selection: comma-separated node ids"></textarea>
        <button id="measureSelectionBtn">Measure Selection</button>
        <div class="tiny" id="liveLabel">live api: probing</div>
      </div>
    </section>
    <section class="panel">
      <h2>Report</h2>
      <div class="body">
        <div id="metrics"></div>
      </div>
    </section>
    <section class="panel">
      <h2>Ablations + Preview</h2>
      <div class="body">
        <pre id="ablation"></pre>
      </div>
    </section>
  </main>
  <script>
    const metricsEl = document.getElementById("metrics");
    const ablationEl = document.getElementById("ablation");
    const reportSelect = document.getElementById("reportSelect");
    const selectionInput = document.getElementById("selectionInput");
    const measureSelectionBtn = document.getElementById("measureSelectionBtn");
    const liveLabel = document.getElementById("liveLabel");
    const reports = {
      full_graph: { kind: "full", payload: payload.full_graph },
      ...Object.fromEntries(Object.entries(payload.slices || {}).map(([key, value]) => [key, { kind: "slice", payload: value }])),
      ...Object.fromEntries(Object.entries(payload.local_reports || {}).map(([key, value]) => [key, { kind: "local", payload: value }])),
    };
    let live = false;
    reportSelect.innerHTML = Object.keys(reports).map(name => `<option value="${name}">${name}</option>`).join("");
    function renderReport() {
      const selected = reports[reportSelect.value] || reports.full_graph;
      const metrics = selected.kind === "full"
        ? selected.payload.metrics.metrics
        : selected.kind === "local"
          ? selected.payload.metrics.metrics
          : selected.payload.metrics;
      metricsEl.innerHTML = Object.entries(metrics || {}).map(([name, metric]) => {
        const label = metric.label === "OBSERVED" ? "obs" : metric.label === "DERIVED" ? "drv" : "spc";
        return `<div class="metric"><span>${name} <span class="${label}">${metric.label}</span></span><span>${Number(metric.score || 0).toFixed(4)}</span></div>`;
      }).join("");
      const ablations = selected.kind === "full" ? (selected.payload.ablations || []) : [];
      ablationEl.textContent = JSON.stringify({
        report: reportSelect.value,
        counts: selected.payload.counts || selected.payload.metrics?.counts || {},
        ablations,
      }, null, 2);
    }
    async function detectLive() {
      try {
        const response = await fetch("/api/status");
        const data = await response.json();
        live = Boolean(data.ok && data.status && data.status.capabilities && data.status.capabilities.preview);
      } catch (_error) {
        live = false;
      }
      liveLabel.textContent = live ? "live api: online" : "live api: static export mode";
    }
    measureSelectionBtn.addEventListener("click", async () => {
      if (!live) {
        ablationEl.textContent = "Live API unavailable. Start the observatory server for exact selection measurement.";
        return;
      }
      const selectedIds = selectionInput.value.split(",").map(item => item.trim()).filter(Boolean);
      const response = await fetch(`/api/experiments/${payload.experiment_id}/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: payload.session_id,
          action: {
            action_type: "geometry_measurement_run",
            selected_node_ids: selectedIds,
            rationale: "live geometry measurement",
            evidence_label: "DERIVED",
            operator_label: "local_operator",
            confidence: 0.8,
          },
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        ablationEl.textContent = JSON.stringify(data, null, 2);
        return;
      }
      ablationEl.textContent = JSON.stringify(data.local_metrics, null, 2);
    });
    reportSelect.addEventListener("input", renderReport);
    detectLive();
    renderReport();
  </script>
</body>
</html>""";
        return template.replace("__DATA__", data)

    def _measurement_html(self, payload: dict[str, Any]) -> str:
        data = json.dumps(payload, ensure_ascii=True)
        template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>EDEN Measurement Ledger</title>
  <style>
    body { margin: 0; min-height: 100vh; font-family: Menlo, SFMono-Regular, monospace; background: linear-gradient(180deg, #050301, #110702); color: #ffe8c0; padding: 18px; }
    .title { font-size: 28px; letter-spacing: 0.16em; color: #ffe09c; }
    table { width: 100%; border-collapse: collapse; margin-top: 18px; background: rgba(20, 11, 3, 0.9); border: 1px solid rgba(255,191,102,0.2); }
    th, td { padding: 10px; border-bottom: 1px solid rgba(255,191,102,0.12); text-align: left; vertical-align: top; }
    th { color: #ffbf66; }
    .tiny { color: #c5924a; }
  </style>
</head>
<body>
  <script>const payload = __DATA__;</script>
  <div class="title">EDEN / MEASUREMENT LEDGER</div>
  <div class="tiny">Every observatory-originated edit or committed measurement is recorded here with provenance.</div>
  <table>
    <thead>
      <tr><th>created_at</th><th>action</th><th>evidence</th><th>confidence</th><th>summary</th><th>revert</th></tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>
  <script>
    document.getElementById("rows").innerHTML = (payload.events || []).slice().reverse().map(row => `
      <tr>
        <td>${row.created_at}</td>
        <td>${row.action_type}</td>
        <td>${row.evidence_label}</td>
        <td>${Number(row.confidence || 0).toFixed(2)}</td>
        <td>${row.summary || ""}</td>
        <td>${row.reverted_from_event_id || ""}</td>
      </tr>
    `).join("");
  </script>
</body>
</html>""";
        return template.replace("__DATA__", data)

    def _index_html_v12(self, payload: dict[str, Any]) -> str:
        graph_name = Path(payload["artifacts"]["graph"]["graph_html"]).name
        basin_name = Path(payload["artifacts"]["basin"]["basin_html"]).name
        geometry_name = Path(payload["artifacts"]["geometry"]["geometry_html"]).name
        measurement_name = Path(payload["artifacts"]["measurement"]["measurement_html"]).name
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>EDEN Observatory Index</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Menlo, SFMono-Regular, monospace;
      color: #ffe8c0;
      background:
        radial-gradient(circle at 14% 18%, rgba(255,191,102,0.16), transparent 22%),
        radial-gradient(circle at 84% 16%, rgba(143,232,255,0.10), transparent 20%),
        linear-gradient(180deg, #040200, #0f0602 60%, #140903 100%);
      padding: 18px;
    }}
    .title {{ font-size: 28px; letter-spacing: 0.16em; color: #ffe09c; text-shadow: 0 0 10px rgba(255,191,102,0.3); }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 18px; }}
    .card {{
      background: rgba(20, 11, 3, 0.92);
      border: 1px solid rgba(255,191,102,0.22);
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 0 16px rgba(255,191,102,0.08), 0 0 36px rgba(0,0,0,0.38);
    }}
    .tiny {{ color: #c5924a; font-size: 12px; }}
    a {{ color: #8fe8ff; }}
    @media (max-width: 1200px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="title">EDEN / OBSERVATORY INDEX</div>
  <div class="tiny">experiment={payload["experiment_id"]} generated_at={payload["generated_at"]} nodes={payload["summary"]["nodes"]} edges={payload["summary"]["edges"]} measurements={payload["summary"]["measurement_events"]}</div>
  <div class="grid">
    <div class="card">
      <h3>Graph Instrument</h3>
      <div class="tiny">inspect / measure / edit / ablate / compare</div>
      <p>Live-editable graph surface with provenance-aware selection, preview, commit, and revert flow.</p>
      <a href="{graph_name}">open graph instrument</a>
    </div>
    <div class="card">
      <h3>Behavioral Basin</h3>
      <div class="tiny">turns={payload["summary"]["turns"]} sessions={payload["summary"]["sessions"]}</div>
      <p>Attractor trajectory with inference-circumstance overlays, recurrence, and phase markers.</p>
      <a href="{basin_name}">open basin artifact</a>
    </div>
    <div class="card">
      <h3>Geometry Lab</h3>
      <div class="tiny">global, slice, and local motif geometry</div>
      <p>Observed and derived metrics, ablations, and live exact-selection measurement when the local API is available.</p>
      <a href="{geometry_name}">open geometry lab</a>
    </div>
    <div class="card">
      <h3>Measurement Ledger</h3>
      <div class="tiny">all observatory-originated events</div>
      <p>Measurement-bearing event history for graph edits, memode assertions, ablations, annotations, and reverts.</p>
      <a href="{measurement_name}">open measurement ledger</a>
    </div>
  </div>
</body>
</html>"""

    def _basin_html(self, payload: dict[str, Any]) -> str:
        data = json.dumps(payload, ensure_ascii=True)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>EDEN Behavioral Attractor Basin</title>
  <style>
    body {{
      margin: 0;
      font-family: Menlo, SFMono-Regular, monospace;
      background: radial-gradient(circle at 25% 25%, rgba(255, 191, 102, 0.18), transparent 30%), linear-gradient(180deg, #060403, #110702);
      color: #ffe2af;
    }}
    header, section {{
      padding: 14px 18px;
    }}
    header {{
      border-bottom: 1px solid rgba(255, 191, 102, 0.22);
      display: flex;
      justify-content: space-between;
      gap: 18px;
      flex-wrap: wrap;
    }}
    main {{
      display: grid;
      grid-template-columns: 1fr 320px;
      gap: 14px;
      padding: 14px;
    }}
    .panel {{
      background: rgba(27, 15, 4, 0.9);
      border: 1px solid rgba(255, 191, 102, 0.22);
      border-radius: 12px;
    }}
    canvas {{
      width: 100%;
      height: 72vh;
      display: block;
    }}
    .body {{
      padding: 12px 14px;
    }}
    select {{
      width: 100%;
      background: #120b04;
      color: #ffe2af;
      border: 1px solid rgba(255, 191, 102, 0.28);
      border-radius: 10px;
      padding: 8px 10px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }}
    .card {{
      background: rgba(255, 191, 102, 0.05);
      border: 1px solid rgba(255, 191, 102, 0.14);
      border-radius: 10px;
      padding: 10px;
    }}
    pre {{
      white-space: pre-wrap;
      margin: 0;
    }}
    @media (max-width: 1050px) {{
      main {{ grid-template-columns: 1fr; }}
      canvas {{ height: 50vh; }}
    }}
  </style>
</head>
<body>
  <script>const payload = {data};</script>
  <header>
    <div>
      <div style="font-size: 28px; letter-spacing: 0.14em; color: #ffbf66;">EDEN / BEHAVIORAL ATTRACTOR BASIN</div>
      <div>Projection method: SVD on real turn features. Explained variance top2: ${{(payload.projection.explained_variance_top2 || 0).toFixed(3)}}</div>
    </div>
    <div class="cards" style="min-width: 340px;">
      <div class="card"><div>turns</div><strong>${{payload.turn_count}}</strong></div>
      <div class="card"><div>sessions</div><strong>${{payload.session_count}}</strong></div>
      <div class="card"><div>phase transitions</div><strong>${{payload.continuity.phase_transition_count}}</strong></div>
    </div>
  </header>
  <main>
    <section class="panel">
      <div class="body"><canvas id="canvas" width="1200" height="760"></canvas></div>
    </section>
    <section class="panel">
      <div class="body">
        <select id="sessionFilter"></select>
        <pre id="inspector">Hover a turn to inspect inference circumstances, budget pressure, recurrence, and membrane markers.</pre>
      </div>
    </section>
  </main>
  <script>
    const turns = payload.turns;
    const sessionFilter = document.getElementById("sessionFilter");
    const sessions = [...new Set(turns.map(turn => turn.session_id))].sort();
    sessionFilter.innerHTML = `<option value="">all sessions</option>` + sessions.map(s => `<option value="${{s}}">${{s}}</option>`).join("");
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");
    const inspector = document.getElementById("inspector");
    const state = {{ hover: null }};
    function color(turn) {{
      if (turn.budget_pressure === "HIGH") return "#ff7b72";
      if (turn.phase_transition) return "#7de3ff";
      if ((turn.feedback_verdicts || []).includes("accept")) return "#8effa0";
      return "#ffbf66";
    }}
    function filtered() {{
      return turns.filter(turn => !sessionFilter.value || turn.session_id === sessionFilter.value);
    }}
    function scale(values, key, size, pad) {{
      const min = Math.min(...values.map(item => item[key]));
      const max = Math.max(...values.map(item => item[key]));
      return value => pad + ((value - min) / Math.max(1e-9, max - min)) * (size - pad * 2);
    }}
    function draw() {{
      const visible = filtered();
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!visible.length) return;
      const scaleX = scale(visible, "x", canvas.width, 60);
      const scaleY = scale(visible, "y", canvas.height, 60);
      ctx.strokeStyle = "rgba(255, 191, 102, 0.26)";
      visible.forEach((turn, index) => {{
        if (!index) return;
        const prev = visible[index - 1];
        ctx.beginPath();
        ctx.moveTo(scaleX(prev.x), scaleY(prev.y));
        ctx.lineTo(scaleX(turn.x), scaleY(turn.y));
        ctx.stroke();
      }});
      visible.forEach(turn => {{
        turn._screen = {{ x: scaleX(turn.x), y: scaleY(turn.y) }};
        ctx.fillStyle = color(turn);
        ctx.beginPath();
        ctx.arc(turn._screen.x, turn._screen.y, turn.phase_transition ? 8 : 6, 0, Math.PI * 2);
        ctx.fill();
      }});
      if (state.hover) inspector.textContent = JSON.stringify(state.hover, null, 2);
    }}
    function nearest(event) {{
      const rect = canvas.getBoundingClientRect();
      const x = (event.clientX - rect.left) * (canvas.width / rect.width);
      const y = (event.clientY - rect.top) * (canvas.height / rect.height);
      let best = null;
      let bestDist = 999999;
      filtered().forEach(turn => {{
        if (!turn._screen) return;
        const dist = Math.hypot(turn._screen.x - x, turn._screen.y - y);
        if (dist < bestDist && dist < 14) {{
          bestDist = dist;
          best = turn;
        }}
      }});
      return best;
    }}
    sessionFilter.addEventListener("input", draw);
    canvas.addEventListener("mousemove", event => {{ state.hover = nearest(event); draw(); }});
    canvas.addEventListener("mouseleave", () => {{ state.hover = null; draw(); }});
    draw();
  </script>
</body>
</html>"""

    def _geometry_html(self, payload: dict[str, Any]) -> str:
        data = json.dumps(payload, ensure_ascii=True)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>EDEN Geometry Lab</title>
  <style>
    body {{
      margin: 0;
      font-family: Menlo, SFMono-Regular, monospace;
      background: radial-gradient(circle at 20% 20%, rgba(125, 227, 255, 0.12), transparent 24%), radial-gradient(circle at 80% 30%, rgba(255, 191, 102, 0.12), transparent 28%), linear-gradient(180deg, #060403, #100804);
      color: #ffe2af;
    }}
    header, main {{
      padding: 14px 18px;
    }}
    main {{
      display: grid;
      grid-template-columns: 320px 1fr 360px;
      gap: 14px;
    }}
    .panel {{
      background: rgba(27, 15, 4, 0.9);
      border: 1px solid rgba(255, 191, 102, 0.22);
      border-radius: 12px;
      overflow: hidden;
    }}
    .panel h2 {{
      margin: 0;
      padding: 12px 14px;
      border-bottom: 1px solid rgba(255, 191, 102, 0.18);
      font-size: 14px;
      color: #ffbf66;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .body {{
      padding: 12px 14px;
    }}
    select, input[type=range] {{
      width: 100%;
      background: #120b04;
      color: #ffe2af;
      border: 1px solid rgba(255, 191, 102, 0.28);
      border-radius: 10px;
      padding: 8px 10px;
      margin-bottom: 10px;
    }}
    canvas {{
      width: 100%;
      height: 70vh;
      display: block;
    }}
    .metric {{
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 191, 102, 0.12);
    }}
    .obs {{ color: #8effa0; }}
    .drv {{ color: #7de3ff; }}
    .spc {{ color: #ff9ec0; }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
    }}
    @media (max-width: 1100px) {{
      main {{ grid-template-columns: 1fr; }}
      canvas {{ height: 50vh; }}
    }}
  </style>
</head>
<body>
  <script>const payload = {data};</script>
  <header>
    <div style="font-size: 28px; letter-spacing: 0.14em; color: #ffbf66;">EDEN / GEOMETRY LAB</div>
    <div>All geometry labels are evidence-scoped. OBSERVED is direct graph computation. DERIVED is transform-based. SPECULATIVE is not used in any current score.</div>
  </header>
  <main>
    <section class="panel">
      <h2>Controls</h2>
      <div class="body">
        <select id="sliceSelect"></select>
        <select id="coordSelect"></select>
        <label>minimum metric score</label>
        <input id="threshold" type="range" min="0" max="1" step="0.05" value="0" />
        <div id="legend">
          <div><span class="obs">OBSERVED</span> direct graph evidence</div>
          <div><span class="drv">DERIVED</span> projection / symmetry proxy</div>
          <div><span class="spc">SPECULATIVE</span> operator hypothesis only</div>
        </div>
      </div>
    </section>
    <section class="panel">
      <h2>Slice View</h2>
      <div class="body"><canvas id="canvas" width="1200" height="760"></canvas></div>
    </section>
    <section class="panel">
      <h2>Metrics + Ablations</h2>
      <div class="body">
        <div id="metrics"></div>
        <pre id="ablation"></pre>
      </div>
    </section>
  </main>
  <script>
    const nodes = payload.nodes;
    const edges = payload.edges;
    const slices = payload.slices;
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");
    const sliceSelect = document.getElementById("sliceSelect");
    const coordSelect = document.getElementById("coordSelect");
    const threshold = document.getElementById("threshold");
    const metricsEl = document.getElementById("metrics");
    const ablationEl = document.getElementById("ablation");
    sliceSelect.innerHTML = Object.keys(slices).map(name => `<option value="${{name}}">${{name}}</option>`).join("");
    coordSelect.innerHTML = Object.keys(payload.coordinate_methods).map(name => `<option value="${{name}}">${{name}}</option>`).join("");
    coordSelect.value = "spectral";

    function sliceNodeIds() {{
      const name = sliceSelect.value;
      if (name === "full_graph") return new Set(nodes.map(node => node.id));
      if (name === "current_session") return new Set(nodes.filter(node => node.session_id === payload.session_id || node.id === payload.session_id).map(node => node.id));
      if (name === "current_active_set") return new Set(nodes.filter(node => (node.source_kind === "feedback" || node.kind === "memode" || node.kind === "meme") && node.session_id === payload.session_id).map(node => node.id));
      if (name.startsWith("verdict_")) {{
        const verdict = name.replace("verdict_", "");
        return new Set(nodes.filter(node => (node.verdicts || []).includes(verdict)).map(node => node.id));
      }}
      return new Set(nodes.map(node => node.id));
    }}

    function coord(node) {{
      const selected = coordSelect.value;
      return (node.derived_coords[selected] || node.render_coords.force || {{ x: 0, y: 0 }});
    }}

    function scale(points) {{
      const xs = points.map(p => p.x);
      const ys = points.map(p => p.y);
      const minX = Math.min(...xs), maxX = Math.max(...xs);
      const minY = Math.min(...ys), maxY = Math.max(...ys);
      return point => ({{
        x: 60 + ((point.x - minX) / Math.max(1e-9, maxX - minX)) * (canvas.width - 120),
        y: 60 + ((point.y - minY) / Math.max(1e-9, maxY - minY)) * (canvas.height - 120),
      }});
    }}

    function color(node) {{
      if (node.cluster_id === -1) return "#ffbf66";
      const palette = ["#ffbf66", "#7de3ff", "#8effa0", "#ff9ec0", "#fff27d", "#b39dff"];
      return palette[node.cluster_id % palette.length];
    }}

    function draw() {{
      const ids = sliceNodeIds();
      const visible = nodes.filter(node => ids.has(node.id));
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!visible.length) return;
      const mapped = visible.map(node => ({{ node, raw: coord(node) }}));
      const transform = scale(mapped.map(item => item.raw));
      mapped.forEach(item => item.screen = transform(item.raw));
      ctx.strokeStyle = "rgba(255, 191, 102, 0.16)";
      edges.forEach(edge => {{
        if (!ids.has(edge.source) || !ids.has(edge.target)) return;
        const left = mapped.find(item => item.node.id === edge.source);
        const right = mapped.find(item => item.node.id === edge.target);
        if (!left || !right) return;
        ctx.lineWidth = Math.max(0.5, Math.min(2.5, edge.weight));
        ctx.beginPath();
        ctx.moveTo(left.screen.x, left.screen.y);
        ctx.lineTo(right.screen.x, right.screen.y);
        ctx.stroke();
      }});
      mapped.forEach(item => {{
        ctx.fillStyle = color(item.node);
        ctx.beginPath();
        ctx.arc(item.screen.x, item.screen.y, item.node.kind === "memode" ? 8 : 6, 0, Math.PI * 2);
        ctx.fill();
      }});
    }}

    function renderMetrics() {{
      const slice = slices[sliceSelect.value];
      const minScore = Number(threshold.value);
      const metrics = Object.entries(slice.metrics).filter(([, value]) => value.score >= minScore);
      metricsEl.innerHTML = metrics.map(([name, value]) => {{
        const cls = value.label === "OBSERVED" ? "obs" : value.label === "DERIVED" ? "drv" : "spc";
        return `<div class="metric"><div class="${{cls}}">${{value.label}}</div><strong>${{name}}</strong>: ${{value.score.toFixed(3)}}<br/><span>${{value.method}}</span></div>`;
      }}).join("");
      ablationEl.textContent = JSON.stringify(payload.full_graph.ablations, null, 2);
    }}

    [sliceSelect, coordSelect, threshold].forEach(el => el.addEventListener("input", () => {{ renderMetrics(); draw(); }}));
    renderMetrics();
    draw();
  </script>
</body>
</html>"""

    def _index_html(self, payload: dict[str, Any]) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>EDEN Observatory Index</title>
  <style>
    body {{
      margin: 0;
      font-family: Menlo, SFMono-Regular, monospace;
      background: linear-gradient(180deg, #050403, #0f0703);
      color: #ffe2af;
      padding: 18px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}
    .card {{
      background: rgba(27, 15, 4, 0.9);
      border: 1px solid rgba(255, 191, 102, 0.22);
      border-radius: 14px;
      padding: 16px;
    }}
    a {{ color: #7de3ff; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div style="font-size: 28px; letter-spacing: 0.14em; color: #ffbf66;">EDEN / OBSERVATORY INDEX</div>
  <div>experiment={payload["experiment_id"]} generated_at={payload["generated_at"]}</div>
  <div class="grid">
    <div class="card">
      <h3>Graph Knowledge Base</h3>
      <div>nodes={payload["summary"]["nodes"]} edges={payload["summary"]["edges"]}</div>
      <a href="{Path(payload["artifacts"]["graph"]["graph_html"]).name}">open graph html</a>
    </div>
    <div class="card">
      <h3>Behavioral Basin</h3>
      <div>turns={payload["summary"]["turns"]} sessions={payload["summary"]["sessions"]}</div>
      <a href="{Path(payload["artifacts"]["basin"]["basin_html"]).name}">open basin html</a>
    </div>
    <div class="card">
      <h3>Geometry Lab</h3>
      <div>full graph metrics + ablations + slice inspector</div>
      <a href="{Path(payload["artifacts"]["geometry"]["geometry_html"]).name}">open geometry lab</a>
    </div>
  </div>
</body>
</html>"""
