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

## What the membrane does

- strips control characters
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
