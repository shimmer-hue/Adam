import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./components/GraphPanel", () => ({
  default: ({
    nodes,
    ariaLabel,
    selectedNodeIds = [],
    selectedEdgeId = null,
    focusNodeIds = [],
    focusVersion = 0,
    onSelectNode,
  }: {
    nodes: Array<Record<string, any>>;
    ariaLabel?: string;
    selectedNodeIds?: string[];
    selectedEdgeId?: string | null;
    focusNodeIds?: string[];
    focusVersion?: number;
    onSelectNode?: (nodeId: string, additive: boolean) => void;
  }) => (
    <div data-testid="graph-panel">
      <div>{`${ariaLabel ?? "Graph canvas"}:${nodes.length}:nodesSelected=${selectedNodeIds.length}:edgeSelected=${selectedEdgeId ?? "none"}:focusNodes=${focusNodeIds.length}:focusVersion=${focusVersion}`}</div>
      {nodes.slice(0, 5).map((node) => (
        <button key={String(node.id)} onClick={() => onSelectNode?.(String(node.id), selectedNodeIds.length > 0)} type="button">
          {`select-${node.id}`}
        </button>
      ))}
    </div>
  ),
}));

vi.mock("./components/BasinPanel", () => ({
  default: ({ liftMode }: { liftMode: string }) => <div data-testid="basin-panel">basin:{liftMode}</div>,
}));

vi.mock("./components/TanakhPanel", () => ({
  default: () => <div data-testid="tanakh-panel">tanakh</div>,
}));

class EventSourceStub {
  addEventListener() {
    return undefined;
  }

  close() {
    return undefined;
  }
}

const workerInstances: WorkerStub[] = [];

class WorkerStub {
  onmessage: ((event: MessageEvent<any>) => void) | null = null;
  onerror: ((event: ErrorEvent) => void) | null = null;
  onmessageerror: (() => void) | null = null;
  messages: any[] = [];
  scriptUrl: string;

  constructor(url: string | URL) {
    this.scriptUrl = String(url);
    workerInstances.push(this);
  }

  postMessage(message: any) {
    this.messages.push(message);
  }

  terminate() {
    return undefined;
  }

  emit(data: any) {
    this.onmessage?.({ data } as MessageEvent<any>);
  }
}

function response(payload: unknown) {
  return Promise.resolve({
    ok: true,
    statusText: "OK",
    json: async () => payload,
  });
}

