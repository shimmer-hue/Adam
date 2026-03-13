import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, type APIRequestContext, type Page, type TestInfo } from "@playwright/test";

type NetworkRecord = {
  method: string;
  url: string;
  resourceType: string;
  postData: string | null;
  startedAt: number;
  status?: number;
  responseBodySnippet?: string;
  failureText?: string;
};

type Recorder = {
  consoleMessages: string[];
  network: NetworkRecord[];
  sseEvents: () => Promise<any[]>;
};

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");
const HARNESS_ORIGIN = process.env.PLAYWRIGHT_TEST_BASE_URL ?? "http://127.0.0.1:4173";

function resolveHarnessUrl(url: string) {
  return new URL(url, HARNESS_ORIGIN).toString();
}

export async function attachRecorder(page: Page): Promise<Recorder> {
  const consoleMessages: string[] = [];
  const network: NetworkRecord[] = [];

  await page.addInitScript(() => {
    const NativeEventSource = window.EventSource;
    const store: unknown[] = [];
    (window as any).__EDEN_E2E_SSE__ = store;
    class WrappedEventSource extends NativeEventSource {
      constructor(url: string | URL, eventSourceInitDict?: EventSourceInit) {
        super(url, eventSourceInitDict);
        this.addEventListener("observatory.invalidate", (event) => {
          const payload = (event as MessageEvent).data;
          try {
            store.push(JSON.parse(payload));
          } catch {
            store.push({ raw: String(payload) });
          }
        });
      }
    }
    (window as any).EventSource = WrappedEventSource;
  });

  page.on("console", (message) => {
    consoleMessages.push(`${message.type()}: ${message.text()}`);
  });

  page.on("request", (request) => {
    network.push({
      method: request.method(),
      url: request.url(),
      resourceType: request.resourceType(),
      postData: request.postData() ?? null,
      startedAt: Date.now(),
    });
  });

  page.on("response", async (response) => {
    const record = [...network].reverse().find((candidate) => candidate.url === response.url() && candidate.status == null);
    if (!record) return;
    record.status = response.status();
    const contentType = response.headers()["content-type"] ?? "";
    if (contentType.includes("application/json")) {
      try {
        record.responseBodySnippet = (await response.text()).slice(0, 600);
      } catch {
        record.responseBodySnippet = "<unavailable>";
      }
    }
  });

  page.on("requestfailed", (request) => {
    const record = [...network].reverse().find((candidate) => candidate.url === request.url() && candidate.failureText == null);
    if (record) {
      record.failureText = request.failure()?.errorText ?? "request failed";
      return;
    }
    network.push({
      method: request.method(),
      url: request.url(),
      resourceType: request.resourceType(),
      postData: request.postData() ?? null,
      startedAt: Date.now(),
      failureText: request.failure()?.errorText ?? "request failed",
    });
  });

  return {
    consoleMessages,
    network,
    sseEvents: async () => page.evaluate(() => ((window as any).__EDEN_E2E_SSE__ ?? []) as any[]),
  };
}

export async function resetScenario(request: APIRequestContext, scenario: string) {
  const response = await request.post(resolveHarnessUrl(`/__e2e__/control/${scenario}/reset`));
  expect(response.ok()).toBeTruthy();
}

export async function triggerInvalidation(request: APIRequestContext, scenario: string) {
  const response = await request.post(resolveHarnessUrl(`/__e2e__/control/${scenario}/trigger-invalidation`));
  expect(response.ok()).toBeTruthy();
  return response.json();
}

export async function snapshotLedger(request: APIRequestContext, url: string) {
  const response = await request.get(resolveHarnessUrl(url));
  expect(response.ok()).toBeTruthy();
  return response.json();
}

export async function snapshotLedgerFile(filePath: string) {
  return JSON.parse(await fs.readFile(filePath, "utf8"));
}

export function diffLedger(before: any, after: any) {
  return {
    beforeCount: Number(before?.counts?.events ?? 0),
    afterCount: Number(after?.counts?.events ?? 0),
    delta: Number(after?.counts?.events ?? 0) - Number(before?.counts?.events ?? 0),
    beforeActionTypes: before?.counts?.action_types ?? {},
    afterActionTypes: after?.counts?.action_types ?? {},
  };
}

