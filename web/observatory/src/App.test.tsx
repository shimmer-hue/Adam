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
            export_formats: ["gexf", "graphml", "nodes_csv", "edges_csv", "selection_json"],
            semantic_nodes: [{ id: "meme-1", label: "Persistence", kind: "meme", domain: "knowledge", render_coords: { force: { x: 0, y: 0 } } }],
            semantic_edges: [],
            runtime_nodes: [],
            runtime_edges: [],
            assemblies: [
              {
                id: "memode-1",
                label: "Persistence memode",
                domain: "behavior",
                member_meme_ids: ["meme-1"],
                supporting_edge_ids: ["edge-1"],
                member_order: [],
                invariance_summary: "Reusable persistence pattern",
                measurement_history: [],
              },
            ],
            cluster_summaries: [
              {
                cluster_signature: "cluster-1",
                display_label: "Persistence cluster",
                member_meme_ids: ["meme-1"],
                top_meme_ids: ["meme-1"],
              },
            ],
            active_set_slices: [],
            counts: { memes: 1, edges: 0 },
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
    expect(screen.getByRole("radio", { name: "Assemblies" }).getAttribute("aria-checked")).toBe("false");
    expect(screen.getByRole("radio", { name: "INSPECT" }).getAttribute("aria-checked")).toBe("true");
    expect((screen.getByRole("button", { name: "Preview" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Commit" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("radio", { name: "force" }).getAttribute("aria-checked")).toBe("true");
    expect(screen.getByRole("heading", { name: "1. Force-Directed Layout Algorithms" })).toBeTruthy();
    expect(screen.getByText(/Nodes repel while edges pull related nodes together/)).toBeTruthy();
    expect(screen.getByText("Runnable in browser worker")).toBeTruthy();
    expect((screen.getByLabelText(/ForceAtlas2.*Iterations/i) as HTMLInputElement).value).toBe("160");
    expect(screen.getByText("Identity")).toBeTruthy();
    expect(screen.getByText("Ontology")).toBeTruthy();
    expect(screen.getByText("Measurement History")).toBeTruthy();

    const forceDirectedFamily = screen.getByRole("heading", { name: "1. Force-Directed Layout Algorithms" }).closest("section");
    if (!forceDirectedFamily) throw new Error("Missing force-directed family section");
    fireEvent.click(within(forceDirectedFamily).getByRole("button", { name: /^OpenOrd / }));
    expect((screen.getByRole("button", { name: "Run Layout" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Reference / explanatory only")).toBeTruthy();
    expect(screen.getByText(/wider layout landscape/i)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /^Kamada-Kawai / }));
    expect((screen.getByRole("button", { name: "Run Layout" }) as HTMLButtonElement).disabled).toBe(false);
    expect(screen.getByText(/distance fidelity matters more than raw scale/i)).toBeTruthy();

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
});
