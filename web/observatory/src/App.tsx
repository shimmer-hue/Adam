import type { ReactNode } from "react";
import { startTransition, useEffect, useMemo, useRef, useState } from "react";

import BasinPanel from "./components/BasinPanel";
import GraphPanel from "./components/GraphPanel";
import TanakhPanel from "./components/TanakhPanel";
import {
  applyFilters,
  applyPreviewPatch,
  buildNodeLookup,
  csvForEdges,
  csvForNodes,
  defaultAppearanceState,
  defaultFilterState,
  downloadText,
  edgeKey,
  edgeLabel,
  gexfForGraph,
  graphMLForGraph,
  hashText,
  jsonForSelection,
  nodeLabel,
  type AppearanceState,
  type CoordinateMap,
  type FilterState,
  type GraphEdge,
  type GraphMode,
  type GraphNode,
  type LayoutSnapshot,
  visibleGraphForMode,
} from "./workbench/graphUtils";
import {
  humanLayoutLabel,
  isRunnableLayout,
  resolveLayoutCatalog,
  resolveLayoutDefaults,
  resolveLayoutFamilies,
  type LayoutAlgorithmMeta,
  type LayoutFamilyMeta,
} from "./workbench/layoutTerrain";

type Surface = "overview" | "graph" | "basin" | "geometry" | "tanakh" | "measurements";
type AssemblyRenderMode = "hulls" | "collapsed-meta-node" | "hidden";
type LiftMode = "flat" | "time_lift" | "density_lift" | "session_offset";
type InspectorTab = "cards" | "json";
type ReasoningLens = "reasoning" | "chain_like" | "hum_live";
type InteractionMode = "INSPECT" | "MEASURE" | "EDIT" | "ABLATE" | "COMPARE";
type PayloadKey = "overview" | "measurements" | "basin" | "graph" | "geometry" | "tanakh" | "transcript" | "trace" | "runtimeStatus" | "runtimeModel";
type PayloadStatusKind = "idle" | "loading" | "ready" | "error" | "deferred";

type Bootstrap = {
  mode?: string;
  initial_surface?: Surface;
  experiment_id?: string;
  session_id?: string | null;
  export_manifest_id?: string | null;
  source_graph_hash?: string | null;
  projection_method?: string | null;
  payload_urls?: Record<string, string>;
  live_api?: Record<string, string>;
};

type GraphPayload = {
  export_manifest_id?: string;
  source_graph_hash?: string;
  graph_modes?: GraphMode[];
  assembly_render_modes?: AssemblyRenderMode[];
  interaction_modes?: InteractionMode[];
  evidence_legend?: Record<string, any>;
  semantic_nodes: GraphNode[];
  semantic_edges: GraphEdge[];
  runtime_nodes: GraphNode[];
  runtime_edges: GraphEdge[];
  assemblies: any[];
  cluster_summaries: any[];
  active_set_slices: any[];
  counts?: Record<string, number>;
  filters?: Record<string, any>;
  view_modes?: Record<string, string>;
  layout_families?: LayoutFamilyMeta[];
  layout_catalog?: Record<string, any>;
  layout_defaults?: Record<string, any>;
  appearance_dimensions?: Record<string, string[]>;
  filter_dimensions?: Record<string, any>;
  statistics_capabilities?: Record<string, any>;
  export_formats?: string[];
};

type BasinPayload = {
  turns: any[];
  attractors: any[];
  diagnostics?: Record<string, any>;
  projection_method?: string;
  projection_version?: string;
  filtered_turn_count?: number;
  source_turn_count?: number;
};

type MeasurementsPayload = {
  counts?: Record<string, any>;
  events?: any[];
};

type OverviewPayload = {
  index?: Record<string, any>;
  summary?: Record<string, number>;
  graph_counts?: Record<string, number>;
  basin?: Record<string, any>;
  measurements?: Record<string, any>;
  tanakh?: Record<string, any>;
  hum?: Record<string, any>;
};

type TranscriptPayload = {
  hum?: Record<string, any>;
  turns?: any[];
};

type SessionTracePayload = {
  latest_turn_id?: string | null;
  latest_turn_index?: number;
  latest_turn_trace?: any[];
  trace_events?: any[];
  membrane_events?: any[];
};

type TanakhPayload = {
  current_ref?: string;
  bundle_hash?: string;
  artifacts?: Record<string, string>;
  bundle?: Record<string, any>;
  live_query_supported?: boolean;
};

type PreviewPayload = {
  action_type?: string;
  measurement_only?: boolean;
  selection?: { before?: string[]; after?: string[] };
  compare_selection?: { baseline_node_ids?: string[]; modified_node_ids?: string[] };
  topology_change?: Record<string, any>;
  preview_graph_patch?: Record<string, any>;
  global_metrics?: Record<string, any>;
  local_metrics?: Record<string, any>;
  error?: string;
};

type DataBundle = {
  graph: GraphPayload | null;
  basin: BasinPayload | null;
  overview: OverviewPayload | null;
  measurements: MeasurementsPayload | null;
  geometry: Record<string, any> | null;
  tanakh: TanakhPayload | null;
  transcript: TranscriptPayload | null;
  trace: SessionTracePayload | null;
  runtimeStatus: Record<string, any> | null;
  runtimeModel: Record<string, any> | null;
  liveEnabled: boolean;
  staleBuildWarning: string | null;
};

type ResolvedSources = Partial<Record<PayloadKey, string>> & {
  liveEnabled: boolean;
  staleBuildWarning: string | null;
};

type PayloadStatus = {
  label: string;
  detail: string;
  status: PayloadStatusKind;
  source: "live_api" | "static_export" | "none";
  error?: string;
};

type LayoutRunState = {
  running: boolean;
  paused: boolean;
  progress: number;
  target: string;
  lastMessage: string;
  activeRunId: string | null;
};

type StatsPayload = {
  summary?: Record<string, any>;
  rankings?: Record<string, Array<{ id: string; label: string; score: number }>>;
  communities?: Array<{ community: number; size: number }>;
  clustering?: Record<string, number>;
  weightedDegree?: Record<string, number>;
  error?: string;
};

type ActionForm = {
  editAction: string;
  edgeType: string;
  weight: number;
  confidence: number;
  operatorLabel: string;
  evidenceLabel: string;
  rationale: string;
  memodeId: string;
  memodeLabel: string;
  memodeDomain: string;
  memodeSummary: string;
  ablationRelation: string;
  manualLabel: string;
  manualSummary: string;
  transferPolicy: string;
};

const SURFACES: Surface[] = ["overview", "graph", "basin", "geometry", "tanakh", "measurements"];
const DEFAULT_GRAPH_MODE: GraphMode = "Semantic Map";
const DEFAULT_ASSEMBLY_RENDER_MODE: AssemblyRenderMode = "hulls";
const DEFAULT_LIFT_MODE: LiftMode = "flat";
const DEFAULT_INTERACTION_MODE: InteractionMode = "INSPECT";
const TEXT_ACCESS_LIMIT = 12;
const ESSENTIAL_PAYLOADS: PayloadKey[] = ["overview", "measurements", "basin"];
const PAYLOAD_ORDER: PayloadKey[] = ["overview", "measurements", "basin", "graph", "geometry", "tanakh", "transcript", "trace", "runtimeStatus", "runtimeModel"];

const EMPTY_DATA: DataBundle = {
  graph: null,
  basin: null,
  overview: null,
  measurements: null,
  geometry: null,
  tanakh: null,
  transcript: null,
  trace: null,
  runtimeStatus: null,
  runtimeModel: null,
  liveEnabled: false,
  staleBuildWarning: null,
};

const EMPTY_STATUS: Record<PayloadKey, PayloadStatus> = {
  overview: { label: "Overview", detail: "Index summary and artifact counts", status: "idle", source: "none" },
  measurements: { label: "Measurements", detail: "Measurement ledger and attribution counts", status: "idle", source: "none" },
  basin: { label: "Basin", detail: "Trajectory summary and attractor metadata", status: "idle", source: "none" },
  graph: { label: "Graph", detail: "Large semantic graph bundle", status: "idle", source: "none" },
  geometry: { label: "Geometry", detail: "Large diagnostics bundle", status: "idle", source: "none" },
  tanakh: { label: "Tanakh", detail: "Canonical text, derived analyzers, and merkavah scene sidecars", status: "idle", source: "none" },
  transcript: { label: "Transcript", detail: "Turn history and active-set cross-links", status: "idle", source: "none" },
  trace: { label: "Runtime trace", detail: "Trace events and latest-turn weighting surface", status: "idle", source: "none" },
  runtimeStatus: { label: "Runtime status", detail: "Live backend status", status: "idle", source: "none" },
  runtimeModel: { label: "Runtime model", detail: "Live model metadata", status: "idle", source: "none" },
};

const DEFAULT_LAYOUT_STATE: LayoutRunState = {
  running: false,
  paused: false,
  progress: 0,
  target: "forceatlas2",
  lastMessage: "",
  activeRunId: null,
};

const DEFAULT_ACTION_FORM: ActionForm = {
  editAction: "edge_add",
  edgeType: "CO_OCCURS_WITH",
  weight: 1,
  confidence: 0.7,
  operatorLabel: "local_operator",
  evidenceLabel: "OPERATOR_ASSERTED",
  rationale: "",
  memodeId: "",
  memodeLabel: "",
  memodeDomain: "behavior",
  memodeSummary: "",
  ablationRelation: "CO_OCCURS_WITH",
  manualLabel: "",
  manualSummary: "",
  transferPolicy: "exact_then_unique_best_jaccard_0.70",
};

