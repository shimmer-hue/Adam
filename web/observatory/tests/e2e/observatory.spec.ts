import { expect, test, type Page } from "@playwright/test";

import {
  assertGracefulDegradation,
  assertPayloadStatus,
  assertSourceMode,
  attachRecorder,
  diffLedger,
  diffLocalStorage,
  findRealExportFixture,
  mutationRequests,
  persistJourneyEvidence,
  resetScenario,
  snapshotLedger,
  snapshotLedgerFile,
  snapshotLocalStorage,
  triggerInvalidation,
} from "./helpers";

const pages = {
  liveNormal: "http://127.0.0.1:4173/__e2e__/pages/live-normal.html",
  staticNormal: "http://127.0.0.1:4173/__e2e__/pages/static-normal.html",
  liveStale: "http://127.0.0.1:4173/__e2e__/pages/live-stale.html",
  liveUnavailable: "http://127.0.0.1:4173/__e2e__/pages/live-unavailable.html",
  livePartial: "http://127.0.0.1:4173/__e2e__/pages/live-partial.html",
  staticSparse: "http://127.0.0.1:4173/__e2e__/pages/static-sparse.html",
  staticHashMismatch: "http://127.0.0.1:4173/__e2e__/pages/static-hash-mismatch.html",
  liveHeavy: "http://127.0.0.1:4173/__e2e__/pages/live-heavy.html",
};

const ledgers = {
  normalLive: "/__e2e__/api/normal/measurements",
  normalStatic: "/__e2e__/static/normal/measurements.json",
  stale: "/__e2e__/api/stale/measurements",
  unavailable: "/__e2e__/static/unavailable/measurements.json",
  partial: "/__e2e__/api/partial/measurements",
  sparse: "/__e2e__/static/sparse/measurements.json",
  hashMismatch: "/__e2e__/static/hash-mismatch/measurements.json",
  heavy: "/__e2e__/api/heavy/measurements",
};

test.describe.configure({ mode: "serial" });

async function waitForSseCount(page: Page, expectedCount: number) {
  await expect.poll(async () => page.evaluate(() => ((window as any).__EDEN_E2E_SSE__ ?? []).length)).toBe(expectedCount);
}

async function tabTo(page: Page, matcher: RegExp, reverse = false) {
  for (let index = 0; index < 400; index += 1) {
    await page.keyboard.press(reverse ? "Shift+Tab" : "Tab");
    const label = await page.evaluate(() => {
      const active = document.activeElement as HTMLElement | null;
      return active?.getAttribute("aria-label") || active?.innerText || active?.textContent || "";
    });
    if (matcher.test(label.trim())) return;
  }
  throw new Error(`Failed to focus element matching ${String(matcher)} with keyboard navigation.`);
}

function surfaceTab(page: Page, name: string) {
  return page.getByRole("tab", { name, exact: true });
}

function inspectorTab(page: Page, name: "Cards" | "Raw JSON") {
  return page.getByRole("tab", { name, exact: true });
}

function modeRadio(page: Page, name: string) {
  return page.getByRole("radio", { name, exact: true });
}

