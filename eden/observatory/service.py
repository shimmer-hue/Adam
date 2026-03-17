from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx

from ..semantic_relations import MEMODE_MEMBERSHIP_EDGE_TYPE
from ..utils import now_utc, safe_excerpt
from .contracts import MEMODE_SUPPORT_EDGE_ALLOWLIST, MEMODE_SUPPORT_EDGE_DENYLIST
from .geometry import compute_geometry_metrics, compute_selection_geometry, metric_deltas


class ObservatoryService:
    def __init__(
        self,
        *,
        store,
        exporter,
        runtime_log,
        export_root: Path,
        runtime_status_provider=None,
        runtime_model_provider=None,
        tanakh_service=None,
        hum_provider=None,
    ) -> None:
        self.store = store
        self.exporter = exporter
        self.runtime_log = runtime_log
        self.export_root = export_root
        self.runtime_status_provider = runtime_status_provider
        self.runtime_model_provider = runtime_model_provider
        self.tanakh_service = tanakh_service
        self.hum_provider = hum_provider

    def refresh_exports(self, *, experiment_id: str, session_id: str | None) -> tuple[dict[str, str], dict[str, Any]]:
        out_dir = self.export_root / experiment_id
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = self.exporter.export_all(experiment_id=experiment_id, session_id=session_id, out_dir=out_dir)
        payload = {
            "graph": json.loads((out_dir / "graph_knowledge_base.json").read_text(encoding="utf-8")),
            "basin": json.loads((out_dir / "behavioral_attractor_basin.json").read_text(encoding="utf-8")),
            "geometry": json.loads((out_dir / "geometry_diagnostics.json").read_text(encoding="utf-8")),
            "measurements": json.loads((out_dir / "measurement_events.json").read_text(encoding="utf-8")),
            "index": json.loads((out_dir / "observatory_index.json").read_text(encoding="utf-8")),
        }
        tanakh_path = out_dir / "tanakh_surface.json"
        if tanakh_path.exists():
            payload["tanakh"] = json.loads(tanakh_path.read_text(encoding="utf-8"))
        return paths, payload

    def experiment_payload(self, *, experiment_id: str, session_id: str | None) -> dict[str, Any]:
        _, payload = self.refresh_exports(experiment_id=experiment_id, session_id=session_id)
        return payload

    def experiment_overview(self, *, experiment_id: str, session_id: str | None) -> dict[str, Any]:
        payload = self.experiment_payload(experiment_id=experiment_id, session_id=session_id)
        overview = {
            "index": payload["index"],
            "graph_counts": payload["graph"].get("counts", {}),
            "basin": {
                "turn_count": payload["basin"].get("turn_count", 0),
                "filtered_turn_count": payload["basin"].get("filtered_turn_count", 0),
                "projection_method": payload["basin"].get("projection_method", ""),
            },
            "measurements": payload["measurements"].get("counts", {}),
            "hum": self._hum_summary(session_id),
        }
        if "tanakh" in payload:
            overview["tanakh"] = {
                "current_ref": payload["tanakh"].get("current_ref"),
                "bundle_hash": payload["tanakh"].get("bundle_hash"),
            }
        return overview

    def graph_payload(self, *, experiment_id: str, session_id: str | None) -> dict[str, Any]:
        return self.experiment_payload(experiment_id=experiment_id, session_id=session_id)["graph"]

    def basin_payload(self, *, experiment_id: str, session_id: str | None) -> dict[str, Any]:
        return self.experiment_payload(experiment_id=experiment_id, session_id=session_id)["basin"]

    def geometry_payload(self, *, experiment_id: str, session_id: str | None) -> dict[str, Any]:
        return self.experiment_payload(experiment_id=experiment_id, session_id=session_id)["geometry"]

    def measurement_payload(self, *, experiment_id: str, session_id: str | None) -> dict[str, Any]:
        return self.experiment_payload(experiment_id=experiment_id, session_id=session_id)["measurements"]

    def tanakh_payload(self, *, experiment_id: str, session_id: str | None) -> dict[str, Any]:
        payload = self.experiment_payload(experiment_id=experiment_id, session_id=session_id)
        return payload.get("tanakh", {})

    def run_tanakh(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        ref: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if self.tanakh_service is None:
            raise ValueError("Tanakh service is unavailable.")
        out_dir = self.export_root / experiment_id
        out_dir.mkdir(parents=True, exist_ok=True)
        _, payload = self.exporter.export_tanakh_surface(
            experiment_id=experiment_id,
            session_id=session_id,
            out_dir=out_dir,
            ref=ref,
            params=params,
        )
        self.runtime_log.emit(
            "INFO",
            "tanakh_run",
            "Generated Tanakh tool-surface run.",
            experiment_id=experiment_id,
            session_id=session_id,
            ref=payload.get("current_ref"),
            bundle_hash=payload.get("bundle_hash"),
        )
        return payload

    def list_experiments(self) -> dict[str, Any]:
        experiments = self.store.list_experiments()
        primary = [
            row
            for row in experiments
            if json.loads(row.get("metadata_json") or "{}").get("graph_role") == "primary"
        ]
        return {"experiments": primary or experiments[:1]}

    def list_sessions(self, *, experiment_id: str) -> dict[str, Any]:
        sessions = [item for item in self.store.list_session_catalog(limit=250) if item.get("experiment_id") == experiment_id]
        return {"sessions": sessions}

    def session_turns(self, *, session_id: str) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        turns = self.store.list_all_turns(session_id)
        feedback_by_turn = {turn["id"]: self.store.list_feedback_for_turn(turn["id"]) for turn in turns}
        membrane_by_turn = defaultdict(list)
        for event in self.store.list_membrane_events(session["experiment_id"], limit=500, session_id=session_id):
            if event.get("turn_id"):
                membrane_by_turn[str(event["turn_id"])].append(event)
        transcript = []
        for turn in turns:
            metadata = json.loads(turn.get("metadata_json") or "{}")
            inference = metadata.get("inference_profile", {})
            budget = metadata.get("budget", {})
            transcript.append({
                "session_id": session_id,
                "turn_id": turn["id"],
                "turn_index": int(turn.get("turn_index", 0) or 0),
                "created_at": turn.get("created_at"),
                "user_text": turn.get("user_text", ""),
                "adam_text": turn.get("membrane_text") or turn.get("response_text") or "",
                "reasoning_text": metadata.get("model_result", {}).get("reasoning_text", ""),
                "feedback": feedback_by_turn.get(turn["id"], []),
                "membrane_events": membrane_by_turn.get(turn["id"], []),
                "active_set_summary": {"size": len(json.loads(turn.get("active_set_json") or "[]"))},
                "active_set_node_ids": [item.get("node_id") for item in json.loads(turn.get("active_set_json") or "[]") if item.get("node_id")],
                "requested_mode": inference.get("requested_mode", ""),
                "effective_mode": inference.get("effective_mode", ""),
                "budget_summary": budget,
            })
        return {"session": session, "turns": transcript, "hum": self._hum_summary(session_id)}

    def session_active_set(self, *, session_id: str) -> dict[str, Any]:
        turns = self.store.list_all_turns(session_id)
        return {
            "session_id": session_id,
            "turns": [
                {
                    "turn_id": turn["id"],
                    "turn_index": int(turn.get("turn_index", 0) or 0),
                    "created_at": turn.get("created_at"),
                    "items": json.loads(turn.get("active_set_json") or "[]"),
                }
                for turn in turns
            ],
        }

    def session_trace(self, *, session_id: str) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        turns = self.store.list_all_turns(session_id)
        latest_turn = turns[-1] if turns else None
        latest_turn_trace = json.loads(latest_turn.get("trace_json") or "[]") if latest_turn else []
        trace_events = [
            {
                **dict(row),
                "payload": json.loads(row.get("payload_json") or "{}"),
            }
            for row in self.store.list_trace_events(session["experiment_id"], limit=80, session_id=session_id)
        ]
        membrane_events = [
            {
                **dict(row),
                "payload": json.loads(row.get("payload_json") or "{}"),
            }
            for row in self.store.list_membrane_events(session["experiment_id"], limit=40, session_id=session_id)
        ]
        return {
            "session": session,
            "session_id": session_id,
            "latest_turn_id": latest_turn.get("id") if latest_turn else None,
            "latest_turn_index": int(latest_turn.get("turn_index", 0) or 0) if latest_turn else 0,
            "latest_turn_trace": latest_turn_trace,
            "trace_events": trace_events,
            "membrane_events": membrane_events,
        }

    def runtime_status(self) -> dict[str, Any]:
        if self.runtime_status_provider is None:
            return {"available": False}
        return self.runtime_status_provider()

    def runtime_model(self) -> dict[str, Any]:
        if self.runtime_model_provider is None:
            return {"available": False}
        return self.runtime_model_provider()

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

    def preview_action(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        turn_id: str | None,
        action: dict[str, Any],
    ) -> dict[str, Any]:
        _, payload = self.refresh_exports(experiment_id=experiment_id, session_id=session_id)
        graph_payload = payload["graph"]
        graph, directed, node_lookup = self._graph_from_payload(graph_payload)
        action_type = str(action.get("action_type", "")).strip()
        if not action_type:
            raise ValueError("action_type is required.")
        selection_ids = self._selection_ids(action, node_lookup)
        before_nodes = {
            str(node_id): dict(graph.nodes[node_id])
            for node_id in graph.nodes()
        }
        before_edges = self._edge_payloads_from_directed(directed)
        before_global = compute_geometry_metrics(graph, directed, node_order=list(graph.nodes()))
        before_local = compute_selection_geometry(
            graph,
            directed,
            selected_node_ids=selection_ids,
            radius=int(action.get("selection_radius", 1) or 1),
            node_order=list(graph.nodes()),
        )
        after_graph = graph.copy()
        after_directed = directed.copy()
        topology_change = self._apply_action_preview(
            experiment_id=experiment_id,
            action=action,
            graph=after_graph,
            directed=after_directed,
            node_lookup=node_lookup,
        )
        exact_before_state = self._exact_before_state(experiment_id=experiment_id, action=action)
        if exact_before_state is not None:
            topology_change["before_state"] = exact_before_state
        after_selection_ids = topology_change.get("after_selection_ids", selection_ids)
        after_global = compute_geometry_metrics(after_graph, after_directed, node_order=list(after_graph.nodes()))
        after_local = compute_selection_geometry(
            after_graph,
            after_directed,
            selected_node_ids=after_selection_ids,
            radius=int(action.get("selection_radius", 1) or 1),
            node_order=list(after_graph.nodes()),
        )
        preview_graph_patch = self._preview_graph_patch(
            before_nodes=before_nodes,
            before_edges=before_edges,
            after_graph=after_graph,
            after_directed=after_directed,
            selection_before=selection_ids,
            selection_after=after_selection_ids,
        )
        return {
            "generated_at": now_utc(),
            "experiment_id": experiment_id,
            "session_id": session_id,
            "turn_id": turn_id,
            "action_type": action_type,
            "measurement_only": bool(topology_change.get("measurement_only", False)),
            "selection": {
                "before": selection_ids,
                "after": after_selection_ids,
            },
            "compare_selection": {
                "baseline_node_ids": selection_ids,
                "modified_node_ids": after_selection_ids,
            },
            "topology_change": topology_change,
            "preview_graph_patch": preview_graph_patch,
            "global_metrics": {
                "before": before_global,
                "after": after_global,
                "delta": metric_deltas(before_global, after_global),
            },
            "local_metrics": {
                "before": before_local,
                "after": after_local,
                "delta": metric_deltas(before_local["metrics"], after_local["metrics"]),
            },
            "evidence_boundary_note": "Coordinate mode changes are rendering choices. Only topology and measurement overlays change graph facts.",
        }

    def commit_action(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        turn_id: str | None,
        action: dict[str, Any],
    ) -> dict[str, Any]:
        preview = self.preview_action(experiment_id=experiment_id, session_id=session_id, turn_id=turn_id, action=action)
        before_state = self._exact_before_state(experiment_id=experiment_id, action=action)
        committed_state = self._apply_action_commit(
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn_id,
            action=action,
            preview=preview,
        )
        event = self.store.record_measurement_event(
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn_id,
            action_type=str(action["action_type"]),
            target_ids=self._targets_for_action(action, committed_state=committed_state),
            before_state=before_state if before_state is not None else preview["topology_change"].get("before_state", {}),
            proposed_state=preview["topology_change"].get("proposed_state", {}),
            committed_state=committed_state,
            rationale=str(action.get("rationale", "")).strip(),
            operator_label=str(action.get("operator_label", "local_operator")).strip(),
            evidence_label=str(action.get("evidence_label", "OPERATOR_ASSERTED")).strip(),
            measurement_method=str(action.get("measurement_method", "local_geometry_preview")).strip(),
            confidence=float(action.get("confidence", 0.6) or 0.0),
            reverted_from_event_id=None,
        )
        self.store.record_trace_event(
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn_id,
            event_type="OBSERVATORY_EDIT" if not preview["measurement_only"] else "OBSERVATORY_MEASUREMENT",
            level="INFO",
            message=f"{action['action_type']} committed from observatory",
            payload={"measurement_event_id": event["id"], "summary": committed_state.get("summary", "")},
        )
        self.runtime_log.emit(
            "INFO",
            "observatory_commit",
            "Committed observatory action.",
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn_id,
            action_type=action["action_type"],
            measurement_event_id=event["id"],
            measurement_only=preview["measurement_only"],
        )
        paths, payload = self.refresh_exports(experiment_id=experiment_id, session_id=session_id)
        return {
            "event": self._event_payload(event),
            "preview": preview,
            "committed_state": committed_state,
            "exports": paths,
            "payload": payload,
        }

    def revert_event(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        turn_id: str | None,
        event_id: str,
    ) -> dict[str, Any]:
        event = self.store.get_measurement_event(event_id)
        revert_action = {
            "action_type": "revert",
            "event_id": event_id,
            "measurement_method": "revert",
            "evidence_label": "OPERATOR_REFINED",
            "operator_label": "local_operator",
            "confidence": 1.0,
            "rationale": f"Revert measurement event {event_id}",
        }
        committed_state = self._apply_revert(experiment_id=experiment_id, event=event)
        revert_event = self.store.record_measurement_event(
            experiment_id=experiment_id,
            session_id=session_id or event.get("session_id"),
            turn_id=turn_id or event.get("turn_id"),
            action_type="revert",
            target_ids=json.loads(event.get("target_ids_json") or "[]"),
            before_state=json.loads(event.get("committed_state_json") or "{}"),
            proposed_state=revert_action,
            committed_state=committed_state,
            rationale=f"Reverted event {event_id}",
            operator_label="local_operator",
            evidence_label="OPERATOR_REFINED",
            measurement_method="revert",
            confidence=1.0,
            reverted_from_event_id=event_id,
        )
        self.store.record_trace_event(
            experiment_id=experiment_id,
            session_id=session_id or event.get("session_id"),
            turn_id=turn_id or event.get("turn_id"),
            event_type="OBSERVATORY_REVERT",
            level="INFO",
            message=f"reverted observatory event {event_id}",
            payload={"measurement_event_id": revert_event["id"]},
        )
        self.runtime_log.emit(
            "INFO",
            "observatory_revert",
            "Reverted observatory action.",
            experiment_id=experiment_id,
            session_id=session_id or event.get("session_id"),
            turn_id=turn_id or event.get("turn_id"),
            target_event_id=event_id,
            measurement_event_id=revert_event["id"],
        )
        paths, payload = self.refresh_exports(experiment_id=experiment_id, session_id=session_id or event.get("session_id"))
        return {
            "event": self._event_payload(revert_event),
            "committed_state": committed_state,
            "exports": paths,
            "payload": payload,
        }

    def _event_payload(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        for field in ("target_ids_json", "before_state_json", "proposed_state_json", "committed_state_json"):
            payload[field.removesuffix("_json")] = json.loads(payload.get(field) or ("[]" if field == "target_ids_json" else "{}"))
        return payload

    def _graph_from_payload(self, graph_payload: dict[str, Any]) -> tuple[nx.Graph, nx.DiGraph, dict[str, dict[str, Any]]]:
        graph = nx.Graph()
        directed = nx.DiGraph()
        node_lookup: dict[str, dict[str, Any]] = {}
        for node in graph_payload["nodes"]:
            node_lookup[node["id"]] = node
            graph.add_node(node["id"], **node)
            directed.add_node(node["id"], **node)
        for edge in graph_payload["edges"]:
            source = edge["source"]
            target = edge["target"]
            if source not in graph or target not in graph:
                continue
            attrs = {
                "weight": float(edge.get("weight", 1.0)),
                "edge_type": edge.get("type", ""),
                "provenance": edge.get("provenance", {}),
            }
            graph.add_edge(source, target, **attrs)
            directed.add_edge(source, target, **attrs)
        return graph, directed, node_lookup

    def _selection_ids(self, action: dict[str, Any], node_lookup: dict[str, dict[str, Any]]) -> list[str]:
        if action.get("selected_node_ids"):
            return [node_id for node_id in action["selected_node_ids"] if node_id in node_lookup]
        selection: list[str] = []
        if action.get("source_id") in node_lookup:
            selection.append(str(action["source_id"]))
        if action.get("target_id") in node_lookup:
            selection.append(str(action["target_id"]))
        if action.get("memode_id") in node_lookup:
            selection.append(str(action["memode_id"]))
        return selection

    def _apply_action_preview(
        self,
        *,
        experiment_id: str,
        action: dict[str, Any],
        graph: nx.Graph,
        directed: nx.DiGraph,
        node_lookup: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        action_type = str(action["action_type"])
        change: dict[str, Any] = {
            "before_state": {},
            "proposed_state": action,
            "after_selection_ids": self._selection_ids(action, node_lookup),
            "measurement_only": False,
            "graph_changed": False,
        }
        if action_type in {"geometry_measurement_run", "motif_annotation"}:
            change["measurement_only"] = True
            if action_type == "motif_annotation":
                change["annotation"] = self._cluster_annotation_from_action(action)
            return change
        if action_type == "ablation_measurement_run":
            removed_edges: list[dict[str, Any]] = []
            relation_type = str(action.get("mask_relation_type", "")).strip()
            if relation_type:
                for source, target, attrs in list(graph.edges(data=True)):
                    if attrs.get("edge_type") != relation_type:
                        continue
                    removed_edges.append({"source": source, "target": target, "edge_type": relation_type})
                    graph.remove_edge(source, target)
                    if directed.has_edge(source, target):
                        directed.remove_edge(source, target)
            change["measurement_only"] = True
            change["graph_changed"] = True
            change["masked_edges"] = removed_edges
            return change
        if action_type in {"edge_add", "edge_update", "edge_remove"}:
            source_id = str(action.get("source_id", "")).strip()
            target_id = str(action.get("target_id", "")).strip()
            edge_type = str(action.get("edge_type", "")).strip()
            current_edge_type = str(action.get("current_edge_type", edge_type)).strip() or edge_type
            if source_id not in graph or target_id not in graph or not edge_type:
                raise ValueError("edge action requires valid source_id, target_id, and edge_type.")
            existing = graph.get_edge_data(source_id, target_id, default=None)
            exact_before = self._exact_before_state(experiment_id=experiment_id, action=action)
            if exact_before is not None:
                change["before_state"] = exact_before
            change["graph_changed"] = True
            if action_type == "edge_remove":
                if graph.has_edge(source_id, target_id):
                    graph.remove_edge(source_id, target_id)
                if directed.has_edge(source_id, target_id):
                    directed.remove_edge(source_id, target_id)
            else:
                next_weight = float(action.get("weight", existing.get("weight", 1.0) if existing else 1.0))
                provenance = self._edge_provenance(action, existing.get("provenance", {}) if existing else {})
                graph.add_edge(source_id, target_id, weight=next_weight, edge_type=edge_type, provenance=provenance)
                directed.add_edge(source_id, target_id, weight=next_weight, edge_type=edge_type, provenance=provenance)
            return change
        if action_type == "memode_assert":
            subgraph = self._validated_memode_subgraph(experiment_id=experiment_id, candidate_ids=action.get("selected_node_ids") or [], node_lookup=node_lookup)
            member_ids = subgraph["member_ids"]
            temp_id = "__preview_memode__"
            graph.add_node(
                temp_id,
                id=temp_id,
                label=str(action.get("label", "Known Memode")).strip() or "Known Memode",
                kind="memode",
                domain=str(action.get("domain", "behavior")).strip() or "behavior",
                source_kind="memode",
                summary=str(action.get("summary", "")).strip(),
                provenance=str(action.get("operator_label", "local_operator")).strip(),
                supporting_edge_ids=subgraph["supporting_edge_ids"],
                invariance_summary=str(action.get("invariance_summary", action.get("summary", ""))).strip(),
            )
            directed.add_node(temp_id, **graph.nodes[temp_id])
            for member_id in member_ids:
                graph.add_edge(temp_id, member_id, weight=1.0, edge_type=MEMODE_MEMBERSHIP_EDGE_TYPE, provenance={})
                directed.add_edge(temp_id, member_id, weight=1.0, edge_type=MEMODE_MEMBERSHIP_EDGE_TYPE, provenance={})
            change["before_state"] = {"memode": None}
            change["graph_changed"] = True
            change["supporting_edge_ids"] = subgraph["supporting_edge_ids"]
            change["after_selection_ids"] = [temp_id, *member_ids]
            return change
        if action_type == "memode_update_membership":
            memode_id = str(action.get("memode_id", "")).strip()
            if memode_id not in node_lookup:
                raise ValueError("memode_update_membership requires a valid memode_id.")
            subgraph = self._validated_memode_subgraph(experiment_id=experiment_id, candidate_ids=action.get("member_ids") or [], node_lookup=node_lookup)
            member_ids = subgraph["member_ids"]
            existing_edges = []
            for _, target, attrs in list(directed.out_edges(memode_id, data=True)):
                if attrs.get("edge_type") == MEMODE_MEMBERSHIP_EDGE_TYPE:
                    existing_edges.append(target)
                    if graph.has_edge(memode_id, target):
                        graph.remove_edge(memode_id, target)
                    directed.remove_edge(memode_id, target)
            for member_id in member_ids:
                graph.add_edge(memode_id, member_id, weight=1.0, edge_type=MEMODE_MEMBERSHIP_EDGE_TYPE, provenance={})
                directed.add_edge(memode_id, member_id, weight=1.0, edge_type=MEMODE_MEMBERSHIP_EDGE_TYPE, provenance={})
            change["before_state"] = {"memode": {"memode_id": memode_id, "member_ids": existing_edges}}
            change["graph_changed"] = True
            change["supporting_edge_ids"] = subgraph["supporting_edge_ids"]
            change["after_selection_ids"] = [memode_id, *member_ids]
            return change
        raise ValueError(f"Unsupported action_type: {action_type}")

    def _apply_action_commit(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        turn_id: str | None,
        action: dict[str, Any],
        preview: dict[str, Any],
    ) -> dict[str, Any]:
        action_type = str(action["action_type"])
        if action_type in {"geometry_measurement_run", "ablation_measurement_run", "motif_annotation"}:
            committed = {
                "summary": safe_excerpt(str(action.get("rationale", action_type)), limit=160),
                "measurement_only": True,
            }
            if action_type == "motif_annotation":
                committed["annotation"] = self._cluster_annotation_from_action(action)
            return committed
        if action_type in {"edge_add", "edge_update"}:
            source_id = str(action["source_id"])
            target_id = str(action["target_id"])
            edge_type = str(action["edge_type"])
            current_edge_type = str(action.get("current_edge_type", edge_type)).strip() or edge_type
            source_kind = str(action.get("source_kind") or "")
            target_kind = str(action.get("target_kind") or "")
            if not source_kind or not target_kind:
                source_kind, target_kind = self._node_kinds(experiment_id, source_id, target_id)
            existing = self.store.get_edge(
                experiment_id=experiment_id,
                src_kind=source_kind,
                src_id=source_id,
                dst_kind=target_kind,
                dst_id=target_id,
                edge_type=current_edge_type,
            )
            if action_type == "edge_update" and current_edge_type != edge_type:
                self.store.delete_edge(
                    experiment_id=experiment_id,
                    src_kind=source_kind,
                    src_id=source_id,
                    dst_kind=target_kind,
                    dst_id=target_id,
                    edge_type=current_edge_type,
                )
            edge = self.store.set_edge(
                experiment_id=experiment_id,
                src_kind=source_kind,
                src_id=source_id,
                dst_kind=target_kind,
                dst_id=target_id,
                edge_type=edge_type,
                weight=float(action.get("weight", existing["weight"] if existing else 1.0)),
                provenance=self._edge_provenance(action, json.loads(existing["provenance_json"]) if existing else {}),
            )
            return {"edge": edge, "summary": f"{action_type} {source_id} -> {target_id} [{edge_type}]"}
        if action_type == "edge_remove":
            source_id = str(action["source_id"])
            target_id = str(action["target_id"])
            edge_type = str(action["edge_type"])
            source_kind, target_kind = self._node_kinds(experiment_id, source_id, target_id)
            removed = self.store.delete_edge(
                experiment_id=experiment_id,
                src_kind=source_kind,
                src_id=source_id,
                dst_kind=target_kind,
                dst_id=target_id,
                edge_type=edge_type,
            )
            return {"edge": removed, "summary": f"edge_remove {source_id} -> {target_id} [{edge_type}]"}
        if action_type == "memode_assert":
            subgraph = self._validated_memode_subgraph(
                experiment_id=experiment_id,
                candidate_ids=action.get("selected_node_ids") or [],
                node_lookup=self._node_lookup_for_experiment(experiment_id),
            )
            member_ids = subgraph["member_ids"]
            memode = self.store.upsert_memode(
                experiment_id=experiment_id,
                label=str(action.get("label", "Known Memode")).strip() or "Known Memode",
                member_ids=member_ids,
                summary=str(action.get("summary", "")).strip() or "Operator-asserted memode.",
                domain=str(action.get("domain", "behavior")).strip() or "behavior",
                metadata={
                    "operator_label": str(action.get("operator_label", "local_operator")).strip(),
                    "evidence_label": str(action.get("evidence_label", "OPERATOR_ASSERTED")).strip(),
                    "confidence": float(action.get("confidence", 0.6) or 0.0),
                    "rationale": str(action.get("rationale", "")).strip(),
                    "assertion_origin": "operator_asserted",
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "supporting_edge_ids": subgraph["supporting_edge_ids"],
                    "invariance_summary": str(action.get("invariance_summary", action.get("summary", ""))).strip(),
                    "member_order": action.get("member_order") or [],
                    "occurrence_examples": action.get("occurrence_examples") or [],
                },
            )
            self._sync_memode_membership_edges(
                experiment_id=experiment_id,
                memode_id=memode["id"],
                member_ids=member_ids,
                action=action,
            )
            return {"memode": memode, "summary": f"memode_assert {memode['label']}"}
        if action_type == "memode_update_membership":
            memode_id = str(action.get("memode_id", "")).strip()
            subgraph = self._validated_memode_subgraph(
                experiment_id=experiment_id,
                candidate_ids=action.get("member_ids") or [],
                node_lookup=self._node_lookup_for_experiment(experiment_id),
            )
            member_ids = subgraph["member_ids"]
            memode = self.store.update_memode(
                memode_id=memode_id,
                label=str(action.get("label", "")).strip() or None,
                member_ids=member_ids,
                summary=str(action.get("summary", "")).strip() or None,
                metadata_updates={
                    "operator_label": str(action.get("operator_label", "local_operator")).strip(),
                    "evidence_label": str(action.get("evidence_label", "OPERATOR_REFINED")).strip(),
                    "confidence": float(action.get("confidence", 0.6) or 0.0),
                    "rationale": str(action.get("rationale", "")).strip(),
                    "assertion_origin": "operator_refined",
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "supporting_edge_ids": subgraph["supporting_edge_ids"],
                    "invariance_summary": str(action.get("invariance_summary", action.get("summary", ""))).strip() or None,
                    "member_order": action.get("member_order") or [],
                    "occurrence_examples": action.get("occurrence_examples") or [],
                },
            )
            self._sync_memode_membership_edges(
                experiment_id=experiment_id,
                memode_id=memode_id,
                member_ids=member_ids,
                action=action,
            )
            return {"memode": memode, "summary": f"memode_update_membership {memode['label']}"}
        raise ValueError(f"Unsupported action_type: {action_type}")

    def _apply_revert(self, *, experiment_id: str, event: dict[str, Any]) -> dict[str, Any]:
        action_type = str(event["action_type"])
        before_state = json.loads(event.get("before_state_json") or "{}")
        committed_state = json.loads(event.get("committed_state_json") or "{}")
        edge_before = before_state.get("edge") or {}
        edge_after = committed_state.get("edge") or {}
        edge_existed = bool(before_state.get("edge_existed"))
        if action_type == "edge_add":
            if not edge_existed and edge_after:
                removed = self.store.delete_edge(
                    experiment_id=experiment_id,
                    src_kind=edge_after.get("src_kind") or self._node_kinds(experiment_id, edge_after["src_id"], edge_after["dst_id"])[0],
                    src_id=edge_after["src_id"],
                    dst_kind=edge_after.get("dst_kind") or self._node_kinds(experiment_id, edge_after["src_id"], edge_after["dst_id"])[1],
                    dst_id=edge_after["dst_id"],
                    edge_type=edge_after["edge_type"],
                )
                return {"edge": removed, "summary": f"removed {edge_after['src_id']} -> {edge_after['dst_id']}"}
        if action_type in {"edge_add", "edge_update"}:
            if edge_before and edge_before.get("weight") is not None:
                if edge_after and edge_after.get("edge_type") and edge_after.get("edge_type") != edge_before["edge_type"]:
                    self.store.delete_edge(
                        experiment_id=experiment_id,
                        src_kind=edge_after.get("src_kind") or self._node_kinds(experiment_id, edge_after["src_id"], edge_after["dst_id"])[0],
                        src_id=edge_after["src_id"],
                        dst_kind=edge_after.get("dst_kind") or self._node_kinds(experiment_id, edge_after["src_id"], edge_after["dst_id"])[1],
                        dst_id=edge_after["dst_id"],
                        edge_type=edge_after["edge_type"],
                    )
                restored = self.store.set_edge(
                    experiment_id=experiment_id,
                    src_kind=edge_before.get("src_kind") or self._node_kinds(experiment_id, edge_before["source"], edge_before["target"])[0],
                    src_id=edge_before["source"],
                    dst_kind=edge_before.get("dst_kind") or self._node_kinds(experiment_id, edge_before["source"], edge_before["target"])[1],
                    dst_id=edge_before["target"],
                    edge_type=edge_before["edge_type"],
                    weight=float(edge_before["weight"]),
                    provenance=edge_before.get("provenance", {}),
                )
                return {"edge": restored, "summary": f"restored {edge_before['source']} -> {edge_before['target']}"}
            if edge_after:
                removed = self.store.delete_edge(
                    experiment_id=experiment_id,
                    src_kind=edge_after.get("src_kind") or self._node_kinds(experiment_id, edge_after["src_id"], edge_after["dst_id"])[0],
                    src_id=edge_after["src_id"],
                    dst_kind=edge_after.get("dst_kind") or self._node_kinds(experiment_id, edge_after["src_id"], edge_after["dst_id"])[1],
                    dst_id=edge_after["dst_id"],
                    edge_type=edge_after["edge_type"],
                )
                return {"edge": removed, "summary": f"removed {edge_after['src_id']} -> {edge_after['dst_id']}"}
        if action_type == "edge_remove":
            if edge_before and edge_before.get("weight") is not None:
                restored = self.store.set_edge(
                    experiment_id=experiment_id,
                    src_kind=edge_before.get("src_kind") or self._node_kinds(experiment_id, edge_before["source"], edge_before["target"])[0],
                    src_id=edge_before["source"],
                    dst_kind=edge_before.get("dst_kind") or self._node_kinds(experiment_id, edge_before["source"], edge_before["target"])[1],
                    dst_id=edge_before["target"],
                    edge_type=edge_before["edge_type"],
                    weight=float(edge_before["weight"]),
                    provenance=edge_before.get("provenance", {}),
                )
                return {"edge": restored, "summary": f"restored removed edge {edge_before['source']} -> {edge_before['target']}"}
        if action_type == "memode_assert":
            memode = committed_state.get("memode") or {}
            if memode.get("id"):
                deleted = self.store.delete_memode(memode["id"])
                return {"memode": deleted, "summary": f"deleted memode {deleted['label']}"}
        if action_type == "memode_update_membership":
            memode_before = before_state.get("memode") or {}
            memode_id = memode_before.get("memode_id")
            if memode_id:
                restored = self.store.update_memode(
                    memode_id=memode_id,
                    member_ids=memode_before.get("member_ids", []),
                )
                self._sync_memode_membership_edges(
                    experiment_id=experiment_id,
                    memode_id=memode_id,
                    member_ids=memode_before.get("member_ids", []),
                    action={"operator_label": "local_operator", "evidence_label": "OPERATOR_REFINED", "confidence": 1.0},
                )
                return {"memode": restored, "summary": f"restored memode {restored['label']}"}
        return {"summary": f"no-op revert for {action_type}"}

    def _targets_for_action(self, action: dict[str, Any], *, committed_state: dict[str, Any]) -> list[dict[str, Any]]:
        action_type = str(action["action_type"])
        if action_type.startswith("edge_"):
            return [
                {
                    "kind": "edge",
                    "source_id": action.get("source_id"),
                    "target_id": action.get("target_id"),
                    "edge_type": action.get("edge_type"),
                }
            ]
        if action_type.startswith("memode_"):
            memode = committed_state.get("memode") or {}
            metadata = json.loads(memode.get("metadata_json", "{}")) if memode else {}
            member_ids = metadata.get("member_ids") or action.get("member_ids") or action.get("selected_node_ids") or []
            supporting_edge_ids = metadata.get("supporting_edge_ids") or action.get("supporting_edge_ids") or []
            return [{"kind": "memode", "memode_id": memode.get("id") or action.get("memode_id"), "member_ids": member_ids, "supporting_edge_ids": supporting_edge_ids}]
        if action_type == "motif_annotation":
            annotation = committed_state.get("annotation") or self._cluster_annotation_from_action(action)
            return [{"kind": annotation.get("target", {}).get("kind", "measurement"), **annotation.get("target", {}), "cluster_signature": annotation.get("cluster_signature"), "source_graph_hash": annotation.get("source_graph_hash"), "algorithm_version": annotation.get("algorithm_version")} ]
        return [{"kind": "measurement", "action_type": action_type}]

    def _edge_provenance(self, action: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
        payload = dict(existing)
        payload.update(
            {
                "assertion_origin": "operator_refined" if str(action["action_type"]) == "edge_update" else "operator_asserted",
                "operator_label": str(action.get("operator_label", "local_operator")).strip(),
                "evidence_label": str(action.get("evidence_label", "OPERATOR_ASSERTED")).strip(),
                "confidence": float(action.get("confidence", 0.6) or 0.0),
                "rationale": str(action.get("rationale", "")).strip(),
                "measurement_method": str(action.get("measurement_method", "local_geometry_preview")).strip(),
                "updated_at": now_utc(),
            }
        )
        return payload

    def _edge_payloads_from_directed(self, graph: nx.DiGraph) -> dict[tuple[str, str, str], dict[str, Any]]:
        payloads: dict[tuple[str, str, str], dict[str, Any]] = {}
        for source, target, attrs in graph.edges(data=True):
            edge_type = str(attrs.get("edge_type", "") or "")
            payloads[(str(source), str(target), edge_type)] = {
                "id": str(attrs.get("id") or f"preview::{source}::{target}::{edge_type or 'EDGE'}"),
                "source": str(source),
                "target": str(target),
                "type": edge_type,
                "weight": float(attrs.get("weight", 1.0) or 1.0),
                "provenance": dict(attrs.get("provenance") or {}),
            }
        return payloads

    def _preview_graph_patch(
        self,
        *,
        before_nodes: dict[str, dict[str, Any]],
        before_edges: dict[tuple[str, str, str], dict[str, Any]],
        after_graph: nx.Graph,
        after_directed: nx.DiGraph,
        selection_before: list[str],
        selection_after: list[str],
    ) -> dict[str, Any]:
        after_nodes = {
            str(node_id): dict(after_graph.nodes[node_id])
            for node_id in after_graph.nodes()
        }
        after_edges = self._edge_payloads_from_directed(after_directed)
        before_node_ids = set(before_nodes)
        after_node_ids = set(after_nodes)
        before_edge_ids = set(before_edges)
        after_edge_ids = set(after_edges)
        added_nodes = [after_nodes[node_id] for node_id in sorted(after_node_ids - before_node_ids)]
        removed_nodes = [before_nodes[node_id] for node_id in sorted(before_node_ids - after_node_ids)]
        added_edges = [after_edges[key] for key in sorted(after_edge_ids - before_edge_ids)]
        removed_edges = [before_edges[key] for key in sorted(before_edge_ids - after_edge_ids)]
        return {
            "graph_changed": bool(added_nodes or removed_nodes or added_edges or removed_edges),
            "baseline_counts": {
                "nodes": len(before_nodes),
                "edges": len(before_edges),
            },
            "modified_counts": {
                "nodes": len(after_nodes),
                "edges": len(after_edges),
            },
            "added_nodes": added_nodes,
            "removed_nodes": removed_nodes,
            "added_edges": added_edges,
            "removed_edges": removed_edges,
            "selection_before": selection_before,
            "selection_after": selection_after,
        }

    def _exact_before_state(self, *, experiment_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
        action_type = str(action.get("action_type", "")).strip()
        if action_type not in {"edge_add", "edge_update", "edge_remove"}:
            return None
        source_id = str(action.get("source_id", "")).strip()
        target_id = str(action.get("target_id", "")).strip()
        edge_type = str(action.get("edge_type", "")).strip()
        current_edge_type = str(action.get("current_edge_type", edge_type)).strip() or edge_type
        if not source_id or not target_id or not current_edge_type:
            return None
        source_kind = str(action.get("source_kind") or "").strip()
        target_kind = str(action.get("target_kind") or "").strip()
        if not source_kind or not target_kind:
            source_kind, target_kind = self._node_kinds(experiment_id, source_id, target_id)
        existing = self.store.get_edge(
            experiment_id=experiment_id,
            src_kind=source_kind,
            src_id=source_id,
            dst_kind=target_kind,
            dst_id=target_id,
            edge_type=current_edge_type,
        )
        return {
            "edge_existed": existing is not None,
            "edge": self._edge_state_from_row(existing) if existing is not None else None,
        }

    def _edge_state_from_row(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "id": row["id"],
            "source": row["src_id"],
            "target": row["dst_id"],
            "src_id": row["src_id"],
            "dst_id": row["dst_id"],
            "src_kind": row["src_kind"],
            "dst_kind": row["dst_kind"],
            "edge_type": row["edge_type"],
            "weight": float(row["weight"]),
            "provenance": json.loads(row.get("provenance_json") or "{}"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    def _cluster_annotation_from_action(self, action: dict[str, Any]) -> dict[str, Any]:
        target = dict(action.get("target") or {})
        if not target and action.get("cluster_signature"):
            target = {
                "kind": "cluster",
                "cluster_signature": str(action.get("cluster_signature")),
            }
        return {
            "target": target,
            "cluster_signature": str(action.get("cluster_signature") or target.get("cluster_signature") or "").strip(),
            "source_graph_hash": str(action.get("source_graph_hash") or "").strip(),
            "algorithm_version": str(action.get("algorithm_version") or "").strip(),
            "manual_label": str(action.get("manual_label") or "").strip(),
            "manual_summary": str(action.get("manual_summary") or "").strip(),
            "transfer_policy": str(action.get("transfer_policy") or "exact_then_unique_best_jaccard_0.70").strip(),
            "confidence": float(action.get("confidence", 0.6) or 0.0),
            "operator_label": str(action.get("operator_label", "local_operator")).strip(),
            "evidence_label": str(action.get("evidence_label", "OPERATOR_ASSERTED")).strip(),
        }

    def _validated_memode_subgraph(
        self,
        *,
        experiment_id: str,
        candidate_ids: list[str],
        node_lookup: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        member_ids = [node_id for node_id in candidate_ids if node_lookup.get(node_id, {}).get("kind") == "meme"]
        member_ids = sorted(dict.fromkeys(member_ids))
        if len(member_ids) < 2:
            raise ValueError("Known memodes require at least two selected meme nodes.")
        support_graph = nx.Graph()
        support_graph.add_nodes_from(member_ids)
        supporting_edge_ids: list[str] = []
        for edge in self.store.list_edges(experiment_id):
            if edge.get("edge_type") in MEMODE_SUPPORT_EDGE_DENYLIST:
                continue
            if edge.get("edge_type") not in MEMODE_SUPPORT_EDGE_ALLOWLIST:
                continue
            if edge.get("src_kind") != "meme" or edge.get("dst_kind") != "meme":
                continue
            source_id = str(edge.get("src_id"))
            target_id = str(edge.get("dst_id"))
            if source_id not in member_ids or target_id not in member_ids:
                continue
            support_graph.add_edge(source_id, target_id, edge_id=str(edge.get("id")), edge_type=str(edge.get("edge_type")))
            supporting_edge_ids.append(str(edge.get("id")))
        if not supporting_edge_ids:
            raise ValueError("Known memodes require at least one qualifying semantic support edge between the selected memes.")
        isolated = sorted(node for node in member_ids if support_graph.degree(node) == 0)
        if isolated:
            raise ValueError(f"Known memodes cannot include disconnected passenger memes: {', '.join(isolated)}")
        if support_graph.number_of_nodes() and not nx.is_connected(support_graph):
            components = [sorted(component) for component in nx.connected_components(support_graph)]
            if len(components) > 1:
                raise ValueError(f"Known memodes require one connected qualifying support subgraph; found {len(components)} disconnected components.")
        return {
            "member_ids": member_ids,
            "supporting_edge_ids": sorted(dict.fromkeys(supporting_edge_ids)),
        }

    def _node_lookup_for_experiment(self, experiment_id: str) -> dict[str, dict[str, Any]]:
        snapshot = self.store.graph_snapshot(experiment_id)
        lookup: dict[str, dict[str, Any]] = {}
        for group in ("memes", "memodes", "sessions", "turns", "documents", "feedback", "agents"):
            for item in snapshot.get(group, []):
                kind = item.get("kind")
                if kind is None:
                    if group == "memes":
                        kind = "meme"
                    elif group == "memodes":
                        kind = "memode"
                    elif group == "feedback":
                        kind = "feedback"
                    elif group == "documents":
                        kind = "document"
                    else:
                        kind = group[:-1]
                lookup[item["id"]] = {"id": item["id"], "kind": kind}
        return lookup

    def _node_kinds(self, experiment_id: str, source_id: str, target_id: str) -> tuple[str, str]:
        lookup = self._node_lookup_for_experiment(experiment_id)
        source_kind = lookup.get(source_id, {}).get("kind")
        target_kind = lookup.get(target_id, {}).get("kind")
        if not source_kind or not target_kind:
            raise ValueError("Unable to resolve source_kind or target_kind.")
        return source_kind, target_kind

    def _sync_memode_membership_edges(
        self,
        *,
        experiment_id: str,
        memode_id: str,
        member_ids: list[str],
        action: dict[str, Any],
    ) -> None:
        existing = self.store.list_edges_for_node(experiment_id, node_kind="memode", node_id=memode_id, edge_type=MEMODE_MEMBERSHIP_EDGE_TYPE)
        for edge in existing:
            target_id = edge["dst_id"] if edge["src_id"] == memode_id else edge["src_id"]
            if target_id not in member_ids:
                self.store.delete_edge(
                    experiment_id=experiment_id,
                    src_kind=edge["src_kind"],
                    src_id=edge["src_id"],
                    dst_kind=edge["dst_kind"],
                    dst_id=edge["dst_id"],
                    edge_type=edge["edge_type"],
                )
        for member_id in member_ids:
            self.store.set_edge(
                experiment_id=experiment_id,
                src_kind="memode",
                src_id=memode_id,
                dst_kind="meme",
                dst_id=member_id,
                edge_type=MEMODE_MEMBERSHIP_EDGE_TYPE,
                weight=1.0,
                provenance={
                    "assertion_origin": "operator_asserted",
                    "operator_label": str(action.get("operator_label", "local_operator")).strip(),
                    "evidence_label": str(action.get("evidence_label", "OPERATOR_ASSERTED")).strip(),
                    "confidence": float(action.get("confidence", 0.6) or 0.0),
                    "rationale": str(action.get("rationale", "")).strip(),
                },
            )
