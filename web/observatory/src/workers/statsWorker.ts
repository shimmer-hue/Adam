import Graph from "graphology";
import louvain from "graphology-communities-louvain";
import betweenness from "graphology-metrics/centrality/betweenness";
import pagerank from "graphology-metrics/centrality/pagerank";
import { density } from "graphology-metrics/graph/density";

type NodeRecord = { id: string; label?: string; kind?: string };
type EdgeRecord = { id: string; source: string; target: string; weight?: number; type?: string };

type StatsRequest = {
  type: "run";
  nodes: NodeRecord[];
  edges: EdgeRecord[];
};

self.onmessage = (event: MessageEvent<StatsRequest>) => {
  const { nodes, edges } = event.data;
  try {
    const graph = new Graph();
    for (const node of nodes) graph.addNode(node.id, { ...node });
    for (const edge of edges) {
      if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target)) continue;
      if (graph.hasEdge(edge.id)) continue;
      graph.addEdgeWithKey(edge.id, edge.source, edge.target, { weight: Number(edge.weight ?? 1), type: edge.type ?? "" });
    }

    const components = connectedComponents(nodes, edges);
    const clustering = clusteringByNode(nodes, edges);
    const weightedDegree = weightedDegreeByNode(nodes, edges);
    const pagerankScores = safeMetric(() => pagerank(graph, { getEdgeWeight: "weight" }), {});
    const betweennessScores = safeMetric(() => betweenness(graph, { getEdgeWeight: "weight" }), {});
    const louvainResult = safeMetric(() => louvain.detailed(graph), { communities: {}, modularity: 0 });
    const shortestPath = shortestPathSample(nodes, edges, components);

    const rankings = {
      degree: topRankings(nodes, (node) => degreeForNode(node.id, edges)),
      weighted_degree: topRankings(nodes, (node) => weightedDegree[node.id] ?? 0),
      pagerank: topRankings(nodes, (node) => Number((pagerankScores as Record<string, number>)[node.id] ?? 0)),
      betweenness: topRankings(nodes, (node) => Number((betweennessScores as Record<string, number>)[node.id] ?? 0)),
    };

    self.postMessage({
      type: "done",
      summary: {
        nodes: nodes.length,
        edges: edges.length,
        density: Number(density(graph).toFixed(4)),
        components: components.length,
        largest_component_size: Math.max(0, ...components.map((component) => component.length)),
        reciprocity: Number(reciprocity(edges).toFixed(4)),
        avg_clustering_coefficient: average(Object.values(clustering)),
        modularity: Number(Number((louvainResult as any).modularity ?? 0).toFixed(4)),
        shortest_path_sample: shortestPath,
      },
      rankings,
      communities: summarizeCommunities((louvainResult as any).communities ?? {}),
      clustering,
      weightedDegree,
    });
  } catch (error) {
    self.postMessage({
      type: "error",
      error: error instanceof Error ? error.message : String(error),
    });
  }
};

function safeMetric<T>(fn: () => T, fallback: T): T {
  try {
    return fn();
  } catch {
    return fallback;
  }
}

function connectedComponents(nodes: NodeRecord[], edges: EdgeRecord[]): string[][] {
  const adjacency = new Map<string, Set<string>>();
  for (const node of nodes) adjacency.set(node.id, new Set());
  for (const edge of edges) {
    adjacency.get(edge.source)?.add(edge.target);
    adjacency.get(edge.target)?.add(edge.source);
  }
  const visited = new Set<string>();
  const components: string[][] = [];
  for (const node of nodes) {
    if (visited.has(node.id)) continue;
    const queue = [node.id];
    const component: string[] = [];
    visited.add(node.id);
    while (queue.length) {
      const current = queue.shift()!;
      component.push(current);
      for (const neighbor of adjacency.get(current) ?? []) {
        if (visited.has(neighbor)) continue;
        visited.add(neighbor);
        queue.push(neighbor);
      }
    }
    components.push(component.sort());
  }
  return components.sort((left, right) => right.length - left.length);
}

