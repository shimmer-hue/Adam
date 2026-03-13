export type GraphNode = Record<string, any> & {
  id: string;
  label?: string;
  kind?: string;
  domain?: string;
};

export type GraphEdge = Record<string, any> & {
  id: string;
  source: string;
  target: string;
  type?: string;
  weight?: number;
};

export type GraphPatch = {
  graph_changed?: boolean;
  added_nodes?: GraphNode[];
  removed_nodes?: GraphNode[];
  added_edges?: GraphEdge[];
  removed_edges?: GraphEdge[];
  selection_before?: string[];
  selection_after?: string[];
};

export type GraphMode = "Semantic Map" | "Assemblies" | "Runtime" | "Active Set" | "Compare";

export type FilterState = {
  search: string;
  session: string;
  kind: string;
  domain: string;
  source: string;
  verdict: string;
  evidence: string;
  createdAt: string;
  degreeMin: number;
  weightMin: number;
  hideIsolated: boolean;
  componentMode: "all" | "largest" | "selection";
  egoRadius: number;
};

export type AppearanceState = {
  nodeColorBy: string;
  nodeSizeBy: string;
  edgeColorBy: string;
  edgeOpacityBy: string;
  labelMode: "selection" | "cluster" | "importance" | "all" | "none";
  showEdgeLabels: boolean;
};

export type VisibleGraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  componentIndex: Map<string, number>;
};

export type CoordinateMap = Record<string, { x: number; y: number }>;

export type LayoutSnapshot = {
  id: string;
  name: string;
  layoutId: string;
  settingsHash: string;
  coordinateMap: CoordinateMap;
  createdAt: string;
};

export function nodeLabel(node: GraphNode | null | undefined): string {
  return String(node?.label ?? node?.id ?? "unknown node");
}

export function edgeLabel(edge: GraphEdge | null | undefined, nodeLookup: Map<string, GraphNode>): string {
  const sourceLabel = nodeLabel(nodeLookup.get(String(edge?.source ?? "")));
  const targetLabel = nodeLabel(nodeLookup.get(String(edge?.target ?? "")));
  return `${String(edge?.type ?? "EDGE")}: ${sourceLabel} -> ${targetLabel}`;
}

export function edgeKey(edge: Pick<GraphEdge, "source" | "target" | "type">): string {
  return `${String(edge.source)}::${String(edge.target)}::${String(edge.type ?? "")}`;
}

export function hashText(value: string): string {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16);
}

export function visibleGraphForMode(payload: any, mode: GraphMode): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const semanticNodes = (payload?.semantic_nodes ?? []) as GraphNode[];
  const semanticEdges = (payload?.semantic_edges ?? []) as GraphEdge[];
  const runtimeNodes = (payload?.runtime_nodes ?? []) as GraphNode[];
  const runtimeEdges = (payload?.runtime_edges ?? []) as GraphEdge[];
  const latestActive = new Set<string>(payload?.latest_active_ids ?? payload?.active_set_slices?.at?.(-1)?.node_ids ?? []);

  if (mode === "Runtime") {
    return { nodes: runtimeNodes, edges: runtimeEdges };
  }

  if (mode === "Active Set") {
    const activeNodes = semanticNodes.filter((node) => latestActive.has(node.id));
    const activeIds = new Set(activeNodes.map((node) => node.id));
    return {
      nodes: activeNodes,
      edges: semanticEdges.filter((edge) => activeIds.has(edge.source) && activeIds.has(edge.target)),
    };
  }

  return { nodes: semanticNodes, edges: semanticEdges };
}

export function applyPreviewPatch(nodes: GraphNode[], edges: GraphEdge[], patch: GraphPatch | null | undefined): { nodes: GraphNode[]; edges: GraphEdge[] } {
  if (!patch) return { nodes, edges };

  const nodeMap = new Map(nodes.map((node) => [node.id, { ...node }]));
  const edgeMap = new Map(edges.map((edge) => [edge.id || edgeKey(edge), { ...edge }]));

  for (const removed of patch.removed_edges ?? []) {
    edgeMap.delete(removed.id || edgeKey(removed));
  }
  for (const removed of patch.removed_nodes ?? []) {
    nodeMap.delete(removed.id);
  }
  for (const added of patch.added_nodes ?? []) {
    nodeMap.set(added.id, { ...added });
  }
  for (const added of patch.added_edges ?? []) {
    edgeMap.set(added.id || edgeKey(added), { ...added });
  }

  const nextNodes = [...nodeMap.values()];
  const validIds = new Set(nextNodes.map((node) => node.id));
  const nextEdges = [...edgeMap.values()].filter((edge) => validIds.has(edge.source) && validIds.has(edge.target));

  return { nodes: nextNodes, edges: nextEdges };
}