function labelForSurface(surface: Surface): string {
  if (surface === "overview") return "Overview";
  if (surface === "graph") return "Graph";
  if (surface === "basin") return "Basin";
  if (surface === "geometry") return "Geometry";
  if (surface === "tanakh") return "Tanakh";
  return "Measurements";
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { credentials: "same-origin" });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText} for ${url}`);
  }
  return (await response.json()) as T;
}

function withSessionScope(url: string | undefined, sessionId: string | null | undefined): string | undefined {
  if (!url || !sessionId) return url;
  const scoped = new URL(url, window.location.href);
  if (!scoped.searchParams.has("session_id")) scoped.searchParams.set("session_id", sessionId);
  return scoped.pathname + scoped.search + scoped.hash;
}

function currentTurnNodeIds(graph: GraphPayload | null, transcript: TranscriptPayload | null, selectedTurnId: string | null): string[] {
  if (!selectedTurnId || !transcript?.turns?.length) return graph?.active_set_slices?.at(-1)?.node_ids ?? [];
  const turn = transcript.turns.find((item: any) => item.turn_id === selectedTurnId);
  return turn?.active_set_node_ids ?? [];
}

function storageKey({
  bootstrap,
  graph,
  surface,
}: {
  bootstrap: Bootstrap;
  graph: GraphPayload | null;
  surface: Surface;
}): string {
  const experimentId = bootstrap.experiment_id ?? "unknown";
  const manifestish =
    bootstrap.export_manifest_id ??
    graph?.export_manifest_id ??
    bootstrap.source_graph_hash ??
    graph?.source_graph_hash ??
    "live";
  return `eden.observatory.view_presets.v2::${experimentId}::${surface}::${manifestish}`;
}

function snapshotStorageKey(bootstrap: Bootstrap, graph: GraphPayload | null): string {
  const experimentId = bootstrap.experiment_id ?? "unknown";
  const manifestish =
    bootstrap.export_manifest_id ??
    graph?.export_manifest_id ??
    bootstrap.source_graph_hash ??
    graph?.source_graph_hash ??
    "live";
  return `eden.observatory.layout_snapshots.v1::${experimentId}::${manifestish}`;
}

function badgeClass(kind: "observed" | "derived" | "warning"): string {
  return `badge badge-${kind}`;
}

function payloadStatusClass(status: PayloadStatusKind): string {
  return `payload-chip payload-${status}`;
}

function sourceLabel(source: PayloadStatus["source"]): string {
  if (source === "live_api") return "live API";
  if (source === "static_export") return "static export";
  return "unavailable";
}

function MetricList({ items }: { items: Array<[string, unknown]> }) {
  return (
    <dl className="metric-list">
      {items.map(([label, value]) => (
        <div key={label} className="metric-row">
          <dt>{label}</dt>
          <dd>{formatValue(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function Card({ title, children, accent }: { title: string; children: ReactNode; accent?: string }) {
  return (
    <section className="inspector-card">
      <div className="card-header">
        <h3>{title}</h3>
        {accent ? <span className="card-accent">{accent}</span> : null}
      </div>
      {children}
    </section>
  );
}

function formatValue(value: unknown): string {
  if (value == null || value === "") return "—";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function excerptText(value: unknown, limit = 560): string {
  const text = String(value ?? "").trim();
  if (!text) return "";
  return text.length > limit ? `${text.slice(0, limit - 1).trimEnd()}…` : text;
}

function chainLikeSteps(value: unknown, limit = 6): string[] {
  const raw = String(value ?? "").replace(/\r/g, "\n").trim();
  if (!raw) return [];
  const segments = raw
    .split(/\n+/)
    .map((segment) => segment.trim())
    .filter(Boolean);
  const source = segments.length ? segments : raw.split(/(?<=[.!?])\s+/).map((segment) => segment.trim()).filter(Boolean);
  return source.slice(0, limit).map((segment, index) => `${index + 1}. ${excerptText(segment, 120)}`);
}

function cappedItems<T>(items: T[], limit = TEXT_ACCESS_LIMIT): { items: T[]; capped: boolean; total: number } {
  return {
    items: items.slice(0, limit),
    capped: items.length > limit,
    total: items.length,
  };
}

function initializePayloadStatuses(sources: Partial<Record<PayloadKey, string>>, liveEnabled: boolean): Record<PayloadKey, PayloadStatus> {
  const next = structuredClone(EMPTY_STATUS);
  for (const key of PAYLOAD_ORDER) {
    if (sources[key]) {
      next[key].source = liveEnabled ? "live_api" : "static_export";
      next[key].status = ESSENTIAL_PAYLOADS.includes(key) ? "loading" : key === "geometry" || key === "tanakh" ? "deferred" : "idle";
    }
  }
  return next;
}

function nowStamp(): string {
  return new Date().toISOString();
}

export default function App({ bootstrap }: { bootstrap: Bootstrap }) {
  const initialSurface = SURFACES.includes((bootstrap.initial_surface as Surface) ?? "overview")
    ? (bootstrap.initial_surface as Surface)
    : "overview";

  const [surface, setSurface] = useState<Surface>(initialSurface);
  const [graphMode, setGraphMode] = useState<GraphMode>(DEFAULT_GRAPH_MODE);
  const [assemblyRenderMode, setAssemblyRenderMode] = useState<AssemblyRenderMode>(DEFAULT_ASSEMBLY_RENDER_MODE);
  const [liftMode, setLiftMode] = useState<LiftMode>(DEFAULT_LIFT_MODE);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("cards");
  const [reasoningLens, setReasoningLens] = useState<ReasoningLens>("reasoning");
  const [interactionMode, setInteractionMode] = useState<InteractionMode>(DEFAULT_INTERACTION_MODE);
  const [coordinateMode, setCoordinateMode] = useState<string>("force");
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [selectedAssemblyId, setSelectedAssemblyId] = useState<string | null>(null);
  const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>(defaultFilterState());
  const [appearance, setAppearance] = useState<AppearanceState>(defaultAppearanceState());
  const [actionForm, setActionForm] = useState<ActionForm>(DEFAULT_ACTION_FORM);
  const [layoutTarget, setLayoutTarget] = useState<string>("forceatlas2");
  const [layoutSettings, setLayoutSettings] = useState<Record<string, Record<string, any>>>({});
  const [layoutRunState, setLayoutRunState] = useState<LayoutRunState>(DEFAULT_LAYOUT_STATE);
  const [layoutSnapshots, setLayoutSnapshots] = useState<LayoutSnapshot[]>([]);
  const [preview, setPreview] = useState<PreviewPayload | null>(null);
  const [mutationPending, setMutationPending] = useState(false);
  const [stats, setStats] = useState<StatsPayload | null>(null);
  const [statsPending, setStatsPending] = useState(false);
  const [loadedPresetKey, setLoadedPresetKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DataBundle>(EMPTY_DATA);
  const [resolvedSources, setResolvedSources] = useState<ResolvedSources | null>(null);
  const [payloadStatuses, setPayloadStatuses] = useState<Record<PayloadKey, PayloadStatus>>(EMPTY_STATUS);
  const [tanakhRunPending, setTanakhRunPending] = useState(false);
  const [lastExportMessage, setLastExportMessage] = useState<string>("");

  const layoutWorkerRef = useRef<Worker | null>(null);
  const statsWorkerRef = useRef<Worker | null>(null);
  const layoutSettingsRef = useRef<Record<string, Record<string, any>>>({});

  const presetStorageKey = useMemo(() => storageKey({ bootstrap, graph: data.graph, surface }), [bootstrap, data.graph, surface]);
  const snapshotsStorageKey = useMemo(() => snapshotStorageKey(bootstrap, data.graph), [bootstrap, data.graph]);

  const selectedNodeId = selectedNodeIds[0] ?? null;
  const unifiedNodes = useMemo(
    () =>
      [
        ...(data.graph?.semantic_nodes ?? []),
        ...(data.graph?.runtime_nodes ?? []),
        ...(data.graph?.assemblies ?? []),
      ] as GraphNode[],
    [data.graph],
  );
  const nodeLookup = useMemo(() => buildNodeLookup(unifiedNodes), [unifiedNodes]);
  const selectedAssembly = useMemo(
    () => data.graph?.assemblies?.find((assembly: any) => assembly.id === selectedAssemblyId) ?? null,
    [data.graph, selectedAssemblyId],
  );
  const selectedNode = useMemo(() => unifiedNodes.find((node) => node.id === selectedNodeId) ?? null, [selectedNodeId, unifiedNodes]);
  const baseGraph = useMemo(() => visibleGraphForMode(data.graph, graphMode), [data.graph, graphMode]);
  const selectedEdge = useMemo(() => baseGraph.edges.find((edge) => edge.id === selectedEdgeId) ?? null, [baseGraph.edges, selectedEdgeId]);
  const selectedTurn = useMemo(() => {
    const basinTurn = data.basin?.turns?.find((turn: any) => turn.turn_id === selectedTurnId);
    if (basinTurn) return basinTurn;
    return data.transcript?.turns?.[0] ?? null;
  }, [data.basin, data.transcript, selectedTurnId]);
  const highlightedNodeIds = useMemo(
    () => currentTurnNodeIds(data.graph, data.transcript, selectedTurn?.turn_id ?? null),
    [data.graph, data.transcript, selectedTurn],
  );
  const hum = data.transcript?.hum ?? data.overview?.hum ?? null;
  const layoutFamilies = useMemo(() => resolveLayoutFamilies(data.graph?.layout_families ?? null), [data.graph?.layout_families]);
  const layoutCatalog = useMemo(() => resolveLayoutCatalog(data.graph?.layout_catalog ?? null), [data.graph?.layout_catalog]);
  const layoutDefaults = useMemo(() => resolveLayoutDefaults(data.graph?.layout_defaults ?? null), [data.graph?.layout_defaults]);
  const selectedLayoutMeta = layoutCatalog[layoutTarget] ?? null;

  const filteredBaseline = useMemo(
    () => applyFilters(baseGraph.nodes, baseGraph.edges, filters, selectedNodeIds),
    [baseGraph.edges, baseGraph.nodes, filters, selectedNodeIds],
  );
  const modifiedGraph = useMemo(
    () => applyPreviewPatch(baseGraph.nodes, baseGraph.edges, (preview?.preview_graph_patch as any) ?? null),
    [baseGraph.edges, baseGraph.nodes, preview],
  );
  const filteredModified = useMemo(
    () => applyFilters(modifiedGraph.nodes, modifiedGraph.edges, filters, preview?.compare_selection?.modified_node_ids ?? selectedNodeIds),
    [filters, modifiedGraph.edges, modifiedGraph.nodes, preview, selectedNodeIds],
  );

  const baselineCoordinateMap = useMemo(() => buildCoordinateMap(filteredBaseline.nodes, coordinateMode, layoutSnapshots), [filteredBaseline.nodes, coordinateMode, layoutSnapshots]);
  const modifiedCoordinateMap = useMemo(() => buildCoordinateMap(filteredModified.nodes, coordinateMode, layoutSnapshots), [filteredModified.nodes, coordinateMode, layoutSnapshots]);
  const visibleGraphNodes = useMemo(() => cappedItems(filteredBaseline.nodes), [filteredBaseline.nodes]);
  const visibleGraphEdges = useMemo(() => cappedItems(filteredBaseline.edges), [filteredBaseline.edges]);
  const visibleBasinTurns = useMemo(() => cappedItems(data.basin?.turns ?? []), [data.basin]);
  const visibleAssemblies = useMemo(() => cappedItems(data.graph?.assemblies ?? []), [data.graph]);
  const latestTranscriptTurn = useMemo(() => {
    const turns = data.transcript?.turns ?? [];
    return turns.length ? turns[turns.length - 1] : null;
  }, [data.transcript]);

  const coordinateOptions = useMemo(() => {
    const options = new Set<string>();
    for (const key of Object.keys(data.graph?.view_modes ?? {})) options.add(key);
    if (layoutDefaults.coordinate_mode) options.add(String(layoutDefaults.coordinate_mode));
    if (!options.size) options.add("force");
    for (const entry of layoutSnapshots) options.add(entry.id);
    if (coordinateMode) options.add(coordinateMode);
    return [...options];
  }, [coordinateMode, data.graph?.view_modes, layoutDefaults.coordinate_mode, layoutSnapshots]);

  const canMutate = Boolean(data.liveEnabled && bootstrap.live_api?.preview && bootstrap.live_api?.commit);
  const interactionModes = (data.graph?.interaction_modes ?? ["INSPECT", "MEASURE", "EDIT", "ABLATE", "COMPARE"]) as InteractionMode[];
  const graphModes = (data.graph?.graph_modes ?? [DEFAULT_GRAPH_MODE]) as GraphMode[];
  const renderModes = (data.graph?.assembly_render_modes ?? [DEFAULT_ASSEMBLY_RENDER_MODE]) as AssemblyRenderMode[];

  useEffect(() => {
    layoutSettingsRef.current = layoutSettings;
  }, [layoutSettings]);

  useEffect(() => {
    if (typeof Worker === "undefined") return undefined;
    layoutWorkerRef.current = new Worker(new URL("./workers/layoutWorker.ts", import.meta.url), { type: "module" });
    statsWorkerRef.current = new Worker(new URL("./workers/statsWorker.ts", import.meta.url), { type: "module" });

    const layoutWorker = layoutWorkerRef.current;
    layoutWorker.onmessage = (event: MessageEvent<any>) => {
      const payload = event.data;
      if (payload.type === "progress") {
        setLayoutRunState((current) => ({
          ...current,
          running: true,
          progress: Number(payload.progress ?? 0),
          lastMessage: `${payload.phase ?? "layout"} ${(Number(payload.progress ?? 0) * 100).toFixed(0)}%`,
        }));
        return;
      }
      if (payload.type === "done") {
        const settingsHash = hashText(JSON.stringify(layoutSettingsRef.current[payload.layoutId] ?? {}));
        const snapshot: LayoutSnapshot = {
          id: `layout-run::${payload.layoutId}::${settingsHash}::${Date.now()}`,
          name: `${humanLayoutLabel(payload.layoutId, layoutCatalog)} run`,
          layoutId: payload.layoutId,
          settingsHash,
          coordinateMap: payload.coordinateMap as CoordinateMap,
          createdAt: nowStamp(),
        };
        setLayoutSnapshots((current) => dedupeSnapshots([...current.filter((entry) => entry.id !== snapshot.id), snapshot]));
        setCoordinateMode(snapshot.id);
        setLayoutRunState({
          running: false,
          paused: false,
          progress: 1,
          target: payload.layoutId,
          lastMessage: `${humanLayoutLabel(payload.layoutId, layoutCatalog)} ready`,
          activeRunId: null,
        });
        return;
      }
      if (payload.type === "cancelled") {
        setLayoutRunState((current) => ({
          ...current,
          running: false,
          paused: false,
          progress: current.progress,
          lastMessage: "Layout run cancelled",
          activeRunId: null,
        }));
        return;
      }
      if (payload.type === "error") {
        setLayoutRunState((current) => ({
          ...current,
          running: false,
          paused: false,
          lastMessage: payload.error,
          activeRunId: null,
        }));
      }
    };

    const statsWorker = statsWorkerRef.current;
    statsWorker.onmessage = (event: MessageEvent<any>) => {
      const payload = event.data;
      if (payload.type === "done") {
        setStats(payload as StatsPayload);
      } else if (payload.type === "error") {
        setStats({ error: payload.error });
      }
      setStatsPending(false);
    };

    return () => {
      layoutWorker.terminate();
      statsWorker.terminate();
      layoutWorkerRef.current = null;
      statsWorkerRef.current = null;
    };
  }, []);

  useEffect(() => {
    let nextGraphMode = DEFAULT_GRAPH_MODE;
    let nextAssemblyRenderMode = DEFAULT_ASSEMBLY_RENDER_MODE;
    let nextLiftMode = DEFAULT_LIFT_MODE;
    let nextInteractionMode = DEFAULT_INTERACTION_MODE;
    let nextCoordinateMode = layoutDefaults.coordinate_mode ?? "force";
    let nextFilters = defaultFilterState();
    let nextAppearance = defaultAppearanceState();
    try {
      const raw = window.localStorage.getItem(presetStorageKey);
      if (raw) {
        const preset = JSON.parse(raw) as Partial<{
          graphMode: GraphMode;
          assemblyRenderMode: AssemblyRenderMode;
          liftMode: LiftMode;
          interactionMode: InteractionMode;
          coordinateMode: string;
          filters: FilterState;
          appearance: AppearanceState;
        }>;
        nextGraphMode = preset.graphMode ?? nextGraphMode;
        nextAssemblyRenderMode = preset.assemblyRenderMode ?? nextAssemblyRenderMode;
        nextLiftMode = preset.liftMode ?? nextLiftMode;
        nextInteractionMode = preset.interactionMode ?? nextInteractionMode;
        nextCoordinateMode = preset.coordinateMode ?? nextCoordinateMode;
        nextFilters = { ...nextFilters, ...(preset.filters ?? {}) };
        nextAppearance = { ...nextAppearance, ...(preset.appearance ?? {}) };
      }
    } catch {
      // ignore corrupt presets
    }
    setGraphMode(nextGraphMode);
    setAssemblyRenderMode(nextAssemblyRenderMode);
    setLiftMode(nextLiftMode);
    setInteractionMode(nextInteractionMode);
    setCoordinateMode(nextCoordinateMode);
    setFilters(nextFilters);
    setAppearance(nextAppearance);
    setLoadedPresetKey(presetStorageKey);
  }, [layoutDefaults.coordinate_mode, presetStorageKey]);

  useEffect(() => {
    if (loadedPresetKey !== presetStorageKey) return;
    const payload = JSON.stringify({
      graphMode,
      assemblyRenderMode,
      liftMode,
      interactionMode,
      coordinateMode,
      filters,
      appearance,
    });
    window.localStorage.setItem(presetStorageKey, payload);
  }, [appearance, assemblyRenderMode, coordinateMode, filters, graphMode, interactionMode, liftMode, loadedPresetKey, presetStorageKey]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(snapshotsStorageKey);
      if (!raw) {
        setLayoutSnapshots([]);
        return;
      }
      const parsed = JSON.parse(raw) as LayoutSnapshot[];
      setLayoutSnapshots(Array.isArray(parsed) ? parsed : []);
    } catch {
      setLayoutSnapshots([]);
    }
  }, [snapshotsStorageKey]);

  useEffect(() => {
    window.localStorage.setItem(snapshotsStorageKey, JSON.stringify(layoutSnapshots));
  }, [layoutSnapshots, snapshotsStorageKey]);

  useEffect(() => {
    const defaultEntries = Object.entries(layoutDefaults).filter(
      ([key, value]) => !["coordinate_mode", "heavy_graph_node_cap"].includes(key) && value && typeof value === "object" && !Array.isArray(value),
    );
    if (!defaultEntries.length) return;
    setLayoutSettings((current) => {
      const next = { ...current };
      let changed = false;
      for (const [key, value] of defaultEntries) {
        if (next[key]) continue;
        next[key] = { ...(value as Record<string, any>) };
        changed = true;
      }
      return changed ? next : current;
    });
  }, [layoutDefaults]);

  useEffect(() => {
    if (!Object.keys(layoutCatalog).length) return;
    if (layoutCatalog[layoutTarget]) return;
    const firstRunnable = Object.values(layoutCatalog).find((meta) => meta.status === "runnable");
    if (firstRunnable) setLayoutTarget(firstRunnable.id);
  }, [layoutCatalog, layoutTarget]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      setPayloadStatuses(EMPTY_STATUS);
      try {
        const statusUrl = bootstrap.live_api?.status;
        let liveEnabled = false;
        let staleBuildWarning: string | null = null;
        if (statusUrl) {
          try {
            const statusPayload = await fetchJson<{ status?: { frontend_build?: { warning?: boolean; reason?: string } } }>(statusUrl);
            liveEnabled = true;
            if (statusPayload.status?.frontend_build?.warning) {
              staleBuildWarning = statusPayload.status.frontend_build.reason ?? "stale frontend build";
            }
          } catch {
            liveEnabled = false;
          }
        }

        const sources = liveEnabled
          ? {
              graph: withSessionScope(bootstrap.live_api?.graph, bootstrap.session_id),
              basin: withSessionScope(bootstrap.live_api?.basin, bootstrap.session_id),
              overview: withSessionScope(bootstrap.live_api?.overview, bootstrap.session_id),
              measurements: withSessionScope(bootstrap.live_api?.measurements, bootstrap.session_id),
              geometry: withSessionScope(bootstrap.live_api?.geometry, bootstrap.session_id),
              tanakh: withSessionScope(bootstrap.live_api?.tanakh, bootstrap.session_id),
              transcript: bootstrap.live_api?.session_turns,
              trace: bootstrap.live_api?.session_trace,
              runtimeStatus: bootstrap.live_api?.runtime_status,
              runtimeModel: bootstrap.live_api?.runtime_model,
            }
          : {
              graph: bootstrap.payload_urls?.graph,
              basin: bootstrap.payload_urls?.basin,
              overview: bootstrap.payload_urls?.overview,
              measurements: bootstrap.payload_urls?.measurements,
              geometry: bootstrap.payload_urls?.geometry,
              tanakh: bootstrap.payload_urls?.tanakh,
            };

        const nextSources: ResolvedSources = {
          ...sources,
          liveEnabled,
          staleBuildWarning,
        };
        if (!cancelled) {
          setResolvedSources(nextSources);
          setPayloadStatuses(initializePayloadStatuses(sources, liveEnabled));
          setData((current) => ({
            ...current,
            liveEnabled,
            staleBuildWarning,
          }));
        }

        const loadPayload = async <T,>(key: PayloadKey, url: string, assign: (payload: T) => void): Promise<void> => {
          if (cancelled) return;
          setPayloadStatuses((current) => ({
            ...current,
            [key]: { ...current[key], status: "loading", error: undefined },
          }));
          try {
            const payload = await fetchJson<T>(url);
            if (cancelled) return;
            startTransition(() => assign(payload));
            setPayloadStatuses((current) => ({
              ...current,
              [key]: { ...current[key], status: "ready" },
            }));
          } catch (payloadError) {
            if (cancelled) return;
            const message = payloadError instanceof Error ? payloadError.message : `Failed to load ${key}.`;
            setPayloadStatuses((current) => ({
              ...current,
              [key]: { ...current[key], status: "error", error: message },
            }));
          }
        };

        const essentialTasks: Array<Promise<void>> = [];
        if (nextSources.overview) {
          essentialTasks.push(loadPayload("overview", nextSources.overview, (payload) => setData((current) => ({ ...current, overview: payload as OverviewPayload }))));
        }
        if (nextSources.measurements) {
          essentialTasks.push(loadPayload("measurements", nextSources.measurements, (payload) => setData((current) => ({ ...current, measurements: payload as MeasurementsPayload }))));
        }
        if (nextSources.basin) {
          essentialTasks.push(
            loadPayload("basin", nextSources.basin, (payload) => {
              const basin = payload as BasinPayload;
              setData((current) => ({ ...current, basin }));
              if (!selectedTurnId && basin.turns?.length) {
                setSelectedTurnId(basin.turns[0].turn_id);
              }
            }),
          );
        }
        await Promise.allSettled(essentialTasks);
        if (!cancelled) setLoading(false);

        const backgroundTasks: Array<Promise<void>> = [];
        if (nextSources.graph) {
          backgroundTasks.push(
            loadPayload("graph", nextSources.graph, (payload) => {
              const graph = payload as GraphPayload;
              setData((current) => ({ ...current, graph }));
              if (!selectedAssemblyId && graph.assemblies?.length) {
                setSelectedAssemblyId(graph.assemblies[0].id);
              }
            }),
          );
        }
        if (nextSources.transcript) {
          backgroundTasks.push(loadPayload("transcript", nextSources.transcript, (payload) => setData((current) => ({ ...current, transcript: payload as TranscriptPayload }))));
        }
        if (nextSources.trace) {
          backgroundTasks.push(loadPayload("trace", nextSources.trace, (payload) => setData((current) => ({ ...current, trace: payload as SessionTracePayload }))));
        }
        if (nextSources.runtimeStatus) {
          backgroundTasks.push(loadPayload("runtimeStatus", nextSources.runtimeStatus, (payload) => setData((current) => ({ ...current, runtimeStatus: payload as Record<string, any> }))));
        }
        if (nextSources.runtimeModel) {
          backgroundTasks.push(loadPayload("runtimeModel", nextSources.runtimeModel, (payload) => setData((current) => ({ ...current, runtimeModel: payload as Record<string, any> }))));
        }
        void Promise.allSettled(backgroundTasks);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load observatory payloads.");
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [bootstrap]);

  useEffect(() => {
    if (!data.liveEnabled || !bootstrap.live_api?.events) return;
    const url = new URL(bootstrap.live_api.events, window.location.href);
    if (bootstrap.session_id) url.searchParams.set("session_id", bootstrap.session_id);
    const stream = new EventSource(url.toString());
    stream.addEventListener("observatory.invalidate", async () => {
      try {
        const [graph, basin, overview, measurements, transcript, trace, runtimeStatus, runtimeModel, tanakh] = await Promise.all([
          bootstrap.live_api?.graph ? fetchJson<GraphPayload>(withSessionScope(bootstrap.live_api.graph, bootstrap.session_id) ?? bootstrap.live_api.graph) : Promise.resolve(null),
          bootstrap.live_api?.basin ? fetchJson<BasinPayload>(withSessionScope(bootstrap.live_api.basin, bootstrap.session_id) ?? bootstrap.live_api.basin) : Promise.resolve(null),
          bootstrap.live_api?.overview ? fetchJson<OverviewPayload>(withSessionScope(bootstrap.live_api.overview, bootstrap.session_id) ?? bootstrap.live_api.overview) : Promise.resolve(null),
          bootstrap.live_api?.measurements
            ? fetchJson<MeasurementsPayload>(withSessionScope(bootstrap.live_api.measurements, bootstrap.session_id) ?? bootstrap.live_api.measurements)
            : Promise.resolve(null),
          bootstrap.live_api?.session_turns ? fetchJson<TranscriptPayload>(bootstrap.live_api.session_turns) : Promise.resolve(null),
          bootstrap.live_api?.session_trace ? fetchJson<SessionTracePayload>(bootstrap.live_api.session_trace) : Promise.resolve(null),
          bootstrap.live_api?.runtime_status ? fetchJson<Record<string, any>>(bootstrap.live_api.runtime_status) : Promise.resolve(null),
          bootstrap.live_api?.runtime_model ? fetchJson<Record<string, any>>(bootstrap.live_api.runtime_model) : Promise.resolve(null),
          bootstrap.live_api?.tanakh ? fetchJson<TanakhPayload>(withSessionScope(bootstrap.live_api.tanakh, bootstrap.session_id) ?? bootstrap.live_api.tanakh) : Promise.resolve(null),
        ]);
        setData((current) => ({
          ...current,
          graph,
          basin,
          overview,
          measurements,
          transcript,
          trace,
          runtimeStatus,
          runtimeModel,
          tanakh,
        }));
      } catch {
        // keep prior payloads if a live refresh fails
      }
    });
    return () => stream.close();
  }, [bootstrap.live_api, bootstrap.session_id, data.liveEnabled]);

  useEffect(() => {
    if (surface !== "geometry" || data.geometry || !resolvedSources?.geometry) return;
    let cancelled = false;
    setPayloadStatuses((current) => ({
      ...current,
      geometry: { ...current.geometry, status: "loading", source: resolvedSources.liveEnabled ? "live_api" : "static_export", error: undefined },
    }));
    void fetchJson<Record<string, any>>(resolvedSources.geometry)
      .then((geometry) => {
        if (cancelled) return;
        setData((current) => ({ ...current, geometry }));
        setPayloadStatuses((current) => ({
          ...current,
          geometry: { ...current.geometry, status: "ready" },
        }));
      })
      .catch((loadError) => {
        if (cancelled) return;
        const message = loadError instanceof Error ? loadError.message : "Failed to load geometry payload.";
        setPayloadStatuses((current) => ({
          ...current,
          geometry: { ...current.geometry, status: "error", error: message },
        }));
      });
    return () => {
      cancelled = true;
    };
  }, [data.geometry, resolvedSources, surface]);

  useEffect(() => {
    if (surface !== "tanakh" || data.tanakh || !resolvedSources?.tanakh) return;
    let cancelled = false;
    setPayloadStatuses((current) => ({
      ...current,
      tanakh: { ...current.tanakh, status: "loading", source: resolvedSources.liveEnabled ? "live_api" : "static_export", error: undefined },
    }));
    void fetchJson<TanakhPayload>(resolvedSources.tanakh)
      .then((tanakh) => {
        if (cancelled) return;
        setData((current) => ({ ...current, tanakh }));
        setPayloadStatuses((current) => ({
          ...current,
          tanakh: { ...current.tanakh, status: "ready" },
        }));
      })
      .catch((loadError) => {
        if (cancelled) return;
        const message = loadError instanceof Error ? loadError.message : "Failed to load Tanakh payload.";
        setPayloadStatuses((current) => ({
          ...current,
          tanakh: { ...current.tanakh, status: "error", error: message },
        }));
      });
    return () => {
      cancelled = true;
    };
  }, [data.tanakh, resolvedSources, surface]);

  function handleSelectNode(nodeId: string, additive: boolean) {
    setSelectedEdgeId(null);
    if (!nodeId) {
      setSelectedNodeIds([]);
      return;
    }
    setSelectedNodeIds((current) => {
      if (!additive) return [nodeId];
      return current.includes(nodeId) ? current.filter((item) => item !== nodeId) : [...current, nodeId];
    });
  }

  function handleClearSelection() {
    setSelectedNodeIds([]);
    setSelectedEdgeId(null);
  }

  function handleSelectAssembly(assemblyId: string) {
    setSelectedAssemblyId(assemblyId);
    setSelectedEdgeId(null);
    setSelectedNodeIds([]);
  }

  function handleSelectEdge(edgeId: string) {
    setSelectedEdgeId(edgeId);
    setSelectedNodeIds([]);
  }

  function handleSelectTurn(turnId: string) {
    setSelectedTurnId(turnId);
    setSelectedAssemblyId(null);
    setSelectedEdgeId(null);
    setSelectedNodeIds([]);
  }

  function handleFocusNode(nodeId: string) {
    setSelectedNodeIds([nodeId]);
    setSelectedEdgeId(null);
  }

  async function handleRunTanakh(request: any) {
    if (!bootstrap.live_api?.tanakh_run) return;
    setTanakhRunPending(true);
    setPayloadStatuses((current) => ({
      ...current,
      tanakh: { ...current.tanakh, status: "loading", source: "live_api", error: undefined },
    }));
    try {
      const response = await fetch(bootstrap.live_api.tanakh_run, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: bootstrap.session_id,
          ref: request.ref,
          params: request.params,
        }),
      });
      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText} for ${bootstrap.live_api.tanakh_run}`);
      }
      const tanakh = (await response.json()) as TanakhPayload;
      setData((current) => ({ ...current, tanakh }));
      setPayloadStatuses((current) => ({
        ...current,
        tanakh: { ...current.tanakh, status: "ready", source: "live_api" },
      }));
    } catch (runError) {
      const message = runError instanceof Error ? runError.message : "Failed to run Tanakh surface.";
      setPayloadStatuses((current) => ({
        ...current,
        tanakh: { ...current.tanakh, status: "error", source: "live_api", error: message },
      }));
    } finally {
      setTanakhRunPending(false);
    }
  }

  function updateFilter<K extends keyof FilterState>(key: K, value: FilterState[K]) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function updateAppearance<K extends keyof AppearanceState>(key: K, value: AppearanceState[K]) {
    setAppearance((current) => ({ ...current, [key]: value }));
  }

  function updateAction<K extends keyof ActionForm>(key: K, value: ActionForm[K]) {
    setActionForm((current) => ({ ...current, [key]: value }));
  }

  function updateLayoutSetting(layoutId: string, key: string, value: any) {
    setLayoutSettings((current) => ({
      ...current,
      [layoutId]: {
        ...(current[layoutId] ?? {}),
        [key]: value,
      },
    }));
  }

  async function refreshTrace() {
    if (!bootstrap.live_api?.session_trace) return;
    try {
      const trace = await fetchJson<SessionTracePayload>(bootstrap.live_api.session_trace);
      setData((current) => ({ ...current, trace }));
    } catch {
      // ignore trace refresh failures
    }
  }

  function buildActionPayload(): Record<string, any> {
    const currentActionType =
      interactionMode === "MEASURE"
        ? "geometry_measurement_run"
        : interactionMode === "ABLATE"
          ? "ablation_measurement_run"
          : interactionMode === "COMPARE"
            ? "geometry_measurement_run"
            : actionForm.editAction;
    const edgeSource = selectedEdge?.source ?? selectedNodeIds[0] ?? null;
    const edgeTarget = selectedEdge?.target ?? selectedNodeIds[1] ?? null;
    const clusterSignature =
      selectedNode?.cluster_signature ??
      selectedAssembly?.cluster_signature ??
      selectedTurn?.dominant_cluster_signature ??
      data.graph?.cluster_summaries?.[0]?.cluster_signature;
    return {
      action_type: currentActionType,
      selected_node_ids: selectedNodeIds,
      source_id: edgeSource,
      target_id: edgeTarget,
      current_edge_type: selectedEdge?.type ?? actionForm.edgeType,
      edge_type: actionForm.edgeType,
      weight: Number(actionForm.weight || 1),
      confidence: Number(actionForm.confidence || 0.7),
      operator_label: actionForm.operatorLabel.trim() || "local_operator",
      evidence_label: actionForm.evidenceLabel || "OPERATOR_ASSERTED",
      measurement_method: interactionMode === "ABLATE" ? "local_ablation_preview" : "local_geometry_preview",
      rationale: actionForm.rationale.trim(),
      label: actionForm.memodeLabel.trim(),
      summary: actionForm.memodeSummary.trim(),
      domain: actionForm.memodeDomain.trim() || "behavior",
      memode_id: actionForm.memodeId.trim(),
      member_ids: selectedNodeIds,
      mask_relation_type: actionForm.ablationRelation,
      target: clusterSignature ? { kind: "cluster", cluster_signature: clusterSignature } : undefined,
      cluster_signature: clusterSignature,
      source_graph_hash: data.graph?.source_graph_hash ?? "",
      algorithm_version: "browser-react-observatory-v1",
      manual_label: actionForm.manualLabel.trim(),
      manual_summary: actionForm.manualSummary.trim(),
      transfer_policy: actionForm.transferPolicy.trim(),
    };
  }

  async function handlePreview() {
    if (!bootstrap.live_api?.preview) {
      setPreview({ error: "Live API unavailable. Preview requires the local observatory server." });
      return;
    }
    setMutationPending(true);
    try {
      const response = await fetch(bootstrap.live_api.preview, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: bootstrap.session_id,
          action: buildActionPayload(),
        }),
      });
      const payload = (await response.json()) as PreviewPayload;
      if (!response.ok) {
        setPreview({ error: payload.error ?? `Preview failed with ${response.status}` });
        return;
      }
      setPreview(payload);
      if (graphMode !== "Compare") setGraphMode("Compare");
    } catch (previewError) {
      setPreview({ error: previewError instanceof Error ? previewError.message : "Preview failed." });
    } finally {
      setMutationPending(false);
    }
  }

  async function handleCommit() {
    if (!bootstrap.live_api?.commit) {
      setPreview({ error: "Live API unavailable. Commit requires the local observatory server." });
      return;
    }
    setMutationPending(true);
    try {
      const response = await fetch(bootstrap.live_api.commit, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: bootstrap.session_id,
          action: buildActionPayload(),
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        setPreview({ error: payload.error ?? `Commit failed with ${response.status}` });
        return;
      }
      setPreview(payload.preview ?? null);
      setData((current) => ({
        ...current,
        graph: payload.payload?.graph ?? current.graph,
        basin: payload.payload?.basin ?? current.basin,
        geometry: payload.payload?.geometry ?? current.geometry,
        measurements: payload.payload?.measurements ?? current.measurements,
        overview: payload.payload?.index ? { ...(current.overview ?? {}), index: payload.payload.index, measurements: payload.payload.measurements?.counts ?? current.overview?.measurements } : current.overview,
      }));
      await refreshTrace();
    } catch (commitError) {
      setPreview({ error: commitError instanceof Error ? commitError.message : "Commit failed." });
    } finally {
      setMutationPending(false);
    }
  }

  async function handleRevert(eventId: string) {
    if (!bootstrap.live_api?.revert) return;
    setMutationPending(true);
    try {
      const response = await fetch(bootstrap.live_api.revert, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: bootstrap.session_id,
          event_id: eventId,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        setPreview({ error: payload.error ?? `Revert failed with ${response.status}` });
        return;
      }
      setData((current) => ({
        ...current,
        graph: payload.payload?.graph ?? current.graph,
        basin: payload.payload?.basin ?? current.basin,
        geometry: payload.payload?.geometry ?? current.geometry,
        measurements: payload.payload?.measurements ?? current.measurements,
        overview: payload.payload?.index ? { ...(current.overview ?? {}), index: payload.payload.index, measurements: payload.payload.measurements?.counts ?? current.overview?.measurements } : current.overview,
      }));
      setPreview(null);
      await refreshTrace();
    } catch (revertError) {
      setPreview({ error: revertError instanceof Error ? revertError.message : "Revert failed." });
    } finally {
      setMutationPending(false);
    }
  }

  function handleRunLayout() {
    if (!layoutWorkerRef.current || !data.graph) return;
    if (!isRunnableLayout(layoutTarget, layoutCatalog)) {
      setLayoutRunState({
        running: false,
        paused: false,
        progress: 0,
        target: layoutTarget,
        lastMessage: `${humanLayoutLabel(layoutTarget, layoutCatalog)} is a reference terrain item. Read its usage notes; the browser worker does not execute it yet.`,
        activeRunId: null,
      });
      return;
    }
    const heavyCap = Number(layoutDefaults.heavy_graph_node_cap ?? data.graph?.statistics_capabilities?.heavy_graph_node_cap ?? 320);
    if (filteredBaseline.nodes.length > heavyCap) {
      setLayoutRunState({
        running: false,
        paused: false,
        progress: 0,
        target: layoutTarget,
        lastMessage: `Layout skipped above heavy cap (${heavyCap} nodes). Exported coordinates remain authoritative.`,
        activeRunId: null,
      });
      return;
    }
    const runId = `layout-${Date.now()}`;
    setLayoutRunState({
      running: true,
      paused: false,
      progress: 0,
      target: layoutTarget,
      lastMessage: `Running ${humanLayoutLabel(layoutTarget, layoutCatalog)}`,
      activeRunId: runId,
    });
    layoutWorkerRef.current.postMessage({
      type: "run",
      runId,
      layoutId: layoutTarget,
      nodes: filteredBaseline.nodes.map((node) => ({
        id: node.id,
        degree: node.degree,
        size: node.degree,
        clusterKey: String(node.cluster_signature ?? node.cluster_label ?? node.domain ?? node.kind ?? "unclustered"),
        latitude: Number(node.latitude ?? node.lat ?? node.geo_latitude ?? node.geo?.lat ?? Number.NaN),
        longitude: Number(node.longitude ?? node.lng ?? node.lon ?? node.geo_longitude ?? node.geo?.lng ?? Number.NaN),
      })),
      edges: filteredBaseline.edges.map((edge) => ({ id: edge.id || edgeKey(edge), source: edge.source, target: edge.target, weight: edge.weight })),
      initialPositions: baselineCoordinateMap,
      settings: layoutSettings[layoutTarget] ?? {},
      selectedNodeIds,
    });
  }

  function handlePauseResumeLayout() {
    const runId = layoutRunState.activeRunId;
    if (!layoutWorkerRef.current || !runId) return;
    const nextPaused = !layoutRunState.paused;
    layoutWorkerRef.current.postMessage({ type: nextPaused ? "pause" : "resume", runId });
    setLayoutRunState((current) => ({
      ...current,
      paused: nextPaused,
      lastMessage: nextPaused ? "Layout paused" : "Layout resumed",
    }));
  }

  function handleCancelLayout() {
    const runId = layoutRunState.activeRunId;
    if (!layoutWorkerRef.current || !runId) return;
    layoutWorkerRef.current.postMessage({ type: "cancel", runId });
  }

  function handleResetLayout() {
    setCoordinateMode(layoutDefaults.coordinate_mode ?? "force");
    setLayoutRunState((current) => ({
      ...current,
      lastMessage: "Reset to exported coordinate mode",
    }));
  }

  function handleSaveLayoutSnapshot() {
    const existing = layoutSnapshots.find((snapshot) => snapshot.id === coordinateMode);
    if (!existing) {
      setLayoutRunState((current) => ({
        ...current,
        lastMessage: "No browser-local layout snapshot selected to save.",
      }));
      return;
    }
    const next = {
      ...existing,
      id: `layout-snapshot::${existing.layoutId}::${existing.settingsHash}::${Date.now()}`,
      name: `${humanLayoutLabel(existing.layoutId, layoutCatalog)} snapshot ${layoutSnapshots.filter((entry) => entry.layoutId === existing.layoutId).length + 1}`,
      createdAt: nowStamp(),
    };
    setLayoutSnapshots((current) => dedupeSnapshots([...current, next]));
    setCoordinateMode(next.id);
    setLayoutRunState((current) => ({
      ...current,
      lastMessage: `${next.name} saved locally`,
    }));
  }

  function handleComputeStats() {
    if (!statsWorkerRef.current) return;
    setStatsPending(true);
    setStats(null);
    statsWorkerRef.current.postMessage({
      type: "run",
      nodes: filteredBaseline.nodes,
      edges: filteredBaseline.edges,
    });
  }

  function handleExport(format: string) {
    if (!data.graph) return;
    if (format === "nodes_csv") {
      downloadText("eden-nodes.csv", csvForNodes(filteredBaseline.nodes), "text/csv");
    } else if (format === "edges_csv") {
      downloadText("eden-edges.csv", csvForEdges(filteredBaseline.edges), "text/csv");
    } else if (format === "selection_json") {
      downloadText("eden-selection.json", jsonForSelection(filteredBaseline.nodes, filteredBaseline.edges, selectedNodeIds), "application/json");
    } else if (format === "graphml") {
      downloadText("eden-graph.graphml", graphMLForGraph(filteredBaseline.nodes, filteredBaseline.edges), "application/xml");
    } else if (format === "gexf") {
      downloadText("eden-graph.gexf", gexfForGraph(filteredBaseline.nodes, filteredBaseline.edges), "application/xml");
    }
    setLastExportMessage(`Exported ${format}`);
  }

  function renderOverview() {
    const graphCounts = data.overview?.graph_counts ?? data.graph?.counts ?? {};
    const measurementCounts = data.measurements?.counts ?? {};
    return (
      <div className="overview-grid">
        <Card title="Identity">
          <MetricList
            items={[
              ["Experiment", bootstrap.experiment_id],
              ["Session", bootstrap.session_id],
              ["Mode", data.liveEnabled ? "Live API" : "Static export"],
              ["Render", "Layout/render != evidence"],
            ]}
          />
        </Card>
        <Card title="Graph">
          <MetricList
            items={[
              ["Payload", payloadStatuses.graph.status],
              ["Source", sourceLabel(payloadStatuses.graph.source)],
              ["Assemblies", data.graph?.assemblies?.length],
              ["Clusters", data.graph?.cluster_summaries?.length],
              ...Object.entries(graphCounts),
            ]}
          />
        </Card>
        <Card title="Workbench">
          <MetricList
            items={[
              ["Interaction mode", interactionMode],
              ["Coordinate mode", coordinateModeLabel(coordinateMode, layoutSnapshots, layoutCatalog)],
              ["Layout target", humanLayoutLabel(layoutTarget, layoutCatalog)],
              ["Local snapshots", layoutSnapshots.length],
            ]}
          />
        </Card>
        <Card title="Basin">
          <MetricList
            items={[
              ["Payload", payloadStatuses.basin.status],
              ["Projection", data.basin?.projection_method ?? bootstrap.projection_method],
              ["Filtered turns", data.basin?.filtered_turn_count],
              ["Source turns", data.basin?.source_turn_count],
              ["Derived", "SVD projection + lift mode"],
            ]}
          />
        </Card>
        <Card title="Measurements">
          <MetricList items={[["Payload", payloadStatuses.measurements.status], ...Object.entries(measurementCounts)]} />
        </Card>
        <Card title="Runtime Trace">
          <MetricList
            items={[
              ["Payload", payloadStatuses.trace.status],
              ["Latest turn", data.trace?.latest_turn_id],
              ["Trace events", data.trace?.trace_events?.length],
              ["Membrane events", data.trace?.membrane_events?.length],
            ]}
          />
        </Card>
        <Card title="Tanakh">
          <MetricList
            items={[
              ["Payload", payloadStatuses.tanakh.status],
              ["Ref", data.tanakh?.current_ref ?? data.overview?.tanakh?.current_ref],
              ["Bundle", data.tanakh?.bundle_hash ?? data.overview?.tanakh?.bundle_hash],
              ["Mode", data.liveEnabled ? "Live/API + static sidecars" : "Static sidecars"],
            ]}
          />
        </Card>
        <Card title="Hum">
          <MetricList
            items={[
              ["Present", hum?.present ? "yes" : "no"],
              ["Generated", hum?.generated_at],
              ["Window", hum?.turn_window_size],
              ["Recurrence", hum?.cross_turn_recurrence_present ? "yes" : "seed-state / no"],
            ]}
          />
        </Card>
      </div>
    );
  }

  function renderPayloadStatus() {
    const entries = PAYLOAD_ORDER.filter((key) => payloadStatuses[key].source !== "none").map((key) => [key, payloadStatuses[key]] as const);
    if (!entries.length) return null;
    const activeLoads = entries.filter(([, item]) => item.status === "loading").length;
    const deferredLoads = entries.filter(([, item]) => item.status === "deferred").length;
    return (
      <section className="status-panel">
        <div className="status-panel-copy">
          <strong>{loading ? "Loading observatory payloads" : activeLoads ? "Background payload activity" : "Payload status"}</strong>
          <span>
            {data.liveEnabled
              ? "Live mode prefers API payloads and refresh invalidations."
              : "Static export mode reads adjacent JSON artifacts; layout and mutation controls remain visible but non-authoritative."}
          </span>
          <span>
            {activeLoads
              ? `${activeLoads} payload${activeLoads === 1 ? "" : "s"} still loading.`
              : deferredLoads
                ? `${deferredLoads} payload${deferredLoads === 1 ? "" : "s"} deferred until needed.`
                : "All requested payloads are ready."}
          </span>
        </div>
        <div className="payload-grid">
          {entries.map(([key, item]) => (
            <div key={key} className="payload-card">
              <div className="payload-card-header">
                <strong>{item.label}</strong>
                <span className={payloadStatusClass(item.status)}>{item.status}</span>
              </div>
              <p>{item.detail}</p>
              <small>{sourceLabel(item.source)}</small>
              {item.error ? <small className="payload-error">{item.error}</small> : null}
            </div>
          ))}
        </div>
      </section>
    );
  }

  function renderContinuityStrip() {
    const visibleReasoning = latestTranscriptTurn?.reasoning_text ?? "";
    const humSurface = hum?.text_surface ?? "";
    const steps = chainLikeSteps(reasoningLens === "hum_live" ? humSurface : visibleReasoning);
    const reasoningBody =
      reasoningLens === "reasoning"
        ? excerptText(visibleReasoning, 720)
        : reasoningLens === "hum_live"
          ? excerptText(humSurface, 720)
          : "";
    return (
      <section className="continuity-strip">
        <article className="continuity-card">
          <header>
            <p className="eyebrow">Hum</p>
            <h2>Bounded continuity fact</h2>
          </header>
          <div className="continuity-meta">
            <span>present={hum?.present ? "yes" : "no"}</span>
            <span>generated={hum?.generated_at ?? "n/a"}</span>
            <span>window={hum?.turn_window_size ?? 0}</span>
            <span>recurrence={hum?.cross_turn_recurrence_present ? "yes" : "seed-state / no"}</span>
          </div>
          <p className="reasoning-copy">
            {hum?.present
              ? excerptText(humSurface, 360) || "Hum present but the bounded text surface is empty."
              : "No bounded hum artifact is present yet for this session."}
          </p>
        </article>
        <article className="continuity-card">
          <header>
            <p className="eyebrow">Reasoning</p>
            <h2>Operator-visible reasoning lens</h2>
          </header>
          <div className="toolbar">
            <div aria-label="Reasoning lens" className="toolbar-group" role="radiogroup">
              {([
                ["reasoning", "Reasoning"],
                ["chain_like", "Chain-Like"],
                ["hum_live", "Hum Live"],
              ] as Array<[ReasoningLens, string]>).map(([mode, label]) => (
                <button
                  aria-checked={mode === reasoningLens}
                  key={mode}
                  className={mode === reasoningLens ? "toolbar-button is-active" : "toolbar-button"}
                  onClick={() => setReasoningLens(mode)}
                  role="radio"
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <p className="continuity-note">
            {reasoningLens === "hum_live"
              ? "Hum-live mode reformats the bounded hum artifact as chain-like continuity beats. It is not hidden chain-of-thought."
              : "This lens only renders operator-visible reasoning artifacts. Hidden chain-of-thought remains out of scope."}
          </p>
          {reasoningLens === "chain_like" || reasoningLens === "hum_live" ? (
            steps.length ? (
              <ol className="reasoning-steps">
                {steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            ) : (
              <p className="reasoning-copy">
                {reasoningLens === "hum_live"
                  ? "Hum-live steps appear after the bounded hum artifact has been generated."
                  : "No operator-visible reasoning artifact is loaded yet from the live session transcript."}
              </p>
            )
          ) : (
            <p className="reasoning-copy">{reasoningBody || "No operator-visible reasoning artifact is loaded yet from the live session transcript."}</p>
          )}
        </article>
      </section>
    );
  }

  function renderFilterRail() {
    if (!data.graph) return null;
    const filterSource = data.graph.filters ?? {};
    return (
      <Card title="Left Rail Filters" accent="browser-local">
        <div className="form-grid">
          <label>
            <span>Search</span>
            <input aria-label="Graph search" value={filters.search} onChange={(event) => updateFilter("search", event.target.value)} placeholder="label / summary / provenance" />
          </label>
          <label>
            <span>Session</span>
            <select aria-label="Session filter" value={filters.session} onChange={(event) => updateFilter("session", event.target.value)}>
              <option value="">all sessions</option>
              {(filterSource.sessions ?? []).map((value: string) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Kind</span>
            <select aria-label="Kind filter" value={filters.kind} onChange={(event) => updateFilter("kind", event.target.value)}>
              <option value="">all kinds</option>
              {(filterSource.kinds ?? []).map((value: string) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Domain</span>
            <select aria-label="Domain filter" value={filters.domain} onChange={(event) => updateFilter("domain", event.target.value)}>
              <option value="">all domains</option>
              {(filterSource.domains ?? []).map((value: string) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Source</span>
            <select aria-label="Source filter" value={filters.source} onChange={(event) => updateFilter("source", event.target.value)}>
              <option value="">all sources</option>
              {(filterSource.sources ?? []).map((value: string) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Verdict</span>
            <select aria-label="Verdict filter" value={filters.verdict} onChange={(event) => updateFilter("verdict", event.target.value)}>
              <option value="">all verdicts</option>
              {(filterSource.verdicts ?? []).map((value: string) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Evidence</span>
            <select aria-label="Evidence label filter" value={filters.evidence} onChange={(event) => updateFilter("evidence", event.target.value)}>
              <option value="">all evidence</option>
              {(filterSource.evidence_labels ?? []).map((value: string) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Created at contains</span>
            <input aria-label="Created at filter" value={filters.createdAt} onChange={(event) => updateFilter("createdAt", event.target.value)} placeholder="2026-03-10" />
          </label>
          <label>
            <span>Min degree</span>
            <input aria-label="Minimum degree" type="number" value={filters.degreeMin} onChange={(event) => updateFilter("degreeMin", Number(event.target.value || 0))} />
          </label>
          <label>
            <span>Min edge weight</span>
            <input aria-label="Minimum edge weight" type="number" step="0.1" value={filters.weightMin} onChange={(event) => updateFilter("weightMin", Number(event.target.value || 0))} />
          </label>
          <label>
            <span>Component mode</span>
            <select aria-label="Component mode" value={filters.componentMode} onChange={(event) => updateFilter("componentMode", event.target.value as FilterState["componentMode"])}>
              <option value="all">all</option>
              <option value="largest">largest</option>
              <option value="selection">selection</option>
            </select>
          </label>
          <label>
            <span>Ego radius</span>
            <input aria-label="Ego radius" type="number" min="0" max="4" value={filters.egoRadius} onChange={(event) => updateFilter("egoRadius", Number(event.target.value || 0))} />
          </label>
          <label className="toggle-line">
            <input aria-label="Hide isolated" checked={filters.hideIsolated} onChange={(event) => updateFilter("hideIsolated", event.target.checked)} type="checkbox" />
            <span>Hide isolated</span>
          </label>
        </div>
      </Card>
    );
  }

  function renderDataLab() {
    if (!data.graph) return null;
    return (
      <Card title="Data Lab" accent={lastExportMessage || "selection + export"}>
        <div className="toolbar toolbar-sticky">
          {(data.graph.export_formats ?? ["gexf", "graphml", "nodes_csv", "edges_csv", "selection_json"]).map((format: string) => (
            <button key={format} className="toolbar-button" onClick={() => handleExport(format)} type="button">
              {humanExportLabel(format)}
            </button>
          ))}
        </div>
        <div className="metric-callout">
          <strong>Visible graph</strong>
          <span>{filteredBaseline.nodes.length} nodes · {filteredBaseline.edges.length} edges</span>
        </div>
        {visibleGraphNodes.capped ? (
          <p className="placeholder-copy">Showing first {TEXT_ACCESS_LIMIT} of {visibleGraphNodes.total} graph entities. This browser list is capped and not exhaustive.</p>
        ) : null}
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Node</th>
                <th>Kind</th>
                <th>Degree</th>
                <th>Select</th>
              </tr>
            </thead>
            <tbody>
              {visibleGraphNodes.items.map((node) => (
                <tr key={node.id}>
                  <td>{nodeLabel(node)}</td>
                  <td>{node.kind}</td>
                  <td>{node.degree ?? 0}</td>
                  <td>
                    <button className="table-button" onClick={() => handleFocusNode(node.id)} type="button">
                      Focus
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {visibleGraphEdges.capped ? (
          <p className="placeholder-copy">Showing first {TEXT_ACCESS_LIMIT} of {visibleGraphEdges.total} relations. This browser list is capped and not exhaustive.</p>
        ) : null}
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Relation</th>
                <th>Weight</th>
                <th>Edit</th>
              </tr>
            </thead>
            <tbody>
              {visibleGraphEdges.items.map((edge) => (
                <tr key={edge.id}>
                  <td>{edgeLabel(edge, nodeLookup)}</td>
                  <td>{Number(edge.weight ?? 1).toFixed(2)}</td>
                  <td>
                    <button
                      className="table-button"
                      onClick={() => {
                        handleSelectEdge(edge.id);
                        setInteractionMode("EDIT");
                        updateAction("editAction", "edge_update");
                        updateAction("edgeType", String(edge.type ?? ""));
                        updateAction("weight", Number(edge.weight ?? 1));
                      }}
                      type="button"
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    );
  }

  function renderSidebar() {
    return (
      <aside className="sidebar">
        {surface === "graph" ? renderFilterRail() : null}
        {surface === "graph" ? renderDataLab() : null}
        <Card title="Assemblies">
          {data.graph ? (
            <>
              {visibleAssemblies.capped ? (
                <p className="placeholder-copy">Showing first {TEXT_ACCESS_LIMIT} of {visibleAssemblies.total} assemblies. This browser list is capped and not exhaustive.</p>
              ) : null}
              <div className="chip-list">
                {visibleAssemblies.items.map((assembly: any) => (
                  <button
                    aria-label={`Assembly ${assembly.label}`}
                    key={assembly.id}
                    className={assembly.id === selectedAssemblyId ? "chip is-active" : "chip"}
                    data-state={assembly.id === selectedAssemblyId ? "active" : "inactive"}
                    onClick={() => handleSelectAssembly(assembly.id)}
                    type="button"
                  >
                    {assembly.label}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <p className="placeholder-copy">Graph payload {payloadStatuses.graph.status}. Assemblies appear after the semantic graph bundle arrives.</p>
          )}
        </Card>
        <Card title="Graph Entities">
          {data.graph ? (
            <div className="chip-list">
              {visibleGraphNodes.items.map((node) => (
                <button
                  aria-label={`Graph entity ${nodeLabel(node)}`}
                  key={node.id}
                  className={node.id === selectedNodeId ? "chip is-active" : "chip"}
                  data-state={node.id === selectedNodeId ? "active" : "inactive"}
                  onClick={() => handleFocusNode(node.id)}
                  type="button"
                >
                  {nodeLabel(node)}
                </button>
              ))}
            </div>
          ) : (
            <p className="placeholder-copy">Graph payload {payloadStatuses.graph.status}. Text selection becomes available once the graph bundle is ready.</p>
          )}
        </Card>
        <Card title="Relations">
          {data.graph ? (
            <div className="transcript-list">
              {visibleGraphEdges.items.map((edge) => (
                <button
                  aria-label={`Graph relation ${edgeLabel(edge, nodeLookup)}`}
                  key={edge.id}
                  className={edge.id === selectedEdgeId ? "transcript-turn is-active" : "transcript-turn"}
                  data-state={edge.id === selectedEdgeId ? "active" : "inactive"}
                  onClick={() => handleSelectEdge(edge.id)}
                  type="button"
                >
                  <span>{edge.type}</span>
                  <span>{edgeLabel(edge, nodeLookup)}</span>
                </button>
              ))}
            </div>
          ) : (
            <p className="placeholder-copy">Relations stay unavailable until the graph payload is ready.</p>
          )}
        </Card>
        <Card title="Semantic Clusters">
          {data.graph ? (
            <div className="chip-list">
              {(data.graph.cluster_summaries ?? []).slice(0, 12).map((cluster: any) => (
                <div key={cluster.cluster_signature} className="cluster-pill">
                  <strong>{cluster.display_label}</strong>
                  <span>{cluster.member_meme_ids?.length ?? 0} memes</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="placeholder-copy">Cluster summaries depend on the graph payload and are loaded separately from the overview.</p>
          )}
        </Card>
        <Card title="Basin Turns">
          {data.basin?.turns?.length ? (
            <>
              {visibleBasinTurns.capped ? (
                <p className="placeholder-copy">Showing first {TEXT_ACCESS_LIMIT} of {visibleBasinTurns.total} basin turns. This browser list is capped and not exhaustive.</p>
              ) : null}
              <div className="transcript-list">
                {visibleBasinTurns.items.map((turn: any) => (
                  <button
                    aria-label={`Basin turn T${turn.turn_index ?? "?"} ${turn.turn_id} ${turn.display_attractor_label ?? turn.dominant_label ?? turn.turn_id}`}
                    key={turn.turn_id}
                    className={turn.turn_id === selectedTurn?.turn_id ? "transcript-turn is-active" : "transcript-turn"}
                    data-state={turn.turn_id === selectedTurn?.turn_id ? "active" : "inactive"}
                    onClick={() => handleSelectTurn(turn.turn_id)}
                    type="button"
                  >
                    <span>T{turn.turn_index ?? "?"}</span>
                    <span>{turn.display_attractor_label ?? turn.dominant_label ?? turn.turn_id}</span>
                  </button>
                ))}
              </div>
            </>
          ) : (
            <p className="placeholder-copy">Basin turns become selectable when filtered trajectory data is available.</p>
          )}
        </Card>
        <Card title="Transcript">
          {data.transcript ? (
            <div className="transcript-list">
              {(data.transcript.turns ?? []).slice(0, 10).map((turn: any) => (
                <button
                  aria-label={`Transcript turn T${turn.turn_index} ${turn.turn_id}`}
                  key={turn.turn_id}
                  className={turn.turn_id === selectedTurn?.turn_id ? "transcript-turn is-active" : "transcript-turn"}
                  data-state={turn.turn_id === selectedTurn?.turn_id ? "active" : "inactive"}
                  onClick={() => handleSelectTurn(turn.turn_id)}
                  type="button"
                >
                  <span>T{turn.turn_index}</span>
                  <span>{turn.user_text}</span>
                </button>
              ))}
            </div>
          ) : (
            <p className="placeholder-copy">{data.liveEnabled ? `Transcript payload ${payloadStatuses.transcript.status}.` : "Transcript is only available from the live API in v1."}</p>
          )}
        </Card>
      </aside>
    );
  }

  function renderGraphControls() {
    return (
      <div className="workbench-grid">
        <Card title="Graph Mode" accent={graphMode}>
          <div aria-label="Graph mode" className="toolbar-group" role="radiogroup">
            {graphModes.map((mode) => (
              <button
                aria-checked={mode === graphMode}
                key={mode}
                className={mode === graphMode ? "toolbar-button is-active" : "toolbar-button"}
                onClick={() => setGraphMode(mode)}
                role="radio"
                type="button"
              >
                {mode}
              </button>
            ))}
          </div>
          <div aria-label="Interaction mode" className="toolbar-group" role="radiogroup">
            {interactionModes.map((mode) => (
              <button
                aria-checked={mode === interactionMode}
                key={mode}
                className={mode === interactionMode ? "toolbar-button is-active" : "toolbar-button"}
                onClick={() => setInteractionMode(mode)}
                role="radio"
                type="button"
              >
                {mode}
              </button>
            ))}
          </div>
          <div className="toolbar-group">
            <button className="primary-button" disabled={!canMutate || mutationPending} onClick={() => void handlePreview()} type="button">
              Preview
            </button>
            <button className="primary-button" disabled={!canMutate || mutationPending} onClick={() => void handleCommit()} type="button">
              Commit
            </button>
            <button className="toolbar-button" onClick={handleClearSelection} type="button">
              Clear Selection
            </button>
          </div>
          {!canMutate ? <p className="placeholder-copy">Static export mode keeps preview / commit / revert visible but disabled. Mutation remains live-only.</p> : null}
        </Card>

        <Card title="Coordinate Mode" accent={coordinateModeLabel(coordinateMode, layoutSnapshots, layoutCatalog)}>
          <div aria-label="Coordinate mode" className="toolbar-group" role="radiogroup">
            {coordinateOptions.map((modeId) => (
              <button
                aria-checked={modeId === coordinateMode}
                key={modeId}
                className={modeId === coordinateMode ? "toolbar-button is-active" : "toolbar-button"}
                onClick={() => setCoordinateMode(modeId)}
                role="radio"
                type="button"
              >
                {coordinateModeLabel(modeId, layoutSnapshots, layoutCatalog)}
              </button>
            ))}
          </div>
          <div aria-label="Assembly render mode" className="toolbar-group" role="radiogroup">
            {renderModes.map((mode) => (
              <button
                aria-checked={mode === assemblyRenderMode}
                key={mode}
                className={mode === assemblyRenderMode ? "toolbar-button is-active" : "toolbar-button"}
                onClick={() => setAssemblyRenderMode(mode)}
                role="radio"
                type="button"
              >
                {mode}
              </button>
            ))}
          </div>
        </Card>

        <Card title="Appearance" accent="browser-local">
          <div className="form-grid">
            <label>
              <span>Node color</span>
              <select aria-label="Node color by" value={appearance.nodeColorBy} onChange={(event) => updateAppearance("nodeColorBy", event.target.value)}>
                {(data.graph?.appearance_dimensions?.node_color ?? ["kind", "domain", "cluster", "evidence_label"]).map((value: string) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Node size</span>
              <select aria-label="Node size by" value={appearance.nodeSizeBy} onChange={(event) => updateAppearance("nodeSizeBy", event.target.value)}>
                {(data.graph?.appearance_dimensions?.node_size ?? ["uniform", "degree"]).map((value: string) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Edge color</span>
              <select aria-label="Edge color by" value={appearance.edgeColorBy} onChange={(event) => updateAppearance("edgeColorBy", event.target.value)}>
                {(data.graph?.appearance_dimensions?.edge_color ?? ["type", "evidence_label"]).map((value: string) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Edge opacity</span>
              <select aria-label="Edge opacity by" value={appearance.edgeOpacityBy} onChange={(event) => updateAppearance("edgeOpacityBy", event.target.value)}>
                {(data.graph?.appearance_dimensions?.edge_opacity ?? ["weight"]).map((value: string) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Label mode</span>
              <select aria-label="Label mode" value={appearance.labelMode} onChange={(event) => updateAppearance("labelMode", event.target.value as AppearanceState["labelMode"])}>
                {(data.graph?.appearance_dimensions?.label_modes ?? ["selection", "all", "none"]).map((value: string) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <label className="toggle-line">
              <input aria-label="Show edge labels" checked={appearance.showEdgeLabels} onChange={(event) => updateAppearance("showEdgeLabels", event.target.checked)} type="checkbox" />
              <span>Show edge labels</span>
            </label>
          </div>
        </Card>
      </div>
    );
  }

  function renderLayoutWorkbench() {
    if (!data.graph) return null;
    const settings = layoutSettings[layoutTarget] ?? {};
    const selectedFamily = layoutFamilies.find((family) => family.id === selectedLayoutMeta?.familyId) ?? null;
    return (
      <Card title="Layout Workbench" accent={layoutRunState.lastMessage || humanLayoutLabel(layoutTarget, layoutCatalog)}>
        <div className="layout-terrain">
          {layoutFamilies.map((family) => {
            const subgroupMap = new Map<string, LayoutAlgorithmMeta[]>();
            Object.values(layoutCatalog)
              .filter((meta) => meta.familyId === family.id && meta.kind !== "exported_coordinate")
              .forEach((meta) => {
                const subgroup = meta.subgroupLabel ?? "Algorithms";
                const bucket = subgroupMap.get(subgroup) ?? [];
                bucket.push(meta);
                subgroupMap.set(subgroup, bucket);
              });
            if (!subgroupMap.size) return null;
            return (
              <section className="layout-family-card" key={family.id}>
                <header>
                  <h3>{family.label}</h3>
                  <p>{family.description}</p>
                </header>
                <div className="chip-list">
                  {family.bestFor.map((item) => (
                    <span className="badge badge-derived" key={item}>
                      {item}
                    </span>
                  ))}
                </div>
                {[...subgroupMap.entries()].map(([subgroup, entries]) => (
                  <div className="layout-subgroup" key={`${family.id}-${subgroup}`}>
                    <h4>{subgroup}</h4>
                    <div className="layout-algorithm-grid">
                      {entries.map((meta) => (
                        <button
                          aria-pressed={meta.id === layoutTarget}
                          className={meta.id === layoutTarget ? "layout-algorithm-button is-active" : "layout-algorithm-button"}
                          key={meta.id}
                          onClick={() => setLayoutTarget(meta.id)}
                          type="button"
                        >
                          <strong>{meta.label}</strong>
                          <span>{meta.status === "runnable" ? "Runnable" : "Reference"}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </section>
            );
          })}
        </div>
        <div className="layout-detail-card">
          <div className="layout-detail-header">
            <div>
              <p className="eyebrow">Selected Algorithm</p>
              <h3>{humanLayoutLabel(layoutTarget, layoutCatalog)}</h3>
            </div>
            <span className={badgeClass(selectedLayoutMeta?.status === "runnable" ? "observed" : "derived")}>
              {selectedLayoutMeta?.status === "runnable" ? "Runnable in browser worker" : "Reference / explanatory only"}
            </span>
          </div>
          <p className="placeholder-copy">{selectedLayoutMeta?.summary ?? "Select a layout terrain item to see how it is used."}</p>
          <p className="placeholder-copy">{selectedLayoutMeta?.usedFor ?? "Layout explanations stay browser-local and do not alter graph evidence."}</p>
          {selectedFamily ? (
            <p className="placeholder-copy">
              Family: <strong>{selectedFamily.label}</strong>
            </p>
          ) : null}
          <div className="chip-list">
            {(selectedLayoutMeta?.bestFor ?? []).map((item) => (
              <span className="badge" key={item}>
                {item}
              </span>
            ))}
          </div>
        </div>
        {selectedLayoutMeta?.status === "runnable" ? <div className="form-grid">{renderLayoutSettingsFields(selectedLayoutMeta, settings, updateLayoutSetting)}</div> : null}
        {selectedLayoutMeta?.status !== "runnable" ? (
          <p className="placeholder-copy">This terrain item is shown so operators can browse the wider layout landscape. Running it would require a dedicated implementation beyond the current browser worker.</p>
        ) : null}
        <div className="toolbar">
          <button className="primary-button" disabled={layoutRunState.running || selectedLayoutMeta?.status !== "runnable"} onClick={handleRunLayout} type="button">
            Run Layout
          </button>
          <button className="toolbar-button" disabled={!layoutRunState.running} onClick={handlePauseResumeLayout} type="button">
            {layoutRunState.paused ? "Resume" : "Pause"}
          </button>
          <button className="toolbar-button" disabled={!layoutRunState.running} onClick={handleCancelLayout} type="button">
            Cancel
          </button>
          <button className="toolbar-button" onClick={handleResetLayout} type="button">
            Reset
          </button>
          <button className="toolbar-button" onClick={handleSaveLayoutSnapshot} type="button">
            Save Local Snapshot
          </button>
        </div>
        <div className="progress-row">
          <span>{layoutRunState.target ? humanLayoutLabel(layoutRunState.target, layoutCatalog) : "layout"}</span>
          <progress max={1} value={layoutRunState.progress} />
          <span>{(layoutRunState.progress * 100).toFixed(0)}%</span>
        </div>
        <p className="placeholder-copy">Layouts run in a browser worker when marked runnable, remain local view state, and never enter the measurement ledger.</p>
      </Card>
    );
  }

  function renderGraphSurface() {
    if (!data.graph) {
      return (
        <div className="empty-state">
          <h2>Graph payload not ready</h2>
          <p>Current status: {payloadStatuses.graph.status}. This semantic bundle is large and loads separately from the overview.</p>
        </div>
      );
    }

    const graphCanvas = (
      <GraphPanel
        nodes={filteredBaseline.nodes}
        edges={filteredBaseline.edges}
        coordinateMap={baselineCoordinateMap}
        appearance={appearance}
        highlightedNodeIds={highlightedNodeIds}
        selectedNodeIds={selectedNodeIds}
        selectedEdgeId={selectedEdgeId}
        selectedAssembly={assemblyRenderMode === "hidden" ? null : selectedAssembly}
        onSelectNode={handleSelectNode}
        onSelectEdge={handleSelectEdge}
        onClearSelection={handleClearSelection}
      />
    );

    const modifiedCanvas = (
      <GraphPanel
        nodes={filteredModified.nodes}
        edges={filteredModified.edges}
        coordinateMap={modifiedCoordinateMap}
        appearance={appearance}
        highlightedNodeIds={preview?.compare_selection?.modified_node_ids ?? highlightedNodeIds}
        selectedNodeIds={preview?.compare_selection?.modified_node_ids ?? selectedNodeIds}
        selectedEdgeId={selectedEdgeId}
        selectedAssembly={assemblyRenderMode === "hidden" ? null : selectedAssembly}
        addedNodeIds={(preview?.preview_graph_patch?.added_nodes ?? []).map((node: any) => node.id)}
        addedEdgeIds={(preview?.preview_graph_patch?.added_edges ?? []).map((edge: any) => edge.id || edgeKey(edge))}
        onSelectNode={handleSelectNode}
        onSelectEdge={handleSelectEdge}
        onClearSelection={handleClearSelection}
        ariaLabel="Modified graph canvas"
      />
    );

    return (
      <>
        {renderGraphControls()}
        {renderLayoutWorkbench()}
        {graphMode === "Compare" ? (
          <div className="compare-grid">
            <section className="compare-panel">
              <div className="compare-header">
                <h2>Baseline</h2>
                <span className={badgeClass("derived")}>{coordinateModeLabel(coordinateMode, layoutSnapshots, layoutCatalog)}</span>
              </div>
              {graphCanvas}
            </section>
            <section className="compare-panel">
              <div className="compare-header">
                <h2>Modified</h2>
                <span className={badgeClass("observed")}>{preview?.preview_graph_patch?.graph_changed ? "preview patch" : "view compare"}</span>
              </div>
              {modifiedCanvas}
            </section>
          </div>
        ) : (
          graphCanvas
        )}
      </>
    );
  }

  function renderMainSurface() {
    if (surface === "overview") return renderOverview();
    if (surface === "graph") return renderGraphSurface();
    if (surface === "basin" && !data.basin) {
      return <div className="empty-state"><h2>Basin payload not ready</h2><p>Current status: {payloadStatuses.basin.status}.</p></div>;
    }
    if (surface === "basin" && data.basin) {
      if ((data.basin.filtered_turn_count ?? 0) < 2) {
        return (
          <>
            <div className="toolbar">
              <div aria-label="Basin lift mode" className="toolbar-group" role="radiogroup">
                {(["flat", "time_lift", "density_lift", "session_offset"] as LiftMode[]).map((mode) => (
                  <button
                    aria-checked={mode === liftMode}
                    key={mode}
                    className={mode === liftMode ? "toolbar-button is-active" : "toolbar-button"}
                    onClick={() => setLiftMode(mode)}
                    role="radio"
                    type="button"
                  >
                    {mode}
                  </button>
                ))}
              </div>
              <div className="toolbar-group toolbar-badges">
                <span className={badgeClass("derived")}>Projection: {data.basin.projection_method ?? bootstrap.projection_method ?? "unknown"}</span>
                <span className={badgeClass("derived")}>Lift: {liftMode}</span>
                <span className={badgeClass("derived")}>Derived</span>
              </div>
            </div>
            <div className="empty-state">
              <h2>Sparse basin data</h2>
              <p>{data.basin.diagnostics?.reason ?? "Not enough turns with non-empty active sets for basin playback."}</p>
              <MetricList
                items={[
                  ["Source turns", data.basin.source_turn_count],
                  ["Filtered turns", data.basin.filtered_turn_count],
                  ["Skipped turns", data.basin.diagnostics?.skipped_turn_count],
                ]}
              />
            </div>
          </>
        );
      }
      return (
        <>
          <div className="toolbar">
            <div aria-label="Basin lift mode" className="toolbar-group" role="radiogroup">
              {(["flat", "time_lift", "density_lift", "session_offset"] as LiftMode[]).map((mode) => (
                <button
                  aria-checked={mode === liftMode}
                  key={mode}
                  className={mode === liftMode ? "toolbar-button is-active" : "toolbar-button"}
                  onClick={() => setLiftMode(mode)}
                  role="radio"
                  type="button"
                >
                  {mode}
                </button>
              ))}
            </div>
            <div className="toolbar-group toolbar-badges">
              <span className={badgeClass("derived")}>Projection: {data.basin.projection_method ?? bootstrap.projection_method ?? "unknown"}</span>
              <span className={badgeClass("derived")}>Lift: {liftMode}</span>
              <span className={badgeClass("derived")}>Derived</span>
            </div>
          </div>
          <BasinPanel payload={data.basin} currentTurnId={selectedTurn?.turn_id ?? null} liftMode={liftMode} onSelectTurn={handleSelectTurn} />
        </>
      );
    }
    if (surface === "geometry") {
      if (!data.geometry) {
        return (
          <div className="empty-state">
            <h2>Geometry payload {payloadStatuses.geometry.status}</h2>
            <p>
              {payloadStatuses.geometry.status === "error"
                ? "Geometry diagnostics are unavailable for this surface."
                : "The geometry bundle is intentionally deferred until you open this tab because it can be very large on seeded experiments."}
            </p>
            {payloadStatuses.geometry.error ? <p>{payloadStatuses.geometry.error}</p> : null}
          </div>
        );
      }
      return <pre className="debug-json">{JSON.stringify(data.geometry ?? {}, null, 2)}</pre>;
    }
    if (surface === "tanakh") {
      if (!data.tanakh) {
        return (
          <div className="empty-state">
            <h2>Tanakh payload {payloadStatuses.tanakh.status}</h2>
            <p>
              {payloadStatuses.tanakh.status === "error"
                ? "Tanakh artifacts are unavailable for this surface."
                : "The Tanakh bundle is deferred until you open this tab because it includes canonical text plus derived sidecars."}
            </p>
            {payloadStatuses.tanakh.error ? <p>{payloadStatuses.tanakh.error}</p> : null}
          </div>
        );
      }
      return (
        <TanakhPanel
          payload={data.tanakh}
          liveEnabled={data.liveEnabled}
          canRun={Boolean(data.liveEnabled && bootstrap.live_api?.tanakh_run)}
          running={tanakhRunPending}
          onRun={handleRunTanakh}
        />
      );
    }
    return <pre className="debug-json">{JSON.stringify(data.measurements ?? {}, null, 2)}</pre>;
  }

  function renderPrecisionDrawer() {
    return (
      <>
        {surface === "graph" ? (
          <Card title="Precision Drawer" accent={interactionMode}>
            <div className="form-grid">
              <label>
                <span>Edit action</span>
                <select aria-label="Edit action" value={actionForm.editAction} onChange={(event) => updateAction("editAction", event.target.value)}>
                  {["edge_add", "edge_update", "edge_remove", "memode_assert", "memode_update_membership", "geometry_measurement_run", "motif_annotation"].map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Edge type</span>
                <input aria-label="Edge type" value={actionForm.edgeType} onChange={(event) => updateAction("edgeType", event.target.value)} />
              </label>
              <label>
                <span>Weight</span>
                <input aria-label="Edge weight" type="number" step="0.1" value={actionForm.weight} onChange={(event) => updateAction("weight", Number(event.target.value || 1))} />
              </label>
              <label>
                <span>Confidence</span>
                <input aria-label="Confidence" type="number" step="0.01" value={actionForm.confidence} onChange={(event) => updateAction("confidence", Number(event.target.value || 0.7))} />
              </label>
              <label>
                <span>Evidence label</span>
                <select aria-label="Evidence label" value={actionForm.evidenceLabel} onChange={(event) => updateAction("evidenceLabel", event.target.value)}>
                  {(data.graph?.evidence_legend ? Object.keys(data.graph.evidence_legend) : ["OPERATOR_ASSERTED", "OPERATOR_REFINED", "DERIVED"]).map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Operator label</span>
                <input aria-label="Operator label" value={actionForm.operatorLabel} onChange={(event) => updateAction("operatorLabel", event.target.value)} />
              </label>
              <label>
                <span>Ablation relation</span>
                <select aria-label="Ablation relation" value={actionForm.ablationRelation} onChange={(event) => updateAction("ablationRelation", event.target.value)}>
                  {["CO_OCCURS_WITH", "MATERIALIZES_AS_MEMODE", "FED_BACK_BY"].map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Memode id</span>
                <input aria-label="Memode id" value={actionForm.memodeId} onChange={(event) => updateAction("memodeId", event.target.value)} />
              </label>
              <label>
                <span>Known memode label</span>
                <input aria-label="Known memode label" value={actionForm.memodeLabel} onChange={(event) => updateAction("memodeLabel", event.target.value)} />
              </label>
              <label>
                <span>Memode domain</span>
                <input aria-label="Memode domain" value={actionForm.memodeDomain} onChange={(event) => updateAction("memodeDomain", event.target.value)} />
              </label>
              <label>
                <span>Cluster manual label</span>
                <input aria-label="Cluster manual label" value={actionForm.manualLabel} onChange={(event) => updateAction("manualLabel", event.target.value)} />
              </label>
              <label>
                <span>Transfer policy</span>
                <input aria-label="Transfer policy" value={actionForm.transferPolicy} onChange={(event) => updateAction("transferPolicy", event.target.value)} />
              </label>
              <label className="field-span">
                <span>Rationale</span>
                <textarea aria-label="Rationale" rows={3} value={actionForm.rationale} onChange={(event) => updateAction("rationale", event.target.value)} />
              </label>
              <label className="field-span">
                <span>Known memode summary / annotation</span>
                <textarea aria-label="Known memode summary" rows={3} value={actionForm.memodeSummary} onChange={(event) => updateAction("memodeSummary", event.target.value)} />
              </label>
              <label className="field-span">
                <span>Cluster manual summary</span>
                <textarea aria-label="Cluster manual summary" rows={3} value={actionForm.manualSummary} onChange={(event) => updateAction("manualSummary", event.target.value)} />
              </label>
            </div>
          </Card>
        ) : null}

        {surface === "graph" ? (
          <Card title="Preview Diff" accent={preview?.action_type ?? "none"}>
            {preview?.error ? (
              <p className="status-error">{preview.error}</p>
            ) : preview ? (
              <pre className="debug-json">{JSON.stringify(preview, null, 2)}</pre>
            ) : (
              <p className="placeholder-copy">No preview yet. Run preview before commit to keep topology and measurement deltas explicit.</p>
            )}
          </Card>
        ) : null}

        {surface === "graph" ? (
          <Card title="Measurement Ledger" accent={String(data.measurements?.counts?.events ?? 0)}>
            <div className="history-list">
              {(data.measurements?.events ?? []).slice(0, 12).map((row: any) => (
                <div className="history-item" key={row.id}>
                  <div>
                    <strong>{row.action_type}</strong> <span className="tiny">{row.evidence_label} · {row.created_at}</span>
                  </div>
                  <div className="tiny">{row.summary || row.rationale || ""}</div>
                  <div className="toolbar">
                    <button className="toolbar-button" disabled={!canMutate || mutationPending} onClick={() => void handleRevert(row.id)} type="button">
                      Revert
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        ) : null}

        {surface === "graph" ? (
          <Card title="Runtime Trace" accent={String(data.trace?.trace_events?.length ?? 0)}>
            {data.trace ? (
              <>
                <p className="placeholder-copy">Trace and causality remain read-only. Observatory commits stay authoritative through preview / commit / revert only.</p>
                <div className="history-list">
                  {(data.trace.trace_events ?? []).slice(0, 8).map((event: any) => (
                    <div className="history-item" key={event.id}>
                      <div>
                        <strong>{event.event_type}</strong> <span className="tiny">{event.created_at}</span>
                      </div>
                      <div className="tiny">{event.message}</div>
                    </div>
                  ))}
                </div>
                {data.trace.latest_turn_trace?.length ? (
                  <pre className="debug-json">{JSON.stringify(data.trace.latest_turn_trace.slice(0, 6), null, 2)}</pre>
                ) : null}
              </>
            ) : (
              <p className="placeholder-copy">{data.liveEnabled ? `Runtime trace payload ${payloadStatuses.trace.status}.` : "Runtime trace is live-only."}</p>
            )}
          </Card>
        ) : null}

        {surface === "graph" ? (
          <Card title="Statistics + Rankings" accent={statsPending ? "running" : "on-demand"}>
            <div className="toolbar">
              <button className="primary-button" disabled={statsPending} onClick={handleComputeStats} type="button">
                Compute Statistics
              </button>
            </div>
            {stats?.error ? <p className="status-error">{stats.error}</p> : null}
            {stats?.summary ? (
              <>
                <MetricList items={Object.entries(stats.summary)} />
                <div className="table-scroll">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Ranking</th>
                        <th>Top nodes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(stats.rankings ?? {}).map(([ranking, rows]) => (
                        <tr key={ranking}>
                          <td>{ranking}</td>
                          <td>{rows.map((row) => `${row.label} (${row.score})`).join(", ")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p className="placeholder-copy">Statistics run client-side in a worker on the currently visible graph.</p>
            )}
          </Card>
        ) : null}
      </>
    );
  }

  function renderInspectorCards() {
    const rawTarget = selectedEdge ?? selectedNode ?? selectedAssembly ?? selectedTurn ?? data.overview ?? {};
    const measurementHistory = selectedEdge?.measurement_history ?? selectedNode?.measurement_history ?? selectedAssembly?.measurement_history ?? [];
    const provenance =
      selectedEdge?.operator_label ??
      selectedEdge?.provenance?.assertion_origin ??
      selectedNode?.provenance ??
      selectedAssembly?.operator_label ??
      selectedTurn?.profile_name ??
      "";
    const identityLabel = selectedEdge ? edgeLabel(selectedEdge, nodeLookup) : rawTarget?.label ?? rawTarget?.display_attractor_label ?? rawTarget?.display_label;
    const ontologyKind = rawTarget?.kind ?? (selectedEdge ? "edge" : selectedAssembly ? "memode" : selectedTurn ? "turn" : "overview");
    const ontologyDomain = selectedEdge ? `${nodeLookup.get(String(selectedEdge.source))?.domain ?? "unknown"} -> ${nodeLookup.get(String(selectedEdge.target))?.domain ?? "unknown"}` : rawTarget?.domain ?? rawTarget?.dominant_domain;
    const ontologySource = selectedEdge?.assertion_origin ?? selectedEdge?.provenance?.assertion_origin ?? rawTarget?.source_kind ?? "observatory";
    const clusterDisplay = selectedEdge
      ? `${nodeLookup.get(String(selectedEdge.source))?.cluster_label ?? nodeLookup.get(String(selectedEdge.source))?.cluster_signature ?? "unknown"} -> ${nodeLookup.get(String(selectedEdge.target))?.cluster_label ?? nodeLookup.get(String(selectedEdge.target))?.cluster_signature ?? "unknown"}`
      : rawTarget?.cluster_label ?? rawTarget?.display_label ?? selectedTurn?.display_attractor_label;
    const supportingRelations = selectedEdge
      ? [
          ["Source", nodeLabel(nodeLookup.get(String(selectedEdge.source)))],
          ["Target", nodeLabel(nodeLookup.get(String(selectedEdge.target)))],
          ["Relation type", selectedEdge?.type],
        ]
      : selectedNode
        ? [
            [
              "Connected relations",
              filteredBaseline.edges
                .filter((edge) => edge.source === selectedNode.id || edge.target === selectedNode.id)
                .slice(0, 4)
                .map((edge) => edgeLabel(edge, nodeLookup)),
            ],
            ["Current turn", selectedTurn?.turn_id],
            ["Attractor", selectedTurn?.display_attractor_label],
          ]
        : [
            ["Active set nodes", selectedTurn?.active_set_node_ids],
            ["Transition", selectedTurn?.transition_kind],
            ["Attractor", selectedTurn?.display_attractor_label],
          ];
    const activeSetPresence = selectedEdge
      ? [
          ["Source presence", nodeLookup.get(String(selectedEdge.source))?.recent_active_set_presence],
          ["Target presence", nodeLookup.get(String(selectedEdge.target))?.recent_active_set_presence],
          ["Highlighted nodes", highlightedNodeIds.length],
        ]
      : selectedAssembly
        ? [
            ["Members in active set", (selectedAssembly.member_meme_ids ?? []).filter((id: string) => highlightedNodeIds.includes(id))],
            ["Highlighted nodes", highlightedNodeIds.length],
            ["Selected turn", selectedTurn?.turn_id],
          ]
        : [
            ["Recent presence", rawTarget?.recent_active_set_presence ?? selectedTurn?.active_set_summary?.size],
            ["Selected turn", selectedTurn?.turn_id],
            ["Highlighted nodes", highlightedNodeIds.length],
          ];
    return (
      <div className="inspector-cards">
        <Card title="Identity">
          <MetricList
            items={[
              ["ID", rawTarget?.id ?? rawTarget?.turn_id ?? rawTarget?.cluster_signature],
              ["Label", identityLabel],
              ["Created", rawTarget?.created_at],
            ]}
          />
        </Card>
        <Card title="Ontology">
          <MetricList
            items={[
              ["Kind", ontologyKind],
              ["Domain", ontologyDomain],
              ["Source", ontologySource],
            ]}
          />
        </Card>
        <Card title="Summary/Invariance">
          <MetricList
            items={[
              ["Summary", rawTarget?.summary ?? rawTarget?.manual_summary ?? rawTarget?.dominant_label],
              ["Invariance", selectedAssembly?.invariance_summary],
              ["Recent turns", selectedTurn?.active_set_labels],
            ]}
          />
        </Card>
        <Card title="Provenance">
          <MetricList
            items={[
              ["Operator/Source", provenance],
              ["Evidence label", rawTarget?.evidence_label ?? selectedAssembly?.evidence_label ?? selectedEdge?.evidence_label],
              ["Confidence", rawTarget?.confidence ?? selectedAssembly?.confidence ?? selectedEdge?.confidence],
            ]}
          />
        </Card>
        <Card title="Cluster Membership">
          <MetricList
            items={[
              ["Cluster", selectedEdge ? `${nodeLookup.get(String(selectedEdge.source))?.cluster_signature ?? "unknown"} -> ${nodeLookup.get(String(selectedEdge.target))?.cluster_signature ?? "unknown"}` : rawTarget?.cluster_signature ?? selectedTurn?.dominant_cluster_signature],
              ["Display label", clusterDisplay],
              ["Domain mix", rawTarget?.domain_mix],
            ]}
          />
        </Card>
        <Card title="Memode Membership">
          <MetricList
            items={[
              ["Assemblies", selectedEdge ? [...(nodeLookup.get(String(selectedEdge.source))?.memode_membership ?? []), ...(nodeLookup.get(String(selectedEdge.target))?.memode_membership ?? [])] : rawTarget?.memode_membership ?? selectedAssembly?.member_meme_ids],
              ["Supporting edges", selectedAssembly?.supporting_edge_ids],
              ["Member order", selectedAssembly?.member_order],
            ]}
          />
        </Card>
        <Card title="Supporting Relations">
          <MetricList items={supportingRelations} />
        </Card>
        <Card title="Active Set Presence">
          <MetricList items={activeSetPresence} />
        </Card>
        <Card title="Measurement History">
          <MetricList
            items={[
              ["Count", measurementHistory.length],
              ["Recent event", measurementHistory[0]?.action_type],
              ["Preview delta", "Use preview/commit API; view-only presets stay out of evidence."],
            ]}
          />
        </Card>
      </div>
    );
  }

  function renderInspector() {
    const rawTarget = selectedEdge ?? selectedNode ?? selectedAssembly ?? selectedTurn ?? data.overview ?? {};
    return (
      <aside className="inspector">
        {renderPrecisionDrawer()}
        <div aria-label="Inspector view" className="inspector-tabs" role="tablist">
          <button
            aria-controls="observatory-inspector-panel"
            aria-selected={inspectorTab === "cards"}
            className={inspectorTab === "cards" ? "toolbar-button is-active" : "toolbar-button"}
            id="observatory-inspector-tab-cards"
            onClick={() => setInspectorTab("cards")}
            role="tab"
            type="button"
          >
            Cards
          </button>
          <button
            aria-controls="observatory-inspector-panel"
            aria-selected={inspectorTab === "json"}
            className={inspectorTab === "json" ? "toolbar-button is-active" : "toolbar-button"}
            id="observatory-inspector-tab-json"
            onClick={() => setInspectorTab("json")}
            role="tab"
            type="button"
          >
            Raw JSON
          </button>
        </div>
        <div aria-labelledby={inspectorTab === "json" ? "observatory-inspector-tab-json" : "observatory-inspector-tab-cards"} id="observatory-inspector-panel" role="tabpanel">
          {inspectorTab === "json" ? <pre className="debug-json">{JSON.stringify(rawTarget, null, 2)}</pre> : renderInspectorCards()}
        </div>
      </aside>
    );
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">EDEN Observatory</p>
          <h1>Live-first semantic graph and basin instrument</h1>
        </div>
        <div className="header-badges">
          <span className={badgeClass("observed")}>{data.liveEnabled ? "Live API" : "Static export"}</span>
          <span className={badgeClass("derived")}>Layout != evidence</span>
          {data.staleBuildWarning ? <span className={badgeClass("warning")}>Build warning: {data.staleBuildWarning}</span> : null}
        </div>
      </header>

      <nav aria-label="Observatory surface" className="surface-tabs" role="tablist">
        {SURFACES.map((item) => (
          <button
            aria-controls="observatory-surface-panel"
            aria-selected={item === surface}
            className={item === surface ? "toolbar-button is-active" : "toolbar-button"}
            id={`observatory-surface-tab-${item}`}
            key={item}
            onClick={() => setSurface(item)}
            role="tab"
            type="button"
          >
            {labelForSurface(item)}
          </button>
        ))}
      </nav>

      {renderPayloadStatus()}
      {renderContinuityStrip()}
      {error ? <div className="status-banner status-error">{error}</div> : null}

      <main className="layout">
        {renderSidebar()}
        <section aria-labelledby={`observatory-surface-tab-${surface}`} className="surface-panel" id="observatory-surface-panel" role="tabpanel">
          {renderMainSurface()}
        </section>
        {renderInspector()}
      </main>
    </div>
  );
}

function buildCoordinateMap(nodes: GraphNode[], coordinateMode: string, snapshots: LayoutSnapshot[]): CoordinateMap {
  const snapshot = snapshots.find((entry) => entry.id === coordinateMode);
  const map: CoordinateMap = {};
  for (const node of nodes) {
    if (snapshot?.coordinateMap?.[node.id]) {
      map[node.id] = snapshot.coordinateMap[node.id];
      continue;
    }
    if (coordinateMode === "force") map[node.id] = node.render_coords?.force ?? node.derived_coords?.spectral ?? { x: 0, y: 0 };
    else if (coordinateMode === "symmetry") map[node.id] = node.derived_coords?.pca ?? node.render_coords?.force ?? { x: 0, y: 0 };
    else map[node.id] = node.derived_coords?.[coordinateMode] ?? node.render_coords?.force ?? { x: 0, y: 0 };
  }
  return map;
}

function renderLayoutSettingsFields(
  layoutMeta: LayoutAlgorithmMeta | null,
  settings: Record<string, any>,
  update: (layoutId: string, key: string, value: any) => void,
) {
  if (!layoutMeta?.controls?.length) return null;
  return layoutMeta.controls.map((control) => {
    const ariaLabel = `${layoutMeta.label} ${control.label}`;
    if (control.input === "checkbox") {
      return (
        <label className="toggle-line" key={`${layoutMeta.id}-${control.key}`}>
          <input
            aria-label={ariaLabel}
            checked={Boolean(settings[control.key])}
            onChange={(event) => update(layoutMeta.id, control.key, event.target.checked)}
            type="checkbox"
          />
          <span>{control.label}</span>
        </label>
      );
    }
    if (control.input === "select") {
      return (
        <label key={`${layoutMeta.id}-${control.key}`}>
          <span>{control.label}</span>
          <select aria-label={ariaLabel} value={String(settings[control.key] ?? control.options[0]?.value ?? "")} onChange={(event) => update(layoutMeta.id, control.key, event.target.value)}>
            {control.options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      );
    }
    if (control.input === "text") {
      return (
        <label key={`${layoutMeta.id}-${control.key}`}>
          <span>{control.label}</span>
          <input aria-label={ariaLabel} onChange={(event) => update(layoutMeta.id, control.key, event.target.value)} type="text" value={String(settings[control.key] ?? "")} />
        </label>
      );
    }
    return (
      <label key={`${layoutMeta.id}-${control.key}`}>
        <span>{control.label}</span>
        <input
          aria-label={ariaLabel}
          max={control.max}
          min={control.min}
          onChange={(event) => {
            const raw = event.target.value;
            update(layoutMeta.id, control.key, raw === "" ? "" : Number(raw));
          }}
          step={control.step}
          type="number"
          value={settings[control.key] ?? ""}
        />
      </label>
    );
  });
}

function coordinateModeLabel(modeId: string, snapshots: LayoutSnapshot[], catalog?: Record<string, LayoutAlgorithmMeta> | null): string {
  const snapshot = snapshots.find((entry) => entry.id === modeId);
  if (snapshot) return snapshot.name;
  return humanLayoutLabel(modeId, catalog);
}

function humanExportLabel(format: string): string {
  if (format === "nodes_csv") return "Nodes CSV";
  if (format === "edges_csv") return "Edges CSV";
  if (format === "selection_json") return "Selection JSON";
  return format.toUpperCase();
}

function dedupeSnapshots(items: LayoutSnapshot[]): LayoutSnapshot[] {
  const seen = new Set<string>();
  const next: LayoutSnapshot[] = [];
  for (const item of [...items].reverse()) {
    if (seen.has(item.id)) continue;
    seen.add(item.id);
    next.push(item);
  }
  return next.reverse();
}
