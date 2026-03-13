import Graph from "graphology";
import { circular } from "graphology-layout";
import forceAtlas2 from "graphology-layout-forceatlas2";
import noverlap from "graphology-layout-noverlap";

type NodeRecord = {
  id: string;
  degree?: number;
  size?: number;
  clusterKey?: string;
  latitude?: number;
  longitude?: number;
};
type EdgeRecord = { id: string; source: string; target: string; weight?: number };
type CoordinateMap = Record<string, { x: number; y: number }>;

type LayoutRequest = {
  type: "run";
  runId: string;
  layoutId: string;
  nodes: NodeRecord[];
  edges: EdgeRecord[];
  initialPositions: CoordinateMap;
  settings: Record<string, any>;
  selectedNodeIds: string[];
};

type ControlRequest = {
  type: "pause" | "resume" | "cancel";
  runId: string;
};

let activeRunId: string | null = null;
let paused = false;
let cancelled = false;

self.onmessage = async (event: MessageEvent<LayoutRequest | ControlRequest>) => {
  const message = event.data;
  if (message.type === "pause") {
    if (message.runId === activeRunId) paused = true;
    return;
  }
  if (message.type === "resume") {
    if (message.runId === activeRunId) paused = false;
    return;
  }
  if (message.type === "cancel") {
    if (message.runId === activeRunId) cancelled = true;
    return;
  }

  activeRunId = message.runId;
  paused = false;
  cancelled = false;

  try {
    const coordinateMap = await runLayout(message);
    if (cancelled) {
      self.postMessage({ type: "cancelled", runId: message.runId });
      return;
    }
    self.postMessage({
      type: "done",
      runId: message.runId,
      layoutId: message.layoutId,
      coordinateMap,
    });
  } catch (error) {
    self.postMessage({
      type: "error",
      runId: message.runId,
      error: error instanceof Error ? error.message : String(error),
    });
  } finally {
    activeRunId = null;
    paused = false;
    cancelled = false;
  }
};

async function runLayout(request: LayoutRequest): Promise<CoordinateMap> {
  const graph = new Graph();

  for (const node of request.nodes) {
    const seed = request.initialPositions[node.id] ?? { x: Math.random() - 0.5, y: Math.random() - 0.5 };
    graph.addNode(node.id, {
      x: seed.x,
      y: seed.y,
      size: Math.max(1, Number(node.size ?? Math.max(2, node.degree ?? 1))),
      degree: Number(node.degree ?? 0),
      clusterKey: String(node.clusterKey ?? "unclustered"),
      latitude: Number(node.latitude ?? Number.NaN),
      longitude: Number(node.longitude ?? Number.NaN),
    });
  }

  for (const edge of request.edges) {
    if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target)) continue;
    if (graph.hasEdge(edge.id)) continue;
    graph.addEdgeWithKey(edge.id, edge.source, edge.target, {
      weight: Number(edge.weight ?? 1),
    });
  }

  if (request.layoutId === "forceatlas2") {
    await runForceAtlasVariant(graph, request, {});
  } else if (request.layoutId === "linlog") {
    await runForceAtlasVariant(graph, request, {
      linLogMode: true,
      gravity: Number(request.settings.gravity ?? 0.6),
      scalingRatio: Number(request.settings.scalingRatio ?? 6),
      barnesHutOptimize: true,
    });
  } else if (request.layoutId === "fruchterman_reingold") {
    await runFruchtermanReingold(graph, request);
  } else if (request.layoutId === "kamada_kawai") {
    await runKamadaKawai(graph, request);
  } else if (request.layoutId === "sugiyama_layered") {
    applyLayeredLayout(graph, request);
  } else if (request.layoutId === "noverlap") {
    noverlap.assign(graph, {
      maxIterations: Number(request.settings.maxIterations ?? 160),
      settings: {
        margin: Number(request.settings.margin ?? 4),
        ratio: Number(request.settings.ratio ?? 1.2),
        speed: Number(request.settings.speed ?? 3),
        gridSize: Number(request.settings.gridSize ?? 20),
      },
    });
  } else if (request.layoutId === "simple_circular") {
    applyCircularLayout(graph, graph.nodes(), {
      radius: Number(request.settings.radius ?? 1.2),
      startAngle: Number(request.settings.startAngle ?? 0),
    });
  } else if (request.layoutId === "circular_degree") {
    const ordered = graph.nodes().sort((left, right) => graph.degree(right) - graph.degree(left) || left.localeCompare(right));
    applyCircularLayout(graph, ordered, {
      radius: Number(request.settings.radius ?? 1.2),
      startAngle: Number(request.settings.startAngle ?? 0),
    });
  } else if (request.layoutId === "circular_community") {
    applyCommunityCircleLayout(graph, request);
  } else if (request.layoutId === "community_clusters") {
    applyCommunityClusterLayout(graph, request);
  } else if (request.layoutId === "radial") {
    applyRadialLayout(graph, request);
  } else if (request.layoutId === "radial_tree") {
    applyRadialLayout(graph, request);
  } else if (request.layoutId === "fixed_coordinate") {
    applyFixedCoordinateLayout(graph, request);
  } else {
    circular.assign(graph, { scale: 1 });
  }

  if (request.settings.preventOverlap || request.settings.adjustSizes) {
    noverlap.assign(graph, {
      maxIterations: Number(request.settings.maxIterations ?? 120),
      settings: {
        margin: Number(request.settings.margin ?? 4),
        ratio: Number(request.settings.ratio ?? 1.2),
        speed: Number(request.settings.speed ?? 3),
        gridSize: Number(request.settings.gridSize ?? 20),
      },
    });
  }

  const coordinateMap: CoordinateMap = {};
  graph.forEachNode((node, attributes) => {
    coordinateMap[node] = {
      x: Number(attributes.x ?? 0),
      y: Number(attributes.y ?? 0),
    };
  });
  return coordinateMap;
}

