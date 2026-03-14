# How To Use Adam TUI

This is the operator manual for the current Adam terminal interface as verified on March 9, 2026.

## What To Do In The First Two Minutes

1. Launch Adam with `.venv/bin/python -m eden`.
2. Look for `Message Input`.
3. Type a question.
4. Press `Ctrl+S`.
5. Read Adam's reply in `Adam Dialogue`.
6. Press `Esc` if you want to get back to typing immediately.
7. Press `F9` before the first turn if you want to load a document first.

If the terminal is small, Adam now switches into a compact layout. In compact mode the transcript and composer stay visible, and the `Message Input` panel repeats the critical keys.

## What Each Panel Is For

### Action Bus

The top control strip.

Use it when you want to:

- choose a command from the menu
- ingest a document quickly
- open or close aperture

If focus is on the action menu, `Enter` runs the selected action.

### Live Contract

The runtime status panel beside the action bus on wide terminals.

It tells you:

- which backend is active
- which session is loaded
- what conversation stage you are in
- which control currently has focus

If you lose track of what to do next, read the `note=` line or press `Esc` to get back to the composer.

### Adam Dialogue

The scrolling transcript tape.

It shows:

- your saved turns
- Adam's saved replies
- stored review events
- your current unsent draft when the composer has text

When the tape has focus and there is enough history to scroll, `PageUp` and `PageDown` move through it.

### Reply Review

The inline feedback strip that appears after Adam replies.

Use it to judge the latest answer:

- `A` = accept
- `E` = edit
- `R` = reject
- `S` = skip

Press `Enter` to move into the next required field.

When the last required field is filled, press `Enter` again to submit.

Important:

- `A`, `E`, and `R` require explanation
- `E` also requires corrected text
- `Shift+Enter` inserts a newline inside explanation or corrected text
- if there is no Adam reply yet, `F7` now tells you that instead of pretending the review form exists

### Message Input

The composer.

This is the main place to work.

Verified behavior:

- focus starts here on launch
- printable keys typed outside menus jump back here automatically
- `Esc` returns focus here
- `Ctrl+S` sends the current draft

### Memgraph Bus

The live glyph-based telemetry panel on wide terminals.

Use it when you want a fast visual read of:

- document roots
- active knowledge and behavior memes
- memodes
- recent graph mutations

It is an operator-facing abstraction, not a claim about hidden model activations.

### Aperture / Active Set

The readable explanation of what the runtime has surfaced for the current turn.

Use it to answer practical questions like:

- did my ingest take effect?
- is this turn pulling more from documents or behavior?
- what is being kept hot right now?

Verified terminal behavior:

- wide terminals: `F8` opens a full-width aperture drawer at the top
- compact terminals: `F8` swaps the main view into an aperture-focused screen and `Esc` returns to dialogue

### Thinking / Reasoning

The panel for model-emitted reasoning text plus the current trace summary.

Use it when you want to inspect how the runtime is weighting the turn. This is visible model output only.

### Runtime / Event Chyron

The bottom status band.

Use it to confirm:

- loop phase
- document count
- active-set count
- pressure level
- latest event summary

### Deck

Open with `F6`.

Use it for the deeper surfaces that do not need to stay on the prime screen:

- budget details
- graph telemetry
- bounded history
- detailed trace
- ingest help
- session and launch utilities

Press `Esc` to close it.

## Focus And Recovery

The app is keyboard-first.

Verified focus rules:

- Launch starts in the composer.
- `Tab` cycles through interactive controls.
- On a no-reply screen the verified order is:
  - composer
  - action menu
  - ingest button
  - aperture button
  - dialogue tape
  - composer
- After Adam replies, the inline review fields join the tab order ahead of the composer.
- `Esc` returns to the composer.

Best recovery rule:

- If focus feels wrong, press `Esc`.

## How To Start A Conversation

1. Type in `Message Input`.
2. Press `Ctrl+S`.
3. Read Adam's reply in `Adam Dialogue`.
4. Either:
   - review it immediately in the inline strip
   - or press `Esc` and continue chatting

After a send, Adam moves focus into the review strip on purpose. That is useful if you want to score the reply right away.

## How To Ingest Documents

1. Press `F9`.
2. Enter an absolute path.
3. Write or edit the framing note.
4. Confirm ingest.

What changes after ingest:

- the status line reports the document title plus meme/memode counts
- the conversation stage changes to `Document armed`
- aperture shows `docs=1` and the current document root

## How Export, Observatory, Archive, Review, And Deck Work

### Export

- Press `F2`.
- Adam writes artifacts under `exports/<experiment_id>/`.
- The status message now includes the export directory path.

### Observatory

- Press `F3`.
- Adam starts or reuses a local server and opens:
  - `http://127.0.0.1:<port>/<experiment_id>/observatory_index.html`

Use observatory when you want the browser surfaces, not when you just want to keep chatting.

### Archive

- Press `F10`.
- Search saved sessions.
- Edit one virtual folder path plus comma-separated tags.
- Resume or close.

Important:

- archive folders and tags are relational metadata
- they do not move or duplicate transcript files on disk

### Review

- Press `F7` after Adam replies.
- Fill verdict, explanation, corrected text if needed, then confirm.

### Deck

- Press `F6`.
- Use it for deep inspection, not for normal chatting.

## Where Files Go

Verified locations:

- session conversation logs: `exports/conversations/<experiment>/<session>.md`
- observability artifacts: `exports/<experiment_id>/`

Typical export files:

- `graph_knowledge_base.html`
- `behavioral_attractor_basin.html`
- `geometry_lab.html`
- `measurement_ledger.html`
- `observatory_index.html`

## Practical Advice

- If you are new, ignore most telemetry at first. Stay in `Message Input`, send one turn, then decide whether you need `F9`, `F6`, `F8`, or `F10`.
- If the terminal feels cramped, keep working in compact mode and use `F6` or `F8` only when you need inspection.
- If you want to find a saved conversation later, use `F10` rather than digging through files by hand.