export function coordsForNode(node: GraphNode, coordinateMode: string, snapshots: LayoutSnapshot[]): { x: number; y: number } {
  const snapshot = snapshots.find((entry) => entry.id === coordinateMode);
  if (snapshot?.coordinateMap?.[node.id]) return snapshot.coordinateMap[node.id];

  if (coordinateMode === "forceatlas2" || coordinateMode === "fruchterman_reingold" || coordinateMode === "noverlap" || coordinateMode === "radial") {
    return node.render_coords?.force ?? node.derived_coords?.spectral ?? { x: 0, y: 0 };
  }
  if (coordinateMode === "force") return node.render_coords?.force ?? node.derived_coords?.spectral ?? { x: 0, y: 0 };
  if (coordinateMode === "symmetry") return node.derived_coords?.pca ?? node.render_coords?.force ?? { x: 0, y: 0 };
  return node.derived_coords?.[coordinateMode] ?? node.render_coords?.force ?? { x: 0, y: 0 };
}

export function buildNodeLookup(nodes: GraphNode[]): Map<string, GraphNode> {
  return new Map(nodes.map((node) => [node.id, node]));
}

export function applyFilters(nodes: GraphNode[], edges: GraphEdge[], filters: FilterState, selectedNodeIds: string[]): VisibleGraph {
  const activeSelection = new Set(selectedNodeIds);
  const search = filters.search.trim().toLowerCase();
  const filteredNodes = nodes.filter((node) => {
    if (filters.session && String(node.session_id ?? "") !== filters.session) return false;
    if (filters.kind && String(node.kind ?? "") !== filters.kind) return false;
    if (filters.domain && String(node.domain ?? "") !== filters.domain) return false;
    if (filters.source && String(node.source_kind ?? "") !== filters.source) return false;
    if (filters.verdict && !(node.verdicts ?? []).includes(filters.verdict)) return false;
    if (filters.evidence && String(node.evidence_label ?? "") !== filters.evidence) return false;
    if (filters.createdAt && !String(node.created_at ?? "").includes(filters.createdAt)) return false;
    if (Number(node.degree ?? 0) < Number(filters.degreeMin || 0)) return false;
    if (!search) return true;
    const haystack = [
      node.label,
      node.summary,
      node.provenance,
      node.operator_label,
      node.cluster_label,
      node.cluster_signature,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(search);
  });

  const visibleIds = new Set(filteredNodes.map((node) => node.id));
  let filteredEdges = edges.filter((edge) => {
    if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) return false;
    if (Number(edge.weight ?? 0) < Number(filters.weightMin || 0)) return false;
    if (filters.evidence && String(edge.evidence_label ?? "") !== filters.evidence) return false;
    return true;
  });

  const nodesById = new Map(filteredNodes.map((node) => [node.id, node]));
  const componentIndex = componentMembership(filteredNodes, filteredEdges);

  if (filters.componentMode === "largest") {
    const largestComponent = largestComponentIds(componentIndex);
    const allowed = new Set(largestComponent);
    filteredEdges = filteredEdges.filter((edge) => allowed.has(edge.source) && allowed.has(edge.target));
    const nodesInLargest = filteredNodes.filter((node) => allowed.has(node.id));
    return finalizeFilters(nodesInLargest, filteredEdges, filters.hideIsolated, componentMembership(nodesInLargest, filteredEdges));
  }

  if (filters.componentMode === "selection" && activeSelection.size) {
    const selectedComponents = new Set<number>();
    for (const nodeId of activeSelection) {
      const componentId = componentIndex.get(nodeId);
      if (componentId != null) selectedComponents.add(componentId);
    }
    const nodesInSelectionComponents = filteredNodes.filter((node) => selectedComponents.has(componentIndex.get(node.id) ?? -1));
    const ids = new Set(nodesInSelectionComponents.map((node) => node.id));
    filteredEdges = filteredEdges.filter((edge) => ids.has(edge.source) && ids.has(edge.target));
    return finalizeFilters(nodesInSelectionComponents, filteredEdges, filters.hideIsolated, componentMembership(nodesInSelectionComponents, filteredEdges));
  }

  if (filters.egoRadius > 0 && activeSelection.size) {
    const egoIds = egoNeighborhood(activeSelection, filteredEdges, filters.egoRadius);
    const egoNodes = filteredNodes.filter((node) => egoIds.has(node.id));
    filteredEdges = filteredEdges.filter((edge) => egoIds.has(edge.source) && egoIds.has(edge.target));
    return finalizeFilters(egoNodes, filteredEdges, filters.hideIsolated, componentMembership(egoNodes, filteredEdges));
  }

  return finalizeFilters(filteredNodes, filteredEdges, filters.hideIsolated, componentIndex, nodesById);
}

