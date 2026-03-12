# TUI Spec

The TUI remains the primary EDEN runtime surface in v1.2.

## Boot flow

Live dialogue boot:

- EDEN opens directly into a chat session surface
- if a previous session exists, EDEN resumes the latest persisted session automatically
- if no session exists yet, EDEN creates a blank experiment/session automatically
- the top action bus remains available:
  - menu actions:
    - `Toggle Aperture Drawer`
    - `Ingest PDF / Doc`
    - `Review Last Reply`
    - `Open Conversation Log`
    - `Open Conversation Atlas`
    - `Tune Session`
    - `Start New Session`
    - `Continue Latest`
    - `Start Blank Eden`
    - `Start Seeded Eden`
    - `Prepare Local Model`
    - `Open Browser Observatory`
    - `Export Artifacts`
    - `Open Utilities Deck`
    - `Help`
  - persistent quick buttons:
    - `Ingest Document`
    - `Open/Close Aperture`
  - layout:
    - full-width action select
    - separate quick-action row to avoid wrapped/clipped menu rendering
- default MLX model storage remains under `models/` in the repo root

Session-start modal:

- explicitly labeled session-start controls
- session title:
  - free typing remains allowed
  - adjacent recent-title selector is populated from persisted session titles
- inference mode:
  - `manual`
  - `runtime_auto`
  - `adam_auto`
- budget mode:
  - `tight`
  - `balanced`
  - `wide`
- manual bounded fields:
  - `temperature`
  - `max_output_tokens`
  - `top_p`
  - `repetition_penalty`
  - `retrieval_depth`
  - `max_context_items`
  - `response_char_cap`
  - `Profile Summary` reflects the clamped request values that will actually be persisted
  - `low_motion`
  - `debug`

## Chat screen

Primary split:

- left primary dialogue bay:
  - scrolling dialogue tape with persisted Brian / Adam turn boxes for the active session
  - static chiaroscuro-shaded transcript cards; decorative interior glyph bands are no longer rendered inside the chat text surface
  - live Brian draft box when the composer is loaded
  - inline reply-review strip for pending/reviewed turn state
  - typed inline review flow:
    - verdict code input: `A`, `E`, `R`, `S`
    - confirm input: `Y` + `Enter` to submit
    - explanation field appears for `A` / `E` / `R`
    - corrected-text field appears for `E`
  - multiline `TextArea` composer for Brian the operator with strong focus styling
  - message-input hint surface directly under the composer; `Ctrl+S` sends
  - keyboard-scrollable tape container so the operator can move up/down through the session history
- right secondary telemetry bay:
  - enlarged slower-pulsing signal field / memgraph bus with explicit symbol legend and live update explanation
  - enlarged aperture / active-set slice that speaks directly to the bus lanes: docs, knowledge memes, behavior memes, memodes, and relation read
  - lower thinking / reasoning slice
- bottom runtime strip:
  - merged runtime/event chyron with loop phase, active-set summary, feedback state, transcript pointer, and latest event flow

Wide aperture drawer:

- toggled from the action menu or `F8`
- occupies the top band of the screen when open
- renders a wider natural-language scan of the active set, persistent anchors, and live heat
- collapses back to the compact telemetry stack when closed
- on compact terminals, `F8` switches the live surface into an aperture-focused view instead of opening the wide top drawer; `Esc` returns to the dialogue composer

Secondary surfaces:

- `Deck` modal:
  - `Inference Circumstances / Budget`
  - graph telemetry
  - bounded history
  - Qwen thinking / reasoning
  - aperture / active set
  - cogitation / decision trace
  - corpus-intake guidance and status
  - `Blank Eden`, `Seeded Eden`, `Resume Latest`
  - `New Session`, low-motion toggle, debug toggle, and look selector
- `Ingest` modal:
  - absolute document path
  - operator framing prompt that is indexed prior to later retrieval
  - keyboard-first submit / cancel flow
- `Review` action:
  - focuses the inline reply-review inputs under Adam's latest answer
- `Conversation Atlas` modal:
  - `all_texts` root shelf over every persisted session transcript
  - relational lenses for folders, tags, experiments, and experiment modes
  - two-column layout:
    - left filter rail for search, sort, lens, facet filter, taxonomy projections, and atlas status
    - main work column for session list, selected-session preview, folder/tags editor, taxonomy actions, and session actions
  - search + facet filter + sort over saved sessions
  - selected-session preview with recent turns and feedback excerpts sits directly under the session list
  - metadata editor keeps the virtual `folder` path plus multi-value `tags`, but the instructional editor panel is removed
  - direct `Open Transcript`, `Save Taxonomy`, `Resume Session`, `Refresh`, and `Close` actions remain in the work column

## Design contract

