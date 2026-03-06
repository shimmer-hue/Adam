# EDEN v1.2 Patch Manifest

Generated during the March 6, 2026 in-place patch cycle for `/Users/brianray/Adam`.

## Scope

- Patch target: existing EDEN repository in place
- Intent: turn the observatory from a read-mostly export surface into a locally editable measurement instrument
- Priority order:
  1. additive measurement / graph-edit persistence
  2. live observatory API and reversible edit flow
  3. local geometry-aware preview / commit / revert workflows
  4. luminous neo-cyber observatory refactor
  5. tests, docs, and truthful handoff

## Files inspected

External context:

- `/Users/brianray/Adam/exports/context/adam_codebase_context_20260306_153705.md`
- `/Users/brianray/Desktop/cannonical_secondary_sources.zip`
- `/Users/brianray/Desktop/cannonical_secondary_sources/2602.15029v2.pdf`
- `/Users/brianray/Desktop/cannonical_secondary_sources/2017-Imari Walker-Origins of Life - A Problem for Physics.pdf`
- `/Users/brianray/Desktop/cannonical_secondary_sources/2026.01.28-Zhang-Recursive_Langauge_Models.pdf`
- `/Users/brianray/Desktop/cannonical_secondary_sources/1962-Austin-How_to_Do_Things_with_Words.pdf`
- `/Users/brianray/Desktop/cannonical_secondary_sources/2019-Dennett-From_Bacteria_to_Bach_and_Back.pdf`
- `docs.zip`
  - Referenced by the operator, but not present at `/Users/brianray/Adam/docs.zip` during this patch cycle.
- Included observatory / UI screenshots
  - No standalone screenshot files were present in the repo root during initial inspection.
- `Considerations from ChatGPT Pro 4`
  - Read from the pasted block in the operator prompt and treated as a secondary conceptual design brief.

Repo files:

- `README.md`
- `docs/OBSERVATORY_SPEC.md`
- `docs/OBSERVATORY_GEOMETRY_SPEC.md`
- `docs/GEOMETRY_EVIDENCE_POLICY.md`
- `docs/CANONICAL_ONTOLOGY.md`
- `docs/TURN_LOOP_AND_MEMBRANE.md`
- `docs/PATCH_MANIFEST_V1_1.md`
- `docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `docs/KNOWN_LIMITATIONS.md`
- `eden/app.py`
- `eden/runtime.py`
- `eden/tui/app.py`
- `eden/observatory/exporters.py`
- `eden/observatory/geometry.py`
- `eden/observatory/server.py`
- `eden/storage/graph_store.py`
- `eden/storage/schema.py`

## v1.1 wins preserved

- Amber-on-dark observatory foundation
- Existing graph / basin / geometry artifact families
- Geometry evidence policy and render-vs-evidence boundary
- Robust observatory host / port reuse behavior
- TUI fixed-pane grammar and session-start inference profile flow
- Additive migration discipline
- Local-first SQLite-backed memgraph and export pipeline

## New capabilities added in v1.2

- Live observatory JSON API layered onto the v1.1 server
- Persistent `measurement_events` table and store helpers
- Preview / commit / revert flow for observatory-originated mutations
- Edge add / update / remove with provenance
- Known memode assertion and membership-refinement workflows
- Local selection geometry diagnostics and before/after metric deltas
- Measurement ledger export family
- Observatory index upgrade for editability metadata
- Luminous neo-cyber graph instrument refactor with explicit mode bar and precision drawer
- Runtime trace/log emission for observatory-originated edits and reverts

## Conceptual block influence

- The pasted `Considerations from ChatGPT Pro 4` block directly shaped the practical memode ladder in the docs and implementation language:
  - `meme = local part`
  - `memode = reusable selected subassembly / historically stabilized motif`
  - `persona = persistent assembly ecology of memodes`
- That framing pushed the observatory away from a read-only graph browser and toward a constructive measurement instrument where operator interventions can create provenance-bearing graph facts.
- The Karkada symmetry paper influenced the geometry upgrade as a theory-of-geometry / latent-variable / ablation source:
  - local selection geometry
  - robustness-under-ablation framing
  - care around clustered motif recovery rather than isolated dyads
- Walker / Cronin / Gisin-adjacent language from the pasted block informed the documentation framing of a memode as an assembly-stabilized, temporally thick causal motif rather than a mere pairwise link.

## Files changed

- `.gitignore`
- `README.md`
- `docs/OBSERVATORY_SPEC.md`
- `docs/OBSERVATORY_GEOMETRY_SPEC.md`
- `docs/GEOMETRY_EVIDENCE_POLICY.md`
- `docs/CANONICAL_ONTOLOGY.md`
- `docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/PATCH_MANIFEST_V1_2.md`
- `docs/OBSERVATORY_INTERACTION_SPEC.md`
- `docs/MEASUREMENT_EVENT_MODEL.md`
- `eden/observatory/exporters.py`
- `eden/observatory/geometry.py`
- `eden/observatory/server.py`
- `eden/observatory/service.py`
- `eden/runtime.py`
- `eden/storage/graph_store.py`
- `eden/storage/schema.py`
- `tests/test_geometry.py`
- `tests/test_observatory_server.py`
- `tests/test_observatory_measurements.py`
- `tests/test_runtime_e2e.py`

## Deferred

- No destructive ontology rewrite. Memodes remain materialized second-order artifacts in the existing store shape.
- No full drag-and-drop graph editor. Editing remains precision-drawer and selection driven.
- Geometry remains graph/topology and trace based. It does not inspect model-internal latent activations.
- The real MLX backend still awaits a local Qwen/Qwen3.5-35B-A3B 4-bit model path for full on-machine validation.
- `adam_auto` on the MLX path still falls back to `runtime_auto`.