test("J01 @smoke @chromium boot, source honesty, and build freshness", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  await resetScenario(request, "stale");
  await resetScenario(request, "unavailable");
  const recorder = await attachRecorder(page);
  const liveBefore = await snapshotLedger(request, ledgers.normalLive);
  const staleBefore = await snapshotLedger(request, ledgers.stale);
  const unavailableBefore = await snapshotLedger(request, ledgers.unavailable);

  await page.goto(pages.liveNormal);
  await expect(page.getByText("exp-observatory-e2e")).toBeVisible();
  await assertSourceMode(page, "Live API");
  await expect(page.getByText(/Build warning:/)).toHaveCount(0);

  await page.goto(pages.staticNormal);
  await assertSourceMode(page, "Static export");
  await assertPayloadStatus(page, /Static export mode reads adjacent JSON artifacts/);
  await expect(page.getByRole("button", { name: /^Preview$/ })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^Commit$/ })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^Revert$/ })).toHaveCount(0);

  await page.goto(pages.liveStale);
  await assertSourceMode(page, "Live API", /Build warning: checked-in observatory bundle is stale/);

  await page.goto(pages.liveUnavailable);
  await assertSourceMode(page, "Static export");
  await expect(page.getByText("exp-observatory-unavailable")).toBeVisible();

  const liveAfter = await snapshotLedger(request, ledgers.normalLive);
  const staleAfter = await snapshotLedger(request, ledgers.stale);
  const unavailableAfter = await snapshotLedger(request, ledgers.unavailable);
  expect(diffLedger(liveBefore, liveAfter).delta).toBe(0);
  expect(diffLedger(staleBefore, staleAfter).delta).toBe(0);
  expect(diffLedger(unavailableBefore, unavailableAfter).delta).toBe(0);
  expect(mutationRequests(recorder.network)).toHaveLength(0);
  expect(recorder.network.some((entry) => entry.url.includes("/__e2e__/api/normal/status"))).toBeTruthy();
  expect(recorder.network.some((entry) => entry.url.includes("/__e2e__/static/normal/overview.json"))).toBeTruthy();

  await persistJourneyEvidence(page, testInfo, "J01", recorder, {
    result: "pass",
    ledgerDiffs: {
      live: diffLedger(liveBefore, liveAfter),
      stale: diffLedger(staleBefore, staleAfter),
      unavailable: diffLedger(unavailableBefore, unavailableAfter),
    },
  });
});

