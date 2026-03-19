# Turn Loop And Membrane

## Direct v1 loop

1. Receive operator input.
2. Retrieve candidates from the persisted memgraph.
3. Assemble the bounded active set and prompt context.
4. Generate Adam’s response through the selected backend.
5. Apply the membrane to the raw model output.
6. Persist turn data, active set snapshot, trace, and membrane events.
7. Accept explicit feedback.
8. Update graph channels and derive new memes/memodes from feedback.

## Session-start graph wake-up audit

- session start can run an explicit wake-up audit before the first operator turn
- phase 1 is legacy knowledge normalization:
  - it is limited to knowledge rows whose graph state is still missing author/work information nodes or typed informational edges
  - deterministic relation extraction runs first
  - the Adam-identity MLX review layer is opt-in only via `EDEN_ENABLE_MLX_WAKEUP_REVIEW=1`; without that flag, session start remains deterministic even when the live backend is MLX
  - when the flag is enabled on the MLX path, a bounded Adam-identity JSON review can refine those candidate relations before persistence
- phase 2 is behavior taxonomy:
  - it audits bounded turn-attached behavior bundles from Adam responses and explicit feedback
  - it can strengthen first-order behavior memes and materialize bounded behavior memodes when at least two selected behavior memes plus qualifying support edges are present
  - the same `EDEN_ENABLE_MLX_WAKEUP_REVIEW=1` opt-in gate controls whether Adam performs the bounded MLX taxonomy review instead of deterministic selection
  - any `memeplex` output is report-only and does not become a first-class graph object in this pass
- the wake-up audit is not part of Adam's operator-facing reply generation
- every run is recorded as visible trace:
  - `GRAPH_NORMALIZATION`
  - `GRAPH_TAXONOMY_AUDIT`
  - `GRAPH_WAKEUP_AUDIT`
- session metadata stores:
  - `session_graph_normalization`
  - `session_graph_taxonomy`
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
- retrieved active-set items, including document-backed evidence blocks with explicit provenance and page/excerpt context when available
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
