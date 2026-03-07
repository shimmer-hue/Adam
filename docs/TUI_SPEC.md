# TUI Spec

The TUI remains the primary EDEN runtime surface in v1.2.

## Boot flow

Live cockpit boot:

- EDEN opens directly into a chat session surface
- if a previous session exists, EDEN resumes the latest persisted session automatically
- if no session exists yet, EDEN creates a blank experiment/session automatically
- the top action menu remains available for:
  - `Review Feedback`
  - `Adjust Profile`
  - `New Session`
  - `Resume Latest`
  - `Blank Eden`
  - `Seeded Eden`
  - `Prepare Qwen`
  - `Open Observatory`
  - `Export Latest`
  - `Open Deck`
  - `Help`
- default MLX model storage remains under `models/` in the repo root

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
  - visible thinking / reasoning artifact panel
  - feedback / session-state panel
- right cockpit bay:
  - upper stack:
    - animated signal field
    - animated amber cockpit instrumentation
    - forensic structured log
  - lower chat deck:
    - latest persisted Brian / Adam transcript boxes
    - live Brian draft box when the composer is loaded
    - multiline `TextArea` composer for Brian the operator
    - transmit hint surface; `Ctrl+S` sends

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
- cockpit-first primary chat surface: aperture/thinking/feedback left, animated telemetry upper-right, chat deck lower-right
- live-session boot is the default path; the app no longer lands on a launcher before chat opens
- session and utility actions now live in the keyboard-executable top menu instead of left-column buttons
- normal entry path is `.venv/bin/python -m eden` or `.venv/bin/python -m eden app`
- shell flags remain optional overrides; the normal runtime contract is repo-local MLX
- the action bar reports model readiness, active session, and focus/keyboard hints
- multiline composition is first-class
- operator turns are persisted and graph-ingested as `Brian the operator: ...`
- MLX/Qwen model-emitted thinking is surfaced as a dedicated panel instead of leaking into the main Adam response
- the prime surface keeps aperture, thinking, feedback, and transcript visible while the operator types; Deck still carries the detailed trace and budget surfaces
- budget changes remain visible, but now live in Deck instead of the prime chat pane
- latest-session resume restores the latest persisted session surface without forcing a new session flow first
- keyboard-only navigation is supported through top-menu focus, `Enter` execution, `Tab` / `Shift+Tab` focus cycling, and the function-key bindings

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
- `F7`: open the review feedback modal
