# Canonical Ontology

## First-class objects

- `Agent`: runtime persona profile and identity anchor. ADAM is the first agent.
- `Session`: operator-delimited run context within an experiment.
- `Turn`: one user input plus one Adam response and associated trace.
- `Document`: ingested external source with provenance.
- `Meme`: first-class replicable semantic or behavioral unit.
- `FeedbackEvent`: explicit operator judgment over a turn.
- `TraceEvent`: operator-visible runtime event.
- `MembraneEvent`: post-generation event emitted by the output membrane.
- `ExportArtifact`: emitted graph/basin outputs plus manifests.
- `Config / Experiment metadata`: run-level settings and identity.
- `MeasurementEvent`: persistent record of observatory-originated measurement, edit, annotation, ablation, or revert.

## Derived objects

- `Memode`: derived second-order structure built from at least two memes plus at least one relation.
- `ActiveSet snapshot`: bounded retrieval result for a turn.
- `Basin summary`: trajectory and attractor summary derived from turns and active sets.
- `Cluster / motif summary`: graph-health and attractor summaries.

## Edge semantics used in v1

- `BELONGS_TO_AGENT`
- `BELONGS_TO_SESSION`
- `DERIVED_FROM`
- `OCCURS_IN`
- `CO_OCCURS_WITH`
- `MATERIALIZES_AS_MEMODE`
- `FED_BACK_BY`

## Domain split

- `behavior`: constitutional constraints, persona scaffolds, feedback-derived adjustments, response behavior
- `knowledge`: document-derived content and user-provided informational content

## V1 interpretation

- Memes are the persistent base primitive.
- Memodes are semantically derived, though they may be materialized and cached in the store.
- Regard acts over memes and memodes, not over tokens.
- Active-set assembly mixes behavior and knowledge but keeps their provenance visible.

## Practical memode ladder for v1.2

- `meme`: local semantic-behavioral part
- `memode`: reusable selected subassembly or historically stabilized motif
- `persona`: persistent assembly ecology of memodes

This patch treats a memode as more than a pairwise relation or a UI label. In practical EDEN terms, a memode is an assembly-stabilized, temporally thick causal motif whose identity may be distributed across a structured neighborhood.

## Operator intervention semantics

- observatory measurements can produce new persistent facts with provenance
- operator assertions and operator refinements remain distinguishable from auto-derived facts
- a known memode can be asserted from a selected node set and later refined
- measurement events are the provenance bridge between observation, mutation, and later runtime effects
