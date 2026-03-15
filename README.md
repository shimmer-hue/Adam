# EDEN / ADAM v1.2

EDEN is a local-first experimental memetic persona runtime. ADAM is the first agent/persona instance inside it. v1.2 preserves the working amber fixed-pane TUI and the v1.1 observatory server/budget/profile upgrades, then turns the observatory into a bidirectional measurement instrument: observation can preview a topology change, commit it with provenance, revert it, and immediately refresh graph and geometry artifacts.

## v1.2 additions

- Live local observatory API layered onto the existing export server
- Measurement-first graph editing with preview, commit, and revert semantics
- Persistent `measurement_events` ledger for edits, measurements, annotations, ablations, and reverts
- Known memode assertion and membership-refinement workflows
- Local selection geometry diagnostics and before/after metric deltas
- Stronger neo-cyber illumination grammar for the browser observatory
- Measurement ledger export family and observatory index upgrade
- Synthetic persistence + local geometry + API tests

## Environment

Validated with repo-local Python 3.12 in `/Users/brianray/Adam/.venv`.
If you rebuild `.venv`, use one interpreter family consistently; do not layer a Homebrew Python onto a `pyenv`-created venv or vice versa.
All commands below assume your shell is already at the repo root. If you run them from `~`, pip will try to install `/Users/brianray` instead of this project.

