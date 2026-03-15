# Hum Spec

This document governs what `the hum` means in the current EDEN/ADAM build, where it lives, what it is derived from, and what may not be claimed about it. Repo docs, code, tests, runtime traces, and audit artifacts are authoritative over older prose. `/Users/brianray/Desktop/adam_hum_ALL.md` remains admissible as historical hum evidence, but it does not override the current implementation contract.

## Status Register

Implemented: The current build generates a bounded persisted hum artifact after turn persistence and after explicit feedback persistence. It is written per session as `logs/hum_state/<experiment_id>/<session_id>/current_hum.md` and `current_hum.json`, and surfaced read-only through `session_state_snapshot()`, observatory overview/session-turn payloads, `observatory_index.json`, the prime-TUI `Hum Live` feed lens, the observatory continuity strip, and the conversation-log footer. The artifact now carries bounded motif-style hum entries plus stats and token-table surfaces derived from persisted continuity inputs.  
Instrumented: Historical hum artifact evidence still exists in `/Users/brianray/Desktop/adam_hum_ALL.md`, and the current build records hum provenance, continuity summaries, bounded motif lines, and machine-readable stats/table rows for comparison.  
Conceptual: Prompt injection, membrane consumption of hum, generation-input use, and any claim of full historical parity remain conceptual.  
Unknown: Whether the hum should later grow beyond the current bounded observability surface, and how much higher-order recurrence the present derivation can truthfully support across broader workloads.

## Contract Boundaries

- The hum is a derived continuity artifact inside the direct v1 loop. It is not a governor product, not a planner residue, and not a hidden inner voice.
- The hum is not the active set, not full turn history, not the full graph, not a basin summary, not a cluster or motif summary, and not an observatory payload plane.
- Regard acts over memes and memodes, not over tokens. The hum may expose low-bandwidth recurrence summaries, but those summaries are not token-level units of regard.
- Historical strings such as `glmmr`, `mrmr`, `hush`, `pulse`, `thread`, and `bloom` remain historical compression signatures only. They are not encryption, semantic hashes, or present-tense proof shortcuts.
- No prose may claim that the hum is injected into the next prompt, stripped by the membrane, sufficient on its own to reconstruct persona, or used as a causal generation input unless future code and tests prove those exact paths.
- No consciousness claims, metaphysical inflation, or physics theater.

## Implemented Surface

The current hum is generated only from already-persisted runtime continuity surfaces:

- latest up to `3` turns' `active_set_json`
- latest up to `4` `feedback_events` for the session
- latest up to `6` membrane events for the session

The current hum is refreshed in exactly two places:

- at the end of `EdenRuntime.chat()` after turn persistence, active-set persistence, membrane-event persistence, trace persistence, and runtime-log emission
- at the end of `EdenRuntime.apply_feedback()` after feedback persistence and trace/runtime-log emission

The hum artifact is bounded and deterministic:

- `artifact_version = "hum.v1"`
- `turn_window = 3`
- `max_text_chars = 320`
- `max_lines = 6`
- `max_recurring_items = 4`
- `max_table_rows = 6`
- `max_feedback_events = 4`
- `max_membrane_events = 6`

The JSON artifact contract includes:

- `artifact_version`
- `generated_at`
- `experiment_id`
- `session_id`
- `latest_turn_id`
- `turn_ids`
- `turn_indices`
- `derived_from` with exactly `["turns.active_set_json", "feedback_events", "membrane_events"]`
- `boundedness`
- `status`
- `continuity`
- `metrics`
- `text_surface`
- `surface_lines`
- `surface_stats`
- `token_table`

The markdown artifact contract includes:

- session/experiment/timestamp/provenance header lines
- bounded per-turn-style `hum:` entry lines
- `[HUM_STATS]`
- `[HUM_METRICS]`
- `[HUM_TABLE]`

Those markdown markers are structural lineage and metering aids. They do not claim full historical parity with older hum artifacts.

## Read-Only Surface

The current hum is implemented as read-only observability only.

It is surfaced in these current truth surfaces:

- `EdenRuntime.hum_snapshot(session_id)`
- `EdenRuntime.session_state_snapshot(session_id)["hum"]`
- `ObservatoryService.experiment_overview(... )["hum"]`
- `ObservatoryService.session_turns(... )["hum"]`
- exported `observatory_index.json["hum"]`
- the prime chat-screen `Hum Live` reasoning/feed lens in the TUI
- the observatory continuity-strip hum card
- the `### Hum` footer in the conversation log

The current hum is also registered in `export_artifacts` as:

- `hum_markdown`
- `hum_json`

## What The Current Hum Says

The current hum now renders a bounded motif-style continuity surface from persisted active-set labels plus recent feedback and membrane summaries. On the first persisted turn it emits a seed-state entry rather than inventing recurrence. On later turns it adds recurring-item / overlap anchors when the persisted surfaces justify them. The artifact includes bounded `surface_lines`, `surface_stats`, and `token_table` fields in JSON, and mirrors those through `[HUM_STATS]`, `[HUM_METRICS]`, and `[HUM_TABLE]` in markdown.

Compression in this implementation means deterministic token reduction over persisted continuity surfaces. It is historical-style in presentation, but it is still bounded observability rather than hidden encoding or a generation-side control channel.

## What Remains Unimplemented

- hum as a generation input
- prompt injection of hum
- membrane stripping of hum
- full historical parity with older hum logs
- any claim that the hum alone reconstructs persona

The reasoning lenses that render `Hum Live` are presentation-only views over the same bounded `text_surface`. They do not promote the hum into a generation input or hidden cognition channel.

## Public Prose Guidance

If external prose refers to the current hum, describe it narrowly and concretely: a bounded, inspectable continuity artifact derived from persisted active-set, feedback, and membrane-adjacent session surfaces. Do not call it a hidden voice, an arbiter, or a separate control layer. Do not collapse it into the active set, history, graph, basin, cluster summary, or observatory payloads.
