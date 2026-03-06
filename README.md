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

```bash
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip setuptools wheel
.venv/bin/pip install -e '.[dev]'
```

Install MLX support for the real backend:

```bash
.venv/bin/pip install -e '.[mlx]'
```

`mlx-lm` is installed and import-validated in the repo venv. A full run with the selected local Qwen/Qwen3.5-35B-A3B 4-bit MLX model still requires you to provide the actual model path on disk.

## Run

Launch the TUI with the fast mock path:

```bash
.venv/bin/python -m eden app --backend mock
```

Launch the TUI with MLX:

```bash
.venv/bin/python -m eden app --backend mlx --model-path /absolute/path/to/Qwen3.5-35B-A3B-4bit-MLX
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

1. Start the TUI with `.venv/bin/python -m eden app --backend mock`.
2. Choose `Blank Eden`, `Seeded Eden`, or `Resume Latest`.
3. In the session-start modal choose the inference profile mode and bounded parameters for that session.
4. Use the multiline composer to write a turn and send it with `Ctrl+S`.
5. Watch the `Inference Circumstances / Budget` panel update as you type and after retrieval preview refreshes.
6. Inspect the `Aperture / Active Set` and `Cogitation / Decision Trace` panes.
7. Apply `Accept`, `Edit`, `Reject`, or `Skip` feedback.
8. Use `Export` to write graph, basin, geometry, measurement, and index artifacts.
9. Use `Observatory` to ensure the local server is running and open the current experiment's index page.
10. In the browser observatory use `INSPECT`, `MEASURE`, `EDIT`, `ABLATE`, or `COMPARE`.
11. Preview a change first, then commit it if the before/after metrics support the edit.
12. Revert recent observatory-originated mutations from the measurement ledger when needed.

## Inference notes

- `manual`: uses the operator-supplied bounded values after clamping.
- `runtime_auto`: chooses a bounded preset per turn from transparent heuristics.
- `adam_auto`: mock mode uses a bounded preset picker; MLX currently falls back to `runtime_auto` and logs that fact.
- `temperature`, `top_p`, and `repetition_penalty` are passed through on the MLX path using local `mlx-lm` sampler/logits controls.
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

- `24 passed`
- observatory CLI fallback from an occupied requested port to the next free port with actual URL reporting
- live API preview / commit / revert cycle executed against a real experiment
- mock demo export generated graph, basin, geometry, measurement, and index artifacts
- observatory graph instrument and geometry lab opened in a real browser session via Playwright
- TUI smoke path from v1.1 remained green

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
