# Adam Intelligence Brief

Generated: 2026-03-23 13:07:47 EDT  
Run slug: `core_audit`  
Repo root: `.`  
Runtime patch level: `v1.2`  
Verbosity profile: `THICK`  
Require write proof: `true`

This brief centers Adam v1. The repository still contains historical `EDEN` labels in package paths, docs titles, and some UI copy; those are treated here as implementation-history anchors, not as permission to frame the current project as Eden.

## Run Classification

- Governance status: `RESOLVED`
- Notes surface: `./codex_notes_garden.md`
- Output status: `EXECUTED`
- Overall audit stance: Adam currently implements a local-first MLX-backed, TUI-first direct turn loop with explicit feedback, durable regard, derived memodes, a live observatory mutation surface, and an additive Tanakh sidecar. It still defers embeddings, training, and governor/planner layers. Browser mutation exists, but browser causality remains read-only and some export surfaces remain scope-sensitive enough to require careful interpretation.
- Current hard defect boundary from this run: repo-wide Python proof is not fully green because `tests/test_ingest.py::test_pages_pdf_fixture_extracts_readable_text` depends on a missing PDF fixture under `assets/cannonical_secondary_sources/`.

## Governance Resolution Log

| Attempt | Absolute path | Exists | Opened | Accepted | Reason |
| --- | --- | --- | --- | --- | --- |
| 1 | `/Users/brianray/Adam/AGENTS.md` | yes | yes | yes | `./AGENTS.md` exists at repo root, so it governs. |
| 2 | `/Users/brianray/Adam/AGENTS.md` | yes | no | no | Same absolute path as attempt 1; not reopened because attempt 1 already governed. |
| 3 | repo-root `AGENTS*.md` matches | yes | no | no | `ls AGENTS*.md` returned only `AGENTS.md`; no alternate governing file was admissible. |

Governance did not fail closed. Intelligence-brief generation was allowed.

## Run Config Audit

| Field | Status | Value used |
| --- | --- | --- |
| `BASELINE_DRAFT_PATH` | `UNSET` | resolved by numbered lineage scan |
| `SUPPORT_MANUSCRIPT_PATH` | `UNSET` | resolved by support-manuscript scan |
| `WHY_NOW` | `UNSET` | current-repo drift control and capability/evidence refresh |
| `AUDIENCE` | `UNSET` | technically literate internal-audit readers and downstream whitepaper-support readers |
| `RED_LINES` | `UNSET` | no fabricated implementation claims; no browser overclaim; no Eden-only path regression; no silent omission |
| `COMPARATORS_ENABLED` | `UNSET` | treated as disabled |
| `PDF_BUILD_REQUIRED` | `UNSET` | no PDF build attempted |
| operator attachments | `UNSET` | none provided in-thread |
| `run_slug` | defaulted | `core_audit` |
| `runtime_patch_level` | inferred | `v1.2` from `README.md` and `docs/PATCH_MANIFEST_V1_2.md` |
| `questions` | defaulted | none |
| `verbosity_profile` | defaulted | `THICK` |
| `require_write_proof` | defaulted | `true` |

## Notes Surface

- Governing notes surface resolved to `./codex_notes_garden.md`.
- PRE note status: `EXECUTED`
- POST note status: pending until finalization of this audit artifact.

## Surface Resolution

Opened first-pass constitutional and truth surfaces:

