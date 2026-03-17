import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

vi.mock("./components/GraphPanel", () => ({
  default: ({ nodes, ariaLabel }: { nodes: Array<unknown>; ariaLabel?: string }) => (
    <div data-testid="graph-panel">{`${ariaLabel ?? "Graph canvas"}:${nodes.length}`}</div>
  ),
}));

vi.mock("./components/BasinPanel", () => ({
  default: ({ liftMode }: { liftMode: string }) => <div data-testid="basin-panel">basin:{liftMode}</div>,
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

describe("EDEN Observatory App", () => {
  beforeEach(() => {
    vi.stubGlobal("EventSource", EventSourceStub);
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState({}, "", "/");
  });

  it("renders graph controls, structured inspector cards, and hardened graph preset keys", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("graph.json")) {
          return response({
            export_manifest_id: "manifest-graph",
            source_graph_hash: "graph-hash-1",
            graph_modes: ["Semantic Map", "Assemblies", "Runtime", "Active Set", "Compare"],
            assembly_render_modes: ["hulls", "collapsed-meta-node", "hidden"],
            interaction_modes: ["INSPECT", "MEASURE", "EDIT", "ABLATE", "COMPARE"],
            evidence_legend: { OPERATOR_ASSERTED: {}, OPERATOR_REFINED: {}, DERIVED: {} },
            view_modes: { force: "Force", spectral: "Spectral" },
            layout_catalog: {
              forceatlas2: { label: "ForceAtlas2" },
              fruchterman_reingold: { label: "Fruchterman-Reingold" },
              noverlap: { label: "Noverlap" },
              radial: { label: "Radial" },
            },
            layout_defaults: {
              coordinate_mode: "force",
              forceatlas2: { iterations: 160, scalingRatio: 8, gravity: 1 },
              fruchterman_reingold: { iterations: 120 },
              noverlap: { maxIterations: 160 },
              radial: { radiusStep: 1.5 },
            },
            appearance_dimensions: {
              node_color: ["kind", "domain", "cluster", "evidence_label"],
              node_size: ["uniform", "degree"],
              edge_color: ["type", "evidence_label"],
              edge_opacity: ["weight", "uniform"],
              label_modes: ["selection", "all", "none"],
            },
            filter_dimensions: { kinds: ["meme"], domains: ["knowledge"], evidence_labels: ["OPERATOR_ASSERTED"] },
            statistics_capabilities: { heavy_graph_node_cap: 320, rankings: ["degree", "pagerank"] },
            export_formats: ["gexf", "graphml", "gdf", "gml", "graphviz_dot", "pajek_net", "netdraw_vna", "ucinet_dl", "tulip_tlp", "tgf", "nodes_csv", "edges_csv", "selection_json"],
            nodes: [
              { id: "meme-1", label: "Persistence", kind: "meme", domain: "knowledge", degree: 1, render_coords: { force: { x: 0, y: 0 } } },
              { id: "meme-2", label: "Retrieval", kind: "meme", domain: "knowledge", degree: 2, render_coords: { force: { x: 1, y: 1 } } },
              { id: "meme-3", label: "Reference Note", kind: "meme", domain: "knowledge", degree: 1, render_coords: { force: { x: 2, y: 2 } } },
              { id: "memode-1", label: "Persistence memode", kind: "memode", domain: "behavior" },
            ],
            edges: [
              { id: "edge-1", source: "meme-1", target: "meme-2", type: "SUPPORTS", weight: 1, evidence_label: "AUTO_DERIVED" },
              { id: "edge-2", source: "meme-2", target: "meme-3", type: "REFERENCES", weight: 0.4, evidence_label: "AUTO_DERIVED" },
            ],
            semantic_nodes: [
              { id: "meme-1", label: "Persistence", kind: "meme", domain: "knowledge", render_coords: { force: { x: 0, y: 0 } } },
              { id: "meme-2", label: "Retrieval", kind: "meme", domain: "knowledge", render_coords: { force: { x: 1, y: 1 } } },
              { id: "meme-3", label: "Reference Note", kind: "meme", domain: "knowledge", render_coords: { force: { x: 2, y: 2 } } },
            ],
            semantic_edges: [{ id: "edge-1", source: "meme-1", target: "meme-2", type: "SUPPORTS", weight: 1, evidence_label: "AUTO_DERIVED" }],
            assembly_nodes: [
              { id: "meme-1", label: "Persistence", kind: "meme", domain: "knowledge", render_coords: { force: { x: 0, y: 0 } } },
              { id: "meme-2", label: "Retrieval", kind: "meme", domain: "knowledge", render_coords: { force: { x: 1, y: 1 } } },
              { id: "meme-3", label: "Reference Note", kind: "meme", domain: "knowledge", render_coords: { force: { x: 2, y: 2 } } },
              { id: "memode-1", label: "Persistence memode", kind: "memode", domain: "behavior" },
            ],
            assembly_edges: [
              { id: "edge-1", source: "meme-1", target: "meme-2", type: "SUPPORTS", weight: 1, evidence_label: "AUTO_DERIVED" },
              { id: "edge-2", source: "meme-2", target: "meme-3", type: "REFERENCES", weight: 0.4, evidence_label: "AUTO_DERIVED" },
              { id: "edge-3", source: "memode-1", target: "meme-1", type: "MEMODE_HAS_MEMBER", weight: 1, evidence_label: "AUTO_DERIVED" },
            ],
            runtime_nodes: [],
            runtime_edges: [],
            assemblies: [
              {
                id: "memode-1",
                label: "Persistence memode",
                domain: "behavior",
                member_meme_ids: ["meme-1", "meme-2"],
                supporting_edge_ids: ["edge-1"],
                member_order: ["meme-1", "meme-2"],
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
                informational_relations: 1,
                knowledge_informational_relations: 1,
                unmaterialized_support_candidates: 0,
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
                  member_meme_ids: ["meme-1", "meme-2"],
                  member_memes: [
                    { id: "meme-1", label: "Persistence", domain: "knowledge", evidence_label: "AUTO_DERIVED", recent_active_set_presence: 2, usage_count: 1, feedback_count: 0 },
                    { id: "meme-2", label: "Retrieval", domain: "knowledge", evidence_label: "AUTO_DERIVED", recent_active_set_presence: 1, usage_count: 1, feedback_count: 0 },
                  ],
                  declared_support_edge_ids: ["edge-1"],
                  declared_support_edges: [
                    {
                      id: "edge-1",
                      identity: "edge-1",
                      source: "meme-1",
                      target: "meme-2",
                      type: "SUPPORTS",
                      weight: 1,
                      evidence_label: "AUTO_DERIVED",
                      assertion_origin: "auto_derived",
                      operator_label: "",
                      confidence: 1,
                      source_label: "Persistence",
                      target_label: "Retrieval",
                      source_domain: "knowledge",
                      target_domain: "knowledge",
                      relation_class: "declared_support",
                      overlapping_memode_ids: [],
                    },
                  ],
                  support_edge_ids: ["edge-1"],
                  support_edges: [
                    {
                      id: "edge-1",
                      identity: "edge-1",
                      source: "meme-1",
                      target: "meme-2",
                      type: "SUPPORTS",
                      weight: 1,
                      evidence_label: "AUTO_DERIVED",
                      assertion_origin: "auto_derived",
                      operator_label: "",
                      confidence: 1,
                      source_label: "Persistence",
                      target_label: "Retrieval",
                      source_domain: "knowledge",
                      target_domain: "knowledge",
                      relation_class: "materialized_support",
                      overlapping_memode_ids: ["memode-1"],
                    },
                  ],
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
              informational_relations: [
                {
                  id: "edge-2",
                  identity: "edge-2",
                  source: "meme-2",
                  target: "meme-3",
                  type: "REFERENCES",
                  weight: 0.4,
                  evidence_label: "AUTO_DERIVED",
                  assertion_origin: "auto_derived",
                  operator_label: "",
                  confidence: 1,
                  source_label: "Retrieval",
                  target_label: "Reference Note",
                  source_domain: "knowledge",
                  target_domain: "knowledge",
                  relation_class: "knowledge_informational",
                  overlapping_memode_ids: [],
                },
              ],
            },
            cluster_summaries: [
              {
                cluster_signature: "cluster-1",
                display_label: "Persistence cluster",
                member_meme_ids: ["meme-1", "meme-2"],
                top_meme_ids: ["meme-1", "meme-2"],
              },
            ],
            active_set_slices: [],
            counts: { memes: 3, edges: 2, memodes: 1 },
          });
        }
        if (url.endsWith("basin.json")) {
          return response({ turns: [], attractors: [], filtered_turn_count: 0, source_turn_count: 0, diagnostics: { empty_state: true } });
        }
        if (url.endsWith("overview.json")) {
          return response({ graph_counts: { memes: 1, edges: 0 }, basin: { filtered_turn_count: 0 }, measurements: { events: 0 } });
        }
        if (url.endsWith("measurements.json")) {
          return response({ counts: { events: 0 }, events: [] });
        }
        if (url.endsWith("geometry.json")) {
          return response({});
        }
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "graph",
          experiment_id: "exp-1",
          session_id: "session-1",
          export_manifest_id: "manifest-graph",
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
    expect(screen.getByText("Large semantic graph bundle")).toBeTruthy();
    expect(screen.getByText("Large diagnostics bundle")).toBeTruthy();
    expect(screen.getByRole("button", { name: "GraphViz DOT" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Pajek NET" })).toBeTruthy();
    expect(screen.getByRole("radio", { name: "Assemblies" }).getAttribute("aria-checked")).toBe("false");
    expect(screen.getByRole("radio", { name: "INSPECT" }).getAttribute("aria-checked")).toBe("true");
    expect((screen.getByRole("button", { name: "Preview" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Commit" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("radio", { name: "force" }).getAttribute("aria-checked")).toBe("true");
    expect(screen.getByRole("heading", { name: "1. Force-Directed Layout Algorithms" })).toBeTruthy();
    expect(screen.getByText(/Nodes repel while edges pull related nodes together/)).toBeTruthy();
    expect(screen.getByText("Runnable in browser worker")).toBeTruthy();
    expect(screen.getByTestId("graph-panel").textContent).toContain(":3");
    expect((screen.getByLabelText(/ForceAtlas2.*Iterations/i) as HTMLInputElement).value).toBe("160");
    expect(screen.getByText("Identity")).toBeTruthy();
    expect(screen.getByText("Ontology")).toBeTruthy();
    expect(screen.getByText("Measurement History")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Memode audit Persistence memode" })).toBeTruthy();
    expect(screen.getByText("Memode Audit Summary")).toBeTruthy();
    expect(screen.getByText("Unmaterialized Relations")).toBeTruthy();
    expect(screen.getByText("knowledge informational")).toBeTruthy();

    const forceDirectedFamily = screen.getByRole("heading", { name: "1. Force-Directed Layout Algorithms" }).closest("section");
    if (!forceDirectedFamily) throw new Error("Missing force-directed family section");
    fireEvent.click(within(forceDirectedFamily).getByRole("button", { name: /^OpenOrd / }));
    expect((screen.getByRole("button", { name: "Run Layout" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Reference / explanatory only")).toBeTruthy();
    expect(screen.getByText(/wider layout landscape/i)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /^Kamada-Kawai / }));
    expect((screen.getByRole("button", { name: "Run Layout" }) as HTMLButtonElement).disabled).toBe(false);
    expect(screen.getByText(/distance fidelity matters more than raw scale/i)).toBeTruthy();

    fireEvent.click(screen.getByRole("radio", { name: "Assemblies" }));
    expect(screen.getByTestId("graph-panel").textContent).toContain(":4");

    fireEvent.click(screen.getByRole("radio", { name: "Compare" }));
    expect(screen.getByText("Baseline")).toBeTruthy();
    expect(screen.getByText("Modified")).toBeTruthy();
    expect(screen.getAllByTestId("graph-panel")).toHaveLength(2);

    fireEvent.click(screen.getByRole("tab", { name: "Raw JSON" }));
    expect(screen.getByText(/"label": "Persistence memode"/)).toBeTruthy();

    await waitFor(() => {
      expect(window.localStorage.getItem("eden.observatory.view_presets.v2::exp-1::graph::manifest-graph")).not.toBeNull();
    });
  });

  it("surfaces payload-status copy and defers geometry until the tab opens", async () => {
    let geometryRequests = 0;
    const fetchMock = vi.fn((url: string) => {
      if (url.endsWith("graph.json")) {
        return response({
          export_manifest_id: "manifest-overview",
          source_graph_hash: "graph-hash-overview",
          semantic_nodes: [],
          semantic_edges: [],
          runtime_nodes: [],
          runtime_edges: [],
          assemblies: [],
          cluster_summaries: [],
          active_set_slices: [],
          counts: { memes: 0, edges: 0 },
        });
      }
      if (url.endsWith("basin.json")) {
        return response({
          turns: [],
          attractors: [],
          filtered_turn_count: 0,
          source_turn_count: 0,
          diagnostics: { empty_state: true },
        });
      }
      if (url.endsWith("overview.json")) {
        return response({ graph_counts: { memes: 0, edges: 0 }, basin: { filtered_turn_count: 0 }, measurements: { events: 0 } });
      }
      if (url.endsWith("measurements.json")) {
        return response({ counts: { events: 0 }, events: [] });
      }
      if (url.endsWith("geometry.json")) {
        geometryRequests += 1;
        return response({ slice_count: 3, projection_count: 2 });
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

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

    expect(await screen.findByText(/Static export mode reads adjacent JSON artifacts/)).toBeTruthy();
    expect(screen.getByText("Large diagnostics bundle")).toBeTruthy();

    await waitFor(() => {
      expect(geometryRequests).toBe(0);
    });

    fireEvent.click(screen.getByRole("tab", { name: "Geometry" }));

    await waitFor(() => {
      expect(geometryRequests).toBe(1);
    });
    expect(await screen.findByText(/"slice_count": 3/)).toBeTruthy();
  });

  it("shows sparse basin diagnostics, derived badges, and graph-hash preset fallback in live mode", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url === "/api/status") {
          return response({
            status: {
              frontend_build: {
                warning: true,
                reason: "stale build",
              },
            },
          });
        }
        if (url === "/api/graph") {
          return response({
            source_graph_hash: "graph-hash-live",
            semantic_nodes: [],
            semantic_edges: [],
            runtime_nodes: [],
            runtime_edges: [],
            assemblies: [],
            cluster_summaries: [],
            active_set_slices: [],
          });
        }
        if (url === "/api/basin") {
          return response({
            projection_method: "svd_on_turn_features",
            turns: [{ turn_id: "turn-1", display_attractor_label: "Persistence" }],
            attractors: [],
            filtered_turn_count: 1,
            source_turn_count: 3,
            diagnostics: {
              empty_state: true,
              skipped_turn_count: 2,
              reason: "Not enough turns with non-empty active sets for basin playback.",
            },
          });
        }
        if (url === "/api/overview") {
          return response({ graph_counts: {}, basin: { filtered_turn_count: 1 }, measurements: {} });
        }
        if (url === "/api/measurements") {
          return response({ counts: { events: 0 }, events: [] });
        }
        if (url === "/api/geometry") {
          return response({});
        }
        if (url === "/api/runtime/status") {
          return response({ available: true });
        }
        if (url === "/api/runtime/model") {
          return response({ available: true, backend: "mock" });
        }
        throw new Error(`Unexpected fetch URL: ${url}`);
      }),
    );

    render(
      <App
        bootstrap={{
          initial_surface: "basin",
          experiment_id: "exp-2",
          live_api: {
            status: "/api/status",
            graph: "/api/graph",
            basin: "/api/basin",
            overview: "/api/overview",
            measurements: "/api/measurements",
            geometry: "/api/geometry",
            runtime_status: "/api/runtime/status",
            runtime_model: "/api/runtime/model",
            events: "/api/events",
          },
        }}
      />,
    );

    expect(await screen.findByText("Sparse basin data")).toBeTruthy();
    expect(screen.getByText(/Projection: svd_on_turn_features/)).toBeTruthy();
    expect(screen.getByText(/Lift: flat/)).toBeTruthy();
    expect(screen.getByText(/Build warning: stale build/)).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Basin" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("radio", { name: "flat" }).getAttribute("aria-checked")).toBe("true");

    await waitFor(
      () => {
        const keys = Object.keys(window.localStorage);
        expect(keys.some((key) => key.startsWith("eden.observatory.view_presets.v2::exp-2::basin::"))).toBe(true);
      },
      { timeout: 2000 },
    );
  });

  it("loads session-scoped reasoning and hum continuity lenses in live mode", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url === "/api/status") {
        return response({
          status: {
            frontend_build: {
              warning: false,
            },
          },
        });
      }
      if (url === "/api/graph?session_id=session-1") {
        return response({
          source_graph_hash: "graph-hash-session",
          semantic_nodes: [],
          semantic_edges: [],
          runtime_nodes: [],
          runtime_edges: [],
          assemblies: [],
          cluster_summaries: [],
          active_set_slices: [],
        });
      }
      if (url === "/api/basin?session_id=session-1") {
        return response({
          projection_method: "svd_on_turn_features",
          turns: [{ turn_id: "turn-1", turn_index: 1, display_attractor_label: "Persistence" }],
          attractors: [],
          filtered_turn_count: 1,
          source_turn_count: 1,
          diagnostics: { empty_state: true },
        });
      }
      if (url === "/api/overview?session_id=session-1") {
        return response({
          graph_counts: {},
          basin: { filtered_turn_count: 1 },
          measurements: {},
          hum: { present: false },
        });
      }
      if (url === "/api/measurements?session_id=session-1") {
        return response({ counts: { events: 0 }, events: [] });
      }
      if (url === "/api/sessions/session-1/turns") {
        return response({
          turns: [
            {
              turn_id: "turn-1",
              turn_index: 1,
              user_text: "hello",
              reasoning_text: "visible step one\nvisible step two",
              active_set_node_ids: [],
            },
          ],
          hum: {
            present: true,
            generated_at: "2026-03-13T18:12:22+00:00",
            turn_window_size: 1,
            cross_turn_recurrence_present: false,
            text_surface: "seed-state: 1 persisted turn; cross-turn recurrence not available yet.",
          },
        });
      }
      if (url === "/api/runtime/status") {
        return response({ available: true });
      }
      if (url === "/api/runtime/model") {
        return response({ available: true, backend: "mock" });
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <App
        bootstrap={{
          initial_surface: "overview",
          experiment_id: "exp-session",
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
    expect(document.body.textContent ?? "").toContain("present=yes");
    expect(fetchMock).toHaveBeenCalledWith("/api/overview?session_id=session-1", { credentials: "same-origin" });
    expect(fetchMock).toHaveBeenCalledWith("/api/graph?session_id=session-1", { credentials: "same-origin" });
    expect(fetchMock).toHaveBeenCalledWith("/api/basin?session_id=session-1", { credentials: "same-origin" });
    expect(fetchMock).toHaveBeenCalledWith("/api/measurements?session_id=session-1", { credentials: "same-origin" });

    fireEvent.click(screen.getByRole("radio", { name: "Chain-Like" }));
    expect(await screen.findByText("1. visible step one")).toBeTruthy();

    fireEvent.click(screen.getByRole("radio", { name: "Hum Live" }));
    expect(await screen.findByText("1. seed-state: 1 persisted turn; cross-turn recurrence not available yet.")).toBeTruthy();
  });

  it("honors session_id query overrides when reopening an existing observatory shell", async () => {
    window.history.replaceState({}, "", "/observatory_index.html?session_id=session-override");
    const fetchMock = vi.fn((url: string) => {
      if (url === "/api/status") {
        return response({
          status: {
            frontend_build: {
              warning: false,
            },
          },
        });
      }
      if (url === "/api/graph?session_id=session-override") {
        return response({
          source_graph_hash: "graph-hash-session",
          semantic_nodes: [],
          semantic_edges: [],
          runtime_nodes: [],
          runtime_edges: [],
          assemblies: [],
          cluster_summaries: [],
          active_set_slices: [],
        });
      }
      if (url === "/api/basin?session_id=session-override") {
        return response({
          projection_method: "svd_on_turn_features",
          turns: [],
          attractors: [],
          filtered_turn_count: 0,
          source_turn_count: 0,
          diagnostics: { empty_state: true },
        });
      }
      if (url === "/api/overview?session_id=session-override") {
        return response({
          graph_counts: {},
          basin: { filtered_turn_count: 0 },
          measurements: {},
          hum: { present: false },
        });
      }
      if (url === "/api/measurements?session_id=session-override") {
        return response({ counts: { events: 0 }, events: [] });
      }
      if (url === "/api/sessions/session-override/turns") {
        return response({ turns: [], hum: { present: false } });
      }
      if (url === "/api/sessions/session-override/trace") {
        return response({ trace_events: [], membrane_events: [] });
      }
      if (url === "/api/runtime/status") {
        return response({ available: true });
      }
      if (url === "/api/runtime/model") {
        return response({ available: true, backend: "mock" });
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <App
        bootstrap={{
          initial_surface: "overview",
          experiment_id: "exp-session",
          session_id: "session-stale",
          live_api: {
            status: "/api/status",
            graph: "/api/graph",
            basin: "/api/basin",
            overview: "/api/overview",
            measurements: "/api/measurements",
            session_turns: "/api/sessions/session-stale/turns",
            session_trace: "/api/sessions/session-stale/trace",
            runtime_status: "/api/runtime/status",
            runtime_model: "/api/runtime/model",
            events: "/api/events",
          },
        }}
      />,
    );

    expect(await screen.findByText(/EDEN Observatory/)).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith("/api/overview?session_id=session-override", { credentials: "same-origin" });
    expect(fetchMock).toHaveBeenCalledWith("/api/graph?session_id=session-override", { credentials: "same-origin" });
    expect(fetchMock).toHaveBeenCalledWith("/api/basin?session_id=session-override", { credentials: "same-origin" });
    expect(fetchMock).toHaveBeenCalledWith("/api/measurements?session_id=session-override", { credentials: "same-origin" });
    expect(fetchMock).toHaveBeenCalledWith("/api/sessions/session-override/turns", { credentials: "same-origin" });
    expect(fetchMock).toHaveBeenCalledWith("/api/sessions/session-override/trace", { credentials: "same-origin" });
  });
});
