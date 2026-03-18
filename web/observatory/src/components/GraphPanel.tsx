import Graph from "graphology";
import Sigma from "sigma";
import { useEffect, useMemo, useRef, useState } from "react";

import type { AppearanceState, CoordinateMap, GraphEdge, GraphNode } from "../workbench/graphUtils";

type Props = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  coordinateMap: CoordinateMap;
  appearance: AppearanceState;
  highlightedNodeIds: string[];
  selectedNodeIds: string[];
  selectedEdgeId: string | null;
  selectedAssembly: any | null;
  addedNodeIds?: string[];
  addedEdgeIds?: string[];
  onSelectNode: (nodeId: string, additive: boolean) => void;
  onSelectEdge: (edgeId: string) => void;
  onClearSelection: () => void;
  ariaLabel?: string;
};

const PALETTE = ["#e8aa55", "#c96f32", "#a4d06f", "#5da271", "#4a7ea8", "#b7678f", "#d7c35f", "#84dce5"];

function colorFor(value: string): string {
  let hash = 0;
  for (const char of value) hash = (hash * 33 + char.charCodeAt(0)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export default function GraphPanel({
  nodes,
  edges,
  coordinateMap,
  appearance,
  highlightedNodeIds,
  selectedNodeIds,
  selectedEdgeId,
  selectedAssembly,
  addedNodeIds = [],
  addedEdgeIds = [],
  onSelectNode,
  onSelectEdge,
  onClearSelection,
  ariaLabel = "Graph canvas",
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);
  const highlighted = useMemo(() => new Set(highlightedNodeIds), [highlightedNodeIds]);
  const selected = useMemo(() => new Set(selectedNodeIds), [selectedNodeIds]);
  const assemblyMembers = useMemo(() => new Set(selectedAssembly?.member_meme_ids ?? []), [selectedAssembly]);
  const assemblyEdges = useMemo(() => new Set(selectedAssembly?.supporting_edge_ids ?? []), [selectedAssembly]);
  const addedNodes = useMemo(() => new Set(addedNodeIds), [addedNodeIds]);
  const addedEdges = useMemo(() => new Set(addedEdgeIds), [addedEdgeIds]);

  useEffect(() => {
    if (!containerRef.current) return;
    if (!nodes.length) {
      containerRef.current.innerHTML = "";
      setRenderError("No graph entities match the current filters.");
      return;
    }
    setRenderError(null);
    let renderer: Sigma | null = null;

    try {
      const graph = new Graph({ multi: true });

      for (const node of nodes) {
        const coords = coordinateMap[node.id] ?? node.render_coords?.force ?? node.derived_coords?.spectral ?? { x: 0, y: 0 };
        const nodeSelected = selected.has(node.id);
        const nodeActive = highlighted.has(node.id);
        const nodeAdded = addedNodes.has(node.id);
        const nodeAssembly = assemblyMembers.has(node.id);
        const importance = Number(node.degree ?? node.recent_active_set_presence ?? 1);

        graph.addNode(node.id, {
          x: Number(coords.x ?? 0),
          y: Number(coords.y ?? 0),
          size: computeNodeSize(node, appearance, nodeSelected, nodeActive, nodeAdded),
          label: computeNodeLabel(node, appearance, nodeSelected, nodeActive, importance),
          color: computeNodeColor(node, appearance, { nodeSelected, nodeActive, nodeAdded, nodeAssembly }),
          borderColor: nodeSelected ? "#fff6cf" : undefined,
          zIndex: nodeSelected || nodeAdded ? 2 : 1,
        });
      }

      for (const edge of edges) {
        if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target)) continue;
        const edgeId = edge.id || `${edge.source}::${edge.target}::${edge.type ?? "EDGE"}`;
        graph.addEdgeWithKey(edgeId, edge.source, edge.target, {
          size: computeEdgeSize(edge, selectedEdgeId === edgeId, addedEdges.has(edgeId), assemblyEdges.has(edgeId)),
          color: computeEdgeColor(edge, appearance, {
            selected: selectedEdgeId === edgeId,
            added: addedEdges.has(edgeId),
            assembly: assemblyEdges.has(edgeId),
          }),
          label: appearance.showEdgeLabels || selectedEdgeId === edgeId || assemblyEdges.has(edgeId) ? String(edge.type ?? "") : "",
          hidden: false,
        });
      }

      renderer = new Sigma(graph, containerRef.current, {
        allowInvalidContainer: true,
        renderEdgeLabels: appearance.showEdgeLabels || Boolean(selectedEdgeId) || Boolean(selectedAssembly),
        labelRenderedSizeThreshold: 7,
        labelDensity: 0.07,
        zIndex: true,
      });
      sigmaRef.current = renderer;
      renderer.on("clickNode", ({ node, event }) => {
        const additive = Boolean((event.original as MouseEvent | undefined)?.shiftKey);
        onSelectNode(String(node), additive);
      });
      renderer.on("clickEdge", ({ edge }) => {
        onSelectEdge(String(edge));
      });
      renderer.on("clickStage", () => onClearSelection());
      renderer.getCamera().animatedReset({ duration: 180 });
    } catch (error) {
      containerRef.current.innerHTML = "";
      setRenderError(error instanceof Error ? error.message : "Graph renderer unavailable.");
    }

    return () => {
      renderer?.kill();
      sigmaRef.current = null;
    };
  }, [
    addedEdges,
    addedNodes,
    appearance,
    assemblyEdges,
    assemblyMembers,
    coordinateMap,
    edges,
    highlighted,
    nodes,
    onClearSelection,
    onSelectEdge,
    onSelectNode,
    selected,
    selectedAssembly,
    selectedEdgeId,
  ]);

  if (renderError) {
    return (
      <div className="empty-state" data-testid="graph-canvas-fallback" role="note">
        <h2>Graph renderer unavailable</h2>
        <p>{renderError}</p>
        <p>Use the Graph Entities, Data Lab, and inspector cards to keep read paths truthful.</p>
      </div>
    );
  }

  return <div aria-label={ariaLabel} className="graph-panel" data-testid="graph-canvas" ref={containerRef} role="region" />;
}