- `./README.md`
- `./codex_notes_garden.md`
- `./docs/PROJECT_CHARTER.md`
- `./docs/CANONICAL_ONTOLOGY.md`
- `./docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `./docs/KNOWN_LIMITATIONS.md`
- `./docs/REGARD_MECHANISM.md`
- `./docs/TURN_LOOP_AND_MEMBRANE.md`
- `./docs/GRAPH_SCHEMA.md`
- `./docs/TUI_SPEC.md`
- `./docs/OBSERVATORY_SPEC.md`
- `./docs/OBSERVATORY_INTERACTION_SPEC.md`
- `./docs/OBSERVATORY_GEOMETRY_SPEC.md`
- `./docs/OBSERVATORY_E2E_AUDIT.md`
- `./docs/MEASUREMENT_EVENT_MODEL.md`
- `./docs/EXPERIMENT_PROTOCOLS.md`
- `./docs/SOURCE_MANIFEST.md`
- `./docs/MIGRATION_NOTES_V1_1.md`
- `./docs/PATCH_MANIFEST_V1_1.md`
- `./docs/PATCH_MANIFEST_V1_2.md`

Opened current implementation and evidence surfaces:

- `./app.py`
- `./eden/app.py`
- `./eden/config.py`
- `./eden/inference.py`
- `./eden/retrieval.py`
- `./eden/regard.py`
- `./eden/runtime.py`
- `./eden/ontology_projection.py`
- `./eden/ingest/pipeline.py`
- `./eden/semantic_relations.py`
- `./eden/storage/schema.py`
- `./eden/storage/graph_store.py`
- `./eden/observatory/service.py`
- `./eden/observatory/server.py`
- `./eden/tui/app.py`
- `./eden/tanakh/service.py`
- `./web/observatory/src/App.tsx`
- `./web/observatory/src/App.test.tsx`
- `./web/observatory/src/workbench/graphUtils.test.ts`
- selected `./tests/*.py`
- `./logs/runtime.jsonl`
- `./exports/context/latest.md`
- selected `./exports/bb298723-5fbf-4554-bf6b-ec5f4d336fbd/*.json`
- `./data/eden.db`

## Numbered Baseline Lineage Resolution

- Scan root: `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/`
- Candidate list:
  - `eden_whitepaper_v14.pdf` -> parsed version `14`
- Chosen baseline: `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/eden_whitepaper_v14.pdf`
- File hash: `sha256:0ac4ed914143db71d9035d92f9091327800e8380988fd9bc0fc3b445d1129107`
- Resolution status: `BASELINE_EXPECTATION_MATCHED`
- Baseline override active: `false`
- Baseline use in this run: drift surface and overclaim detector, not implementation proof

## Support Manuscript Resolution

- Resolution order used: newest `adam_whitepaper_*.pdf` under pipeline draft subdirectories
- Chosen support manuscript: `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/20260320_111343/pdf/adam_whitepaper_20260320_111343.pdf`
- File hash: `sha256:0c5659e33917a8526f96591cb8cde105efde09f10219dd383fbd5e857dcd2e54`
- Support status: resolved
- Support role in this run: preservation-target input only, not implementation proof

## Research Library Resolution

- Resolved path: `./assets/cannonical_secondary_sources/`
- Status: present
- Notable present canonical sources:
  - Austin
  - Foucault
  - Butler
  - Blackmore
  - Barad
  - Dennett
  - Zhang Recursive Language Models

## Archaeology and Drift Findings

1. The numbered baseline `eden_whitepaper_v14.pdf` is materially misaligned with current Adam ontology. Its extracted text repeatedly treats memodes as the main durable unit, permits knowledge memodes, and still speaks in staged-governor language. Current repo truth instead makes memes first-class, memodes derived and behavior-only, and governor/planner layers explicitly absent.
2. The newer Adam-first support manuscript improves naming, direct-loop framing, and empirical tone, but it appears to have dropped compiled canonical-source discipline. A `pdftotext | rg` pass found baseline references to Foucault, Austin, Butler, Barad, Blackmore, Dennett, and Recursive Language Models, while the Adam support manuscript surfaced none of those names.
3. Preservation target split:
   - preserve from support manuscript: Adam-first framing, graph-legibility emphasis, stronger empirical boundary language
   - restore from baseline where still admissible: Foucault archive discipline and Austin felicity/governance discipline

## Default Current Expectations Verdict

| Expectation | Verdict | Evidence anchor |
| --- | --- | --- |
| no governor in v1 | `CONFIRMED` | `docs/PROJECT_CHARTER.md`, `docs/INFERENCE_PROFILES.md`, `eden/agents/adam/profile.json` |
| no hidden planner | `CONFIRMED` | `docs/INFERENCE_PROFILES.md`, `docs/TURN_LOOP_AND_MEMBRANE.md`, inspected runtime path in `eden/runtime.py` |
| no weight training, fine-tuning, or LoRA | `PARTIALLY TRUE` | charter and truth surfaces agree; no training path surfaced in inspected runtime code; this remains an absence claim rather than a full negative proof |
| MLX is the active local runtime backend | `CONFIRMED` | `eden/config.py`, `eden/models/mlx_backend.py`, `logs/runtime.jsonl`, `tests/test_runtime_e2e.py` |
| TUI is the primary runtime surface | `CONFIRMED` | `docs/TUI_SPEC.md`, `eden/tui/app.py`, `tests/test_tui_smoke.py` |
| browser observatory is observability / measurement rather than main dialogue loop | `CONFIRMED` | `docs/TUI_SPEC.md`, `docs/OBSERVATORY_SPEC.md`, `web/observatory/src/App.tsx` |
| `adam_auto` on MLX falls back to `runtime_auto` | `CONFIRMED` | `eden/inference.py`, `tests/test_inference_profiles.py::test_adam_auto_falls_back_to_runtime_auto_for_mlx` |
| embedding-based semantic retrieval is deferred | `CONFIRMED` | `docs/KNOWN_LIMITATIONS.md`, `eden/retrieval.py` |
| observatory edit / preview / revert and causal-runtime browser exposure may be partial | `PARTIALLY TRUE` | preview/commit/revert are live and tested; trace/causality remain browser-visible but read-only; static mode keeps controls visible but non-authoritative |

## Patch Gate Verdict

Inferred patch ladder: `v1.2`

| Required capability for inferred patch | Verdict | Evidence |
| --- | --- | --- |
| live observatory JSON API | `PASS` | `README.md`, `eden/observatory/server.py`, `tests/test_observatory_server.py::test_observatory_server_exposes_live_api` |
| preview / commit / revert mutation loop | `PASS` | `eden/observatory/service.py`, `tests/test_observatory_measurements.py::test_edge_measurement_commit_and_revert_persist`, live API test |
| persistent `measurement_events` ledger | `PASS` | `eden/storage/schema.py`, `eden/storage/graph_store.py`, geometry export payload with committed + reverted events |
| memode assertion and membership refinement workflow | `PASS` | `tests/test_observatory_measurements.py::test_memode_assert_and_membership_update_persist` |
| local geometry diagnostics and compare selection | `PASS` | `geometry_diagnostics.json`, `tests/test_observatory_server.py` preview assertions |
| TUI preserved as primary runtime surface | `PASS` | `docs/TUI_SPEC.md`, `tests/test_tui_smoke.py` |
| active MLX local backend | `PASS` | `eden/config.py`, `eden/models/mlx_backend.py`, `logs/runtime.jsonl` |
| repo-wide Python proof still green | `FAIL` | `./.venv/bin/pytest -q -x` failed on missing PDF fixture |
| browser exposure of all server-side causal surfaces | `UNKNOWN` | preview/commit/revert are exposed; trace is visible but read-only; no proof that every server-side mutation-analysis path is equivalently browser-drivable |

### Next Minimal Closure Steps

1. Restore or deliberately retire `assets/cannonical_secondary_sources/bad_trip_with_jesus_theory_memoir.pdf`, then rerun `./.venv/bin/pytest -q`.
2. Decide whether the browser title and remaining public copy should be renamed from `EDEN Observatory` to `Adam Observatory`, or explicitly freeze the shell/runtime distinction in docs.
3. Tighten observatory export scoping language so operators can distinguish session-scoped ledgers from experiment-level measurement history embedded in geometry diagnostics.
4. Recompile the next numbered whitepaper draft from current repo truth: preserve Adam-first empirical framing while restoring admissible Foucault/Austin discipline.

## Basin A — Naming, Ontology, and Legacy-Shell Drift

Definition snapshot: Adam is the current project/runtime framing for this run. The repository still exposes historical `EDEN` naming in package paths, docs titles, and at least one browser-visible shell title.

Mechanism / data model:

- package/runtime code lives under `./eden/`
- launcher is `./app.py`
- top-level README still says `EDEN / ADAM v1.2`
- browser shell title in `web/observatory/src/App.tsx` still renders `EDEN Observatory`

Evidence map:

- `README.md`
- `web/observatory/src/App.tsx`
- `docs/CANONICAL_ONTOLOGY.md`
- `docs/PROJECT_CHARTER.md`
- `pdftotext` baseline lineage scan

Failure modes:

- public-facing artifacts regress into Eden-first framing and obscure the current Adam audit target
- baseline whitepaper language re-imports obsolete ontology, especially memode-as-primary and governance-object framing

Probes:

- `rg -n "EDEN / ADAM|EDEN Observatory|workbench-title" README.md web/observatory/src/App.tsx`
- `pdftotext assets/white_paper_pipeline/white_paper_drafts/eden_whitepaper_v14.pdf - | rg -n "governor|knowledge memodes|memodes are the units of persistence"`

Claim tuples:

| CLAIM | EVIDENCE | PRIMARY REGISTER | OPTIONAL MODIFIERS | GAPS / RISKS | PROBE |
| --- | --- | --- | --- | --- | --- |
| Adam is the right present-tense project/runtime name for audit prose, while EDEN strings survive as lineage anchors. | `README.md`, `docs/PROJECT_CHARTER.md`, `docs/CANONICAL_ONTOLOGY.md` | `INSTRUMENTED` |  | Public shell/package naming still mixes both labels. | `rg -n "ADAM|EDEN" README.md docs/*.md` |
| Browser-visible naming drift is still real. | `web/observatory/src/App.tsx` renders `EDEN Observatory` | `INSTRUMENTED` | `EXPLICIT_BROWSER_CONTRACT_GAP` | Operator-facing browser copy still lags the Adam-first naming discipline. | `rg -n "EDEN Observatory" web/observatory/src/App.tsx` |

Evidence excerpt / command:

```bash
rg -n "EDEN / ADAM v1.2|EDEN Observatory" README.md web/observatory/src/App.tsx
```

Proposed synthetic clay patch:

> Rename the browser shell title to `Adam Observatory`, keep `eden/` package paths unchanged, and add one explicit shell/runtime history note instead of leaving mixed naming implicit.

## Basin B — Meme / Memode Object Model

Definition snapshot: Adam treats memes as first-class graph objects. Memodes are derived second-order behavior structures built from multiple behavioral memes plus relations. Knowledge-domain rows project outward as information rather than as memodes.

Mechanism / data model:

- ontology projection distinguishes `meme`, `memode`, and `information`
- `memode_materialization_allowed(domain)` only admits behavior
- graph store rejects memodes with fewer than two members
- ingest materializes memodes only when behavior-domain support exists
- observatory audit plane distinguishes materialized support from informational passenger relations

Evidence map:

- `eden/ontology_projection.py`
- `eden/ingest/pipeline.py`
- `eden/storage/graph_store.py`
- `tests/test_observatory_measurements.py::test_memode_assert_and_membership_update_persist`
- `tests/test_observatory_measurements.py::test_memode_audit_plane_distinguishes_support_from_informational_relations`
- `tests/test_runtime_e2e.py` ontology export assertions

Failure modes:

- historical prose reintroduces knowledge memodes or cluster summaries as if they were canonical memodes
- operators assert memodes without enough behavioral support edges, causing ontology drift or invalid second-order objects

Probes:

- `./.venv/bin/pytest -q tests/test_observatory_measurements.py -k "memode_assert or memode_audit"`
- `rg -n "memode_materialization_allowed|member_ids < 2|MATERIALIZES_AS_MEMODE" eden/ontology_projection.py eden/storage/graph_store.py eden/ingest/pipeline.py`

Claim tuples:

| CLAIM | EVIDENCE | PRIMARY REGISTER | OPTIONAL MODIFIERS | GAPS / RISKS | PROBE |
| --- | --- | --- | --- | --- | --- |
| Memes are first-class and knowledge rows project as information, not memodes. | `eden/ontology_projection.py`, `tests/test_runtime_e2e.py::test_graph_payload_projects_knowledge_constatives_into_information_nodes` | `IMPLEMENTED` |  | Baseline whitepaper still describes knowledge memodes; prose drift is active. | `./.venv/bin/pytest -q tests/test_runtime_e2e.py -k knowledge_constatives` |
| Memodes are derived behavior-only structures with explicit admissibility. | `eden/ontology_projection.py`, `eden/storage/graph_store.py`, memode audit test | `IMPLEMENTED` | `DEFERRED_BY_DESIGN` | Cluster summaries remain nearby derived surfaces and can be confused with memodes if copy is sloppy. | `./.venv/bin/pytest -q tests/test_observatory_measurements.py -k memode` |

Evidence excerpt / command:

```bash
rg -n "kind =|memode_materialization_allowed|member_ids < 2|MATERIALIZES_AS_MEMODE" \
  eden/ontology_projection.py eden/storage/graph_store.py eden/ingest/pipeline.py
```

Proposed synthetic clay patch:

> Reject any memode-assert request whose selected nodes are not all behavioral memes with at least one support edge class in the allowlist, and surface the rejection reason verbatim in the browser audit pane.

## Basin C — Active Set, Retrieval Salience, and Prompt Assembly

Definition snapshot: Adam assembles a bounded active set from lexical/graph retrieval plus regard, activation, scope, and membrane penalties. The active set is a turn-local attention proxy, not persistent identity.

Mechanism / data model:

- retrieval scores combine semantic similarity, activation, regard, session bias, explicit feedback, scope penalty, and membrane penalty
- behavior items reserve at least one-third of `max_context_items`
- `preview_turn()` persists trace-visible budget and selection details before generation
- active set is exported to session/turn traces and observatory surfaces

Evidence map:

- `eden/retrieval.py`
- `eden/runtime.py::preview_turn`
- `tests/test_runtime_e2e.py::test_single_graph_bootstrap_chat_feedback_and_exports`
- `tests/test_inference_profiles.py`
- `logs/runtime.jsonl` `turn_preview_ready`

Failure modes:

- operators mistake active-set inclusion for durable persona identity
- lexical/graph retrieval can miss semantically relevant material because embeddings are deferred

Probes:

- `./.venv/bin/pytest -q tests/test_inference_profiles.py tests/test_runtime_e2e.py -k "preview or history"`
- `rg -n "behavior_target|selection_score|trace =|turn_preview_ready" eden/retrieval.py eden/runtime.py logs/runtime.jsonl`

Claim tuples:

| CLAIM | EVIDENCE | PRIMARY REGISTER | OPTIONAL MODIFIERS | GAPS / RISKS | PROBE |
| --- | --- | --- | --- | --- | --- |
| Active-set selection is bounded, weighted, and trace-visible. | `eden/retrieval.py`, `eden/runtime.py`, runtime logs | `IMPLEMENTED` |  | Exported active-set views are summaries, not the full internal prompt state. | `./.venv/bin/pytest -q tests/test_runtime_e2e.py::test_single_graph_bootstrap_chat_feedback_and_exports` |
| Retrieval is not embedding-based; it is lexical/graph heuristic plus regard-weighted pressure. | `docs/KNOWN_LIMITATIONS.md`, `eden/retrieval.py` | `IMPLEMENTED` | `DEFERRED_BY_DESIGN` | Semantically relevant misses remain plausible on sparse lexical overlap. | `./.venv/bin/pytest -q tests/test_inference_profiles.py` |

Evidence excerpt / command:

```bash
rg -n "behavior_target|selection_score|trace =|turn_preview_ready" \
  eden/retrieval.py eden/runtime.py logs/runtime.jsonl
```

Proposed synthetic clay patch:

> Add a turn-local operator note that explicitly labels the active set as a bounded salience slice and lists the first excluded near-miss item with its score delta.

## Basin D — Regard, Feedback, and Durable Selection

Definition snapshot: Regard is durable selection pressure, not prompt-time salience. Feedback changes later retrieval pressure through reward, risk, edit, persistence, and decay terms.

Mechanism / data model:

- `regard_breakdown()` composes reward, evidence, coherence, persistence, decay, isolation, and risk
- verdict mapping: `accept`, `edit`, `reject`, `skip`
- `apply_feedback()` requires explanation for `accept` / `reject` and explanation plus corrected text for `edit`
- feedback updates memodes first, then member memes, then indexes feedback text back into the graph

Evidence map:

- `eden/regard.py`
- `eden/runtime.py::apply_feedback`
- `tests/test_regard.py`
- `tests/test_runtime_e2e.py::test_single_graph_bootstrap_chat_feedback_and_exports`
- `data/eden.db` counts show `feedback_events=53`

Failure modes:

- feedback without explanation collapses evidence quality and weakens later auditability
- over-strong risk or decay tuning can cool useful memes/memodes out of retrieval even after legitimate edits

Probes:

- `./.venv/bin/pytest -q tests/test_regard.py tests/test_runtime_e2e.py::test_single_graph_bootstrap_chat_feedback_and_exports`
- `rg -n "accept|edit|reject|skip|reward|risk|persistence|decay" eden/regard.py eden/runtime.py`

Claim tuples:

| CLAIM | EVIDENCE | PRIMARY REGISTER | OPTIONAL MODIFIERS | GAPS / RISKS | PROBE |
| --- | --- | --- | --- | --- | --- |
| Regard math is implemented as durable retrieval pressure rather than a transient prompt tag. | `eden/regard.py`, `tests/test_regard.py` | `IMPLEMENTED` |  | No separate calibration artifact proves the chosen weights are optimal. | `./.venv/bin/pytest -q tests/test_regard.py` |
| Feedback is explicit, structured, and reinjected into later retrieval. | `eden/runtime.py`, e2e feedback retrieval assertions | `IMPLEMENTED` |  | High-quality explanation discipline still depends on the operator. | `./.venv/bin/pytest -q tests/test_runtime_e2e.py::test_single_graph_bootstrap_chat_feedback_and_exports` |

Evidence excerpt / command:

```bash
rg -n "if verdict == \"accept\"|if verdict == \"edit\"|if verdict == \"reject\"|return {\"reward\"" eden/regard.py
```

Proposed synthetic clay patch:

> Persist a compact feedback-attribution ledger row that shows which later retrieval wins were causally helped by a given feedback event, without promoting correlation into proof.

## Basin E — Turn Loop, Membrane, and Traceability

Definition snapshot: Adam’s direct v1 loop is `input -> retrieve/assemble -> Adam response -> membrane -> feedback -> graph update`. The membrane removes reasoning spill and scaffolding but does not act as a hidden planner.

Mechanism / data model:

- `preview_turn()` assembles active set, history window, profile, and budget
- `chat()` runs preview, generation, membrane, persistence, indexing, logging, hum refresh, and observatory invalidation
- membrane strips headings like `Answer:`, `Basis:`, and `Next Step:`
- trace events and membrane events persist separately

Evidence map:

- `docs/TURN_LOOP_AND_MEMBRANE.md`
- `eden/runtime.py`
- `tests/test_runtime_membrane.py`
- `tests/test_runtime_e2e.py`
- `logs/runtime.jsonl`
- `data/eden.db` counts show `trace_events=240`, `membrane_events=75`

Failure modes:

- membrane repairs can hide a generation-quality problem by salvaging a poor raw response
- operators can overread trace visibility as full causal proof when it remains an instrumentation surface

Probes:

- `./.venv/bin/pytest -q tests/test_runtime_membrane.py tests/test_runtime_e2e.py -k "chat or membrane"`
- `rg -n "preview_turn|_apply_membrane|record_membrane_event|chat\\(" eden/runtime.py`

Claim tuples:

| CLAIM | EVIDENCE | PRIMARY REGISTER | OPTIONAL MODIFIERS | GAPS / RISKS | PROBE |
| --- | --- | --- | --- | --- | --- |
| The direct v1 loop is implemented without a hidden planner stage. | `eden/runtime.py`, membrane tests, inference docs | `IMPLEMENTED` |  | Session-start wake-up audits are visible extra control paths and must not be mistaken for hidden turn-time planning. | `./.venv/bin/pytest -q tests/test_runtime_membrane.py tests/test_runtime_e2e.py -k "start_session or membrane"` |
| Membrane behavior is explicit and operator-visible in stored turn state and logs. | e2e tests, `logs/runtime.jsonl`, DB membrane-event counts | `IMPLEMENTED` | `INSTRUMENTED` | The membrane proves output sanitation, not answer correctness. | `rg -n "\"event\": \"hum_refreshed\"|\"event\": \"generation_complete\"" logs/runtime.jsonl | tail` |

Evidence excerpt / command:

```bash
rg -n "preview_turn|_apply_membrane|record_membrane_event|def chat\\(" eden/runtime.py
```

Proposed synthetic clay patch:

> Export a compact per-turn membrane diff that shows raw-generation scaffolding removed versus final operator-facing text, without exposing disallowed reasoning content in the default UI.

## Basin F — TUI Runtime Surface

Definition snapshot: The TUI is the primary runtime surface. Dialogue-first interaction dominates; observatory launching and exports are secondary actions off the strip.

Mechanism / data model:

- repo root launcher re-execs into `.venv`
- `eden/app.py` defaults to the TUI `app` command path
- TUI action strip includes review, observatory, export, session tuning, and ingestion
- multiline composer, inline review, runtime chyron, and hum/reasoning panels are all present

Evidence map:

- `app.py`
- `eden/app.py`
- `docs/TUI_SPEC.md`
- `eden/tui/app.py`
- `tests/test_tui_smoke.py`

Failure modes:

- the browser observatory can be mistaken for the main dialogue loop because it is visually rich
- TUI complexity can regress boot flow, focus, or inline review if smoke coverage is not maintained

Probes:

- `./.venv/bin/pytest -q tests/test_tui_smoke.py`
- `rg -n "Open Browser Observatory|Composer|Reasoning / Hum|runtime_action_menu" eden/tui/app.py docs/TUI_SPEC.md`

Claim tuples:

| CLAIM | EVIDENCE | PRIMARY REGISTER | OPTIONAL MODIFIERS | GAPS / RISKS | PROBE |
| --- | --- | --- | --- | --- | --- |
| The TUI is the primary runtime interface and boots through the repo-local Python path. | `app.py`, `eden/app.py`, `docs/TUI_SPEC.md` | `IMPLEMENTED` |  | README title still preserves EDEN/ADAM split wording. | `./.venv/bin/pytest -q tests/test_cli_entry.py tests/test_tui_smoke.py::test_tui_boots_single_graph_mode_and_uses_multiline_composer` |
| Review, ingestion, session tuning, observatory launch, and multiline composition are all live in the TUI surface. | `tests/test_tui_smoke.py` | `IMPLEMENTED` |  | This turn did not launch a live interactive TUI manually; evidence relies on deterministic test harness plus code read. | `./.venv/bin/pytest -q tests/test_tui_smoke.py -k "observatory or tune_session or multiline"` |

Evidence excerpt / command:

```bash
./.venv/bin/pytest -q tests/test_tui_smoke.py::test_tui_boots_single_graph_mode_and_uses_multiline_composer
```

Proposed synthetic clay patch:

> Add a one-line boot badge that says `Primary runtime surface: TUI` whenever the browser observatory is launched from the strip, so cross-surface hierarchy stays explicit.

## Basin G — Observatory Read Surfaces

Definition snapshot: The observatory exposes graph, basin, geometry, measurement, transcript, runtime, trace, and Tanakh read surfaces through a live API and static-export sidecars. It is a workbench, not a replacement dialogue loop.

Mechanism / data model:

- server GET endpoints expose overview, graph, basin, geometry, measurement-events, tanakh, sessions, turns, active set, trace, runtime status, and runtime model
- frontend defers heavy payloads and can operate in live or static-export mode
- SSE invalidation exists after commit/revert
- static exports keep controls visible but clearly disable mutation authority

Evidence map:

- `eden/observatory/server.py`
- `eden/observatory/service.py`
- `web/observatory/src/App.tsx`
- `tests/test_observatory_server.py`
- `docs/OBSERVATORY_E2E_AUDIT.md`
- `web/observatory/test-results/*/.last-run.json`

Failure modes:

- operators misread static-export controls as live mutation affordances
- payload scope or deferred loading can create false impressions that data is missing when it is only not yet loaded

Probes:

- `./.venv/bin/pytest -q tests/test_observatory_server.py`
- `npm --prefix web/observatory test`

Claim tuples:

| CLAIM | EVIDENCE | PRIMARY REGISTER | OPTIONAL MODIFIERS | GAPS / RISKS | PROBE |
| --- | --- | --- | --- | --- | --- |
| Observatory read surfaces are live API backed and also exportable as static sidecars. | server tests, build meta check, frontend copy | `IMPLEMENTED` |  | Export bundles are summaries and can diverge from raw DB totals by projection or session scoping. | `./.venv/bin/pytest -q tests/test_observatory_server.py::test_observatory_server_exposes_live_api` |
| Static mode remains honest by leaving action chrome visible but disabled. | `web/observatory/src/App.tsx`, `docs/OBSERVATORY_E2E_AUDIT.md`, Vitest | `IMPLEMENTED` | `EXPLICIT_BROWSER_CONTRACT_GAP` | Honesty depends on copy remaining precise; a future CSS-only disable would be insufficient. | `npm --prefix web/observatory test` |

Evidence excerpt / command:

```bash
rg -n "Static export mode keeps|Trace and causality remain read-only|liveEnabled" web/observatory/src/App.tsx
```

Proposed synthetic clay patch:

> Add an always-visible source badge that names the active authority for the current panel: `live API`, `static export`, or `not loaded yet`.

## Basin H — Observatory Mutation / Measurement Contract

Definition snapshot: Adam v1.2 implements preview, commit, and revert semantics for observatory mutation. Measurement events persist before/proposed/committed state and are replayable or revertible, but browser causality stays read-only.

Mechanism / data model:

- `measurement_events` table stores state snapshots and revert ancestry
- service layer computes preview graph patches and compare selections
- commit persists measurement events, trace events, and refreshed exports
- revert records a new event linked by `reverted_from_event_id`
- frontend exposes preview, commit, and revert buttons when live API is available

Evidence map:

- `eden/storage/schema.py`
- `eden/storage/graph_store.py`
- `eden/observatory/service.py`
- `eden/observatory/server.py`
- `web/observatory/src/App.tsx`
- `tests/test_observatory_measurements.py`
- `tests/test_observatory_server.py`
- `exports/bb298723-5fbf-4554-bf6b-ec5f4d336fbd/geometry_diagnostics.json`

Failure modes:

- session-scoped measurement ledgers can look empty while geometry diagnostics still embed experiment-level event history, creating interpretive confusion
- browser users can see trace/causality but cannot mutate those paths directly, which may be misread as missing causality rather than bounded exposure

Probes:

- `./.venv/bin/pytest -q tests/test_observatory_measurements.py tests/test_observatory_server.py -k "preview or revert or measurement"`
- `./.venv/bin/python scripts/check_observatory_build_meta.py`

Claim tuples:

| CLAIM | EVIDENCE | PRIMARY REGISTER | OPTIONAL MODIFIERS | GAPS / RISKS | PROBE |
| --- | --- | --- | --- | --- | --- |
| Preview / commit / revert semantics are implemented end to end. | service code, measurement tests, live API test | `IMPLEMENTED` |  | This turn did not rerun Playwright journeys, so browser proof leans on retained canonical audit artifacts plus fresh Vitest/API proof. | `./.venv/bin/pytest -q tests/test_observatory_measurements.py::test_edge_measurement_commit_and_revert_persist tests/test_observatory_server.py::test_observatory_server_exposes_live_api` |
| Browser exposure is real but not total: trace and causality remain read-only. | `web/observatory/src/App.tsx`, server trace endpoint | `INSTRUMENTED` | `EXPLICIT_BROWSER_CONTRACT_GAP` | Operators can inspect causal surfaces but not author them except through preview/commit/revert. | `rg -n "Trace and causality remain read-only|session_trace|preview|commit|revert" web/observatory/src/App.tsx eden/observatory/server.py` |

Evidence excerpt / command:

```bash
./.venv/bin/pytest -q tests/test_observatory_measurements.py::test_edge_measurement_commit_and_revert_persist
```

Proposed synthetic clay patch:

> When the ledger view is session-scoped, show a second count for experiment-wide historical measurement events so zero-event ledgers do not silently contradict geometry history.

## Basin I — Geometry and Basin Evidence

Definition snapshot: Geometry and basin exports are evidence surfaces, not free interpretation engines. They expose observed and derived structure, local reports, verdict slices, coordinate families, and measurement overlays, but interpretation must stay bounded.

Mechanism / data model:

- geometry export includes slices for full graph, current session, current active set, and verdict partitions
- basin payload exposes projection metadata and sparse diagnostics
- coordinate methods are documented in export metadata
- local geometry and ablation measurements can be persisted without necessarily mutating topology

Evidence map:

- `docs/OBSERVATORY_GEOMETRY_SPEC.md`
- `docs/GEOMETRY_EVIDENCE_POLICY.md` (referenced constitutionally even if not reopened in this turn)
- `exports/bb298723-5fbf-4554-bf6b-ec5f4d336fbd/geometry_diagnostics.json`
- `tests/test_geometry.py`
- `tests/test_observatory_measurements.py::test_ablation_and_motif_actions_emit_trace_and_revertible_events`
- `tests/test_observatory_measurements.py::test_basin_payload_exposes_projection_metadata_and_sparse_diagnostics`

Failure modes:

- operators read derived geometry as semantic proof rather than as measurement surface
- slice labels can be confused with ontological categories, especially where verdict partitions or active-set slices are involved

Probes:

- `./.venv/bin/pytest -q tests/test_geometry.py tests/test_observatory_measurements.py -k "basin or ablation or local_selection"`
- `./.venv/bin/python - <<'PY' ... geometry_diagnostics.json ... PY`

Claim tuples:

| CLAIM | EVIDENCE | PRIMARY REGISTER | OPTIONAL MODIFIERS | GAPS / RISKS | PROBE |
| --- | --- | --- | --- | --- | --- |
| Geometry exports are implemented and include multiple bounded slice families plus measurement overlays. | `geometry_diagnostics.json`, geometry tests | `IMPLEMENTED` |  | Density is null in the sampled export slices, so not every metric is always populated. | `./.venv/bin/pytest -q tests/test_geometry.py` |
| Basin and ablation surfaces support evidence production, not free causal claims. | basin payload tests, ablation measurement tests, evidence policy docs | `IMPLEMENTED` | `BOUNDED_FALLBACK` | Interpretation still depends on explicit ablation or local measurement, not visual pattern alone. | `./.venv/bin/pytest -q tests/test_observatory_measurements.py -k "ablation or basin"` |

Evidence excerpt / command:

```bash
./.venv/bin/python - <<'PY'
import json, pathlib
data = json.loads(pathlib.Path('exports/bb298723-5fbf-4554-bf6b-ec5f4d336fbd/geometry_diagnostics.json').read_text())
print(data['coordinate_methods'])
print(sorted(data['slices'].keys()))
PY
```

Proposed synthetic clay patch:

> Add a per-slice badge set of `observed`, `derived`, or `speculative-not-computed` so geometry consumers do not infer proof strength from visual richness alone.

## Basin J — Local-First Runtime and Model Constraints

Definition snapshot: Adam is local-first and MLX-backed in the active runtime path. `adam_auto` on MLX visibly falls back to `runtime_auto`. Governor, training, and embeddings are absent or deferred by design.

Mechanism / data model:

- default runtime settings choose backend `mlx` and a repo-local model directory
- MLX adapter loads local model files and can run reasoning and answer fallback phases
- `adam_auto` persists the request but resolves to `runtime_auto` on MLX
- no inspected runtime code path performs fine-tuning, LoRA, or embedding retrieval

Evidence map:

- `app.py`
- `eden/config.py`
- `eden/models/mlx_backend.py`
- `eden/inference.py`
- `tests/test_inference_profiles.py`
- `tests/test_runtime_e2e.py`
- `logs/runtime.jsonl`

Failure modes:

- absence claims around training or planners can be overstated if future code lands outside the inspected paths
- MLX-only defaults can look implemented even when model files are unavailable on a fresh machine without provisioning

Probes:

- `./.venv/bin/pytest -q tests/test_inference_profiles.py tests/test_runtime_e2e.py::test_runtime_launch_profile_and_session_snapshot`
- `rg -n "model_backend: str = \"mlx\"|adam_auto_fallback_runtime_auto|mlx_lm" eden/config.py eden/inference.py eden/models/mlx_backend.py`

Claim tuples:

| CLAIM | EVIDENCE | PRIMARY REGISTER | OPTIONAL MODIFIERS | GAPS / RISKS | PROBE |
| --- | --- | --- | --- | --- | --- |
| MLX is the active local runtime backend in the implemented path. | config defaults, MLX adapter, runtime logs, tests | `IMPLEMENTED` |  | Fresh-machine model readiness still depends on local model provisioning. | `./.venv/bin/pytest -q tests/test_runtime_e2e.py::test_runtime_launch_profile_and_session_snapshot` |
| `adam_auto` on MLX is a visible bounded fallback, not a hidden second planner pass. | `eden/inference.py`, inference-profile test | `IMPLEMENTED` | `BOUNDED_FALLBACK` | Future patch levels could supersede this fallback if a separate chooser is added. | `./.venv/bin/pytest -q tests/test_inference_profiles.py::test_adam_auto_falls_back_to_runtime_auto_for_mlx` |

Evidence excerpt / command:

```bash
rg -n "adam_auto_fallback_runtime_auto|does not run a separate MLX prepass chooser|model_backend: str = \"mlx\"" \
  eden/inference.py eden/config.py
