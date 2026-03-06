# Geometry Evidence Policy

EDEN may use evocative operator language such as “geometry lab” or “sacred geometry,” but every geometry claim must be evidence-scoped.

## Labels

### `OBSERVED`

- directly computed from graph topology, temporal recurrence, or explicit counts
- examples:
  - ringness proxy
  - radiality proxy
  - modularity
  - triadic closure

### `DERIVED`

- computed from transforms, projections, or ordered-structure proxies
- examples:
  - spectral coordinates
  - PCA symmetry proxy
  - chirality proxy
  - translation-symmetry proxy

### `SPECULATIVE`

- operator-facing hypothesis only
- may be visually suggestive
- must not be reported as evidence without a score and method

### `OPERATOR_ASSERTED`

- used for graph facts or annotations introduced by an operator
- not equivalent to a computed geometry result
- may later be supported or weakened by measurement

### `OPERATOR_REFINED`

- used when an operator revises an existing graph fact, memode, or annotation
- remains attributable to the edit history rather than being promoted to observed geometry automatically

### `AUTO_DERIVED`

- graph fact produced by EDEN-side ingest, retrieval, or update logic
- still distinct from geometry evidence labels

## Measurement vs assertion

- A geometry score is a measurement.
- A manually added edge is an assertion unless and until measurement supports it.
- A memode assertion is a structured operator claim about a reusable motif.
- A coordinate-mode switch is only a rendering change.

## Forbidden shortcuts

- a force-layout circle is not evidence of circular structure
- a pleasing radial rendering is not proof of spoke-ness
- a mirrored screenshot is not proof of reflection symmetry
- “sacred” language must never substitute for score + method + slice provenance
- an operator-added edge is not automatically `OBSERVED`
- a layout shift with unchanged topology must never be described as a graph mutation

## Required provenance for a geometry claim

- score
- method
- slice
- sample size
- whether it is `OBSERVED`, `DERIVED`, or `SPECULATIVE`
- whether it survives at least one ablation, if an ablation is available

## Required provenance for an observatory mutation

- action type
- target ids
- before state
- proposed state
- committed state
- operator label
- evidence label
- rationale
- measurement method
- confidence
- revert linkage when applicable