async function runForceAtlasVariant(graph: Graph, request: LayoutRequest, overrides: Record<string, any>): Promise<void> {
  const totalIterations = Number(request.settings.iterations ?? 160);
  const inferred = forceAtlas2.inferSettings(graph);
  const settings = {
    ...inferred,
    scalingRatio: Number(request.settings.scalingRatio ?? inferred.scalingRatio ?? 8),
    gravity: Number(request.settings.gravity ?? inferred.gravity ?? 1),
    strongGravityMode: Boolean(request.settings.strongGravityMode),
    barnesHutOptimize: Boolean(request.settings.barnesHutOptimize ?? true),
    barnesHutTheta: Number(request.settings.barnesHutTheta ?? inferred.barnesHutTheta ?? 1.2),
    linLogMode: Boolean(request.settings.linLogMode),
    outboundAttractionDistribution: Boolean(request.settings.outboundAttractionDistribution),
    edgeWeightInfluence: Number(request.settings.edgeWeightInfluence ?? 1),
    adjustSizes: Boolean(request.settings.adjustSizes),
    slowDown: Number(request.settings.slowDown ?? 1),
    ...overrides,
  };

  let completed = 0;
  while (completed < totalIterations) {
    if (cancelled) return;
    await waitIfPaused();
    const chunk = Math.min(20, totalIterations - completed);
    forceAtlas2.assign(graph, {
      iterations: chunk,
      settings,
      getEdgeWeight: "weight",
    });
    completed += chunk;
    self.postMessage({
      type: "progress",
      runId: request.runId,
      progress: completed / Math.max(1, totalIterations),
      phase: request.layoutId,
    });
    await yieldTick();
  }
}

