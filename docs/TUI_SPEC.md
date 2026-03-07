# TUI Spec

The TUI remains the primary EDEN runtime surface in v1.2.

## Startup flow

Startup screen:

- top startup action menu:
  - `Blank Eden`
  - `Seeded Eden`
  - `Resume Latest`
  - `Prepare Qwen`
  - `Refresh Model`
  - `Open Observatory`
  - `Export Latest`
  - `Help`
- aperture / active-set reference panel
- Qwen thinking panel populated from the latest visible reasoning artifact
- animated cockpit panel
- startup runtime log
- latest Brian / Adam chat preview
- default MLX model stored under `models/` in the repo root

Session-start modal:

- session title
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
  - `low_motion`
  - `debug`

## Chat screen

Primary split:

- left cockpit bay:
  - aperture / active set
  - session capsule with regard trace
  - utility controls: `New Session`, `Observatory`, `Export`, `Deck`, `Profile`, `Help`
- right cockpit bay:
  - upper stack:
    - animated amber cockpit instrumentation
    - forensic structured log
  - lower chat deck:
    - Brian transmission box
    - Adam membrane box
    - multiline `TextArea` composer for Brian the operator
    - primary actions: `Send`, `Review`

Secondary surfaces:

- `Deck` modal:
  - `Inference Circumstances / Budget`
  - graph telemetry
  - bounded history
  - Qwen thinking / reasoning
  - aperture / active set
  - cogitation / decision trace
  - ingest input
  - `Blank Eden`, `Seeded Eden`, `Resume Latest`
  - `New Session`, low-motion toggle, debug toggle
- `Review` modal:
  - explicit accept / edit / reject / skip feedback surface
  - explanation and corrected-answer fields
  - last-response summary

## Design contract

- fixed panes, no primary scrolling transcript
- amber-on-dark operator grammar preserved
- cockpit-first primary chat surface: aperture and controls left, animated telemetry upper-right, chat deck lower-right
- startup launcher is fixed to local MLX; runtime/model-path picking is removed from the launcher surface
- startup launch/export/observatory actions live in a keyboard-executable top menu instead of left-column buttons
- normal entry path is `.venv/bin/python -m eden` or `.venv/bin/python -m eden app`
- shell flags remain optional overrides, but the TUI launcher itself is locked to local MLX
- the launcher reports model readiness, shard progress, and repo-local storage instead of asking for a manual MLX path
- multiline composition is first-class
- operator turns are persisted and graph-ingested as `Brian the operator: ...`
- MLX/Qwen model-emitted thinking is surfaced in Deck instead of leaking into the main Adam response
- latest startup reasoning preview is surfaced directly on the startup screen
- the prime surface keeps the aperture visible while the operator types; Deck still carries the detailed trace and budget surfaces
- budget changes remain visible, but now live in Deck instead of the prime chat pane
- latest-session resume restores the latest persisted session surface instead of forcing a new session flow
- keyboard-only navigation is supported through startup menu focus, `Enter` execution, `Tab` / `Shift+Tab` focus cycling, and the existing function-key bindings

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
- `F6`: open the operator deck
