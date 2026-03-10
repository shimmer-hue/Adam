# User Journeys

This file records the main operator journeys that were re-run against the live TUI on March 9, 2026.

Evidence basis:

- real PTY launch at `80x24`
- pilot-driven app runs at `80x24`, `120x30`, and `140x40`
- `tests/test_tui_smoke.py`

## Journey 1 - First Launch And Orientation

Purpose:

- Understand what appears on launch and what to do first.

Steps:

1. Run `.venv/bin/python -m eden` or `.venv/bin/python -m eden app`.
2. Wait for the live chat surface to boot. Adam resumes the latest session if one exists; otherwise it creates a live blank session.
3. Look for `Message Input`. That is the place to type.

Expected result:

- Focus starts in the composer.
- On wide terminals, you see:
  - `Action Bus` at the top
  - `Adam Dialogue` and `Message Input` on the left
  - `Memgraph Bus`, `Aperture / Active Set`, and `Thinking / Reasoning` on the right
  - `Runtime / Event Chyron` at the bottom
- On compact terminals, the right telemetry stack is hidden by default so the transcript and composer stay visible.

Verified notes:

- The `Message Input` panel repeats the critical first-run keys on compact terminals:
  - `Ctrl+S`
  - `F9`
  - `F5`
  - `F6`
  - `F10`
- The launch stage note is visible in the composer hint:
  - `Start here: type below, press Ctrl+S to send, or press F9 to ingest first.`

Caveats:

- The stock footer still truncates later function-key labels on narrow terminals.
- Use `F1` or the `Message Input` hint if the footer does not show everything you need.

## Journey 2 - Start A Basic Conversation

Purpose:

- Send a normal prompt and continue the session.

Steps:

1. Type in the composer.
2. If focus is not in the composer, press `Esc`.
3. Press `Ctrl+S`.

Expected result:

- Your prompt is added to `Adam Dialogue`.
- Adam's reply appears above the composer in the same transcript tape.
- A markdown conversation log is written for the active session.
- Focus moves to the inline review strip so you can judge Adam's reply immediately.

Verified notes:

- After a reply exists, focus moves to the review strip.
- `Esc` returns focus to the composer if you want to keep chatting instead of reviewing first.
- `F7` jumps to the review strip again later.

Caveats:

- If you press `F7` before Adam has replied, the app now keeps focus in the composer and tells you to send a turn first.

## Journey 3 - Ingest A Document Before The First Turn

Purpose:

- Load a document into the current experiment before asking Adam about it.

Steps:

1. Press `F9`.
2. In `Ingest Bay`, type an absolute file path into the first field.
3. Edit the framing prompt if needed.
4. `Tab` to `Ingest Into Memgraph`.
5. Press `Enter`.
6. Return to the composer and ask a question about the document.

Expected result:

- The modal closes automatically.
- The status line reports the ingested title and the meme/memode counts.
- The conversation stage changes from generic start guidance to `Document armed: ...`.
- The aperture surface shows `docs=1` and the document title.

Verified notes:

- The path field is focused when the modal opens.
- The framing prompt is plain text; there is no file picker in this pass.
- Verified with a PDF ingest path.

Caveats:

- On the mock backend, the reply quality is not a proof of real MLX retrieval quality.
- What was verified here is the ingest workflow, the state change, and the document's presence in the active-set surfaces.

## Journey 4 - Open And Read Aperture / Active Set

Purpose:

- Inspect what the runtime has surfaced for the current turn.

Wide-terminal steps:

1. Press `F8`.
2. Read the full-width aperture drawer at the top of the screen.
3. Press `F8` again to close it.

Compact-terminal steps:

1. Press `F8`.
2. The live screen swaps into an aperture-focused view.
3. Press `Esc` or `F8` again to return to dialogue.

Expected result:

- The aperture view shows:
  - whether the turn is knowledge-led or behavior-led
  - document presence
  - ranked pulls
  - recall anchors
  - memode counts

