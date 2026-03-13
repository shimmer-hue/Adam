import fs from "node:fs";
import fsp from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { cloneScenarioState, createScenarioStore } from "./fixtures.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const defaultRoot = path.resolve(__dirname, "../../../../../..");
const args = process.argv.slice(2);
const port = Number(readArg("--port", "4173"));
const root = path.resolve(readArg("--root", defaultRoot));

const scenarioTemplates = createScenarioStore();
const scenarioState = new Map(Object.keys(scenarioTemplates).map((name) => [name, cloneScenarioState(scenarioTemplates, name)]));
const sseClients = new Map();

const pageDefinitions = {
  "live-normal": { scenario: "normal", liveMode: "live" },
  "static-normal": { scenario: "normal", liveMode: "static" },
  "live-stale": { scenario: "stale", liveMode: "live" },
  "live-unavailable": { scenario: "unavailable", liveMode: "live" },
  "live-partial": { scenario: "partial", liveMode: "live" },
  "static-sparse": { scenario: "sparse", liveMode: "static" },
  "static-hash-mismatch": { scenario: "hash-mismatch", liveMode: "static" },
  "live-heavy": { scenario: "heavy", liveMode: "live" },
};

const server = http.createServer(async (request, response) => {
  try {
    await handleRequest(request, response);
  } catch (error) {
    response.writeHead(500, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
    response.end(JSON.stringify({ error: error instanceof Error ? error.message : String(error) }, null, 2));
  }
});

server.listen(port, "127.0.0.1", () => {
  process.stdout.write(`Observatory E2E harness listening on http://127.0.0.1:${port}\n`);
});

function readArg(flag, fallback) {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : fallback;
}

function stateFor(name) {
  if (!scenarioState.has(name)) {
    throw new Error(`Unknown scenario '${name}'.`);
  }
  return scenarioState.get(name);
}

function resetScenario(name) {
  scenarioState.set(name, cloneScenarioState(scenarioTemplates, name));
  closeScenarioClients(name);
}

function closeScenarioClients(name) {
  const clients = sseClients.get(name) ?? [];
  for (const client of clients) {
    try {
      client.write(": reset\n\n");
      client.end();
    } catch {
      // ignore teardown errors
    }
  }
  sseClients.delete(name);
}

async function readJsonBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  const raw = Buffer.concat(chunks).toString("utf8").trim();
  return raw ? JSON.parse(raw) : {};
}

function nextSyntheticId(state, prefix) {
  state.synthetic_sequence = Number(state.synthetic_sequence ?? state.measurements?.events?.length ?? 0) + 1;
  return `${prefix}-${String(state.synthetic_sequence).padStart(3, "0")}`;
}

function computeCounts(events) {
  const action_types = {};
  const evidence_labels = {};
  for (const event of events) {
    action_types[event.action_type] = (action_types[event.action_type] ?? 0) + 1;
    evidence_labels[event.evidence_label] = (evidence_labels[event.evidence_label] ?? 0) + 1;
  }
  return { events: events.length, action_types, evidence_labels };
}

function refreshDerivedState(state) {
  state.measurements.counts = computeCounts(state.measurements.events);
  state.graph.counts.measurement_events = state.measurements.counts.events;
  state.graph.counts.edges = state.graph.semantic_edges.length;
  state.graph.counts.memodes = state.graph.assemblies.length;
  state.overview.graph_counts = state.graph.counts;
  state.overview.measurements = state.measurements.counts;
  state.overview.hum = state.transcript?.hum ?? null;
}

function appendTrace(state, eventType, message, payload = {}) {
  state.trace ??= {
    session: { id: state.session_id, experiment_id: state.experiment_id, title: "Harness session" },
    session_id: state.session_id,
    latest_turn_id: state.basin.turns.at(-1)?.turn_id ?? null,
    latest_turn_index: state.basin.turns.at(-1)?.turn_index ?? null,
    latest_turn_trace: [],
    trace_events: [],
    membrane_events: [],
  };
  state.trace.trace_events.unshift({
    id: nextSyntheticId(state, "trace"),
    event_type: eventType,
    created_at: "2026-03-11T12:20:00Z",
    message,
    payload,
  });
}

