# Observatory Interaction Spec

EDEN v1.2 treats the observatory as a constructive measurement instrument. Observation can lead to a preview, a preview can lead to a committed mutation, and the mutation remains revertible and attributable.

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

- the graph workbench keeps a search/filter rail, selection summary, coordinate-mode selector, measurement ledger panel, runtime trace panel, and Data Lab available beside the main graph surface
- the precision drawer is the single browser control surface for:
  - `Preview`
  - `Commit`
  - `Revert`
  - action-specific fields such as rationale, evidence label, confidence, operator label, edge parameters, memode details, ablation relation masks, and motif annotation fields
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

- `Semantic Map` is the default reading mode
- `Assemblies` highlights memode member memes and supporting edges
- `Runtime` isolates turns, sessions, documents, feedback, and provenance relations
- `Active Set` foregrounds turn-bounded retrieval participation
- `Compare` keeps baseline vs modified state visible without hiding the measurement ledger

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