async function runFruchtermanReingold(graph: Graph, request: LayoutRequest): Promise<void> {
  const nodes = graph.nodes();
  const iterations = Number(request.settings.iterations ?? 120);
  const gravity = Number(request.settings.gravity ?? 0.08);
  const speed = Number(request.settings.speed ?? 0.18);
  const cooling = Number(request.settings.cooling ?? 0.95);
  let temperature = 0.28;
  const area = Math.max(1, nodes.length);
  const idealDistance = Math.sqrt(area);

  for (let iteration = 0; iteration < iterations; iteration += 1) {
    if (cancelled) return;
    await waitIfPaused();
    const displacement = new Map<string, { x: number; y: number }>(nodes.map((node) => [node, { x: 0, y: 0 }]));

    for (let i = 0; i < nodes.length; i += 1) {
      const left = nodes[i];
      const leftAttr = graph.getNodeAttributes(left);
      for (let j = i + 1; j < nodes.length; j += 1) {
        const right = nodes[j];
        const rightAttr = graph.getNodeAttributes(right);
        const dx = Number(leftAttr.x ?? 0) - Number(rightAttr.x ?? 0);
        const dy = Number(leftAttr.y ?? 0) - Number(rightAttr.y ?? 0);
        const distance = Math.max(0.01, Math.hypot(dx, dy));
        const repulsion = (idealDistance * idealDistance) / distance;
        const rx = (dx / distance) * repulsion;
        const ry = (dy / distance) * repulsion;
        displacement.get(left)!.x += rx;
        displacement.get(left)!.y += ry;
        displacement.get(right)!.x -= rx;
        displacement.get(right)!.y -= ry;
      }
    }

    graph.forEachEdge((edgeKey, attributes, source, target) => {
      const leftAttr = graph.getNodeAttributes(source);
      const rightAttr = graph.getNodeAttributes(target);
      const dx = Number(leftAttr.x ?? 0) - Number(rightAttr.x ?? 0);
      const dy = Number(leftAttr.y ?? 0) - Number(rightAttr.y ?? 0);
      const distance = Math.max(0.01, Math.hypot(dx, dy));
      const attraction = (distance * distance) / idealDistance;
      const ax = (dx / distance) * attraction;
      const ay = (dy / distance) * attraction;
      displacement.get(source)!.x -= ax;
      displacement.get(source)!.y -= ay;
      displacement.get(target)!.x += ax;
      displacement.get(target)!.y += ay;
    });

    graph.forEachNode((node, attributes) => {
      const delta = displacement.get(node)!;
      const distance = Math.max(0.01, Math.hypot(delta.x, delta.y));
      const step = Math.min(temperature, distance) * speed;
      graph.setNodeAttribute(node, "x", Number(attributes.x ?? 0) + (delta.x / distance) * step);
      graph.setNodeAttribute(node, "y", Number(attributes.y ?? 0) + (delta.y / distance) * step - gravity * 0.01);
    });

    temperature *= cooling;
    self.postMessage({
      type: "progress",
      runId: request.runId,
      progress: (iteration + 1) / Math.max(1, iterations),
      phase: "fruchterman_reingold",
    });
    await yieldTick();
  }
}

async function runKamadaKawai(graph: Graph, request: LayoutRequest): Promise<void> {
  const nodes = graph.nodes();
  if (!nodes.length) return;
  applyCircularLayout(graph, nodes, { radius: 1, startAngle: 0 });
  const distances = shortestPathDistances(graph);
  const iterations = Number(request.settings.iterations ?? 80);
  const springLength = Number(request.settings.springLength ?? 1.4);
  const springStrength = Number(request.settings.springStrength ?? 0.08);
  const cooling = Number(request.settings.cooling ?? 0.18);

  for (let iteration = 0; iteration < iterations; iteration += 1) {
    if (cancelled) return;
    await waitIfPaused();
    for (const left of nodes) {
      const leftAttr = graph.getNodeAttributes(left);
      let gradientX = 0;
      let gradientY = 0;
      for (const right of nodes) {
        if (left === right) continue;
        const rightAttr = graph.getNodeAttributes(right);
        const graphDistance = Math.max(1, distances.get(left)?.get(right) ?? nodes.length);
        const idealDistance = springLength * graphDistance;
        const spring = springStrength / Math.max(1, graphDistance * graphDistance);
        const dx = Number(leftAttr.x ?? 0) - Number(rightAttr.x ?? 0);
        const dy = Number(leftAttr.y ?? 0) - Number(rightAttr.y ?? 0);
        const distance = Math.max(0.01, Math.hypot(dx, dy));
        gradientX += spring * (dx - (idealDistance * dx) / distance);
        gradientY += spring * (dy - (idealDistance * dy) / distance);
      }
      graph.setNodeAttribute(left, "x", Number(leftAttr.x ?? 0) - gradientX * cooling);
      graph.setNodeAttribute(left, "y", Number(leftAttr.y ?? 0) - gradientY * cooling);
    }
    recenterGraph(graph);
    self.postMessage({
      type: "progress",
      runId: request.runId,
      progress: (iteration + 1) / Math.max(1, iterations),
      phase: "kamada_kawai",
    });
    await yieldTick();
  }
}

