# TUI Spec

The TUI remains the primary EDEN runtime surface in v1.2.

## Boot flow

Live dialogue boot:

- EDEN opens directly into a chat session surface
- if a previous session exists, EDEN resumes the latest persisted session automatically
- if no session exists yet, EDEN creates the first session on the persistent Adam graph automatically
- the top action strip remains available:
  - numbered actions:
    - `01 Review Last Reply`
    - `02 Open Conversation Log`
    - `03 Open Conversation Atlas`
    - `04 Tune Session`
    - `05 Start New Session`
    - `06 Continue Latest`
    - `07 Prepare Local Model`
    - `08 Open Browser Observatory`
    - `09 Export Artifacts`
    - `10 Open Utilities Deck`
    - `11 Help`
    - `12 Ingest PDF / Doc`
    - `13 Toggle Aperture Drawer`
    - `14 Toggle Runtime Chyron`
  - layout:
    - single focusable top action shelf with a multi-row button grid and integrated runtime/status lines
    - no separate quick-action row or dropdown surface
  - interaction:
    - `Tab` / `Shift+Tab` focuses the strip
    - `Left` / `Right` moves selection
    - typing digits jumps to an action number
    - `Enter` executes the currently selected action
    - clicking a numbered action executes it directly
- default MLX model storage remains under `models/` in the repo root

Session-start modal:

- explicitly labeled session-start controls
- session title:
  - free typing remains allowed
  - adjacent recent-title selector is populated from persisted session titles
  - `Tune Session` reuses the same title field and recent-title selector so the active session can be renamed in-place
- inference mode:
  - `manual`: operator-specified bounded values are clamped and used directly
  - `runtime_auto`: EDEN chooses a bounded preset per turn from visible runtime heuristics
  - `adam_auto`: mock backend uses the Adam-guided bounded picker; current MLX path persists the request but resolves as `runtime_auto`
- budget mode:
  - `tight`: leanest prompt-budget envelope for smaller/faster turns
  - `balanced`: middle preset for default retrieval/output breadth
  - `wide`: larger prompt-budget envelope for deeper retrieval and longer replies within safe local bounds
- manual bounded fields:
  - `temperature`: sampling randomness; lower is steadier, higher is more varied
  - `max_output_tokens`: hard generation-token cap; lower is shorter, higher allows longer continuations; current manual clamp is `128..4096`, and the balanced default is `1200`
  - `top_p`: nucleus-sampling cutoff; lower narrows token choice, higher widens it
  - `repetition_penalty`: discourages token reuse; higher suppresses loops more aggressively
  - `retrieval_depth`: number of recall candidates inspected before prompt assembly; lower is narrower/faster, higher searches deeper
  - `max_context_items`: number of retrieved items allowed into the active prompt; lower keeps the aperture tighter, higher spends more prompt budget
  - `history_turns`: number of recent Brian/Adam turns requested for prompt history; lower keeps conversation context tighter, higher preserves more continuity at added prompt-budget cost; current manual clamp is `1..256`
  - EDEN trims the actually injected recent-history block to the active prompt-budget envelope after active set, feedback, and operator text are accounted for, so requested history and injected history can differ on dense turns
  - `response_char_cap`: post-generation operator-facing character cap; lower forces tighter replies, higher allows fuller answers; current manual clamp is `600..12000`, and the balanced default is `5200`
  - `Profile Summary` reflects the clamped request values that will actually be persisted
  - `low_motion`: `On` reduces terminal animation only; it does not change retrieval or sampling
  - `debug`: persisted session/profile flag surfaced in runtime status; current MLX path does not alter sampler or retrieval behavior from this toggle yet

## Chat screen

Primary split:

- left primary dialogue bay:
  - longer scrolling dialogue tape with persisted Brian / Adam turn boxes for the active session
  - Adam transcript cards reconstruct their readable text from raw stored turn output under a larger bounded display cap, so older turns clipped by a smaller generation-time `response_char_cap` remain readable in the tape without rewriting graph history
  - static alternating transcript cards for faster scanning: Brian cards sit on a true-black field and Adam cards on a slightly lifted rose-black shade; decorative interior glyph bands are no longer rendered inside the chat text surface
  - live Brian draft box when the composer is loaded
  - multiline `TextArea` composer for Brian the operator with strong focus styling
  - pasted text must remain in the composer until Brian explicitly sends it; trailing newline bursts from paste are treated as composer newlines rather than auto-submitting the turn
  - keyboard-scrollable tape container so the operator can move up/down through the session history
