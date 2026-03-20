# Observatory Interaction Spec

EDEN v1.2 treats the observatory as a constructive measurement instrument. Observation can lead to a preview, a preview can lead to a committed mutation, and the mutation remains revertible and attributable.

## Workspace grammar

- the browser shell is partitioned into three top-level workspaces:
  - `Overview` for graph-first exploration
  - `Data Laboratory` for spreadsheet audit and slice operations
  - `Preview` for final render/export styling
- `Overview` uses a deterministic dock layout with:
  - left dock for `Appearance` and `Layout`
  - center graph canvas with graph-mode strip, tool rail, and render tray
  - right dock for `Statistics`, `Filters`, `Context`, `Inspector`, `Queries`, `Memode Audit`, action controls, ledger, and runtime adjuncts
- workspace layout, dock collapse state, appearance presets, filters, table sort state, and preview settings are browser-local view state only
- `Reset layout` restores the default dock arrangement and does not touch graph authority or measurement history

## Interaction modes

### `INSPECT`

- hover and pin nodes or edges
- inspect provenance, geometry context, and measurement history
- inspect runtime causality through session trace and continuity-strip reasoning surfaces
- no graph mutation

### `MEASURE`

- select nodes
- compute local geometry
- inspect before/after deltas without committing topology changes
- preview compare state through `preview_graph_patch`

### `EDIT`

- add an edge
- update an edge
- remove an edge
- assert a known memode from a multi-node selection
- refine an existing memode's membership
- annotate a derived semantic cluster without mutating topology

### `ABLATE`

- preview masked-edge or relation-class perturbations
- compare geometry without silently rewriting the graph

### `COMPARE`

- compare baseline vs modified preview
- compare slices and coordinate modes
- keep layout interpretation separate from topology interpretation
- expose layout snapshots and baseline/modified highlights without committing graph mutation

## Precision drawer and side rails

- the graph workbench keeps graph-first focus while selection-sensitive controls live in the right dock
- the action/precision area is the single browser control surface for:
  - `Preview`
  - `Commit`
  - `Revert`
  - action-specific fields such as rationale, evidence label, confidence, operator label, edge parameters, memode details, ablation relation masks, and motif annotation fields
- `Statistics`, `Filters`, `Context`, `Inspector`, `Queries`, `Memode Audit`, the measurement ledger, and runtime trace remain switchable beside the graph instead of replacing it
- the graph canvas itself exposes a tool rail for direct interaction plus a bottom render tray for labels/overlay/render settings
- static exports retain the same visible controls but disable mutation actions with explicit copy instead of hiding them

## Preview / commit / revert flow

1. Select nodes or pin an edge.
2. Configure the intended action in the precision drawer.
3. Run preview.
4. Inspect:
   - local metric deltas
   - global metric deltas
   - `compare_selection`
   - `preview_graph_patch`
   - topology change summary
5. Commit if warranted.
6. Observe refreshed graph, geometry, and ledger state.
7. Revert explicitly if needed.

`Preview` the workspace is distinct from `Preview` the mutation step. The workspace controls final render/export styling and requires explicit refresh, while mutation preview remains the attributable pre-commit evidence path.

## Known memode workflow

The operator may:

- select multiple meme nodes
- satisfy the admissibility floor:
  - at least two meme nodes
  - at least one qualifying semantic support edge
  - every selected meme participates in that support graph
  - the support graph is connected
- set label, summary, domain, rationale, confidence, and evidence label
- preview the local geometry impact
- commit a memode assertion
- later refine the memode membership or notes

Known memodes are operator-facing structured claims about reusable motifs. They are not silently promoted to observed geometry.

## Graph reading workflow

- `Semantic Map` is the default reading mode and appears inside `Overview`
- `Assemblies` highlights memode member memes and supporting edges
- `Runtime` isolates turns, sessions, documents, feedback, and provenance relations
- `Active Set` foregrounds turn-bounded retrieval participation
- `Compare` keeps baseline vs modified state visible without hiding the measurement ledger

## Data Laboratory workflow

- switch between `Nodes` and `Edges` tables without leaving the browser workbench
- sort/search/filter rows in a spreadsheet-style surface
- show or hide audit columns while keeping stable ids and `export_label` available
- row selection highlights the corresponding graph entity
- graph selection highlights the corresponding row
- `Select in Graph` and workspace-tab handoff keep graph/table navigation explicit
- export-scope controls remain visible in Data Laboratory because operators often choose slices from the table view

## Memode audit workflow

- open `Memode Audit` from the graph workbench while staying on the graph surface
- inspect the per-memode admissibility readout:
  - minimum member count
  - materialized support-edge presence
  - member participation in that support graph
  - connectedness of the support graph
- inspect member memes directly from the audit table
- inspect materialized memetic support edges separately from:
  - member-local informational relations
  - unmaterialized support candidates
  - knowledge informational relations that remain non-memetic
- use relation focus from the audit table to hand off into inspector / precision-drawer workflows without collapsing evidence families together

## Preview workspace workflow

- open `Preview` to stage final-render settings separately from graph mutation
- adjust label mode, edge opacity, curvature, background, legend, caption, and export scope
- run `Refresh preview` explicitly when preview settings change
- export from this workspace after confirming appearance
- preview settings remain browser-local and do not enter the measurement ledger

Inspector workflow:

- cards first
- raw JSON only as a debug tab
- view presets stay browser-local and never enter the measurement ledger
- layout presets, styling, filter presets, and table sorting stay browser-local and never enter the measurement ledger

## Runtime bridge

Committed observatory actions emit runtime log and trace events. Subsequent retrieval and active-set assembly can then operate on the changed graph state, which makes observatory edits causally visible to later turns.

Browser-visible runtime causality is exposed through `GET /api/sessions/<session_id>/trace`, which carries:

- `latest_turn_trace`
- `trace_events`
- `membrane_events`

This trace surface is read-only. It mirrors runtime causality; it does not authorize mutation.