export async function snapshotLocalStorage(page: Page) {
  return page.evaluate(() => {
    const result: Record<string, string> = {};
    for (let index = 0; index < window.localStorage.length; index += 1) {
      const key = window.localStorage.key(index);
      if (key) result[key] = window.localStorage.getItem(key) ?? "";
    }
    return result;
  });
}

export function diffLocalStorage(before: Record<string, string>, after: Record<string, string>) {
  const added = Object.keys(after).filter((key) => !(key in before));
  const removed = Object.keys(before).filter((key) => !(key in after));
  const changed = Object.keys(after).filter((key) => key in before && before[key] !== after[key]);
  return { added, removed, changed };
}

export async function assertSourceMode(page: Page, expectedLabel: "Live API" | "Static export", buildWarning?: string | RegExp) {
  await expect(page.getByText(expectedLabel, { exact: true }).first()).toBeVisible();
  const opposite = expectedLabel === "Live API" ? "Static export" : "Live API";
  await expect(page.getByText(opposite, { exact: true })).toHaveCount(0);
  if (buildWarning) {
    await expect(page.getByText(buildWarning)).toBeVisible();
  }
}

export async function assertPayloadStatus(page: Page, statusCopy: string | RegExp) {
  await expect(page.getByText(statusCopy)).toBeVisible();
}

export async function assertGracefulDegradation(page: Page, scopedHeading: string | RegExp, diagnosticText: string | RegExp) {
  await expect(page.getByText(scopedHeading).first()).toBeVisible();
  await expect(page.getByText(diagnosticText).first()).toBeVisible();
}

export function mutationRequests(network: NetworkRecord[]) {
  return network.filter((entry) => entry.method === "POST");
}

export async function findRealExportFixture() {
  const exportsRoot = path.join(REPO_ROOT, "exports");
  const entries = await fs.readdir(exportsRoot, { withFileTypes: true });
  const directories = entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort();

  for (const directory of directories) {
    const exportDir = path.join(exportsRoot, directory);
    const observatoryIndex = path.join(exportDir, "observatory_index.html");
    const measurementEvents = path.join(exportDir, "measurement_events.json");
    const bundledApp = path.join(exportDir, "_observatory_app", "index.js");
    try {
      await Promise.all([
        fs.access(observatoryIndex),
        fs.access(measurementEvents),
        fs.access(bundledApp),
      ]);
      return {
        exportDir,
        observatoryIndex,
        measurementEvents,
        fileUrl: `file://${observatoryIndex}`,
      };
    } catch {
      // keep scanning until a complete export bundle is found
    }
  }

  throw new Error(`No real observatory export fixture found under ${exportsRoot}.`);
}

export async function persistJourneyEvidence(
  page: Page,
  testInfo: TestInfo,
  journeyId: string,
  recorder: Recorder,
  extra: Record<string, unknown>,
) {
  const screenshotPath = testInfo.outputPath(`${journeyId}.png`);
  const domPath = testInfo.outputPath(`${journeyId}.html`);
  const jsonPath = testInfo.outputPath(`${journeyId}.json`);
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await fs.writeFile(domPath, await page.content(), "utf8");
  const payload = {
    journeyId,
    screenshotPath,
    domPath,
    consoleMessages: recorder.consoleMessages,
    network: recorder.network,
    sseEvents: await recorder.sseEvents(),
    ...extra,
  };
  await fs.writeFile(jsonPath, JSON.stringify(payload, null, 2), "utf8");
  if (!Array.isArray(payload.consoleMessages) || !Array.isArray(payload.network) || !Array.isArray(payload.sseEvents)) {
    throw new Error(`${journeyId} evidence payload is missing recorder arrays.`);
  }
  if (typeof payload.result !== "string" || !payload.result) {
    throw new Error(`${journeyId} evidence payload is missing a string result.`);
  }
  const stats = await Promise.all([fs.stat(screenshotPath), fs.stat(domPath), fs.stat(jsonPath)]);
  if (stats.some((stat) => stat.size <= 0)) {
    throw new Error(`${journeyId} evidence bundle is missing or empty.`);
  }
  await testInfo.attach(`${journeyId}-evidence`, { path: jsonPath, contentType: "application/json" });
  await testInfo.attach(`${journeyId}-screenshot`, { path: screenshotPath, contentType: "image/png" });
  await testInfo.attach(`${journeyId}-dom`, { path: domPath, contentType: "text/html" });
  return { screenshotPath, domPath, jsonPath };
}
