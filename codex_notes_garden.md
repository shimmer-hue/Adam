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