function applyCircularLayout(graph: Graph, orderedNodes: string[], options: { radius: number; startAngle: number }): void {
  const radius = Math.max(0.1, Number(options.radius ?? 1));
  const startAngle = Number(options.startAngle ?? 0);
  orderedNodes.forEach((node, index) => {
    const angle = startAngle + ((Math.PI * 2) / Math.max(1, orderedNodes.length)) * index;
    graph.setNodeAttribute(node, "x", Math.cos(angle) * radius);
    graph.setNodeAttribute(node, "y", Math.sin(angle) * radius);
  });
}

function applyCommunityCircleLayout(graph: Graph, request: LayoutRequest): void {
  const grouped = clusterGroups(graph);
  const clusterSpacing = Number(request.settings.clusterSpacing ?? 2.4);
  const intraClusterRadius = Number(request.settings.intraClusterRadius ?? 0.45);
  const startAngle = Number(request.settings.startAngle ?? 0);
  const groups = [...grouped.entries()].sort((left, right) => right[1].length - left[1].length || left[0].localeCompare(right[0]));
  groups.forEach(([clusterKey, members], index) => {
    const angle = startAngle + ((Math.PI * 2) / Math.max(1, groups.length)) * index;
    const centerX = Math.cos(angle) * clusterSpacing;
    const centerY = Math.sin(angle) * clusterSpacing;
    members.sort((left, right) => graph.degree(right) - graph.degree(left) || left.localeCompare(right));
    members.forEach((node, memberIndex) => {
      const memberAngle = ((Math.PI * 2) / Math.max(1, members.length)) * memberIndex;
      graph.setNodeAttribute(node, "x", centerX + Math.cos(memberAngle) * intraClusterRadius);
      graph.setNodeAttribute(node, "y", centerY + Math.sin(memberAngle) * intraClusterRadius);
      graph.setNodeAttribute(node, "clusterKey", clusterKey);
    });
  });
}

function applyCommunityClusterLayout(graph: Graph, request: LayoutRequest): void {
  const grouped = clusterGroups(graph);
  const clusterSpacing = Number(request.settings.clusterSpacing ?? 2.8);
  const intraClusterRadius = Number(request.settings.intraClusterRadius ?? 0.5);
  const orderBy = String(request.settings.orderBy ?? "cluster_size");
  const groups = [...grouped.entries()].sort((left, right) => {
    if (orderBy === "label") return left[0].localeCompare(right[0]);
    return right[1].length - left[1].length || left[0].localeCompare(right[0]);
  });
  groups.forEach(([clusterKey, members], index) => {
    const angle = ((Math.PI * 2) / Math.max(1, groups.length)) * index;
    const centerX = Math.cos(angle) * clusterSpacing;
    const centerY = Math.sin(angle) * clusterSpacing;
    members.sort();
    members.forEach((node, memberIndex) => {
      const memberAngle = ((Math.PI * 2) / Math.max(1, members.length)) * memberIndex;
      graph.setNodeAttribute(node, "x", centerX + Math.cos(memberAngle) * intraClusterRadius);
      graph.setNodeAttribute(node, "y", centerY + Math.sin(memberAngle) * intraClusterRadius);
      graph.setNodeAttribute(node, "clusterKey", clusterKey);
    });
  });
}