function finalizeFilters(
  nodes: GraphNode[],
  edges: GraphEdge[],
  hideIsolated: boolean,
  componentIndex: Map<string, number>,
  nodesById = new Map(nodes.map((node) => [node.id, node])),
): VisibleGraph {
  if (!hideIsolated) {
    return { nodes, edges, componentIndex };
  }

  const connected = new Set<string>();
  for (const edge of edges) {
    connected.add(edge.source);
    connected.add(edge.target);
  }
  const nextNodes = nodes.filter((node) => connected.has(node.id));
  const nextIds = new Set(nextNodes.map((node) => node.id));
  return {
    nodes: nextNodes.map((node) => nodesById.get(node.id) ?? node),
    edges: edges.filter((edge) => nextIds.has(edge.source) && nextIds.has(edge.target)),
    componentIndex: componentMembership(nextNodes, edges.filter((edge) => nextIds.has(edge.source) && nextIds.has(edge.target))),
  };
}

export function componentMembership(nodes: GraphNode[], edges: GraphEdge[]): Map<string, number> {
  const adjacency = new Map<string, Set<string>>();
  for (const node of nodes) adjacency.set(node.id, new Set());
  for (const edge of edges) {
    adjacency.get(edge.source)?.add(edge.target);
    adjacency.get(edge.target)?.add(edge.source);
  }

  const visited = new Set<string>();
  const membership = new Map<string, number>();
  let componentId = 0;

  for (const node of nodes) {
    if (visited.has(node.id)) continue;
    const queue = [node.id];
    visited.add(node.id);
    while (queue.length) {
      const current = queue.shift()!;
      membership.set(current, componentId);
      for (const neighbor of adjacency.get(current) ?? []) {
        if (visited.has(neighbor)) continue;
        visited.add(neighbor);
        queue.push(neighbor);
      }
    }
    componentId += 1;
  }

  return membership;
}

function largestComponentIds(componentIndex: Map<string, number>): string[] {
  const counts = new Map<number, number>();
  for (const value of componentIndex.values()) {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  let winner = -1;
  let winnerCount = -1;
  for (const [componentId, count] of counts.entries()) {
    if (count > winnerCount) {
      winner = componentId;
      winnerCount = count;
    }
  }
  return [...componentIndex.entries()].filter(([, componentId]) => componentId === winner).map(([nodeId]) => nodeId);
}

function egoNeighborhood(seed: Set<string>, edges: GraphEdge[], radius: number): Set<string> {
  const adjacency = new Map<string, Set<string>>();
  for (const edge of edges) {
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, new Set());
    if (!adjacency.has(edge.target)) adjacency.set(edge.target, new Set());
    adjacency.get(edge.source)!.add(edge.target);
    adjacency.get(edge.target)!.add(edge.source);
  }
  const seen = new Set(seed);
  let frontier = [...seed];
  for (let depth = 0; depth < radius; depth += 1) {
    const next: string[] = [];
    for (const nodeId of frontier) {
      for (const neighbor of adjacency.get(nodeId) ?? []) {
        if (seen.has(neighbor)) continue;
        seen.add(neighbor);
        next.push(neighbor);
      }
    }
    frontier = next;
    if (!frontier.length) break;
  }
  return seen;
}