function graphPayload() {
  return {
    export_manifest_id: "manifest-graph",
    source_graph_hash: "graph-hash-1",
    graph_modes: ["Semantic Map", "Assemblies", "Runtime", "Active Set", "Compare"],
    assembly_render_modes: ["hulls", "collapsed-meta-node", "hidden"],
    interaction_modes: ["INSPECT", "MEASURE", "EDIT", "ABLATE", "COMPARE"],
    evidence_legend: { OPERATOR_ASSERTED: {}, OPERATOR_REFINED: {}, DERIVED: {} },
    view_modes: { force: "Force", spectral: "Spectral" },
    layout_families: [
      { id: "force_directed", label: "1. Force-Directed Layout Algorithms", description: "Layouts that balance attraction and repulsion.", bestFor: ["exploration"] },
    ],
    layout_catalog: {
      forceatlas2: {
        id: "forceatlas2",
        label: "ForceAtlas2",
        summary: "Nodes repel while edges pull related nodes together.",
        usedFor: "General semantic exploration",
        familyId: "force_directed",
        subgroupLabel: "Runnable",
        bestFor: ["exploration"],
        status: "runnable",
        controls: [{ key: "iterations", label: "Iterations", input: "number", min: 10, max: 300, step: 10 }],
      },
      openord: {
        id: "openord",
        label: "OpenOrd",
        summary: "Large-cluster overview terrain item.",
        usedFor: "Reference-only landscape entry",
        familyId: "force_directed",
        subgroupLabel: "Reference",
        bestFor: ["large overview"],
        status: "reference",
        controls: [],
      },
    },
    layout_defaults: {
      coordinate_mode: "force",
      forceatlas2: { iterations: 160 },
      heavy_graph_node_cap: 320,
    },
    appearance_dimensions: {
      node_color: ["kind", "domain", "cluster", "evidence_label"],
      node_size: ["uniform", "degree"],
      edge_color: ["type", "evidence_label"],
      edge_opacity: ["weight", "uniform"],
      label_modes: ["selection", "all", "none"],
    },
    filters: {
      kinds: ["meme", "memode"],
      domains: ["knowledge", "behavior"],
      evidence_labels: ["OPERATOR_ASSERTED", "AUTO_DERIVED"],
      sessions: ["session-1"],
      sources: ["operator", "document"],
      verdicts: ["accept"],
    },
    statistics_capabilities: { heavy_graph_node_cap: 320, rankings: ["degree", "pagerank"] },
    export_formats: ["gexf", "graphml", "\u200b", "nodes_csv", "edges_csv", "selection_json"],
    nodes: [
      { id: "meme-1", label: "Persistence", kind: "meme", domain: "knowledge", degree: 1, render_coords: { force: { x: 0, y: 0 } }, export_label: "Persistence" },
      { id: "meme-2", label: "Retrieval", kind: "meme", domain: "behavior", degree: 2, render_coords: { force: { x: 1, y: 1 } }, export_label: "Retrieval", memode_membership: ["memode-1"] },
      { id: "memode-1", label: "Persistence memode", kind: "memode", domain: "behavior", degree: 1, render_coords: { force: { x: 2, y: 2 } }, export_label: "Persistence memode" },
    ],
    edges: [
      { id: "edge-1", source: "meme-1", target: "meme-2", type: "SUPPORTS", weight: 1, evidence_label: "AUTO_DERIVED" },
      { id: "edge-2", source: "memode-1", target: "meme-2", type: "MEMODE_HAS_MEMBER", weight: 1, evidence_label: "AUTO_DERIVED" },
    ],
    semantic_nodes: [
      { id: "meme-1", label: "Persistence", kind: "meme", domain: "knowledge", degree: 1, render_coords: { force: { x: 0, y: 0 } }, export_label: "Persistence" },
      { id: "meme-2", label: "Retrieval", kind: "meme", domain: "behavior", degree: 2, render_coords: { force: { x: 1, y: 1 } }, export_label: "Retrieval", memode_membership: ["memode-1"] },
    ],
    semantic_edges: [{ id: "edge-1", source: "meme-1", target: "meme-2", type: "SUPPORTS", weight: 1, evidence_label: "AUTO_DERIVED" }],
    assembly_nodes: [
      { id: "meme-1", label: "Persistence", kind: "meme", domain: "knowledge", degree: 1, render_coords: { force: { x: 0, y: 0 } }, export_label: "Persistence" },
      { id: "meme-2", label: "Retrieval", kind: "meme", domain: "behavior", degree: 2, render_coords: { force: { x: 1, y: 1 } }, export_label: "Retrieval", memode_membership: ["memode-1"] },
      { id: "memode-1", label: "Persistence memode", kind: "memode", domain: "behavior", degree: 1, render_coords: { force: { x: 2, y: 2 } }, export_label: "Persistence memode" },
    ],
    assembly_edges: [
      { id: "edge-1", source: "meme-1", target: "meme-2", type: "SUPPORTS", weight: 1, evidence_label: "AUTO_DERIVED" },
      { id: "edge-2", source: "memode-1", target: "meme-2", type: "MEMODE_HAS_MEMBER", weight: 1, evidence_label: "AUTO_DERIVED" },
    ],
    runtime_nodes: [],
    runtime_edges: [],
    assemblies: [
      {
        id: "memode-1",
        label: "Persistence memode",
        domain: "behavior",
        member_meme_ids: ["meme-2"],
        supporting_edge_ids: ["edge-1"],
        member_order: ["meme-2"],
        invariance_summary: "Reusable persistence pattern",
        measurement_history: [],
      },
    ],
    memode_audit: {
      summary: {
        memodes: 1,
        admissible_memodes: 1,
        flagged_memodes: 0,
        materialized_support_edges: 1,
        informational_relations: 0,
      },
      memodes: [
        {
          id: "memode-1",
          label: "Persistence memode",
          summary: "Reusable persistence pattern",
          domain: "behavior",
          evidence_label: "AUTO_DERIVED",
          operator_label: "",
          confidence: 0.8,
          member_meme_ids: ["meme-2"],
          member_memes: [
            { id: "meme-2", label: "Retrieval", domain: "behavior", evidence_label: "AUTO_DERIVED", recent_active_set_presence: 1, usage_count: 1, feedback_count: 0 },
          ],
          declared_support_edge_ids: ["edge-1"],
          declared_support_edges: [],
          support_edge_ids: ["edge-1"],
          support_edges: [],
          informational_edge_ids: [],
          informational_edges: [],
          admissibility: {
            minimum_members: true,
            support_edges_present: true,
            all_members_supported: true,
            connected_support_graph: true,
            passes: true,
            unsupported_member_ids: [],
          },
        },
      ],
      informational_relations: [],
    },
    cluster_summaries: [{ cluster_signature: "cluster-1", display_label: "Persistence cluster", member_meme_ids: ["meme-1", "meme-2"] }],
    active_set_slices: [{ node_ids: ["meme-1"], document_count: 1 }],
    counts: { memes: 2, edges: 2, memodes: 1 },
  };
}