function applyLayeredLayout(graph: Graph, request: LayoutRequest): void {
  const orientation = String(request.settings.orientation ?? "top_down");
  const layerSpacing = Number(request.settings.layerSpacing ?? 1.6);
  const nodeSpacing = Number(request.settings.nodeSpacing ?? 1.2);
  const nodes = graph.nodes();
  const outgoing = new Map<string, string[]>(nodes.map((node) => [node, []]));
  const indegree = new Map<string, number>(nodes.map((node) => [node, 0]));
  const layerByNode = new Map<string, number>(nodes.map((node) => [node, 0]));

  for (const edge of request.edges) {
    if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target) || edge.source === edge.target) continue;
    outgoing.get(edge.source)?.push(edge.target);
    indegree.set(edge.target, (indegree.get(edge.target) ?? 0) + 1);
  }

  const pending = new Set(nodes);
  const queue = nodes.filter((node) => (indegree.get(node) ?? 0) === 0).sort();
  while (pending.size) {
    if (!queue.length) {
      const fallback = [...pending].sort((left, right) => (indegree.get(left) ?? 0) - (indegree.get(right) ?? 0) || left.localeCompare(right))[0];
      queue.push(fallback);
    }
    const current = queue.shift()!;
    if (!pending.has(current)) continue;
    pending.delete(current);
    const currentLayer = layerByNode.get(current) ?? 0;
    for (const target of outgoing.get(current) ?? []) {
      layerByNode.set(target, Math.max(layerByNode.get(target) ?? 0, currentLayer + 1));
      indegree.set(target, Math.max(0, (indegree.get(target) ?? 0) - 1));
      if ((indegree.get(target) ?? 0) === 0) queue.push(target);
    }
  }

  const grouped = new Map<number, string[]>();
  for (const node of nodes) {
    const layer = layerByNode.get(node) ?? 0;
    const bucket = grouped.get(layer) ?? [];
    bucket.push(node);
    grouped.set(layer, bucket);
  }

  [...grouped.entries()]
    .sort((left, right) => left[0] - right[0])
    .forEach(([layer, members]) => {
      members.sort((left, right) => graph.degree(right) - graph.degree(left) || left.localeCompare(right));
      members.forEach((node, index) => {
        const centered = index - (members.length - 1) / 2;
        if (orientation === "left_right") {
          graph.setNodeAttribute(node, "x", layer * layerSpacing);
          graph.setNodeAttribute(node, "y", centered * nodeSpacing);
        } else {
          graph.setNodeAttribute(node, "x", centered * nodeSpacing);
          graph.setNodeAttribute(node, "y", layer * layerSpacing);
        }
      });
    });
}

function applyFixedCoordinateLayout(graph: Graph, request: LayoutRequest): void {
  const anchoredNodes = graph
    .nodes()
    .filter((node) => Number.isFinite(Number(graph.getNodeAttribute(node, "latitude"))) && Number.isFinite(Number(graph.getNodeAttribute(node, "longitude"))));
  if (!anchoredNodes.length) {
    if (!Boolean(request.settings.fallbackToInitial ?? true)) {
      applyCircularLayout(graph, graph.nodes(), { radius: 1, startAngle: 0 });
    }
    return;
  }

  const latitudes = anchoredNodes.map((node) => Number(graph.getNodeAttribute(node, "latitude")));
  const longitudes = anchoredNodes.map((node) => Number(graph.getNodeAttribute(node, "longitude")));
  const latMin = Math.min(...latitudes);
  const latMax = Math.max(...latitudes);
  const lonMin = Math.min(...longitudes);
  const lonMax = Math.max(...longitudes);

  for (const node of anchoredNodes) {
    const latitude = Number(graph.getNodeAttribute(node, "latitude"));
    const longitude = Number(graph.getNodeAttribute(node, "longitude"));
    graph.setNodeAttribute(node, "x", normalize(longitude, lonMin, lonMax));
    graph.setNodeAttribute(node, "y", -normalize(latitude, latMin, latMax));
  }
}

