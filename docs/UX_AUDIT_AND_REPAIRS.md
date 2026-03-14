# UX Audit And Repairs

This document records the user-journey audit run on March 9, 2026.

Evidence used:

- live PTY launch at `80x24`
- pilot-driven live app runs at `80x24`, `120x30`, and `140x40`
- targeted smoke tests in `tests/test_tui_smoke.py`

## Summary

Primary finding:

- The app already had useful controls, but the first-run path was not reliably legible on a standard terminal.

Main failures found:

- the composer path was effectively off-screen in `80x24`
- the footer clipped later hotkeys on narrow terminals
- `F10` used an unsafe archive code path through the global action binding
- `F7` claimed there was a review surface even when no Adam reply existed
- export feedback named files but did not tell the operator where they were written

## Defects Found

### 1. First-run launch was not legible at `80x24`

Observed before repair:

- top chrome dominated the screen
- the dialogue/composer area was clipped
- the top status note truncated the first-action guidance
- the footer only showed the early function keys

Operator impact:

- a first-time operator could not reliably tell where to type
- the send path existed but was not visible enough

Repair:

- added a compact responsive mode
- compact mode hides the right telemetry stack by default
- compact mode keeps transcript + composer visible and makes the runtime chyron drawer available via `F11`

Verified after repair:

- real `80x24` PTY launch shows `Adam Dialogue` and the composer again
- compact run starts with composer focus
- compact `F8` opens an aperture-focused swap view and `Esc` returns to dialogue

### 2. Archive hotkey path was unsafe

Observed before repair:

- `F10` used `action_show_archive()`
- that path called `handle_archive()` directly
- `handle_archive()` depends on `push_screen_wait()`, which must run inside a worker

Operator impact:

- the visible hotkey path could fail even though the internal action-bus path worked

Repair:

- changed `action_show_archive()` to launch the archive flow through `run_worker(...)`

Verified after repair:

- `F10`/binding path opens `ConversationAtlasModal`
- archive modal closes cleanly
- existing atlas resume path still passes smoke coverage

### 3. Review guidance lied when there was nothing to review

Observed before repair:

- `F7` always suggested an inline review surface existed
- if no Adam reply existed yet, focus returned to the composer but the message still implied a reviewable reply target

Operator impact:

- misleading guidance
- confusing first-run behavior

Repair:

- `handle_review()` now checks whether a reply exists first
- if no reply exists, it keeps focus in the composer and says to send a turn first

Verified after repair:

- `F7` before any Adam reply now leaves focus on the composer
- the feedback message now states the missing prerequisite clearly

### 4. Export feedback lacked the destination path

Observed before repair:

- export feedback only listed filenames

Operator impact:

- operator still had to guess where the artifacts were written

Repair:

- export status now includes the actual export directory path

Verified after repair:

- export feedback now reports:
  - `Exports generated in /Users/brianray/Adam/exports/<experiment_id>: ...`

## Discoverability Improvements Made

### Compact first-action hint

Before:

- the old top status note was too narrow to carry the first action on small terminals

After:

- `Composer` now carries the start instruction and the critical keys in compact mode

### Aperture behavior on small terminals

Before:

- the wide-drawer model assumed a larger screen

After:

- compact mode uses a dedicated aperture-focused swap view
- `Esc` returns to the composer

### Focus consistency on session transitions

Before:

- focus could land inconsistently after resume/new-session flows

After:

- bootstrap resume
- archive resume
- new session
- blank/seeded/resume launch paths

all return focus to the composer.

## Before / After Notes

### Before

- first-time operator path depended on prior knowledge
- some visible hotkeys were not reliable enough
- export completion lacked a usable destination hint

### After

- first-time operator can see the composer on `80x24`
- `Esc` is a dependable recovery key again
- `F10` works through the same safe archive flow as the menu
- `F7` now respects whether a reply exists
- export completion tells the operator where the files went

## Regression Coverage Added Or Updated

- compact layout smoke coverage
- `Tab` to the action strip and `Enter` execution coverage
- `Esc` recovery coverage
- compact aperture open/close coverage
- no-reply review guard coverage
- export path feedback coverage
- archive opened through the official `F10`/binding action path

## Remaining Unknowns

- The stock footer still clips later hotkey labels on narrow terminals. The compact composer hint now compensates, but the footer itself is not yet fully responsive.
- Large-library ergonomics in `Conversation Atlas` are still unknown beyond the tested path.
- Real MLX retrieval quality after ingest was not re-audited in this pass. The workflow and state changes were verified; semantic answer quality on the local MLX path still wants a dedicated content-quality pass.