function computeNodeSize(node: GraphNode, appearance: AppearanceState, selected: boolean, active: boolean, added: boolean): number {
  let base = 6;
  if (appearance.nodeSizeBy === "degree") base = 4 + Number(node.degree ?? 0) * 1.1;
  else if (appearance.nodeSizeBy === "recent_active_set_presence") base = 4 + Number(node.recent_active_set_presence ?? 0) * 1.2;
  else if (appearance.nodeSizeBy === "evidence") base = 4 + Number(node.evidence ?? 0) * 1.8;
  else if (appearance.nodeSizeBy === "reward") base = 4 + Number(node.reward ?? 0) * 2.4;
  else if (appearance.nodeSizeBy === "risk") base = 4 + Number(node.risk ?? 0) * 2.4;
  if (active) base += 1.4;
  if (selected) base += 2.2;
  if (added) base += 1.8;
  return clamp(base, 4, 18);
}

function computeNodeLabel(node: GraphNode, appearance: AppearanceState, selected: boolean, active: boolean, importance: number): string {
  if (appearance.labelMode === "none") return "";
  if (appearance.labelMode === "all") return String(node.label ?? node.id);
  if (appearance.labelMode === "cluster") return String(node.cluster_label ?? node.cluster_signature ?? "");
  if (appearance.labelMode === "importance") return importance >= 3 ? String(node.label ?? node.id) : "";
  if (selected || active) return String(node.label ?? node.id);
  return "";
}

function computeNodeColor(
  node: GraphNode,
  appearance: AppearanceState,
  state: { nodeSelected: boolean; nodeActive: boolean; nodeAdded: boolean; nodeAssembly: boolean },
): string {
  if (state.nodeAdded) return "#b8ffbc";
  if (state.nodeSelected) return "#fff0a8";
  if (state.nodeAssembly) return "#cfeeb0";
  if (state.nodeActive) return "#ffcb73";
  if (appearance.nodeColorBy === "domain") return colorFor(String(node.domain ?? node.id));
  if (appearance.nodeColorBy === "entity_type") return colorFor(String(node.entity_type ?? node.kind ?? node.id));
  if (appearance.nodeColorBy === "cluster") return colorFor(String(node.cluster_signature ?? node.id));
  if (appearance.nodeColorBy === "evidence_label") return colorFor(String(node.evidence_label ?? node.id));
  if (appearance.nodeColorBy === "active_set_presence") return Number(node.recent_active_set_presence ?? 0) > 0 ? "#f8cb7e" : "#7e6b5a";
  if (appearance.nodeColorBy === "regard_balance") return regardTone(node);
  return colorFor(String(node.kind ?? node.id));
}

function regardTone(node: GraphNode): string {
  const reward = Number(node.reward ?? 0);
  const risk = Number(node.risk ?? 0);
  if (reward >= risk) return "#9cd39e";
  if (risk > reward) return "#d4866b";
  return "#9aaad2";
}

function computeEdgeSize(edge: GraphEdge, selected: boolean, added: boolean, assembly: boolean): number {
  let base = clamp(Number(edge.weight ?? 1), 0.8, 3.6);
  if (assembly) base += 0.9;
  if (selected) base += 0.8;
  if (added) base += 0.8;
  return base;
}

function computeEdgeColor(
  edge: GraphEdge,
  appearance: AppearanceState,
  state: { selected: boolean; added: boolean; assembly: boolean },
): string {
  const opacity = edgeOpacity(edge, appearance);
  if (state.added) return `rgba(157, 255, 176, ${opacity})`;
  if (state.selected) return `rgba(255, 240, 168, ${opacity})`;
  if (state.assembly) return `rgba(255, 230, 160, ${opacity})`;
  if (appearance.edgeColorBy === "evidence_label") return withOpacity(colorFor(String(edge.evidence_label ?? edge.type ?? "EDGE")), opacity);
  if (appearance.edgeColorBy === "assertion_origin") return withOpacity(colorFor(String(edge.assertion_origin ?? edge.type ?? "EDGE")), opacity);
  if (appearance.edgeColorBy === "selection_state") return `rgba(233, 177, 90, ${opacity})`;
  return withOpacity(colorFor(String(edge.type ?? "EDGE")), opacity);
}

function edgeOpacity(edge: GraphEdge, appearance: AppearanceState): number {
  if (appearance.edgeOpacityBy === "uniform") return 0.48;
  if (appearance.edgeOpacityBy === "measurement_history") return clamp(0.22 + Number(edge.measurement_history?.length ?? 0) * 0.12, 0.22, 0.9);
  if (appearance.edgeOpacityBy === "assertion_origin") return String(edge.assertion_origin ?? "").startsWith("operator") ? 0.78 : 0.34;
  return clamp(0.18 + Number(edge.weight ?? 1) * 0.22, 0.18, 0.86);
}

function withOpacity(color: string, opacity: number): string {
  if (color.startsWith("rgba(")) return color;
  const normalized = color.replace("#", "");
  const bigint = Number.parseInt(normalized.length === 3 ? normalized.split("").map((item) => `${item}${item}`).join("") : normalized, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}
