# Turn Loop And Membrane

## Direct v1 loop

1. Receive operator input.
2. Retrieve candidates from the persisted memgraph.
3. Assemble the bounded active set and prompt context.
4. Deliberate (Talmud layer): check query coverage against the knowledge graph, surface dissenting positions, traverse edges from activated memes, retrieve precedent from prior turns. Report coverage gaps honestly.
5. Generate Adam’s response through the selected backend.
6. Apply the membrane to the raw model output.
7. Persist turn data, active set snapshot, trace, and membrane events.
8. Accept explicit feedback.
9. Update graph channels and derive new memes/memodes from feedback.

## Session-start graph wake-up audit

- session start can run an explicit wake-up audit before the first operator turn
- phase 1 is legacy knowledge normalization:
  - it is limited to knowledge rows whose graph state is still missing author/work information nodes or typed informational edges
  - deterministic relation extraction runs first
  - when the live backend is MLX and the local model is ready, Adam-identity JSON review is enabled by default and can refine those candidate relations before persistence
  - the review can still be disabled explicitly via `EDEN_DISABLE_MLX_WAKEUP_REVIEW=1`, and deterministic repair remains the fallback when MLX is unavailable or abstains
- phase 2 is behavior taxonomy:
  - it audits bounded turn-attached behavior bundles from Adam responses and explicit feedback
  - it can strengthen first-order behavior memes and materialize bounded behavior memodes when at least two selected behavior memes plus qualifying support edges are present
  - the same default-on MLX gate controls whether Adam performs the bounded taxonomy review instead of deterministic selection
  - any `memeplex` output is report-only and does not become a first-class graph object in this pass
- phase 3 is coherence reweave:
  - it reviews a bounded candidate set of existing behavior memodes and selects the memodes Adam should wake through first
  - the selected memodes and their member memes are touched so activation/regard pressure reflects the new session's coherence pass
  - the pass is Adam-identity MLX by default when ready, with deterministic anchor selection as bounded fallback
- the wake-up audit is not part of Adam's operator-facing reply generation
- every run is recorded as visible trace:
  - `GRAPH_NORMALIZATION`
  - `GRAPH_TAXONOMY_AUDIT`
  - `GRAPH_COHERENCE_REWEAVE`
  - `GRAPH_WAKEUP_AUDIT`
- session metadata stores:
  - `session_graph_normalization`
  - `session_graph_taxonomy`
  - `session_graph_coherence`
  - `session_graph_wakeup`

## What the membrane does

- strips control characters
- strips recognized visible planning spills such as `<think>` blocks and `Thinking Process` scaffolds before persisting operator-facing text
- fails closed when a response is reasoning-only and does not contain a recoverable operator-facing answer
- enforces a sectioned `Answer / Basis / Next Step` response contract when needed
- clamps excessive response length
- records visible membrane events into persistent storage

## What the membrane does not do

- hidden planning
- latent policy search
- inaccessible chain-of-thought exposure
- silent re-ranking after operator-visible scoring

## Prompt assembly inputs

- constitutional seed
- retrieved active-set items, including direct `document_chunks` recall plus document-backed evidence blocks with explicit provenance and page/excerpt context when available
- deliberation context: relevant knowledge memes, dissenting positions, connected concepts via edge traversal, coverage assessment, precedent turns
- recent feedback summaries
- bounded recent turn history

## Operator-visible trace

The TUI and exports surface:

- selected active-set members
- semantic similarity
- activation
- regard total
- session bias
- explicit feedback relevance
- scope and membrane penalties
- membrane events and prompt assembly summary
