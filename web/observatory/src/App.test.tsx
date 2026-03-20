import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./components/GraphPanel", () => ({
  default: ({
    nodes,
    ariaLabel,
    selectedNodeIds = [],
    selectedEdgeId = null,
  }: {
    nodes: Array<unknown>;
    ariaLabel?: string;
    selectedNodeIds?: string[];
    selectedEdgeId?: string | null;
  }) => (
    <div data-testid="graph-panel">{`${ariaLabel ?? "Graph canvas"}:${nodes.length}:nodesSelected=${selectedNodeIds.length}:edgeSelected=${selectedEdgeId ?? "none"}`}</div>
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
    export_formats: ["gexf", "graphml", "nodes_csv", "edges_csv", "selection_json"],
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

describe("EDEN Observatory App", () => {
  beforeEach(() => {
    vi.stubGlobal("EventSource", EventSourceStub);
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
    expect(screen.getByText("Appearance")).toBeTruthy();
    expect(screen.getByText("Layout Workbench")).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Filters" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Memode Audit" })).toBeTruthy();

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

    fireEvent.click(screen.getAllByRole("button", { name: "Reset layout" })[0]);
    expect(screen.queryByRole("button", { name: "Appearance / Layout" })).toBeNull();
    expect(screen.getByText("Appearance")).toBeTruthy();
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
    expect(await screen.findByText(/"slice_count": 3/)).toBeTruthy();
  });

  it("surfaces live build warnings and sparse basin honesty from the right dock", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url === "/api/status") {
          return response({ status: { frontend_build: { warning: true, reason: "stale build" } } });
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
    expect(screen.getByText(/Build warning: stale build/)).toBeTruthy();
    expect(screen.getByText(/Not enough turns with non-empty active sets/)).toBeTruthy();
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
    const selectedRow = screen.getAllByText("Persistence")[0].closest("tr");
    expect(selectedRow?.className).toContain("is-selected");

    fireEvent.click(screen.getAllByRole("button", { name: "Select in Graph" })[0]);
    fireEvent.click(screen.getByRole("tab", { name: "Overview" }));
    expect(screen.getByTestId("graph-panel").textContent).toContain("nodesSelected=1");

    fireEvent.click(screen.getByRole("tab", { name: "Data Laboratory" }));
    fireEvent.change(screen.getByLabelText("Export scope"), { target: { value: "full" } });
    expect(screen.getByText(/Full ontology · 3 nodes · 2 edges/)).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Preview" }));
    expect(screen.getByText("Preview Settings")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Refresh preview" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Commit" })).toBeNull();
  });
});
