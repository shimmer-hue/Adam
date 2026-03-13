# Observatory Spec

EDEN v1.2 keeps Python authoritative for exports, clustering, basin projection, and measurement provenance while replacing the inline canvas artifacts with one checked-in React + TypeScript + Vite observatory bundle. The browser layer is now a live-first graph workbench: it exposes inspect, measure, edit, ablate, compare, layout, filtering, styling, ranking, tabular, and export surfaces while keeping authority boundaries explicit.

## Artifact families

Generated per experiment under `exports/<experiment_id>/`:

- `graph_knowledge_base.html`
- `graph_knowledge_base.json`
- `graph_knowledge_base.manifest.json`
- `behavioral_attractor_basin.html`
- `behavioral_attractor_basin.json`
- `behavioral_attractor_basin.manifest.json`
- `geometry_lab.html`
- `geometry_diagnostics.json`
- `geometry_manifest.json`
- `measurement_ledger.html`
- `measurement_events.json`
- `measurement_events.manifest.json`
- `tanakh_manifest.json`
- `tanakh_index.json`
- `tanakh_surface.json`
- `tanakh_measurements.json`
- `tanakh_render_validation.json`
- `tanakh_render_validation.html`
- `tanakh_passage_cache/<ref>.json`
- `tanakh_scene_<id>.json`
- `observatory_index.html`
- `observatory_index.json`
- `_observatory_app/` checked-in frontend bundle copied from `eden/observatory/static/observatory_app/`

## Observatory modes

- `INSPECT`
  - hover, pin, inspect provenance, regard, local neighborhood, and measurement history
- `MEASURE`
  - compute local motif metrics or geometry deltas without mutating topology
- `EDIT`
  - add/update/remove edges with provenance
  - assert known memodes
  - refine memode membership
- `ABLATE`
  - preview masked-edge comparisons and relation-class perturbations
- `COMPARE`
  - compare slices, coordinate methods, or baseline vs modified states

## Continuity strip

- the browser shell keeps a continuity strip visible above the main three-column layout
- the strip contains:
  - a persistent hum fact card grounded in the bounded hum artifact summary
  - an operator-visible reasoning card with a radio-group lens switcher:
    - `Reasoning`
    - `Chain-Like`
    - `Hum Live`
- `Hum Live` reformats the bounded hum text surface as chain-like continuity beats; it does not claim hidden chain-of-thought
- operator-visible reasoning in the browser is sourced from live session transcript payloads when available; static export alone may not provide a current reasoning artifact

## Graph knowledge base

- authoritative graph payload planes:
  - `semantic_nodes`
  - `semantic_edges`
  - `runtime_nodes`
  - `runtime_edges`
  - `assemblies`
  - `cluster_summaries`
  - `active_set_slices`
- browser workbench metadata surfaces:
  - `layout_families`
  - `layout_catalog`
  - `layout_defaults`
  - `appearance_dimensions`
  - `filter_dimensions`
  - `statistics_capabilities`
  - `export_formats`
- legacy `nodes` / `edges` remain for one compatibility release only
- semantic clustering is computed only on the meme-only semantic subgraph with deterministic Louvain settings, canonical node ordering, and versioned tokenization/labeling inputs
- graph UI grammar is explicit:
  - `Semantic Map`
  - `Assemblies`
  - `Runtime`
  - `Active Set`
  - `Compare`
- `Semantic Map` shows memes as first-class visible nodes, semantic edges, cluster hull/label summaries, and memode overlays
- memodes render as second-order assemblies with `hulls`, `collapsed-meta-node`, or `hidden` overlay modes; they are not default peer dots
- label disclosure is progressive and non-hover-dependent:
  - cluster labels first
  - selected / pinned / high-centrality meme labels next
  - edge labels only on focus or selection
- inspector surfaces structured cards for identity, ontology, domain, provenance, evidence/confidence, cluster membership, memode membership, supporting relations, active-set presence, measurement history, and preview delta
- raw JSON survives only as a debug tab
- coordinate modes remain explicit view modes, not evidence claims