function applyRadialLayout(graph: Graph, request: LayoutRequest): void {
  const rootNodeId = resolveRadialRoot(graph, request);
  const depthByNode = new Map<string, number>([[rootNodeId, 0]]);
  const queue = [rootNodeId];
  const spread = Number(request.settings.spread ?? Math.PI * 2);

  while (queue.length) {
    const current = queue.shift()!;
    const currentDepth = depthByNode.get(current) ?? 0;
    graph.forEachNeighbor(current, (neighbor) => {
      if (depthByNode.has(neighbor)) return;
      depthByNode.set(neighbor, currentDepth + 1);
      queue.push(neighbor);
    });
  }

  const ringSpacing = Number(request.settings.ringSpacing ?? 1);
  const grouped = new Map<number, string[]>();
  for (const node of graph.nodes()) {
    const depth = depthByNode.get(node) ?? 0;
    const bucket = grouped.get(depth) ?? [];
    bucket.push(node);
    grouped.set(depth, bucket);
  }

  for (const [depth, members] of grouped.entries()) {
    if (depth === 0) {
      graph.setNodeAttribute(rootNodeId, "x", 0);
      graph.setNodeAttribute(rootNodeId, "y", 0);
      continue;
    }
    members.sort();
    members.forEach((node, index) => {
      const angle = (spread * index) / Math.max(1, members.length);
      graph.setNodeAttribute(node, "x", Math.cos(angle) * depth * ringSpacing);
      graph.setNodeAttribute(node, "y", Math.sin(angle) * depth * ringSpacing);
    });
  }
}

function resolveRadialRoot(graph: Graph, request: LayoutRequest): string {
  const explicit = String(request.settings.rootNodeId ?? "").trim();
  if (explicit && graph.hasNode(explicit)) return explicit;
  const selected = request.selectedNodeIds.find((nodeId) => graph.hasNode(nodeId));
  if (selected) return selected;
  let bestNode = graph.nodes()[0];
  let bestDegree = -1;
  graph.forEachNode((node) => {
    const degree = graph.degree(node);
    if (degree > bestDegree) {
      bestNode = node;
      bestDegree = degree;
    }
  });
  return bestNode;
}

async function waitIfPaused(): Promise<void> {
  while (paused && !cancelled) {
    await new Promise((resolve) => setTimeout(resolve, 30));
  }
}

async function yieldTick(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

function shortestPathDistances(graph: Graph): Map<string, Map<string, number>> {
  const adjacency = new Map<string, string[]>();
  graph.forEachNode((node) => {
    const neighbors: string[] = [];
    graph.forEachNeighbor(node, (neighbor) => neighbors.push(neighbor));
    adjacency.set(node, neighbors);
  });
  const distances = new Map<string, Map<string, number>>();
  for (const start of graph.nodes()) {
    const seen = new Map<string, number>([[start, 0]]);
    const queue = [start];
    while (queue.length) {
      const current = queue.shift()!;
      const depth = seen.get(current) ?? 0;
      for (const neighbor of adjacency.get(current) ?? []) {
        if (seen.has(neighbor)) continue;
        seen.set(neighbor, depth + 1);
        queue.push(neighbor);
      }
    }
    distances.set(start, seen);
  }
  return distances;
}

function clusterGroups(graph: Graph): Map<string, string[]> {
  const grouped = new Map<string, string[]>();
  graph.forEachNode((node, attributes) => {
    const key = String(attributes.clusterKey ?? "unclustered");
    const bucket = grouped.get(key) ?? [];
    bucket.push(node);
    grouped.set(key, bucket);
  });
  return grouped;
}

function recenterGraph(graph: Graph): void {
  const nodes = graph.nodes();
  if (!nodes.length) return;
  let sumX = 0;
  let sumY = 0;
  nodes.forEach((node) => {
    sumX += Number(graph.getNodeAttribute(node, "x") ?? 0);
    sumY += Number(graph.getNodeAttribute(node, "y") ?? 0);
  });
  const centerX = sumX / nodes.length;
  const centerY = sumY / nodes.length;
  nodes.forEach((node) => {
    graph.setNodeAttribute(node, "x", Number(graph.getNodeAttribute(node, "x") ?? 0) - centerX);
    graph.setNodeAttribute(node, "y", Number(graph.getNodeAttribute(node, "y") ?? 0) - centerY);
  });
}

function normalize(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return 0;
  if (!Number.isFinite(min) || !Number.isFinite(max) || Math.abs(max - min) < 1e-9) return 0;
  return ((value - min) / (max - min) - 0.5) * 2;
}
