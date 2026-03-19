# Inference Profiles

EDEN v1.1 adds explicit session-start inference profiles. The request is stored in session metadata, and the resolved per-turn profile is stored in each turn record.

## Modes

### `manual`

- operator supplies bounded values directly
- EDEN clamps them to safe local ranges
- resolved mode remains `manual`

### `runtime_auto`

- deterministic runtime policy chooses a bounded preset per turn
- inputs include:
  - query length
  - graph density proxies
  - memode coverage
  - recent membrane-event count
  - recent feedback balance
- no hidden governor is introduced

### `adam_auto`

- mock backend: bounded preset chooser tied to operator-approved ranges
- MLX backend: currently falls back to `runtime_auto`
- fallback is persisted and visible as:
  - `requested_mode=adam_auto`
  - `effective_mode=runtime_auto`
  - `selection_source=adam_auto_fallback_runtime_auto`

## Persisted fields

Session metadata stores the requested profile:

- `mode`
- `budget_mode`
- `temperature`
- `max_output_tokens`
- `top_p`
- `repetition_penalty`
- `retrieval_depth`
- `max_context_items`
- `history_turns`
- `response_char_cap`
- `low_motion`
- `debug`

Turn metadata stores the resolved profile plus budget circumstances:

- `requested_mode`
- `effective_mode`
- `profile_name`
- `selection_source`
- heuristic inputs used by the chooser
- prompt budget and remaining allowance
- count method
- budget pressure

## Session-start operator guidance

Left-side controls:

- `mode`
  - `manual`: EDEN clamps the operator-entered values and uses them directly
  - `runtime_auto`: EDEN chooses a bounded preset per turn from query length, graph density proxies, memode coverage, membrane-event count, and feedback balance
  - `adam_auto`: mock backend uses the bounded Adam-guided picker; current MLX path persists the request but resolves visibly as `runtime_auto`
- `budget_mode`
  - `tight`: leanest prompt-budget envelope
  - `balanced`: middle preset
  - `wide`: largest bounded prompt-budget envelope
  - in `manual`, this still frames budget accounting even though the typed numeric values remain in force after clamping
- `low_motion`
  - `off`: keep TUI motion surfaces animated
  - `on`: reduce animation / redraw churn only
- `debug`
  - persisted session/profile flag surfaced in runtime status and metadata
  - current MLX path does not switch sampler settings, retrieval policy, or hidden extra passes on this flag alone

## Explicit session-start graph wake-up audit

- session start may run a separate wake-up audit before Brian's first turn
- knowledge phase:
  - the deterministic path upgrades missing author/work information nodes and typed informational edges into the persistent graph when they can be grounded from existing text
  - the Adam-identity MLX review path is now explicit opt-in only via `EDEN_ENABLE_MLX_WAKEUP_REVIEW=1`; otherwise session start stays on deterministic repair even when the live backend is MLX
  - when that opt-in is enabled on the real MLX path, EDEN can ask Adam in a bounded JSON-only review pass to confirm or refine those legacy knowledge relations before persistence
- behavior phase:
  - EDEN audits bounded turn-attached behavior bundles from Adam responses and explicit feedback
  - the deterministic fallback can strengthen first-order behavior memes and materialize bounded behavior memodes from existing support edges
  - when `EDEN_ENABLE_MLX_WAKEUP_REVIEW=1` is set on the real MLX path, Adam can review the candidate behavior bundle in a bounded JSON-only taxonomy pass and choose a tighter memode label/member set
  - any `memeplex` hint is report-only in this build
- this audit is explicit and visible:
  - session metadata stores `session_graph_normalization`
  - session metadata stores `session_graph_taxonomy`
  - session metadata stores `session_graph_wakeup`
  - the trace surface records `GRAPH_NORMALIZATION`, `GRAPH_TAXONOMY_AUDIT`, and `GRAPH_WAKEUP_AUDIT`
- this audit is separate from `adam_auto` turn-profile selection and separate from Adam's operator-facing response generation

Manual numeric fields:

- `temperature`: lower values are steadier; higher values produce more randomness/variation
- `max_output_tokens`: lower values force shorter outputs; higher values allow longer continuations
- current manual clamp is `128..4096`; the balanced manual default is now `1200` for longer-form local replies
- `top_p`: lower values narrow the candidate-token pool; higher values widen it
- `repetition_penalty`: higher values suppress repeated phrasing more strongly; lower values allow more reuse
- `retrieval_depth`: lower values inspect fewer recall candidates; higher values inspect more
- `max_context_items`: lower values admit fewer retrieved items into the active prompt; higher values admit more at added prompt-budget cost
- `history_turns`: lower values keep the prompt history tighter; higher values preserve more recent Brian/Adam turns at added prompt-budget cost; current manual clamp is `1..256`
- requested `history_turns` is not identical to injected history every turn: EDEN now trims the actual recent-history block against the active prompt-budget envelope after active set, feedback, and operator text are accounted for
- `response_char_cap`: lower values enforce tighter post-generation operator-facing replies; higher values allow fuller replies
- current manual clamp is `600..12000`; the balanced manual default is now `5200` so longer replies are not immediately re-trimmed on the visible surface
- `response_char_cap` still governs the membrane-cleaned operator-facing answer stored at turn time, but readable archive/tape surfaces may reconstruct from raw stored `response_text` under a larger bounded display cap so older clipped turns remain legible

## MLX pass-through

On the real MLX path, v1.1 passes through:

- `temperature`
- `top_p`
- `repetition_penalty`
- `max_output_tokens`

The visible Adam reply surface is related but separate:

- `max_output_tokens` governs generation length
- `response_char_cap` governs the post-generation operator-facing visible reply after membrane cleanup
- longer Adam replies only appear in full when both are set high enough at generation time, although some readable transcript surfaces can recover more of the answer later from raw stored model text

using the installed local `mlx-lm` sampler/logits processor utilities.

## What the profile does not mean

- It is not a hidden planner.
- It is not a weight update.
- It is not a claim about the model’s absolute maximum context window.
- `adam_auto` is not a secret second model pass on the current MLX path; the only extra MLX control paths in this build are the explicit, trace-visible session-start wake-up audit phases.
