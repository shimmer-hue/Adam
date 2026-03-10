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