function degreeForNode(nodeId: string, edges: EdgeRecord[]): number {
  let total = 0;
  for (const edge of edges) {
    if (edge.source === nodeId || edge.target === nodeId) total += 1;
  }
  return total;
}

function weightedDegreeByNode(nodes: NodeRecord[], edges: EdgeRecord[]): Record<string, number> {
  const result: Record<string, number> = Object.fromEntries(nodes.map((node) => [node.id, 0]));
  for (const edge of edges) {
    const weight = Number(edge.weight ?? 1);
    result[edge.source] = Number((result[edge.source] ?? 0) + weight);
    result[edge.target] = Number((result[edge.target] ?? 0) + weight);
  }
  return result;
}

function clusteringByNode(nodes: NodeRecord[], edges: EdgeRecord[]): Record<string, number> {
  const adjacency = new Map<string, Set<string>>();
  for (const node of nodes) adjacency.set(node.id, new Set());
  for (const edge of edges) {
    adjacency.get(edge.source)?.add(edge.target);
    adjacency.get(edge.target)?.add(edge.source);
  }
  const result: Record<string, number> = {};
  for (const node of nodes) {
    const neighbors = [...(adjacency.get(node.id) ?? [])];
    if (neighbors.length < 2) {
      result[node.id] = 0;
      continue;
    }
    let links = 0;
    for (let i = 0; i < neighbors.length; i += 1) {
      for (let j = i + 1; j < neighbors.length; j += 1) {
        if (adjacency.get(neighbors[i])?.has(neighbors[j])) links += 1;
      }
    }
    result[node.id] = Number((links / ((neighbors.length * (neighbors.length - 1)) / 2)).toFixed(4));
  }
  return result;
}

function reciprocity(edges: EdgeRecord[]): number {
  const keys = new Set(edges.map((edge) => `${edge.source}::${edge.target}`));
  let mutual = 0;
  for (const edge of edges) {
    if (keys.has(`${edge.target}::${edge.source}`)) mutual += 1;
  }
  return edges.length ? mutual / edges.length : 0;
}

function shortestPathSample(nodes: NodeRecord[], edges: EdgeRecord[], components: string[][]): { source: string | null; target: string | null; distance: number | null } {
  const largest = components[0] ?? [];
  if (largest.length < 2) return { source: largest[0] ?? null, target: null, distance: null };
  const adjacency = new Map<string, Set<string>>();
  for (const node of nodes) adjacency.set(node.id, new Set());
  for (const edge of edges) {
    adjacency.get(edge.source)?.add(edge.target);
    adjacency.get(edge.target)?.add(edge.source);
  }
  const source = largest[0];
  const target = largest[largest.length - 1];
  const queue: Array<{ node: string; distance: number }> = [{ node: source, distance: 0 }];
  const visited = new Set<string>([source]);
  while (queue.length) {
    const current = queue.shift()!;
    if (current.node === target) {
      return { source, target, distance: current.distance };
    }
    for (const neighbor of adjacency.get(current.node) ?? []) {
      if (visited.has(neighbor)) continue;
      visited.add(neighbor);
      queue.push({ node: neighbor, distance: current.distance + 1 });
    }
  }
  return { source, target, distance: null };
}

function topRankings(nodes: NodeRecord[], score: (node: NodeRecord) => number): Array<{ id: string; label: string; score: number }> {
  return nodes
    .map((node) => ({
      id: node.id,
      label: String(node.label ?? node.id),
      score: Number(score(node) || 0),
    }))
    .sort((left, right) => right.score - left.score)
    .slice(0, 8)
    .map((item) => ({ ...item, score: Number(item.score.toFixed(4)) }));
}

function summarizeCommunities(communities: Record<string, number>): Array<{ community: number; size: number }> {
  const counts = new Map<number, number>();
  for (const value of Object.values(communities)) {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([community, size]) => ({ community, size }))
    .sort((left, right) => right.size - left.size)
    .slice(0, 8);
}

function average(values: number[]): number {
  if (!values.length) return 0;
  return Number((values.reduce((total, value) => total + value, 0) / values.length).toFixed(4));
}