```bash
cd /Users/brianray/Adam
```

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -e '.[dev,mlx]'
```

If you already created `.venv` and only need the MLX extras:

```bash
.venv/bin/python -m pip install -e '.[mlx]'
```

`mlx-lm` is installed in the repo venv. The default runtime now targets a repo-managed local MLX build of the official `Qwen/Qwen3.5-35B-A3B` line at `models/qwen3.5-35b-a3b-mlx-mxfp4`. This repo-local model has been downloaded and validated on this machine.

## Run

From a fresh shell, the safest normal path is:

```bash
cd /Users/brianray/Adam
.venv/bin/python app.py
```

Equivalent explicit TUI command from the repo root:

```bash
.venv/bin/eden
```

Original module path from the repo root:

```bash
.venv/bin/python -m eden app
```

`python3 app.py` is also valid, but only after you have already changed into `/Users/brianray/Adam`.

The live dialogue surface boots directly into a real chat session on the repo-local runtime. The top action shelf exposes review, conversation-log, profile, session, export, observatory, model-prepare, ingest, aperture, and chyron actions as a multi-row button grid with integrated runtime/progress lines, without dropping you onto a separate launcher. The default MLX model is stored under `models/` inside the repo root rather than an external cache path.

Use flags only when you want an explicit shell override. The normal path is the repo-local MLX default. The action strip can prepare the local Qwen model directly if it is not cached yet.

Advanced shell override example:

```bash
.venv/bin/python -m eden app --backend mock
```

Run a one-turn demo and emit graph, basin, geometry, measurement, and index exports:

```bash
.venv/bin/python -m eden demo --backend mock --mode blank --prompt 'Map the graph-conditioned persistence surfaces and geometry evidence.' --feedback accept --feedback-explanation 'Useful for observatory validation.'
```

Ingest a document into an existing experiment:

```bash
.venv/bin/python -m eden ingest <experiment_id> /absolute/path/to/file.pdf
```

Export observability artifacts for an experiment:

```bash
.venv/bin/python -m eden export <experiment_id> --session-id <session_id>
```

Serve the exports directory with robust port handling:

```bash
.venv/bin/python -m eden observatory --host 127.0.0.1 --port 8741 --open
```

Useful flags:

```bash
.venv/bin/python -m eden observatory --no-open
.venv/bin/python -m eden observatory --reuse-existing
.venv/bin/python -m eden observatory --no-reuse-existing
```

## First Run

1. Change into the repo root with `cd /Users/brianray/Adam`.
2. Start EDEN with `.venv/bin/python app.py`.
3. EDEN resumes the latest persisted session automatically. If none exists yet, it creates a blank live session automatically.
4. If the local model is not cached yet, use the top action strip and run `Prepare Local Model`. EDEN stores it under `models/` in this repo.
5. The top action strip is keyboard-first: `Tab` / `Shift+Tab` moves focus, `Left` / `Right` changes the selected action, typing digits jumps to an action number, and `Enter` executes it.
6. If focus drifts away from the composer, press `Esc` to return to it. Printable keys typed outside editable widgets are routed back into the composer automatically.
7. Press `F8` to pull down the full-width aperture drawer. It occupies the top band of the screen and renders a wider natural-language scan of the active set.
8. The large left column is the Adam dialogue surface: scrolling Brian/Adam tape, inline reply-review strip, and always-visible composer.
9. Transcript cards now use static chiaroscuro shading instead of animated decorative glyph bands inside the chat surface.
10. On wide terminals the top row now pairs the action shelf with a live turn-status strip and `Aperture / Active Set`, while the right column keeps only the memgraph bus and the lower reasoning/feed surface.
11. The memgraph bus includes a visible glyph legend so `D`, `o`, `^`, `M`, `@`, `R`, `*`, `!`, and `?` can be read directly on-screen.
12. The runtime loop and session/event summary now ride in a merged bottom chyron instead of taking a full telemetry square.
13. Type into the visible composer at the bottom of the left dialogue column and send with `Ctrl+S`.
14. The prime screen now refreshes on state changes instead of a constant whole-screen repaint loop, which materially improves typing responsiveness.
15. Start a conversation by asking Adam a question or pressing `F9` to ingest a document with a framing prompt. End a conversation by opening a new session with `F5`.
16. The signal field is an orthographic operator slice of the live memgraph: `D` marks the latest ingested document root, `o` knowledge memes, `^` behavior memes, `M` memodes, `@` the session anchor, and `R` the high-regard recall bank. `*` marks turn pulses, `!` feedback sparks, and `?` a framing-brief lens. It is still not a hidden-activation visualizer.
17. `F9` opens the ingest bay, where you provide a PDF/document path plus a short framing prompt. The document content and framing prompt are both indexed into the memgraph for later retrieval.
18. Open `Utilities Deck` when you want detailed budget, thinking, history, ingest, and launch utilities.
19. Review Adam inline: after each Adam reply, the reply-review strip appears directly under the transcript. Type `A`, `E`, `R`, or `S`, press `Enter` to move into the required field, then press `Enter` again in the last required field to commit. `A` / `R` require explanation; `E` requires explanation plus corrected text. Use `Shift+Enter` for a newline inside explanation or corrected text. Submitting there writes a feedback event and updates graph channels.
20. Conversation logs are also written to `exports/conversations/<experiment-slug>/...md`. The merged bottom chyron shows the active transcript file, and `Open Conversation Log` in the action strip opens it directly.
21. Adam's visible reply is now a clean operator-facing answer. Model thinking stays in the separate thinking surface instead of appearing as `Answer`, `Basis`, or `Next Step` scaffolding inside the dialogue.
22. Use `Tune Session` or `Start New Session` from the action strip when you want a bounded inference-profile change.
23. Use `Export Artifacts` to write graph, basin, geometry, measurement, and index artifacts.
24. Use `Open Browser Observatory` to ensure the local server is running and open the current experiment's latest existing artifact without forcing a fresh export first.
23. In the browser observatory use `INSPECT`, `MEASURE`, `EDIT`, `ABLATE`, or `COMPARE`.
24. Preview a change first, then commit it if the before/after metrics support the edit.
25. Revert recent observatory-originated mutations from the measurement ledger when needed.

## Inference notes

- `manual`: uses the operator-supplied bounded values after clamping.
- `runtime_auto`: chooses a bounded preset per turn from transparent heuristics.
- `adam_auto`: mock mode uses a bounded preset picker; MLX currently falls back to `runtime_auto` and logs that fact.
- `temperature`, `top_p`, and `repetition_penalty` are passed through on the MLX path using local `mlx-lm` sampler/logits controls.
- Qwen thinking is left enabled on the MLX path. EDEN keeps the final answer in the main response panel while the prime feed now suppresses prompt-mirror scaffolding and mixes response-first material, bounded visible reasoning/hum artifacts, runtime constraints, membrane behavior, continuity, and consideration telemetry; it still does not claim hidden reasoning access.
- Prompt budget is an EDEN-side working budget estimate, not a claim about the model’s absolute maximum context window.
- Token counts are exact when a tokenizer-backed counter is available; otherwise EDEN uses an explicit heuristic and labels it that way.

## Observatory artifacts

Per experiment under `exports/<experiment_id>/`:

- `graph_knowledge_base.html`
- `behavioral_attractor_basin.html`
- `geometry_lab.html`
- `measurement_ledger.html`
- `observatory_index.html`
- matching `.json` and manifest files

The graph surface separates `render_coords` from `derived_coords`. The geometry lab reports topology, symmetry proxies, projection diagnostics, local selection metrics, and ablation persistence without claiming that layout aesthetics are evidence. The live observatory layer adds JSON endpoints for preview, commit, revert, and measurement-event inspection while preserving static export compatibility.

## Live observatory editing

- `INSPECT`: hover, pin, inspect provenance, regard, neighborhood, and measurement history
- `MEASURE`: select nodes and compute local geometry without mutating topology
- `EDIT`: add or update edges, assert known memodes, and refine memode membership with provenance
- `ABLATE`: mask a relation class for comparison without silently rewriting the graph
- `COMPARE`: inspect baseline vs modified slices and coordinate-method differences

Every observatory-originated mutation is stored as a measurement-bearing event with:

- action type
- target ids
- before / proposed / committed state
- operator label
- evidence label
- rationale
- measurement method
- confidence
- revert linkage when applicable

## Tests

```bash
.venv/bin/pytest -q
```

Validated in this patch:

- observatory CLI fallback from an occupied requested port to the next free port with actual URL reporting
- live API preview / commit / revert cycle executed against a real experiment
- mock demo export generated graph, basin, geometry, measurement, and index artifacts
- observatory graph instrument and geometry lab opened in a real browser session via Playwright
- repo-local Qwen MLX model download completed at `models/qwen3.5-35b-a3b-mlx-mxfp4`
- direct MLX generation returned a clean answer from the repo-local Qwen model
- EDEN runtime chat completed against the repo-local MLX backend with separate reasoning and answer surfaces
- `31 passed`

## Evidence

Fresh v1.2 demo artifacts from this patch cycle:

- `exports/b178bed2-731e-4f8b-b5f8-a93d1300b2f7/observatory_index.html`
- `exports/b178bed2-731e-4f8b-b5f8-a93d1300b2f7/graph_knowledge_base.html`
- `exports/b178bed2-731e-4f8b-b5f8-a93d1300b2f7/behavioral_attractor_basin.html`
- `exports/b178bed2-731e-4f8b-b5f8-a93d1300b2f7/geometry_lab.html`
- `exports/b178bed2-731e-4f8b-b5f8-a93d1300b2f7/measurement_ledger.html`

Runtime artifacts:

- `logs/runtime.jsonl`
- `data/eden.db`

## Docs

- `docs/INFERENCE_PROFILES.md`
- `docs/TUI_SPEC.md`
- `docs/OBSERVATORY_SPEC.md`
- `docs/OBSERVATORY_GEOMETRY_SPEC.md`
- `docs/GEOMETRY_EVIDENCE_POLICY.md`
- `docs/OBSERVATORY_INTERACTION_SPEC.md`
- `docs/MEASUREMENT_EVENT_MODEL.md`
- `docs/PATCH_MANIFEST_V1_2.md`
- `docs/PATCH_MANIFEST_V1_1.md`
- `docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `docs/KNOWN_LIMITATIONS.md`
