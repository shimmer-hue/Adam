import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import TanakhPanel from "./TanakhPanel";

vi.mock("./TanakhScenePanel", () => ({
  default: () => <div data-testid="tanakh-scene">scene</div>,
}));

describe("TanakhPanel", () => {
  it("keeps Tanakh debug JSON hidden until explicitly revealed", () => {
    render(
      <TanakhPanel
        canRun={false}
        liveEnabled={false}
        onRun={vi.fn(async () => undefined)}
        payload={{
          current_ref: "Ezek 1",
          bundle_hash: "bundle-1",
          artifacts: [{ path: "artifact.json" }],
          bundle: {
            manifest: { dataset_id: "uxlc-test", build: "vite-react-ts", archive_sha256: "archive-1" },
            passage: { verses: [] },
            analyses: {},
            validation: { cases: [{ id: "case-1" }] },
            scene: { scene_hash: "scene-1", nodes: [], edges: [] },
          },
        }}
        running={false}
      />,
    );

    expect(screen.getByRole("button", { name: "Live server required" })).toBeTruthy();
    expect(screen.getByText(/Debug JSON stays hidden until you explicitly reveal the Tanakh artifact payload/)).toBeTruthy();
    expect(screen.queryByText(/artifact\.json/)).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Show Debug JSON" }));
    expect(screen.getByText(/artifact\.json/)).toBeTruthy();
  });
});
