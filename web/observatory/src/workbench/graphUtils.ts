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
export type ExportScope = "current" | "full" | "behavior" | "information";

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
  edgeOpacityScale?: number;
};

export type VisibleGraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  componentIndex: Map<string, number>;
};

export type GraphSlice = Pick<VisibleGraph, "nodes" | "edges">;

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

export function nodeExportLabel(node: GraphNode | null | undefined): string {
  return String(node?.export_label ?? node?.label ?? node?.summary ?? node?.id ?? "unknown node");
}

export function edgeLabel(edge: GraphEdge | null | undefined, nodeLookup: Map<string, GraphNode>): string {
  const sourceLabel = nodeLabel(nodeLookup.get(String(edge?.source ?? "")));
  const targetLabel = nodeLabel(nodeLookup.get(String(edge?.target ?? "")));
  return `${String(edge?.type ?? "EDGE")}: ${sourceLabel} -> ${targetLabel}`;
}

export function edgeExportLabel(edge: GraphEdge | null | undefined, nodeLookup: Map<string, GraphNode>): string {
  if (edge?.export_label) return String(edge.export_label);
  const sourceNode = nodeLookup.get(String(edge?.source ?? ""));
  const targetNode = nodeLookup.get(String(edge?.target ?? ""));
  if (!sourceNode || !targetNode) return String(edge?.type ?? "EDGE");
  const sourceLabel = nodeExportLabel(sourceNode);
  const targetLabel = nodeExportLabel(targetNode);
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

function assemblyGraphNodes(payload: any): GraphNode[] {
  const semanticNodes = (payload?.semantic_nodes ?? []) as GraphNode[];
  return dedupeNodes([
    ...((payload?.assembly_nodes ?? []) as GraphNode[]),
    ...semanticNodes,
  ]);
}

export function lookupNodesForPayload(payload: any): GraphNode[] {
  return dedupeNodes([
    ...((payload?.assembly_nodes ?? []) as GraphNode[]),
    ...((payload?.semantic_nodes ?? []) as GraphNode[]),
    ...((payload?.runtime_nodes ?? []) as GraphNode[]),
  ]);
}

function filterGraphSlice(nodes: GraphNode[], edges: GraphEdge[], predicate: (node: GraphNode) => boolean): GraphSlice {
  const selectedIds = new Set(nodes.filter(predicate).map((node) => node.id));
  return {
    nodes: nodes.filter((node) => selectedIds.has(node.id)),
    edges: edges.filter((edge) => selectedIds.has(edge.source) && selectedIds.has(edge.target)),
  };
}

export function graphForExportScope(payload: any, currentGraph: GraphSlice, scope: ExportScope): GraphSlice {
  if (scope === "current" || !payload) return currentGraph;
  const assemblyGraph = visibleGraphForMode(payload, "Assemblies");
  if (scope === "full") return assemblyGraph;
  if (scope === "behavior") {
    return filterGraphSlice(assemblyGraph.nodes, assemblyGraph.edges, (node) => String(node.domain ?? "") === "behavior");
  }
  return filterGraphSlice(
    assemblyGraph.nodes,
    assemblyGraph.edges,
    (node) => String(node.domain ?? "") === "knowledge" || String(node.kind ?? "") === "information",
  );
}

export function exportScopeSuffix(scope: ExportScope): string {
  return scope === "current" ? "" : `-${scope}`;
}

export function visibleGraphForMode(payload: any, mode: GraphMode): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const semanticNodes = (payload?.semantic_nodes ?? []) as GraphNode[];
  const semanticEdges = (payload?.semantic_edges ?? []) as GraphEdge[];
  const assemblyNodes = assemblyGraphNodes(payload);
  const assemblyEdges = ((payload?.assembly_edges ?? payload?.semantic_edges ?? []) as GraphEdge[]);
  const runtimeNodes = (payload?.runtime_nodes ?? []) as GraphNode[];
  const runtimeEdges = (payload?.runtime_edges ?? []) as GraphEdge[];
  const latestActive = new Set<string>(payload?.latest_active_ids ?? payload?.active_set_slices?.at?.(-1)?.node_ids ?? []);

  if (mode === "Runtime") {
    return { nodes: runtimeNodes, edges: runtimeEdges };
  }

  if (mode === "Assemblies") {
    return { nodes: assemblyNodes, edges: assemblyEdges };
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

function dedupeNodes(nodes: GraphNode[]): GraphNode[] {
  const nodeMap = new Map<string, GraphNode>();
  for (const node of nodes) {
    if (!node?.id) continue;
    nodeMap.set(node.id, node);
  }
  return [...nodeMap.values()];
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
  const columns: Array<[string, string]> = [
    ["Id", "id"],
    ["Label", "label"],
    ["Kind", "kind"],
    ["EntityType", "entity_type"],
    ["SpeechActMode", "speech_act_mode"],
    ["StorageKind", "storage_kind"],
    ["Domain", "domain"],
    ["SourceKind", "source_kind"],
    ["ClusterSignature", "cluster_signature"],
    ["Degree", "degree"],
    ["RecentActiveSetPresence", "recent_active_set_presence"],
  ];
  return [
    columns.map(([header]) => header).join(","),
    ...nodes.map((node) =>
      columns
        .map(([, column]) => csvEscape(column === "label" ? nodeExportLabel(node) : node[column]))
        .join(","),
    ),
  ].join("\n");
}

export function csvForEdges(edges: GraphEdge[]): string {
  const columns: Array<[string, string]> = [
    ["Id", "id"],
    ["Source", "source"],
    ["Target", "target"],
    ["Label", "label"],
    ["Type", "type"],
    ["Weight", "weight"],
    ["EvidenceLabel", "evidence_label"],
    ["AssertionOrigin", "assertion_origin"],
    ["Confidence", "confidence"],
  ];
  const nodeLookup = buildNodeLookup(
    dedupeNodesFromEdges(edges).map((id) => ({ id })),
  );
  return [
    columns.map(([header]) => header).join(","),
    ...edges.map((edge) =>
      columns
        .map(([, column]) => csvEscape(column === "label" ? edgeExportLabel(edge, nodeLookup) : edge[column]))
        .join(","),
    ),
  ].join("\n");
}

export function jsonForSelection(nodes: GraphNode[], edges: GraphEdge[], selectedNodeIds: string[]): string {
  const selectedIds = new Set(selectedNodeIds);
  const selectedNodes = nodes.filter((node) => selectedIds.has(node.id));
  const selectedEdges = edges.filter((edge) => selectedIds.has(edge.source) || selectedIds.has(edge.target));
  return JSON.stringify({ nodes: selectedNodes, edges: selectedEdges }, null, 2);
}

export function graphMLForGraph(nodes: GraphNode[], edges: GraphEdge[]): string {
  const header = `<?xml version="1.0" encoding="UTF-8"?>`;
  const nodeLookup = buildNodeLookup(nodes);
  const keys = [
    `<key id="node_label" for="node" attr.name="label" attr.type="string"/>`,
    `<key id="node_kind" for="node" attr.name="kind" attr.type="string"/>`,
    `<key id="node_entity_type" for="node" attr.name="entity_type" attr.type="string"/>`,
    `<key id="node_speech_act_mode" for="node" attr.name="speech_act_mode" attr.type="string"/>`,
    `<key id="node_storage_kind" for="node" attr.name="storage_kind" attr.type="string"/>`,
    `<key id="node_domain" for="node" attr.name="domain" attr.type="string"/>`,
    `<key id="node_source_kind" for="node" attr.name="source_kind" attr.type="string"/>`,
    `<key id="node_cluster_signature" for="node" attr.name="cluster_signature" attr.type="string"/>`,
    `<key id="edge_label" for="edge" attr.name="label" attr.type="string"/>`,
    `<key id="edge_type" for="edge" attr.name="type" attr.type="string"/>`,
    `<key id="edge_weight" for="edge" attr.name="weight" attr.type="double"/>`,
    `<key id="edge_evidence_label" for="edge" attr.name="evidence_label" attr.type="string"/>`,
    `<key id="edge_assertion_origin" for="edge" attr.name="assertion_origin" attr.type="string"/>`,
    `<key id="edge_confidence" for="edge" attr.name="confidence" attr.type="double"/>`,
  ].join("");
  const nodeXml = nodes
    .map(
      (node) =>
        `<node id="${xmlEscape(node.id)}"><data key="node_label">${xmlEscape(nodeExportLabel(node))}</data><data key="node_kind">${xmlEscape(
          String(node.kind ?? ""),
        )}</data><data key="node_entity_type">${xmlEscape(String(node.entity_type ?? ""))}</data><data key="node_speech_act_mode">${xmlEscape(
          String(node.speech_act_mode ?? ""),
        )}</data><data key="node_storage_kind">${xmlEscape(String(node.storage_kind ?? ""))}</data><data key="node_domain">${xmlEscape(
          String(node.domain ?? ""),
        )}</data><data key="node_source_kind">${xmlEscape(
          String(node.source_kind ?? ""),
        )}</data><data key="node_cluster_signature">${xmlEscape(String(node.cluster_signature ?? ""))}</data></node>`,
    )
    .join("");
  const edgeXml = edges
    .map(
      (edge) =>
        `<edge id="${xmlEscape(edge.id || edgeKey(edge))}" source="${xmlEscape(edge.source)}" target="${xmlEscape(edge.target)}"><data key="edge_label">${xmlEscape(
          edgeExportLabel(edge, nodeLookup),
        )}</data><data key="edge_type">${xmlEscape(String(edge.type ?? ""))}</data><data key="edge_weight">${xmlEscape(
          String(numericValue(edge.weight, 1)),
        )}</data><data key="edge_evidence_label">${xmlEscape(String(edge.evidence_label ?? ""))}</data><data key="edge_assertion_origin">${xmlEscape(
          String(edge.assertion_origin ?? ""),
        )}</data><data key="edge_confidence">${xmlEscape(String(numericValue(edge.confidence, 0)))}</data></edge>`,
    )
    .join("");
  return `${header}<graphml xmlns="http://graphml.graphdrawing.org/xmlns">${keys}<graph edgedefault="directed">${nodeXml}${edgeXml}</graph></graphml>`;
}

export function gexfForGraph(nodes: GraphNode[], edges: GraphEdge[]): string {
  const nodeLookup = buildNodeLookup(nodes);
  const nodeAttributes = [
    `<attribute id="kind" title="kind" type="string"/>`,
    `<attribute id="entity_type" title="entity_type" type="string"/>`,
    `<attribute id="speech_act_mode" title="speech_act_mode" type="string"/>`,
    `<attribute id="storage_kind" title="storage_kind" type="string"/>`,
    `<attribute id="domain" title="domain" type="string"/>`,
    `<attribute id="source_kind" title="source_kind" type="string"/>`,
    `<attribute id="cluster_signature" title="cluster_signature" type="string"/>`,
  ].join("");
  const edgeAttributes = [
    `<attribute id="type" title="type" type="string"/>`,
    `<attribute id="evidence_label" title="evidence_label" type="string"/>`,
    `<attribute id="assertion_origin" title="assertion_origin" type="string"/>`,
    `<attribute id="confidence" title="confidence" type="double"/>`,
  ].join("");
  const nodeXml = nodes
    .map(
      (node) =>
        `<node id="${xmlEscape(node.id)}" label="${xmlEscape(nodeExportLabel(node))}"><attvalues><attvalue for="kind" value="${xmlEscape(
          String(node.kind ?? ""),
        )}"/><attvalue for="entity_type" value="${xmlEscape(String(node.entity_type ?? ""))}"/><attvalue for="speech_act_mode" value="${xmlEscape(
          String(node.speech_act_mode ?? ""),
        )}"/><attvalue for="storage_kind" value="${xmlEscape(String(node.storage_kind ?? ""))}"/><attvalue for="domain" value="${xmlEscape(
          String(node.domain ?? ""),
        )}"/><attvalue for="source_kind" value="${xmlEscape(
          String(node.source_kind ?? ""),
        )}"/><attvalue for="cluster_signature" value="${xmlEscape(String(node.cluster_signature ?? ""))}"/></attvalues></node>`,
    )
    .join("");
  const edgeXml = edges
    .map(
      (edge, index) =>
        `<edge id="${xmlEscape(edge.id || `edge-${index}`)}" source="${xmlEscape(edge.source)}" target="${xmlEscape(edge.target)}" type="directed" weight="${xmlEscape(
          String(numericValue(edge.weight, 1)),
        )}" label="${xmlEscape(edgeExportLabel(edge, nodeLookup))}"><attvalues><attvalue for="type" value="${xmlEscape(
          String(edge.type ?? ""),
        )}"/><attvalue for="evidence_label" value="${xmlEscape(String(edge.evidence_label ?? ""))}"/><attvalue for="assertion_origin" value="${xmlEscape(
          String(edge.assertion_origin ?? ""),
        )}"/><attvalue for="confidence" value="${xmlEscape(String(numericValue(edge.confidence, 0)))}"/></attvalues></edge>`,
    )
    .join("");
  return `<?xml version="1.0" encoding="UTF-8"?><gexf version="1.3" xmlns="http://gexf.net/1.3"><graph defaultedgetype="directed" mode="static"><attributes class="node">${nodeAttributes}</attributes><attributes class="edge">${edgeAttributes}</attributes><nodes>${nodeXml}</nodes><edges>${edgeXml}</edges></graph></gexf>`;
}

export function gdfForGraph(nodes: GraphNode[], edges: GraphEdge[]): string {
  const nodeHeader = "nodedef>name VARCHAR,label VARCHAR,kind VARCHAR,entity_type VARCHAR,speech_act_mode VARCHAR,storage_kind VARCHAR,domain VARCHAR,source_kind VARCHAR,cluster_signature VARCHAR,degree DOUBLE,recent_active_set_presence DOUBLE";
  const edgeHeader = "edgedef>node1 VARCHAR,node2 VARCHAR,label VARCHAR,weight DOUBLE,evidence_label VARCHAR,assertion_origin VARCHAR,confidence DOUBLE";
  const nodeLookup = buildNodeLookup(nodes);
  const nodeRows = nodes.map((node) =>
    [
      csvEscape(node.id),
      csvEscape(nodeExportLabel(node)),
      csvEscape(node.kind),
      csvEscape(node.entity_type),
      csvEscape(node.speech_act_mode),
      csvEscape(node.storage_kind),
      csvEscape(node.domain),
      csvEscape(node.source_kind),
      csvEscape(node.cluster_signature),
      numericValue(node.degree, 0),
      numericValue(node.recent_active_set_presence, 0),
    ].join(","),
  );
  const edgeRows = edges.map((edge) =>
    [
      csvEscape(edge.source),
      csvEscape(edge.target),
      csvEscape(edgeExportLabel(edge, nodeLookup)),
      numericValue(edge.weight, 1),
      csvEscape(edge.evidence_label),
      csvEscape(edge.assertion_origin),
      numericValue(edge.confidence, 0),
    ].join(","),
  );
  return [nodeHeader, ...nodeRows, edgeHeader, ...edgeRows].join("\n");
}

export function gmlForGraph(nodes: GraphNode[], edges: GraphEdge[]): string {
  const nodeLookup = buildNodeLookup(nodes);
  const nodeBlocks = nodes
    .map(
      (node) => `  node [
    id ${gmlValue(node.id)}
    label ${gmlValue(nodeExportLabel(node))}
    kind ${gmlValue(String(node.kind ?? ""))}
    entity_type ${gmlValue(String(node.entity_type ?? ""))}
    speech_act_mode ${gmlValue(String(node.speech_act_mode ?? ""))}
    storage_kind ${gmlValue(String(node.storage_kind ?? ""))}
    domain ${gmlValue(String(node.domain ?? ""))}
    source_kind ${gmlValue(String(node.source_kind ?? ""))}
    cluster_signature ${gmlValue(String(node.cluster_signature ?? ""))}
  ]`,
    )
    .join("\n");
  const edgeBlocks = edges
    .map(
      (edge) => `  edge [
    source ${gmlValue(edge.source)}
    target ${gmlValue(edge.target)}
    label ${gmlValue(edgeExportLabel(edge, nodeLookup))}
    weight ${numericValue(edge.weight, 1)}
    evidence_label ${gmlValue(String(edge.evidence_label ?? ""))}
    assertion_origin ${gmlValue(String(edge.assertion_origin ?? ""))}
    confidence ${numericValue(edge.confidence, 0)}
  ]`,
    )
    .join("\n");
  return `graph [\n  directed 1\n${nodeBlocks}${edgeBlocks ? `\n${edgeBlocks}` : ""}\n]\n`;
}

export function graphVizDotForGraph(nodes: GraphNode[], edges: GraphEdge[]): string {
  const nodeLookup = buildNodeLookup(nodes);
  const nodeLines = nodes
    .map(
      (node) =>
        `  ${dotValue(node.id)} [label=${dotValue(nodeExportLabel(node))}, kind=${dotValue(String(node.kind ?? ""))}, domain=${dotValue(
          String(node.domain ?? ""),
        )}, entity_type=${dotValue(String(node.entity_type ?? ""))}, speech_act_mode=${dotValue(String(node.speech_act_mode ?? ""))}, storage_kind=${dotValue(String(node.storage_kind ?? ""))}, source_kind=${dotValue(String(node.source_kind ?? ""))}];`,
    )
    .join("\n");
  const edgeLines = edges
    .map(
      (edge) =>
        `  ${dotValue(edge.source)} -> ${dotValue(edge.target)} [label=${dotValue(edgeExportLabel(edge, nodeLookup))}, weight=${dotValue(
          String(numericValue(edge.weight, 1)),
        )}, evidence_label=${dotValue(String(edge.evidence_label ?? ""))}, assertion_origin=${dotValue(String(edge.assertion_origin ?? ""))}];`,
    )
    .join("\n");
  return `digraph eden {\n  graph [charset="UTF-8"];\n  node [shape=ellipse];\n${nodeLines}${edgeLines ? `\n${edgeLines}` : ""}\n}\n`;
}

export function pajekNetForGraph(nodes: GraphNode[], edges: GraphEdge[]): string {
  const nodeIndex = new Map(nodes.map((node, index) => [node.id, index + 1]));
  const vertexLines = nodes.map((node, index) => `${index + 1} "${pajekEscape(nodeExportLabel(node))}"`);
  const edgeLines = edges
    .filter((edge) => nodeIndex.has(edge.source) && nodeIndex.has(edge.target))
    .map((edge) => `${nodeIndex.get(edge.source)} ${nodeIndex.get(edge.target)} ${numericValue(edge.weight, 1)}`);
  return [`*Vertices ${nodes.length}`, ...vertexLines, "*Arcs", ...edgeLines].join("\n");
}

export function netdrawVnaForGraph(nodes: GraphNode[], edges: GraphEdge[]): string {
  const nodeLookup = buildNodeLookup(nodes);
  const nodeLines = nodes.map((node) =>
    [
      vnaValue(node.id),
      vnaValue(nodeExportLabel(node)),
      vnaValue(String(node.kind ?? "")),
      vnaValue(String(node.entity_type ?? "")),
      vnaValue(String(node.speech_act_mode ?? "")),
      vnaValue(String(node.storage_kind ?? "")),
      vnaValue(String(node.domain ?? "")),
      vnaValue(String(node.source_kind ?? "")),
    ].join("\t"),
  );
  const edgeLines = edges.map((edge) =>
    [
      vnaValue(edge.source),
      vnaValue(edge.target),
      numericValue(edge.weight, 1),
      vnaValue(edgeExportLabel(edge, nodeLookup)),
      vnaValue(String(edge.evidence_label ?? "")),
      vnaValue(String(edge.assertion_origin ?? "")),
    ].join("\t"),
  );
  return [
    "*node data",
    "ID\tname\tkind\tentity_type\tspeech_act_mode\tstorage_kind\tdomain\tsource_kind",
    ...nodeLines,
    "*tie data",
    "from\tto\tstrength\ttype\tevidence_label\tassertion_origin",
    ...edgeLines,
  ].join("\n");
}

export function ucinetDlForGraph(nodes: GraphNode[], edges: GraphEdge[]): string {
  const nodeIndex = new Map(nodes.map((node, index) => [node.id, index + 1]));
  const labels = nodes.map((node) => ucinetLabel(node.id)).join(",");
  const edgeLines = edges
    .filter((edge) => nodeIndex.has(edge.source) && nodeIndex.has(edge.target))
    .map((edge) => `${nodeIndex.get(edge.source)} ${nodeIndex.get(edge.target)} ${numericValue(edge.weight, 1)}`);
  return [`dl n=${nodes.length} format=edgelist1`, "labels:", labels, "data:", ...edgeLines].join("\n");
}

export function tulipTlpForGraph(nodes: GraphNode[], edges: GraphEdge[]): string {
  const nodeIndex = new Map(nodes.map((node, index) => [node.id, index]));
  const nodeIds = nodes.map((_, index) => index).join(" ");
  const nodesBlock = nodeIds ? `(nodes ${nodeIds})` : "(nodes)";
  const edgeLines = edges
    .filter((edge) => nodeIndex.has(edge.source) && nodeIndex.has(edge.target))
    .map((edge, index) => `  (edge ${index} ${nodeIndex.get(edge.source)} ${nodeIndex.get(edge.target)})`)
    .join("\n");
  return `(tlp "2.0"\n  ${nodesBlock}${edgeLines ? `\n${edgeLines}` : ""}\n)\n`;
}

export function tgfForGraph(nodes: GraphNode[], edges: GraphEdge[]): string {
  const nodeLookup = buildNodeLookup(nodes);
  const ids = new Map(nodes.map((node, index) => [node.id, whitespaceSafeId(node.id, `n${index + 1}`)]));
  const nodeLines = nodes.map((node) => `${ids.get(node.id)} ${tgfLabel(nodeExportLabel(node))}`.trimEnd());
  const edgeLines = edges
    .filter((edge) => ids.has(edge.source) && ids.has(edge.target))
    .map((edge) => {
      const label = tgfEdgeLabel(edgeExportLabel(edge, nodeLookup), edge);
      return `${ids.get(edge.source)} ${ids.get(edge.target)}${label ? ` ${label}` : ""}`;
    });
  return [...nodeLines, "#", ...edgeLines].join("\n");
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
    edgeOpacityScale: 1,
  };
}

function csvEscape(value: unknown): string {
  const text = String(value ?? "");
  if (!/[",\n]/.test(text)) return text;
  return `"${text.replaceAll('"', '""')}"`;
}

function dotValue(value: string): string {
  return `"${value.replaceAll("\\", "\\\\").replaceAll('"', '\\"')}"`;
}

function gmlValue(value: unknown): string {
  const text = String(value ?? "");
  return `"${text.replaceAll("\\", "\\\\").replaceAll('"', '\\"').replaceAll("\n", "\\n")}"`;
}

function numericValue(value: unknown, fallback: number): number {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function pajekEscape(value: string): string {
  return value.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
}

function ucinetLabel(value: string): string {
  return value.replaceAll(",", "_").replace(/\s+/g, "_");
}

function vnaValue(value: string): string {
  const text = value.replaceAll('"', '""').replace(/\s+/g, " ").trim();
  if (!text) return '""';
  return /[\s"]/u.test(text) ? `"${text}"` : text;
}

function xmlEscape(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function whitespaceSafeId(value: string, fallback: string): string {
  const text = value.trim();
  if (text && !/\s/u.test(text)) return text;
  return fallback;
}

function tgfEdgeLabel(label: string, edge: GraphEdge): string {
  const segments = [label.trim()];
  const weight = numericValue(edge.weight, 1);
  if (weight !== 1) segments.push(`weight=${weight}`);
  return segments.filter(Boolean).join(" | ");
}

function tgfLabel(label: string): string {
  return label.replace(/\s+/g, " ").trim();
}

function dedupeNodesFromEdges(edges: GraphEdge[]): string[] {
  const seen = new Set<string>();
  for (const edge of edges) {
    seen.add(edge.source);
    seen.add(edge.target);
  }
  return [...seen];
}