```

Proposed synthetic clay patch:

> Emit a startup capability line that says `backend=mlx`, `mode=local-first`, `adam_auto=runtime_auto fallback on MLX`, and `embeddings=deferred` so operators do not infer capabilities from legacy manuscripts.

## Basin K — Tanakh Sidecar Surface

Definition snapshot: Tanakh is present as an additive instrument. It is not the core Adam loop. It carries its own provenance, deterministic analyzer outputs, and scene-generation surfaces.

Mechanism / data model:

- Tanakh substrate sync writes manifest/index/passage cache
- analyzers like gematria are deterministic for fixed inputs
- merkavah scene compilation is deterministic under fixed params and seed
- observatory and export bundle expose Tanakh artifacts and optional live runs

Evidence map:

- `eden/tanakh/service.py`
- `tests/test_tanakh_tools.py`
- `tests/test_observatory_server.py`
- `exports/bb298723-5fbf-4554-bf6b-ec5f4d336fbd/tanakh_surface.json`

Failure modes:

- Tanakh outputs can be mistaken for canonical runtime memory rather than additive sidecar artifacts
- scene richness can invite mystical interpretation where only deterministic rendering/provenance is actually proved

Probes:

- `./.venv/bin/pytest -q tests/test_tanakh_tools.py`
- `./.venv/bin/pytest -q tests/test_observatory_server.py::test_observatory_server_exposes_live_api`

Claim tuples:

| CLAIM | EVIDENCE | PRIMARY REGISTER | OPTIONAL MODIFIERS | GAPS / RISKS | PROBE |
| --- | --- | --- | --- | --- | --- |
| Tanakh sidecar surfaces are implemented and export provenance-rich artifacts. | Tanakh tests, tanakh surface export, live API test | `IMPLEMENTED` | `SERVER_SIDE_ONLY` | The core Adam loop does not depend on Tanakh; over-integrating it into whitepaper identity would overclaim. | `./.venv/bin/pytest -q tests/test_tanakh_tools.py` |
| Tanakh analyzers and scene generation are deterministic under fixed parameters. | `tests/test_tanakh_tools.py::test_tanakh_analyzer_and_scene_hashes_are_deterministic` | `IMPLEMENTED` |  | Deterministic output is not the same as interpretive validity. | `./.venv/bin/pytest -q tests/test_tanakh_tools.py::test_tanakh_analyzer_and_scene_hashes_are_deterministic` |

Evidence excerpt / command:

```bash
./.venv/bin/pytest -q tests/test_tanakh_tools.py
```

Proposed synthetic clay patch:

> Label every Tanakh panel with `Additive sidecar; not canonical Adam memory` and pin the passage hash beside the scene hash.

## Current Capability Summary

What Adam currently implements with the strongest repo-grounded support:

- local-first MLX-backed runtime bootstrap
- direct v1 turn loop with preview, generation, membrane, persistence, feedback, and graph update
- explicit regard and feedback propagation
- memes as first-class objects; memodes as derived behavior structures
- TUI-primary runtime surface
- live observatory read API plus static-export sidecars
- preview / commit / revert mutation path with `measurement_events`
- geometry, basin, and memode audit surfaces
- session-start deterministic wake-up audits, with optional visible MLX review gates
- additive Tanakh sidecar with deterministic analyzers and scene outputs

What Adam instruments but does not fully close:

- browser-visible trace and causality: visible and queryable, but still read-only
- cross-surface measurement interpretation: session and experiment scope must be read carefully
- absence claims around training/planners: strongly supported, but still negative claims

What Adam currently defers by design:

- embedding-based retrieval
- weight training / fine-tuning / LoRA
- hidden governor / hidden planner

## Prompt Drift Self-Check

Prompt assumptions confirmed:

- governance had to be resolved before analysis
- canonical pipeline root under `assets/white_paper_pipeline/` is active
- numbered baseline lineage winner was `eden_whitepaper_v14.pdf`
- support manuscript had to be resolved separately from baseline
- v1.2 is still inferable from current repo surfaces
- browser observatory must be treated as measurement/observability workbench rather than the primary dialogue surface

Prompt assumptions superseded by stronger current repo evidence:

- baseline-era memode/governance framing is no longer admissible as present-tense implementation truth; current repo ontology makes memes first-class and memodes derived behavior-only
- the repo’s current browser mutation path is stronger than a pure observability-only description; preview/commit/revert are live
- some exported measurement surfaces are session-sensitive enough that a plain `measurement events exist` claim needs scope qualification

Prompt assumptions not fully evaluable from this run:

- exhaustive absence of any training-related experimentation outside the inspected runtime paths
- full browser parity for every server-side causal-analysis path beyond the tested preview/commit/revert surfaces

Current repo surfaces that materially replace older expectations:

- `docs/CANONICAL_ONTOLOGY.md`
- `docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/OBSERVATORY_E2E_AUDIT.md`
- `tests/test_observatory_measurements.py`
- `tests/test_observatory_server.py`

Baseline-drift results:

- baseline override active: `false`
- designated baseline draft opened: `yes`
- overclaims identified relative to that draft: `yes`

Detected overclaims in `eden_whitepaper_v14.pdf` relative to current repo truth:

1. It treats memodes as the main durable unit of persistence and allows knowledge memodes, while current ontology treats memes as first-class and projects knowledge rows outward as information.
2. It still speaks in staged-governor language and governance-object framing, while current repo truth explicitly states there is no governor in v1.
3. It implies historical shell/runtime architecture that predates the current Adam-first audit framing and v1.2 mutation-capable observatory.

## Execution / Build Status Log

| Status | Command / action | Result | Affected output family | Downstream consequence |
| --- | --- | --- | --- | --- |
| `EXECUTED` | `./.venv/bin/pytest -q -x` | failed at `tests/test_ingest.py::test_pages_pdf_fixture_extracts_readable_text` because `/Users/brianray/Adam/assets/cannonical_secondary_sources/bad_trip_with_jesus_theory_memoir.pdf` does not exist | repo-wide Python regression proof | Python suite not green; ingest extractor path remains implemented but proof family is `DEPENDENCY_BLOCKED` by missing fixture |
| `EXECUTED` | `npm --prefix web/observatory test` | passed: `2` files, `12` tests | browser frontend proof | fresh frontend proof available for this turn |
| `EXECUTION_BLOCKED` | `npm --prefix web/observatory test -- --runInBand` | Vitest rejected unsupported flag `--runInBand`; rerun with repo-native command | browser frontend proof | no product inference taken from this failed invocation |
| `EXECUTED` | `./.venv/bin/python scripts/check_observatory_build_meta.py` | passed; frontend build hash matched source hash | observatory build freshness | confirms built static bundle matches current source hash |
| `EXECUTED` | runtime-log inspection | `generation_complete` and `hum_refreshed` events observed with `"backend":"mlx"` | runtime evidence | corroborates MLX path and hum refresh behavior |
| `EXECUTED` | DB inspection of `data/eden.db` | sessions, turns, memes, memodes, edges, feedback, measurement, trace, and membrane tables populated | persistence evidence | supports implemented persistence surfaces |
| `SKIPPED` | new PDF build | `PDF_BUILD_REQUIRED` was unset | whitepaper PDF output | intelligence brief remained Markdown-only as allowed |
| `SKIPPED` | Playwright rerun | canonical browser proof already retained in `docs/OBSERVATORY_E2E_AUDIT.md` and `web/observatory/test-results/` | browser E2E proof | current brief relies on retained E2E audit plus fresh Vitest/API/build proof |

## Shortest Proof Path From Here

1. Fix the missing PDF fixture or downgrade that one ingest test to an explicit optional-fixture guard.
2. Rerun `./.venv/bin/pytest -q`.
3. If the numbered whitepaper lineage is being advanced, use this brief plus the Adam-first support manuscript as the drafting inputs, then explicitly restore admissible Foucault/Austin framing from the baseline where current repo truth still supports it.
