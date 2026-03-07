# Repo Guidance - Codex-Builder

This file defines the operating contract for Codex-Builder inside the Adam repository.

In this repo, prose is not decoration. The spec stack in `docs/` is a set of natural-language contracts: versioned constraint surfaces that govern code, runtime behavior, evidence, and handoff. Code is operative reality. Tests, traces, exports, and manifests are evidence surfaces. Robust work ties these together in one turn.

## Runtime Invariants

- Use the repo-local `.venv` and prefer `python3.12`.
- Keep the real runtime on MLX. Do not introduce Ollama, vLLM, llama.cpp, or remote inference as the core path.
- Treat the TUI as the primary runtime interface. Browser work is observability/export work unless the project charter changes.
- Preserve the ontology: memes are first-class; memodes are derived structures built from multiple memes plus relations.
- Preserve the v1 control loop: `input -> retrieve/assemble -> Adam response -> membrane -> feedback -> graph update`.
- Keep feedback explicit and structured. `accept` and `reject` require explanation; `edit` requires explanation and corrected text.

## Robustness Doctrine

Work in the loop's native order:

`spec -> implementation -> evidence -> audit -> next action`

Apply strict claim discipline:

- `Implemented` = proved by code plus run output, test output, or an equivalent evidence surface from this turn.
- `Instrumented` = telemetry or logging exists and measures something real, but correctness is still not proved.
- `Conceptual` = specified in prose or proposed in notes, but not yet proved in code/runtime.
- `Unknown` = insufficient evidence.

Rules:

- Do not overclaim.
- Treat summaries, including your own, as marketing until anchored.
- If evidence is missing, downgrade the claim, name the exact missing artifact, and prescribe the shortest proof path.
- Operate one-shot when a bounded path exists. Record assumptions in PRE-FLIGHT instead of deferring.
- Every load-bearing change should leave a ratchet: a regression test, a durable trace signature, an export artifact, or a reproducible command result.
- Guard ontology and vocabulary. Do not let sloppy synonyms create category errors.
- Do not collapse archive with evidence, behavior with knowledge, or implemented status with conceptual proposal.

## Natural Language Programming

Natural language in Adam is the human prompt and archive channel. It is ambiguous by default and is not a programming language merely because it is written down.

A natural-language contract exists only when language is anchored to:

- a versioned spec surface
- canonical terms and scoped relations
- a concrete implementation surface
- at least one reproducible evidence path

Until those anchors exist, treat the item as `Conceptual`, not `Implemented`.

A new canonical term, workflow, or behavior is only complete when it has a spec anchor, an implementation anchor, and an evidence-producing path. When the term is externally sourced or canon-derived, record that provenance in `docs/SOURCE_MANIFEST.md` when materially relevant.

Do not treat prose as vibes, aspiration, or post-hoc narration. Treat it as executable constraint text with named terms, explicit boundaries, and verification paths.

## Canonical Spec Stack

The `docs/` directory is the canonical source of truth before a turn and the natural-language contract surface after a turn. Read the relevant slice before editing code. Restore spec/code alignment before handoff.

Normative contract surfaces:

- `docs/PROJECT_CHARTER.md` - project scope and primary directional constraints
- `docs/CANONICAL_ONTOLOGY.md` - first-class objects, derived objects, edge semantics, domain split, memode ladder
- `docs/TURN_LOOP_AND_MEMBRANE.md` - turn order, membrane behavior, prompt assembly inputs, operator-visible trace
- `docs/REGARD_MECHANISM.md` - regard semantics and selection pressure
- `docs/GRAPH_SCHEMA.md` - persistent graph/storage shape
- `docs/TUI_SPEC.md` - startup flow, chat layout, panel grammar, key runtime surfaces
- `docs/INFERENCE_PROFILES.md` - inference modes, budgets, and profile semantics
- `docs/DOCUMENT_INGEST.md` - ingest pipeline and provenance discipline
- `docs/EXPERIMENT_PROTOCOLS.md` - blank/seeded flows and feedback protocol
- `docs/OBSERVATORY_SPEC.md` - browser observatory contract
- `docs/OBSERVATORY_INTERACTION_SPEC.md` - inspect/measure/edit/ablate/compare workflows
- `docs/OBSERVATORY_GEOMETRY_SPEC.md` - geometry slices, metrics, ablations, interpretation boundary
- `docs/GEOMETRY_EVIDENCE_POLICY.md` - evidence labels, forbidden shortcuts, required provenance
- `docs/MEASUREMENT_EVENT_MODEL.md` - measurement event persistence and revertible mutation semantics

Status and constraint surfaces:

- `docs/IMPLEMENTATION_TRUTH_TABLE.md` - current status by capability and evidence notes
- `docs/KNOWN_LIMITATIONS.md` - explicit caveats, fallbacks, and deferred surfaces

Archaeology and provenance surfaces:

- `docs/SOURCE_MANIFEST.md` - source authority, inspiration, and provenance notes
- latest `docs/PATCH_MANIFEST_*.md` - patch-cycle scope, changed files, and deferred items

`SOURCE_MANIFEST.md` and `PATCH_MANIFEST_*.md` inform provenance and archaeology. They do not override normative behavior specs.

## Spec-to-Change Mapping

When a change touches one of these surfaces, update the matching contract in the same turn.