test("J02 @chromium payload lifecycle clarity and progressive loading", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.normalLive);

  await page.goto(pages.liveNormal);
  await expect(page.getByText("Loading observatory payloads")).toBeVisible();
  await expect(page.getByText("exp-observatory-e2e")).toBeVisible();
  expect(recorder.network.some((entry) => entry.url.endsWith("/geometry"))).toBeFalsy();

  await surfaceTab(page, "Geometry").click();
  await assertGracefulDegradation(page, /Geometry payload loading/, /intentionally deferred until you open this tab/);
  await expect(page.getByText(/"coordinate_modes": \[/)).toBeVisible();
  const geometryCalls = recorder.network.filter((entry) => entry.url.includes("/geometry"));
  expect(geometryCalls.length).toBe(1);
  expect(mutationRequests(recorder.network)).toHaveLength(0);

  const ledgerAfter = await snapshotLedger(request, ledgers.normalLive);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(0);

  await persistJourneyEvidence(page, testInfo, "J02", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J03 @chromium graph inspect is read-only and provenance rich", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.normalLive);

  await page.goto(pages.liveNormal);
  await surfaceTab(page, "Graph").click();
  await expect(page.getByRole("button", { name: "Graph entity Persistence Loop" })).toBeVisible();
  await page.getByRole("button", { name: "Graph entity Persistence Loop" }).click();
  await expect(page.getByRole("heading", { name: "Identity" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ontology" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Provenance" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Cluster Membership" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Memode Membership" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Supporting Relations" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Active Set Presence" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Measurement History" })).toBeVisible();
  await expect(page.getByRole("definition").filter({ hasText: /^meme-persistence$/ })).toBeVisible();

  await inspectorTab(page, "Raw JSON").click();
  await expect(page.getByText(/"id": "meme-persistence"/)).toBeVisible();
  await inspectorTab(page, "Cards").click();
  await page.getByRole("button", { name: "Graph relation SUPPORTS: Persistence Loop -> Retrieval Bridge" }).click();
  await expect(page.locator(".inspector-cards").getByText(/OPERATOR_ASSERTED/)).toBeVisible();
  await expect(page.locator(".inspector-cards").getByText(/0.91/)).toBeVisible();
  expect(mutationRequests(recorder.network)).toHaveLength(0);

  const ledgerAfter = await snapshotLedger(request, ledgers.normalLive);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(0);

  await persistJourneyEvidence(page, testInfo, "J03", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J04 @chromium cross-surface coherence", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.normalLive);

  await page.goto(pages.liveNormal);
  await surfaceTab(page, "Graph").click();
  await page.getByRole("button", { name: "Graph entity Persistence Loop" }).click();
  await expect(page.getByRole("definition").filter({ hasText: /^meme-persistence$/ })).toBeVisible();

  await surfaceTab(page, "Basin").click();
  await expect(page.getByRole("definition").filter({ hasText: /^meme-persistence$/ })).toBeVisible();
  await page.getByRole("button", { name: "Basin turn T3 turn-003 Regard Cluster" }).click();
  await expect(page.getByRole("button", { name: "Transcript turn T3 turn-003" })).toHaveAttribute("data-state", "active");

  await surfaceTab(page, "Overview").click();
  await expect(page.getByRole("button", { name: "Transcript turn T3 turn-003" })).toHaveAttribute("data-state", "active");
  await surfaceTab(page, "Graph").click();
  await expect(page.getByRole("button", { name: "Transcript turn T3 turn-003" })).toHaveAttribute("data-state", "active");
  expect(mutationRequests(recorder.network)).toHaveLength(0);

  const ledgerAfter = await snapshotLedger(request, ledgers.normalLive);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(0);

  await persistJourneyEvidence(page, testInfo, "J04", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J05 @smoke @chromium basin provenance, derived badges, and sparse honesty", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  await resetScenario(request, "sparse");
  const recorder = await attachRecorder(page);
  const normalBefore = await snapshotLedger(request, ledgers.normalStatic);
  const sparseBefore = await snapshotLedger(request, ledgers.sparse);

  await page.goto(pages.staticNormal);
  await surfaceTab(page, "Basin").click();
  await expect(page.getByText(/Projection: svd_on_turn_features/)).toBeVisible();
  await expect(page.getByText(/Lift: flat/)).toBeVisible();
  await expect(page.getByText("Derived")).toBeVisible();
  await modeRadio(page, "time_lift").click();
  await expect(modeRadio(page, "time_lift")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByText(/Lift: time_lift/)).toBeVisible();
  if (await page.getByTestId("basin-plot").count()) {
    await expect(page.getByTestId("basin-plot")).toBeVisible();
  } else {
    await assertGracefulDegradation(page, /Basin renderer unavailable/, /Use Basin Turns, transcript buttons, and projection metadata/);
  }

  await page.goto(pages.staticSparse);
  await surfaceTab(page, "Basin").click();
  await expect(page.getByText("Sparse basin data")).toBeVisible();
  await expect(page.getByText(/Filtered trajectory contains fewer than two turns/)).toBeVisible();
  await expect(page.getByTestId("basin-plot")).toHaveCount(0);
  expect(mutationRequests(recorder.network)).toHaveLength(0);

  const normalAfter = await snapshotLedger(request, ledgers.normalStatic);
  const sparseAfter = await snapshotLedger(request, ledgers.sparse);
  expect(diffLedger(normalBefore, normalAfter).delta).toBe(0);
  expect(diffLedger(sparseBefore, sparseAfter).delta).toBe(0);

  await persistJourneyEvidence(page, testInfo, "J05", recorder, {
    result: "pass",
    ledgerDiffs: {
      normal: diffLedger(normalBefore, normalAfter),
      sparse: diffLedger(sparseBefore, sparseAfter),
    },
  });
});

test("J06 @chromium compare mode, layout controls, and browser-local layout snapshots", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.normalLive);

  await page.goto(pages.liveNormal);
  await surfaceTab(page, "Graph").click();
  await modeRadio(page, "Compare").click();
  await expect(modeRadio(page, "Compare")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByRole("heading", { name: "Baseline" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Modified" })).toBeVisible();
  await expect(modeRadio(page, "force")).toHaveAttribute("aria-checked", "true");

  await page.getByRole("spinbutton", { name: /ForceAtlas2.*Iterations/i }).fill("240");
  await page.getByRole("button", { name: "Run Layout" }).click();
  await expect(page.getByRole("radio", { name: "ForceAtlas2 run" })).toBeVisible();
  await page.getByRole("button", { name: "Save Local Snapshot" }).click();
  await expect(page.getByRole("radio", { name: /ForceAtlas2 snapshot/i })).toBeVisible();

  await page.getByRole("button", { name: /^Fruchterman-Reingold / }).click();
  await page.getByRole("spinbutton", { name: /Fruchterman-Reingold.*Iterations/i }).fill("5000");
  await page.getByRole("button", { name: "Run Layout" }).click();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByText(/Layout run cancelled/)).toBeVisible();

  const ledgerAfter = await snapshotLedger(request, ledgers.normalLive);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(0);
  expect(mutationRequests(recorder.network)).toHaveLength(0);

  await persistJourneyEvidence(page, testInfo, "J06", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J07 @chromium browser-local preset persistence remains non-authoritative", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  await resetScenario(request, "hash-mismatch");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.normalStatic);

  await page.goto(pages.staticNormal);
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();
  const storageBefore = await snapshotLocalStorage(page);
  await surfaceTab(page, "Graph").click();
  await expect(page.getByRole("button", { name: "Preview" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Commit" })).toBeDisabled();
  await modeRadio(page, "Compare").click();
  await modeRadio(page, "hidden").click();
  await page.reload();
  await surfaceTab(page, "Graph").click();
  await expect(modeRadio(page, "Compare")).toHaveAttribute("aria-checked", "true");
  await expect(modeRadio(page, "hidden")).toHaveAttribute("aria-checked", "true");
  const storageAfterRestore = await snapshotLocalStorage(page);

  await page.goto(pages.staticHashMismatch);
  await surfaceTab(page, "Graph").click();
  await expect(modeRadio(page, "Semantic Map")).toHaveAttribute("aria-checked", "true");
  const storageAfterMismatch = await snapshotLocalStorage(page);

  const ledgerAfter = await snapshotLedger(request, ledgers.normalStatic);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(0);
  expect(diffLocalStorage(storageBefore, storageAfterRestore).added.length).toBeGreaterThan(0);
  expect(diffLocalStorage(storageAfterRestore, storageAfterMismatch).added.length).toBeGreaterThan(0);
  expect(mutationRequests(recorder.network)).toHaveLength(0);

  await persistJourneyEvidence(page, testInfo, "J07", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
    localStorageDiff: {
      restore: diffLocalStorage(storageBefore, storageAfterRestore),
      mismatch: diffLocalStorage(storageAfterRestore, storageAfterMismatch),
    },
  });
});

test("J08 @chromium graceful degradation for partial payload failures", async ({ page, request }, testInfo) => {
  await resetScenario(request, "partial");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.partial);

  await page.goto(pages.livePartial);
  await expect(page.getByText("exp-observatory-partial")).toBeVisible();
  await surfaceTab(page, "Geometry").click();
  await assertGracefulDegradation(page, /Geometry payload error/, /500 Internal Server Error for \/__e2e__\/api\/partial\/geometry/);
  await surfaceTab(page, "Graph").click();
  await expect(page.getByRole("button", { name: "Graph entity Persistence Loop" })).toBeVisible();
  await expect(page.getByText(/Transcript payload error/)).toBeVisible();
  expect(mutationRequests(recorder.network)).toHaveLength(0);

  const ledgerAfter = await snapshotLedger(request, ledgers.partial);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(0);

  await persistJourneyEvidence(page, testInfo, "J08", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J09 @chromium SSE invalidation refresh discipline", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.normalLive);

  await page.goto(pages.liveNormal);
  await page.getByRole("button", { name: "Transcript turn T2 turn-002" }).click();
  await expect(page.getByRole("button", { name: "Transcript turn T2 turn-002" })).toHaveAttribute("data-state", "active");

  const triggerResult = await triggerInvalidation(request, "normal");
  await waitForSseCount(page, 1);
  await expect.poll(async () => {
    await surfaceTab(page, "Measurements").click();
    return page.textContent("pre");
  }).toContain('"events": 2');
  await surfaceTab(page, "Overview").click();
  await expect(page.getByRole("button", { name: "Transcript turn T2 turn-002" })).toHaveAttribute("data-state", "active");

  const ledgerAfter = await snapshotLedger(request, ledgers.normalLive);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(1);
  expect(mutationRequests(recorder.network)).toHaveLength(0);
  const sseEvents = await recorder.sseEvents();
  expect(sseEvents).toHaveLength(1);
  expect(sseEvents[0]).toMatchObject({
    experiment_id: "exp-observatory-e2e",
    session_id: "session-alpha",
    reason: "measurement_committed",
  });
  expect((sseEvents[0] as Record<string, unknown>).payload).toBeUndefined();

  await persistJourneyEvidence(page, testInfo, "J09", recorder, {
    result: "pass",
    triggerResult,
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J10 @chromium measure preview and commit stay authoritative", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.normalLive);

  await page.goto(pages.liveNormal);
  await surfaceTab(page, "Graph").click();
  await page.getByRole("button", { name: "Graph entity Persistence Loop" }).click();
  await modeRadio(page, "MEASURE").click();
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByText(/"action_type": "geometry_measurement_run"/)).toBeVisible();
  await page.getByRole("button", { name: "Commit" }).click();
  const measurementLedger = page.locator(".inspector-card").filter({ has: page.getByRole("heading", { name: "Measurement Ledger" }) });
  await expect(measurementLedger.getByText(/geometry_measurement_run/)).toBeVisible();

  const ledgerAfter = await snapshotLedger(request, ledgers.normalLive);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(1);
  expect(mutationRequests(recorder.network).some((entry) => entry.url.includes("/preview"))).toBeTruthy();
  expect(mutationRequests(recorder.network).some((entry) => entry.url.includes("/commit"))).toBeTruthy();

  await persistJourneyEvidence(page, testInfo, "J10", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J11 @chromium edge edit preview and commit update the visible relation surface", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.normalLive);

  await page.goto(pages.liveNormal);
  await surfaceTab(page, "Graph").click();
  await page.getByRole("button", { name: "Graph relation SUPPORTS: Persistence Loop -> Retrieval Bridge" }).click();
  await modeRadio(page, "EDIT").click();
  await page.getByRole("combobox", { name: "Edit action" }).selectOption("edge_update");
  await page.getByLabel("Edge type", { exact: true }).fill("REINFORCES");
  await page.getByLabel("Edge weight", { exact: true }).fill("1.4");
  await page.getByLabel("Operator label", { exact: true }).fill("browser_tester");
  await page.getByLabel("Rationale", { exact: true }).fill("Edge edit through the workbench");
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByText(/"action_type": "edge_update"/)).toBeVisible();
  await expect(page.getByText(/REINFORCES/)).toBeVisible();
  await page.getByRole("button", { name: "Commit" }).click();
  await expect(page.getByRole("button", { name: "Graph relation REINFORCES: Persistence Loop -> Retrieval Bridge" })).toBeVisible();

  const ledgerAfter = await snapshotLedger(request, ledgers.normalLive);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(1);
  expect(mutationRequests(recorder.network).filter((entry) => entry.url.includes("/preview")).length).toBeGreaterThan(0);
  expect(mutationRequests(recorder.network).filter((entry) => entry.url.includes("/commit")).length).toBeGreaterThan(0);

  await persistJourneyEvidence(page, testInfo, "J11", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J12 @chromium memode assertion and membership update flow through preview and commit", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.normalLive);

  await page.goto(pages.liveNormal);
  await surfaceTab(page, "Graph").click();
  await page.getByRole("button", { name: "Graph entity Persistence Loop" }).click();
  await modeRadio(page, "EDIT").click();
  await page.getByRole("combobox", { name: "Edit action" }).selectOption("memode_assert");
  await page.getByLabel("Memode id", { exact: true }).fill("memode-harness");
  await page.getByLabel("Known memode label", { exact: true }).fill("Harness memode");
  await page.getByLabel("Known memode summary", { exact: true }).fill("Harness memode assertion.");
  await page.getByLabel("Rationale", { exact: true }).fill("Assert a reusable memode.");
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByText(/"action_type": "memode_assert"/)).toBeVisible();
  await page.getByRole("button", { name: "Commit" }).click();
  await expect(page.getByRole("button", { name: "Assembly Harness memode" })).toBeVisible();

  await page.getByRole("button", { name: "Graph entity Retrieval Bridge" }).click();
  await page.getByRole("combobox", { name: "Edit action" }).selectOption("memode_update_membership");
  await page.getByLabel("Memode id", { exact: true }).fill("memode-harness");
  await page.getByLabel("Known memode summary", { exact: true }).fill("Membership refined in-browser.");
  await page.getByLabel("Rationale", { exact: true }).fill("Swap membership to the retrieval bridge.");
  await page.getByRole("button", { name: "Preview" }).click();
  await expect(page.getByText(/"action_type": "memode_update_membership"/)).toBeVisible();
  await page.getByRole("button", { name: "Commit" }).click();
  await page.getByRole("button", { name: "Assembly Harness memode" }).click();
  await inspectorTab(page, "Raw JSON").click();
  const rawInspector = page.locator("#observatory-inspector-panel .debug-json");
  await expect(rawInspector).toContainText('"id": "memode-harness"');
  await expect(rawInspector).toContainText('"meme-retrieval"');
  await inspectorTab(page, "Cards").click();

  const ledgerAfter = await snapshotLedger(request, ledgers.normalLive);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(2);

  await persistJourneyEvidence(page, testInfo, "J12", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J13 @chromium revert restores the browser-visible graph state", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.normalLive);

  await page.goto(pages.liveNormal);
  await surfaceTab(page, "Graph").click();
  await page.getByRole("button", { name: "Graph relation SUPPORTS: Persistence Loop -> Retrieval Bridge" }).click();
  await modeRadio(page, "EDIT").click();
  await page.getByRole("combobox", { name: "Edit action" }).selectOption("edge_remove");
  await page.getByLabel("Rationale", { exact: true }).fill("Temporarily remove the bridge.");
  await page.getByRole("button", { name: "Commit" }).click();
  await expect(page.getByRole("button", { name: "Graph relation SUPPORTS: Persistence Loop -> Retrieval Bridge" })).toHaveCount(0);
  await page.getByRole("button", { name: "Revert" }).first().click();
  await expect(page.getByRole("button", { name: "Graph relation SUPPORTS: Persistence Loop -> Retrieval Bridge" })).toBeVisible();

  const ledgerAfter = await snapshotLedger(request, ledgers.normalLive);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(2);
  expect(mutationRequests(recorder.network).some((entry) => entry.url.includes("/revert"))).toBeTruthy();

  await persistJourneyEvidence(page, testInfo, "J13", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J14 @chromium runtime trace and causality surface are visible in the browser", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.normalLive);

  await page.goto(pages.liveNormal);
  await surfaceTab(page, "Graph").click();
  await expect(page.getByRole("heading", { name: "Runtime Trace" })).toBeVisible();
  await expect(page.getByText(/Trace and causality remain read-only/)).toBeVisible();
  await expect(page.getByText(/geometry_measurement_run committed from observatory/)).toBeVisible();
  expect(recorder.network.some((entry) => entry.url.includes("/trace"))).toBeTruthy();
  expect(mutationRequests(recorder.network)).toHaveLength(0);

  const ledgerAfter = await snapshotLedger(request, ledgers.normalLive);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(0);

  await persistJourneyEvidence(page, testInfo, "J14", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J15 @chromium large-graph resilience, textual caps, and layout fallback honesty", async ({ page, request }, testInfo) => {
  await resetScenario(request, "heavy");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.heavy);

  await page.goto(pages.liveHeavy);
  await expect(page.getByText("exp-observatory-heavy")).toBeVisible();
  await surfaceTab(page, "Graph").click();
  await expect(page.getByText(/Showing first 12 of 24 graph entities/)).toBeVisible();
  await expect(page.getByText(/Showing first 12 of 23 relations/)).toBeVisible();
  await page.getByRole("button", { name: "Run Layout" }).click();
  await expect(page.getByText(/Layout skipped above heavy cap \(18 nodes\)/)).toBeVisible();
  await surfaceTab(page, "Basin").click();
  await expect(page.getByText(/Showing first 12 of 16 basin turns/)).toBeVisible();
  expect(mutationRequests(recorder.network)).toHaveLength(0);

  const ledgerAfter = await snapshotLedger(request, ledgers.heavy);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(0);

  await persistJourneyEvidence(page, testInfo, "J15", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J16a @chromium supported HTTP-served static parity and honest limitations", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  const recorder = await attachRecorder(page);
  const liveBefore = await snapshotLedger(request, ledgers.normalLive);
  const staticBefore = await snapshotLedger(request, ledgers.normalStatic);

  await page.goto(pages.liveNormal);
  await surfaceTab(page, "Graph").click();
  await expect(page.getByRole("button", { name: "Graph entity Persistence Loop" })).toBeVisible();
  await surfaceTab(page, "Basin").click();
  await expect(page.getByText(/Projection: svd_on_turn_features/)).toBeVisible();
  await surfaceTab(page, "Measurements").click();
  await expect(page.getByText(/"events": 1/)).toBeVisible();

  await page.goto(pages.staticNormal);
  await assertSourceMode(page, "Static export");
  await expect(page.getByRole("button", { name: /^Preview$/ })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^Commit$/ })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^Revert$/ })).toHaveCount(0);
  await surfaceTab(page, "Graph").click();
  await expect(page.getByRole("button", { name: "Graph entity Persistence Loop" })).toBeVisible();
  await surfaceTab(page, "Basin").click();
  await expect(page.getByText(/Projection: svd_on_turn_features/)).toBeVisible();
  await surfaceTab(page, "Measurements").click();
  await expect(page.getByText(/"events": 1/)).toBeVisible();
  expect(mutationRequests(recorder.network)).toHaveLength(0);
  expect(recorder.network.some((entry) => entry.url.includes("/__e2e__/api/normal/"))).toBeTruthy();
  expect(recorder.network.some((entry) => entry.url.includes("/__e2e__/static/normal/"))).toBeTruthy();

  const liveAfter = await snapshotLedger(request, ledgers.normalLive);
  const staticAfter = await snapshotLedger(request, ledgers.normalStatic);
  expect(diffLedger(liveBefore, liveAfter).delta).toBe(0);
  expect(diffLedger(staticBefore, staticAfter).delta).toBe(0);

  await persistJourneyEvidence(page, testInfo, "J16a", recorder, {
    result: "pass",
    ledgerDiffs: {
      live: diffLedger(liveBefore, liveAfter),
      static: diffLedger(staticBefore, staticAfter),
    },
  });
});

test("J16b @chromium unsupported file runtime does not reach supported static-ready state", async ({ page }, testInfo) => {
  const recorder = await attachRecorder(page);
  const exportFixture = await findRealExportFixture();
  const ledgerBefore = await snapshotLedgerFile(exportFixture.measurementEvents);

  await page.goto(exportFixture.fileUrl, { waitUntil: "load" });
  await page.waitForTimeout(1000);

  await expect(page.getByRole("heading", { name: "Live-first semantic graph and basin instrument" })).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "Overview", exact: true })).toHaveCount(0);
  expect(mutationRequests(recorder.network)).toHaveLength(0);
  expect(
    recorder.consoleMessages.some((message) => message.startsWith("error:")) ||
      recorder.network.some((entry) => Boolean(entry.failureText)),
  ).toBeTruthy();

  const ledgerAfter = await snapshotLedgerFile(exportFixture.measurementEvents);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(0);

  await persistJourneyEvidence(page, testInfo, "J16b", recorder, {
    result: "pass",
    exportDir: exportFixture.exportDir,
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});

test("J17 @smoke @chromium keyboard-operable controls and textual graph equivalents", async ({ page, request }, testInfo) => {
  await resetScenario(request, "normal");
  const recorder = await attachRecorder(page);
  const ledgerBefore = await snapshotLedger(request, ledgers.normalStatic);

  await page.goto(pages.staticNormal);
  await tabTo(page, /^Graph$/);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Graph entity Persistence Loop" })).toBeVisible();
  await tabTo(page, /^Graph entity Persistence Loop$/);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("definition").filter({ hasText: /^meme-persistence$/ })).toBeVisible();
  await tabTo(page, /^Raw JSON$/);
  await page.keyboard.press("Enter");
  await expect(page.getByText(/"id": "meme-persistence"/)).toBeVisible();
  await tabTo(page, /^Basin$/, true);
  await page.keyboard.press("Enter");
  await expect(surfaceTab(page, "Basin")).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("heading", { name: "Basin Turns" })).toBeVisible();
  expect(mutationRequests(recorder.network)).toHaveLength(0);

  const ledgerAfter = await snapshotLedger(request, ledgers.normalStatic);
  expect(diffLedger(ledgerBefore, ledgerAfter).delta).toBe(0);

  await persistJourneyEvidence(page, testInfo, "J17", recorder, {
    result: "pass",
    ledgerDiff: diffLedger(ledgerBefore, ledgerAfter),
  });
});