function overviewPayload() {
  return {
    graph_counts: { memes: 2, edges: 2, memodes: 1 },
    basin: { filtered_turn_count: 0 },
    measurements: { events: 1 },
    hum: {
      present: true,
      generated_at: "2026-03-19T15:00:00Z",
      turn_window_size: 1,
      cross_turn_recurrence_present: false,
      text_surface: "seed-state: 1 persisted turn; cross-turn recurrence not available yet.",
    },
  };
}

function transcriptPayload() {
  return {
    hum: {
      present: true,
      generated_at: "2026-03-19T15:00:00Z",
      turn_window_size: 1,
      cross_turn_recurrence_present: false,
      text_surface: "hum-live continuity beat one",
    },
    turns: [
      {
        turn_id: "turn-1",
        turn_index: 1,
        user_text: "What is active?",
        active_set_node_ids: ["meme-1"],
        reasoning_text: "visible step one\nvisible step two",
      },
    ],
  };
}

function measurementsPayload() {
  return { counts: { events: 1 }, events: [{ id: "evt-1", action_type: "geometry_measurement_run", evidence_label: "DERIVED", created_at: "2026-03-19T15:00:00Z" }] };
}

function largeGraphPayload(nodeCount = 330, heavyCap = 320) {
  const base = graphPayload();
  const nodes = Array.from({ length: nodeCount }, (_, index) => ({
    id: `node-${index + 1}`,
    label: `Node ${index + 1}`,
    export_label: `Node ${index + 1}`,
    kind: "meme",
    domain: index % 2 === 0 ? "knowledge" : "behavior",
    degree: index === 0 || index === nodeCount - 1 ? 1 : 2,
    render_coords: { force: { x: index % 20, y: Math.floor(index / 20) } },
  }));
  const edges = nodes.slice(1).map((node, index) => ({
    id: `edge-${index + 1}`,
    source: nodes[index].id,
    target: node.id,
    type: "SUPPORTS",
    weight: 1,
    evidence_label: "AUTO_DERIVED",
  }));
  return {
    ...base,
    layout_defaults: {
      ...base.layout_defaults,
      heavy_graph_node_cap: heavyCap,
    },
    statistics_capabilities: {
      ...(base.statistics_capabilities ?? {}),
      heavy_graph_node_cap: heavyCap,
    },
    nodes,
    edges,
    semantic_nodes: nodes,
    semantic_edges: edges,
    assembly_nodes: nodes,
    assembly_edges: edges,
    assemblies: [],
    memode_audit: {
      summary: {
        memodes: 0,
        admissible_memodes: 0,
        flagged_memodes: 0,
        materialized_support_edges: 0,
        unmaterialized_support_candidates: 0,
        knowledge_informational_relations: 0,
      },
      memodes: [],
      informational_relations: [],
      capped: false,
      total: 0,
    },
  };
}

