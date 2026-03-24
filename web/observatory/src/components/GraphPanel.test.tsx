import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GraphPanel from "./GraphPanel";

const cameraAnimatedReset = vi.fn(() => Promise.resolve());
const sigmaSetCustomBBox = vi.fn();
const sigmaRefresh = vi.fn();
const sigmaOn = vi.fn();
const sigmaKill = vi.fn();

vi.mock("sigma", () => {
  return {
    default: class SigmaMock {
      private graph: any;

      constructor(graph: any) {
        this.graph = graph;
      }

      getCamera() {
        return {
          animatedReset: cameraAnimatedReset,
        };
      }

      setCustomBBox(bounds: any) {
        sigmaSetCustomBBox(bounds);
      }

      refresh() {
        sigmaRefresh();
      }

      on(event: string, handler: unknown) {
        sigmaOn(event, handler);
      }

      getGraph() {
        return this.graph;
      }

      kill() {
        sigmaKill();
      }
    },
  };
});

describe("GraphPanel", () => {
  beforeEach(() => {
    cameraAnimatedReset.mockClear();
    sigmaSetCustomBBox.mockClear();
    sigmaRefresh.mockClear();
    sigmaOn.mockClear();
    sigmaKill.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("focuses the camera on an explicit selected subgraph when focusVersion advances", async () => {
    render(
      <GraphPanel
        nodes={[
          { id: "node-1", label: "Node 1", degree: 1, render_coords: { force: { x: 0, y: 0 } } },
          { id: "node-2", label: "Node 2", degree: 1, render_coords: { force: { x: 4, y: 2 } } },
          { id: "node-3", label: "Node 3", degree: 1, render_coords: { force: { x: 12, y: 8 } } },
        ]}
        edges={[
          { id: "edge-1", source: "node-1", target: "node-2", type: "SUPPORTS", weight: 1 },
          { id: "edge-2", source: "node-2", target: "node-3", type: "SUPPORTS", weight: 1 },
        ]}
        coordinateMap={{
          "node-1": { x: 0, y: 0 },
          "node-2": { x: 4, y: 2 },
          "node-3": { x: 12, y: 8 },
        }}
        appearance={{
          nodeColorBy: "kind",
          nodeSizeBy: "uniform",
          edgeColorBy: "type",
          edgeOpacityBy: "uniform",
          labelMode: "selection",
          showEdgeLabels: false,
          edgeOpacityScale: 1,
        }}
        highlightedNodeIds={[]}
        selectedNodeIds={["node-1", "node-2"]}
        selectedEdgeId={null}
        selectedAssembly={null}
        focusNodeIds={["node-1", "node-2"]}
        focusVersion={1}
        onSelectNode={() => undefined}
        onSelectEdge={() => undefined}
        onClearSelection={() => undefined}
      />,
    );

    expect(sigmaSetCustomBBox).toHaveBeenCalledWith({
      x: [-0.88, 4.88],
      y: [-0.44, 2.44],
    });
    expect(cameraAnimatedReset).toHaveBeenCalled();
  });
});