- fixed telemetry panes, but the prime dialogue tape itself scrolls
- amber-on-dark remains the default operator grammar, while Deck exposes a persisted `Typewriter Light` look for paper-and-ink terminal reading
- the prime screen now refreshes on state changes instead of a constant whole-screen repaint loop; decorative chat shading is static rather than animated
- dialogue-first prime surface: visible transcript and composer dominate the left column; telemetry stays visible but secondary on the right
- live-session boot is the default path; the app no longer lands on a launcher before chat opens
- session and utility actions now live in the keyboard-executable top action bus instead of left-column buttons
- normal entry path is `.venv/bin/python -m eden` or `.venv/bin/python -m eden app`
- shell flags remain optional overrides; the normal runtime contract is repo-local MLX
- the action bus exposes keyboard-focusable menu + quick buttons, while Live Contract reports model readiness, active session, and focus state
- choosing an action from the top action `Select` executes it immediately; `Enter` on a focused action menu executes the currently selected action and duplicate dispatch is suppressed
- the Action Bus now separates menu focus from active work: `menu_focus` reflects the current `Select` value, while long-running observatory work surfaces a phase-based progress bar plus accurate elapsed time
- `Open Browser Observatory` resets the runtime menu back to its neutral review focus after dispatch so repeat observatory launches stay selectable instead of getting stuck on the same `Select` value
- multiline composition is first-class
- `Esc` returns focus to the composer, and printable keys pressed outside editable widgets are routed back into the composer automatically
- the dialogue tape is scrollable and can be navigated by focusing it, then using `Up`, `Down`, `PageUp`, `PageDown`, `Home`, or `End`
- operator turns are persisted and graph-ingested as `Brian the operator: ...`
- MLX/Qwen model-emitted thinking is surfaced as a dedicated panel instead of leaking into the main Adam response
- the signal field is explicitly explanatory: it renders a live orthographic memgraph slice using active-set nodes, recall anchors, recent trace events, and ingest roots while remaining separate from any claim about hidden activations
- the memgraph bus keeps an always-visible legend for its glyph vocabulary so the operator can read it as a tool rather than decorative telemetry
- the aperture is rendered as both a compact but more verbose bus-to-active-set read and a full-width pull-down readable scan with natural-language summaries plus a ranked queue
- the prime surface keeps transcript, reply review, composer, memgraph, aperture, thinking, and the merged runtime/event chyron visible while the operator types; Deck still carries the detailed trace and budget surfaces
- on compact terminals, the prime surface prioritizes transcript + composer + chyron and hides the right telemetry stack until the operator explicitly opens aperture/deeper surfaces
- feedback is integrated directly into the primary dialogue bay through an inline reply-review strip under Adam's latest answer
- inline review uses typed `A` / `E` / `R` / `S` codes plus `Y` confirmation, but still reuses the graph-backed feedback path and therefore updates regard, reward, risk, and edit channels
- `Review` only jumps into the inline strip when Adam has already replied; otherwise the composer keeps focus and the status line explains that there is nothing to review yet
- conversation logs are written as markdown artifacts under `exports/conversations/` for the active session and surfaced on-screen plus via `Open Conversation Log`
- the conversation atlas treats saved sessions as a relational transcript library: all logs remain under the single export root while folder/tag organization is stored as session metadata and projected in the atlas
- conversation boundaries are explicit through the live contract, transcript state, and inline review flow: ask or ingest, review when Adam answers, and end by opening a new session
- budget changes remain visible, but now live in Deck instead of the prime chat pane
- latest-session resume restores the latest persisted session surface without forcing a new session flow first
- keyboard-only navigation is supported through top action-bus focus, `Enter` execution, `Tab` / `Shift+Tab` focus cycling, and the function-key bindings
- corpus ingest supports a framing prompt whose phrases are graph-indexed as persistent document-conditioning material
- export actions report the artifact directory path in the status surface so the operator can find the generated files without guesswork
- observatory launch status is explicitly phased in the Action Bus (`queued`, `ensuring server`, `exporting payloads`, `opening browser`); elapsed time is real elapsed time, not an ETA claim

## Budget panel contents

- current profile name
- requested mode and effective mode
- retrieval depth
- max context items
- reserved output tokens
- prompt budget estimate
- current user tokens and characters
- remaining estimated user allowance
- count method
- response char cap
- budget pressure
- active-set contribution
- history contribution
- allowance-change reasons

## Key bindings

- `F1`: help
- `Ctrl+S`: send turn
- `F2`: export observability artifacts
- `F3`: ensure/open local observatory
- `F4`: toggle low-motion in the current session request
- `F5`: open the new-session inference-profile flow
- `F6`: open the utilities deck
- `F7`: focus the inline reply-review strip
- `F8`: toggle the full-width aperture drawer
- `F9`: open document ingest with framing prompt
- `F10`: open the conversation atlas
- `Esc`: return focus to the composer on the main chat screen
