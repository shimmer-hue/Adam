# Observatory Geometry Spec

The geometry layer in v1.2 is an empirical observability surface over the memgraph and its temporal traces. It now supports both global reports and local, selection-based measurement previews tied to possible graph edits.

## Artifact outputs

- `geometry_diagnostics.json`
- `geometry_lab.html`
- `geometry_manifest.json`

## Coordinate methods

`force`

- render-only layout
- useful for navigation
- not evidence by itself

`spectral`

- Laplacian eigenvector projection
- derived coordinate method

`pca`

- PCA on adjacency rows
- derived coordinate method

`circular_candidate`

- evenly spaced circle ordered by spectral angle
- useful for testing whether circular organization survives coordinate changes

`temporal`

- chronology-oriented projection over ordered nodes

`basin_linked`

- rendering mode anchored to basin ordering rather than a claim about topology

## Computed diagnostics

`OBSERVED`

- circularity / ringness proxy
- radiality / spoke-ness proxy
- linearity / chain-like proxy
- community structure
- triadic closure / motif richness

`DERIVED`

- mirror/reflection symmetry proxy
- chirality / handedness proxy on directed motifs
- translation-symmetry proxy on ordered structures
- projection quality summaries

`SPECULATIVE`

- operator-facing hypothesis only
- never used for score-bearing summaries

## Slice support

- `full_graph`
- `current_session`
- `current_active_set`
- `latest_active_set`
- verdict slices when populated
- memode-local slices when a materialized memode exists

## Local measurement support

For a live selection the geometry layer can report:

- neighborhood-local metric bundle
- selection counts
- before/after metric deltas for a proposed edit
- comparison against the full graph slice
- local ablation behavior when a relation class is masked

This is the key v1.2 change: geometry is no longer only a global report. It can be used as a local measurement surface around a candidate memode or relation edit.

## Ablations

Current v1.2 ablations:

- mask direct `CO_OCCURS_WITH` edges
- remove the dominant detected community
- compare selected local subgraph vs full graph

Each report includes:

- before scores
- after scores
- persistence score
- ablation detail string

## Interpretation boundary

The geometry lab is intentionally in conversation with the Karkada et al. symmetry paper on representation geometry and perturbation robustness, but it does not claim that the paper proves graph-based persona persistence. In EDEN, the paper influences:

- geometry-aware diagnostics
- symmetry language
- perturbation / ablation framing
- care around collective structure surviving local masking
- the treatment of memodes as recoverable higher-order motifs rather than pairwise links
