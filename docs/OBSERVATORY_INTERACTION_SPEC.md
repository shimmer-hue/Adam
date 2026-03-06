# Observatory Interaction Spec

EDEN v1.2 treats the observatory as a constructive measurement instrument. Observation can lead to a preview, a preview can lead to a committed mutation, and the mutation remains revertible and attributable.

## Interaction modes

### `INSPECT`

- hover and pin nodes or edges
- inspect provenance, geometry context, and measurement history
- no graph mutation

### `MEASURE`

- select nodes
- compute local geometry
- inspect before/after deltas without committing topology changes

### `EDIT`

- add an edge
- update an edge
- remove an edge
- assert a known memode from a multi-node selection
- refine an existing memode's membership

### `ABLATE`

- preview masked-edge or relation-class perturbations
- compare geometry without silently rewriting the graph

### `COMPARE`

- compare baseline vs modified preview
- compare slices and coordinate modes
- keep layout interpretation separate from topology interpretation

## Preview / commit / revert flow

1. Select nodes or pin an edge.
2. Configure the intended action in the precision drawer.
3. Run preview.
4. Inspect:
   - local metric deltas
   - global metric deltas
   - topology change summary
5. Commit if warranted.
6. Observe refreshed graph, geometry, and ledger state.
7. Revert explicitly if needed.

## Known memode workflow

The operator may:

- select multiple meme nodes
- set label, summary, domain, rationale, confidence, and evidence label
- preview the local geometry impact
- commit a memode assertion
- later refine the memode membership or notes

Known memodes are operator-facing structured claims about reusable motifs. They are not silently promoted to observed geometry.

## Runtime bridge

Committed observatory actions emit runtime log and trace events. Subsequent retrieval and active-set assembly can then operate on the changed graph state, which makes observatory edits causally visible to later turns.