describe("EDEN Observatory App", () => {
  beforeEach(() => {
    vi.stubGlobal("EventSource", EventSourceStub);
    workerInstances.length = 0;
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "/");
  });

  it("renders the Gephi-style workbench shell with docked panels and memode audit access", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("graph.json")) return response(graphPayload());
        if (url.endsWith("overview.json")) return response(overviewPayload());
        if (url.endsWith("measurements.json")) return response(measurementsPayload());
        if (url.endsWith("basin.json")) return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "graph",
          experiment_id: "exp-1",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Overview" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("tab", { name: "Data Laboratory" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Preview" })).toBeTruthy();
    expect(screen.getByText(/Static export mode reads adjacent JSON artifacts/)).toBeTruthy();
    expect(screen.getByText("Browser-local graph workbench")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Reset layout" })).toHaveLength(1);
    expect(screen.getByText("Appearance")).toBeTruthy();
    expect(screen.getByText("Layout Workbench")).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Filters" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Memode Audit" })).toBeTruthy();
    expect(screen.getByText("Authority actions")).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Memode Audit" }));
    expect(screen.getByText("Memode Audit Summary")).toBeTruthy();
  });

  it("resets the dock layout after collapsing the left dock", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("graph.json")) return response(graphPayload());
        if (url.endsWith("overview.json")) return response(overviewPayload());
        if (url.endsWith("measurements.json")) return response(measurementsPayload());
        if (url.endsWith("basin.json")) return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "graph",
          experiment_id: "exp-2",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Collapse Left Dock" }));
    expect(screen.getByRole("button", { name: "Appearance / Layout" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Reset layout" }));
    expect(screen.queryByRole("button", { name: "Appearance / Layout" })).toBeNull();
    expect(screen.getByText("Appearance")).toBeTruthy();
  });

  it("always normalizes startup interaction mode to INSPECT even when saved presets requested MEASURE", async () => {
    window.localStorage.setItem(
      "eden.observatory.view_presets.v2::exp-startup::overview::manifest-startup",
      JSON.stringify({
        interactionMode: "MEASURE",
        graphMode: "Semantic Map",
      }),
    );
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("graph.json")) return response(graphPayload());
        if (url.endsWith("overview.json")) return response(overviewPayload());
        if (url.endsWith("measurements.json")) return response(measurementsPayload());
        if (url.endsWith("basin.json")) return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "overview",
          experiment_id: "exp-startup",
          export_manifest_id: "manifest-startup",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    expect(screen.getByRole("radio", { name: "INSPECT" }).getAttribute("aria-checked")).toBe("true");
    expect(screen.getByRole("radio", { name: "Semantic Map" }).getAttribute("aria-checked")).toBe("true");
  });

  it("defers geometry loading until the Geometry dock tab opens", async () => {
    let geometryRequests = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("graph.json")) return response(graphPayload());
        if (url.endsWith("overview.json")) return response(overviewPayload());
        if (url.endsWith("measurements.json")) return response(measurementsPayload());
        if (url.endsWith("basin.json")) return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        if (url.endsWith("geometry.json")) {
          geometryRequests += 1;
          return response({ slice_count: 3, projection_count: 2 });
        }
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "overview",
          experiment_id: "exp-3",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
            geometry: "/geometry.json",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    await waitFor(() => {
      expect(geometryRequests).toBe(0);
    });

    fireEvent.click(screen.getByRole("tab", { name: "Geometry" }));
    await waitFor(() => {
      expect(geometryRequests).toBe(1);
    });
    expect(screen.getByText("Summary-first diagnostics")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Show Geometry JSON" })).toBeTruthy();
    expect(screen.queryByText(/"slice_count": 3/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Show Geometry JSON" }));
    expect(screen.getByText(/Preparing geometry json/i)).toBeTruthy();
    expect(await screen.findByText(/"slice_count": 3/)).toBeTruthy();
  });

  it("surfaces live build warnings and sparse basin honesty from the right dock", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url === "/api/status") {
          return response({ status: { frontend_build: { warning: true, reason: "frontend shell is older than the current source tree; run npm --prefix web/observatory run build" } } });
        }
        if (url === "/api/graph") return response(graphPayload());
        if (url === "/api/basin") {
          return response({
            projection_method: "svd_on_turn_features",
            turns: [{ turn_id: "turn-1", display_attractor_label: "Persistence" }],
            attractors: [],
            filtered_turn_count: 1,
            source_turn_count: 3,
            diagnostics: { empty_state: true, skipped_turn_count: 2, reason: "Not enough turns with non-empty active sets for basin playback." },
          });
        }
        if (url === "/api/overview") return response(overviewPayload());
        if (url === "/api/measurements") return response(measurementsPayload());
        if (url === "/api/runtime/status") return response({ available: true });
        if (url === "/api/runtime/model") return response({ available: true, backend: "mock" });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "basin",
          experiment_id: "exp-4",
          live_api: {
            status: "/api/status",
            graph: "/api/graph",
            basin: "/api/basin",
            overview: "/api/overview",
            measurements: "/api/measurements",
            runtime_status: "/api/runtime/status",
            runtime_model: "/api/runtime/model",
            events: "/api/events",
          },
        }}
      />,
    );

    expect(await screen.findByText("Sparse basin data")).toBeTruthy();
    expect(screen.getByText(/Build warning: frontend shell is older than the current source tree; run npm --prefix web\/observatory run build/)).toBeTruthy();
    expect(screen.getByText(/Not enough turns with non-empty active sets/)).toBeTruthy();
  });

  it("keeps overview context truthful and payload diagnostics separate from overview content", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("graph.json")) return response(graphPayload());
        if (url.endsWith("overview.json")) return response(overviewPayload());
        if (url.endsWith("measurements.json")) return response(measurementsPayload());
        if (url.endsWith("basin.json")) return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "overview",
          experiment_id: "exp-context",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    expect(screen.getByText("Current plane")).toBeTruthy();
    expect(screen.getByText("Assemblies plane")).toBeTruthy();
    expect(screen.getByText("Assemblies loaded")).toBeTruthy();
    expect(screen.getByText("Visible node domains")).toBeTruthy();
    expect(screen.getByText("Knowledge nodes")).toBeTruthy();

    fireEvent.click(screen.getByRole("radio", { name: "Semantic Map" }));
    expect(screen.getByText("Semantic meme-support slice")).toBeTruthy();
    expect(screen.queryByText("Assemblies loaded")).toBeNull();
    expect(screen.getByText("Clusters")).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Payloads" }));
    expect(screen.getByText("Bundle diagnostics")).toBeTruthy();
    expect(screen.queryByText("Experiment")).toBeNull();
  });

  it("simplifies appearance controls to subject-specific browser-local mappings", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("graph.json")) return response(graphPayload());
        if (url.endsWith("overview.json")) return response(overviewPayload());
        if (url.endsWith("measurements.json")) return response(measurementsPayload());
        if (url.endsWith("basin.json")) return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "overview",
          experiment_id: "exp-appearance",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Unique" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Partition" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Ranking" })).toBeNull();
    expect(screen.getByLabelText("Node color by")).toBeTruthy();
    expect(screen.queryByLabelText("Edge color by")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Edges" }));
    expect(screen.getByLabelText("Edge color by")).toBeTruthy();
    expect(screen.queryByLabelText("Node color by")).toBeNull();
  });

  it("makes measure mode visibly instructive instead of inert", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url === "/api/status") return response({ status: { frontend_build: { warning: false } } });
        if (url === "/api/graph") return response(graphPayload());
        if (url === "/api/basin") return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        if (url === "/api/overview") return response(overviewPayload());
        if (url === "/api/measurements") return response(measurementsPayload());
        if (url === "/api/runtime/status") return response({ available: true });
        if (url === "/api/runtime/model") return response({ available: true, backend: "mock" });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "overview",
          experiment_id: "exp-measure",
          live_api: {
            status: "/api/status",
            graph: "/api/graph",
            basin: "/api/basin",
            overview: "/api/overview",
            measurements: "/api/measurements",
            runtime_status: "/api/runtime/status",
            runtime_model: "/api/runtime/model",
            preview: "/api/preview",
            commit: "/api/commit",
            events: "/api/events",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: "MEASURE" }));
    expect(screen.getByText("Measure mode")).toBeTruthy();
    expect(screen.getByText("No graph selection yet.")).toBeTruthy();
    expect(screen.getByText(/Select nodes or a relation, then open Actions to preview a measurement run/)).toBeTruthy();
    expect(screen.getByText(/Preview remains the next attributable step; commit is still explicit and reversible/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "select-meme-1" }));
    expect(await screen.findByText("1-node selection active.")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Open Actions" }).length).toBeGreaterThan(0);
  });

  it("does not describe the default assembly context as a graph selection", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url === "/api/status") return response({ status: { frontend_build: { warning: false } } });
        if (url === "/graph.json") return response(graphPayload());
        if (url === "/overview.json") return response(overviewPayload());
        if (url === "/measurements.json") return response(measurementsPayload());
        if (url === "/basin.json") return response(basinPayload());
        if (url === "/api/sessions/session-1/turns") return response(transcriptPayload());
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          mode: "hybrid",
          initial_surface: "overview",
          session_id: "session-1",
          live_api: {
            status: "/api/status",
            sessions: "/api/sessions",
            events: "/api/events",
          },
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    expect(screen.getByText("No graph selection yet.")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Inspector" }));
    expect(screen.getByRole("tab", { name: "Inspector cards" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Inspector raw JSON" })).toBeTruthy();
    expect(screen.getByText("No graph selection yet; inspector is showing the current assembly context.")).toBeTruthy();
    expect(screen.queryByText("Inspecting 1 selected assembly.")).toBeNull();
  });

  it("loads heavy payloads from static sidecars in hybrid mode without waiting for stalled live overview requests", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url === "/api/status") return response({ status: { frontend_build: { warning: false } } });
      if (url === "/graph.json") return response(graphPayload());
      if (url === "/overview.json") return new Promise(() => {});
      if (url === "/measurements.json") return new Promise(() => {});
      if (url === "/basin.json") return new Promise(() => {});
      if (url === "/api/sessions/session-1/turns") return response(transcriptPayload());
      if (url === "/api/runtime/status") return response({ available: true });
      if (url === "/api/runtime/model") return response({ available: true, backend: "mock" });
      throw new Error(`Unexpected fetch URL: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <App
        bootstrap={{
          mode: "hybrid",
          initial_surface: "graph",
          experiment_id: "exp-hybrid",
          session_id: "session-1",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
          },
          live_api: {
            status: "/api/status",
            graph: "/api/graph",
            basin: "/api/basin",
            overview: "/api/overview",
            measurements: "/api/measurements",
            session_turns: "/api/sessions/session-1/turns",
            runtime_status: "/api/runtime/status",
            runtime_model: "/api/runtime/model",
            events: "/api/events",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    expect(screen.getByText(/Hybrid mode uses adjacent JSON for heavy bundles/)).toBeTruthy();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/api/graph"))).toBe(false);
    expect(fetchMock.mock.calls.some(([url]) => String(url) === "/graph.json")).toBe(true);
  });

  it("surfaces an explicit large-graph layout warning when the visible slice exceeds the browser cap", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("graph.json")) return response(largeGraphPayload());
        if (url.endsWith("overview.json")) return response(overviewPayload());
        if (url.endsWith("measurements.json")) return response(measurementsPayload());
        if (url.endsWith("basin.json")) return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "graph",
          experiment_id: "exp-large-layout",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    expect(screen.getAllByText(/Current filtered view has 330 nodes, above the browser layout cap of 320\./).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "Select Nodes to Run" })[0].hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("button", { name: "Select Visible Sample (25)" })).toBeTruthy();
  });

  it("runs a browser-local layout on a selected visible sample when the full graph exceeds the cap", async () => {
    vi.stubGlobal("Worker", WorkerStub as any);
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("graph.json")) return response(largeGraphPayload());
        if (url.endsWith("overview.json")) return response(overviewPayload());
        if (url.endsWith("measurements.json")) return response(measurementsPayload());
        if (url.endsWith("basin.json")) return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "graph",
          experiment_id: "exp-selection-layout",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Select Visible Sample (25)" }));

    expect(screen.getByTestId("graph-panel").textContent).toContain("Graph canvas:25:nodesSelected=25");
    expect(screen.getByTestId("graph-panel").textContent).toContain("focusNodes=25");
    expect(screen.getAllByText(/Selected visible sample \(25 nodes\) for browser-local layout; isolated and focused that subgraph/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Run Selected Layout" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Restore Full View" })).toBeTruthy();

    fireEvent.click(screen.getAllByRole("button", { name: "Run Selected Layout" })[0]);

    const layoutWorker = workerInstances.find((instance) => instance.scriptUrl.includes("layoutWorker")) ?? workerInstances[0];
    expect(layoutWorker).toBeTruthy();
    expect(layoutWorker.messages[0].type).toBe("run");
    expect(layoutWorker.messages[0].nodes).toHaveLength(25);
    expect(layoutWorker.messages[0].edges.length).toBeGreaterThan(0);

    act(() => {
      layoutWorker.emit({
        type: "done",
        runId: layoutWorker.messages[0].runId,
        layoutId: "forceatlas2",
        coordinateMap: {
          "node-1": { x: 1, y: 1 },
          "node-2": { x: 2, y: 2 },
        },
      });
    });

    await waitFor(() => {
      expect(screen.getAllByText(/ForceAtlas2 ready; isolated and focused selected subgraph \(25 nodes\)/).length).toBeGreaterThan(0);
    });
    expect(screen.getByTestId("graph-panel").textContent).toContain("Graph canvas:25:nodesSelected=25");
    expect(screen.getByTestId("graph-panel").textContent).toContain("focusNodes=25");

    fireEvent.click(screen.getByRole("button", { name: "Restore Full View" }));

    expect(screen.getAllByText(/Restored full filtered graph view/).length).toBeGreaterThan(0);
    expect(screen.getByTestId("graph-panel").textContent).toContain("Graph canvas:330:nodesSelected=0");
    expect(screen.getByTestId("graph-panel").textContent).toContain("focusNodes=0");
    expect(screen.getAllByRole("button", { name: "Select Nodes to Run" })[0].hasAttribute("disabled")).toBe(true);
    expect(screen.getAllByText("0%").length).toBeGreaterThan(0);
  });

  it("keeps visible reasoning and hum continuity in the demoted status row", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url === "/api/status") return response({ status: { frontend_build: { warning: false } } });
        if (url === "/api/graph?session_id=session-1") return response(graphPayload());
        if (url === "/api/basin?session_id=session-1") return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        if (url === "/api/overview?session_id=session-1") return response(overviewPayload());
        if (url === "/api/measurements?session_id=session-1") return response(measurementsPayload());
        if (url === "/api/sessions/session-1/turns") return response(transcriptPayload());
        if (url === "/api/runtime/status") return response({ available: true });
        if (url === "/api/runtime/model") return response({ available: true, backend: "mock" });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "overview",
          experiment_id: "exp-5",
          session_id: "session-1",
          live_api: {
            status: "/api/status",
            graph: "/api/graph",
            basin: "/api/basin",
            overview: "/api/overview",
            measurements: "/api/measurements",
            session_turns: "/api/sessions/session-1/turns",
            runtime_status: "/api/runtime/status",
            runtime_model: "/api/runtime/model",
            events: "/api/events",
          },
        }}
      />,
    );

    expect(await screen.findByText(/visible step one/)).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: "Hum Live" }));
    expect((await screen.findAllByText(/hum-live continuity beat one/)).length).toBeGreaterThan(0);
  });

  it("synchronizes overview selection into Data Laboratory and keeps Preview separate from mutation controls", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("graph.json")) return response(graphPayload());
        if (url.endsWith("overview.json")) return response(overviewPayload());
        if (url.endsWith("measurements.json")) return response(measurementsPayload());
        if (url.endsWith("basin.json")) return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "graph",
          experiment_id: "exp-6",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Queries" }));
    fireEvent.click(screen.getByRole("button", { name: "Graph entity Persistence" }));

    fireEvent.click(screen.getByRole("tab", { name: "Data Laboratory" }));
    expect(screen.getByText("Bounded audit tables")).toBeTruthy();
    const selectedRow = screen.getAllByText("Persistence")[0].closest("tr");
    expect(selectedRow?.className).toContain("is-selected");

    fireEvent.click(screen.getAllByRole("button", { name: "Select in Graph" })[0]);
    fireEvent.click(screen.getByRole("tab", { name: "Overview" }));
    expect(screen.getByTestId("graph-panel").textContent).toContain("nodesSelected=1");

    fireEvent.click(screen.getByRole("tab", { name: "Data Laboratory" }));
    fireEvent.change(screen.getByLabelText("Export scope"), { target: { value: "full" } });
    expect(screen.getByText(/Full ontology · 3 nodes · 2 edges/)).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Preview" }));
    expect(screen.getByText("Final render workspace")).toBeTruthy();
    expect(screen.getByText("Preview Settings")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Refresh preview" })).toBeTruthy();
    const previewExportActions = screen.getByText("Export Actions").closest("section");
    expect(previewExportActions).toBeTruthy();
    const exportButtons = within(previewExportActions as HTMLElement)
      .getAllByRole("button")
      .map((button) => button.textContent?.trim() ?? "");
    expect(exportButtons.every((label) => label.length > 0)).toBe(true);
    expect(within(previewExportActions as HTMLElement).getByRole("button", { name: "Selection JSON" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Commit" })).toBeNull();
  });

  it("uses relation-aware Data Laboratory selection wording in Edges view", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("graph.json")) return response(graphPayload());
        if (url.endsWith("overview.json")) return response(overviewPayload());
        if (url.endsWith("measurements.json")) return response(measurementsPayload());
        if (url.endsWith("basin.json")) return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "overview",
          experiment_id: "exp-data-lab-edges",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Data Laboratory" }));
    fireEvent.click(screen.getByRole("button", { name: "Edges" }));
    expect(screen.getByText("0 relation rows selected")).toBeTruthy();
    expect(screen.getByText("No current graph selection")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Select first visible relation" }));
    expect(screen.getByText("1 relation row selected")).toBeTruthy();
    expect(screen.getByText("1 relation selected in graph")).toBeTruthy();
  });

  it("keeps inspector raw JSON collapsed until explicitly revealed", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("graph.json")) return response(graphPayload());
        if (url.endsWith("overview.json")) return response(overviewPayload());
        if (url.endsWith("measurements.json")) return response(measurementsPayload());
        if (url.endsWith("basin.json")) return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "overview",
          experiment_id: "exp-inspector-json",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    expect(await screen.findByText("Current plane")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Inspector" }));
    expect(screen.getByText("Cards first, JSON on reveal")).toBeTruthy();
    expect(screen.queryByText(/"graph_counts"/)).toBeNull();

    fireEvent.click(screen.getByRole("tab", { name: "Inspector raw JSON" }));
    expect(screen.getByRole("button", { name: "Show Raw JSON" })).toBeTruthy();
    expect(screen.queryByText(/"graph_counts"/)).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Show Raw JSON" }));
    const inspectorPanel = screen.getByRole("tabpanel", { name: "Inspector raw JSON" });
    await waitFor(() => {
      const rawJson = inspectorPanel.querySelector("pre.debug-json");
      expect(rawJson?.textContent).toContain('"member_meme_ids"');
    });
  });

  it("adds guidance to the Tanakh tab and avoids duplicating payload mode copy", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url === "/api/status") return response({ status: { frontend_build: { warning: false } } });
      if (url === "/graph.json") return response(graphPayload());
      if (url === "/overview.json") return response(overviewPayload());
      if (url === "/measurements.json") return response(measurementsPayload());
      if (url === "/basin.json") return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
      if (url === "/tanakh.json") return response({ current_ref: "Ezek 1", bundle_hash: "bundle-1", bundle: { manifest: { dataset_id: "uxlc-test" } } });
      throw new Error(`Unexpected fetch URL: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <App
        bootstrap={{
          mode: "hybrid",
          initial_surface: "overview",
          experiment_id: "exp-tanakh-audit",
          payload_urls: {
            graph: "/graph.json",
            basin: "/basin.json",
            overview: "/overview.json",
            measurements: "/measurements.json",
            tanakh: "/tanakh.json",
          },
          live_api: {
            status: "/api/status",
            events: "/api/events",
          },
        }}
      />,
    );

    expect(await screen.findByTestId("graph-panel")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Tanakh" }));
    expect(screen.getByText("Canonical text and derived sidecars")).toBeTruthy();
    expect(screen.getByText(/Tanakh runs are separate derived tools and do not participate in preview \/ commit \/ revert semantics/)).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Payloads" }));
    expect(screen.getAllByText(/Hybrid mode loads heavy graph\/basin\/overview bundles from adjacent JSON sidecars/).length).toBe(1);
  });
});