- right secondary telemetry bay:
  - top-row compact context-budget strip between the action shelf and live turn-status strip on wide terminals, so the operator can always read EDEN's current used/remaining prompt-budget estimate without opening Deck
  - top-row live turn-status strip between the compact context-budget strip and aperture panel on wide terminals, so generation/finalization phases remain visible while Adam is composing
  - wider top-right aperture / active-set slice beside the action shelf on wide terminals, so the current retrieval surface stays visible without consuming the lower telemetry stack and the action shelf does not waste dead space
  - enlarged slower-pulsing signal field / memgraph bus with explicit symbol legend and live update explanation
  - lower reasoning/feed slice with three operator lenses:
    - `Reasoning`: response material first, then any non-boilerplate visible reasoning signal, plus runtime condition, membrane record, and live consideration trace
      - while MLX/Qwen is still generating and emits visible reasoning text, this lens updates live from the streaming model output and marks the panel title as `[LIVE]`
    - `Chain-Like`: numbered beats cut from the operator-facing answer, with optional non-boilerplate reasoning residue and live assembly anchors
    - `Hum Live`: bounded hum entries, `[HUM_STATS]`, `[HUM_METRICS]`, `[HUM_TABLE]`, and carryover/memory anchors derived from the persisted hum artifact; on first-turn / no-recurrence states it remains seed-state rather than inventing recurrence
    - focusable scroll viewport so longer reasoning or hum-live traces can be read in-place from the prime chat surface, directly beneath the memgraph bus
- bottom runtime drawer:
  - merged runtime/event chyron with loop phase, active-set summary, feedback state, transcript pointer, and latest event flow
  - hidden by default and revealed via `F11` from the bottom

Wide aperture drawer:

- toggled from the action strip or `F8`
- occupies a narrower top band of the screen when open
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
  - `Resume Latest`
  - `New Session`, low-motion toggle, debug toggle, and look selector
- `Ingest` modal:
  - absolute document path
  - operator framing prompt that is indexed prior to later retrieval
  - keyboard-first submit / cancel flow
- `Review` action:
  - focuses the inline explicit-feedback surface bound to Adam's latest answer while that answer is awaiting review
  - inline review applies graph-backed `accept` / `edit` / `reject` / `skip` feedback through the existing runtime API
- `Conversation Atlas` modal:
  - `all_texts` root shelf over every persisted session transcript
  - relational lenses for folders and tags over the same persistent graph
  - two-column layout:
    - left filter rail for search, sort, lens, facet filter, taxonomy projections, and atlas status
    - right work column with the session list at the top and a lower split:
      - metadata/editor pane on the lower left for `Folder`, a larger square-ish `Tags` editor, and taxonomy actions
      - selected-session preview pane on the lower right with richer session metadata, transcript path/state, recent turns, recent feedback, and session-scoped observatory references
      - the preview subpane scrolls independently so `Resume Session`, `Refresh`, and companion observatory controls remain visible at the bottom of the work column
  - search + facet filter + sort over saved sessions
  - metadata editor keeps the virtual `folder` path plus multi-value `tags`, but the instructional editor panel is removed
  - session preview exposes live/session-specific observatory affordances grounded in the existing browser observatory surface:
    - `Open Observatory` refreshes a session-scoped export and opens the GUI surface
    - `Turns API` opens the live session transcript endpoint
    - `Active Set API` opens the live session active-set endpoint
  - direct `Open Transcript`, `Save Taxonomy`, `Resume Session`, `Refresh`, and `Close` actions remain in the work column

## Design contract

