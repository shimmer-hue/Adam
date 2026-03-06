# Observatory Spec

EDEN v1.2 keeps the static export path from v1.1 and adds a lightweight local observatory API so the browser layer can act as a measurement-bearing instrument instead of a read-only gallery.

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
- `observatory_index.html`
- `observatory_index.json`

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

## Graph knowledge base

- filterable by search, session, kind, domain, source, verdict, evidence label, and timestamp substring
- multiple coordinate modes:
  - `force`
  - `spectral`
  - `circular_candidate`
  - `temporal`
  - `symmetry` (`pca`)
  - `basin_linked`
- left rail filters, health cards, graph surface, measurement toolbar, precision drawer, and measurement ledger
- inspector shows:
  - node or edge identity
  - provenance
  - community and motif signals
  - memode membership
  - recent active-set presence
  - observatory-originated event history
- coordinate modes are explicitly view modes, not evidence claims

## Measurement-first contract

1. Select nodes or an edge.
2. Propose an action in the precision drawer.
3. Preview before/after metric deltas.
4. Commit only if the change is warranted.
5. Persist the event with provenance.
6. Refresh graph, geometry, and measurement ledger views.
7. Revert explicitly if needed.

Observation does not silently mutate the graph. Mutation is a separate, attributable step.

## Behavioral attractor basin

- turn trajectory computed from real turn features
- explicit projection provenance (`svd_on_turn_features`)
- per-turn overlays for:
  - inference profile
  - requested/effective mode
  - budget pressure
  - remaining input budget
  - membrane-event counts
  - active-set recurrence
  - phase-transition markers
- session filter in the browser artifact

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
- `GET /api/experiments/<experiment_id>/payload`
- `GET /api/experiments/<experiment_id>/measurement-events`
- `POST /api/experiments/<experiment_id>/preview`
- `POST /api/experiments/<experiment_id>/commit`
- `POST /api/experiments/<experiment_id>/revert`

TUI behavior:

- `Observatory` ensures the local server is running and opens the current experiment index page
- repeated use is safe and does not create ghost server state
- observatory-originated edits are logged back into the runtime trace surfaces

## Validation

Validated in this patch:

- CLI port fallback from an occupied requested port to a nearby free port
- live API preview / commit / revert against a real experiment
- observatory graph instrument opened in a real browser session
- geometry lab opened in a real browser session