function edgeIdFor(action) {
  return action.edge_id || `edge-${String(action.source_id)}-${String(action.target_id)}-${String(action.edge_type || action.current_edge_type || "EDGE")}`;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function buildEdge(action, existing = {}) {
  return {
    ...clone(existing),
    id: existing.id || edgeIdFor(action),
    source: action.source_id,
    target: action.target_id,
    type: action.edge_type || action.current_edge_type || existing.type || "SUPPORTS",
    weight: Number(action.weight ?? existing.weight ?? 1),
    evidence_label: action.evidence_label || existing.evidence_label || "OPERATOR_ASSERTED",
    operator_label: action.operator_label || existing.operator_label || "Brian the operator",
    confidence: Number(action.confidence ?? existing.confidence ?? 0.7),
    assertion_origin: existing.assertion_origin || "operator_asserted",
    measurement_history: clone(existing.measurement_history ?? []),
    measurement_event_ids: clone(existing.measurement_event_ids ?? []),
    reverted: false,
    provenance: {
      assertion_origin: existing.assertion_origin || "operator_asserted",
      evidence_label: action.evidence_label || existing.evidence_label || "OPERATOR_ASSERTED",
      confidence: Number(action.confidence ?? existing.confidence ?? 0.7),
      rationale: action.rationale || existing.provenance?.rationale || "",
    },
  };
}

function findEdge(state, action) {
  return (
    state.graph.semantic_edges.find((edge) => edge.id === action.edge_id) ??
    state.graph.semantic_edges.find(
      (edge) =>
        edge.source === action.source_id &&
        edge.target === action.target_id &&
        (!action.current_edge_type || edge.type === action.current_edge_type),
    ) ??
    null
  );
}

function compareSelection(action) {
  const ids = [...new Set((action.selected_node_ids ?? []).filter(Boolean))];
  if (action.source_id) ids.push(action.source_id);
  if (action.target_id) ids.push(action.target_id);
  return [...new Set(ids)];
}

function previewForAction(state, action) {
  const selectionIds = compareSelection(action);
  const existingEdge = findEdge(state, action);
  const patch = {
    graph_changed: false,
    added_nodes: [],
    removed_nodes: [],
    added_edges: [],
    removed_edges: [],
    selection_before: action.selected_node_ids ?? [],
    selection_after: selectionIds,
  };
  const topology_change = {
    graph_changed: false,
    before_state: {},
    proposed_state: {},
  };

  if (action.action_type === "edge_add") {
    const edge = buildEdge(action);
    patch.graph_changed = true;
    patch.added_edges.push(edge);
    topology_change.graph_changed = true;
    topology_change.proposed_state = { edge };
  } else if (action.action_type === "edge_update" && existingEdge) {
    const updated = buildEdge(action, existingEdge);
    patch.graph_changed = true;
    patch.removed_edges.push(clone(existingEdge));
    patch.added_edges.push(updated);
    topology_change.graph_changed = true;
    topology_change.before_state = { edge: clone(existingEdge) };
    topology_change.proposed_state = { edge: updated };
  } else if (action.action_type === "edge_remove" && existingEdge) {
    patch.graph_changed = true;
    patch.removed_edges.push(clone(existingEdge));
    topology_change.graph_changed = true;
    topology_change.before_state = { edge: clone(existingEdge) };
    topology_change.proposed_state = { remove_edge_id: existingEdge.id };
  } else if (action.action_type === "memode_assert") {
    topology_change.proposed_state = { memode_id: action.memode_id || "__preview_memode__" };
  } else if (action.action_type === "memode_update_membership") {
    topology_change.proposed_state = { memode_id: action.memode_id, member_ids: action.member_ids ?? [] };
  }

  return {
    action_type: action.action_type,
    measurement_only: !patch.graph_changed,
    selection: { before: action.selected_node_ids ?? [], after: selectionIds },
    compare_selection: { baseline_node_ids: action.selected_node_ids ?? [], modified_node_ids: selectionIds },
    topology_change,
    preview_graph_patch: patch,
    global_metrics: { delta: { nodes: patch.added_nodes.length - patch.removed_nodes.length, edges: patch.added_edges.length - patch.removed_edges.length } },
    local_metrics: { delta: { selection_size: selectionIds.length } },
  };
}

function applyActionCommit(state, action, preview) {
  const before_state = {};
  const committed_state = { summary: action.rationale || `${action.action_type} committed from harness` };

  if (action.action_type === "edge_add") {
    const edge = buildEdge(action);
    state.graph.semantic_edges.unshift(edge);
    committed_state.edge = clone(edge);
  } else if (action.action_type === "edge_update") {
    const existingEdge = findEdge(state, action);
    if (existingEdge) {
      before_state.edge = clone(existingEdge);
      const updated = buildEdge(action, existingEdge);
      Object.assign(existingEdge, updated);
      committed_state.edge = clone(updated);
      committed_state.before_edge = before_state.edge;
    }
  } else if (action.action_type === "edge_remove") {
    const existingEdge = findEdge(state, action);
    if (existingEdge) {
      before_state.edge = clone(existingEdge);
      state.graph.semantic_edges = state.graph.semantic_edges.filter((edge) => edge.id !== existingEdge.id);
      committed_state.before_edge = before_state.edge;
    }
  } else if (action.action_type === "memode_assert") {
    const memode = {
      id: action.memode_id || nextSyntheticId(state, "memode"),
      label: action.label || action.memode_label || "Harness memode",
      summary: action.summary || action.rationale || "Harness memode assertion",
      domain: action.domain || "behavior",
      member_meme_ids: clone(action.member_ids ?? action.selected_node_ids ?? []),
      supporting_edge_ids: state.graph.semantic_edges
        .filter((edge) => (action.member_ids ?? action.selected_node_ids ?? []).includes(edge.source) && (action.member_ids ?? action.selected_node_ids ?? []).includes(edge.target))
        .map((edge) => edge.id),
      member_order: clone(action.member_ids ?? action.selected_node_ids ?? []),
      invariance_summary: action.summary || "Harness memode assertion",
      evidence_label: action.evidence_label || "OPERATOR_ASSERTED",
      operator_label: action.operator_label || "Brian the operator",
      confidence: Number(action.confidence ?? 0.8),
      created_at: "2026-03-11T12:21:00Z",
      measurement_history: [],
    };
    state.graph.assemblies.unshift(memode);
    committed_state.memode = clone(memode);
  } else if (action.action_type === "memode_update_membership") {
    const memode = state.graph.assemblies.find((entry) => entry.id === action.memode_id);
    if (memode) {
      before_state.memode = clone(memode);
      memode.member_meme_ids = clone(action.member_ids ?? []);
      memode.member_order = clone(action.member_ids ?? []);
      memode.summary = action.summary || memode.summary;
      committed_state.memode = clone(memode);
      committed_state.before_memode = before_state.memode;
    }
  } else if (action.action_type === "motif_annotation") {
    committed_state.annotation = {
      cluster_signature: action.cluster_signature || "cluster-loop",
      manual_label: action.manual_label || "Annotated cluster",
      manual_summary: action.manual_summary || action.rationale || "",
    };
  }

  const event = {
    id: nextSyntheticId(state, "evt"),
    action_type: action.action_type,
    evidence_label: action.evidence_label || "DERIVED",
    operator_label: action.operator_label || "local_operator",
    measurement_method: action.measurement_method || "local_geometry_preview",
    confidence: Number(action.confidence ?? 0.7),
    rationale: action.rationale || "",
    created_at: "2026-03-11T12:22:00Z",
    target_ids: selectionTargets(action),
    before_state,
    proposed_state: preview.topology_change?.proposed_state ?? {},
    committed_state,
    summary: committed_state.summary,
  };
  state.measurements.events.unshift(event);
  appendTrace(
    state,
    preview.measurement_only ? "OBSERVATORY_MEASUREMENT" : "OBSERVATORY_EDIT",
    `${action.action_type} committed from observatory`,
    { measurement_event_id: event.id, summary: committed_state.summary },
  );
  refreshDerivedState(state);
  return { event, committed_state };
}

function selectionTargets(action) {
  const ids = compareSelection(action);
  return ids;
}

function applyRevert(state, eventId) {
  const target = state.measurements.events.find((event) => event.id === eventId);
  if (!target) {
    throw new Error(`Unknown event '${eventId}'.`);
  }

  const committed_state = { summary: `reverted ${eventId}` };
  if (target.action_type === "edge_add") {
    const edgeId = target.committed_state?.edge?.id;
    state.graph.semantic_edges = state.graph.semantic_edges.filter((edge) => edge.id !== edgeId);
  } else if (target.action_type === "edge_update") {
    const beforeEdge = target.before_state?.edge ?? target.committed_state?.before_edge;
    if (beforeEdge) {
      const index = state.graph.semantic_edges.findIndex((edge) => edge.id === beforeEdge.id);
      if (index >= 0) state.graph.semantic_edges[index] = clone(beforeEdge);
    }
  } else if (target.action_type === "edge_remove") {
    const beforeEdge = target.before_state?.edge ?? target.committed_state?.before_edge;
    if (beforeEdge) state.graph.semantic_edges.unshift(clone(beforeEdge));
  } else if (target.action_type === "memode_assert") {
    const memodeId = target.committed_state?.memode?.id;
    state.graph.assemblies = state.graph.assemblies.filter((entry) => entry.id !== memodeId);
  } else if (target.action_type === "memode_update_membership") {
    const beforeMemode = target.before_state?.memode ?? target.committed_state?.before_memode;
    if (beforeMemode) {
      const index = state.graph.assemblies.findIndex((entry) => entry.id === beforeMemode.id);
      if (index >= 0) state.graph.assemblies[index] = clone(beforeMemode);
    }
  }

  const revertEvent = {
    id: nextSyntheticId(state, "evt"),
    action_type: "revert",
    evidence_label: "OPERATOR_REFINED",
    operator_label: "local_operator",
    measurement_method: "revert",
    confidence: 1,
    rationale: `Reverted ${eventId}`,
    created_at: "2026-03-11T12:23:00Z",
    target_ids: target.target_ids ?? [],
    before_state: clone(target.committed_state ?? {}),
    proposed_state: { revert_event_id: eventId },
    committed_state,
    summary: committed_state.summary,
    reverted_from_event_id: eventId,
  };
  state.measurements.events.unshift(revertEvent);
  appendTrace(state, "OBSERVATORY_REVERT", `reverted observatory event ${eventId}`, { measurement_event_id: revertEvent.id });
  refreshDerivedState(state);
  return revertEvent;
}

async function handleRequest(request, response) {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const pathname = url.pathname;

  if (request.method === "POST" && pathname.startsWith("/__e2e__/control/")) {
    await handleControl(request, response, pathname);
    return;
  }
  if (pathname.startsWith("/__e2e__/pages/")) {
    await handlePage(response, pathname);
    return;
  }
  if (pathname.startsWith("/__e2e__/static/")) {
    await handleStaticPayload(response, pathname);
    return;
  }
  if (pathname.startsWith("/__e2e__/api/")) {
    await handleApi(request, response, pathname);
    return;
  }
  await serveFile(response, pathname);
}

async function handleControl(request, response, pathname) {
  const parts = pathname.split("/").filter(Boolean);
  const scenario = parts[2];
  const action = parts[3];

  if (action === "reset") {
    resetScenario(scenario);
    return sendJson(response, { ok: true, scenario, action: "reset" });
  }

  if (action === "trigger-invalidation") {
    const state = stateFor(scenario);
    const nextEvent = {
      id: nextSyntheticId(state, "evt"),
      action_type: "edge_add",
      evidence_label: "OPERATOR_ASSERTED",
      operator_label: "second_actor",
      measurement_method: "edge_commit",
      confidence: 0.77,
      rationale: "Synthetic external mutation for SSE refresh coverage.",
      created_at: "2026-03-11T12:15:00Z",
      target_ids: ["meme-persistence", "meme-retrieval"],
      before_state: {},
      proposed_state: { edge_type: "SUPPORTS" },
      committed_state: { summary: "External edge commit triggered by harness." },
      summary: "External edge commit triggered by harness.",
    };
    state.measurements.events.unshift(nextEvent);
    state.graph.semantic_nodes[0].measurement_history = [
      { id: nextEvent.id, action_type: nextEvent.action_type },
      ...(state.graph.semantic_nodes[0].measurement_history ?? []),
    ];
    appendTrace(state, "OBSERVATORY_EDIT", "edge_add committed from observatory", { measurement_event_id: nextEvent.id });
    refreshDerivedState(state);
    publishInvalidation(scenario, {
      experiment_id: state.experiment_id,
      session_id: state.session_id,
      kinds: ["graph", "measurements", "overview", "transcript", "trace"],
      reason: "measurement_committed",
    });
    return sendJson(response, { ok: true, scenario, event_id: nextEvent.id });
  }

  sendJson(response, { error: `Unknown control action '${action}'.` }, 404);
}

async function handlePage(response, pathname) {
  const pageName = pathname.split("/").pop()?.replace(/\.html$/, "") ?? "";
  const page = pageDefinitions[pageName];
  if (!page) {
    sendJson(response, { error: `Unknown page '${pageName}'.` }, 404);
    return;
  }
  const state = stateFor(page.scenario);
  const bootstrap = buildBootstrap(pageName, page, state);
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>EDEN Observatory</title>
  <link rel="stylesheet" href="/eden/observatory/static/observatory_app/style.css" />
</head>
<body>
  <div id="observatory-root"></div>
  <script>window.__EDEN_BOOTSTRAP__ = ${JSON.stringify(bootstrap).replace(/</g, "\\u003c")};</script>
  <script type="module" src="/eden/observatory/static/observatory_app/index.js"></script>
</body>
</html>`;
  response.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" });
  response.end(html);
}

function buildBootstrap(pageName, page, state) {
  const payloadUrls = {
    graph: `/__e2e__/static/${page.scenario}/graph.json`,
    basin: `/__e2e__/static/${page.scenario}/basin.json`,
    overview: `/__e2e__/static/${page.scenario}/overview.json`,
    measurements: `/__e2e__/static/${page.scenario}/measurements.json`,
    geometry: `/__e2e__/static/${page.scenario}/geometry.json`,
  };

  const bootstrap = {
    mode: page.liveMode === "static" ? "static" : "hybrid",
    initial_surface: "overview",
    experiment_id: state.experiment_id,
    session_id: state.session_id,
    export_manifest_id: state.graph.export_manifest_id,
    source_graph_hash: state.graph.source_graph_hash,
    projection_method: state.basin.projection_method,
    payload_urls: payloadUrls,
  };

  if (page.liveMode === "live") {
    bootstrap.live_api = {
      status: `/__e2e__/api/${page.scenario}/status`,
      runtime_status: `/__e2e__/api/${page.scenario}/runtime/status`,
      runtime_model: `/__e2e__/api/${page.scenario}/runtime/model`,
      events: `/__e2e__/api/${page.scenario}/events`,
      overview: `/__e2e__/api/${page.scenario}/overview`,
      graph: `/__e2e__/api/${page.scenario}/graph`,
      basin: `/__e2e__/api/${page.scenario}/basin`,
      measurements: `/__e2e__/api/${page.scenario}/measurements`,
      geometry: `/__e2e__/api/${page.scenario}/geometry`,
      preview: `/__e2e__/api/${page.scenario}/preview`,
      commit: `/__e2e__/api/${page.scenario}/commit`,
      revert: `/__e2e__/api/${page.scenario}/revert`,
      session_turns: `/__e2e__/api/${page.scenario}/transcript`,
      session_trace: `/__e2e__/api/${page.scenario}/trace`,
      sessions: `/__e2e__/api/${page.scenario}/sessions`,
    };
  }

  return bootstrap;
}

async function handleStaticPayload(response, pathname) {
  const [, , , scenario, fileName] = pathname.split("/");
  const state = stateFor(scenario);
  const payloadMap = {
    "graph.json": state.graph,
    "basin.json": state.basin,
    "overview.json": state.overview,
    "measurements.json": state.measurements,
    "geometry.json": state.geometry,
  };
  const payload = payloadMap[fileName];
  if (!payload) {
    sendJson(response, { error: `Unknown static payload '${fileName}'.` }, 404);
    return;
  }
  sendJson(response, payload);
}

async function handleApi(request, response, pathname) {
  const parts = pathname.split("/").filter(Boolean);
  const scenario = parts[2];
  const resource = parts.slice(3).join("/");
  const state = stateFor(scenario);

  if (request.method === "POST") {
    const body = await readJsonBody(request);
    if (resource === "preview") {
      return sendJson(response, previewForAction(state, body.action ?? {}));
    }
    if (resource === "commit") {
      const action = body.action ?? {};
      const preview = previewForAction(state, action);
      const committed = applyActionCommit(state, action, preview);
      publishInvalidation(scenario, {
        experiment_id: state.experiment_id,
        session_id: state.session_id,
        kinds: ["graph", "measurements", "overview", "trace"],
        reason: "measurement_committed",
      });
      return sendJson(response, {
        event: committed.event,
        preview,
        committed_state: committed.committed_state,
        payload: {
          graph: state.graph,
          basin: state.basin,
          geometry: state.geometry,
          measurements: state.measurements,
          index: state.overview,
        },
      });
    }
    if (resource === "revert") {
      const revertEvent = applyRevert(state, body.event_id);
      publishInvalidation(scenario, {
        experiment_id: state.experiment_id,
        session_id: state.session_id,
        kinds: ["graph", "measurements", "overview", "trace"],
        reason: "measurement_reverted",
      });
      return sendJson(response, {
        event: revertEvent,
        committed_state: revertEvent.committed_state,
        payload: {
          graph: state.graph,
          basin: state.basin,
          geometry: state.geometry,
          measurements: state.measurements,
          index: state.overview,
        },
      });
    }
    return sendJson(response, { error: `Unknown API resource '${resource}'.` }, 404);
  }

  if (resource === "events") {
    handleEvents(response, scenario);
    return;
  }

  const failure = state.failures?.[resource];
  if (failure) {
    await maybeDelay(state, resource);
    sendJson(response, failure.body, failure.status);
    return;
  }

  await maybeDelay(state, resource);

  if (resource === "status") {
    if (state.status.error) {
      sendJson(response, { error: state.status.error }, 503);
      return;
    }
    sendJson(response, state.status);
    return;
  }
  if (resource === "runtime/status") {
    sendJson(response, state.runtime_status);
    return;
  }
  if (resource === "runtime/model") {
    sendJson(response, state.runtime_model);
    return;
  }
  if (resource === "graph") {
    sendJson(response, state.graph);
    return;
  }
  if (resource === "basin") {
    sendJson(response, state.basin);
    return;
  }
  if (resource === "overview") {
    sendJson(response, state.overview);
    return;
  }
  if (resource === "measurements") {
    sendJson(response, state.measurements);
    return;
  }
  if (resource === "trace") {
    sendJson(response, state.trace);
    return;
  }
  if (resource === "geometry") {
    sendJson(response, state.geometry);
    return;
  }
  if (resource === "transcript") {
    sendJson(response, state.transcript);
    return;
  }
  if (resource === "sessions") {
    sendJson(response, { sessions: [{ id: state.session_id, experiment_id: state.experiment_id, title: "E2E session" }] });
    return;
  }

  sendJson(response, { error: `Unknown API resource '${resource}'.` }, 404);
}

async function maybeDelay(state, key) {
  const delay = Number(state.delays?.[key] ?? 0);
  if (delay > 0) {
    await new Promise((resolve) => setTimeout(resolve, delay));
  }
}

function handleEvents(response, scenario) {
  response.writeHead(200, {
    "Content-Type": "text/event-stream; charset=utf-8",
    "Cache-Control": "no-store",
    Connection: "keep-alive",
  });
  response.write(": connected\n\n");

  const clientList = sseClients.get(scenario) ?? [];
  clientList.push(response);
  sseClients.set(scenario, clientList);

  const heartbeat = setInterval(() => {
    response.write(": heartbeat\n\n");
  }, 5000);

  response.on("close", () => {
    clearInterval(heartbeat);
    const next = (sseClients.get(scenario) ?? []).filter((client) => client !== response);
    sseClients.set(scenario, next);
  });
}

function publishInvalidation(scenario, payload) {
  const encoded = JSON.stringify(payload);
  for (const client of sseClients.get(scenario) ?? []) {
    client.write("event: observatory.invalidate\n");
    client.write(`data: ${encoded}\n\n`);
  }
}

async function serveFile(response, pathname) {
  const safePath = pathname === "/" ? "/README.md" : pathname;
  const filePath = path.resolve(root, `.${safePath}`);
  if (!filePath.startsWith(root)) {
    sendJson(response, { error: "Forbidden path." }, 403);
    return;
  }
  let stat;
  try {
    stat = await fsp.stat(filePath);
  } catch {
    sendJson(response, { error: "File not found." }, 404);
    return;
  }
  if (stat.isDirectory()) {
    sendJson(response, { error: "Directory listing disabled." }, 404);
    return;
  }
  response.writeHead(200, {
    "Content-Type": contentType(filePath),
    "Content-Length": stat.size,
    "Cache-Control": "no-store",
  });
  fs.createReadStream(filePath).pipe(response);
}

function contentType(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  if (extension === ".html") return "text/html; charset=utf-8";
  if (extension === ".js") return "text/javascript; charset=utf-8";
  if (extension === ".css") return "text/css; charset=utf-8";
  if (extension === ".json") return "application/json; charset=utf-8";
  if (extension === ".md") return "text/plain; charset=utf-8";
  return "application/octet-stream";
}

function sendJson(response, payload, status = 200) {
  const body = JSON.stringify(payload, null, 2);
  response.writeHead(status, { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" });
  response.end(body);
}