- fixed telemetry panes, but the prime dialogue tape itself scrolls
- amber-on-dark remains the default operator grammar, while Deck exposes a persisted `Typewriter Light` look for paper-and-ink terminal reading
- the prime screen now refreshes on state changes instead of a constant whole-screen repaint loop; decorative chat shading is static rather than animated
- dialogue-first prime surface: visible transcript and composer dominate the left column; telemetry stays visible but secondary on the right
- the prime dialogue bay is intentionally longer than the secondary telemetry stack so more transcript remains visible at once
- live-session boot is the default path; the app no longer lands on a launcher before chat opens
- session and utility actions now live in the compact keyboard-executable top action strip instead of left-column buttons
- normal entry path is `.venv/bin/python -m eden` or `.venv/bin/python -m eden app`
- shell flags remain optional overrides; the normal runtime contract is repo-local MLX
- the action strip is a single focusable runtime control rather than a dropdown; it now owns the full topbar when the aperture drawer is closed
- choosing an action now means selecting it in the strip and pressing `Enter`, typing its number then pressing `Enter`, or clicking it directly
- the strip renders fully spelled-out numbered actions as brighter button-like chips and carries the runtime/session/progress lines directly beneath them
- the topbar also carries a dedicated live turn-status strip so the operator can see Adam move through preflight, prompt-ready, generating, finalizing, and review phases without losing the aperture surface
- `Open Browser Observatory` stays repeatable from the strip without forcing a reset back to review focus
- when the current graph already has an `observatory_index.html` shell, `Open Browser Observatory` should launch the browser immediately from that shell and continue refreshing payloads in the background rather than blocking browser open on a full export rebuild
- immediate observatory launches must preserve the current session scope by appending a session override in the browser URL instead of silently falling back to the stale session baked into the previous export shell
- multiline composition is first-class
- `Esc` returns focus to the composer, and printable keys pressed outside editable widgets are routed back into the composer automatically
- the dialogue tape is scrollable and can be navigated by focusing it, then using `Up`, `Down`, `PageUp`, `PageDown`, `Home`, or `End`
- the reasoning / hum-live viewport is also scrollable when focused, using the same navigation keys as the dialogue tape
- operator turns are persisted and graph-ingested as `Brian the operator: ...`
- MLX/Qwen model-emitted thinking is kept out of the main Adam response; the prime feed now combines response material, filtered visible reasoning/hum artifacts, runtime linguistic condition, membrane behavior, continuity, and active consideration telemetry, while suppressing prompt-mirror scaffolding and avoiding any claim about hidden reasoning
- the signal field is explicitly explanatory: it renders a live orthographic memgraph slice using active-set nodes, recall anchors, recent trace events, and ingest roots while remaining separate from any claim about hidden activations
- the memgraph bus keeps an always-visible legend for its glyph vocabulary so the operator can read it as a tool rather than decorative telemetry
- the aperture is rendered as both a compact top-right bus-to-active-set read and a wider pull-down readable scan with natural-language summaries plus a ranked queue; `docs=` in these summaries refers to unique document-backed active-set groups, not merely the latest ingest action
- the prime surface keeps transcript, composer, aperture, memgraph, and reasoning/feed lenses visible while the operator types; the standalone hum fact box is removed from the prime screen, while `Hum Live` now renders bounded hum entries, stats, metrics, and token-table carryover inside the feed lens
- on compact terminals, the prime surface prioritizes transcript + composer + runtime chyron trigger and hides the right telemetry stack until the operator explicitly opens aperture/deeper surfaces
- feedback is integrated inline inside the chat column through the explicit-feedback surface directly above the composer
- when the local MLX/Qwen backend emits visible reasoning incrementally, the prime `Reasoning` lens updates during generation from streaming model output rather than waiting for the completed turn artifact
- explicit review is collected there after each successful turn submission; `Review` / `F7` focuses the inline form only while Adam's latest reply is awaiting review
- once feedback is stored for the latest reply, the inline form collapses to a stored-feedback payload block showing verdict, timestamp, ids, explanation, and any corrected text until Adam answers again
- inline review reuses the graph-backed feedback path and therefore updates regard, reward, risk, and edit channels
- `Review` only focuses the inline form when Adam has already replied and that reply is still pending review; otherwise the composer keeps focus and the status line explains whether there is nothing new to review or the latest reply is already settled
- conversation logs are written as markdown artifacts under `exports/conversations/` for the active session and surfaced on-screen plus via `Open Conversation Log`
- the conversation atlas treats saved sessions as a relational transcript library: all logs remain under the single export root while folder/tag organization is stored as session metadata and projected in the atlas
- conversation boundaries are explicit through the top action shelf status lines, transcript state, pending inline review followed by a stored-feedback line, and new-session flow: ask or ingest, review when Adam answers, and end by opening a new session
- detailed budget changes remain visible in Deck, while the prime chat topbar carries a compact used/remaining context-budget estimate
- latest-session resume restores the latest persisted session surface without forcing a new session flow first
- keyboard-only navigation is supported through top action-strip focus, digit jump or `Left` / `Right` selection, `Enter` execution, `Tab` / `Shift+Tab` focus cycling, and the function-key bindings
- focused keyboard targets on the prime chat surface carry an explicit `>>` marker in their border title or button label, so `Tab` / `Shift+Tab` navigation is legible without relying only on border-color shifts
- corpus ingest supports a framing prompt whose phrases are graph-indexed as persistent document-conditioning material
- export actions report the artifact directory path in the status surface so the operator can find the generated files without guesswork
- observatory launch status is explicitly phased in the top action shelf (`queued`, `ensuring server`, `exporting payloads`, `opening browser`); elapsed time is real elapsed time, not an ETA claim
- when an existing shell is available, `opening browser` can truthfully occur before `exporting payloads` completes; the status line must make that background refresh explicit rather than implying the browser is still idle

## Budget panel contents

- current profile name
- requested mode and effective mode
- retrieval depth
- max context items
- history turns
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
- `Enter`: send turn (or `Ctrl+S` as a shortcut)
- `F2`: export observability artifacts
- `F3`: ensure/open local observatory
- `F4`: toggle low-motion in the current session request
- `F5`: open the new-session inference-profile flow
- `F6`: open the utilities deck
- `F7`: focus the latest-turn inline review form in chat while review is pending
- `F8`: toggle the full-width aperture drawer
- `F9`: open document ingest with framing prompt
- `F10`: open the conversation atlas
- `F11`: toggle runtime/event chyron drawer
- `Esc`: return focus to the composer on the main chat screen