export function csvForNodes(nodes: GraphNode[]): string {
  const columns = ["id", "label", "kind", "domain", "source_kind", "cluster_signature", "degree", "recent_active_set_presence"];
  return [columns.join(","), ...nodes.map((node) => columns.map((column) => csvEscape(node[column])).join(","))].join("\n");
}

export function csvForEdges(edges: GraphEdge[]): string {
  const columns = ["id", "source", "target", "type", "weight", "evidence_label", "assertion_origin", "confidence"];
  return [columns.join(","), ...edges.map((edge) => columns.map((column) => csvEscape(edge[column])).join(","))].join("\n");
}

export function jsonForSelection(nodes: GraphNode[], edges: GraphEdge[], selectedNodeIds: string[]): string {
  const selectedIds = new Set(selectedNodeIds);
  const selectedNodes = nodes.filter((node) => selectedIds.has(node.id));
  const selectedEdges = edges.filter((edge) => selectedIds.has(edge.source) || selectedIds.has(edge.target));
  return JSON.stringify({ nodes: selectedNodes, edges: selectedEdges }, null, 2);
}

export function graphMLForGraph(nodes: GraphNode[], edges: GraphEdge[]): string {
  const header = `<?xml version="1.0" encoding="UTF-8"?>`;
  const nodeXml = nodes
    .map((node) => `<node id="${xmlEscape(node.id)}"><data key="label">${xmlEscape(nodeLabel(node))}</data><data key="kind">${xmlEscape(String(node.kind ?? ""))}</data><data key="domain">${xmlEscape(String(node.domain ?? ""))}</data></node>`)
    .join("");
  const edgeXml = edges
    .map(
      (edge) =>
        `<edge id="${xmlEscape(edge.id || edgeKey(edge))}" source="${xmlEscape(edge.source)}" target="${xmlEscape(edge.target)}"><data key="type">${xmlEscape(
          String(edge.type ?? ""),
        )}</data><data key="weight">${xmlEscape(String(edge.weight ?? 1))}</data></edge>`,
    )
    .join("");
  return `${header}<graphml xmlns="http://graphml.graphdrawing.org/xmlns"><graph edgedefault="directed">${nodeXml}${edgeXml}</graph></graphml>`;
}

export function gexfForGraph(nodes: GraphNode[], edges: GraphEdge[]): string {
  const nodeXml = nodes
    .map(
      (node) =>
        `<node id="${xmlEscape(node.id)}" label="${xmlEscape(nodeLabel(node))}"><attvalues><attvalue for="kind" value="${xmlEscape(
          String(node.kind ?? ""),
        )}"/><attvalue for="domain" value="${xmlEscape(String(node.domain ?? ""))}"/></attvalues></node>`,
    )
    .join("");
  const edgeXml = edges
    .map(
      (edge, index) =>
        `<edge id="${xmlEscape(edge.id || `edge-${index}`)}" source="${xmlEscape(edge.source)}" target="${xmlEscape(edge.target)}" type="directed" weight="${xmlEscape(
          String(edge.weight ?? 1),
        )}" label="${xmlEscape(String(edge.type ?? ""))}" />`,
    )
    .join("");
  return `<?xml version="1.0" encoding="UTF-8"?><gexf version="1.3" xmlns="http://gexf.net/1.3"><graph defaultedgetype="directed" mode="static"><attributes class="node"><attribute id="kind" title="kind" type="string"/><attribute id="domain" title="domain" type="string"/></attributes><nodes>${nodeXml}</nodes><edges>${edgeXml}</edges></graph></gexf>`;
}

export function downloadText(filename: string, content: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(href);
}

export function defaultFilterState(): FilterState {
  return {
    search: "",
    session: "",
    kind: "",
    domain: "",
    source: "",
    verdict: "",
    evidence: "",
    createdAt: "",
    degreeMin: 0,
    weightMin: 0,
    hideIsolated: false,
    componentMode: "all",
    egoRadius: 0,
  };
}

export function defaultAppearanceState(): AppearanceState {
  return {
    nodeColorBy: "kind",
    nodeSizeBy: "degree",
    edgeColorBy: "type",
    edgeOpacityBy: "weight",
    labelMode: "selection",
    showEdgeLabels: false,
  };
}

function csvEscape(value: unknown): string {
  const text = String(value ?? "");
  if (!/[",\n]/.test(text)) return text;
  return `"${text.replaceAll('"', '""')}"`;
}

function xmlEscape(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}
