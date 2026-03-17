# Canonical Ontology

## First-class objects

- `Agent`: runtime persona profile and identity anchor. ADAM is the first agent.
- `Session`: operator-delimited run context within the persistent Adam graph.
- `Turn`: one user input plus one Adam response and associated trace.
- `Document`: ingested external source with provenance.
- `Meme`: first-class replicable semantic or behavioral unit.
- `FeedbackEvent`: explicit operator judgment over a turn.
- `TraceEvent`: operator-visible runtime event.
- `MembraneEvent`: post-generation event emitted by the output membrane.
- `ExportArtifact`: emitted graph/basin outputs plus manifests.
- `Config / graph metadata`: run-level settings and identity.
- `MeasurementEvent`: persistent record of observatory-originated measurement, edit, annotation, ablation, or revert.

## Derived objects

- `Memode`: derived second-order structure built from at least two memes plus a connected qualifying semantic support subgraph.
- `ActiveSet snapshot`: bounded retrieval result for a turn.
- `Basin summary`: trajectory and attractor summary derived from turns and active sets.
- `Cluster / motif summary`: derived semantic neighborhood label or graph-health summary. Clusters are not memodes.

## Edge semantics used in v1.2

- `BELONGS_TO_AGENT`
- `BELONGS_TO_SESSION`
- `DERIVED_FROM`
- `OCCURS_IN`
- `CO_OCCURS_WITH`
- `CONTEXTUALIZES_DOCUMENT`
- `AUTHOR_OF`
- `INFLUENCES`
- `REFERENCES`
- `MATERIALIZES_AS_MEMODE`
- `MEMODE_HAS_MEMBER`
- `FED_BACK_BY`

## Domain split

- `behavior`: constitutional constraints, persona scaffolds, feedback-derived adjustments, response behavior
- `knowledge`: document-derived content and user-provided informational content

## V1 interpretation

- Memes are the persistent base primitive.
- Memodes are semantically derived, though they may be materialized and cached in the store.
- The memode admissibility floor is graph-theoretic, not conceptual completeness: every selected meme must participate in at least one qualifying support edge and the support subgraph must be connected.
- Knowledge relations and memode relations are not interchangeable. Informational edges such as `AUTHOR_OF`, `INFLUENCES`, and `REFERENCES` may be auto-derived and persisted, but they do not silently become memode support unless they are admitted by the qualifying support-edge rules.
- Semantic clusters are derived summaries over meme-only semantic neighborhoods. They may carry manual labels, but they are never auto-promoted into memodes.
- Regard acts over memes and memodes, not over tokens.
- `The hum`, when referenced, names a low-bandwidth continuity artifact rather than a first-class runtime object. It is not identical to the active set, turn history, full graph, basin summary, cluster summary, or observatory payload.
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
- manual cluster labels are attributable measurement annotations over derived cluster instances, not silent topology rewrites
- measurement events are the provenance bridge between observation, mutation, and later runtime effects