## Browser-local workbench surfaces

- the graph tab exposes explicit mode controls for `INSPECT`, `MEASURE`, `EDIT`, `ABLATE`, and `COMPARE`
- the shell keeps a search/filter rail, coordinate-mode selector, selection summary, precision drawer, measurement ledger actions, runtime trace panel, and Data Lab tables visible as first-class workbench surfaces
- compare mode renders baseline vs modified state from preview responses without committing mutation
- local layout execution is browser-only:
  - layouts run through a worker-backed `LayoutRunner`
  - the layout picker is organized as a 12-family terrain browser spanning force-directed, hierarchical, tree, circular, spectral, multilevel, constraint, orthogonal, planar, geographic, community, and edge-bundling families
  - every terrain item carries operator-facing explanation copy for what it is and how it is typically used
  - runnable browser-worker layouts currently include `forceatlas2`, `fruchterman_reingold`, `kamada_kawai`, `linlog`, `sugiyama_layered`, `radial_tree`, `simple_circular`, `circular_degree`, `circular_community`, `radial`, `noverlap`, `fixed_coordinate`, and `community_clusters`
  - many additional algorithms are exposed as reference-only terrain items so the operator can browse the wider layout landscape without EDEN pretending they execute locally
  - presets and layout snapshots persist in browser-local storage keyed by experiment identity plus manifest / graph hash
  - layout, filter, appearance, and table state do not enter the measurement ledger
- appearance controls can style node / edge color, size, label visibility, and opacity from EDEN attributes such as kind, domain, cluster, evidence label, active-set presence, degree, weight, and regard/reward/risk where present
- filter controls can constrain text, attribute/range slices, connected components, isolated-node visibility, and ego neighborhoods without mutating graph facts
- the Data Lab provides node/edge tables, sorting, bulk selection, CSV/JSON export of the current selection, and precision-drawer handoff
- export interoperability includes `gexf`, `graphml`, node CSV, and edge CSV for the current browser-visible graph slice

## Public browser payload contract

- graph payloads expose layout, appearance, filter, statistics, and export capability metadata so the React shell can stay declarative instead of hard-coding instrument assumptions
- graph payload layout metadata includes:
  - `layout_families`
  - `layout_catalog`
  - `layout_defaults`
- payload layout metadata may be partial; the checked-in frontend terrain catalog fills unspecified reference/explanation entries so older static exports still render the full layout landscape truthfully
- preview responses expose:
  - `compare_selection`
  - `preview_graph_patch`
- `preview_graph_patch` is a browser compare artifact only; it is not a persisted graph fact
- when live session context exists, the shell bootstrap exposes `session_trace` alongside `preview`, `commit`, and `revert`

## Measurement-first contract

1. Select nodes or an edge.
2. Propose an action in the precision drawer.
3. Preview before/after metric deltas plus `preview_graph_patch` baseline vs modified state.
4. Commit only if the change is warranted.
5. Persist the event with provenance.
6. Refresh graph, geometry, measurement ledger, and runtime trace views.
7. Revert explicitly if needed.

Observation does not silently mutate the graph. Mutation is a separate, attributable step.
Layout, styling, filter presets, table sort state, and coordinate-mode choices remain browser-local view state and are not evidence.

## Behavioral attractor basin

- turn trajectory computed from real turn features
- explicit projection provenance (`svd_on_turn_features`)
- projection metadata includes:
  - `projection_method`
  - `projection_version`
  - `projection_input_hash`
  - `source_turn_count`
  - `filtered_turn_count`
- per-turn overlays for:
  - inference profile
  - requested/effective mode
  - budget pressure
  - remaining input budget
  - membrane-event counts
  - active-set recurrence
  - phase-transition markers
- stable per-turn and per-attractor identity fields include dominant node, dominant memode, dominant cluster signature, and display attractor label
- basin lift modes are explicit derived rendering choices:
  - `flat`
  - `time_lift`
  - `density_lift`
  - `session_offset`
