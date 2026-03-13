## [2026-03-07 09:44:09 EST] PRE-FLIGHT
Task summary:
Push current local work on `main` to GitHub under `shimmer-hue/Adam`.
Scope of work:
Verify remote/auth state, record the operation, commit any required log changes, and push local commits to `origin/main`.
Likely files/modules:
`/Users/brianray/Adam/codex_notes_garden.md`, Git metadata, and remote `origin`.
Relevant invariants:
Stay on `main`, do not rewrite history, use append-only notes, and preserve current MLX/TUI repo constraints without runtime changes.
Proof path (how success will be verified):
Confirm local branch status, inspect commits ahead of `origin/main`, run push, and verify `main` matches `origin/main`.
## [2026-03-07 09:47:24 EST] POST-FLIGHT
Files changed:
`/Users/brianray/Adam/.gitignore` and `/Users/brianray/Adam/codex_notes_garden.md`.
Behavior implemented or modified:
Rebuilt the unpushed local `main` history without oversized generated `graph_knowledge_base` export blobs, added ignore rules for future oversized export HTML/JSON files, and pushed `main` to `origin`.
Evidence (tests / commands run):
`git push --dry-run origin main`, `git push origin main`, and `git rev-list --left-right --count origin/main...main` returned `0 0`.
Docs updated:
No feature docs changed; operational log appended and `.gitignore` updated to prevent future GitHub push failures.
Remaining uncertainties or follow-ups:
Older export artifacts remain tracked on `origin/main`; only the newly blocked oversized files were removed from the unpushed history.
## [2026-03-07 09:51:43 EST] PRE-FLIGHT
Task summary:
Merge branch-held progress into `main` without losing work or reintroducing blocked oversized artifacts.
Scope of work:
Audit `codex/*` branches for unique commits, back up current `main`, merge or absorb branch-only work into `main`, run verification, and push the result to GitHub.
Likely files/modules:
Git branch history, `/Users/brianray/Adam/codex_notes_garden.md`, and any source/docs touched by branch-only commits.
Relevant invariants:
Do not rewrite or drop user progress, avoid restoring GitHub-rejected export blobs, keep append-only notes, and verify with repo-local tooling.
Proof path (how success will be verified):
Inspect branch diffs/cherries, merge or cherry-pick required work onto `main`, run `./.venv/bin/pytest -q`, and confirm `main` equals `origin/main` after push.
## [2026-03-07 09:54:19 EST] POST-FLIGHT
Files changed:
`/Users/brianray/Adam/codex_notes_garden.md`.
Behavior implemented or modified:
Backed up the pre-consolidation `main` tip, audited all `codex/*` branches, and merged remaining non-ancestor branch histories into `main` with safe `ours` merges where their meaningful code was already represented on `main` or where the branch only preserved stale artifact history.
Evidence (tests / commands run):
`git branch --merged main`, `git log --graph -10`, and `./.venv/bin/pytest -q` with `31 passed in 6.46s`.
Docs updated:
Operational log appended; product docs unchanged because repository contents stayed on the current `main` tree.
Remaining uncertainties or follow-ups:
Branch refs still exist after consolidation; delete them only if you want branch cleanup in addition to merge history.
## [2026-03-07 09:58:36 EST] POST-FLIGHT
Files changed:
`/Users/brianray/Adam/codex_notes_garden.md`.
Behavior implemented or modified:
Rebuilt branch consolidation from `origin/main` after GitHub rejected local merge ancestry containing oversized export and `.venv` blobs; kept `main` pushable, merged the safe `codex/2-oneshot-reboot` branch into `main`, and repointed local backup branches to clean commits already represented on `main`.
Evidence (tests / commands run):
`git rev-list --objects origin/main..main | git cat-file --batch-check ... | tail -20`, `./.venv/bin/pytest -q` with `31 passed in 6.33s`, and branch ancestry checks against `main`.
Docs updated:
Operational log appended; product docs unchanged.
Remaining uncertainties or follow-ups:
The local helper branch `codex/main-failed-consolidation-attempt-20260307` preserves the rejected merge attempt for inspection; it is not needed for runtime behavior and can be cleaned up later.
## [2026-03-07 09:59:59 EST] PRE-FLIGHT
Task summary:
Delete every branch except `main` and ensure future commits use the `shimmer-hue` git identity.
Scope of work:
Audit local and remote refs, remove the non-`main` worktree, delete non-`main` local and remote branches, set local git identity, and verify only `main` remains.
Likely files/modules:
Git refs, worktree metadata, and `/Users/brianray/Adam/codex_notes_garden.md`.
Relevant invariants:
Stay on `main`, do not disturb current tracked files, remove only non-`main` refs/worktrees, and keep commit identity explicitly configured for this repo.
Proof path (how success will be verified):
Confirm branch/worktree inventory before and after deletion, verify `git config user.name`/`user.email`, and ensure `git branch -a` shows only `main` plus `origin/main`.
## [2026-03-07 10:00:30 EST] POST-FLIGHT
Files changed:
`/Users/brianray/Adam/codex_notes_garden.md`.
Behavior implemented or modified:
Removed all non-`main` local branches, removed the extra non-`main` worktree, deleted the non-`main` remote branch, and explicitly set the repo-local git identity to `user.name=shimmer-hue` and `user.email=warnerpallitz@gmail.com`.
Evidence (tests / commands run):
`git branch -a -vv`, `git worktree list`, `git config --get user.name`, `git config --get user.email`, and `git status --short --branch`.
Docs updated:
Operational log appended; repository code/docs unchanged.
Remaining uncertainties or follow-ups:
GitHub commit attribution depends on the email remaining associated with the `shimmer-hue` account; the repo-local git config is now pinned for future commits in this repo.
## [2026-03-07 10:03:54 EST] PRE-FLIGHT
Task summary:
Clarify repo-root setup and launch steps so the app can be opened without ambiguity.
Scope of work:
Update the operational log and tighten README install/run instructions around /Users/brianray/Adam and the repo-local .venv.
Likely files/modules:
`/Users/brianray/Adam/codex_notes_garden.md` and `/Users/brianray/Adam/README.md`.
Relevant invariants:
Use the repo-local .venv with Python 3.12, keep the TUI as the primary runtime, and preserve docs alignment with actual launcher behavior.
Proof path (how success will be verified):
Confirm the repo-local editable install and CLI entrypoint exist, then verify the documented launcher command resolves from the repo root.
## [2026-03-07 10:05:02 EST] POST-FLIGHT
Files changed:
`/Users/brianray/Adam/README.md` and `/Users/brianray/Adam/codex_notes_garden.md`.
Behavior implemented or modified:
Clarified that setup and launch commands must be run from `/Users/brianray/Adam`, collapsed the normal install path to `.[dev,mlx]`, and documented the repo-local launcher command that works from a fresh shell.
Evidence (tests / commands run):
`./.venv/bin/python -m pip show eden-adam mlx-lm`, `cd /Users/brianray/Adam && .venv/bin/python app.py --help`, and `cd /Users/brianray/Adam && .venv/bin/eden --help`.
Docs updated:
`README.md` and the operational log.
Remaining uncertainties or follow-ups:
This was a docs-only correction; the app already launched correctly from the repo root, so no behavior tests were required.
## [2026-03-07 10:15:36 EST] PRE-FLIGHT
Task summary:
Rework the EDEN TUI into a denser amber cockpit: fewer left panels, a split right bay, promoted active-set visibility, animated instrumentation, and a fixed local-MLX launcher.
Scope of work:
Update the Textual startup/chat layouts, remove startup backend selection, add animated cockpit widgets and transcript boxes, refresh the TUI spec, and verify with tests.
Likely files/modules:
`/Users/brianray/Adam/eden/tui/app.py`, `/Users/brianray/Adam/docs/TUI_SPEC.md`, and `/Users/brianray/Adam/codex_notes_garden.md`.
Relevant invariants:
Keep the TUI as the primary runtime surface, preserve memes as first-class and memodes as derived, preserve the v1 loop and explicit feedback semantics, and keep the core runtime on MLX.
Proof path (how success will be verified):
Exercise the startup-to-chat flow in tests, verify the new widget ids and fixed-MLX launcher behavior, and run `./.venv/bin/pytest -q`.
## [2026-03-07 10:26:48 EST] POST-FLIGHT
Files changed:
`/Users/brianray/Adam/eden/tui/app.py`, `/Users/brianray/Adam/eden/runtime.py`, `/Users/brianray/Adam/tests/test_tui_smoke.py`, `/Users/brianray/Adam/README.md`, `/Users/brianray/Adam/docs/TUI_SPEC.md`, `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`, `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`, and `/Users/brianray/Adam/codex_notes_garden.md`.
Behavior implemented or modified:
Rebuilt the startup and chat TUI into a denser amber cockpit with three left-side panels, a split right-side bay, animated telemetry, visible aperture/active-set surfaces, shaded Brian/Adam transcript boxes, and a startup launcher fixed to local MLX while preserving CLI mock overrides for explicit shell use.
Evidence (tests / commands run):
`./.venv/bin/python -m py_compile eden/tui/app.py eden/runtime.py tests/test_tui_smoke.py`, `./.venv/bin/pytest -q tests/test_tui_smoke.py`, and `./.venv/bin/pytest -q` with `31 passed in 6.48s`.
Docs updated:
`README.md`, `docs/TUI_SPEC.md`, `docs/IMPLEMENTATION_TRUTH_TABLE.md`, `docs/KNOWN_LIMITATIONS.md`, and the operational log.
Remaining uncertainties or follow-ups:
Layout proportions and animation cadence were validated by structure and tests; the next pass should be visual tuning against live terminal screenshots now that the cockpit architecture is in place.
## [2026-03-07 10:33:40 EST] PRE-FLIGHT
Task summary:
Refine the startup cockpit by replacing MLX/launch-contract panels with a Qwen thinking panel and moving startup actions into a top keyboard-driven menu.
Scope of work:
Update the startup layout and action wiring in the Textual app, strengthen keyboard navigation, refresh tests, and sync docs if the startup contract changes.
Likely files/modules:
`/Users/brianray/Adam/eden/tui/app.py`, `/Users/brianray/Adam/tests/test_tui_smoke.py`, `/Users/brianray/Adam/docs/TUI_SPEC.md`, and `/Users/brianray/Adam/codex_notes_garden.md`.
Relevant invariants:
Keep the TUI primary, keep the launcher fixed to local MLX, preserve explicit Qwen reasoning separation, and maintain keyboard-only operability.
Proof path (how success will be verified):
Verify the startup menu is focusable/executable from the keyboard, confirm the thinking panel renders latest reasoning, and run the targeted smoke test plus full pytest.
## [2026-03-07 10:38:08 EST] POST-FLIGHT
Files changed:
`/Users/brianray/Adam/eden/tui/app.py`, `/Users/brianray/Adam/tests/test_tui_smoke.py`, `/Users/brianray/Adam/docs/TUI_SPEC.md`, `/Users/brianray/Adam/README.md`, `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`, and `/Users/brianray/Adam/codex_notes_garden.md`.
Behavior implemented or modified:
Replaced the startup MLX-readiness and launch-contract stack with a single Qwen thinking panel, moved startup launch/export/observatory controls into a top action menu, and added explicit keyboard-first focus cycling plus menu execution on Enter.
Evidence (tests / commands run):
`./.venv/bin/python -m py_compile eden/tui/app.py tests/test_tui_smoke.py`, `./.venv/bin/pytest -q tests/test_tui_smoke.py`, and `./.venv/bin/pytest -q` with `31 passed in 6.87s`.
Docs updated:
`README.md`, `docs/TUI_SPEC.md`, `docs/IMPLEMENTATION_TRUTH_TABLE.md`, and the operational log.
Remaining uncertainties or follow-ups:
The keyboard path is covered structurally and by the startup smoke test; the next pass can refine menu phrasing and reasoning-panel density from live screenshots if you want the startup surface even tighter.

## [2026-03-07 10:50:02 EST] PRE-FLIGHT
Task summary:
Make the TUI launch into a live MLX chat cockpit, replace preview-only startup behavior with an active session, expand active aperture/thinking/chat/feedback surfaces, and strengthen the amber cybernetic aesthetic.
Scope of work:
Boot flow, TUI layout/state wiring, MLX chat path, keyboard navigation, and synchronized docs/tests.
Likely files/modules:
eden/tui/app.py, eden/app.py, eden/runtime.py, eden/models/mlx_backend.py, tests/test_tui_smoke.py, README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Relevant invariants:
Repo-local .venv, MLX as real runtime, TUI as primary interface, preserve v1 loop and explicit feedback, use apply_patch, run pytest before handoff.
Proof path (how success will be verified):
Run focused smoke coverage for boot/chat behavior, then full ./.venv/bin/pytest -q; verify the app boots into a live session path and keyboard navigation remains intact.

## [2026-03-07 11:18:28 EST] POST-FLIGHT
Files changed:
eden/tui/app.py, tests/test_tui_smoke.py, README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Behavior implemented or modified:
TUI now boots directly into a resumed-or-created live session, uses the top action menu for keyboard-first control, exposes active aperture/thinking/feedback panels, shows a bounded live transcript plus composer, and sends real turns through the runtime-backed chat path.
Evidence (tests / commands run):
python3 -m py_compile eden/tui/app.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py; ./.venv/bin/pytest -q
Docs updated:
README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Remaining uncertainties or follow-ups:
StartupScreen remains in code as a fallback/reference surface but is no longer the default entry path; further visual tuning can iterate on the signal-field animation density and transcript packing.

## [2026-03-07 11:28:49 EST] PRE-FLIGHT
Task summary:
Integrate feedback into the lower-right chat loop, expand and explain the signal field, and make aperture formatting more animated and human-legible.
Scope of work:
TUI layout, signal-field rendering, aperture rendering, feedback surfacing, tests/docs sync.
Likely files/modules:
eden/tui/app.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md, README.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Relevant invariants:
Repo-local .venv, MLX as real runtime, TUI as primary interface, preserve v1 loop and explicit feedback, use apply_patch, run pytest before handoff.
Proof path (how success will be verified):
Run focused TUI smoke coverage, then full ./.venv/bin/pytest -q.

## [2026-03-07 11:34:14 EST] PRE-FLIGHT
Operator task:
Add `/Users/brianray/Adam/data/cannonical_secondary_sources` to GitHub ignore list for this repository.
Task checksum:
Single-path `.gitignore` change for repository-level ignore behavior.
Repo situation:
Working tree has prior local history entries in `codex_notes_garden.md`; no uncommitted code changes affecting runtime behavior were observed for this request.
Relevant spec surfaces read:
`AGENTS.md` guidance for Codex-Builder operational process.
Natural-language contracts in force:
`spec -> implementation -> evidence -> audit -> next action`; append-only operational log.
Files/modules likely in scope:
`/Users/brianray/Adam/.gitignore`, `/Users/brianray/Adam/codex_notes_garden.md`
Status register:
- Implemented:
- Instrumented:
- Conceptual:
- Unknown:
Risks / invariants:
- Preserve existing ignore semantics while adding this one path.
- Confirm repository-local `.gitignore` remains canonical over path-level alternatives.
Evidence plan:
- Confirm `.gitignore` contains `data/cannonical_secondary_sources/`.
- Verify current `git status --short` remains clean aside from intended edits.
Shortest proof path:
View diff, run `git status --short`, and validate `git check-ignore` on the target path.