- Ontology, term definitions, or domain boundaries -> `docs/CANONICAL_ONTOLOGY.md`
- Turn order, membrane behavior, or prompt assembly -> `docs/TURN_LOOP_AND_MEMBRANE.md`
- Regard math, decay, or selection pressure -> `docs/REGARD_MECHANISM.md`
- Table shape, persistence, or graph semantics -> `docs/GRAPH_SCHEMA.md`
- Startup flow, pane layout, launcher contract, or key bindings -> `docs/TUI_SPEC.md`
- Inference modes, budgets, or profile behavior -> `docs/INFERENCE_PROFILES.md`
- Ingest pipeline or provenance handling -> `docs/DOCUMENT_INGEST.md`
- Experiment flow or feedback semantics -> `docs/EXPERIMENT_PROTOCOLS.md`
- Observatory UX, API behavior, or edit flow -> observatory spec documents
- Geometry claims or measurement interpretation -> geometry spec documents plus evidence policy
- Measurement persistence or revert semantics -> `docs/MEASUREMENT_EVENT_MODEL.md`
- Feature status changes -> `docs/IMPLEMENTATION_TRUTH_TABLE.md` and `docs/KNOWN_LIMITATIONS.md`
- Source authority or external reference material that materially shaped the build -> `docs/SOURCE_MANIFEST.md`
- Major patch-cycle archaeology -> latest `docs/PATCH_MANIFEST_*.md`

If code and spec disagree, do not leave silent drift. Either bring code back to the existing contract or revise the contract in the same turn and record the status change truthfully.

## Code Discipline

- Use `apply_patch` for source edits.
- Keep documentation synchronized with code changes.
- Read the relevant spec documents before editing code.
- Do not summarize the entire repo. Read and cite only the task-relevant spec slice.
- When introducing a new canonical term, workflow, or behavioral promise, anchor it in the relevant spec document before treating it as real.
- Preserve exact repository vocabulary unless the task is explicitly to revise the vocabulary. If you must introduce a new term, map it to existing ontology or record the ontology change explicitly.
- Run tests before handoff when behavior changes:

```
./.venv/bin/pytest -q
```

- When feature status changes, update:

```
docs/IMPLEMENTATION_TRUTH_TABLE.md
docs/KNOWN_LIMITATIONS.md
```

## Codex Working Notepad

Codex-Builder must maintain an append-only operational log at:

```
/codex_notes_garden.md
```

This file is a working-memory bridge, a flight recorder, and a lightweight audit surface. It is not a diary and not a design novella.

Entries must be appended only. Never rewrite, compress, or silently normalize prior entries.

### Notepad Style Contract

Write notes in short, fielded prose.

- Be factual, bounded, and adversarial to overclaim.
- Name exact files, docs, commands, tests, traces, exports, and unresolved risks.
- Use repository vocabulary exactly: meme, memode, regard, membrane, active set, observatory, measurement event, Brian the operator.
- Separate observed facts from intended actions and from unknowns.
- Do not write motivational filler, self-congratulation, vague promises, or long narrative summaries.
- Do not say a behavior is implemented unless the evidence named in the note proves it.
- If evidence is absent, write the missing artifact and the shortest proof path.

### Pre-Flight Entry (before editing code)

Before making code changes, append:

```md
## [TIMESTAMP] PRE-FLIGHT
Operator task:
Task checksum:
Repo situation:
Relevant spec surfaces read:
Natural-language contracts in force:
Files/modules likely in scope:
Status register:
- Implemented:
- Instrumented:
- Conceptual:
- Unknown:
Risks / invariants:
Evidence plan:
Shortest proof path:
```

Pre-flight rules:

- Read the relevant spec documents first.
- Name the exact contract surfaces governing the change.
- Record any visible spec/code conflict before editing.
- If the working tree is already dirty or mid-refactor, say so in `Repo situation`.
- Keep the note local to the task; do not summarize the whole repo.
- Prefer the shortest bounded proof path over vague intent.

### Post-Flight Entry (after completing work)

After edits and verification, append:

```md
## [TIMESTAMP] POST-FLIGHT
Files changed:
Specs changed:
Natural-language contracts added/revised/preserved:
Behavior implemented or modified:
Evidence produced (tests / traces / commands / exports):
Status register changes:
- Implemented:
- Instrumented:
- Conceptual:
- Unknown:
Truth-table / limitations updates:
Remaining uncertainties:
Next shortest proof path:
```

Post-flight rules:

- No `Implemented` claim without code plus evidence from this turn.
- If the turn only added logging, previews, or export surfaces, mark that as `Instrumented` unless correctness is also proved.
- If a proposal was specified but not built, mark it `Conceptual`.
- If the evidence surface is missing or ambiguous, mark it `Unknown` and name the missing artifact.
- State exactly which spec documents were updated to restore contract/code alignment.

## Handoff Standard

Before finishing a task:

1. Read the relevant spec surfaces.
2. Make the bounded code change.
3. Produce evidence.
4. Update the relevant contract surfaces in `docs/`.
5. Update truth-table / limitations surfaces when status changed.
6. Append the POST-FLIGHT note.
7. Provide the operator a short summary of what changed, how it was verified, and what remains conceptual or unknown.

The goal is a stable loop: spec -> implementation -> evidence -> audit -> next action.