- the UI surfaces projection method, lift mode, and derived-status badges directly in the controls and inspector
- sparse basin payloads are honest: if fewer than two turns survive filtering, the browser shows a diagnostic empty state instead of a fake basin

## Geometry lab

- global geometry diagnostics
- slice views:
  - `full_graph`
  - `current_session`
  - `current_active_set`
  - `latest_active_set`
  - verdict slices when populated
  - memode-local slices when populated
- local selection measurement over the live API when available
- metric evidence labels:
  - `OBSERVED`
  - `DERIVED`
  - `SPECULATIVE`
  - operator assertion labels surfaced separately from geometry evidence labels

## Tanakh tool-surface

- the Tanakh surface is an additive observatory instrument, not a replacement runtime
- canonical Tanakh reading stays DOM/CSS-based unless a separate render-validation proof upgrades that claim
- derived analyzers are exposed as explicit sidecars:
  - `get_passage`
  - `gematria`
  - `notarikon`
  - `temurah`
  - `compile_merkavah_scene`
- every Tanakh payload carries provenance for:
  - canonical citation or raw source
  - dataset id / text version / build / archive hash
  - preprocessing choices
  - operator version
  - parameterization
  - creation timestamp
  - output kind (`canonical_text`, `derived_transformation`, or `derived_visualization`)
- the first merkavah slice is explicitly derived:
  - canonical entry ref defaults to `Ezek 1`
  - same ref + params produce hash-stable scene JSON
  - `sceneNodeId -> citation span` linkage is exported in the scene payload
- Tanakh runs are surfaced in observatory sidecar artifacts and overview badges; they are not silently promoted to first-class measurement events

## Local observatory server

CLI:

```bash
.venv/bin/python -m eden observatory --host 127.0.0.1 --port 8741 --open
```

Behavior:

- if the requested port is free, EDEN uses it
- if the requested port is already serving the same exports root, EDEN reuses it
- if the requested port is occupied by something else, EDEN walks to the next free port in a bounded range
- the actual URL is printed as JSON
- server info is persisted at `exports/.eden_observatory.json`

Live API:

- `GET /api/status`
- `GET /api/experiments`
- `GET /api/experiments/<experiment_id>/payload`
- `GET /api/experiments/<experiment_id>/overview`
- `GET /api/experiments/<experiment_id>/graph`
- `GET /api/experiments/<experiment_id>/basin`
- `GET /api/experiments/<experiment_id>/geometry`
- `GET /api/experiments/<experiment_id>/measurement-events`
- `GET /api/experiments/<experiment_id>/tanakh`
- `GET /api/experiments/<experiment_id>/sessions`
- `GET /api/sessions/<session_id>/turns`
- `GET /api/sessions/<session_id>/active-set`
- `GET /api/sessions/<session_id>/trace`
- `GET /api/runtime/status`
- `GET /api/runtime/model`
- `GET /api/experiments/<experiment_id>/events` (SSE invalidation stream)
- `POST /api/experiments/<experiment_id>/preview`
- `POST /api/experiments/<experiment_id>/commit`
- `POST /api/experiments/<experiment_id>/revert`
- `POST /api/experiments/<experiment_id>/tanakh-run`

SSE emits small invalidation payloads only. It does not push full graph or basin payloads.

TUI behavior:

- `Observatory` ensures the local server is running and opens the current experiment index page
- repeated use is safe and does not create ghost server state
- observatory-originated edits are logged back into the runtime trace surfaces
- static exports must be HTTP-served, either by the EDEN observatory server or another static file server; direct `file://` opening is not a supported runtime path for the v1 bundle
- runtime status exposes frontend build freshness so stale checked-in assets can warn at runtime and fail CI/release checks

## Validation

Validated in this patch:

- CLI port fallback from an occupied requested port to a nearby free port
- live API preview / commit / revert plus graph / basin / transcript read endpoints against a real experiment
- SSE invalidation stream emits compact refresh messages after observatory commits
- the checked-in React observatory bundle builds and emits `build-meta.json`
- Tanakh surface export writes canonical/derived sidecars plus a manual-review render-validation harness