## [2026-03-07 11:35:21 EST] POST-FLIGHT
Files changed:
`/Users/brianray/Adam/.gitignore`, `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
None (ignore-list operational housekeeping only).
Natural-language contracts added/revised/preserved:
Codex-Builder operational loop maintained; no canonical spec surfaces were modified.
Behavior implemented or modified:
Ignored `data/cannonical_secondary_sources/` in repository Git ignores.
Evidence produced (tests / traces / commands / exports):
`git check-ignore -v /Users/brianray/Adam/data/cannonical_secondary_sources`
`git status --short`
`git diff -- .gitignore`
Status register changes:
- Implemented:
  - `.gitignore` now excludes `data/cannonical_secondary_sources/` from Git tracking.
- Instrumented:
- Conceptual:
- Unknown:
  - Confirmation that the directory is now untracked in all current/previous commits (outside ignore check and working tree status) was not run in this turn.
Truth-table / limitations updates:
None needed.
Remaining uncertainties:
None for requested change.
Next shortest proof path:
Create a file inside `data/cannonical_secondary_sources/`, run `git status`, and confirm it does not appear unignored.

## [2026-03-07 11:41:44 EST] POST-FLIGHT
Files changed:
eden/tui/app.py, tests/test_tui_smoke.py, README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Behavior implemented or modified:
Integrated a feedback-loop strip into the lower-right chat deck, expanded the signal field into a full-width explanatory telemetry surface, and rewrote the aperture as an animated readable scan with natural-language summaries and ranked queue rendering.
Evidence (tests / commands run):
python3 -m py_compile eden/tui/app.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py; ./.venv/bin/pytest -q
Docs updated:
README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Remaining uncertainties or follow-ups:
Further tuning may still help with panel density at smaller terminal sizes, especially if the transcript grows beyond two recent turns or the operator wants quick inline verdict controls instead of the F7 review path.

## [2026-03-07 11:50:27 EST] PRE-FLIGHT
Task summary:
Add a collapsible wide aperture scan, clarify the lower-right conversation lifecycle, visualize memgraph updates more directly in the signal field, and add a PDF ingest + framing-prompt flow for Adam.
Scope of work:
TUI layout and controls, ingest modal/runtime plumbing, memgraph telemetry rendering, tests/docs sync.
Likely files/modules:
eden/tui/app.py, eden/runtime.py, eden/ingest/pipeline.py, eden/storage/graph_store.py, tests/test_tui_smoke.py, README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Relevant invariants:
Repo-local .venv, MLX as real runtime, TUI as primary interface, preserve v1 loop and explicit feedback, use apply_patch, run pytest before handoff.
Proof path (how success will be verified):
Run focused TUI smoke coverage for aperture/ingest flow, then full ./.venv/bin/pytest -q.

## [2026-03-07 12:07:12 EST] POST-FLIGHT
Files changed:
eden/tui/app.py, eden/runtime.py, eden/ingest/pipeline.py, tests/test_tui_smoke.py, README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Behavior implemented or modified:
Added an F8 pull-down aperture drawer, explicit conversation lifecycle strip, orthographic memgraph bus rendering in the signal field, and a top-level ingest modal with framing prompt whose text is indexed into the graph alongside the document.
Evidence (tests / commands run):
python3.12 -m py_compile eden/tui/app.py eden/runtime.py eden/ingest/pipeline.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py; ./.venv/bin/pytest -q
Docs updated:
README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Remaining uncertainties or follow-ups:
The ingest flow is keyboard-first and graph-real, but it still relies on absolute file paths rather than an OS-native picker, and resumed sessions do not yet reconstruct the most recent ingest summary into the dedicated UI state without a fresh ingest in the current run.

## [2026-03-07 12:55:15 EST] PRE-FLIGHT
Task summary:
Investigate why the operator cannot type into the chat composer reliably and make the prompt-entry path obvious and robust.
Scope of work:
TUI focus behavior, composer affordances, keyboard bindings, smoke coverage, docs if behavior changes.
Likely files/modules:
eden/tui/app.py, tests/test_tui_smoke.py, README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Relevant invariants:
Repo-local .venv, TUI primary, MLX runtime preserved, apply_patch for edits, run full pytest before handoff.
Proof path (how success will be verified):
Reproduce typing/focus via Textual test, add robust composer-focus/send path, run focused smoke then full ./.venv/bin/pytest -q.

## [2026-03-07 13:11:38 EST] POST-FLIGHT
Files changed:
eden/tui/app.py, tests/test_tui_smoke.py, README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, codex_notes_garden.md
Behavior implemented or modified:
Hardened prompt entry by routing printable keys back to the composer when focus leaves editable widgets, added Esc-to-composer recovery, stronger composer affordances, and smoke coverage proving typing still works after focus shifts to the action menu.
Evidence (tests / commands run):
python3.12 -m py_compile eden/tui/app.py eden/runtime.py eden/ingest/pipeline.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py; ./.venv/bin/pytest -q
Docs updated:
README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md
Remaining uncertainties or follow-ups:
Mouse-based click targeting at very small terminal sizes can still be awkward in automated tests, but keyboard-first composer recovery is now explicit and verified.

## [2026-03-08 10:53:40 EDT] PRE-FLIGHT
Task summary:
Move feedback inline into the chat loop after each Adam response, keep it graph-effective, clarify conversation/menu meaning, and rename the self-aware cockpit panel.
Scope of work:
TUI chat deck widgets and bindings, feedback submission path reuse, menu/copy renaming, docs/tests sync.
Likely files/modules:
eden/tui/app.py, tests/test_tui_smoke.py, README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Relevant invariants:
TUI primary, explicit structured feedback, v1 loop preserved, apply_patch edits, full pytest before handoff.
Proof path (how success will be verified):
Focused TUI smoke for inline feedback path, then full ./.venv/bin/pytest -q.

## [2026-03-08 11:24:51 EDT] POST-FLIGHT
Files changed:
eden/tui/app.py, tests/test_tui_smoke.py, README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, codex_notes_garden.md
Behavior implemented or modified:
Reply review now lives inline under Adam's latest answer with Accept/Edit/Reject/Skip controls, explanation/corrected-text inputs, and graph-impact messaging; the old self-aware cockpit wording was renamed to Runtime Loop and the top action menu labels were rewritten into more familiar operator language.
Evidence (tests / commands run):
python3.12 -m py_compile eden/tui/app.py eden/runtime.py eden/ingest/pipeline.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py; ./.venv/bin/pytest -q
Docs updated:
README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Remaining uncertainties or follow-ups:
Inline reply review is currently scoped to Adam's latest turn in the live session; historical turns retain verdict labels in the transcript but do not yet reopen as full inline review forms.

## [2026-03-08 11:41:09 EDT] PRE-FLIGHT
Operator task:
Refactor the Adam TUI so the conversation surface is primary at launch, the composer is always visible, and telemetry remains present but secondary.
Task checksum:
adam-tui-dialogue-first-redesign-20260308
Repo situation:
Dirty worktree already includes README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, eden/tui/app.py, tests/test_tui_smoke.py, and this notepad; treat checked-out contents as baseline and patch surgically.
Relevant spec surfaces read:
docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, README.md first-run guidance.
Natural-language contracts in force:
TUI is the primary runtime surface, chat boots live by default, local MLX remains the real runtime, explicit feedback remains graph-effective, and composer focus recovery stays keyboard-first.
Files/modules likely in scope:
eden/tui/app.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, README.md.
Status register:
- Implemented:
Live session boot, multiline composer, composer focus recovery, inline reply review, telemetry surfaces, fixed-pane amber TUI.
- Instrumented:
Runtime loop, signal field / memgraph bus, aperture snapshot, live contract/action bus status text.
- Conceptual:
Dialogue-first hierarchy where chat is visually dominant and telemetry is subordinate; stronger visible interaction affordances in the top controls.
- Unknown:
Whether the current Textual CSS/layout can be rearranged without clipping at smaller terminal sizes; whether existing smoke coverage is sufficient for the new hierarchy.
Risks / invariants:
Do not break the v1 operator loop, feedback semantics, or MLX runtime contract. Keep the composer always visible and preserve Esc/printable-key recovery. Avoid silent spec drift because the current TUI spec still describes the older cockpit-first hierarchy.
Evidence plan:
Patch the compose tree and panel copy in eden/tui/app.py, update smoke assertions for dialogue-first boot surfaces, then run python3.12 -m py_compile plus focused and full pytest from the repo-local .venv.
Shortest proof path:
Make the chat column primary, restack telemetry into a narrower secondary column, adjust affordance copy/titles, update TUI spec/truth table/limitations/README, run ./.venv/bin/pytest -q tests/test_tui_smoke.py then ./.venv/bin/pytest -q.

## [2026-03-08 11:50:31 EDT] POST-FLIGHT
Files changed:
eden/tui/app.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, README.md, codex_notes_garden.md
Specs changed:
docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Natural-language contracts added/revised/preserved:
Revised the TUI contract from cockpit-first to dialogue-first, preserved live-session boot, preserved composer focus recovery, preserved graph-effective inline feedback, and preserved local-MLX as the real runtime contract.
Behavior implemented or modified:
Refactored the chat screen so the primary left column is a persistent Adam dialogue deck with visible transcript, inline review strip, and always-visible composer; moved memgraph/runtime/aperture/thinking/session telemetry into a secondary right stack; added explicit header quick controls for ingest and aperture; rewrote panel copy so interaction affordances point at the visible composer instead of hidden telemetry assumptions.
Evidence produced (tests / traces / commands / exports):
python3.12 -m py_compile eden/tui/app.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py -> 1 passed; ./.venv/bin/pytest -q -> 31 passed
Status register changes:
- Implemented:
Dialogue-first chat layout, persistent header action bus with quick buttons, visible message-input affordance near the composer, docs/tests aligned to the new hierarchy.
- Instrumented:
Telemetry remains visible through memgraph bus, runtime loop, aperture snapshot, thinking, session feedback, and bounded forensic log in the secondary column.
- Conceptual:
No additional conceptual surfaces were introduced this turn.
- Unknown:
No visual artifact from this turn proves how the new split behaves at the smallest terminal sizes; only Textual smoke and full pytest evidence exist so far.
Truth-table / limitations updates:
Updated docs/IMPLEMENTATION_TRUTH_TABLE.md to record dialogue-first boot/layout semantics and docs/KNOWN_LIMITATIONS.md to keep the bounded-transcript limitation truthful under the new hierarchy.
Remaining uncertainties:
Tab from the composer currently lands on the forensic log before the header controls. Printable-key recovery still routes input back to the composer and the smoke test now proves that path, but tiny-terminal visual tuning and focus-order ergonomics could still use a dedicated follow-up if operator testing keeps surfacing friction.
Next shortest proof path:
Run the TUI in a small terminal, confirm the left dialogue deck remains visibly dominant without clipping, and decide whether telemetry widgets like the forensic log should remain in the tab order or be demoted further.

## [2026-03-08 11:52:08 EDT] POST-FLIGHT ADDENDUM
Files changed:
eden/tui/app.py, tests/test_tui_smoke.py, codex_notes_garden.md
Behavior implemented or modified:
Removed the forensic log from the tab order so keyboard focus now cycles from the composer back to actionable header controls instead of landing on passive telemetry first.
Evidence produced (tests / traces / commands / exports):
python3.12 -m py_compile eden/tui/app.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py -> 1 passed; ./.venv/bin/pytest -q -> 31 passed
Status register changes:
- Implemented:
Forensic log is now non-focusable in the primary TUI, and the smoke test again proves composer-to-header keyboard recovery.
- Instrumented:
Trace visibility is preserved; only focusability changed.
- Conceptual:
No additional conceptual surfaces were introduced.
- Unknown:
Small-terminal visual density still lacks a dedicated artifact from this turn.
Remaining uncertainties:
The remaining risk is visual density, not keyboard focus order.
Next shortest proof path:
Open the TUI in a smaller terminal and confirm the left dialogue deck still reads as the dominant surface without clipping or telemetry crowd-out.

## [2026-03-08 12:00:04 EDT] PRE-FLIGHT
Operator task:
Rebalance the dialogue-first TUI so the memgraph bus regains readable real estate and legending, aperture and thinking become full-width telemetry slices, runtime loop becomes a thin chyron, the event bus becomes more legible, and the action dropdown stops formatting/wrapping incorrectly.
Task checksum:
adam-tui-telemetry-restack-20260308
Repo situation:
Dirty worktree already includes the prior dialogue-first refactor in README.md, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, eden/tui/app.py, tests/test_tui_smoke.py, and this notepad; patch surgically from the checked-out state.
Relevant spec surfaces read:
docs/TUI_SPEC.md, prior truth-table/limitations state, current TUI layout/render code in eden/tui/app.py.
Natural-language contracts in force:
Dialogue remains primary, telemetry remains visible and explanatory, local MLX remains the real runtime, composer focus recovery stays intact, and explicit feedback remains graph-effective even if the square leaves the prime telemetry stack.
Files/modules likely in scope:
eden/tui/app.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, README.md.
Status register:
- Implemented:
Dialogue-first layout, inline reply review, action bus quick controls, composer focus recovery, memgraph bus, aperture drawer, dedicated thinking panel.
- Instrumented:
Runtime loop widget, memgraph glyph bus, aperture snapshot, chat-screen forensic log, live contract state text.
- Conceptual:
Telemetry restack with full-width memgraph/aperture/thinking/event slices and a thinner runtime chyron; better readable legending for the memgraph bus; cleaner action dropdown ergonomics.
- Unknown:
Whether the built-in Textual Select formatting issue is purely width/layout pressure or needs a deeper control substitution; whether the taller telemetry stack still fits well at medium terminal sizes.
Risks / invariants:
Do not regress the visible composer, inline feedback path, or keyboard recovery. Keep the memgraph bus explanatory rather than mystical. Preserve the active-set/aperture ontology and do not overclaim the event bus as more than an operator-facing trace.
Evidence plan:
Restack the telemetry column, rework the memgraph legend/event bus/chyron rendering, widen the action control area, update docs/tests, then run python3.12 -m py_compile plus focused and full pytest from the repo-local .venv.
Shortest proof path:
Patch eden/tui/app.py to stack telemetry vertically and widen the menu control, update smoke assertions for the new telemetry widgets, then run ./.venv/bin/pytest -q tests/test_tui_smoke.py and ./.venv/bin/pytest -q.

## [2026-03-08 12:08:05 EDT] POST-FLIGHT
Files changed:
eden/tui/app.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, README.md, codex_notes_garden.md
Specs changed:
docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Natural-language contracts added/revised/preserved:
Preserved dialogue-first interaction, revised the telemetry contract to use a stacked tool-oriented right column, preserved explicit inline feedback in the dialogue bay, and preserved the memgraph bus as an explanatory operator surface with visible legend.
Behavior implemented or modified:
Restacked the right telemetry column into enlarged full-width slices for memgraph bus, aperture, thinking, and event bus; moved runtime-loop status into a thin bottom chyron; removed the old feedback square from the prime stack; replaced the raw chat-screen RichLog with a cleaner event-bus panel; widened and reformatted the top action controls so the action select gets a full row and the quick buttons live on a separate row beneath it.
Evidence produced (tests / traces / commands / exports):
python3.12 -m py_compile eden/tui/app.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py -> 1 passed; ./.venv/bin/pytest -q -> 31 passed
Status register changes:
- Implemented:
Readable memgraph legend in the prime screen, full-width aperture/active-set slice, expanded thinking surface, bounded event-bus slice, thin runtime chyron, and wider action-control layout.
- Instrumented:
Event flow remains a bounded operator-facing slice derived from runtime/cockpit events; it is cleaner, but still not a full historical log browser in the prime screen.
- Conceptual:
No additional conceptual surfaces were introduced.
- Unknown:
No fresh screenshot artifact from this turn proves the exact visual result of the widened action dropdown and taller telemetry stack at the 163x67 geometry shown by the operator.
Truth-table / limitations updates:
Updated docs/IMPLEMENTATION_TRUTH_TABLE.md to record the stacked telemetry layout and visible memgraph legend, and docs/KNOWN_LIMITATIONS.md to state that the prime event bus is a bounded readability-first slice.
Remaining uncertainties:
The main remaining risk is visual tuning at specific terminal geometries, not correctness or regression. The select control has been given its own full row, but this turn still lacks a screenshot proof that the malformed dropdown is fully resolved at the operator’s exact window size.
Next shortest proof path:
Boot the TUI at the target terminal geometry, open the action menu once, and confirm the dropdown no longer wraps/clips while the memgraph/aperture/thinking/event stack reads cleanly at a glance.

## [2026-03-08 12:44:25 EDT] POST-FLIGHT
Files changed:
eden/runtime.py, eden/storage/graph_store.py, eden/tui/app.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, README.md, codex_notes_garden.md
Specs changed:
docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, README.md
Natural-language contracts added/revised/preserved:
Preserved dialogue-first TUI, preserved explicit graph-effective feedback requirements, revised the transcript contract from bounded static deck to scrolling tape, and added a durable operator-accessible conversation-log artifact under exports/conversations.
Behavior implemented or modified:
Replaced the static bounded transcript with a focusable VerticalScroll tape over the full persisted session; removed the top dialogue-surface instruction panel; replaced inline feedback buttons with typed verdict/confirm inputs (`A`/`E`/`R`/`S` plus `Y`) while preserving explanation/corrected-text requirements; added markdown transcript writing/opening for the active session and surfaced the path in the event bus/action bus; switched new-session/resume flows to restore snapshot-backed transcript metadata.
Evidence produced (tests / traces / commands / exports):
./.venv/bin/python -m py_compile eden/tui/app.py eden/runtime.py eden/storage/graph_store.py tests/test_tui_smoke.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py -> 1 passed; ./.venv/bin/pytest -q -> 31 passed
Status register changes:
- Implemented:
Scrollable dialogue tape, typed inline review command flow, keyboard scrolling for the focused tape, active-session markdown transcript artifact, action-bus transcript opener, and transcript-path surfacing in the event bus.
- Instrumented:
Event bus now reports the saved transcript path and last status, but it remains a bounded readability-first slice rather than a full log browser.
- Conceptual:
Richer transcript replay/index features such as per-turn jump links, filtering, or diff views remain conceptual only.
- Unknown:
No fresh screenshot artifact from this turn proves the exact visual result of the tape plus typed review inputs at the operator’s target terminal geometry.
Truth-table / limitations updates:
Updated docs/IMPLEMENTATION_TRUTH_TABLE.md to record the scrolling tape, typed inline review, and conversation-log artifact; updated docs/KNOWN_LIMITATIONS.md to replace the old bounded-transcript limitation with the newer transcript-artifact caveat.
Remaining uncertainties:
The main unknown is visual fit, not correctness: long real-world transcripts and the typed review strip have test coverage and compile/test proof, but this turn still lacks a screenshot at the operator’s exact window size after the latest patch.
Next shortest proof path:
Open the live TUI at the target terminal size, tab into the transcript tape to verify keyboard scrolling ergonomics, then open one saved transcript through Action Bus -> Open Conversation Log and confirm the operator can reach the file without leaving the cockpit workflow.

## [2026-03-08 13:02:06 EDT] PRE-FLIGHT
Operator task:
Stop visible reasoning/section-scaffolding from leaking into Adam's operator-facing reply, simplify transcript speaker labels to Brian/Adam, brighten and aesthetically enrich the TUI, deepen the memgraph/aperture coupling, enlarge the aperture surface, and demote/remove the prime Event Bus box by folding any necessary state into the chyron.
Task checksum:
adam-tui-answer-sanitize-aperture-restyle-20260308
Repo situation:
Dirty worktree includes the prior dialogue-tape and conversation-log refactor plus older TUI restacks; patch surgically from the checked-out state and avoid touching unrelated `.DS_Store`.
Relevant spec surfaces read:
docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, current runtime prompt/membrane code in eden/runtime.py, current model output splitting in eden/models/base.py and eden/models/mlx_backend.py, current TUI layout/render/CSS in eden/tui/app.py.
Natural-language contracts in force:
TUI remains the primary runtime surface; MLX/Qwen reasoning can be surfaced separately but must not leak into Adam's visible answer; telemetry should remain explanatory and operator-facing rather than mystical; explicit feedback semantics remain graph-effective; repo-local .venv / python3.12 stays the execution path.
Files/modules likely in scope:
eden/runtime.py, eden/models/mock.py, eden/tui/app.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, README.md.
Status register:
- Implemented:
Scrolling dialogue tape, typed inline review, conversation-log artifact, explanatory memgraph bus, aperture slice, dedicated thinking panel, runtime chyron.
- Instrumented:
Reasoning panel, memgraph bus live read, runtime/chyron event summaries.
- Conceptual:
More aesthetic marble-like interior treatments, richer memgraph-to-aperture narrative coupling, and a telemetry hierarchy where the bus and aperture feel predictive before Adam speaks.
- Unknown:
Whether Textual CSS can support the desired scrollbar styling directly; whether answer leakage is solely prompt/membrane scaffolding or also requires stronger answer sanitization against model fallbacks.
Risks / invariants:
Do not regress separate reasoning capture, explicit feedback requirements, transcript persistence, or keyboard navigation. Preserve operator readability even while brightening the palette. Avoid introducing hidden-thought claims under the guise of memgraph “mind reading”; keep it framed as operator-facing graph/active-set diagnostics.
Evidence plan:
Remove section-forcing from prompt/membrane, add response sanitization, restack right-column layout to memgraph + larger aperture + thinking + richer chyron, update CSS/palette/scrollbars, update docs/tests, then run py_compile plus focused and full pytest.
Shortest proof path:
Patch runtime sanitization first, then reshape TUI layout/render/CSS, adjust smoke assertions around clean Adam/Brian labels and the removed Event Bus panel, then run ./.venv/bin/python -m py_compile and ./.venv/bin/pytest -q tests/test_tui_smoke.py followed by full pytest.

## [2026-03-08 13:30:28 EDT] POST-FLIGHT
Files changed:
eden/runtime.py, eden/models/mock.py, eden/models/mlx_backend.py, eden/tui/app.py, tests/test_tui_smoke.py, tests/test_runtime_e2e.py, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, README.md, codex_notes_garden.md
Specs changed:
docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Natural-language contracts added/revised/preserved:
Preserved the dialogue-first cockpit, revised the operator-facing reply contract so Adam emits one clean visible answer with separate reasoning instrumentation, enlarged the aperture as the readable companion to the memgraph bus, and preserved explicit inline feedback semantics plus transcript persistence.
Behavior implemented or modified:
Removed runtime-enforced `Answer` / `Basis` / `Next Step` scaffolding from operator-facing responses and sanitized any leaked reasoning or labels before display/logging; restyled the prime TUI with brighter marbled interior surfaces and styled scrollbars; made the memgraph bus more color-dynamic and more explicit about document, knowledge-meme, behavior-meme, memode, and recall relations; enlarged the aperture panel with a richer bus-to-aperture narrative; removed the prime Event Bus box in favor of a merged runtime/event chyron; simplified transcript speaker labels to Brian / Adam in the visible tape and saved markdown log.
Evidence produced (tests / traces / commands / exports):
./.venv/bin/python -m py_compile eden/tui/app.py eden/runtime.py eden/models/mock.py eden/models/mlx_backend.py tests/test_tui_smoke.py tests/test_runtime_e2e.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py tests/test_runtime_e2e.py -> 3 passed; ./.venv/bin/pytest -q -> 31 passed; exports/conversations/ updated with session markdown transcript artifacts during test/runtime execution.
Status register changes:
- Implemented:
Operator-facing answer sanitization; Brian / Adam display labels in tape/log; brighter marbled prime-surface styling; richer colorized memgraph bus with relation legend/readout; expanded aperture/active-set narrative surface; merged runtime/event chyron replacing the prime Event Bus box.
- Instrumented:
Reasoning remains separately surfaced in the lower panel and sanitized out of Adam's visible answer; transcript artifact path remains surfaced through the runtime/event chyron and action bus.
- Conceptual:
Exact terminal-rendered marble fidelity is still constrained by Textual/terminal color-cell rendering; the aesthetic direction is implemented, but full graphical marbling remains terminal-native rather than image-grade.
- Unknown:
No fresh screenshot artifact from this turn proves the exact visual result of the brighter marble treatment, scrollbar appearance, and enlarged right-column stack at the operator's target window geometry.
Truth-table / limitations updates:
Updated docs/IMPLEMENTATION_TRUTH_TABLE.md for clean operator-facing answer sanitization and richer bus/aperture contract; updated docs/KNOWN_LIMITATIONS.md to record terminal-rendering constraints for marbled accents/scrollbars and the merged runtime/event chyron; updated docs/TUI_SPEC.md to align the prime layout and answer-surface contract with the current build.
Remaining uncertainties:
The main residual risk is visual tuning at the exact live terminal geometry, not correctness. The response bleed path is fixed in runtime code and covered by tests, but this turn still lacks a new screenshot proving the final aesthetic balance at 163x67.
Next shortest proof path:
Launch the TUI at the target geometry, send one turn that previously leaked reasoning, confirm the visible Adam reply is clean, then visually inspect the memgraph bus / aperture stack and scrollbar treatment for final aesthetic tuning.

## [2026-03-08 14:00:52 EDT] PRE-FLIGHT
Operator task:
Fix the runtime crash triggered by sending a turn from the TUI, where `_index_text_into_graph()` raises `KeyError: Unknown meme` while building a memode label after Adam has already generated a reply.
Task checksum:
adam-runtime-index-memode-label-crash-20260308
Repo situation:
Dirty worktree already contains the dialogue/answer-sanitization/TUI restyle work from earlier today plus unrelated `.DS_Store`; patch only the bounded runtime/test surface needed for this crash.
Relevant spec surfaces read:
docs/GRAPH_SCHEMA.md, current runtime indexing path in eden/runtime.py, current graph-store meme/memode semantics in eden/storage/graph_store.py.
Natural-language contracts in force:
Turns must persist into the graph without crashing; memes remain first-class and memodes remain derived bundles over multiple meme ids; fixes should preserve the current v1 loop and avoid broad storage-contract drift.
Files/modules likely in scope:
eden/runtime.py, tests/test_runtime_e2e.py, codex_notes_garden.md.
Status register:
- Implemented:
Turn persistence, meme indexing, memode derivation, TUI send-turn path, explicit feedback, transcript persistence.
- Instrumented:
Runtime traces and TUI traceback surface the crash path clearly through `_index_text_into_graph`.
- Conceptual:
Broader graph-store thread-safety hardening is not yet scoped for this turn.
- Unknown:
Whether the root issue is purely the redundant `get_meme()` refetch during memode label construction or a wider shared-SQLite read/write hazard.
Risks / invariants:
Do not change graph ontology or memode semantics. Preserve current turn indexing behavior and avoid introducing new storage keys or contract drift unless evidence requires it. Add a regression test so this exact crash path stays closed.
Evidence plan:
Replace the memode-label refetch with labels captured from the just-upserted meme rows, add a regression test covering `_index_text_into_graph()` with a store that would fail on redundant `get_meme()` calls, then run py_compile and targeted/full pytest.
Shortest proof path:
Patch eden/runtime.py, add the regression test in tests/test_runtime_e2e.py, run `./.venv/bin/python -m py_compile eden/runtime.py tests/test_runtime_e2e.py`, run `./.venv/bin/pytest -q tests/test_runtime_e2e.py`, then run `./.venv/bin/pytest -q`.

## [2026-03-08 14:04:21 EDT] POST-FLIGHT
Files changed:
eden/runtime.py, tests/test_runtime_e2e.py, codex_notes_garden.md
Specs changed:
None.
Natural-language contracts added/revised/preserved:
Preserved the existing graph contract: a turn still materializes memes first and may derive a memode bundle from them, but memode label construction no longer depends on a second store lookup for those same meme rows.
Behavior implemented or modified:
Changed `_index_text_into_graph()` to capture meme labels directly from the `upsert_meme()` results and reuse those labels when creating the derived memode, instead of re-fetching meme rows by id. Also bounded memode-member selection to the unique upserted meme ids already in hand. Added a regression test that fails if `_index_text_into_graph()` tries the redundant `get_meme()` refetch path again.
Evidence produced (tests / traces / commands / exports):
./.venv/bin/python -m py_compile eden/runtime.py tests/test_runtime_e2e.py; ./.venv/bin/pytest -q tests/test_runtime_e2e.py -> 3 passed; ./.venv/bin/pytest -q -> 32 passed
Status register changes:
- Implemented:
Crash-free memode derivation during turn indexing for the TUI send-turn path, backed by a regression test.
- Instrumented:
The traceback already identified the failing call path clearly; no new instrumentation was added.
- Conceptual:
Broader graph-store read-lock hardening across all shared-SQLite read methods remains out of scope for this turn.
- Unknown:
Whether the original missing-row symptom was purely the redundant refetch or also reflects a rarer shared-connection timing issue elsewhere; this exact crash path is now closed.
Truth-table / limitations updates:
None. This is a bounded correctness fix, not a user-facing contract change.
Remaining uncertainties:
The current fix removes the brittle lookup that triggered the crash. If another shared-connection race appears on a different read path, the next bounded step would be to audit and lock all GraphStore reads consistently.
Next shortest proof path:
Relaunch the TUI, send the same prompt that previously crashed, and confirm the turn persists normally with the reply-review strip appearing instead of a traceback.

## [2026-03-08 14:28:47 EDT] PRE-FLIGHT
Operator task:
Replace the animated decorative chat glyph bands with static chiaroscuro panel shading, reduce panel animation cost, and make the chat materially faster while preserving the dialogue-first cockpit.
Task checksum:
adam-tui-static-chiaroscuro-refresh-optimization-20260308
Repo situation:
Dirty worktree already includes the reply-surface redesign and the recent turn-index crash fix; this turn should stay bounded to TUI rendering/performance surfaces plus matching docs/tests.
Relevant spec surfaces read:
docs/TUI_SPEC.md, docs/KNOWN_LIMITATIONS.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, current chat/preview/render loop in eden/tui/app.py.
Natural-language contracts in force:
The TUI remains the primary runtime interface; telemetry stays visible but secondary; Adam/Brian transcript readability takes precedence over decorative effects; changes must remain stable on this Apple Silicon local machine.
Files/modules likely in scope:
eden/tui/app.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, README.md, codex_notes_garden.md.
Status register:
- Implemented:
Dialogue-first chat tape, inline typed review, merged runtime/event chyron, memgraph bus, aperture stack, conversation logs, operator-facing answer sanitization.
- Instrumented:
Live preview, memgraph bus animation, runtime/event trace surfaces.
- Conceptual:
Terminal-native neo-classical cyberspace shading with no animated chat ornament and a lighter prime-screen refresh path.
- Unknown:
Which hot path is dominating perceived slowness: the 450ms full-screen repaint loop, live preview churn while typing, repeated graph-health computation, transcript rebuild cost, or some combination.
Risks / invariants:
Do not regress transcript readability, preview correctness, keyboard focus flow, inline review, or signal-field utility. Avoid decorative glyphs inside the message surface that can be mistaken for semantic content.
Evidence plan:
Remove the whole-screen repaint interval, make transcript cards static, cache historical transcript renderables and graph-health reads, slow the signal-field tick, debounce preview harder, add at least one smoke-test ratchet for the simpler transcript surface / cached health path, then run py_compile and focused/full pytest.
Shortest proof path:
Patch eden/tui/app.py, update tests/test_tui_smoke.py and the relevant docs, run `./.venv/bin/python -m py_compile eden/tui/app.py tests/test_tui_smoke.py`, then `./.venv/bin/pytest -q tests/test_tui_smoke.py` and full `./.venv/bin/pytest -q`.

## [2026-03-08 14:31:34 EDT] POST-FLIGHT
Files changed:
eden/tui/app.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, README.md, codex_notes_garden.md
Specs changed:
docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, README.md
Natural-language contracts added/revised/preserved:
Preserved the dialogue-first cockpit and readable secondary telemetry stack; revised the chat-surface aesthetic contract from animated interior glyph bands to static chiaroscuro shading; revised the prime-screen refresh contract from periodic whole-screen repaint to event-driven refresh with cached heavy surfaces.
Behavior implemented or modified:
Removed the 450ms whole-screen `refresh_panels()` loop from the live chat screen; cached graph-health computation until the graph changes; cached historical transcript panel renderables per session and invalidated them only on graph/session mutation; slowed the signal-field animation tick; made preview refresh single-flight with a longer debounce while typing; removed decorative animated glyph bands from Brian/Adam/review/draft cards and replaced them with static shaded panel treatments plus darker, neo-classical cyberpunk/chiaroscuro color fields.
Evidence produced (tests / traces / commands / exports):
./.venv/bin/python -m py_compile eden/tui/app.py tests/test_tui_smoke.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py -> 1 passed; ./.venv/bin/pytest -q -> 32 passed
Status register changes:
- Implemented:
Static shaded transcript cards, event-driven prime-screen refresh, cached graph-health reads, cached historical transcript rendering, slower memgraph pulse cadence, and single-flight debounced preview refresh.
- Instrumented:
Signal-field animation and preview retrieval remain live, but now on a lighter cadence/path.
- Conceptual:
Terminal-native “shader” aesthetics remain constrained to color fields, borders, and dither-like static shading rather than true pixel shaders.
- Unknown:
No fresh screenshot artifact from this turn proves the final neo-classical cyberspace look or the perceived typing-speed improvement at the operator’s exact window geometry.
Truth-table / limitations updates:
Updated docs/TUI_SPEC.md to record static shaded transcript cards and event-driven refresh; updated docs/IMPLEMENTATION_TRUTH_TABLE.md for static transcript shading plus event-driven prime refresh; updated docs/KNOWN_LIMITATIONS.md to document the lighter refresh path and remaining preview/signal-field cost.
Remaining uncertainties:
The correctness path is proved, but the aesthetic/performance outcome still needs operator validation in a live session. If typing is still slower than acceptable, the next bounded target is live preview itself rather than panel repaint.
Next shortest proof path:
Launch the TUI, type a multi-line draft in a seeded session, confirm the transcript no longer shows interior glyph ornaments, and judge whether preview responsiveness is acceptable; if not, gate live preview behind a manual toggle or a larger idle delay.


## [2026-03-09 09:05:47 EDT] PRE-FLIGHT
Operator task:
Add a new TUI conversation-archive screen for browsing saved conversations with relational sorting/grouping, plus persisted virtual folder/tag metadata and direct transcript/session actions.
Task checksum:
adam-conversation-atlas-terminal-archive-20260309
Repo situation:
Dirty worktree already contains the recent TUI refresh optimization and turn-index crash fix; this turn should stay bounded to TUI archive surfaces, session metadata/query helpers, tests, and matching docs.
Relevant spec surfaces read:
docs/TUI_SPEC.md, docs/GRAPH_SCHEMA.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, conversation-log/session paths in eden/runtime.py, session storage in eden/storage/graph_store.py.
Natural-language contracts in force:
TUI remains the primary runtime surface; conversation logs are markdown artifacts under exports; SQLite remains the local persistence layer; new behavior must preserve the experiment/session ontology and keep claims truthful about virtual archive organization vs physical files.
Files/modules likely in scope:
eden/tui/app.py, eden/storage/graph_store.py, eden/runtime.py, tests/test_tui_smoke.py, tests/test_runtime_e2e.py, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, codex_notes_garden.md.
Status register:
- Implemented:
Conversation log markdown export per session; session metadata persistence; deck/history surfaces; session resume/new-session/profile flows.
- Instrumented:
Runtime/event traces and conversation-log sync already expose saved-session activity, but there is no dedicated archive browser.
- Conceptual:
A terminal-native conversation archive/atlas with relational folder/tag projections over the transcript corpus.
- Unknown:
How much metadata editing and grouping UX can be added cleanly in one bounded patch without destabilizing the prime chat flow.
Risks / invariants:
Do not break live chat focus flow, session resume, or transcript export. Keep all text logs under the existing export root while making folder/tag organization explicitly relational metadata, not a misleading filesystem duplication claim.
Evidence plan:
Add session-catalog query/update helpers, implement a modal archive browser with sorting/grouping and metadata editing, wire it into startup/runtime menus and bindings, add smoke/runtime tests, then run py_compile and focused/full pytest.
Shortest proof path:
Patch storage/runtime/TUI surfaces, verify the modal can list sessions and persist folder/tags, then run `./.venv/bin/python -m py_compile eden/tui/app.py eden/storage/graph_store.py eden/runtime.py tests/test_tui_smoke.py tests/test_runtime_e2e.py` followed by focused pytest and full `./.venv/bin/pytest -q`.

## [2026-03-09 09:23:06 EDT] POST-FLIGHT
Files changed:
eden/storage/graph_store.py, eden/runtime.py, eden/tui/app.py, tests/test_runtime_e2e.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md, docs/GRAPH_SCHEMA.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, codex_notes_garden.md
Specs changed:
docs/TUI_SPEC.md, docs/GRAPH_SCHEMA.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Natural-language contracts added/revised/preserved:
Added a new `Conversation Atlas` secondary TUI surface with an `all_texts` root shelf plus relational folder/tag projections over saved sessions. Preserved the existing contract that conversation logs remain markdown artifacts under the export root and clarified that atlas folders/tags are session-metadata projections rather than duplicate filesystem copies.
Behavior implemented or modified:
Added `GraphStore.list_session_catalog()` for experiment/session catalog queries with turn and feedback counts plus latest-turn excerpts. Added runtime archive helpers to normalize and persist `sessions.metadata_json.archive.folder` and `sessions.metadata_json.archive.tags`, expose atlas records, and build selected-session previews. Added a new `ConversationAtlasModal` with search, facet filtering, sort modes, projection summaries, selected-session preview, metadata editing, transcript opening, and session resume. Wired the atlas into the startup launcher, live action bus, deck, help text, and `F10`.
Evidence produced (tests / traces / commands / exports):
`./.venv/bin/python -m py_compile eden/tui/app.py eden/runtime.py eden/storage/graph_store.py tests/test_tui_smoke.py tests/test_runtime_e2e.py`; `./.venv/bin/pytest -q tests/test_runtime_e2e.py::test_conversation_archive_records_and_taxonomy` -> `1 passed`; `./.venv/bin/pytest -q tests/test_runtime_e2e.py` -> `4 passed`; `./.venv/bin/pytest -q tests/test_tui_smoke.py` -> `2 passed`; `./.venv/bin/pytest -q` -> `34 passed`
Status register changes:
- Implemented:
Terminal-native conversation atlas with persisted folder/tag taxonomy over saved sessions, startup/runtime access points, transcript open, and resume-session flow.
- Instrumented:
Atlas preview panels surface recent turns and recent feedback excerpts from persisted session data, but they remain bounded summaries rather than full replay timelines.
- Conceptual:
More ambitious DEVONthink-class boolean querying, arbitrary multi-parent folder graphs, or richer transcript diff/replay tooling remain out of scope.
- Unknown:
How the atlas feels with a very large real-world session library; the smoke path proves correctness, not large-catalog ergonomics.
Truth-table / limitations updates:
Updated TUI, graph-schema, truth-table, and limitations docs to record the atlas surface, persisted archive metadata, and the explicit limitation that the taxonomy is relational metadata rather than a physical transcript mirror.
Remaining uncertainties:
The atlas now works and is tested, but very large catalogs may need pagination, cached counts, or richer facet widgets later.
Next shortest proof path:
Launch the TUI, open `Conversation Atlas` from the action bus or `F10`, assign real folder/tag metadata to several sessions, then judge whether you want the next patch to focus on nested shelves, saved searches, or richer transcript preview/replay.

## [2026-03-09 10:10:00 EDT] PRE-FLIGHT
Operator task:
Walk the live TUI as a first-time operator, execute the main keyboard journeys, fix discoverability/focus/layout defects, and write operator-facing usage docs from verified behavior.
Task checksum:
adam-tui-user-journey-audit-20260309
Repo situation:
Dirty worktree includes prior atlas work plus exported conversation markdown updates. Live 80x24 TUI audit already exposed a first-run layout failure: top chrome dominates the screen, F6-F10 hints are clipped, and the composer path is not legible without trial-and-error.
Relevant spec surfaces read:
docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, relevant live-layout/runtime sections in eden/tui/app.py.
Natural-language contracts in force:
TUI is the primary runtime surface; claims must be grounded in executed journeys; keyboard-only recovery must remain possible; terminology may stay poetic only if the operator can still act without guesswork.
Files/modules likely in scope:
eden/tui/app.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, docs/USER_JOURNEYS.md, docs/HOW_TO_USE_ADAM_TUI.md, docs/UX_AUDIT_AND_REPAIRS.md, docs/FIRST_RUN_QUICKSTART.md, codex_notes_garden.md.
Status register:
- Implemented:
Live chat surface, action bus, aperture drawer, ingest modal, observatory/export actions, deck, inline review, conversation atlas.
- Instrumented:
Forensic/event bus and transcript export surfaces already report state changes, but first-run intent is not yet reliably legible at common terminal sizes.
- Conceptual:
Any larger redesign of the screen hierarchy beyond surgical discoverability/layout repairs.
- Unknown:
How many of the secondary journeys remain legible without fixes when exercised end-to-end on the live app.
Risks / invariants:
Do not break chat flow, atlas, ingest, or transcript/export behavior while compressing the prime screen. Keep first-action guidance visible inside the live surface, not only in help text.
Evidence plan:
Run the live TUI in PTY, execute Journeys 1 and 2 first, patch the smallest layout/help/focus defects, re-run, then continue through ingest, aperture, observatory, export, deck/review/archive, and keyboard-only flow. Add smoke coverage for repaired guidance/focus behavior and write docs from the verified final state.
Shortest proof path:
Repair the 80x24 launch path so the composer and send guidance are visible, prove send/focus recovery in smoke tests plus live PTY runs, then complete the remaining journeys and document only the behaviors re-run successfully.

## [2026-03-09 10:28:48 EDT] POST-FLIGHT
Files changed:
eden/tui/app.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md, docs/USER_JOURNEYS.md, docs/HOW_TO_USE_ADAM_TUI.md, docs/UX_AUDIT_AND_REPAIRS.md, docs/FIRST_RUN_QUICKSTART.md, codex_notes_garden.md
Specs changed:
docs/TUI_SPEC.md, docs/IMPLEMENTATION_TRUTH_TABLE.md, docs/KNOWN_LIMITATIONS.md
Natural-language contracts added/revised/preserved:
Preserved the dialogue-first TUI contract while adding an explicit compact-terminal contract: small terminals now prioritize transcript/composer/chyron legibility over simultaneous telemetry visibility. Revised the review contract so `F7` only promises an inline review surface when an Adam reply actually exists. Revised the export contract so the operator is told where artifacts were written.
Behavior implemented or modified:
Added responsive compact-mode layout logic to the live chat screen, including compact aperture view swap plus `Esc` recovery back to dialogue. Tightened first-action copy in the stage note, empty transcript panel, and composer hint. Fixed the `F10`/binding archive path to launch through a worker-safe modal flow. Ensured bootstrap/session-resume/new-session/archive-resume flows return focus to the composer. Guarded `Review` when there is no reply yet. Export status now includes the artifact directory path.
Evidence produced (tests / traces / commands / exports):
Live PTY runs at `80x24` before and after repair; pilot-driven live app runs at `80x24`, `120x30`, and `140x40`; observatory URL opened from the TUI and returned `HTTP 200`; export action wrote browser artifacts under `exports/<experiment_id>/`; transcript log action opened a markdown file under `exports/conversations/...`; `./.venv/bin/python -m py_compile eden/tui/app.py tests/test_tui_smoke.py tests/test_runtime_e2e.py`; `./.venv/bin/pytest -q tests/test_tui_smoke.py` -> `3 passed`; `./.venv/bin/pytest -q` -> `35 passed`
Status register changes:
- Implemented:
Compact first-run TUI path, compact `F8` aperture swap view, worker-safe `F10` archive binding, no-reply review guard, export-directory feedback, composer-focus return after session transitions, operator docs grounded in executed journeys.
- Instrumented:
UX audit evidence now includes live PTY and pilot-driven journey traces plus exported artifact directories from the pass.
- Conceptual:
Fully responsive footer hotkey legend, richer large-library atlas ergonomics, and a broader content-quality audit of real MLX ingest/retrieval remain outside this patch.
- Unknown:
Very large archive/session libraries and long-duration operator use on real MLX sessions still need broader ergonomic validation.
Truth-table / limitations updates:
Updated docs/TUI_SPEC.md for compact-mode chat behavior, compact aperture semantics, no-reply review behavior, and export path feedback. Updated docs/IMPLEMENTATION_TRUTH_TABLE.md for compact boot, `Esc` recovery, archive binding, review guard, and export-location feedback. Updated docs/KNOWN_LIMITATIONS.md to record the remaining narrow-footer clipping and the compact-mode dialogue-over-telemetry tradeoff.
Remaining uncertainties:
The core journeys are now verified, but the stock footer still clips later hotkeys on narrow terminals and the atlas has only been exercised against a small saved-session set. Real MLX retrieval quality after ingest was not re-audited here.
Next shortest proof path:
Run the same operator journeys on a real local-MLX session with a substantive source document, then decide whether the next patch should target footer responsiveness, atlas scaling, or retrieval-quality affordances.

## [2026-03-10T13:08:34Z] PRE-FLIGHT
Operator task:
- Identify what is generating large GitHub line-count spikes from working tree changes and add ignore rules to prevent it.
Task checksum:
- Root cause candidate: unignored runtime artifacts under `exports/`.
Repo situation:
- Working tree already contains local edits from prior active changes plus many untracked/ignored-generated artifacts.
Relevant spec surfaces read:
- AGENTS.md runtime contract; no ontology or turn-loop specs were changed.
Natural-language contracts in force:
- No ontology/turn-loop changes for this task; only artifact-control behavior in VCS handling.
Files/modules likely in scope:
- `.gitignore`
- `exports/` output directories
Status register:
- Implemented: none
- Instrumented: none
- Conceptual: none
- Unknown: whether ignore coverage includes all future export artifacts
Risks / invariants:
- Broad `exports/*/` ignore may hide newly generated artifacts intended for commit in a later workflow.
- Existing tracked files in `exports/` remain tracked and visible.
Evidence plan:
- Measure current untracked export line volume.
- Add `.gitignore` entries.
- Re-check `git ls-files -o --exclude-standard exports` and `git status --short`.
Shortest proof path:
- `git ls-files -o --exclude-standard exports | wc -l`
- `git status --short`

## [2026-03-10T13:08:34Z] POST-FLIGHT
Files changed:
- `.gitignore`
Specs changed:
- None (no normative contract doc needed for `.gitignore` hygiene adjustment)
Natural-language contracts added/revised/preserved:
- Preserved all prior contracts; only added VCS hygiene to avoid export artifacts in working tree churn.
Behavior implemented or modified:
- Added `exports/*/` to `.gitignore` to suppress new runtime export directories under `exports/` from untracked-file noise.
Evidence produced (tests / traces / commands / exports):
- `git ls-files -o --exclude-standard exports | wc -l` returned `0` after ignore rule.
- `git status --short` shows previous docs/code edits plus the `.gitignore` change, with no new untracked `exports/*` entries.
Status register changes:
- Implemented:
  - Git ignore hygiene fix for generated export artifacts.
- Instrumented: None
- Conceptual: None
- Unknown:
  - Whether all future exporter variants require additional exclusions (no evidence yet for formats outside current run set).
Truth-table / limitations updates:
- Not applicable.
Remaining uncertainties:
- If a future run needs tracked artifacts under `exports/<id>/`, it must use `git add -f` or a dedicated allowlist exception.
Next shortest proof path:
- Run one additional export workflow and confirm the generated files are still ignored.
## [2026-03-10T13:15:12Z] PRE-FLIGHT
Operator task:
- Produce a thorough observatory status brief for ChatGPT DeepResearch, grounded in code/spec evidence, and curate a zip bundle of relevant spec documents plus Codex notes into Downloads.
Task checksum:
- Need accurate current-state vs target-state language for the browser observatory, especially graph labeling, right-panel readability, and the incomplete attractor basin surface.
Repo situation:
- Working tree is dirty at `.DS_Store` only. No observatory code/spec edits are planned unless a documentation correction becomes necessary.
Relevant spec surfaces read:
- `docs/PROJECT_CHARTER.md`
- `docs/CANONICAL_ONTOLOGY.md`
- `docs/OBSERVATORY_SPEC.md`
- `docs/OBSERVATORY_INTERACTION_SPEC.md`
- `docs/OBSERVATORY_GEOMETRY_SPEC.md`
- `docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `docs/KNOWN_LIMITATIONS.md`
Natural-language contracts in force:
- TUI remains the primary runtime; browser observatory is an observability/export instrument.
- Memes are first-class; memodes are derived structures with provenance.
- Observatory claims require separation between implemented behavior, instrumented surfaces, conceptual intent, and unknowns.
Files/modules likely in scope:
- `eden/observatory/exporters.py`
- `eden/observatory/service.py`
- `tests/test_observatory_server.py`
- `tests/test_observatory_measurements.py`
- `exports/*/graph_knowledge_base.html`
- `exports/*/behavioral_attractor_basin.html`
- `/Users/brianray/Adam/codex_notes_garden.md`
- `/Users/brianray/Downloads/` deliverables
Status register:
- Implemented:
- Instrumented:
- Conceptual:
- Unknown:
Risks / invariants:
- Do not overstate the current GUI; the specs promise more than the current HTML ergonomics deliver.
- Keep the package bounded to documents that help external UI research without dumping irrelevant repo bulk.
Evidence plan:
- Inspect exporter code that emits the graph and basin HTML/JSON.
- Review observatory tests for validated behavior.
- Open current generated artifacts to confirm the UI complaints against the actual output.
- Produce a brief plus a curated zip in Downloads.
Shortest proof path:
- Read `eden/observatory/exporters.py` graph and basin renderers plus observatory tests.
- Verify generated artifacts under `exports/` and package the selected docs.
## [2026-03-10T13:22:16Z] POST-FLIGHT
Files changed:
- `/Users/brianray/Adam/codex_notes_garden.md`
- `/Users/brianray/Downloads/eden_observatory_research_packet_2026-03-10/README_PACKET.md`
- `/Users/brianray/Downloads/eden_observatory_research_packet_2026-03-10/brief/EDEN_observatory_status_brief_2026-03-10.md`
- `/Users/brianray/Downloads/eden_observatory_research_packet_2026-03-10/...` curated copied docs, notes, code, sample export, and screenshots
- `/Users/brianray/Downloads/eden_observatory_research_packet_2026-03-10_final.zip`
Specs changed:
- None
Natural-language contracts added/revised/preserved:
- Preserved the TUI-primary / observatory-secondary contract.
- Preserved the distinction between implemented observatory data paths and underimplemented browser presentation.
- Preserved the ontology boundary: memes first-class, memodes derived, measurement events as the observatory provenance bridge.
Behavior implemented or modified:
- No repo runtime behavior changed.
- Produced an external research packet for UI/DeepResearch handoff with a paste-ready observatory brief, relevant specs, current observatory code/tests, one sample export, and current screenshots.
Evidence produced (tests / traces / commands / exports):
- `./.venv/bin/pytest -q tests/test_observatory_measurements.py tests/test_observatory_server.py` -> `8 passed in 3.75s`
- Browser inspection of `graph_knowledge_base.html` and `behavioral_attractor_basin.html` from export `b178bed2-731e-4f8b-b5f8-a93d1300b2f7`
- Screenshots captured:
  - `/Users/brianray/Downloads/eden_observatory_research_packet_2026-03-10/screenshots/raw_capture_graph_surface.png`
  - `/Users/brianray/Downloads/eden_observatory_research_packet_2026-03-10/screenshots/raw_capture_attractor_basin.png`
- Verified packet contents with `find /Users/brianray/Downloads/eden_observatory_research_packet_2026-03-10 -maxdepth 3 -type f | sort`
- Verified final zip contents with `unzip -l /Users/brianray/Downloads/eden_observatory_research_packet_2026-03-10_final.zip`
Status register changes:
- Implemented:
  - External observatory research packet assembled and zipped for operator handoff.
- Instrumented: None
- Conceptual: None
- Unknown:
  - Whether the target UI should consolidate on Three.js across both surfaces or split graph and basin rendering across different stacks.
Truth-table / limitations updates:
- None; no repo capability status changed.
Remaining uncertainties:
- The current basin screenshot is explained by both UI immaturity and the sampled export having `turn_count = 1`; a richer multi-turn export was not generated in this turn.
- The graph and basin surfaces were audited from generated artifacts and source, not redesigned here.
Next shortest proof path:
- Feed the final zip and brief into DeepResearch, then decide whether the next build step is a design-spike document, a dedicated frontend architecture spike, or direct observatory UI implementation.

## [2026-03-10 16:08:51 EDT] PRE-FLIGHT
Operator task:
Implement the approved EDEN observatory live-first refactor: layered graph/basin payloads, stricter memode validation, new live API breadth, checked-in frontend bundle, and matching tests/docs.
Task checksum:
EDEN observatory v1 live-first refactor plan approved on 2026-03-10 with localStorage presets, deterministic clustering, explicit memode support allowlist/denylist, SSE invalidation events, stale-build guard, and HTTP-served static export constraint.
Repo situation:
Working tree clean at start. Current observatory remains Python exporters plus inline handwritten HTML/JS in `eden/observatory/exporters.py`; no existing frontend toolchain is present.
Relevant spec surfaces read:
`docs/CANONICAL_ONTOLOGY.md`, `docs/OBSERVATORY_SPEC.md`, `docs/OBSERVATORY_INTERACTION_SPEC.md`, `docs/OBSERVATORY_GEOMETRY_SPEC.md`, `docs/MEASUREMENT_EVENT_MODEL.md`, `docs/GEOMETRY_EVIDENCE_POLICY.md`, `docs/IMPLEMENTATION_TRUTH_TABLE.md`, `docs/KNOWN_LIMITATIONS.md`, and repo `AGENTS.md`.
Natural-language contracts in force:
Browser remains observability/export work, not the primary runtime chat surface. Memes remain first-class, memodes derived second-order assemblies, clusters derived summaries, attractors dynamic summaries, and layout/render coordinates are not evidence.
Files/modules likely in scope:
`/Users/brianray/Adam/eden/observatory/exporters.py`, `/Users/brianray/Adam/eden/observatory/service.py`, `/Users/brianray/Adam/eden/observatory/server.py`, `/Users/brianray/Adam/eden/storage/schema.py`, `/Users/brianray/Adam/eden/storage/graph_store.py`, `/Users/brianray/Adam/tests/test_observatory_measurements.py`, `/Users/brianray/Adam/tests/test_observatory_server.py`, `/Users/brianray/Adam/docs/*.md`, `/Users/brianray/Adam/web/observatory/*`, and checked-in frontend build assets under the observatory package.
Status register:
- Implemented:
  - Preview/commit/revert observatory flow, measurement ledger persistence, graph/basin/geometry exports, and minimal local API.
- Instrumented:
  - Existing geometry metrics, basin feature projection, and lightweight live server status.
- Conceptual:
  - Layered semantic/runtime/assembly payloads, deterministic cluster summaries, live transcript/runtime APIs, shell-page frontend bundle, and Quid-like graph UI grammar.
- Unknown:
  - Exact effort/risk for landing the full frontend plus backend breadth in one turn without regressions; stale-build guard and build pipeline are not yet present in code.
Risks / invariants:
Do not break preview/commit/revert semantics, measurement attribution, or the TUI-primary runtime contract. Keep export artifact filenames stable. Keep view presets out of authoritative payload planes. Avoid overclaiming implementation if verification is partial.
Evidence plan:
Run targeted observatory pytest coverage while refactoring backend contracts, add/extend tests for memode validation and new APIs, build the frontend bundle, and run the full `./.venv/bin/pytest -q` plus frontend verification commands.
Shortest proof path:
Land backend/store/payload changes first, wire server endpoints/SSE, scaffold and build the frontend shell against real payloads, update docs/truth tables, then prove with pytest and frontend build/test commands.

## [2026-03-10 16:40:22 EDT] POST-FLIGHT
Files changed:
- `/Users/brianray/Adam/eden/observatory/contracts.py`
- `/Users/brianray/Adam/eden/observatory/clustering.py`
- `/Users/brianray/Adam/eden/observatory/graph_planes.py`
- `/Users/brianray/Adam/eden/observatory/frontend_assets.py`
- `/Users/brianray/Adam/eden/observatory/exporters.py`
- `/Users/brianray/Adam/eden/observatory/service.py`
- `/Users/brianray/Adam/eden/observatory/server.py`
- `/Users/brianray/Adam/eden/runtime.py`
- `/Users/brianray/Adam/eden/tui/app.py`
- `/Users/brianray/Adam/tests/test_observatory_measurements.py`
- `/Users/brianray/Adam/tests/test_observatory_server.py`
- `/Users/brianray/Adam/web/observatory/...`
- `/Users/brianray/Adam/eden/observatory/static/observatory_app/...`
- `/Users/brianray/Adam/scripts/check_observatory_build_meta.py`
- `/Users/brianray/Adam/docs/CANONICAL_ONTOLOGY.md`
- `/Users/brianray/Adam/docs/OBSERVATORY_SPEC.md`
- `/Users/brianray/Adam/docs/OBSERVATORY_INTERACTION_SPEC.md`
- `/Users/brianray/Adam/docs/OBSERVATORY_GEOMETRY_SPEC.md`
- `/Users/brianray/Adam/docs/MEASUREMENT_EVENT_MODEL.md`
- `/Users/brianray/Adam/docs/GEOMETRY_EVIDENCE_POLICY.md`
- `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`
- `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
- Updated ontology, observatory, geometry, evidence, measurement, truth-table, and limitations surfaces to describe layered payload planes, deterministic cluster summaries, connected memode admissibility, browser-local view presets, live API breadth, SSE invalidation, HTTP-served static export, and build freshness semantics.
Natural-language contracts added/revised/preserved:
- Preserved TUI-primary runtime contract.
- Revised observatory contract from inline placeholder HTML to checked-in React/Sigma/Three shell with Python-authoritative payloads.
- Revised memode admissibility floor to require a connected qualifying semantic support subgraph with no passenger memes.
- Preserved measurement-first attribution boundary and kept browser view presets outside authoritative graph facts.
Behavior implemented or modified:
- Added authoritative graph payload planes (`semantic_*`, `runtime_*`, `assemblies`, `cluster_summaries`, `active_set_slices`) plus deterministic meme-only cluster computation and transfer-aware manual cluster labels.
- Tightened memode validation to explicit allowlist/denylist support edges, connected support-subgraph requirement, and returned `supporting_edge_ids`.
- Added live observatory read endpoints, runtime/model status, transcript/active-set endpoints, and SSE invalidation events.
- Replaced inline graph/basin/measurement/index HTML with thin shell pages that bootstrap the checked-in observatory bundle.
- Added checked-in React app with Sigma graph surface, Three basin surface, structured inspector cards, localStorage view presets, derived-status badges, and sparse-basin empty state.
- Added frontend build freshness metadata and CI/runtime verification script.
- Fixed unrelated TUI conversation-log thread misuse revealed by the full-suite proof path.
Evidence produced (tests / traces / commands / exports):
- `./.venv/bin/pytest -q tests/test_observatory_measurements.py tests/test_observatory_server.py` -> `14 passed in 5.64s`
- `npm --prefix web/observatory run test` -> `2 passed`
- `npm --prefix web/observatory run build` -> success, emitted checked-in bundle + `build-meta.json`
- `npm --prefix web/observatory run test:e2e` -> `2 passed`
- `./.venv/bin/python scripts/check_observatory_build_meta.py` -> `ok: true`
- `./.venv/bin/pytest -q` -> `41 passed in 16.16s`
Status register changes:
- Implemented:
  - Layered observatory payloads, deterministic semantic clustering, connected memode admissibility checks, live observatory read APIs, SSE invalidation, checked-in frontend shell, build freshness guard, and frontend/browser test harness.
- Instrumented:
  - Runtime build-freshness warning surface via `/api/status`.
- Conceptual:
  - No figure-generation jobs or richer View Studio controls landed in this turn.
- Unknown:
  - Large-graph frontend performance beyond the bounded smoke/test fixtures remains unproved in this turn.
Truth-table / limitations updates:
- Updated `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md` and `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md` to reflect the new observatory stack, payload contract, and HTTP-served export/runtime limits.
Remaining uncertainties:
- The React graph surface is functionally present, but it is not yet tuned for very large semantic graphs or richer assembly hull rendering beyond the current highlight/overlay path.
- Figure job persistence and a full View Studio control surface remain deferred.
Next shortest proof path:
- Exercise the new observatory shell against a heavier seeded experiment, then implement server-side analytics job persistence plus the View Studio / figure-generation path on top of the now-stable payload and shell contracts.

## [2026-03-11 09:41:10 EDT] PRE-FLIGHT
Operator task:
Fix the browser observatory open path so it opens a coherent experiment shell instead of the export-root directory listing, and ensure the linked observatory materials refresh before opening.
Task checksum:
Observed on 2026-03-11: TUI/CLI observatory open path lands on root directory listing and appears stale; approved observatory refactor already landed, so the open-target/export-refresh path is now the likely fault line.
Repo situation:
Working tree already contains the large observatory refactor from the prior turn and is dirty by design. Full repo pytest and frontend verification were green at the end of the previous turn.
Relevant spec surfaces read:
`docs/OBSERVATORY_SPEC.md`, `docs/IMPLEMENTATION_TRUTH_TABLE.md`, `docs/KNOWN_LIMITATIONS.md`, repo `AGENTS.md`, and current TUI/runtime observatory open-path code in `eden/tui/app.py`, `eden/runtime.py`, and `eden/app.py`.
Natural-language contracts in force:
Open Browser Observatory should open the current experiment's observatory shell, not a filesystem-style export root. Browser observatory remains export/observability work, with Python authoritative for refreshed payloads.
Files/modules likely in scope:
`/Users/brianray/Adam/eden/tui/app.py`, `/Users/brianray/Adam/eden/app.py`, possibly `/Users/brianray/Adam/eden/runtime.py`, observatory docs/status surfaces if behavior status changes, and `/Users/brianray/Adam/codex_notes_garden.md`.
Status register:
- Implemented:
  - Observability export generation, local observatory server, shell-page frontend bundle, and live API.
- Instrumented:
  - Runtime observatory status and frontend build freshness reporting.
- Conceptual:
  - None required for this bug fix.
- Unknown:
  - Whether the open path is stale because exports are not refreshed, because target URL selection falls back to server root, or both.
Risks / invariants:
Do not break the now-green observatory/test path. Preserve TUI-primary runtime behavior. Keep browser open path bounded to current/latest experiment export. Avoid loosening server root semantics.
Evidence plan:
Trace `_observatory_target_url`, TUI/CLI observatory open handlers, patch them to refresh exports and target `observatory_index.html`, then rerun the relevant observatory/TUI tests plus a focused smoke proof.
Shortest proof path:
Patch TUI and CLI observatory open handlers to regenerate exports before opening and to target an experiment-specific shell page, then prove with targeted pytest and a direct URL/target assertion if feasible.

## [2026-03-11 09:44:55 EDT] POST-FLIGHT
Files changed:
- `/Users/brianray/Adam/eden/tui/app.py`
- `/Users/brianray/Adam/eden/app.py`
- `/Users/brianray/Adam/tests/test_tui_smoke.py`
- `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
- None; this turn repaired an implemented observatory-open behavior to match the existing contract.
Natural-language contracts added/revised/preserved:
- Preserved the contract that Browser Observatory opens an experiment-specific observatory shell, not a raw exports root listing.
- Preserved Python-authoritative export refresh before browser observation.
Behavior implemented or modified:
- TUI observatory open now refreshes the current/latest experiment export before opening and targets `observatory_index.html` directly.
- CLI `python -m eden observatory --open` now does the same for the latest experiment when one exists.
Evidence produced (tests / traces / commands / exports):
- `./.venv/bin/pytest -q tests/test_tui_smoke.py tests/test_observatory_server.py` -> `10 passed in 16.48s`
- `./.venv/bin/pytest -q` -> `42 passed in 18.13s`
- Manual code trace confirmed the previous root-listing fallback came from `_observatory_target_url(...)->status["url"]` when no fresh export target existed.
Status register changes:
- Implemented:
  - Observability open path now regenerates the experiment shell before opening, eliminating the export-root directory-listing failure mode.
- Instrumented: None
- Conceptual: None
- Unknown:
  - No remaining unknown on the target URL/open-refresh path itself; broader observatory UX quality remains governed by the prior refactor state.
Truth-table / limitations updates:
- None; capability remained implemented, this turn repaired the open-path bug.
Remaining uncertainties:
- None specific to this bug beyond normal browser/open behavior on the host machine.
Next shortest proof path:
- Re-open Browser Observatory from the TUI and confirm the browser lands on `.../<experiment_id>/observatory_index.html` with freshly regenerated JSON-backed content.

## [2026-03-11 09:49:30 EDT] PRE-FLIGHT
Operator task:
Improve observatory loading transparency so the browser explains which payloads are loading, which are deferred, and why the page can appear stuck while large static exports are fetched.
Task checksum:
Observed on 2026-03-11: current experiment export pulls very large static payloads (`graph_knowledge_base.json` ~92 MB, `geometry_diagnostics.json` ~52 MB) while the UI only shows a generic loading banner.
Repo situation:
Working tree already contains the observatory open-path repair from earlier this morning. Targeted and full pytest were green after that fix.
Relevant spec surfaces read:
`docs/OBSERVATORY_SPEC.md`, repo `AGENTS.md`, and current frontend loader in `web/observatory/src/App.tsx`.
Natural-language contracts in force:
Browser observatory should remain coherent while payloads load. Loading state must keep render/evidence boundaries visible and should not hide which payload class is blocking or deferred.
Files/modules likely in scope:
`/Users/brianray/Adam/web/observatory/src/App.tsx`, `/Users/brianray/Adam/web/observatory/src/styles.css`, `/Users/brianray/Adam/web/observatory/src/App.test.tsx`, possibly observatory specs/limitations if the loading contract changes materially, and `/Users/brianray/Adam/codex_notes_garden.md`.
Status register:
- Implemented:
  - Observatory shell, static/live bootstrap, and coarse loading banner.
- Instrumented:
  - Build freshness and runtime observatory status.
- Conceptual:
  - Fine-grained payload loading diagnostics and staged/lazy loading behavior.
- Unknown:
  - Whether the best immediate fix is staged loading, better diagnostics, or both.
Risks / invariants:
Do not break the now-working observatory shell or live/static bootstrap. Preserve browser-local presets. Keep overview usable before graph/geometry finish.
Evidence plan:
Patch the frontend to track per-payload status, stage the heavy payloads, surface current/deferred/error states in the UI, then rerun frontend tests/build and the full pytest suite.
Shortest proof path:
Add payload status state + diagnostics banner, avoid blocking overview on heavy graph/geometry fetches, add frontend assertions for the new status surface, then rerun frontend and repo verification.

## [2026-03-11 09:49:59 EDT] POST-FLIGHT
Files changed:
- `/Users/brianray/Adam/web/observatory/src/App.tsx`
- `/Users/brianray/Adam/web/observatory/src/styles.css`
- `/Users/brianray/Adam/web/observatory/src/App.test.tsx`
- `/Users/brianray/Adam/web/observatory/vite.config.ts`
- `/Users/brianray/Adam/eden/observatory/static/observatory_app/index.js`
- `/Users/brianray/Adam/eden/observatory/static/observatory_app/style.css`
- `/Users/brianray/Adam/eden/observatory/static/observatory_app/build-meta.json`
- `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
- None. Existing observatory contracts already required explicit graph/basin payload provenance and HTTP-served static exports; this turn made the loader surface legible and staged heavy payload fetches accordingly.
Natural-language contracts added/revised/preserved:
- Preserved that Overview should remain usable before the large graph payload finishes.
- Preserved that geometry is a distinct derived payload and can be deferred until the operator actually opens the Geometry surface.
- Preserved that static-export mode is HTTP-served and may incur noticeable load time for large JSON artifacts, which now needs to be shown explicitly in the UI.
Behavior implemented or modified:
- Replaced the single opaque loading banner with per-payload status cards covering overview, measurements, basin, graph, geometry, transcript, and runtime payloads.
- Overview/measurement/basin now load first; graph loads in the background; geometry is deferred until the Geometry tab is opened.
- Overview cards now show payload readiness/source so the operator can tell whether graph counts are missing because the payload is still loading versus absent.
- Added placeholder copy in sidebar/surfaces so blank cards explain what is pending instead of appearing broken.
- Tightened frontend test config so `npm run test` excludes Playwright e2e specs and remains a unit-test gate.
Evidence produced (tests / traces / commands / exports):
- `npm --prefix /Users/brianray/Adam/web/observatory run test` -> `1 passed (3 tests)`.
- `npm --prefix /Users/brianray/Adam/web/observatory run test:e2e` -> `2 passed`.
- `npm --prefix /Users/brianray/Adam/web/observatory run build` -> success; rebuilt checked-in assets under `/Users/brianray/Adam/eden/observatory/static/observatory_app/`.
- `./.venv/bin/python /Users/brianray/Adam/scripts/check_observatory_build_meta.py` -> `ok: true`, source/build hashes match.
- `./.venv/bin/pytest -q` -> `42 passed in 18.37s`.
Status register changes:
- Implemented:
  - Observability loader now surfaces payload-level readiness/deferred/error state and stages heavy payload fetches instead of blocking the whole shell behind a generic banner.
- Instrumented:
  - Static/live payload source visibility is now exposed directly in the Overview/status surface.
- Conceptual:
  - No new conceptual observatory capability introduced in this turn.
- Unknown:
  - No remaining unknown about why the page can appear stalled on large exports; the heavy graph/geometry payload size remains real, but it is now surfaced explicitly instead of hidden.
Truth-table / limitations updates:
- None; this turn improved an implemented frontend behavior without changing the documented contract surface.
Remaining uncertainties:
- Large exported graph bundles are still large. This turn improves transparency and staging, not payload size reduction or server-side pagination.
Next shortest proof path:
- Re-open Browser Observatory on the current large export and confirm the Overview appears immediately with per-payload status cards, deferred Geometry, and background Graph readiness instead of an opaque loading banner.

## [2026-03-11 09:53:01 EDT] PRE-FLIGHT
Operator task:
Repair Browser Observatory launch from the TUI. Current operator report: selecting `Open Browser Observatory` now does nothing.
Task checksum:
The current TUI path still calls `webbrowser.open(target_url)` directly and assumes success. No fallback or failure reporting exists if the platform launcher returns false or raises.
Repo situation:
Working tree already contains the earlier observatory open-path target fix plus the frontend payload-status refactor. Full pytest was green after the loading-transparency change.
Relevant spec surfaces read:
`docs/TUI_SPEC.md`, `docs/OBSERVATORY_SPEC.md`, repo `AGENTS.md`.
Natural-language contracts in force:
`Open Browser Observatory` should ensure the local observatory is running and open the current experiment index page. Failure to launch must not be silent.
Files/modules likely in scope:
`/Users/brianray/Adam/eden/tui/app.py`, `/Users/brianray/Adam/eden/app.py`, `/Users/brianray/Adam/tests/test_tui_smoke.py`, and `/Users/brianray/Adam/codex_notes_garden.md`.
Status register:
- Implemented:
  - Observatory export generation, local observatory server, experiment-specific `observatory_index.html` targeting.
- Instrumented:
  - TUI feedback/status text for successful observatory launch target.
- Conceptual:
  - Robust browser-launch fallback and explicit launch-failure reporting.
- Unknown:
  - Whether the operator-visible failure is a `webbrowser.open` false-return path, an exception path, or a menu-action routing issue.
Risks / invariants:
Do not break the now-correct experiment-specific target URL. Preserve CLI and TUI launch semantics. Keep the fix bounded to launcher robustness and evidence it with tests.
Evidence plan:
Add a browser-launch helper with verified success/fallback/error reporting, route TUI and CLI observatory opens through it, add focused tests for fallback and failure visibility, then rerun targeted and full verification.
Shortest proof path:
Patch the launcher helper, prove fallback behavior with a monkeypatched test, then rerun `tests/test_tui_smoke.py`, observatory server tests, and full pytest.

## [2026-03-11 09:53:01 EDT] POST-FLIGHT
Files changed:
- `/Users/brianray/Adam/eden/browser.py`
- `/Users/brianray/Adam/eden/tui/app.py`
- `/Users/brianray/Adam/eden/app.py`
- `/Users/brianray/Adam/tests/test_tui_smoke.py`
- `/Users/brianray/Adam/tests/test_browser_open.py`
- `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
- None. Existing TUI/observatory contracts already required that the menu action open the current experiment shell; this turn made launcher failure explicit and added OS fallback.
Natural-language contracts added/revised/preserved:
- Preserved that `Open Browser Observatory` targets the current experiment's `observatory_index.html`.
- Preserved that the TUI is responsible for ensuring the local observatory is running before trying to open the browser.
- Revised the effective runtime behavior so browser-launch failure is not silent: the operator now gets explicit status feedback when the URL could not be opened.
Behavior implemented or modified:
- Added shared browser-launch helper `open_browser_url(...)` with `webbrowser.open(...)` first, platform fallback (`open` on macOS, `xdg-open` on Linux), and structured success/failure result.
- Routed TUI observatory open, startup observatory open, transcript-log open, and CLI `eden observatory --open` through the helper.
- TUI observatory action now records either a success trace with the launcher method or a failure message that includes the target URL and launcher error detail.
- CLI observatory open now prints a structured warning to stderr if the browser launcher fails instead of failing silently.
Evidence produced (tests / traces / commands / exports):
- `./.venv/bin/pytest -q /Users/brianray/Adam/tests/test_browser_open.py /Users/brianray/Adam/tests/test_tui_smoke.py /Users/brianray/Adam/tests/test_observatory_server.py` -> `13 passed in 18.71s`
- `python -m compileall /Users/brianray/Adam/eden/browser.py /Users/brianray/Adam/eden/tui/app.py /Users/brianray/Adam/eden/app.py` -> success
- `./.venv/bin/pytest -q` -> `45 passed in 20.51s`
Status register changes:
- Implemented:
  - Observatory browser launch now has verified success/failure handling with OS fallback instead of a blind `webbrowser.open(...)` call.
- Instrumented:
  - TUI/CLI status surfaces now expose browser-launch failure details instead of silently assuming success.
- Conceptual:
  - No new conceptual behavior introduced.
- Unknown:
  - No remaining unknown about the silent-launch path itself; if the browser still does not appear, the TUI will now surface the exact launcher failure detail.
Truth-table / limitations updates:
- None; this was a robustness repair to an already-implemented capability.
Remaining uncertainties:
- Browser launch still depends on host OS handlers. The difference now is that fallback is attempted and failure is surfaced explicitly.
Next shortest proof path:
- Trigger `Open Browser Observatory` from the TUI and verify either that the browser opens or that the TUI status line now reports the exact launcher failure with the observatory URL.

## [2026-03-11 10:05:09 EDT] PRE-FLIGHT
Operator task:
Repair the actual TUI action-menu path for `Open Browser Observatory`. Operator report after the launcher fallback fix: selecting the menu item still does nothing.
Task checksum:
Current code inspection shows the runtime action `Select` only updates the action/status panels on `Select.Changed`; it does not dispatch the selected action. Execution only occurs on `Enter` while the menu is focused.
Repo situation:
The browser-launch helper and failure reporting fix are already in the working tree and were previously verified. The remaining symptom points to menu wiring, not the launcher.
Relevant spec surfaces read:
`docs/TUI_SPEC.md`, repo `AGENTS.md`.
Natural-language contracts in force:
Choosing `Open Browser Observatory` from the top action bus should actually launch the observatory. The action menu must not require hidden extra steps when the operator selects an item.
Files/modules likely in scope:
`/Users/brianray/Adam/eden/tui/app.py`, `/Users/brianray/Adam/tests/test_tui_smoke.py`, `/Users/brianray/Adam/docs/TUI_SPEC.md`, and `/Users/brianray/Adam/codex_notes_garden.md`.
Status register:
- Implemented:
  - Browser launcher fallback and explicit launch-failure reporting.
- Instrumented:
  - TUI status surfaces for launch result.
- Conceptual:
  - Immediate action dispatch on menu selection.
- Unknown:
  - Whether `Select.Changed` on the Textual action menu can be used directly without introducing duplicate dispatch alongside the existing `Enter` path.
Risks / invariants:
Do not break keyboard execution of the action menu. Avoid duplicate execution if a change event is followed by Enter. Keep the observatory target URL and export refresh behavior intact.
Evidence plan:
Patch the action-menu change handlers to dispatch immediately with a short duplicate-suppression window, add a regression test that drives the actual menu selection path, update the TUI spec line, then rerun targeted and full pytest.
Shortest proof path:
Use `Select.Changed` to call `_execute_runtime_action("observatory")`, suppress immediate duplicate `Enter`, then prove with a real action-menu test plus full pytest.

## [2026-03-11 10:05:09 EDT] POST-FLIGHT
Files changed:
- `/Users/brianray/Adam/eden/tui/app.py`
- `/Users/brianray/Adam/tests/test_tui_smoke.py`
- `/Users/brianray/Adam/docs/TUI_SPEC.md`
- `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
- `/Users/brianray/Adam/docs/TUI_SPEC.md`
Natural-language contracts added/revised/preserved:
- Revised the TUI contract so choosing an item from the top action `Select` executes it immediately.
- Preserved keyboard execution: `Enter` on a focused action menu still executes the current value, with duplicate dispatch suppression.
- Preserved the observatory launcher contract itself: current experiment shell, export refresh, and launcher fallback behavior remain unchanged.
Behavior implemented or modified:
- Startup and runtime action menus now dispatch on `Select.Changed` instead of acting as passive selectors.
- Added duplicate-suppression windows so a just-dispatched selection does not fire again if the operator immediately presses `Enter`.
- Added regression coverage for the real runtime action-menu observatory path rather than only direct `handle_observatory()` calls.
Evidence produced (tests / traces / commands / exports):
- `./.venv/bin/pytest -q /Users/brianray/Adam/tests/test_tui_smoke.py /Users/brianray/Adam/tests/test_browser_open.py` -> `8 passed in 17.63s`
- `python -m compileall /Users/brianray/Adam/eden/tui/app.py` -> success
- `./.venv/bin/pytest -q` -> `46 passed in 23.39s`
Status register changes:
- Implemented:
  - Action-menu selection now executes the chosen observatory action directly.
- Instrumented:
  - No new instrumentation beyond the already-landed launcher status reporting.
- Conceptual:
  - None remaining for this path.
- Unknown:
  - No remaining unknown on the TUI action-menu route; the prior “nothing happens” path was caused by non-dispatching `Select.Changed` handlers.
Truth-table / limitations updates:
- None beyond the synchronized TUI spec sentence.
Remaining uncertainties:
- None specific to the menu route; repeated browser-open success still depends on host OS launch handling, which is now separately surfaced if it fails.
Next shortest proof path:
- Select `Open Browser Observatory` directly from the TUI action menu and confirm the browser opens without requiring an extra `Enter`.

## [2026-03-11 10:10:30 EDT] PRE-FLIGHT
Operator task:
Repair the TUI crash triggered while selecting `Open Browser Observatory`.
Task checksum:
Observed crash path: `ChatScreen.handle_focus_surface_change -> main_action_status_panel -> _conversation_stage -> _recent_turns -> GraphStore.list_turns`, raising `sqlite3.InterfaceError: bad parameter or other API misuse` while an observatory worker thread was also active. Current store code uses one shared SQLite connection with `check_same_thread=False`, locks writes, but leaves many read paths unlocked.
Repo situation:
Working tree already contains the action-menu immediate-dispatch change and launcher fallback/reporting fixes. The crash appears after that dispatch because background observatory work now overlaps with focus-triggered UI reads.
Relevant spec surfaces read:
`docs/TUI_SPEC.md`, repo `AGENTS.md`.
Natural-language contracts in force:
Selecting an action must not crash the TUI. The shared graph store must remain safe under the TUI's main-thread reads plus background worker usage.
Files/modules likely in scope:
`/Users/brianray/Adam/eden/storage/graph_store.py`, possibly tests under `/Users/brianray/Adam/tests/`, and `/Users/brianray/Adam/codex_notes_garden.md`.
Status register:
- Implemented:
  - Immediate menu dispatch for the observatory action.
- Instrumented:
  - Launcher success/failure reporting.
- Conceptual:
  - Store-level read serialization across worker/UI concurrency.
- Unknown:
  - Whether all read paths need locking or only the turn/session reads exercised by the TUI stack.
Risks / invariants:
Do not change graph semantics or persistence shape. Preserve current runtime behavior while serializing access to the shared SQLite connection. Keep the fix minimal and provable.
Evidence plan:
Add locked `_fetchone` / `_fetchall` helpers to `GraphStore`, route read queries through them, add a deterministic regression test that asserts SELECTs happen under the store lock, then rerun focused and full pytest.
Shortest proof path:
Patch store read methods onto locked helpers, add a proxy-based lock assertion test, then rerun the TUI/browser/store tests and full pytest.

## [2026-03-11 10:11:58 EDT] POST-FLIGHT
Files changed:
- `/Users/brianray/Adam/eden/storage/graph_store.py`
- `/Users/brianray/Adam/tests/test_graph_store.py`
- `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
- None. The fix preserves the existing TUI/runtime contract and hardens the persistence layer under concurrent UI/worker access.
Natural-language contracts added/revised/preserved:
- Preserved that selecting an action must not crash the TUI.
- Preserved that the graph store is the shared durable substrate across UI and worker operations.
- Revised the effective implementation so shared SQLite reads are serialized just like writes.
Behavior implemented or modified:
- Added locked `_fetchone(...)` / `_fetchall(...)` helpers to `GraphStore`.
- Routed store read paths through the same re-entrant lock already used by transactions, including turn/session, observatory snapshot, measurement, feedback, and search reads.
- This removes the shared-connection race between focus-triggered TUI reads and background observatory worker operations.
Evidence produced (tests / traces / commands / exports):
- `./.venv/bin/pytest -q /Users/brianray/Adam/tests/test_graph_store.py /Users/brianray/Adam/tests/test_tui_smoke.py /Users/brianray/Adam/tests/test_browser_open.py` -> `9 passed in 16.93s`
- `python -m compileall /Users/brianray/Adam/eden/storage/graph_store.py /Users/brianray/Adam/eden/tui/app.py` -> success
- `./.venv/bin/pytest -q` -> `47 passed in 22.82s`
Status register changes:
- Implemented:
  - Shared SQLite read access is now serialized under the store lock, eliminating the action-menu observatory crash path.
- Instrumented:
  - Added deterministic regression coverage that asserts SELECT queries run while the store lock is held.
- Conceptual:
  - None remaining for this crash path.
- Unknown:
  - No remaining unknown on the observed crash: it was caused by unlocked reads on a shared SQLite connection while background worker activity was in flight.
Truth-table / limitations updates:
- None; this was a runtime-hardening repair, not a change in feature scope.
Remaining uncertainties:
- None specific to this crash path. Future concurrency work should continue to treat the single shared SQLite connection as a serialized resource.
Next shortest proof path:
- Start the TUI, select `Open Browser Observatory`, and confirm the menu selection no longer crashes while the observatory starts/exports in the background.

## [2026-03-11 10:28:39 EDT] PRE-FLIGHT
Operator task:
Repair the repeated `Open Browser Observatory` action path and make the Action Bus show real observatory action progress instead of only the selected menu label.
Task checksum:
Observed operator report: selecting `Open Browser Observatory` again appears to do nothing; the Action Bus still reads `menu=Open Browser Observatory`, which reflects menu state rather than in-flight action state. Likely repeat-dispatch gap: selecting the same `Select` value again does not emit `Select.Changed`.
Repo situation:
Working tree is already dirty with prior observatory launcher, menu-dispatch, and GraphStore concurrency repairs. Unrelated `.DS_Store` is still modified. The current TUI contract and observatory server/export path are otherwise green under pytest.
Relevant spec surfaces read:
`/Users/brianray/Adam/docs/TUI_SPEC.md`, `/Users/brianray/Adam/docs/OBSERVATORY_SPEC.md`, repo `/Users/brianray/Adam/AGENTS.md`.
Natural-language contracts in force:
The TUI is the primary runtime surface. Action Bus text must remain an operator-readable contract surface, not a misleading reflection of stale widget state. `Open Browser Observatory` must be repeatable and should surface observatory startup/export/browser-launch phases without claiming speculative ETA.
Files/modules likely in scope:
`/Users/brianray/Adam/eden/tui/app.py`, `/Users/brianray/Adam/tests/test_tui_smoke.py`, `/Users/brianray/Adam/docs/TUI_SPEC.md`, `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`, `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`, `/Users/brianray/Adam/codex_notes_garden.md`.
Status register:
- Implemented:
  - Immediate action-menu dispatch on `Select.Changed`.
  - Observatory launcher/export/browser-open path with explicit success/failure feedback.
- Instrumented:
  - Browser launcher fallback reporting.
- Conceptual:
  - Action Bus progress semantics for long-running observatory work.
- Unknown:
  - Whether repeat selection failure is entirely due to unchanged `Select` value or whether browser launch also intermittently fails on the host.
Risks / invariants:
Do not regress keyboard execution or compact-layout behavior. Do not claim accurate remaining time; only accurate elapsed time is defensible. Keep the menu usable for repeated observatory launches.
Evidence plan:
Add explicit runtime action-progress state plus phase-based progress display, reset the runtime action menu to a neutral value after dispatch without triggering a second action, and add TUI tests for repeat observatory launch plus Action Bus progress text. Then rerun focused and full pytest.
Shortest proof path:
Patch `ChatScreen` to track active action metadata, render it in `main_action_bus_panel()`, suppress programmatic menu resets, and verify with `tests/test_tui_smoke.py` plus full `./.venv/bin/pytest -q`.

## [2026-03-11 10:34:41 EDT] POST-FLIGHT
Files changed:
- `/Users/brianray/Adam/eden/tui/app.py`
- `/Users/brianray/Adam/tests/test_tui_smoke.py`
- `/Users/brianray/Adam/docs/TUI_SPEC.md`
- `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`
- `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
- `/Users/brianray/Adam/docs/TUI_SPEC.md`
- `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`
Natural-language contracts added/revised/preserved:
- Revised the TUI contract so the Action Bus distinguishes `menu_focus` from active observatory work.
- Preserved the immediate-dispatch action-menu contract while making `Open Browser Observatory` repeatable through a neutral post-dispatch menu reset.
- Added an explicit boundary that the Action Bus observatory meter reports phase progress plus accurate elapsed time, not ETA.
Behavior implemented or modified:
- Added runtime action-progress state to `UiState`.
- `Open Browser Observatory` now surfaces `Queued launch`, `Ensuring observatory server`, `Exporting observatory payloads`, and `Opening browser` phases with a phase bar and elapsed time in the Action Bus.
- The runtime action menu resets back to `Review Last Reply` after observatory dispatch so re-selecting Observatory later emits a fresh `Select.Changed` event instead of silently doing nothing on the same selected value.
- Re-selecting Observatory while it is already running no longer silently no-ops; the TUI reports that the observatory action is already running and keeps the first worker alive.
- Added cancellation-safe observatory cleanup so action-progress state clears even if the worker is cancelled.
Evidence produced (tests / traces / commands / exports):
- `python -m compileall /Users/brianray/Adam/eden/tui/app.py /Users/brianray/Adam/tests/test_tui_smoke.py` -> success
- `./.venv/bin/pytest -q /Users/brianray/Adam/tests/test_tui_smoke.py /Users/brianray/Adam/tests/test_browser_open.py` -> `9 passed in 20.23s`
- `./.venv/bin/pytest -q` -> `48 passed in 26.23s`
Status register changes:
- Implemented:
  - Repeatable TUI observatory dispatch with explicit Action Bus progress and accurate elapsed-time reporting.
- Instrumented:
  - Action Bus observatory phase surface now exposes queued/server/export/browser-launch progress as a real runtime status signal.
- Conceptual:
  - Accurate remaining-time estimate for observatory launch remains intentionally unimplemented.
- Unknown:
  - Host OS browser acceptance after a successful launcher call is still outside EDEN's direct proof surface; EDEN can report the attempted URL and launch method but not prove the browser foregrounded.
Truth-table / limitations updates:
- Added the TUI observatory action-progress surface to `IMPLEMENTATION_TRUTH_TABLE.md`.
- Added the no-ETA boundary to `KNOWN_LIMITATIONS.md`.
Remaining uncertainties:
- The Action Bus now makes the in-flight observatory path legible, but if the host browser ignores both `webbrowser.open(...)` and the OS fallback, EDEN can only report the attempted launch path and failure detail.
Next shortest proof path:
- Start the TUI, select `Open Browser Observatory`, and confirm the Action Bus shows the observatory phases plus elapsed time and that the menu returns to `Review Last Reply` after dispatch so a later Observatory selection re-runs cleanly.


## [2026-03-11 11:15:00 EDT] PRE-FLIGHT
Operator task:
Build an observatory Playwright E2E audit from repo root that proves truthful browser-instrument behavior, adds deterministic browser fixtures/harness helpers, records per-journey evidence, and classifies absent browser mutation flows honestly.
Task checksum:
Requested journey battery J01-J17 with strict truth registers. Canonical contract slice: `docs/OBSERVATORY_SPEC.md`, `docs/OBSERVATORY_INTERACTION_SPEC.md`, `docs/OBSERVATORY_GEOMETRY_SPEC.md`, `docs/GEOMETRY_EVIDENCE_POLICY.md`, `docs/MEASUREMENT_EVENT_MODEL.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/IMPLEMENTATION_TRUTH_TABLE.md`, plus current UI code in `web/observatory/src/App.tsx`, `web/observatory/src/components/GraphPanel.tsx`, `web/observatory/src/components/BasinPanel.tsx`, and existing Python observatory tests.
Repo situation:
Working tree already dirty before this turn with modified `.DS_Store` and untracked `docs.zip`. Existing Playwright config and a minimal E2E spec already exist under `web/observatory/`, but current React UI appears strongest on read/inspect behavior. Server-side preview/commit/revert contracts exist in Python; browser exposure is not yet proved.
Relevant spec surfaces read:
`/Users/brianray/Adam/docs/OBSERVATORY_SPEC.md`, `/Users/brianray/Adam/docs/OBSERVATORY_INTERACTION_SPEC.md`, `/Users/brianray/Adam/docs/OBSERVATORY_GEOMETRY_SPEC.md`, `/Users/brianray/Adam/docs/GEOMETRY_EVIDENCE_POLICY.md`, `/Users/brianray/Adam/docs/MEASUREMENT_EVENT_MODEL.md`, `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`, `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`, `/Users/brianray/Adam/AGENTS.md`.
Natural-language contracts in force:
The observatory is a live-first measurement instrument, not a generic graph IDE. Inspect is read-only. Layout, coordinate modes, basin lift modes, and browser-local presets must never masquerade as evidence or graph mutation. Preview is separate from commit. Revert is explicit and ledgered. Static versus live source mode must remain explicit. Browser-local presets stay non-authoritative and absent from the measurement ledger.
Files/modules likely in scope:
`/Users/brianray/Adam/web/observatory/src/App.tsx`, `/Users/brianray/Adam/web/observatory/src/components/GraphPanel.tsx`, `/Users/brianray/Adam/web/observatory/src/components/BasinPanel.tsx`, `/Users/brianray/Adam/web/observatory/playwright.config.ts`, `/Users/brianray/Adam/web/observatory/tests/e2e/**`, `/Users/brianray/Adam/web/observatory/tests/fixtures/**`, `/Users/brianray/Adam/docs/OBSERVATORY_E2E_AUDIT.md`, `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`, `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`, `/Users/brianray/Adam/codex_notes_garden.md`.
Status register:
- Implemented:
  - React observatory shell exposes source-mode badge, stale-build warning, payload status, deferred geometry loading, graph/basin/measurement read surfaces, inspector cards/json toggle, browser-local view presets, and SSE refresh wiring in code.
  - Python observatory server exposes live API, preview/commit/revert endpoints, measurement-events payloads, and compact SSE invalidation events under pytest.
- Instrumented:
  - Existing Playwright config and minimal static-fixture smoke tests.
- Conceptual:
  - Browser GUI preview/commit/revert/edit/memode mutation workflows until actual React controls are proved.
  - Runtime-bridge causality in the browser until a visible runtime surface is proved.
- Unknown:
  - Whether current browser UI exposes any hidden mutation controls beyond the read surfaces already seen in `App.tsx`.
  - Whether current fixtures are sufficient to prove cross-surface coherence, sparse honesty, payload degradation, and live/static parity without augmentation.
Risks / invariants:
Do not invent browser mutation workflows absent from the UI. Prefer public DOM/ARIA selectors; add narrow stable hooks only where canvas/custom rendering blocks observability. Keep browser-local preset state non-authoritative. Do not let static export mode silently fall back to live claims. Preserve exact repository vocabulary around meme, memode, observatory, and measurement event.
Evidence plan:
Inspect the existing E2E harness and export fixtures, add deterministic live/static/failure/SSE fixtures or a small local harness, add Playwright helpers for network/SSE/ledger/localStorage/source-mode assertions, patch UI with narrow test hooks only where public DOM is insufficient, run Chromium-first journeys plus smaller Firefox/WebKit smoke journeys, and write `docs/OBSERVATORY_E2E_AUDIT.md` with per-journey register/evidence/gap classification.
Shortest proof path:
Prove J01-J09 and J17 against deterministic browser fixtures/harnesses first, classify J10-J14 as pass only if a real GUI path exists, otherwise record exact GUI contract gaps with DOM/code proof, then add P2 parity/resilience coverage and rerun Playwright plus repo pytest.


## [2026-03-11 12:00:20 EDT] POST-FLIGHT
Files changed:
- `/Users/brianray/Adam/web/observatory/src/App.tsx`
- `/Users/brianray/Adam/web/observatory/src/components/GraphPanel.tsx`
- `/Users/brianray/Adam/web/observatory/src/components/BasinPanel.tsx`
- `/Users/brianray/Adam/web/observatory/playwright.config.ts`
- `/Users/brianray/Adam/web/observatory/tests/e2e/harness/fixtures.mjs`
- `/Users/brianray/Adam/web/observatory/tests/e2e/harness/server.mjs`
- `/Users/brianray/Adam/web/observatory/tests/e2e/helpers.ts`
- `/Users/brianray/Adam/web/observatory/tests/e2e/observatory.spec.ts`
- `/Users/brianray/Adam/docs/OBSERVATORY_E2E_AUDIT.md`
- `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`
- `/Users/brianray/Adam/eden/observatory/static/observatory_app/build-meta.json`
- `/Users/brianray/Adam/eden/observatory/static/observatory_app/index.js`
Specs changed:
- `/Users/brianray/Adam/docs/OBSERVATORY_E2E_AUDIT.md`
- `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`
Natural-language contracts added/revised/preserved:
- Added the browser-proof audit surface with per-journey register/evidence/gap classification.
- Revised truth surfaces so browser-local presets, read/inspect journeys, and GUI mutation gaps are stated honestly.
- Preserved the normative observatory contract while downgrading absent React mutation/runtime surfaces to browser UI gaps instead of overclaiming implementation.
Behavior implemented or modified:
- Added deterministic Playwright harness fixtures for live/static/stale/unavailable/partial/heavy/hash-mismatch scenarios plus SSE invalidation control.
- Added browser E2E helpers for source-mode checks, payload-status checks, ledger diffs, localStorage diffs, SSE capture, and artifact persistence.
- Added accessible text-access controls for graph entities, relations, basin turns, transcript turns, and inspector cross-surface state.
- Fixed Graph/Basin renderer fallback so headless or no-WebGL contexts show explicit renderer-unavailable notes instead of blank panels.
- Fixed browser-local preset hydration so reload restores the saved graph view without leaking into the wrong manifest hash.
- Fixed Geometry error handling so real HTTP failures surface as scoped in-panel diagnostics instead of generic deferred copy.
Evidence produced (tests / traces / commands / exports):
- `npm --prefix web/observatory test`
- `npm --prefix web/observatory run build`
- `npm --prefix web/observatory run test:e2e -- --project=chromium --output=test-results/chromium-final`
- `npm --prefix web/observatory run test:e2e -- --project=firefox --output=test-results/firefox-final`
- `npm --prefix web/observatory run test:e2e -- --project=webkit --output=test-results/webkit-final`
- `npx playwright install firefox webkit`
- `./.venv/bin/pytest -q` -> `48 passed in 26.20s`
- Durable browser evidence bundles under `/Users/brianray/Adam/web/observatory/test-results/chromium-final`, `/Users/brianray/Adam/web/observatory/test-results/firefox-final`, and `/Users/brianray/Adam/web/observatory/test-results/webkit-final` with `Jxx.json`, `Jxx.png`, and `Jxx.html` artifacts.
Status register changes:
- Implemented:
  - Chromium browser proof for J01-J05, J07-J09, J15-J17.
  - Firefox/WebKit smoke proof for J01, J05, and J17.
  - Honest Graph/Basin renderer fallback, scoped Geometry failure diagnostics, and browser-local preset restore.
- Instrumented:
  - Stable accessible names and persisted Playwright journey evidence with network/SSE/ledger/localStorage traces.
- Conceptual:
  - J06 coordinate-mode compare surface in the current React UI.
  - J10-J14 measure/edit/memode/revert/runtime-causality flows in the current React UI.
- Unknown:
  - No additional browser observatory unknowns remain in the audited journey set; remaining gaps are classified as conceptual GUI absences rather than unknown behavior.
Truth-table / limitations updates:
- Added the Playwright browser audit row to `IMPLEMENTATION_TRUTH_TABLE.md`.
- Replaced overclaimed browser interaction rows with server-side/browser-gap distinctions.
- Updated `KNOWN_LIMITATIONS.md` with the current read/inspect-first React posture and the explicit WebGL fallback boundary.
Remaining uncertainties:
- Server-side preview/commit/revert and runtime-bridge contracts are still not browser-proved because the current React bundle does not surface those controls.
- Firefox/WebKit coverage remains intentionally smoke-scoped to J01, J05, and J17 rather than the full Chromium journey battery.
Next shortest proof path:
- If browser mutation work is in scope next, surface explicit MEASURE/EDIT/REVERT/runtime-causality controls in the React UI and then replace the J06/J10-J14 gap proofs with browser mutation evidence in the same harness.
## [2026-03-11 12:07:07 EDT] PRE-FLIGHT
Operator task:
Instantiate a first truthful Tanakh tool-surface vertical slice inside the existing EDEN observatory, using the attached PDF plus the observatory/spec stack as requirements.
Task checksum:
e47b6eae4afece2219c010e922ab1c0ea5613c18b5e855eb46b7eddffbc45f98
Repo situation:
Root `AGENTS.md` is in force. Working tree is dirty only at `.DS_Store`. Existing observatory stack is already live: Python exporter/service/server plus checked-in React+Vite bundle under `web/observatory`.
Relevant spec surfaces read:
`docs/OBSERVATORY_SPEC.md`, `docs/OBSERVATORY_INTERACTION_SPEC.md`, `docs/MEASUREMENT_EVENT_MODEL.md`, `docs/GEOMETRY_EVIDENCE_POLICY.md`, `docs/OBSERVATORY_GEOMETRY_SPEC.md`, `docs/IMPLEMENTATION_TRUTH_TABLE.md`, `docs/TUI_SPEC.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/CANONICAL_ONTOLOGY.md`, `docs/PROJECT_CHARTER.md`.
Natural-language contracts in force:
TUI remains primary. Browser observatory is additive and measurement-facing. Observation must not silently mutate the graph. Layout/rendering is never evidence. Memes remain first-class and memodes remain derived. New Tanakh outputs must carry provenance and derived-status labels.
Files/modules likely in scope:
`eden/runtime.py`, `eden/observatory/service.py`, `eden/observatory/server.py`, `eden/observatory/exporters.py`, `web/observatory/src/App.tsx`, `web/observatory/src/components/BasinPanel.tsx`, `web/observatory/src/styles.css`, new `eden/tanakh/*`, new tests/harness files, relevant docs truth surfaces, and observatory frontend build artifacts.
Status register:
- Implemented:
  - Observatory export/service/server path with live API and sidecar export artifacts.
  - React observatory shell with existing graph/basin/geometry/measurement surfaces.
  - Measurement-event persistence and preview/commit/revert semantics server-side.
- Instrumented:
  - Browser SSE refresh, checked-in bundle build metadata, Playwright browser proof for current observatory surfaces.
- Conceptual:
  - Tanakh tool-surface, Tanakh artifact family, Hebrew render validation harness, Tanakh-specific observatory UI.
- Unknown:
  - No repo evidence yet for Tanakh substrate tooling, deterministic Tanakh analyzers, scene compiler, or Hebrew render validation.
Risks / invariants:
Do not overclaim Hebrew rendering. Do not force whole Tanakh text into Three geometry. Avoid unlicensed dependencies. Keep Python authoritative for provenance/export paths. Prefer sidecar artifacts over fake first-class measurement integration if schema/UI extension grows non-trivial.
Evidence plan:
Primary-source research memo with official URLs. Deterministic Tanakh tool tests. Scene hash determinism test. Render-validation artifact JSON plus screenshots. Frontend build proof. Repo pytest proof path. Exported Tanakh artifacts under the existing observatory export root.
Shortest proof path:
Build Tanach.us fetch/verify/index tooling and local analyzers first; compile one deterministic scene for Ezekiel 1; expose it through observatory sidecar payloads plus one live API; render canonical text in DOM and derived scene in Three; prove determinism and render artifact generation with tests/harnesses; then update docs/truth surfaces.
## [2026-03-11 12:37:45 EDT] POST-FLIGHT
Files changed:
- `/Users/brianray/Adam/eden/tanakh/__init__.py`
- `/Users/brianray/Adam/eden/tanakh/service.py`
- `/Users/brianray/Adam/eden/config.py`
- `/Users/brianray/Adam/eden/runtime.py`
- `/Users/brianray/Adam/eden/observatory/exporters.py`
- `/Users/brianray/Adam/eden/observatory/service.py`
- `/Users/brianray/Adam/eden/observatory/server.py`
- `/Users/brianray/Adam/scripts/sync_tanakh_uxlc.py`
- `/Users/brianray/Adam/scripts/run_tanakh_render_validation.py`
- `/Users/brianray/Adam/web/observatory/src/App.tsx`
- `/Users/brianray/Adam/web/observatory/src/components/TanakhPanel.tsx`
- `/Users/brianray/Adam/web/observatory/src/components/TanakhScenePanel.tsx`
- `/Users/brianray/Adam/web/observatory/src/styles.css`
- `/Users/brianray/Adam/tests/conftest.py`
- `/Users/brianray/Adam/tests/test_tanakh_tools.py`
- `/Users/brianray/Adam/tests/test_observatory_server.py`
- `/Users/brianray/Adam/tests/test_runtime_e2e.py`
- `/Users/brianray/Adam/docs/OBSERVATORY_SPEC.md`
- `/Users/brianray/Adam/docs/MEASUREMENT_EVENT_MODEL.md`
- `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`
- `/Users/brianray/Adam/eden/observatory/static/observatory_app/build-meta.json`
- `/Users/brianray/Adam/eden/observatory/static/observatory_app/index.js`
- `/Users/brianray/Adam/eden/observatory/static/observatory_app/style.css`
Specs changed:
- `/Users/brianray/Adam/docs/OBSERVATORY_SPEC.md`
- `/Users/brianray/Adam/docs/MEASUREMENT_EVENT_MODEL.md`
- `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`
Natural-language contracts added/revised/preserved:
- Added a Tanakh observatory sidecar contract with explicit artifact families, live read/run endpoints, provenance payload requirements, and the boundary that Tanakh runs are not first-class measurement events yet.
- Preserved the TUI-primary / browser-additive contract and the rule that layout/rendering is not evidence.
- Preserved the measurement-event model by keeping Tanakh runs in dedicated sidecars instead of silently mutating the measurement schema.
Behavior implemented or modified:
- Added Tanach.us UXLC substrate sync, manifest, and index generation with version/build/hash/source metadata and truthful fetch-timestamp handling.
- Added deterministic Tanakh tool functions for passage retrieval, gematria, notarikon, temurah, and a replayable merkavah scene compiler with scene-node citation linkage.
- Added Tanakh observatory export sidecars, live API endpoints, overview integration, and a React surface with canonical reader, analyzer cards, provenance/debug panes, and a derived Three scene.
- Added a Hebrew render-validation harness that emits oracle/HTML/JSON artifacts and requires explicit manual glyph-order/mark-placement review.
- Added offline Tanakh test fixtures plus deterministic service/runtime/server proofs.
Evidence produced (tests / traces / commands / exports):
- `./.venv/bin/python -m compileall eden tests`
- `./.venv/bin/pytest -q tests/test_tanakh_tools.py tests/test_observatory_server.py tests/test_runtime_e2e.py` -> `13 passed`
- `./.venv/bin/pytest -q` -> `51 passed in 26.90s`
- `npm --prefix web/observatory run build`
- `npm --prefix web/observatory run test`
- `./.venv/bin/python scripts/sync_tanakh_uxlc.py --force`
- `./.venv/bin/python scripts/run_tanakh_render_validation.py --ref 'Ezek 1:1-5'`
- Artifact paths:
  - `/Users/brianray/Adam/data/tanakh_cache/tanakh_manifest.json`
  - `/Users/brianray/Adam/data/tanakh_cache/tanakh_index.json`
  - `/Users/brianray/Adam/exports/tanakh_validation/tanakh_surface.json`
  - `/Users/brianray/Adam/exports/tanakh_validation/tanakh_render_validation.json`
  - `/Users/brianray/Adam/exports/tanakh_validation/tanakh_render_validation.html`
Status register changes:
- Implemented:
  - Tanach.us substrate sync/index/manifest pipeline.
  - Deterministic Tanakh analyzers and merkavah scene compiler.
  - Tanakh observatory sidecar surface and live run/read API wiring.
- Instrumented:
  - Hebrew render-validation harness with oracle capture and manual-review HTML/JSON artifacts.
- Conceptual:
  - HarfBuzz-backed Hebrew shaping integration.
  - First-class Tanakh measurement-event schema participation and preview/commit/revert semantics.
- Unknown:
  - No unknowns remain in the implemented vertical slice; 3D Hebrew glyph correctness beyond the manual-review harness remains intentionally unclaimed rather than unknown.
Truth-table / limitations updates:
- Added Tanakh substrate/tool-surface/render-validation rows to `IMPLEMENTATION_TRUTH_TABLE.md`.
- Added Tanakh render and measurement-sidecar boundaries to `KNOWN_LIMITATIONS.md`.
- Added Tanakh artifact/live-endpoint contract text to `OBSERVATORY_SPEC.md`.
- Added Tanakh non-event sidecar boundary to `MEASUREMENT_EVENT_MODEL.md`.
Remaining uncertainties:
- The render-validation harness proves artifact generation and oracle capture, but not automatic glyph-placement correctness for niqqud/cantillation in 3D or worker-shaped text.
- The fetched Tanakh cache under `/Users/brianray/Adam/data/tanakh_cache/` is a generated local artifact, not a checked-in repo fixture.
Next shortest proof path:
- If Hebrew scene text fidelity must move beyond the DOM canonical reader, add a browser proof harness that compares Troika-rendered labels against the current validation oracle and only escalate to HarfBuzz-based shaping if that proof fails.
## [2026-03-11 13:00:44 EDT] PRE-FLIGHT
Operator task:
Add ignore rules for generated material that is inflating the pending git commit.
Task checksum:
05bc5b7f0fb1d4fe64b75f8fa614825f6e1f6d8d001c59f7bd091c7115cb6294
Repo situation:
Tanakh vertical-slice work is still live in the tree. The main inflation source is newly generated `data/tanakh_cache/` with the fetched UXLC archive plus extracted `Books/*.xml`; a smaller generated Vite test-cache file under `web/observatory/node_modules/.vite/` is also showing as modified.
Relevant spec surfaces read:
Root `AGENTS.md` only. No behavioral/product spec surface is affected by this turn; this is repository hygiene.
Natural-language contracts in force:
Keep the checked-in observatory bundle as contract surface. Do not hide intentional source/build artifacts; only ignore generated local cache/test material.
Files/modules likely in scope:
`/Users/brianray/Adam/.gitignore`, `/Users/brianray/Adam/codex_notes_garden.md`.
Status register:
- Implemented:
  - Tanakh substrate cache generation under `data/tanakh_cache/`.
- Instrumented:
  - None.
- Conceptual:
  - None.
- Unknown:
  - Whether any tracked generated file beyond the Tanakh cache is materially inflating the commit.
Risks / invariants:
Do not ignore checked-in observatory bundle outputs that the repo treats as runtime contract. Avoid broad ignores that would hide source files or durable exports.
Evidence plan:
Inspect `git status`, inspect `.gitignore`, add narrow ignore rules, then verify ignored status.
Shortest proof path:
Ignore `data/tanakh_cache/` and the local Vite cache directory, then confirm `git status --ignored` shows `data/` suppressed.
## [2026-03-11 13:00:44 EDT] POST-FLIGHT
Files changed:
- `/Users/brianray/Adam/.gitignore`
- `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
- None. Repository hygiene only.
Natural-language contracts added/revised/preserved:
- Preserved the rule that checked-in observatory bundle assets remain visible contract files.
- Added narrow ignore coverage for Tanakh substrate cache material and local Vite cache material only.
Behavior implemented or modified:
- Added `data/tanakh_cache/` to `.gitignore`.
- Added `web/observatory/node_modules/.vite/` to `.gitignore`.
Evidence produced (tests / traces / commands / exports):
- `git status --short`
- `git diff --numstat -- . ':(exclude).DS_Store'`
- `git status --short --ignored`
Status register changes:
- Implemented:
  - Generated Tanakh cache is now ignored for future adds.
  - Local Vite cache directory is now ignored for future adds.
- Instrumented:
  - None.
- Conceptual:
  - None.
- Unknown:
  - The modified `web/observatory/node_modules/.vite/.../results.json` entry remains visible because it is already tracked; `.gitignore` does not retroactively hide tracked files.
Truth-table / limitations updates:
- None.
Remaining uncertainties:
- If the tracked Vite results file should also disappear from the pending commit, it needs a separate cleanup/removal step rather than another ignore rule.
Next shortest proof path:
- Remove or restore the already tracked Vite results file if you want the pending diff trimmed further.
## [2026-03-12 12:15:37 EDT] PRE-FLIGHT
Operator task:
Refresh the observatory browser truth audit: tighten public UI state semantics, harden Playwright evidence emission, split J16 into HTTP-served static parity vs unsupported `file://`, and update browser truth surfaces without flattening backend truth.
Task checksum:
46f6e6c39efd7f9c0b22ee852ce2685dab874fd3df4a7995cf5bd26f91483152
Repo situation:
Existing observatory browser audit infrastructure is already present under `web/observatory/tests/e2e/` plus `docs/OBSERVATORY_E2E_AUDIT.md`. Current worktree is dirty in unrelated files only: `.DS_Store` modified and `docs.zip` deleted. Current execution revalidated baseline proof before edits: Vitest 3/3, pytest 14/14 on observatory server/measurement tests, Playwright Chromium 17/17, Firefox/WebKit smoke 6/6.
Relevant spec surfaces read:
- `docs/OBSERVATORY_SPEC.md`
- `docs/OBSERVATORY_INTERACTION_SPEC.md`
- `docs/OBSERVATORY_GEOMETRY_SPEC.md`
- `docs/GEOMETRY_EVIDENCE_POLICY.md`
- `docs/MEASUREMENT_EVENT_MODEL.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/IMPLEMENTATION_TRUTH_TABLE.md`
Natural-language contracts in force:
Browser proof must privilege observatory truth over rendering. Inspect remains read-only. Layout/coordinate/lift/preset changes must not masquerade as evidence or graph mutation. Browser-local presets remain non-authoritative and absent from the measurement ledger. Backend/server implementation truth must remain separate from browser exposure truth.
Files/modules likely in scope:
- `/Users/brianray/Adam/web/observatory/src/App.tsx`
- `/Users/brianray/Adam/web/observatory/src/App.test.tsx`
- `/Users/brianray/Adam/web/observatory/tests/e2e/observatory.spec.ts`
- `/Users/brianray/Adam/web/observatory/tests/e2e/helpers.ts`
- `/Users/brianray/Adam/docs/OBSERVATORY_E2E_AUDIT.md`
- `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`
- `/Users/brianray/Adam/codex_notes_garden.md`
Status register:
- Implemented:
  - Browser proof for J01-J05, J07-J09, J15, J17 was reproduced in this execution.
  - Backend/server observatory preview/commit/revert and measurement-event semantics were reproduced by pytest in this execution.
- Instrumented:
  - Existing Playwright harness already records network, SSE, screenshot, and DOM artifacts per journey, but does not yet fail fast on missing/empty artifact files.
- Conceptual:
  - None claimed for browser truth at pre-flight; J06 and J10-J14 require fresh browser classification after edits/rerun.
- Unknown:
  - Whether J06 still deserves a browser truth downgrade after public-state semantic cleanup and rerun.
  - Whether any current audit language still collapses backend truth into browser truth after this refresh.
Risks / invariants:
Do not invent absent React mutation flows. Keep Playwright as the canonical browser surface. Use `role=tab` + `aria-selected` for tabs, `aria-checked` for exclusive radio-like controls, and `data-state="active"` only where no narrower ARIA pattern fits. Do not rely on CSS classes for browser truth assertions after this turn.
Evidence plan:
Edit App semantics and tests, add explicit `file://` negative proof, refresh audit/truth docs, then rerun Vitest, observatory pytest targets, Playwright Chromium full battery, and Firefox/WebKit smoke with fresh artifact directories.
Shortest proof path:
Make semantic-state changes in the React shell, rewrite Playwright active-state assertions, split J16 with a real exported `observatory_index.html` `file://` proof, update truth surfaces, and rerun the browser/server proof stack from repo root.
## [2026-03-12 12:28:17 EDT] POST-FLIGHT
Files changed:
- `/Users/brianray/Adam/web/observatory/src/App.tsx`
- `/Users/brianray/Adam/web/observatory/src/App.test.tsx`
- `/Users/brianray/Adam/web/observatory/tests/e2e/helpers.ts`
- `/Users/brianray/Adam/web/observatory/tests/e2e/observatory.spec.ts`
- `/Users/brianray/Adam/docs/OBSERVATORY_E2E_AUDIT.md`
- `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`
- `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
- `docs/OBSERVATORY_E2E_AUDIT.md`
- `docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `docs/KNOWN_LIMITATIONS.md`
Natural-language contracts added/revised/preserved:
- Preserved the live-first observatory posture and read-only inspect contract.
- Revised browser truth language so backend/server implementation is not flattened into browser exposure truth.
- Added explicit `file://` unsupported-runtime proof to the browser audit rather than treating HTTP-served static parity as exhaustive.
Behavior implemented or modified:
- Surface navigation and inspector tabs now expose `role="tab"` with `aria-selected`.
- Graph-mode, assembly-render, and basin-lift exclusive controls now expose radio-like state through `aria-checked`.
- Assembly, graph-entity, relation, basin-turn, and transcript selection buttons now expose `data-state="active"` for browser-proofable selection state without relying on CSS classes.
- Playwright journeys now assert public state attributes instead of `is-active` CSS classes.
- Journey evidence emission now fails fast if screenshot/DOM/JSON artifacts are missing or empty, and request-failure evidence is recorded.
- J16 is now split into `J16a` HTTP-served static parity and `J16b` unsupported `file://` runtime proof using a real exported `observatory_index.html`.
Evidence produced (tests / traces / commands / exports):
- `npm --prefix web/observatory test` → 3/3 passed.
- `npm --prefix web/observatory run build` → passed, refreshed checked-in observatory bundle/build metadata.
- `npm --prefix web/observatory run test:e2e -- --project=chromium --output=test-results/chromium-final` → 18/18 passed.
- `npm --prefix web/observatory run test:e2e -- --project=firefox --project=webkit --output=test-results/cross-browser-smoke` → 6/6 passed.
- `./.venv/bin/pytest -q tests/test_observatory_server.py tests/test_observatory_measurements.py` → 14/14 passed.
- Fresh browser evidence under `/Users/brianray/Adam/web/observatory/test-results/chromium-final/` and `/Users/brianray/Adam/web/observatory/test-results/cross-browser-smoke/`.
Status register changes:
- Implemented:
  - Public browser state semantics are now directly observable through ARIA/data-state rather than CSS classes.
  - Browser proof now includes explicit unsupported `file://` runtime evidence (`J16b`).
  - J01-J05, J07-J09, J15, J16a, J16b, and J17 are re-proved in this execution.
- Instrumented:
  - Journey evidence bundling is hardened with non-empty artifact verification and request-failure capture.
- Conceptual:
  - None newly introduced.
- Unknown:
  - None remaining for the audited browser journeys; J06 and J10-J14 are now explicit browser contract gaps rather than unknowns.
Truth-table / limitations updates:
- `IMPLEMENTATION_TRUTH_TABLE.md` now distinguishes implemented browser view controls from explicit browser contract gaps for compare/coordinate exposure and mutation/causality flows.
- `KNOWN_LIMITATIONS.md` now states that compare/coordinate exposure plus J10-J14 flows are explicit browser contract gaps and that direct `file://` does not reach a supported-static-ready state.
Remaining uncertainties:
- The current React bundle still does not expose browser paths for compare/coordinate surface semantics, measure preview, attributable edit, memode assertion, revert, or runtime causality; those remain backend/server implemented where noted, but absent in the browser.
- `J16b` proves unsupported `file://` failure in Chromium. Firefox/WebKit smoke intentionally remains limited to read-only honesty journeys.
Next shortest proof path:
- If the React observatory later surfaces compare/coordinate controls or mutation flows, upgrade J06 and J10-J14 from browser gap proofs to positive browser journeys with preview/commit/revert assertions and rerun the same artifact-validated Playwright stack.
## [2026-03-12T17:24:30Z] POST-FLIGHT
Files changed:
- `eden/config.py`
- `eden/runtime.py`
- `eden/app.py`
- `eden/tui/app.py`
- `tests/test_tui_smoke.py`
- `docs/TUI_SPEC.md`
- `docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `docs/KNOWN_LIMITATIONS.md`
- `codex_notes_garden.md`
Specs changed:
- `docs/TUI_SPEC.md`
- `docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `docs/KNOWN_LIMITATIONS.md`
Natural-language contracts added/revised/preserved:
- Preserved the dialogue-first TUI contract and keyboard-first deck/control flow.
- Revised the design contract so amber-dark remains the default look while Deck exposes a persisted `Typewriter Light` operator look.
- Preserved the limitation boundary that terminal rendering remains constrained by Textual/Rich; the light look is appearance-only and not a knowledge/runtime mutation.
Behavior implemented or modified:
- Added a persisted app-level `ui_look` runtime setting backed by `config_store` key `tui_appearance`.
- `build_runtime()` now restores the persisted look on launch.
- `Deck` now exposes a `Look` selector with `Amber Dark` and `Typewriter Light`.
- Switching looks updates both Rich-rendered panel colors and Textual CSS surfaces so the light mode reads as paper/ink/typewriter rather than a generic bright palette.
- Deck status/summary surfaces now report the active look.
Evidence produced (tests / traces / commands / exports):
- `./.venv/bin/pytest -q tests/test_tui_smoke.py` -> `8 passed`
- `./.venv/bin/pytest -q tests/test_runtime_e2e.py tests/test_cli_entry.py` -> `6 passed`
- `./.venv/bin/pytest -q` -> `52 passed`
Status register changes:
- Implemented:
  - Persisted TUI look selection with `Amber Dark` default plus `Typewriter Light` alternative.
  - Deck control-surface exposure for look selection.
  - TUI smoke proof for look switching and persisted appearance state.
- Instrumented:
  - None newly added.
- Conceptual:
  - None for this task.
- Unknown:
  - No remaining code-path unknowns from this turn; visual taste is subjective, but the palette/control behavior is now proved.
Truth-table / limitations updates:
- `IMPLEMENTATION_TRUTH_TABLE.md` now records fixed-pane operator looks instead of an amber-only surface.
- `KNOWN_LIMITATIONS.md` now states explicitly that `Typewriter Light` is appearance-only and non-authoritative.
Remaining uncertainties:
- The exact perceived “typewriter” feel still depends on terminal font choice outside the repo; the palette and panel treatment are implemented, but EDEN does not control the operator’s terminal font renderer.
Next shortest proof path:
- If you want stronger typewriter character, add a tiny screenshot-based manual audit on this Mac for terminal/profile combinations and tune the light palette from that evidence rather than guessing further in code.

## [2026-03-12T17:14:26Z] PRE-FLIGHT
Operator task:
Add a light TUI look to Adam, expose it in the control menu with the other operator controls, and make the light mode feel like a typewriter surface rather than a generic bright palette.
Task checksum:
User request anchored to current TUI behavior and control surfaces in `eden/tui/app.py` plus `docs/TUI_SPEC.md` design contract.
Repo situation:
Worktree already dirty from prior observatory audit turn (`.DS_Store`, observatory audit/docs/test artifacts). Do not revert unrelated changes. Current TUI has no explicit look selector; palette is largely hard-coded across Rich panel rendering and Textual CSS.
Relevant spec surfaces read:
- `docs/TUI_SPEC.md` (secondary surfaces / design contract)
- `docs/IMPLEMENTATION_TRUTH_TABLE.md` (status surface to update if capability changes)
- `docs/KNOWN_LIMITATIONS.md` (rendering limitations surface)
Natural-language contracts in force:
- TUI remains the primary runtime interface.
- Dialogue-first layout and keyboard-first control surfaces stay intact.
- Spec/code drift on design contract must be resolved in the same turn if a new look becomes implemented.
Files/modules likely in scope:
- `eden/tui/app.py`
- `eden/config.py`
- `eden/runtime.py`
- `eden/app.py`
- `tests/test_tui_smoke.py`
- `docs/TUI_SPEC.md`
- `docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `docs/KNOWN_LIMITATIONS.md`
Status register:
- Implemented:
  - Deck modal exposes low-motion/debug controls.
  - TUI palette system is effectively amber-on-dark only.
- Instrumented:
  - TUI smoke tests cover boot, deck-adjacent controls, observatory launch, and compact-layout behavior.
- Conceptual:
  - Alternative looks/themes in the TUI control surface.
- Unknown:
  - Whether current Textual surface can support a coherent light/typewriter look without breaking readability or focus states.
Risks / invariants:
- Do not break keyboard-first flow or session/profile semantics.
- A look change should be an app/runtime appearance setting, not a graph/runtime knowledge mutation.
- Textual CSS and Rich panel rendering must stay visually coherent; partial recolor would look dishonest.
Evidence plan:
- Add deterministic TUI smoke coverage for the new look control and palette switch.
- Run targeted pytest for `tests/test_tui_smoke.py`.
- Update TUI spec and status/limitations docs if the look ships.
Shortest proof path:
- Introduce a narrow persisted UI look setting, add a deck selector, apply a light/typewriter palette through CSS + panel colors, prove selection and persistence in TUI smoke, then update docs and flight log.

## [2026-03-12T16:30:58-04:00] PRE-FLIGHT
Operator task:
Implement the Session Start and Conversation Atlas TUI refactor plan without changing runtime behavior, archive semantics, graph mutation behavior, or schema.
Task checksum:
session-atlas-refactor-v1
Repo situation:
Working tree dirty before edits; preserve unrelated changes. Relevant implementation concentrated in eden/tui/app.py, eden/runtime.py, tests/test_tui_smoke.py, docs/TUI_SPEC.md.
Relevant spec surfaces read:
AGENTS.md; docs/TUI_SPEC.md.
Natural-language contracts in force:
TUI remains the primary runtime surface; session-start modal carries title plus inference controls; Conversation Atlas is a relational transcript library over folder/tag metadata; no schema or graph-semantic drift.
Files/modules likely in scope:
eden/tui/app.py; eden/runtime.py; tests/test_tui_smoke.py; docs/TUI_SPEC.md.
Status register:
- Implemented:
Current SessionConfigModal and ConversationAtlasModal behavior in eden/tui/app.py; archive metadata persistence via eden/runtime.py.
- Instrumented:
Existing TUI smoke coverage for atlas save/resume and live session flows.
- Conceptual:
Labeled session-start stacks, composite title input/history control, two-column atlas work-column flow.
- Unknown:
Whether Textual widget composition needs CSS adjustments beyond the planned modal containers until the refactor is exercised in tests.
Risks / invariants:
Do not change session creation/update semantics, archive metadata shape, transcript path behavior, or graph mutation paths. Keep summary values aligned with clamped request values only; do not invent auto-mode runtime resolution at modal time.
Evidence plan:
Patch runtime helper + modal layout/CSS + tests + TUI spec, then run ./.venv/bin/pytest -q.
Shortest proof path:
Implement the read-only title-history helper, refactor modal widget trees and CSS, extend smoke tests for labels/history/layout, run pytest, then append POST-FLIGHT with exact evidence.

## [2026-03-12T16:44:44-04:00] POST-FLIGHT
Files changed:
eden/runtime.py; eden/tui/app.py; tests/test_tui_smoke.py; docs/TUI_SPEC.md; codex_notes_garden.md.
Specs changed:
docs/TUI_SPEC.md.
Natural-language contracts added/revised/preserved:
Preserved session/graph/archive semantics. Revised TUI contract for labeled session-start controls, persisted-title history selector, clamped Profile Summary, and two-column Conversation Atlas work flow.
Behavior implemented or modified:
Added read-only recent session title helper over persisted session catalog; SessionConfigModal now renders labeled field stacks plus input+history selector and summarizes clamped request values; ConversationAtlasModal now uses filter rail + main work column with preview, taxonomy inputs, taxonomy actions, and session actions in linear operator order.
Evidence produced (tests / traces / commands / exports):
./.venv/bin/python -m py_compile eden/tui/app.py eden/runtime.py tests/test_tui_smoke.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py -> 9 passed; ./.venv/bin/pytest -q -> 53 passed.
Status register changes:
- Implemented:
Session-start labeling/history selector/clamped summary and atlas two-column work flow, backed by code plus passing smoke/full test runs.
- Instrumented:
Extended TUI smoke coverage for modal labels/history/clamp behavior and atlas layout/actions.
- Conceptual:
None added.
- Unknown:
No unresolved runtime-semantic unknowns from this turn.
Truth-table / limitations updates:
No updates required; capability status did not change beyond TUI layout/ergonomics and no new caveat surfaced.
Remaining uncertainties:
Working tree remains dirty with pre-existing unrelated edits outside this refactor scope.
Next shortest proof path:
Manual visual pass in the live TUI to confirm spacing and panel proportions on the target terminal size using the provided screenshot baseline.

## [2026-03-12T17:58:21-04:00] PRE-FLIGHT
Operator task:
Rearrange the Conversation Atlas to match the new two-column mockup: session table on the upper right, folder/tags editor on the lower-left of the right work area, richer session preview on the lower-right, and session-scoped browser observatory access.
Task checksum:
atlas-layout-reflow-v2
Repo situation:
Working tree remains dirty from prior and unrelated edits; preserve existing modifications. Relevant implementation remains centered in eden/tui/app.py with supporting docs/tests in docs/TUI_SPEC.md and tests/test_tui_smoke.py.
Relevant spec surfaces read:
AGENTS.md; docs/TUI_SPEC.md.
Natural-language contracts in force:
Conversation Atlas remains a relational transcript library over persisted session metadata; layout and operator ergonomics may change, but archive semantics, transcript generation, graph mutation behavior, and schema must not.
Files/modules likely in scope:
eden/tui/app.py; docs/TUI_SPEC.md; tests/test_tui_smoke.py; codex_notes_garden.md.
Status register:
- Implemented:
Conversation Atlas search/filter/save/open/resume/refresh flow and session-scoped observatory export/runtime support already exist in code.
- Instrumented:
TUI smoke coverage already proves atlas selection, metadata save, transcript open, refresh, resume, and observatory launch from chat.
- Conceptual:
Nested lower Atlas split with square-ish tags editor and richer session preview/observatory affordances.
- Unknown:
Exact Textual sizing needed for the lower split to visually match the mockup without starving the preview or records table.
Risks / invariants:
Do not change update_conversation_archive semantics, transcript path semantics, or observatory artifact naming. Session preview may expose more factual fields and observatory URLs, but must only surface data grounded in current runtime/export capabilities.
Evidence plan:
Patch Atlas compose/CSS/preview/actions, update the TUI spec and smoke tests for the new structure and observatory controls, then run ./.venv/bin/pytest -q.
Shortest proof path:
Implement the right-column lower split and observatory buttons in eden/tui/app.py, prove the new structure and actions in tests/test_tui_smoke.py, update docs/TUI_SPEC.md, then run the full pytest suite and append POST-FLIGHT with exact evidence.

## [2026-03-12T18:03:40-04:00] POST-FLIGHT
Files changed:
eden/tui/app.py; tests/test_tui_smoke.py; docs/TUI_SPEC.md; codex_notes_garden.md.
Specs changed:
docs/TUI_SPEC.md.
Natural-language contracts added/revised/preserved:
Preserved archive metadata, transcript, observatory artifact, and graph semantics. Revised the Atlas layout contract to a top table plus lower split, with richer session preview and honest session-scoped browser observatory affordances.
Behavior implemented or modified:
Conversation Atlas now renders a two-column shell where the right work column contains the session table above a split detail row; the detail row places Folder + larger Tags editor + taxonomy actions on the left and Session Preview + observatory/session actions on the right. Session preview now exposes session id, experiment id, profile flags, transcript path/state, recent turns, recent feedback, and observatory export/live API references. Added buttons to open the session-scoped observatory GUI export, session turns API, and session active-set API for the selected conversation.
Evidence produced (tests / traces / commands / exports):
./.venv/bin/python -m py_compile eden/tui/app.py tests/test_tui_smoke.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py -> 9 passed in 27.60s; ./.venv/bin/pytest -q -> 53 passed in 33.99s.
Status register changes:
- Implemented:
Atlas nested lower split, square-ish tags editor, richer preview content, and session observatory/open-API buttons, proved by passing smoke and full-suite runs.
- Instrumented:
Smoke coverage now asserts the new Atlas subtree shape and observatory button behavior.
- Conceptual:
None added.
- Unknown:
Visual parity against the operator-provided screenshot is still unproved because this turn did not include a live terminal screenshot comparison.
Truth-table / limitations updates:
No updates required; behavior changed within the existing Atlas capability surface rather than adding a new runtime capability.
Remaining uncertainties:
The worktree still contains pre-existing unrelated edits outside this Atlas task. Exact screenshot-level spacing/proportion match remains visually unverified.
Next shortest proof path:
Launch the TUI, open Conversation Atlas, and compare the lower split proportions plus preview density against the provided mockup at the target terminal size.

## [2026-03-12T18:37:14-04:00] PRE-FLIGHT
Operator task:
Restore visible Atlas action buttons, specifically `Resume Session` and `Refresh`, which are being pushed out of the visible lower-right work area by the current preview sizing.
Task checksum:
atlas-action-visibility-v1
Repo situation:
Working tree remains dirty from prior task work and unrelated edits; preserve those changes. Current Atlas implementation already contains the action widgets in eden/tui/app.py, so the expected fix is layout/CSS plus any minimal structure needed for visibility.
Relevant spec surfaces read:
AGENTS.md; docs/TUI_SPEC.md.
Natural-language contracts in force:
Conversation Atlas stays a two-column relational transcript surface with visible direct actions in the work column. This turn must not change archive/update/resume semantics; it must restore the promised button visibility.
Files/modules likely in scope:
eden/tui/app.py; docs/TUI_SPEC.md; tests/test_tui_smoke.py; codex_notes_garden.md.
Status register:
- Implemented:
Atlas action handlers for `Resume Session`, `Refresh`, and `Close` already exist and are covered by tests.
- Instrumented:
Smoke tests prove the buttons exist in the widget tree and their handlers work when reachable.
- Conceptual:
Scrollable/constrained lower-right preview region that guarantees action rows remain visible.
- Unknown:
Whether a pure CSS height constraint is sufficient, or whether the preview needs its own scroll container to prevent clipping on the target terminal geometry.
Risks / invariants:
Do not move or rename the action semantics. Keep preview richness, but not at the cost of hiding required controls.
Evidence plan:
Patch the Atlas preview region so the lower-right buttons remain visible, update the TUI spec/test expectations if structure changes, then run targeted and full pytest.
Shortest proof path:
Constrain the lower detail row and make the preview independently scrollable if needed, prove the action rows still exist and the suite passes, then append POST-FLIGHT.

## [2026-03-12T18:39:12-04:00] POST-FLIGHT
Files changed:
eden/tui/app.py; tests/test_tui_smoke.py; docs/TUI_SPEC.md; codex_notes_garden.md.
Specs changed:
docs/TUI_SPEC.md.
Natural-language contracts added/revised/preserved:
Preserved Atlas action semantics and two-column workflow. Revised the layout contract so the preview pane can scroll independently and no longer obscures the required action rows.
Behavior implemented or modified:
Wrapped the lower-right preview surface in its own scroll container and constrained the lower detail row height so `Resume Session`, `Refresh`, `Close`, and the observatory buttons remain visible beneath the preview content.
Evidence produced (tests / traces / commands / exports):
./.venv/bin/python -m py_compile eden/tui/app.py tests/test_tui_smoke.py; ./.venv/bin/pytest -q tests/test_tui_smoke.py -> 9 passed in 27.63s; ./.venv/bin/pytest -q -> 53 passed in 33.89s.
Status register changes:
- Implemented:
Atlas preview scrolling/action-row visibility fix, proved by compile plus passing targeted/full test runs.
- Instrumented:
Smoke coverage now asserts the preview column structure with the dedicated preview scroller.
- Conceptual:
None added.
- Unknown:
Exact screenshot-level spacing remains visually unverified in a live terminal pass, though the action-row visibility defect is addressed structurally.
Truth-table / limitations updates:
No updates required; this was a layout correction within an existing capability.
Remaining uncertainties:
Working tree remains dirty from unrelated prior edits; live screenshot comparison still not performed in this turn.
Next shortest proof path:
Open the Atlas in the live TUI and confirm the lower-right buttons are visible at the target window size shown in the screenshot.

## [2026-03-13T00:26:03-0400] PRE-FLIGHT
Operator task:
Create a hum spec under docs, anchor the term in repo truth surfaces, and implement the approved rewrite as repo documentation rather than free-floating chat prose.
Task checksum:
hum-spec-and-blog-rewrite-20260313
Repo situation:
Working tree is already dirty with unrelated `.DS_Store` and deleted `docs.zip`; preserve those changes. No repo-tracked hum spec or blog source currently exists. Historical hum evidence lives outside the repo at `/Users/brianray/Desktop/adam_hum_ALL.md`.
Relevant spec surfaces read:
AGENTS.md; docs/PROJECT_CHARTER.md; docs/TURN_LOOP_AND_MEMBRANE.md; docs/CANONICAL_ONTOLOGY.md; docs/REGARD_MECHANISM.md; docs/INFERENCE_PROFILES.md; docs/TUI_SPEC.md; docs/IMPLEMENTATION_TRUTH_TABLE.md; docs/KNOWN_LIMITATIONS.md; docs/OBSERVATORY_SPEC.md; docs/GRAPH_SCHEMA.md; codex_notes_garden.md; `/Users/brianray/Desktop/adam_hum_ALL.md`.
Natural-language contracts in force:
No governor in v1. TUI remains primary. Memes are first-class, memodes are derived, regard acts over memes and memodes rather than tokens, and active-set assembly is turn-local and bounded. Any hum language must remain subordinate to current repo truth and must not claim a current first-class runtime hum surface without proof.
Files/modules likely in scope:
/Users/brianray/Adam/docs/HUM_SPEC.md; /Users/brianray/Adam/docs/CANONICAL_ONTOLOGY.md; /Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md; /Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md; /Users/brianray/Adam/codex_notes_garden.md.
Status register:
- Implemented:
Current EDEN continuity surfaces: direct v1 loop, persisted memgraph, bounded active set, visible membrane, explicit feedback, TUI-primary runtime, observatory exports.
- Instrumented:
Historical hum artifact with timestamped `hum:` entries and `[HUM_STATS]` / `[HUM_METRICS]` / `[HUM_TABLE]` summaries exists at `/Users/brianray/Desktop/adam_hum_ALL.md`.
- Conceptual:
Hum as low-bandwidth continuity artifact compatible with current graph/regard/feedback architecture.
- Unknown:
Whether the current repo still generates, foregrounds, injects, or membrane-processes a live hum channel.
Risks / invariants:
Do not promote hum to a first-class object or current runtime guarantee. Do not reintroduce governor rhetoric by euphemism. Keep Austin/Foucault references subordinate to mechanism rather than theory-forward. Preserve exact distinctions between hum, active set, history, graph, basin summary, cluster summary, and observatory payloads.
Evidence plan:
Create a dedicated hum spec with status and forbidden-claim boundaries, update ontology/truth/limitations surfaces to reflect that status, and use the approved replacement prose as the implemented documentation artifact.
Shortest proof path:
Patch the new spec plus linked docs, verify the resulting language stays conservative and internally consistent, then append POST-FLIGHT with the exact docs changed and note that no tests were required for docs-only work.

## [2026-03-13T00:28:02-0400] POST-FLIGHT
Files changed:
/Users/brianray/Adam/docs/HUM_SPEC.md; /Users/brianray/Adam/docs/CANONICAL_ONTOLOGY.md; /Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md; /Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md; /Users/brianray/Adam/codex_notes_garden.md.
Specs changed:
/Users/brianray/Adam/docs/HUM_SPEC.md; /Users/brianray/Adam/docs/CANONICAL_ONTOLOGY.md.
Natural-language contracts added/revised/preserved:
Added a dedicated hum spec that treats the hum as a historical/instrumented continuity artifact rather than a proved current-runtime surface. Preserved the direct v1 loop, TUI-primary runtime, meme/memode ontology, and explicit feedback/regard semantics. Revised ontology and status surfaces so hum language cannot silently reintroduce governor rhetoric or collapse hum into active set, history, graph, basin, cluster, or observatory payload.
Behavior implemented or modified:
No runtime behavior changed. Documentation now includes an approved blog-replacement section for the hum, a contract boundary for how the term may be used, and synchronized truth-surface language describing hum as historical artifact evidence plus conceptual fit rather than a repo-proved first-class live channel.
Evidence produced (tests / traces / commands / exports):
Repo/document scan completed before edits; historical artifact `/Users/brianray/Desktop/adam_hum_ALL.md` inspected for timestamped `hum:` entries and `[HUM_STATS]` / `[HUM_METRICS]` / `[HUM_TABLE]`; post-edit readback of the new spec and linked truth surfaces completed. No tests run because this turn was docs-only.
Status register changes:
- Implemented:
Added a repo-tracked hum spec and anchored the term in ontology/truth surfaces.
- Instrumented:
Recorded historical hum artifact evidence explicitly in `docs/HUM_SPEC.md` and `docs/IMPLEMENTATION_TRUTH_TABLE.md`.
- Conceptual:
Hum as low-bandwidth continuity artifact compatible with current graph/regard/feedback architecture is now explicitly specified.
- Unknown:
Current live hum generation/foregrounding/prompt-injection/membrane-processing path remains unproved and is now named as unknown in the spec.
Truth-table / limitations updates:
`docs/IMPLEMENTATION_TRUTH_TABLE.md` now includes a hum row with historical artifact evidence only / current runtime surface unproved status. `docs/KNOWN_LIMITATIONS.md` now forbids claiming live prompt/membrane/persona-reconstruction hum behavior without future proof.
Remaining uncertainties:
There is still no repo-tracked blog source to patch directly; the implemented revision lives as the approved prose block inside `docs/HUM_SPEC.md`. The current repo still does not prove a live first-class hum runtime surface.
Next shortest proof path:
If a repo-tracked external-facing article source is added later, paste the approved replacement block from `docs/HUM_SPEC.md` into that source and keep the same status register language unless new code/runtime evidence upgrades the claim.

## [2026-03-13T05:28:07Z] PRE-FLIGHT
Operator task:
Build a hum user-journey troubleshooting guide plus an automated pre-exploration audit that classifies live, historical-only, docs-only, stale-residue, and unknown hum status without touching the live store by default.
Task checksum:
hum-user-journey-audit-20260313
Repo situation:
Worktree appears clean in this turn. Existing hum truth surfaces already include `docs/HUM_SPEC.md`, the hum row in `docs/IMPLEMENTATION_TRUTH_TABLE.md`, and the hum limitation in `docs/KNOWN_LIMITATIONS.md`; preserve their conservative status unless new code plus current-run proof upgrades it.
Relevant spec surfaces read:
AGENTS.md; docs/HUM_SPEC.md; docs/USER_JOURNEYS.md; docs/HOW_TO_USE_ADAM_TUI.md; docs/FIRST_RUN_QUICKSTART.md; docs/UX_AUDIT_AND_REPAIRS.md; docs/TUI_SPEC.md; docs/TURN_LOOP_AND_MEMBRANE.md; docs/CANONICAL_ONTOLOGY.md; docs/REGARD_MECHANISM.md; docs/IMPLEMENTATION_TRUTH_TABLE.md; docs/KNOWN_LIMITATIONS.md; codex_notes_garden.md.
Natural-language contracts in force:
No governor in v1. TUI remains primary. Memes are first-class, memodes are derived, regard acts over memes and memodes rather than tokens, active-set assembly is turn-local and bounded, and hum must remain distinct from active set, full history, full graph, basin summary, cluster summary, and observatory payloads.
Files/modules likely in scope:
/Users/brianray/Adam/docs/HUM_TROUBLESHOOTING_GUIDE.md; /Users/brianray/Adam/scripts/run_hum_user_journey_audit.py; /Users/brianray/Adam/tests/test_hum_user_journey_audit.py; /Users/brianray/Adam/codex_notes_garden.md.
Status register:
- Implemented:
Current repo proves direct v1 loop surfaces, active-set snapshots, membrane events, explicit feedback persistence, conversation/session traces, and observatory exports/API payloads. No live first-class hum runtime surface is currently proved.
- Instrumented:
Historical hum artifact evidence remains `/Users/brianray/Desktop/adam_hum_ALL.md` with timestamped `hum:` entries and `[HUM_STATS]` / `[HUM_METRICS]` / `[HUM_TABLE]`.
- Conceptual:
Hum as a low-bandwidth continuity artifact compatible with graph state, regard, feedback, and bounded retrieval.
- Unknown:
Whether the current build still emits, foregrounds, injects, or membrane-processes a live hum channel.
Risks / invariants:
Do not let interface drift become fake hum absence. Do not write to repo-global data/log/export paths by default. Do not claim feedback pressure equals hum. Do not treat repeated motif words in unrelated code as hum proof.
Evidence plan:
Create a probe-first audit script that scans claims, builds a scratch mock runtime if safe, runs bounded continuity journeys, scans exported and observatory-adjacent artifacts, optionally compares a historical hum artifact, and emits JSON plus markdown reports with chain-of-custody metadata.
Shortest proof path:
Implement the script and tests, run the script with and without a historical hum artifact, verify the report bundle and statuses, then append POST-FLIGHT with exact evidence and any unchanged truth-table outcome.

## [2026-03-13T05:45:53Z] POST-FLIGHT
Files changed:
/Users/brianray/Adam/docs/HUM_TROUBLESHOOTING_GUIDE.md; /Users/brianray/Adam/scripts/run_hum_user_journey_audit.py; /Users/brianray/Adam/tests/test_hum_user_journey_audit.py; /Users/brianray/Adam/codex_notes_garden.md.
Specs changed:
/Users/brianray/Adam/docs/HUM_TROUBLESHOOTING_GUIDE.md.
Natural-language contracts added/revised/preserved:
Added an operator-facing hum troubleshooting guide and preserved the existing hum contract from `docs/HUM_SPEC.md`: no governor in v1, no live hum overclaim, hum distinct from active set/history/graph/basin/cluster/observatory payloads, regard over memes and memodes rather than tokens, and historical motif strings treated only as compression signatures.
Behavior implemented or modified:
Added a probe-first, scratch-scoped hum audit script that scans hum claims, probes runtime and observatory capabilities, runs bounded scratch journeys, generates JSON and markdown report bundles, optionally parses a historical hum artifact, and exits zero when hum is absent but the audit itself succeeds. Added targeted pytest coverage for claim inventory generation, graceful no-hum classification, optional historical parsing, report emission, and infrastructure-failure exit handling.
Evidence produced (tests / traces / commands / exports):
`./.venv/bin/python scripts/run_hum_user_journey_audit.py --out exports/hum_audit/latest` -> succeeded and emitted the report bundle under `/Users/brianray/Adam/exports/hum_audit/latest`.
`./.venv/bin/python scripts/run_hum_user_journey_audit.py --out exports/hum_audit/latest --historical-hum /Users/brianray/Desktop/adam_hum_ALL.md` -> succeeded; final classification reported `current_live_hum=NOT_PRESENT`, `claim_surface=DOCS_ONLY`, `historical_comparison=HISTORICAL_ONLY`.
`./.venv/bin/pytest -q tests/test_hum_user_journey_audit.py` -> `6 passed`.
Status register changes:
- Implemented:
Added the hum audit stack itself: guide, script, tests, and report bundle generation.
- Instrumented:
The audit now emits machine-readable and human-readable hum audit artifacts under `exports/hum_audit/latest`.
- Conceptual:
Hum remains conceptually compatible with graph/regard/feedback continuity, but the audit did not upgrade it to a current first-class runtime surface.
- Unknown:
Status register language for live hum remains unchanged; the current build still does not prove emission, foregrounding, prompt injection, or membrane handling of a live hum channel.
Truth-table / limitations updates:
No updates made. The audit results matched the existing conservative hum status in `docs/IMPLEMENTATION_TRUTH_TABLE.md` and `docs/KNOWN_LIMITATIONS.md`.
Remaining uncertainties:
The current automated audit does not drive the full live TUI PTY surface. Current exports and runtime artifacts do not prove a live hum surface, but a TUI-only presentation would still need a separate PTY proof path if someone insists on that last inch.
Next shortest proof path:
Use the generated `next_shortest_proof_paths.md` artifact under `/Users/brianray/Adam/exports/hum_audit/latest` and start with the PTY/TUI proof path or a read-only hum status field in runtime metadata if future builds intend hum to be machine-auditable.

## [2026-03-13T07:01:35Z] PRE-FLIGHT
Operator task:
Implement a minimal truthful hum runtime surface that survives the existing audit in scratch scope: bounded artifact generation, persistence, read-only surfacing, audit promotion, tests, and aligned docs.
Task checksum:
minimal-truthful-hum-surface-20260313
Repo situation:
Dirty worktree already present before edits: `.DS_Store` modified, `codex_notes_garden.md` modified, and untracked hum audit files under `docs/`, `scripts/`, and `tests/`. Treat those audit files as baseline and preserve unrelated changes.
Relevant spec surfaces read:
AGENTS.md; docs/HUM_SPEC.md; docs/HUM_TROUBLESHOOTING_GUIDE.md; docs/TURN_LOOP_AND_MEMBRANE.md; docs/CANONICAL_ONTOLOGY.md; docs/REGARD_MECHANISM.md; docs/IMPLEMENTATION_TRUTH_TABLE.md; docs/KNOWN_LIMITATIONS.md; codex_notes_garden.md.
Natural-language contracts in force:
No governor in v1. Hum must remain a low-bandwidth continuity artifact inside the direct retrieve/assemble -> response -> membrane -> feedback -> graph update loop. Hum is not the active set, full turn history, full graph, basin summary, cluster summary, or observatory payload. Regard acts over memes and memodes, not tokens. No prompt injection or membrane-stripping claim unless code plus evidence proves it.
Files/modules likely in scope:
/Users/brianray/Adam/eden/hum.py; /Users/brianray/Adam/eden/runtime.py; /Users/brianray/Adam/eden/observatory/service.py; /Users/brianray/Adam/eden/observatory/exporters.py; /Users/brianray/Adam/scripts/run_hum_user_journey_audit.py; /Users/brianray/Adam/tests/test_hum_runtime.py; /Users/brianray/Adam/tests/test_hum_user_journey_audit.py; /Users/brianray/Adam/docs/HUM_SPEC.md; /Users/brianray/Adam/docs/HUM_TROUBLESHOOTING_GUIDE.md; /Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md; /Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md; /Users/brianray/Adam/codex_notes_garden.md.
Status register:
- Implemented:
Direct v1 runtime persistence surfaces are implemented: turns, active-set snapshots, membrane events, feedback events, trace events, conversation logs, and observatory exports/API payloads. Live hum remains unproved before this turn.
- Instrumented:
Historical hum artifact evidence exists in `/Users/brianray/Desktop/adam_hum_ALL.md` with timestamped `hum:` entries and `[HUM_STATS]` / `[HUM_METRICS]` / `[HUM_TABLE]`.
- Conceptual:
Hum as a bounded low-bandwidth continuity artifact derived from persisted continuity surfaces and surfaced read-only.
- Unknown:
Whether a current scratch/runtime path can emit, persist, and expose a truthful hum artifact without becoming prompt input or collapsing into adjacent continuity surfaces.
Risks / invariants:
Do not add governor-like control logic, prompt injection, or hidden causal influence. Keep hum bounded, deterministic, provenance-rich, scratch-safe, and audit-detectable. Do not confuse export metadata with a new observatory hum payload plane.
Evidence plan:
Add a post-turn/post-feedback hum service, persist markdown + JSON artifacts plus export_artifact rows, expose read-only hum references in session snapshot and observatory overview/transcript/index, update the audit to validate artifacts directly, then prove with targeted hum runtime tests, audit tests, audit command output, and full pytest.
Shortest proof path:
Implement the smallest post-persistence hum artifact in `eden/runtime.py`, validate it in a mock-backed scratch run through the audit, then upgrade docs and truth surfaces only as far as the tests and run artifacts justify.

## [2026-03-13T07:22:40Z] POST-FLIGHT
Files changed:
/Users/brianray/Adam/eden/hum.py; /Users/brianray/Adam/eden/runtime.py; /Users/brianray/Adam/eden/observatory/service.py; /Users/brianray/Adam/eden/observatory/exporters.py; /Users/brianray/Adam/tests/conftest.py; /Users/brianray/Adam/tests/test_hum_runtime.py; /Users/brianray/Adam/tests/test_hum_user_journey_audit.py; /Users/brianray/Adam/scripts/run_hum_user_journey_audit.py; /Users/brianray/Adam/docs/HUM_SPEC.md; /Users/brianray/Adam/docs/HUM_TROUBLESHOOTING_GUIDE.md; /Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md; /Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md; /Users/brianray/Adam/codex_notes_garden.md.
Specs changed:
/Users/brianray/Adam/docs/HUM_SPEC.md; /Users/brianray/Adam/docs/HUM_TROUBLESHOOTING_GUIDE.md; /Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md; /Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md.
Natural-language contracts added/revised/preserved:
Revised the hum contract from historical-only/conceptual to a bounded current-build runtime artifact. Preserved all load-bearing constraints: no governor in v1, no hidden planner, no prompt injection, no membrane consumption claim, no token-level regard, and no collapse of hum into active set, full history, full graph, basin summary, cluster summary, or observatory payloads.
Behavior implemented or modified:
Added `eden/hum.py` with a bounded `HumService` that derives `hum.v1` from persisted `active_set_json`, `feedback_events`, and membrane events; persists `current_hum.md` plus `current_hum.json` per session; records export artifacts; and refreshes after `chat()` and `apply_feedback()`. Added read-only hum references to `session_state_snapshot()`, the conversation-log footer, observatory overview/session-turn payloads, and `observatory_index.json`. Upgraded the hum audit to validate the artifacts and matching reference blocks instead of inferring live hum from generic string hits.
Evidence produced (tests / traces / commands / exports):
`./.venv/bin/pytest -q tests/test_hum_runtime.py tests/test_hum_user_journey_audit.py` -> `12 passed in 5.25s`.
`./.venv/bin/pytest -q` -> `65 passed in 39.36s`.
`./.venv/bin/python scripts/run_hum_user_journey_audit.py --out exports/hum_audit/latest` -> succeeded; final classification `current_live_hum=PASS`, `claim_surface=PASS`, `historical_comparison=MANUAL_REQUIRED`.
`./.venv/bin/python scripts/run_hum_user_journey_audit.py --out exports/hum_audit/latest --historical-hum /Users/brianray/Desktop/adam_hum_ALL.md` -> succeeded; final classification `current_live_hum=PASS`, `claim_surface=PASS`, `historical_comparison=PASS`.
Scratch runtime probe under `/tmp/adam_hum_probe` showed first-turn seed-state hum, second-turn refreshed hum with overlap metrics, and feedback-refreshed hum without prompt injection.
Status register changes:
- Implemented:
Current build now generates a bounded persisted hum artifact (`current_hum.md` plus `current_hum.json`) after turn and feedback persistence, and surfaces it read-only through runtime and observatory reference surfaces.
- Instrumented:
Historical hum artifact evidence remains, and the current runtime now records hum provenance, continuity summaries, and bounded metrics in machine-readable form.
- Conceptual:
Anything richer than the current bounded read-only artifact remains conceptual, including prompt injection, membrane consumption, generation-input reuse, and a more expressive historical-style compressed hum channel.
- Unknown:
Whether the hum should later grow beyond this bounded observability surface, and how much additional higher-order recurrence is justified across broader workloads.
Truth-table / limitations updates:
Updated the hum row in `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md` to implemented minimal runtime artifact, and updated `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md` to state that the current hum remains bounded, read-only, non-causal, and non-equivalent to adjacent continuity surfaces.
Remaining uncertainties:
The current `hum.v1` artifact is intentionally human-readable and minimal rather than a recreation of the older compressed motif channel. Cross-turn recurrence is only reported when the persisted active-set window actually supports it. No dedicated TUI pane or observatory plane exists yet; current surfacing remains compact reference metadata plus artifact files.
Next shortest proof path:
If richer hum behavior is wanted later, add one new proof surface at a time: either a dedicated read-only TUI hum inspector backed by `hum_snapshot()`, or a clearly versioned higher-fidelity derivation contract in `docs/HUM_SPEC.md` with tests and audit updates before any causal generation reuse is considered.
## [2026-03-13  (UTC)] PRE-FLIGHT
Operator task: Add utility script to create a repo-wide Python snapshot document.
Task checksum: create /Users/brianray/Adam/scripts/utility/codebase_snapshot.sh and generate codebase_snapshot.md at repo root.
Repo situation: Working tree is not clean (`.DS_Store` modified, `logs/` untracked).
Relevant spec surfaces read: AGENTS.md instructions supplied in user message; no normative docs in `docs/` were modified for this task.
Natural-language contracts in force: shell utility behavior is anchored to user request and repository boundaries.
Files/modules likely in scope: `/Users/brianray/Adam/scripts/utility/codebase_snapshot.sh` and `/Users/brianray/Adam/codebase_snapshot.md` (generated output).
Status register:
- Implemented:
- Instrumented:
- Conceptual:
- Unknown:
Risks / invariants:
- Must include all `.py` files in repository tree, excluding cache/runtime-only directories.
- Snapshot should include file title, relative tree position, and full file content.
Evidence plan:
- After creation, run the script once and inspect generated document sections.
Shortest proof path:
- Create script and execute it to produce `codebase_snapshot.md`.
## [2026-03-13  (UTC)] POST-FLIGHT
Files changed:
- /Users/brianray/Adam/scripts/utility/codebase_snapshot.sh
Specs changed: None
Natural-language contracts added/revised/preserved:
- No normative spec contracts in `docs/` were modified.
Behavior implemented or modified:
- Added a shell utility that discovers `*.py` files under the repository tree, computes tree position metadata, extracts a title for each file, and writes concatenated markdown sections into `codebase_snapshot.md` at repo root.
Evidence produced (tests / traces / commands / exports):
- None executed for this task; no snapshot generated yet in this turn.
Status register changes:
- Implemented:
- Instrumented:
- Conceptual:
- Unknown: codebase_snapshot utility behavior not yet executed in this turn.
Truth-table / limitations updates: None
Remaining uncertainties:
- `codebase_snapshot.md` format may need adjustment for your preferred structure (e.g., include section names, numbering, or additional metadata).
Next shortest proof path:
- Run `/Users/brianray/Adam/scripts/utility/codebase_snapshot.sh /Users/brianray/Adam`, then review `/Users/brianray/Adam/codebase_snapshot.md` and verify the file set and section ordering.

## [2026-03-13T13:15:13-04:00] PRE-FLIGHT
Operator task:
Refactor the chat TUI to show more dialogue at once, move explicit feedback into a separate terminal popup flow, narrow the aperture drawer, restore a persistent hum box across prime TUI views and the GUI observatory, and add operator-visible reasoning / chain-of-thought-like controls without violating the no-hidden-chain-of-thought contract.
Task checksum:
TUI-layout+feedback-popup+aperture-width+hum-surface+reasoning-controls+observatory-mirror
Repo situation:
Top-level repo guidance and runtime/spec constraints loaded from AGENTS.md. Working tree dirtiness not inspected in this turn to avoid extra churn.
Relevant spec surfaces read:
docs/TUI_SPEC.md; docs/OBSERVATORY_SPEC.md; docs/HUM_SPEC.md; docs/IMPLEMENTATION_TRUTH_TABLE.md; docs/KNOWN_LIMITATIONS.md
Natural-language contracts in force:
TUI remains the primary runtime surface; hum is a bounded read-only continuity artifact; operator-visible reasoning may be surfaced but hidden chain-of-thought may not be claimed or exposed; observatory is a live-first measurement instrument with checked-in frontend bundle.
Files/modules likely in scope:
eden/tui/app.py; web/observatory/src/App.tsx; web/observatory/src/styles.css; docs/TUI_SPEC.md; docs/OBSERVATORY_SPEC.md; docs/HUM_SPEC.md; docs/IMPLEMENTATION_TRUTH_TABLE.md; docs/KNOWN_LIMITATIONS.md; codex_notes_garden.md
Status register:
- Implemented:
Current TUI dialogue-first layout, inline reply review, aperture drawer, dedicated model reasoning panel, bounded hum artifact surfaced through runtime and observatory payloads.
- Instrumented:
Hum provenance/metrics artifacts and observatory build freshness surfaces.
- Conceptual:
A dedicated hum TUI pane, richer historical-style hum channel, browser/TUI reasoning mode controls beyond current single thinking panel.
- Unknown:
Whether the current prime-screen proportions already satisfy the requested terminal geometry; whether the checked-in observatory bundle must be refreshed separately from source edits in this turn.
Risks / invariants:
Do not expose hidden chain-of-thought; preserve hum as derived/read-only; preserve v1 loop vocabulary; keep runtime on MLX; avoid broad refactors outside chat/observatory surfaces.
Evidence plan:
Code diffs plus synchronized spec/truth-table/limitations updates and a post-flight note. No runtime/test proof will be produced unless explicitly requested.
Shortest proof path:
Patch the TUI layout and feedback flow in eden/tui/app.py, mirror hum/reasoning controls in observatory React/CSS, then update the affected docs to truthfully mark implemented vs conceptual surfaces.

## [2026-03-13T13:40:12-04:00] POST-FLIGHT
Files changed:
eden/hum.py; eden/observatory/service.py; eden/app.py; eden/tui/app.py; web/observatory/src/App.tsx; web/observatory/src/styles.css; docs/TUI_SPEC.md; docs/OBSERVATORY_SPEC.md; docs/HUM_SPEC.md; docs/IMPLEMENTATION_TRUTH_TABLE.md; docs/KNOWN_LIMITATIONS.md; eden/observatory/static/observatory_app/index.html; eden/observatory/static/observatory_app/index.js; eden/observatory/static/observatory_app/style.css; eden/observatory/static/observatory_app/build-meta.json
Specs changed:
docs/TUI_SPEC.md; docs/OBSERVATORY_SPEC.md; docs/HUM_SPEC.md; docs/IMPLEMENTATION_TRUTH_TABLE.md; docs/KNOWN_LIMITATIONS.md
Natural-language contracts added/revised/preserved:
Revised TUI contract from inline review to latest-turn popup review; revised TUI/observatory continuity surfaces to include persistent hum fact boxes and operator-visible reasoning lenses; preserved no-hidden-chain-of-thought rule and hum read-only boundary.
Behavior implemented or modified:
Chat prime layout now favors longer transcript visibility; latest-turn feedback launches via `python -m eden feedback` in Terminal.app on macOS; aperture drawer top band reduced; hum snapshot now includes bounded `text_surface`; TUI prime view renders persistent hum plus reasoning/chain-like/hum-live lenses; observatory session transcript payload exposes `reasoning_text`; observatory shell renders continuity strip with hum card and reasoning radio group.
Evidence produced (tests / traces / commands / exports):
`npm --prefix web/observatory run build` succeeded and refreshed `eden/observatory/static/observatory_app/` plus `build-meta.json`.
Status register changes:
- Implemented:
Latest-turn feedback popup command path; persistent TUI hum box; observatory continuity strip; operator-visible reasoning lens switchers; hum snapshot `text_surface`; transcript payload `reasoning_text`.
- Instrumented:
Observatory checked-in bundle refreshed with new build metadata.
- Conceptual:
Anything implying hidden chain-of-thought or hum as generation input remains conceptual and unimplemented.
- Unknown:
Python/TUI runtime behavior was not executed in this turn; popup-launch behavior outside macOS Terminal.app remains unproved; no pytest evidence was produced.
Truth-table / limitations updates:
Updated truth table rows for dialogue layout, latest-turn reply review popup, model reasoning panel, and hum continuity artifact; updated limitations for macOS popup scope and presentation-only hum/reasoning lenses.
Remaining uncertainties:
No Python syntax/runtime check or TUI/manual interaction proof was run; the new popup flow relies on Terminal.app AppleScript on macOS and may need manual confirmation in the live environment.
Next shortest proof path:
Run the TUI once, trigger `F7` after a real Adam reply, and confirm the popup writes feedback plus hum refresh; if needed, follow with targeted pytest or a tiny smoke script for the new `eden feedback` command.

## [2026-03-13T18:16:23Z] PRE-FLIGHT
Operator task:
Implement the EDEN observatory graph workbench roadmap: close browser contract gaps for preview/commit/revert and measurement/edit flows, add browser-local layout workbench controls including ForceAtlas2-class parameters, add Gephi-style filters/appearance/statistics/data-lab/export surfaces, and update specs/evidence honestly.
Task checksum:
observatory-react-workbench+preview-commit-revert+trace-endpoint+layout-runner+filters-appearance-stats+export-interoperability
Repo situation:
Root AGENTS.md constraints already loaded. Working tree is dirty before edits: modified `.DS_Store` plus untracked `logs/hum_state/65c7b12d-2a42-4daa-bf8c-259bd3baeb6e/`. Existing observatory docs and Playwright audit still mark browser contract gaps while legacy exporter HTML already contains an older non-React graph instrument with preview/edit/revert controls.
Relevant spec surfaces read:
docs/OBSERVATORY_SPEC.md; docs/OBSERVATORY_INTERACTION_SPEC.md; docs/MEASUREMENT_EVENT_MODEL.md; docs/OBSERVATORY_E2E_AUDIT.md; docs/KNOWN_LIMITATIONS.md; docs/IMPLEMENTATION_TRUTH_TABLE.md
Natural-language contracts in force:
Observatory remains EDEN-native and live-first; layout/render changes are not evidence claims; browser view state stays local and non-authoritative; preview computes candidate deltas without persistence; commit/revert are the authoritative mutation path; memodes remain derived structures with connected support-floor requirements.
Files/modules likely in scope:
eden/observatory/service.py; eden/observatory/server.py; eden/observatory/exporters.py; eden/observatory/contracts.py; eden/observatory/geometry.py; eden/storage/graph_store.py; web/observatory/src/App.tsx; web/observatory/src/components/GraphPanel.tsx; web/observatory/src/styles.css; web/observatory/src/App.test.tsx; web/observatory/tests/e2e/observatory.spec.ts; tests/test_observatory_measurements.py; tests/test_observatory_server.py; docs/OBSERVATORY_SPEC.md; docs/OBSERVATORY_INTERACTION_SPEC.md; docs/MEASUREMENT_EVENT_MODEL.md; docs/OBSERVATORY_E2E_AUDIT.md; docs/KNOWN_LIMITATIONS.md; docs/IMPLEMENTATION_TRUTH_TABLE.md
Status register:
- Implemented:
Server-side preview/commit/revert, edge mutation, memode assertion/update, measurement ledger persistence, and SSE invalidation; React observatory read surfaces with graph/basin/overview/measurements/tanakh tabs and browser-local view presets.
- Instrumented:
Legacy exporter HTML graph instrument demonstrates preview/edit/revert and filter controls but is not the checked-in React runtime contract; trace events are persisted in storage and surfaced in TUI, not yet in React observatory API/UI.
- Conceptual:
Browser-local layout worker registry, ForceAtlas2-class parameter controls, Gephi-style appearance/ranking/data-lab/export surfaces in the React shell.
- Unknown:
Whether current fixture payloads already contain enough node attributes for the planned appearance/ranking surface without additional exporter changes; whether full Playwright suite runtime is tractable in this turn on this machine.
Risks / invariants:
Do not overclaim Gephi parity; keep browser mutation live-only and explicit in static mode; keep layout/style/filter state out of measurement events; preserve evidence boundary wording; avoid breaking existing static export and SSE behavior; preserve performance on large seeded graphs.
Evidence plan:
Targeted pytest coverage for new preview/trace/export payload behavior, vitest coverage for React controls/state, build of checked-in observatory bundle, and at least targeted Playwright/browser proofs or fixture-based evidence for the closed gap surfaces.
Shortest proof path:
Add missing API/payload fields first (`preview_graph_patch`, trace endpoint, layout/export metadata), port legacy graph instrument behaviors into React with static/live gating, then refresh tests/docs and rebuild the checked-in frontend bundle.

## [2026-03-13T18:20:39Z] PRE-FLIGHT
Operator task:
Fix the chat/observatory continuity lenses so reasoning, chain-like, and hum-live surfaces load session-scoped data during and between turns.
Task checksum:
aa3b671decb650eedd5086f4ea121bbc3d03a39b0d4504989945f0a2b237a2aa
Repo situation:
Root AGENTS.md constraints already loaded. Working tree is dirty before edits: modified `.DS_Store` plus untracked `logs/hum_state/65c7b12d-2a42-4daa-bf8c-259bd3baeb6e/`. Live store inspection shows the latest session already has persisted reasoning (`last_reasoning_len=1965`) and hum (`present=true`, `text_surface` populated), so persistence is not the failing surface.
Relevant spec surfaces read:
docs/TUI_SPEC.md; docs/TURN_LOOP_AND_MEMBRANE.md; docs/HUM_SPEC.md
Natural-language contracts in force:
The chat surface must keep transcript, hum, aperture, and reasoning lenses visible for the active session; the reasoning lens may only render operator-visible reasoning artifacts; hum is a bounded read-only continuity artifact surfaced through session snapshots, observatory payloads, and the prime TUI hum box; hidden chain-of-thought remains out of scope.
Files/modules likely in scope:
web/observatory/src/App.tsx; web/observatory/src/App.test.tsx; eden/observatory/exporters.py; eden/observatory/service.py; tests/test_observatory_server.py
Status register:
- Implemented:
Runtime persistence of `last_reasoning` and bounded hum for the active session; TUI headless render proves the latest session can already display both surfaces from `session_state_snapshot()` and `hum_snapshot()`.
- Instrumented:
Live observatory frontend has payload-status reporting and background transcript loading, but session-scoped continuity behavior is not yet proved in tests.
- Conceptual:
Anything implying hum as generation input or hidden reasoning beyond operator-visible artifacts remains conceptual and out of scope.
- Unknown:
Whether the user report is confined to the browser observatory continuity strip or also includes another chat-adjacent surface outside the reproduced TUI path.
Risks / invariants:
Preserve the existing session-scoped observatory contract; do not overclaim hidden reasoning; do not regress static export mode; keep hum read-only and bounded; avoid changing server API shape unless necessary because the backend already supports `session_id` query parameters.
Evidence plan:
Patch the React frontend to preserve `session_id` on live API requests and prefer a present hum surface, then prove the continuity strip with a focused vitest regression plus targeted backend checks.
Shortest proof path:
Thread `session_id` through live experiment-scoped fetches, stop a sessionless `overview.hum` object from masking transcript hum, add a continuity-strip test, and run the focused frontend/backend evidence path.

## [2026-03-13T18:26:12Z] POST-FLIGHT
Files changed:
web/observatory/src/App.tsx; web/observatory/src/App.test.tsx; eden/observatory/static/observatory_app/index.js; eden/observatory/static/observatory_app/build-meta.json; codex_notes_garden.md
Specs changed:
None. Existing TUI/hum contracts were preserved; this turn restored code to the current contract rather than revising prose.
Natural-language contracts added/revised/preserved:
Preserved the existing contract that live reasoning and hum lenses are session-scoped observability surfaces. No new canonical terms were introduced.
Behavior implemented or modified:
Live observatory experiment-scoped fetches now retain the active `session_id` query parameter for overview/graph/basin/measurements/geometry/tanakh requests. The browser continuity strip now prefers a present transcript hum over a sessionless overview hum placeholder, so `Reasoning`, `Chain-Like`, and `Hum Live` can bind to the active session instead of falling back to blank/sessionless continuity state.
Evidence produced (tests / traces / commands / exports):
`./.venv/bin/python` live-store inspection proved persisted reasoning and hum already existed for session `1042c094-fa43-45d4-8c4e-2d0a7c5707b1`; `cd web/observatory && npm test -- src/App.test.tsx` passed with new continuity-strip regression; `./.venv/bin/pytest tests/test_observatory_server.py -q` passed; `cd web/observatory && npm run build` refreshed the checked-in bundle; `build_status()` now reports `warning=false` with matching source/built hash `da43b2311468a95b`; full `./.venv/bin/pytest -q` exposed one unrelated TUI review-focus failure in `tests/test_tui_smoke.py::test_tui_boots_blank_mode_and_uses_multiline_composer`.
Status register changes:
- Implemented:
Session-scoped browser continuity loading is now proved by source change plus vitest regression and rebuilt static bundle; live observatory no longer drops `session_id` on experiment-scoped continuity fetches.
- Instrumented:
The full repo suite still reports an unrelated TUI review-focus mismatch, outside the observatory continuity path changed in this turn.
- Conceptual:
Hum remains read-only and bounded; no prompt-injection or hidden reasoning behavior was added.
- Unknown:
Whether the operator also observed a separate non-observatory chat surface issue beyond the reproduced browser continuity path remains unproved.
Truth-table / limitations updates:
No docs/status tables changed in this turn because the existing contract already described the intended behavior and the fix restored code to that contract.
Remaining uncertainties:
Full pytest is not green because of the unrelated `action_show_review()` focus expectation in `tests/test_tui_smoke.py`; I did not alter that popup-review path in this turn.
Next shortest proof path:
Manual-check the browser observatory from a live session to confirm the continuity strip updates across a second turn, then address the separate TUI review-focus failure in its own bounded turn if full-suite green is required.

## [2026-03-13T19:17:26Z] POST-FLIGHT
Files changed:
`/Users/brianray/Adam/eden/observatory/service.py`; `/Users/brianray/Adam/eden/observatory/server.py`; `/Users/brianray/Adam/eden/observatory/exporters.py`; `/Users/brianray/Adam/web/observatory/src/App.tsx`; `/Users/brianray/Adam/web/observatory/src/App.test.tsx`; `/Users/brianray/Adam/web/observatory/src/components/GraphPanel.tsx`; `/Users/brianray/Adam/web/observatory/src/workbench/graphUtils.ts`; `/Users/brianray/Adam/web/observatory/src/workers/layoutWorker.ts`; `/Users/brianray/Adam/web/observatory/src/workers/statsWorker.ts`; `/Users/brianray/Adam/web/observatory/tests/e2e/harness/fixtures.mjs`; `/Users/brianray/Adam/web/observatory/tests/e2e/harness/server.mjs`; `/Users/brianray/Adam/web/observatory/tests/e2e/helpers.ts`; `/Users/brianray/Adam/web/observatory/tests/e2e/observatory.spec.ts`; `/Users/brianray/Adam/tests/test_observatory_measurements.py`; `/Users/brianray/Adam/tests/test_observatory_server.py`; `/Users/brianray/Adam/eden/tui/app.py`; `/Users/brianray/Adam/docs/OBSERVATORY_SPEC.md`; `/Users/brianray/Adam/docs/OBSERVATORY_INTERACTION_SPEC.md`; `/Users/brianray/Adam/docs/MEASUREMENT_EVENT_MODEL.md`; `/Users/brianray/Adam/docs/OBSERVATORY_E2E_AUDIT.md`; `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`; `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`; `/Users/brianray/Adam/eden/observatory/static/observatory_app/index.js`; `/Users/brianray/Adam/eden/observatory/static/observatory_app/build-meta.json`; `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
`docs/OBSERVATORY_SPEC.md`; `docs/OBSERVATORY_INTERACTION_SPEC.md`; `docs/MEASUREMENT_EVENT_MODEL.md`; `docs/OBSERVATORY_E2E_AUDIT.md`; `docs/IMPLEMENTATION_TRUTH_TABLE.md`; `docs/KNOWN_LIMITATIONS.md`
Natural-language contracts added/revised/preserved:
Revised the observatory contract from a read-mostly React shell with explicit browser gaps to an EDEN-native graph workbench. Preserved the evidence boundary that preview/commit/revert remain the only authoritative mutation path and that layout/style/filter/table state remains browser-local and non-authoritative.
Behavior implemented or modified:
React observatory now exposes explicit `INSPECT` / `MEASURE` / `EDIT` / `ABLATE` / `COMPARE` controls, coordinate-mode switching, compare rendering from `preview_graph_patch`, attributable preview/commit/revert flows, session-trace visibility, browser-local layout execution (`forceatlas2`, `fruchterman_reingold`, `noverlap`, `radial`), appearance/filter/statistics/Data Lab surfaces, and graph export interoperability. Live API now serves `GET /api/sessions/<session_id>/trace`, preview responses now expose `compare_selection` and `preview_graph_patch`, graph payloads now expose layout/appearance/filter/statistics/export capability metadata, and the prime TUI review surface again mounts/focuses its inline feedback controls.
Evidence produced (tests / traces / commands / exports):
`./.venv/bin/pytest -q tests/test_observatory_measurements.py tests/test_observatory_server.py` -> `16 passed`
`npm --prefix web/observatory run build`
`npm --prefix web/observatory test -- --run src/App.test.tsx` -> `4 passed`
`npm --prefix web/observatory exec playwright test tests/e2e/observatory.spec.ts --project=chromium` -> `18 passed`
`./.venv/bin/python scripts/check_observatory_build_meta.py` -> `ok=true`, matching source/built hash `4492769cf8e966d8`
`./.venv/bin/pytest -q` -> `67 passed`
Status register changes:
- Implemented:
Browser-visible compare/coordinate controls, browser-visible measure/edit/ablate/compare flows, preview patch rendering, runtime trace surface, worker-backed layout/statistics surfaces, Data Lab export surface, and backend proof for preview patch plus trace linkage.
- Instrumented:
Large frontend bundle warning remains visible at build time (`index.js` ~873 kB minified); runtime/build freshness guard proves the bundle is current but not yet split into smaller chunks.
- Conceptual:
Literal Gephi plugin parity, arbitrary external import, and plugin ecosystems remain conceptual/out of scope.
- Unknown:
No additional unknowns were introduced in this turn beyond future performance characteristics on materially larger graphs than the current heavy fixture cap.
Truth-table / limitations updates:
Updated observatory truth/limitations surfaces to remove the stale browser-gap language, add the workbench contract, and restate the non-authoritative layout/style/filter boundary explicitly.
Remaining uncertainties:
The workbench contract is proved for the current fixture families and live API shape, not for arbitrary third-party graph imports or unconstrained Gephi-scale workloads.
Next shortest proof path:
If broader scale proof is required, add a larger seeded fixture and a dedicated performance audit for worker cancelation/repaint cadence before claiming stronger throughput guarantees.

## [2026-03-13T19:42:54Z] PRE-FLIGHT
Operator task:
Add ignore rules for local/generated paths that are bloating commit surfaces, targeting the current 50k+-line churn risk without hiding checked-in runtime contract files.
Task checksum:
gitignore-noise-pruning+node_modules+hum-state+test-results
Repo situation:
Working tree is already dirty from prior observatory/frontend/docs edits. Current status shows local/generated noise mixed with real source edits: root `test-results/`, per-session `logs/hum_state/...`, and large `web/observatory/node_modules/...` churn alongside intentional source changes under `web/observatory/src/...`.
Relevant spec surfaces read:
`AGENTS.md`; `docs/OBSERVATORY_SPEC.md`; `docs/HUM_SPEC.md`
Natural-language contracts in force:
The checked-in observatory bundle under `eden/observatory/static/observatory_app/` remains runtime contract surface and should not be blanket-ignored. Hum artifacts are generated per session under `logs/hum_state/<experiment_id>/<session_id>/...`; ignore hygiene may suppress new local churn but must not overclaim removal of already tracked files.
Files/modules likely in scope:
`/Users/brianray/Adam/.gitignore`; `/Users/brianray/Adam/codex_notes_garden.md`
Status register:
- Implemented:
Current ignore rules already cover `.DS_Store`, `.venv*`, Python cache, tmp, selected logs, databases, exports, and one Vite cache path.
- Instrumented:
`git status --short`, `git diff --numstat`, `du -sh`, and `git ls-files` prove current churn sources and show that `web/observatory/node_modules/` is already heavily indexed.
- Conceptual:
Purging already tracked generated/frontend dependency files from the index.
- Unknown:
Whether the operator wants tracked `web/observatory/node_modules/` removed from the index in this turn or only future-ignore protection.
Risks / invariants:
Do not ignore observatory bundle files that the runtime contract expects to be checked in. `.gitignore` will not stop changes on already tracked files. Keep the change minimal and root-scoped where possible.
Evidence plan:
Patch `.gitignore`, then verify with `git status --short --ignored` and direct path checks that root `test-results/`, new `logs/hum_state/...`, and untracked `web/observatory/node_modules/...` paths are now ignored.
Shortest proof path:
Add three targeted ignore patterns, rerun status with ignored markers, and report the remaining tracked-node_modules caveat explicitly.

## [2026-03-13T19:43:42Z] POST-FLIGHT
Files changed:
`/Users/brianray/Adam/.gitignore`; `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
None.
Natural-language contracts added/revised/preserved:
Preserved the observatory runtime contract that the checked-in bundle under `eden/observatory/static/observatory_app/` should remain version-visible. Preserved the hum contract while adding ignore hygiene for newly generated per-session `logs/hum_state/...` artifacts.
Behavior implemented or modified:
Git now ignores new root `test-results/` artifacts, new per-session `logs/hum_state/` artifacts, and new/untracked `web/observatory/node_modules/` churn.
Evidence produced (tests / traces / commands / exports):
Patched `.gitignore`; verified with `git status --short --ignored`; verified direct matches with `git check-ignore -v test-results logs/hum_state/65c7b12d-2a42-4daa-bf8c-259bd3baeb6e web/observatory/node_modules/@yomguithereal`; measured tracked dependency caveat with `git ls-files web/observatory/node_modules | wc -l` -> `7618`.
Status register changes:
- Implemented:
Targeted ignore rules now cover the main newly generated local churn surfaces seen in this turn.
- Instrumented:
Proof now exists that the new ignore rules match the intended paths and that `web/observatory/node_modules/` remains heavily indexed.
- Conceptual:
Removing already tracked generated/dependency files from the index remains conceptual in this turn.
- Unknown:
Whether Brian the operator wants the indexed `web/observatory/node_modules/` and historical tracked `logs/hum_state/...` artifacts purged from the index now or preserved for repo archaeology.
Truth-table / limitations updates:
None; no runtime feature status changed.
Remaining uncertainties:
`.gitignore` does not affect already tracked files. Current status still shows modified tracked files under `web/observatory/node_modules/` because they are already in the index.
Next shortest proof path:
If commit-surface reduction must include already tracked dependency/runtime artifacts, run a separate index-cleanup turn using `git rm -r --cached web/observatory/node_modules` and any tracked `logs/hum_state/...` files, then verify with `git status --short`.

## [2026-03-13T19:35:39Z] PRE-FLIGHT
Operator task:
Extend the layout workbench beyond ForceAtlas2 by organizing a wider terrain of layout families in the UI, with sub-item algorithms and explicit usage explanations.
Task checksum:
layout-workbench-taxonomy+algorithm-descriptions+family-organized-ui
Repo situation:
Observatory graph workbench turn is already in progress and the tree is dirty from prior observatory/frontend/docs/test edits in this session. Current layout worker only runs a small subset (`forceatlas2`, `fruchterman_reingold`, `noverlap`, `radial`) and the exporter/UI catalog still exposes a flat layout list rather than a family-organized terrain.
Relevant spec surfaces read:
`docs/OBSERVATORY_SPEC.md`
Natural-language contracts in force:
Layout execution remains browser-local and non-authoritative; coordinate/layout choices are view state, not graph evidence; do not overclaim literal Gephi/plugin parity; add explanations that clarify when each algorithm family is useful.
Files/modules likely in scope:
`/Users/brianray/Adam/eden/observatory/exporters.py`; `/Users/brianray/Adam/web/observatory/src/App.tsx`; `/Users/brianray/Adam/web/observatory/src/workbench/graphUtils.ts`; `/Users/brianray/Adam/web/observatory/src/workers/layoutWorker.ts`; `/Users/brianray/Adam/web/observatory/src/App.test.tsx`; `/Users/brianray/Adam/docs/OBSERVATORY_SPEC.md`; `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`; `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`
Status register:
- Implemented:
Browser-local layout workbench with worker-backed `forceatlas2`, `fruchterman_reingold`, `noverlap`, and `radial`; compare/render/state boundary already proved.
- Instrumented:
Layout metadata is already exported to the frontend, but it is flat and sparse on explanations.
- Conceptual:
Broader layout family taxonomy and UI explanation surface for force-directed, hierarchical, tree, circular, spectral, multilevel, constraint-based, orthogonal, planar, geographic, community, and edge-bundling families.
- Unknown:
How many of the requested algorithms can be made runnable in this turn without destabilizing the workbench or overclaiming unsupported implementations.
Risks / invariants:
Do not silently label reference-only algorithms as runnable; keep heavy-graph honesty; preserve current layout snapshot keys; avoid inflating the bundle with unnecessary dependencies.
Evidence plan:
Extend exported layout catalog metadata with family/group/explanation fields, add more runnable browser-local layouts where feasible, render an organized family browser in the React UI, add focused frontend tests, rebuild the bundle, and rerun the focused frontend/backend proof path.
Shortest proof path:
First make the layout catalog hierarchical and descriptive, then add runnable algorithms that fit the existing worker model, then wire grouped UI rendering and prove the new layout/explanation surface in Vitest plus build.

## [2026-03-13T20:05:18Z] POST-FLIGHT
Files changed:
`/Users/brianray/Adam/web/observatory/src/workbench/layoutTerrain.ts`; `/Users/brianray/Adam/web/observatory/src/App.tsx`; `/Users/brianray/Adam/web/observatory/src/workers/layoutWorker.ts`; `/Users/brianray/Adam/web/observatory/src/styles.css`; `/Users/brianray/Adam/web/observatory/src/App.test.tsx`; `/Users/brianray/Adam/web/observatory/tests/e2e/observatory.spec.ts`; `/Users/brianray/Adam/eden/observatory/exporters.py`; `/Users/brianray/Adam/tests/test_observatory_server.py`; `/Users/brianray/Adam/docs/OBSERVATORY_SPEC.md`; `/Users/brianray/Adam/docs/IMPLEMENTATION_TRUTH_TABLE.md`; `/Users/brianray/Adam/docs/KNOWN_LIMITATIONS.md`; `/Users/brianray/Adam/docs/OBSERVATORY_E2E_AUDIT.md`; `/Users/brianray/Adam/codex_notes_garden.md`
Specs changed:
`docs/OBSERVATORY_SPEC.md`; `docs/IMPLEMENTATION_TRUTH_TABLE.md`; `docs/KNOWN_LIMITATIONS.md`; `docs/OBSERVATORY_E2E_AUDIT.md`
Natural-language contracts added/revised/preserved:
Revised the observatory spec so the graph workbench now names a 12-family layout terrain, distinguishes runnable browser-worker layouts from reference/explanation-only algorithms, and makes the payload/bundled-terrain merge explicit. Preserved the evidence boundary: layouts, layout explanations, snapshots, appearance, filters, and Data Lab state remain browser-local and non-authoritative.
Behavior implemented or modified:
React graph workbench now renders a family-organized layout browser with subgroup headings, usage explanations, runnable/reference badges, generic parameter controls, and a broader runnable subset (`forceatlas2`, `fruchterman_reingold`, `kamada_kawai`, `linlog`, `sugiyama_layered`, `radial_tree`, `simple_circular`, `circular_degree`, `circular_community`, `radial`, `noverlap`, `fixed_coordinate`, `community_clusters`). Layout worker now executes the added runnable subset and carries cluster/geo metadata needed for community and anchored layouts. Python graph payload now exports `layout_families` plus expanded runnable-layout metadata/defaults so live/static API surfaces advertise the same workbench terrain.
Evidence produced (tests / traces / commands / exports):
`npm --prefix web/observatory test -- --run src/App.test.tsx` -> `4 passed`; `npm --prefix web/observatory run build` -> success; `npm --prefix web/observatory exec playwright test tests/e2e/observatory.spec.ts --project=chromium` -> `18 passed`; `./.venv/bin/pytest -q tests/test_observatory_server.py tests/test_observatory_measurements.py` -> `16 passed`; `./.venv/bin/pytest -q` -> `67 passed`; `./.venv/bin/python scripts/check_observatory_build_meta.py` -> `ok: true`, matching source/built hash `3a1f0dfdd8e7a2e2`.
Status register changes:
- Implemented:
Family-organized layout terrain UI, expanded runnable browser-worker layouts, and exported payload family metadata are now proved by build/tests in this turn.
- Instrumented:
Payload metadata covers family ordering and runnable-layout overrides/defaults; the checked-in frontend terrain catalog still supplies many reference-only algorithm descriptions for breadth.
- Conceptual:
Literal execution of every listed reference algorithm, true Gephi plugin parity, and post-layout edge bundling execution remain conceptual.
- Unknown:
Performance/readability quality of the newly added runnable layouts on very large real seeded graphs beyond the existing heavy-cap and Playwright fixture proofs.
Truth-table / limitations updates:
Updated truth-table row for the browser-local layout workbench and added limitations covering the broader terrain vs executable subset plus payload/bundled-terrain merge behavior.
Remaining uncertainties:
The layout terrain shown in the UI is intentionally broader than the executable worker subset. Many reference-only algorithms are explanatory browse targets, not active implementations.
Next shortest proof path:
If Brian the operator wants more of the reference terrain to become executable, pick the next bounded family (`stress-majorization`, `Yifan Hu`, or an orthogonal/grid pass), add one worker-backed implementation at a time, and prove each with targeted UI + performance tests rather than bulk-promoting the whole catalog.