Verified notes:

- After document ingest and a turn, the aperture panel reported `docs=1` and updated behavior/memode counts.
- On wide terminals, `#aperture_drawer_panel` opens and closes.
- On compact terminals, `F8` hides the dialogue surface and shows the aperture path, then `Esc` returns to the composer.

Caveats:

- Simultaneous dialogue plus right-hand telemetry still wants a wider/taller terminal.

## Journey 5 - Open Observatory / Live Telemetry

Purpose:

- Move from terminal chat into the local browser observability surface.

Steps:

1. Press `F3`.
2. Wait for the status message.
3. Open the provided local URL if the browser does not appear automatically.

Expected result:

- The TUI starts or reuses the observatory server.
- It opens the current experiment's `observatory_index.html`.
- The verified URL shape is:
  - `http://127.0.0.1:<port>/<experiment_id>/observatory_index.html`

Verified notes:

- The observatory URL returned `HTTP 200` in this pass.
- The observatory is a browser handoff, not an embedded TUI pane.

## Journey 6 - Export Session Artifacts

Purpose:

- Write the current experiment's browser/HTML artifacts to disk.

Steps:

1. Press `F2`.
2. Read the status message for the export directory.

Expected result:

- The TUI writes artifacts under `exports/<experiment_id>/`.
- The status message now includes the directory path, not just filenames.

Verified files in this pass:

- `graph_knowledge_base.html`
- `behavioral_attractor_basin.html`
- `geometry_lab.html`
- `measurement_ledger.html`
- `observatory_index.html`
- JSON diagnostics and measurement payloads

Caveats:

- Session conversation logs live separately under `exports/conversations/<experiment>/...md`.

## Journey 7 - New Session / Archive / Review / Deck

Purpose:

- Use the secondary controls that matter during normal operation.

### New Session

Steps:

1. Press `F5`.
2. Adjust the session profile if you want.
3. Press `Open Session`.

Expected result:

- A fresh session opens.
- Focus returns to the composer automatically.

### Archive

Steps:

1. Press `F10`.
2. Search or filter saved sessions.
3. Edit folder/tags if needed.
4. Use `Resume Session` or `Close`.

Expected result:

- `Conversation Atlas` opens as a modal.
- The archive path is keyboard-safe from both the menu and `F10`.
- Resuming a session returns you to chat with that session loaded.

Verified notes:

- The archive bug in the `F10`/binding path was repaired in this pass.

### Review

Steps:

1. After Adam replies, press `F7` if focus is elsewhere.
2. Type one verdict code:
  - `A`
  - `E`
  - `R`
  - `S`
3. Type `Y` in confirm.
4. Press `Enter`.

Expected result:

- `A`, `E`, and `R` require explanation.
- `E` also requires corrected text.
- The review is written into feedback storage and shows in the transcript.

### Deck

Steps:

1. Press `F6`.
2. Read the detailed budget, telemetry, history, and ingest panels.
3. Press `Esc` to close.

Expected result:

- `Deck` opens as a modal and dismisses cleanly back to chat.

## Journey 8 - Keyboard-Only Operator Flow

Purpose:

- Work entirely without the mouse.

Verified focus behavior:

- Initial launch focus: `composer_input`
- No-reply tab order on the live chat screen:
  1. composer
  2. action menu
  3. ingest button
  4. aperture button
  5. dialogue tape
  6. composer
- After an Adam reply, the inline review fields enter the tab order ahead of the composer.

Verified key behaviors:

- `Tab` moves through interactive controls.
- `Enter` on the action menu executes the selected item.
- `Esc` returns to the composer.
- `PageUp` and `PageDown` scroll the dialogue tape when it has focus and enough content to scroll.
- `Esc` closes `Deck`, `Ingest Bay`, `Conversation Atlas`, and compact aperture view.

Recovery notes:

- If you are not sure where focus is, press `Esc`.
- If you opened compact aperture view by mistake, press `Esc` once to get back to dialogue.
