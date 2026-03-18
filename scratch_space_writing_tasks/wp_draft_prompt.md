# ADAM V1 — INTELLIGENCE BRIEF PRODUCTION PROMPT

You are Codex.

Produce an intelligence brief for the current Adam repository. This is a forensic, engineering-grade audit artifact, not marketing copy, not speculative architecture, and not a vibes-based positioning memo.

Your job is to determine what Adam currently implements, instruments, defers, and merely describes, using repo-grounded evidence only.

NAME DISCIPLINE
- This run is about ADAM.
- Use “Adam” as the project/runtime name in all newly generated prose unless an opened artifact explicitly requires the historical EDEN/Adam shell-runtime distinction.
- Treat legacy `EDEN` / `eden/` strings in code paths, docs, manifests, and filenames as implementation-history anchors, not as permission to frame the current project as Eden.
- If the shell/runtime distinction is materially necessary, state it once, precisely, and then keep the brief centered on Adam v1.

REPO ROOT RESOLUTION
- Prefer `.` if the current working directory is already the Adam repo root.
- Otherwise resolve `/Users/brianray/Adam`.
- Use repo-relative paths in the brief whenever possible.

WHITE PAPER PIPELINE ROOT
The canonical output root for white-paper pipeline artifacts is:

`/Users/brianray/Adam/assets/white_paper_pipeline`

Canonical subdirectories:
- intelligence briefs: `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs`
- writing memos: `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos`
- whitepaper drafts: `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts`

Hard rules:
- Treat these as the primary pipeline artifact locations.
- Create them if missing and the environment allows writing.
- If writing is blocked, record `WRITE_BLOCKED` with exact attempted absolute path(s).
- Repo root resolution and pipeline output resolution are distinct.
- Even if the current working directory is repo root, pipeline artifacts still write under `/Users/brianray/Adam/assets/white_paper_pipeline/...`
- Do not confuse pipeline artifact directories with implementation-truth surfaces under `./docs/`, `./eden/`, `./tests/`, `./logs/`, or `./exports/`.

Fallback rule:
- Legacy root-level directories such as `./intelligence_briefs/`, `./whitepaper_prewriting_memo/`, and `./whitepaper_drafts/` may still be searched as archaeology or fallback inputs if present, but they are no longer the canonical output targets.

GOVERNANCE
- If `./AGENTS.md` exists, follow it.
- Do not depend on `AGENTS_CODEX-WRITER.md`, `AGENTS_CODEX_WRITER.md`, `AGENTS-CODEX_WRITER.md`, or any writer-specialized agent file. They are not part of this pipeline.
- If `./codex_notes_garden.md` exists and the environment is writable, you may append concise PRE/POST run notes for continuity. This is recommended, not a stop condition. If write is blocked, record `WRITE_BLOCKED` with the attempted path; do not invent success.

UNIVERSALIZATION RULE
This prompt is designed for repeated use across the remaining Adam project lifecycle.

Do not treat any file path, patch label, UI limitation, or present-tense repo condition named in this prompt as permanently canonical unless it is re-confirmed by currently opened evidence.

Prefer current repo truth over prompt inertia.

Treat prompt assumptions as auditable scaffolding, not self-justifying fact.

SURFACE RESOLUTION RULE
Treat explicitly listed files as preferred high-value entry points, not as a permanent exhaustive file contract.

If a listed file is missing, search nearby current-repo equivalents before concluding `MISSING`.

Search order:
1. exact listed path
2. same filename elsewhere under `./docs/`
3. close semantic equivalents under:
   - `./docs/`
   - `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs/`
   - `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos/`
   - `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/`
   - `./exports/context/`
4. if no equivalent exists, record `MISSING`

Hard rule:
- prefer opened current equivalents over stale filename loyalty
- do not hallucinate equivalence
- record the resolved substitute path explicitly

REQUIRED CONTEXT SURFACES
Read these current-repo surfaces first if present:

Core repo discipline:
- `./AGENTS.md`
- `./README.md`
- `./codex_notes_garden.md`

Project constitution and truth surfaces:
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

Implementation surfaces:
- `./eden/`
- `./tests/`
- `./scripts/`
- `./data/eden.db` or current repo-equivalent local database artifacts if direct inspection is part of the run

Supporting evidence surfaces:
- `./logs/runtime.jsonl`
- `./exports/context/latest.md` and `./exports/context/*.md`
- selected `./exports/<experiment_id>/*.json`, `*.manifest.json`, `*.html`
- `./exports/conversations/**/*.md`

Historical conceptual anchors (NOT implementation proof):
- `./assets/seed_canon/eden_whitepaper_v14.pdf`
- `./assets/seed_canon/cannonical_secondary_sources/` or `./assets/seed_canon/canonical_secondary_sources/` (whichever exists)

Missingness rule:
- If a surface is missing, record `MISSING` and continue.
- If present but empty, record `EMPTY` and continue.
- Missingness is never permission to fabricate.

DEFAULT CURRENT EXPECTATIONS TO VERIFY (NOT SELF-JUSTIFYING)
Unless contradicted by newer opened evidence, the auditor should test for the following conditions and report them explicitly as:

`CONFIRMED | SUPERSEDED | NOT LOCATED | PARTIALLY TRUE`

Candidate expectations:
- no governor in v1
- no hidden planner
- no weight training, fine-tuning, or LoRA
- MLX is the active local runtime backend
- TUI is the primary runtime surface
- browser observatory functions as an observability / measurement instrument rather than the main dialogue loop
- `adam_auto` on the MLX path falls back to `runtime_auto`
- embedding-based semantic retrieval is deferred
- observatory edit / preview / revert and causal-runtime browser exposure may be partial and must be verified rather than assumed

Hard rule:
- Never treat these expectations as proof.
- They are drift-detection probes only.

BROWSER EXPOSURE DISCIPLINE
For any server-side observatory capability, determine whether it is:
- fully browser-exposed
- partially browser-exposed
- server-side only
- documented but not currently evidenced

Use the modifier:
- `EXPLICIT_BROWSER_CONTRACT_GAP`

whenever the server-side mechanism exists but current browser exposure is incomplete.

Do not bake a specific gap list into the reusable base prompt unless the current run artifacts prove it.

SOURCE OF TRUTH + RESOLUTION RULES
1) Evidence primacy.
- Current implementation truth comes from opened code, tests, runtime-visible artifacts, and the current docs truth surfaces.
- `./docs/IMPLEMENTATION_TRUTH_TABLE.md` and `./docs/KNOWN_LIMITATIONS.md` are high-value constitutional summaries, but they do not outrank contradictory code/test evidence you actually open.
- Tests and executed scripts count as the strongest practical execution-proof surfaces when they directly exercise the mechanism in question.
- Exports and logs can corroborate runtime behavior; they do not license architectural invention.

2) Historical references are not current implementation proof.
- `./assets/seed_canon/eden_whitepaper_v14.pdf` is a historical conceptual anchor only.
- Canonical secondary sources discipline method and definition stability; they do not prove Adam implements anything.

3) Current archaeology surfaces replace the old `prompt_arch` / `for_review` assumptions.
Treat the following as the current drift-control archive:
- `./docs/PATCH_MANIFEST_V1_1.md`
- `./docs/PATCH_MANIFEST_V1_2.md`
- `./docs/MIGRATION_NOTES_V1_1.md`
- prior intelligence briefs in `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs/` if present
- prior whitepaper memos in `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos/` if present
- prior whitepaper drafts in `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/` if present
- legacy fallback only:
  - `./intelligence_briefs/`
  - `./whitepaper_prewriting_memo/`
  - `./whitepaper_drafts/`
- `./exports/context/*.md` if present

Hard rule:
- pipeline-root directories are canonical
- legacy root-level directories are fallback archaeology surfaces only

4) Path discipline.
- Prefer repo-relative citations.
- Include absolute paths only when reproducibility truly requires them.

PRIMARY REGISTERS (STRICT)
Use exactly one primary register per claim:
- IMPLEMENTED = code path exists and this run includes execution proof or an opened, unambiguous test/log/export trace that proves the mechanism actually ran
- INSTRUMENTED = logged, exported, or test-visible, but correctness, completeness, or current UI exposure remains partial
- CONCEPTUAL = specified in prose or manifests, but not proven running in the currently opened evidence
- UNKNOWN = no evidence located

REPO-NATIVE MODIFIERS (OPTIONAL BUT IMPORTANT)
Add zero or more modifiers when the repo truth demands them:
- BOUNDED_FALLBACK
- SERVER_SIDE_ONLY
- EXPLICIT_BROWSER_CONTRACT_GAP
- DEFERRED_BY_DESIGN
- HISTORICAL_REFERENCE_ONLY

Hard rule:
- Do not collapse a modifier away when it carries real causal meaning. Example: “implemented server-side; explicit browser contract gap” is not the same as “implemented in the current browser UI.”

EVIDENCE CLASSES
- PRIMARY: code, tests, schemas, configs, manifests, current docs that directly match code, current runtime artifacts
- SUPPORTING: notes, patch manifests, exports, logs, context dumps, screenshots, generated HTML reports
- SECONDARY-CANONICAL: canonical secondary sources under `assets/seed_canon/...secondary_sources`
- SECONDARY: other attached/operator-supplied literature

METHODOLOGICAL CONSTRAINTS
Treat prose as executable specification only when it cashes out in code, schema, tests, or repeatable evidence.

Use the current canonical secondary sources only as discipline surfaces:
- Foucault: archaeology / archive / discontinuity discipline
- Blackmore and Dennett: replication, selection pressure, persistence, but not metaphor-as-proof
- Austin and Butler: governance phrases require felicity conditions and observed enforcement paths
- Barad: apparatus matters; traces, measurements, and boundary-making practices determine accountability

Compile-or-omit rule:
If a theoretical reference cannot be compiled into a definition boundary, an admissibility rule, or a concrete evidence obligation, omit it.

NON-COLLAPSE INVARIANTS
- Regard is durable selection, not prompt-time salience.
- Active-set salience is an attention proxy, not persistent identity.
- Observability is not control.
- Server-side capability is not browser-exposed capability.
- Historical whitepaper language is not present-tense implementation proof.
- Cluster summaries are not memodes.
- Memodes are not free-floating labels.

RUN CARD
Resolve these before analysis. Do not stall if missing.
- `run_slug`: short stable label; default `core_audit`
- `audience_mode`: `{internal_audit | whitepaper_support}`; default `internal_audit`
- `runtime_patch_level`: inferred current release / patch label, or `UNKNOWN`; do not assume historical enumerations exhaust future project states
- `questions`: explicit pressure-vessel questions; default none
- `comparators_enabled`: explicit comparator modules; default none
- `baseline_draft_path`: optional whitepaper baseline path; default none
- `verbosity_profile`: `{THICK | STANDARD | LITE}`; default `THICK`
- `require_write_proof`: `{true|false}`; default `true`

RELEASE / PATCH LADDER GATE
Infer the active release or patch ladder from currently opened manifests, migration notes, README, and current artifact lineage.

Prefer, in order:
- explicit patch manifest files
- migration notes
- README / docs release statements
- prior intelligence briefs
- writing memos
- whitepaper drafts
- exports/context run summaries

If no stable ladder can be inferred, use:
`runtime_patch_level = UNKNOWN`

When a ladder is inferred, evaluate only capabilities actually evidenced in currently opened artifacts.

Do not assume that the historical `v1 / v1.1 / v1.2` ladder is still exhaustive or current.

If no stable ladder is inferable, emit a `Current Capability Gate` based on observed subsystems instead of historical patch labels.

Include a `Patch Gate Verdict` section:
- For the inferred patch level, list required capabilities and mark PASS / FAIL / UNKNOWN with evidence anchors.
- Include `Next Minimal Closure Steps`: a shortest path of evidence-producing probes that would convert UNKNOWN or partial states into stronger proof.
- If no stable ladder is inferable, emit a `Current Capability Gate` instead.

CORE BASINS TO AUDIT
You must cover these basins. Keep boundaries crisp.

A) Naming, ontology, and legacy-shell drift
Required: Adam naming discipline, EDEN remnants, shell/runtime distinction handling, public-claim hygiene.

B) Meme / memode object model
Required: first-class vs derived objects, admissibility floor, cluster/non-cluster distinction, persistence shape.

C) Active set, retrieval salience, and prompt assembly
Required: what is bounded retrieval, what selects into the active set, what is visible to the operator, and where salience ends.

D) Regard, feedback, and durable selection
Required: `eden/regard.py`, reward/risk/edit propagation, persistence/decay, and how feedback changes later retrieval pressure.

E) Turn loop, membrane, and traceability
Required: direct v1 loop, membrane effects, what is persisted, operator-visible trace fields, and what the membrane does not do.

F) TUI runtime surface
Required: current boot path, dialogue-first grammar, review flow, budget/inference surfaces, session handling, file outputs.

G) Observatory read surfaces
Required: graph, basin, geometry, measurement ledger, Tanakh sidecars, live API vs static export, SSE invalidation.

H) Observatory mutation / measurement contract
Required:
- preview / commit / revert semantics if present
- measurement-event semantics if present
- server-side mutation capabilities
- browser exposure completeness
- causal visibility back into runtime
- explicit distinction between documented contract, tested contract, and current UI availability

I) Geometry and basin evidence
Required: observed vs derived vs speculative labels, slice semantics, ablations, basin overlays, interpretation boundary.

J) Local-first runtime and model constraints
Required: MLX-only runtime, model storage, `adam_auto` fallback reality, no governor, no training, no embeddings.

K) Tanakh sidecar surface (ONLY IF PRESENT)
Required: additive instrument status, provenance, derived-vs-canonical distinction, scene determinism.
If absent: explicitly say so and stop there.

PER-BASIN MINIMUMS
For each basin A–J:
1. Definition snapshot
2. Mechanism / data model
3. Evidence map with paths
4. Failure modes (at least 2)
5. Probes (at least 2; prefer runnable tests/scripts)
6. Claim tuples
   Each tuple must include:
   - CLAIM
   - EVIDENCE
   - PRIMARY REGISTER
   - OPTIONAL MODIFIERS
   - GAPS / RISKS
   - PROBE
7. At least one short evidence excerpt or exact command that would generate it
8. One synthetic clay patch: controlled-English constraint material clearly marked as proposed, never as implementation proof

COMPARATIVE POSTURE — OPT-IN ONLY
- If `comparators_enabled` is empty, do not generate a comparative positioning section.
- You may still cite related work as secondary framing, but do not write “Adam is not just X” unless the operator explicitly enables a comparator.
- If a comparator is enabled, define the baseline first and compare only implemented or instrumented mechanisms.

AUDIT PROCEDURE
Pass 1: Context ingest
- Read the current repo truth surfaces first.

Pass 2: Archaeology ingest
- Read patch manifests, migration notes, prior briefs/memos/drafts if present.
- Enumerate what changed, what persisted, and what silently vanished.

Pass 3: Mechanism grounding
- Anchor each strong claim to code, test, log, export, or manifest evidence.
- Downgrade aggressively when proof is missing.

Pass 4: Basin analysis
- Produce claim tuples basin by basin.

Pass 5: Patch gate verdict
- Evaluate the current repo against the inferred release / patch ladder when it is evidentially grounded.
- If no stable ladder is inferable, emit a `Current Capability Gate` instead.

Pass 6: Verbosity gate
- Expand only with evidence excerpts, mechanism walk-throughs, failure cases, and probes.
- Do not pad with theory.

OUTPUT ARTIFACTS
Write these if the environment allows. If it does not, emit them in-response and mark `WRITE_BLOCKED` honestly.

Required:
- `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs/adam_intelligence_<YYYY-MM-DD>_<run_slug>.md`

Optional support artifacts when useful:
- `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs/_support/adam_mechanism_matrix_<YYYYMMDD>_<run_slug>.md`
- `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs/_support/implementation_work_order_<YYYYMMDD>_<run_slug>.md`
- `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs/_support/synthetic_clay_patchkit_<YYYYMMDD>_<run_slug>.md`

OUTPUT NAMING RULE
Default artifact family is:
- `adam_intelligence_<date>_<run_slug>.md`

If the project later adopts a new repo-wide naming convention, prefer the current repo convention discovered in existing pipeline-root or legacy `intelligence_briefs` artifacts over this default, but preserve `adam_` unless current repo evidence clearly replaces it.

WRITE PROOF
If `require_write_proof=true`, record deterministic write proof: `ls -l`, file size, hash, or equivalent.

REPO-DRIFT SELF-CHECK (MANDATORY)
Before finalizing the brief, explicitly check whether this prompt itself contains stale assumptions relative to the currently opened repo.

Report:
- assumptions in this prompt that were confirmed
- assumptions in this prompt that were superseded
- assumptions in this prompt that could not be evaluated
- any current repo surfaces that materially replace the prompt’s older expectations

If a prompt assumption is superseded by stronger current evidence, follow the repo evidence, not the prompt’s historical wording.

START CONDITION
Begin now.
- Do not ask for permission.
- Do not invent missing directories from the old Eden beta workflow.
- Produce the intelligence brief for the Adam repo that actually exists.


----------------------------------------
----------------------------------------
----------------------------------------

# ADAM V1 — WHITEPAPER PRE-WRITING MEMO PROMPT

You are Codex.

You are generating Step 2 in the current Adam whitepaper workflow:
1. Intelligence brief
2. Codex pre-writing memo
3. Whitepaper generation

There is no Claude memo step in this pipeline.

ROLE
Produce an advisory pre-writing memo that helps the later whitepaper pass decide what to write next, what to downgrade, and what evidence must be anchored before any public-facing claim is allowed to harden.

This memo is not the whitepaper. It is not a substitute for the final analysis pass. It is a pressure-adjustment artifact.

NAME DISCIPLINE
- This memo is about Adam.
- Use “Adam” as the current project/runtime name.
- Treat legacy `EDEN` / `eden/` strings as historical/internal anchors unless an opened artifact explicitly requires the shell/runtime distinction.

REPO ROOT RESOLUTION
- Prefer `.` if already in the Adam repo root.
- Otherwise resolve `/Users/brianray/Adam`.

WHITE PAPER PIPELINE ROOT
The canonical output root for white-paper pipeline artifacts is:

`/Users/brianray/Adam/assets/white_paper_pipeline`

Canonical subdirectories:
- intelligence briefs: `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs`
- writing memos: `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos`
- whitepaper drafts: `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts`

Hard rules:
- Treat these as the primary pipeline artifact locations.
- Create them if missing and the environment allows writing.
- If writing is blocked, record `WRITE_BLOCKED` with exact attempted absolute path(s).
- Repo root resolution and pipeline output resolution are distinct.
- Even if the current working directory is repo root, pipeline artifacts still write under `/Users/brianray/Adam/assets/white_paper_pipeline/...`
- Do not confuse pipeline artifact directories with implementation-truth surfaces under `./docs/`, `./eden/`, `./tests/`, `./logs/`, or `./exports/`.

Fallback rule:
- Legacy root-level directories such as `./intelligence_briefs/`, `./whitepaper_prewriting_memo/`, and `./whitepaper_drafts/` may still be searched as archaeology or fallback inputs if present, but they are no longer the canonical output targets.

PIPELINE ARTIFACT RESOLUTION
Use the canonical white-paper pipeline root:

`/Users/brianray/Adam/assets/white_paper_pipeline`

Canonical input / output directories:
- intelligence briefs: `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs`
- writing memos: `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos`
- whitepaper drafts: `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts`

Legacy fallbacks may be searched only if the canonical pipeline directories do not yet contain the needed artifact:
- `./intelligence_briefs/`
- `./whitepaper_prewriting_memo/`
- `./whitepaper_drafts/`

Hard rule:
- treat the pipeline directories as canonical artifact lineage surfaces
- treat legacy repo-root directories as fallback archaeology only

GOVERNANCE
- If `./AGENTS.md` exists, follow it.
- Do not depend on any writer-specialized agent file.
- If `./codex_notes_garden.md` exists and is writable, you may append short PRE/POST notes. This is recommended, not a blocking condition.

UNIVERSALIZATION RULE
This prompt is designed for repeated use across the remaining Adam project lifecycle.

Do not treat any file path, patch label, UI limitation, or present-tense repo condition named in this prompt as permanently canonical unless it is re-confirmed by currently opened evidence.

Prefer current repo truth over prompt inertia.

Treat prompt assumptions as auditable scaffolding, not self-justifying fact.

PRIMARY INPUTS
Read in this order when present:

1. Latest intelligence brief
   Search in:
   - `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs/`
   - fallback `./intelligence_briefs/`
   - If missing: record `INTELLIGENCE_BRIEF_MISSING` and proceed from current repo truth surfaces.

2. Current repo truth surfaces:
- `./docs/PROJECT_CHARTER.md`
- `./docs/CANONICAL_ONTOLOGY.md`
- `./docs/IMPLEMENTATION_TRUTH_TABLE.md`
- `./docs/KNOWN_LIMITATIONS.md`
- `./docs/REGARD_MECHANISM.md`
- `./docs/TURN_LOOP_AND_MEMBRANE.md`
- `./docs/TUI_SPEC.md`
- `./docs/OBSERVATORY_SPEC.md`
- `./docs/OBSERVATORY_INTERACTION_SPEC.md`
- `./docs/OBSERVATORY_GEOMETRY_SPEC.md`
- `./docs/OBSERVATORY_E2E_AUDIT.md`
- `./docs/MEASUREMENT_EVENT_MODEL.md`
- `./docs/EXPERIMENT_PROTOCOLS.md`
- `./docs/SOURCE_MANIFEST.md`

3. Repo archaeology surfaces:
- `./docs/MIGRATION_NOTES_V1_1.md`
- `./docs/PATCH_MANIFEST_V1_1.md`
- `./docs/PATCH_MANIFEST_V1_2.md`
- prior memos in `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos/` if present
- prior whitepaper drafts in `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/` if present
- legacy fallback only:
  - `./whitepaper_prewriting_memo/` if present
  - `./whitepaper_drafts/` if present
- `./assets/seed_canon/eden_whitepaper_v14.pdf` as historical context only

4. Evidence and runtime surfaces as needed:
- `./tests/`
- `./logs/runtime.jsonl`
- `./exports/context/latest.md`
- selected `./exports/conversations/**/*.md`
- selected `./exports/<experiment_id>/*.json` and manifests

Hard rule:
- treat the pipeline directories as canonical artifact lineage surfaces
- treat legacy repo-root directories as fallback archaeology only
- do not treat pipeline artifact directories as implementation proof by themselves

TRUTH RULES
- Current implementation truth must come from opened code/tests/runtime-visible artifacts, not from inherited whitepaper prose.
- `./docs/IMPLEMENTATION_TRUTH_TABLE.md` and `./docs/KNOWN_LIMITATIONS.md` are required discipline surfaces for the memo.
- Use the same strict primary registers as the intelligence brief:
  - IMPLEMENTED
  - INSTRUMENTED
  - CONCEPTUAL
  - UNKNOWN
- Add modifiers when needed:
  - BOUNDED_FALLBACK
  - SERVER_SIDE_ONLY
  - EXPLICIT_BROWSER_CONTRACT_GAP
  - DEFERRED_BY_DESIGN
  - HISTORICAL_REFERENCE_ONLY

DEFAULT CURRENT EXPECTATIONS TO VERIFY (NOT SELF-JUSTIFYING)
Unless contradicted by newer opened evidence, the memo should test for the following conditions and report them explicitly as:

`CONFIRMED | SUPERSEDED | NOT LOCATED | PARTIALLY TRUE`

Candidate expectations:
- no governor in v1
- no hidden planner
- no training / LoRA / fine-tuning
- MLX is the active local runtime backend
- TUI is the primary runtime surface
- browser observatory functions as an observability / measurement instrument rather than the main dialogue loop
- `adam_auto` on the MLX path falls back to `runtime_auto`
- embedding-based semantic retrieval is deferred
- observatory edit / preview / revert and causal-runtime browser exposure may be partial and must be verified rather than assumed

Hard rule:
- Never treat these expectations as proof.
- They are drift-detection probes only.

BROWSER EXPOSURE DISCIPLINE
For any observatory mutation or measurement capability, distinguish:
- documented contract
- server-side tested contract
- browser-exposed contract
- current browser gap or partial exposure

Do not let the memo hard-code specific UI gaps unless the currently opened evidence proves them.

ADVISORY DISCIPLINE
This memo may do four things only:
1. Stabilize constraints.
2. Surface drift and downgrade risks.
3. Rank what the whitepaper should tackle next.
4. Point to concrete anchors and evidence obligations.

It may not silently launder speculative or historical claims into the implemented register.

OPTIONAL SECONDARY DISCIPLINE
If canonical secondary sources exist under `./assets/seed_canon/cannonical_secondary_sources/` or `./assets/seed_canon/canonical_secondary_sources/`, you may use them only to discipline definitions and admissibility rules, never to prove implementation.

DELIVERABLE STRUCTURE
Address the memo to the later whitepaper-generation pass. Use this exact section order:

1. Header
2. Corpus Read Receipt
3. Situational Summary
   - implemented
   - instrumented
   - conceptual
   - unknown
   - with modifiers where needed
4. Constraint Ledger
   - current hard boundaries
   - definitional non-collapse rules
   - evidence obligations for strong claims
5. Drift and Downgrade Ledger
   - what prior language must be weakened or deleted
   - where historical Eden phrasing exceeds current Adam proof
   - where browser/UI wording must separate from server-side capability
6. What The Whitepaper Should Tackle Next
   - ranked priorities only
   - each priority must include done-condition + anchor path(s)
7. Research Feed
   - OPTIONAL
   - include only if you actually have local or attached sources that materially sharpen the paper
   - no invented field survey
8. Open Questions and Decision Points
   - state uncertainty without asking the operator questions
   - give decision criteria and the shortest proof path
9. Claim→Anchor Map
   - claim id
   - short claim text
   - register
   - modifiers
   - anchor path / test / trace / work order
10. Integration Notes
   - how the later whitepaper pass should use this memo without being hijacked by it

STYLE
- Tight, high-signal prose.
- Minimal bullets.
- No decorative theory.
- Every recommendation must cash out in a path, test, trace, export, or explicit missing artifact request.

OUTPUT ARTIFACT
Write if possible:
- `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos/<YYYYMMDD_HHMMSS>_codex_memo.md`

If write is blocked:
- emit the memo in full
- record `WRITE_BLOCKED`
- include the exact attempted absolute path
- do not pretend it was saved

PROMPT-ASSUMPTION SELF-CHECK (MANDATORY)
Before finalizing the memo, explicitly report:
- which memo assumptions were confirmed by current repo evidence
- which memo assumptions were superseded
- which memo assumptions could not be evaluated
- which current repo surfaces materially replace older memo expectations

If a memo assumption conflicts with stronger current evidence, follow the evidence.

BEGIN NOW
- Do not ask for permission.
- Do not mention Claude.
- Do not depend on old `for_review/` or writer-agent scaffolding.
- Produce the Adam v1 memo that the current repo can actually support.

----------------------------------------
----------------------------------------
----------------------------------------

# ADAM V1 — WHITEPAPER GENERATION PROMPT

You are Codex.

Generate or revise the Adam v1 whitepaper as a repo-grounded scientific/technical artifact. Treat prose as executable specification. Treat revision as refactoring. Treat the current Adam repo as the truth condition for any implementation-strength claim.

This is Step 3 of 3:
1. Intelligence brief
2. Codex pre-writing memo
3. Whitepaper generation

Only two upstream artifact classes are expected for this run:
- intelligence brief
- Codex pre-writing memo

If either is missing, record the missingness and continue under current repo truth.

ROLE
Your job is not to produce marketing prose or a vibes-based conceptual essay. Your job is to compile the current Adam repository, its current evidence surfaces, and its current drift-controlled artifact lineage into a coherent whitepaper that remains scientifically legible without laundering speculative or historical claims into present-tense implementation.

Treat this pass as the final integrator:
- it must absorb the intelligence brief and pre-writing memo without being captured by them
- it must remain subordinate to current repo truth
- it must preserve continuity with prior drafts where continuity is still evidence-compatible
- it must explicitly surface discontinuity where prior language outruns current proof

NAME DISCIPLINE
- This whitepaper is about Adam.
- Use “Adam” as the project/runtime name throughout new prose.
- Legacy `EDEN` / `eden/` strings in current repo artifacts are historical/internal anchors. They may be cited in code paths, legacy manifests, or historical framing, but they are not the default public name for the current paper.
- If the shell/runtime distinction is genuinely needed, explain it once, precisely, and then keep the paper centered on Adam v1.

REPO ROOT RESOLUTION
- Prefer `.` if already at repo root.
- Otherwise resolve `/Users/brianray/Adam`.

WHITE PAPER PIPELINE ROOT
The canonical output root for white-paper pipeline artifacts is:

`/Users/brianray/Adam/assets/white_paper_pipeline`

Canonical subdirectories:
- intelligence briefs: `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs`
- writing memos: `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos`
- whitepaper drafts: `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts`

Hard rules:
- Treat these as the primary pipeline artifact locations.
- Create them if missing and the environment allows writing.
- If writing is blocked, record `WRITE_BLOCKED` with exact attempted absolute path(s).
- Repo root resolution and pipeline output resolution are distinct.
- Even if the current working directory is repo root, pipeline artifacts still write under `/Users/brianray/Adam/assets/white_paper_pipeline/...`
- Do not confuse pipeline artifact directories with implementation-truth surfaces under `./docs/`, `./eden/`, `./tests/`, `./logs/`, or `./exports/`.

Fallback rule:
- Legacy root-level directories such as `./intelligence_briefs/`, `./whitepaper_prewriting_memo/`, and `./whitepaper_drafts/` may still be searched as archaeology or fallback inputs if present, but they are no longer the canonical output targets.

FAIL-CLOSED GOVERNANCE RESOLUTION
Resolve governance before inventory, drafting, or canonization.

Attempt governance paths in this order:
1. `./AGENTS.md`
2. `<REPO_ROOT>/AGENTS.md`
3. repo-root matches for `AGENTS*.md`, excluding stale writer-specialized aliases unless current repo evidence explicitly points to them

For every attempted path, record:
- absolute path
- exists / missing
- opened / not opened
- accepted / rejected
- reason

Hard rules:
- If `./AGENTS.md` exists, it governs.
- Do not depend on `AGENTS_CODEX-WRITER.md` or any writer-specialized agent file unless current repo evidence explicitly reactivates it.
- If governance cannot be established from current repo evidence, record `GOVERNANCE_UNRESOLVED` and fail closed.
- The only allowed degraded mode is a limited audit-output mode explaining unresolved governance. Do not draft or canonize the whitepaper in degraded mode.

If governance remains unresolved after admissible current-repo resolution attempts, classify the run as `FAIL`.

In this degraded mode, emit only:
- the governance resolution log
- a short degraded-mode report explaining why drafting and canonization were not allowed
- the execution/build status log

Do not produce draft, figure, bibliography, or canonization outputs in degraded mode.

GOVERNANCE GATE PRECEDENCE
If governance is unresolved, the governance failure state supersedes the generic run pipeline.

Hard rules:
- Do not proceed to baseline selection, empirical extraction, figure generation, rewrite/refactor, citation verification, LaTeX build, or canonization.
- Generic full-run output requirements apply only when governance is resolved and drafting is allowed.
- In governance-unresolved degraded mode, only the explicitly allowed degraded-mode artifacts may be written.

MANDATORY PRE / POST RUN-NOTE DISCIPLINE
Resolve the canonical run-note surface from the governing file. In the current Adam repo, prefer `./codex_notes_garden.md` when governance names it.

Governance dependency:
- Do not independently guess or resolve a canonical notes surface if governance is unresolved.
- In governance-unresolved degraded mode, PRE and POST note actions are `SKIPPED`, and the reason must be recorded in the execution/build status log.

Hard rules:
- Write PRE notes before final execution or drafting.
- Write POST notes before finalization.
- If the notes file is not writable, record `WRITE_BLOCKED` with attempted absolute path(s) and reasons.
- Do not silently skip PRE or POST.
- When governance is resolved, record the resolved notes file path or `MISSING`.
- When governance is unresolved, do not guess `MISSING` unless that missingness was independently established from admissible evidence; record instead in the short degraded-mode report and/or the execution/build status log that notes-surface resolution was skipped because governance was unresolved.

UNIVERSALIZATION RULE
This prompt is designed for repeated use across the remaining Adam project lifecycle.

Do not treat any file path, patch label, UI limitation, or present-tense repo condition named in this prompt as permanently canonical unless it is re-confirmed by currently opened evidence.

Prefer current repo truth over prompt inertia.

Treat prompt assumptions as auditable scaffolding, not self-justifying fact.

RECURSIVE NATURAL LANGUAGE PROGRAMMING / SELF-SIMILARITY CONTRACT
This drafting process is not merely “documentation around a codebase.” It is part of the codebase’s second implementation surface: controlled English constrained by evidence.

In this workflow:
- prose is allowed to function as executable specification
- the compilation target is code, tests, logs, traces, figures, and auditable claims
- drift artifacts are regression tests for the prose surface
- the whitepaper must remain an isomorphic projection of the repository’s strongest evidence-backed commitments

Self-similarity is correctness, not style. The paper should recur to the same canonical primitives the repo actually supports, with stable denotation across:
- docs
- code
- tests
- runtime artifacts
- briefs
- memos
- draft lineage

If a strong claim in the paper cannot be pointed back to an actual file path, symbol, test, trace, export, or reproducible evidence excerpt, it must not appear in implementation-strength language.

If the repo visibly implements a mechanism but the paper cannot name it cleanly and place it in the causal story, that is under-specification and must be repaired.

BASELINE DRAFT RESOLUTION
Resolve the baseline in this order:

1. If the operator explicitly provides `BASELINE_DRAFT_PATH`, use it.
2. Else if `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/` already contains prior Adam draft artifacts, choose the latest deterministic candidate:
   - prefer highest explicit `vNN` suffix if present
   - otherwise newest modified timestamp
3. Else if legacy `./whitepaper_drafts/` already contains prior Adam draft artifacts, choose the latest deterministic candidate there as a fallback archaeology surface only:
   - prefer highest explicit `vNN` suffix if present
   - otherwise newest modified timestamp
4. Else if `./assets/seed_canon/eden_whitepaper_v14.pdf` exists, treat it as a historical conceptual reference only, not as the current canonical Adam draft
5. Else start fresh from the current repo truth surfaces

Record which case fired.
Record file hash for any baseline artifact actually used.

BASELINE CANDIDATE FILTER
Eligible baseline artifacts are manuscript-bearing files only:
- `*.tex`
- `*.md`
- `*.pdf`
- canonical pointer pairs such as `LATEST_ADAM_WHITEPAPER.pdf` plus its provenance manifest may be used to resolve the real manuscript artifact

Exclude from baseline selection:
- `audit/`
- `figure_bundle/`
- `data/`
- LaTeX auxiliary files
- build logs
- manifests that are not canonical provenance pointers
- per-run support files that are not themselves draft manuscripts

Hard rule:
- provenance manifests are metadata for manuscript resolution only and are not themselves eligible baseline manuscripts

If selecting from a run directory, prefer the manuscript artifact named by the run’s provenance file when present.

RUN VERSION
Set:
- `THIS_RUN_VERSION = YYYYMMDD_HHMMSS` in `America/New_York`

Write all run outputs under:
- `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/<THIS_RUN_VERSION>/`

Required subpaths:
- `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/<THIS_RUN_VERSION>/latex/`
- `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/<THIS_RUN_VERSION>/pdf/`
- `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/<THIS_RUN_VERSION>/audit/`
- `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/<THIS_RUN_VERSION>/figure_bundle/`
- `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/<THIS_RUN_VERSION>/data/`

These full output subpaths are required only when governance is resolved and the run proceeds beyond degraded mode.
In governance-unresolved degraded mode, only the audit output family is permitted.

The `pdf/` output directory is always created when writing is permitted and governance is resolved.
It must contain either:
- the compiled PDF artifact
- or an explicit build-status note when PDF generation was skipped or blocked

RUN CONFIG / CONTROL-FLOW GUARD
Resolve a deterministic `RUN_CONFIG` before drafting or full-run artifact generation.

Audit these operator fields whether present or not:
- `BASELINE_DRAFT_PATH`
- `WHY_NOW`
- `AUDIENCE`
- `RED_LINES`
- `COMPARATORS_ENABLED`
- `PDF_BUILD_REQUIRED`
- operator-supplied attachments or external artifacts

Hard rules:
- Record each field as `PROVIDED`, `UNSET`, or `PLACEHOLDER`.
- If a field is missing, continue with a bounded default. Do not invent facts and do not halt when a safe continuation path exists.
- If `WHY_NOW` is missing, frame urgency only as current-repo drift control and evidence refresh.
- If `AUDIENCE` is missing, default to technically literate readers who need scientific legibility plus repo-grounded evidence.
- If `RED_LINES` is missing, default to: no fabricated implementation claims, no browser overclaim, no Eden-only path regression, no silent omission.
- If `COMPARATORS_ENABLED` is missing, treat comparative claims as disabled.
- If `PDF_BUILD_REQUIRED` is missing, continue the drafting/audit path and record whether PDF build was attempted, skipped, or blocked.
- Record what was provided, what was missing, and what defaults were used.
- Do not ask the operator for clarification when a safe documented continuation path exists.

Governance-unresolved degraded mode:
- resolve only the minimal `RUN_CONFIG` needed for gating and context capture
- record that minimal `RUN_CONFIG` status in the short degraded-mode report and/or the execution/build status log
- do not require a separate full run-config audit artifact in degraded mode

EXECUTION STATUS DISCIPLINE
Use these statuses where relevant:
- `EXECUTED`
- `SKIPPED`
- `EXECUTION_BLOCKED`
- `DEPENDENCY_BLOCKED`
- `WRITE_BLOCKED`

If a test, script, build, or launch attempt fails because of missing dependencies, permissions, environment limits, or unavailable services, record:
- exact attempted command
- failure reason
- affected output family
- downstream consequence for run classification

Use `SKIPPED` when an action is intentionally not run because operator configuration, phase gating, missing applicability, or explicit degraded-mode rules make execution unnecessary.

Do not collapse an intentional skip into `EXECUTION_BLOCKED` or `DEPENDENCY_BLOCKED`.

Record these statuses in the execution/build status log.

Do not convert environment inability into fabricated implementation success or failure.

CANONIZATION
If a compiled PDF exists and passed the required verification steps, copy it to:
- `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/LATEST_ADAM_WHITEPAPER.pdf`

Also write a small provenance file:
- `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/LATEST_ADAM_WHITEPAPER.json`

with:
- source run directory
- timestamp
- hash
- baseline artifact used

If PDF build is skipped, blocked, or fails, do not overwrite `LATEST_ADAM_WHITEPAPER.pdf` or its provenance manifest.
Record PDF build status, failure or skip reason, and downstream consequence in the audit artifacts.

SURFACE RESOLUTION RULE
Treat explicitly listed files as preferred high-value entry points, not as a permanent exhaustive file contract.

If a listed file is missing, search nearby current-repo equivalents before concluding `MISSING`.

Search order:
1. exact listed path
2. same filename elsewhere under `./docs/`
3. close semantic equivalents under:
   - `./docs/`
   - `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs/`
   - `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos/`
   - `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/`
   - `./exports/context/`
4. if no equivalent exists, record `MISSING`

Hard rule:
- prefer opened current equivalents over stale filename loyalty
- do not hallucinate equivalence
- record the resolved substitute path explicitly

AUTHORITY STACK / SOURCE OF TRUTH
Use this precedence order when surfaces disagree:
1. opened current code, direct tests, and audited runtime/export evidence from the current repo
2. opened current normative docs in `./docs/` plus current `README.md`
3. audit artifacts produced in this run
4. current pipeline briefs, memos, and drafts under `/Users/brianray/Adam/assets/white_paper_pipeline/` if they exist
5. historical notes, manifests, prompts, and public-facing discourse surfaces as archaeology only
6. research literature / canonical secondary sources as framing only

Explicit conflict rules:
- direct repo evidence outranks drifted prompt prose
- current implementation evidence outranks historical aspiration
- audited runtime evidence outranks speculative summaries
- historical prompt/discourse artifacts can inform archaeology, but they do not prove implementation

OPERATIONAL INSTRUCTION PRECEDENCE
When operational instructions conflict, follow this order:
1. governing file resolved from current repo governance
2. explicit operator-supplied run config and attached artifacts
3. this prompt
4. current intelligence brief and current Codex pre-writing memo
5. prior drafts and archaeology artifacts

Hard rule:
- no lower-precedence artifact may force behavior that violates higher-precedence governance
- no prose artifact at any level may override current opened repo evidence for implementation-strength claims

Current implementation-truth surfaces come from:
- opened runtime code under `./eden/`, or the current equivalent runtime package/directory when the repo has been renamed or restructured
- tests under `./tests/`
- current docs truth surfaces under `./docs/`
- `./README.md`
- runtime-visible artifacts under `./logs/` and `./exports/`

Historical conceptual / archaeology context comes from:
- prior briefs in `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs/`
- prior memos in `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos/`
- prior drafts in `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/`
- legacy fallback only:
  - `./intelligence_briefs/`
  - `./whitepaper_prewriting_memo/`
  - `./whitepaper_drafts/`
- `./codex_notes_garden.md`
- patch manifests and migration notes
- `./assets/seed_canon/eden_whitepaper_v14.pdf`

Hard rule:
- pipeline artifact directories are lineage / staging / drift surfaces
- they do not outrank opened current code, tests, logs, exports, or current docs as implementation truth

Missingness rule:
- record `MISSING` or `EMPTY`
- proceed without fabrication

RESEARCH LIBRARY / CANONICAL SECONDARY DISCIPLINE
Resolve the current research library or literature cache in this order:
1. `./assets/cannonical_secondary_sources/`
2. `./assets/canonical_secondary_sources/`
3. `./assets/seed_canon/cannonical_secondary_sources/`
4. `./assets/seed_canon/canonical_secondary_sources/`

Record the resolved path or `MISSING`.

Research literature is allowed only for bounded roles:
- comparative baseline
- formalization aid
- gap exposure
- evaluation scaffold
- definition boundary / admissibility discipline

Hard rules:
- Research literature may not prove that Adam implements a mechanism.
- Repo-evidenced claims and literature-evidenced framing must remain explicitly distinguished in the paper and in the audit artifacts.
- If a theoretical reference cannot be compiled into a definition boundary, admissibility rule, or concrete evidence obligation, omit it.

Use current literature in this constrained way:
- Foucault: archaeology / archive / discontinuity discipline
- Blackmore and Dennett: replication, fidelity/fecundity/longevity framing, but not metaphor-as-proof
- Austin and Butler: governance phrases require felicity conditions and observed enforcement paths
- Barad: apparatus matters; traces, measurements, and boundary-making practices determine accountability

TRAVERSAL AND CONTEXT-CRAWL PROTOCOL
Perform exhaustive review within admissible high-signal corpus surfaces before writing implementation-strength claims.

Authority classes to log explicitly:
- `normative_doc`
- `status_doc`
- `code`
- `test`
- `runtime_log`
- `conversation_transcript`
- `export_manifest`
- `output_registry`
- `notes_archaeology`
- `prompt_archaeology`
- `literature`
- `public_discourse`

When a surface has versions or families, enumerate the ladder and read it in order:
- patch manifests
- migration notes
- prior briefs, memos, and drafts
- conversation-export families
- export run directories
- prompt variants

Maintain a traversal log with, at minimum:
- file path
- type
- version or date
- authority class
- anchors found
- key claims
- evidence hooks
- search / extraction method
- status `{opened | resolved_alias | missing | empty | skipped}`

LARGE-CORPUS BOUNDING RULE
Exhaustive inventory is required for large file families.
Exhaustive opening is required for:
- canonical high-signal surfaces
- files matched by anchor keywords
- files selected as direct evidence for claims
- failure-heavy or warning-heavy artifacts when detectable

If a family is too large to open exhaustively, use a deterministic sampling rule and record it:
- newest
- oldest
- anchor-matched
- failure-heavy / warning-heavy
- one median or representative specimen when useful

Do not label a sampled family as exhaustively opened.

PDF / binary-search fallback:
- If native search is unavailable, resolve or generate a text extraction under `./tmp/source_inventory/` or a current equivalent.
- Record the extractor used, the extracted-text path, and the reason fallback was needed.

Hard rule:
- docs, notes, logs, tests, prompts, archaeology directories, output registries, and research surfaces must remain distinct authority classes in the traversal log
- do not collapse them into a generic “sources consulted” list

PRIMARY REGISTERS (STRICT)
Use exactly one primary register internally for every non-trivial claim:
- IMPLEMENTED
- INSTRUMENTED
- CONCEPTUAL
- UNKNOWN

Allowed modifiers:
- BOUNDED_FALLBACK
- SERVER_SIDE_ONLY
- EXPLICIT_BROWSER_CONTRACT_GAP
- DEFERRED_BY_DESIGN
- HISTORICAL_REFERENCE_ONLY

PUBLIC-CLAIM RULE
When writing the public-facing whitepaper body, never upgrade beyond what the internal register allows.
- If the internal audit says `IMPLEMENTED + SERVER_SIDE_ONLY + EXPLICIT_BROWSER_CONTRACT_GAP`, the paper may not phrase the mechanism as a current browser-UI affordance.
- If the internal audit says `CONCEPTUAL` or `UNKNOWN`, the paper must phrase the mechanism as proposal, open problem, or future work.

INTERNAL AUDIT VS PUBLIC PAPER
Registers, ledgers, execution-status markers such as `SKIPPED`, `EXECUTION_BLOCKED`, `DEPENDENCY_BLOCKED`, and `WRITE_BLOCKED`, and audit taxonomies belong in audit artifacts by default.
The public whitepaper should translate these into ordinary scientific prose unless exposing the audit term is necessary for honesty or reproducibility.

DEFAULT CURRENT EXPECTATIONS TO VERIFY (NOT SELF-JUSTIFYING)
Unless contradicted by newer opened evidence, the writer should test for the following conditions and report them explicitly as:

`CONFIRMED | SUPERSEDED | NOT LOCATED | PARTIALLY TRUE`

Candidate expectations:
- no governor in v1
- no hidden planner
- no weight training, fine-tuning, or LoRA
- MLX is the active local runtime backend
- TUI is the primary runtime surface
- browser observatory functions as an observability / measurement instrument rather than the main dialogue loop
- `adam_auto` on the MLX path falls back to `runtime_auto`
- embedding-based semantic retrieval is deferred
- observatory edit / preview / revert and causal-runtime browser exposure may be partial and must be verified rather than assumed

Hard rule:
- Never treat these expectations as proof.
- They are drift-detection probes only.

BROWSER EXPOSURE DISCIPLINE
For any server-side observatory capability, determine whether it is:
- fully browser-exposed
- partially browser-exposed
- server-side only
- documented but not currently evidenced

Use the modifier:
- `EXPLICIT_BROWSER_CONTRACT_GAP`

whenever the server-side mechanism exists but current browser exposure is incomplete.

Do not bake a specific gap list into the reusable base prompt unless the current run artifacts prove it.

ADAM V1 SPINE TO VERIFY
Treat the following as default Adam v1 invariants to preserve unless superseded by stronger currently opened repo evidence.
If current repo truth materially supersedes any item below, report the supersession explicitly and rewrite the paper to match current reality.
- Adam is a local-first graph-conditioned runtime.
- Persistent identity is externalized into graph state, explicit feedback, and retrieval assembly rather than learned into model weights.
- The base model is an inference surface, not the persistence substrate.
- Memes are first-class persistent units.
- Memodes are derived second-order assemblies with an admissibility floor, not free-floating labels.
- Regard is durable selection over memes and memodes, distinct from prompt-time salience.
- Active-set assembly is a bounded retrieval and prompt-compilation process, not hidden governance.
- The membrane is an operator-visible post-generation control surface with logged effects.
- The TUI is the main runtime instrument; the observatory is a secondary measurement instrument.

ARCHAEOLOGY SURFACES
Treat the repo’s current archaeology surfaces as drift-control input:
- `./docs/PATCH_MANIFEST_V1_1.md`
- `./docs/PATCH_MANIFEST_V1_2.md`
- `./docs/MIGRATION_NOTES_V1_1.md`
- `./codex_notes_garden.md`
- prior intelligence briefs in `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs/` if present
- prior memos in `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos/` if present
- prior drafts in `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/` if present
- legacy fallback only:
  - `./intelligence_briefs/` if present
  - `./whitepaper_prewriting_memo/` if present
  - `./whitepaper_drafts/` if present
- `./exports/context/*.md` if present
- historical conceptual reference `./assets/seed_canon/eden_whitepaper_v14.pdf`

Archaeology rule:
- enumerate versions when multiple versions exist
- read in order
- record what changed
- record what stayed invariant
- record what silently vanished
- do not smooth discontinuities into a fake clean lineage

PROMPT ARCHAEOLOGY PROTOCOL
Search for prompt-archaeology surfaces in the current repo, including:
- this prompt
- `scratch_space_writing_tasks/*.md`
- pipeline briefs, memos, and prior drafts if they exist
- relevant prompt- or whitepaper-oriented notes inside `./codex_notes_garden.md`
- prompt-adjacent archaeology in patch manifests and migration notes

Use prompt-archaeology surfaces as time-series evidence when present.

Hard rules:
- feed prompt deltas into the claim map and vanished-claims ledger
- require explicit drift detection rather than intuitive “it seems different now” summaries
- if no qualifying prompt-archaeology family exists, record `PROMPT_ARCH_MISSING`

PUBLIC-FACING DISCOURSE PACKET PROTOCOL
Activate this protocol only if relevant materials actually exist, such as essays, Substack-like drafts, public explainers, dissemination notes, or other outward-facing discourse artifacts.

Use qualifying discourse materials only for:
- drift detection
- readiness signals
- overstatement detection
- memetic compression analysis

Hard rules:
- public-facing discourse is never proof of implementation
- if no qualifying discourse packet exists, record `PUBLIC_DISCOURSE_MISSING`

VANISHED CLAIMS + DEFINITIONS LEDGER
If multiple prior briefs, memos, drafts, or legacy conceptual anchors exist, you must produce a vanished ledger.

For each vanished item:
- item
- class `{claim | definition | mechanism | failure_mode | experiment | meta-theory}`
- last source/version where it appeared
- keywords searched
- authoritative corpus files searched
- matches found or `no_match`
- anchor strength `{strong | weak | none}`
- final disposition `{RESTORED | COMPRESSED | MOVED_TO_APPENDIX | LEDGER_ONLY | TOMBSTONED}`
- target location `{main_body | appendix | ledger_only | removed}`
- justification

If no relevant prior-version family exists, emit a short `NO_PRIOR_DRAFT_FAMILY` note instead of inventing archaeology.

CLAIM MAP REQUIREMENT
You must construct and preserve an internal claim map for the baseline draft and the revised draft.

For each major claim record:
- claim text
- draft location
- evidence anchor(s)
- current internal register
- modifiers if any
- whether the claim was preserved, downgraded, rephrased, removed, or newly introduced

Hard rule:
- every implementation-sounding sentence in the revised paper must be traceable through the claim map to evidence you actually opened

STATEMENT / DEFINITION LINEAGE INTEGRATION
If prior drafts, briefs, or memos contain stable definitional or statement-style formulations, do not silently discard them.

For each such recurring statement:
- determine whether it remains admissible under current evidence
- preserve its denotation if still valid
- downgrade it if evidence weakened
- tombstone it if it no longer survives current repo truth

Do not let definitions drift merely because the rhetorical surface changed.

STATEMENT-LOG / APPENDIX INTEGRATION
Extract statement-form utterances from prior drafts, appendices, notes, and statement-like source surfaces when they exist. Current Adam candidates include:
- prior draft families
- appendix-like audit artifacts
- statement-heavy notes in `./codex_notes_garden.md`
- constitutional or statement-like surfaces in current docs and runtime code

Classify each extracted statement as:
- `definition`
- `mechanism`
- `failure_mode`
- `experiment`
- `meta-theory`

Hard rules:
- integrate non-meta-theory substance into the paper body where admissible
- preserve the full statement archive as an appendix or audit artifact
- verify that no important statement disappears silently during condensation

ANCHOR VERIFICATION PROTOCOL (MANDATORY BEFORE REMOVING PRIOR-VERSION CONTENT)
When content appears in a prior draft family but not in the baseline draft you are revising, you must verify before deleting, compressing, or silently omitting it.

Step 1: extract anchor keywords
- choose 3–5 substantive terms that characterize the missing concept
- prefer technical nouns, canonical primitives, symbols, tests, or mechanism names

Step 2: search authoritative corpus files in order
Search these surfaces systematically:
1. `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs/` and fallback `./intelligence_briefs/`
2. `./docs/`
3. `./tests/`
4. `./exports/context/`
5. `./logs/runtime.jsonl`
6. `./exports/conversations/**/*.md`
7. `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos/` and fallback `./whitepaper_prewriting_memo/`
8. `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/` and fallback `./whitepaper_drafts/`
9. current runtime code under `./eden/` or the current equivalent runtime package/directory
10. relevant scripts under `./scripts/`

Step 3: tag anchor strength
- `strong_anchor`: explicit implementation or direct evidence path exists
- `weak_anchor`: conceptual or partial reference exists without current execution proof
- `no_anchor`: no meaningful evidence located

Step 4: disposition
- `strong_anchor` → RESTORE or preserve, with the correct register
- `weak_anchor` → COMPRESS or downgrade, with explicit wording change
- `no_anchor` → TOMBSTONE in the vanished ledger with search record

Step 5: record the search
For every evaluated section or concept, record:
- section id or concept label
- keywords searched
- files searched
- matches found
- anchor strength
- disposition
- justification

Hard rule:
- do not remove content just because it disappeared from a later draft
- that is precisely the drift event you are supposed to audit

EVIDENCE TYPES TAXONOMY
Use this taxonomy to keep the paper honest.

1. EMPIRICAL CLAIMS
Assertions about runtime behavior, outputs, or observable system properties.
They require:
- code path
- and/or direct test
- and/or runtime log / transcript / export evidence
- and locator-quality citation

2. DEFINITIONAL OPERATORS
Terms that establish distinctions or interfaces.
They require:
- a crisp definition
- operational correspondence
- measurement or falsification boundary
- optional current evidence showing the distinction matters in practice

3. CONSTITUTIONAL INVARIANTS
Non-negotiable system constraints.
They require:
- explicit statement in current docs or tests
- and preferably evidence that violating them matters or is checked

4. ARCHITECTURAL PROPOSALS
Planned or partially sketched mechanisms.
They must be labeled as:
- proposed
- open problem
- future work
- or bounded closure item

Hard rule:
Ask, for every claim:
- what file would I open?
- what test would I run?
- what trace would prove it?
If you cannot answer concretely, the claim is not implementation-strength.

EVIDENCE SUBSTRATE FOR OBSERVED RESULTS
Do not assume `CURRENT_ADAM_LOG.md` exists.

Resolve operational evidence from the current repo in this order:
1. operator-supplied or attached current run log if present
2. `./logs/runtime.jsonl` as the canonical current runtime log if it exists
3. `./exports/conversations/**/*.md`
4. selected `./exports/<experiment_id>/*.json`, manifests, and HTML artifacts
5. tests that directly exercise runtime behavior

If no usable runtime evidence surface exists:
- record `RUN_LOG_MISSING`
- do not fabricate observed results
- proceed with a clearly bounded protocol/future-work section plus synthetic pipeline checks

RUNTIME LOGS / TRANSCRIPTS AS FIRST-CLASS EVIDENCE
Runtime logs, conversation transcripts, export manifests, and direct runtime tests are not optional ornamentation. They are the highest-frequency behavioral evidence stream available inside the repo.

Operationally:
- mine them exhaustively within admissible current surfaces
- prefer failures and edge cases as much as success cases
- do not cherry-pick only the flattering examples
- every observed-result claim must be reproducibly locatable

When evidence supports it, the paper must include an explicit “Observed Operational Evidence” layer rather than hiding behind future-work language.

RUNTIME LOGS / TRANSCRIPTS AS EXPERIMENTAL RECORD
A substantial portion of Adam’s empirical program may appear as executed conversational or runtime episodes rather than formal benchmark harnesses.

Therefore:
- treat explicit tests, probes, constrained prompts, retries, parameter changes, and comparison runs as candidate experiment episodes
- treat repeated prompts under changed constraints as incidental experiments when the outcome is measurable
- report completed episodes as DONE when the evidence genuinely supports that status
- do not claim generalization beyond the observed evidence span

Minimum expectation when evidence supports completed episodes:
- extract and report at least three distinct observed `DONE` experiment episodes
- if the evidence truly does not support three completed observed episodes, classify the run `PARTIAL`, document the shortage honestly, and explain what evidence was missing
- do not let genuinely completed observed episodes drift into vague future-work language

For each observed episode include:
- episode_id
- hypothesis (explicit or carefully inferred)
- manipulation
- measured observable
- outcome
- confounds
- locator-quality evidence citation

Hard rule:
- synthetic, proposed, or planned episodes must remain in separate registries or clearly separate subsections
- only completed observed episodes may be labeled `DONE`

SYNTHETIC DATA MANDATE
Synthetic data is required whenever it materially strengthens the measurement pipeline or keeps the figure / metric workflow runnable despite incomplete observed evidence.

Synthetic here means:
- deterministic
- explicitly labeled
- tied to a generator path and seed
- never represented as actual Adam runtime performance

At minimum:
- observed figures/tables and synthetic figures/tables must be kept visibly distinct
- captions must carry provenance
- synthetic artifacts should mirror the schema of the real pipeline whenever possible so the pipeline can be swapped from synthetic to observed data without conceptual rewrite

RUNTIME EVIDENCE MINING PROTOCOL
When usable runtime evidence exists, treat it as first-class empirical substrate.

For every cited runtime event or turn, extract as many of the following as the evidence supports:
- file path
- run identifier and/or session identifier
- timestamp anchor
- turn span and/or event span
- prompt text, prompt excerpt, or prompt hash
- retrieval or active-set indicators
- tool/action indicators
- model / profile / budget fields
- timing or latency fields
- membrane, feedback, and response fields
- observed errors, fallbacks, refusals, retries, or guard activations
- line ranges, excerpt hashes, or equivalent reproducible locators
- evidence-quality / locator-confidence assessment

Do not cite runtime evidence without a concrete locator.

You must also try to extract experiment episodes where the evidence supports them.

An experiment episode minimally requires:
- a manipulation or constrained condition
- a measurable or inspectable outcome
- a bounded evidence span
- enough locator quality to support reproducible citation

For each extracted episode, record:
- `episode_id`
- `status` where observed completed episodes use `DONE`
- inferred or explicit hypothesis
- manipulation
- measured observable
- outcome
- confounds
- evidence locator(s)

If runtime evidence exists and supports completed observed episodes, the paper must report them as observed `DONE` episodes rather than pretending everything remains future work.

EMPIRICAL PROGRAM
The empirical section must separate three layers whenever evidence allows:

1. Protocol
   - what the experiment is meant to test
   - manipulation
   - measured outputs
   - metrics
   - pass/fail criteria

2. Observed repo-grounded evidence
   - what already happened in current logs, transcripts, exports, or tests
   - cited with reproducible locators

3. Synthetic demonstrator
   - deterministic, labeled synthetic data that validates the metric pipeline
   - never presented as real system performance

SYNTHETIC DATA DISCIPLINE
Synthetic artifacts are allowed and often necessary, but they may only do three things:
- validate the measurement pipeline
- stress-test metrics or visualizations
- demonstrate the shape of a future harness

Synthetic artifacts may not be written as observed repo performance.

Every synthetic figure or table must include:
- provenance tag `SYNTHETIC`
- seed
- generator path
- dataset path under the run output root

MEMETICS + SPEECH-ACT DISCIPLINE
When the paper uses words like persistence, selection pressure, imitation, memode survival, governance, commitment, or directive force, cash them out.

At minimum specify:
- object representation
- update rule or current absence thereof
- what selects
- where the audit trail lives
- fidelity proxy where available
- fecundity proxy where available
- longevity proxy where available

When interpreting governance utterances, constitutional commitments, or operator directives, also specify:
- utterance source
- felicity conditions
- enforcement path
- persistence surface
- observed compliance, violation, or absence evidence

Hard rules:
- do not let memetic or speech-act language float as decorative theory gloss
- if the repo cannot support a strong causal claim or proxy, downgrade the language accordingly and record the missing evidence

ARCHAEOLOGY DISCIPLINE
At least one analysis must treat the repo’s own document field as data when the corpus supports it.

Examples:
- patch-level claim drift
- definition survival or vanishing across docs, briefs, memos, and drafts
- browser contract drift between server implementation and UI exposure

This is not decorative meta-writing. It is drift-control instrumentation.

COMPARATIVE CLAIMS — OPT-IN ONLY
- Do not generate a GraphRAG or “not just X” posture by default.
- Comparative claims are allowed only if explicitly enabled by the operator or required by a current attached source.
- If enabled, define the comparator class first and compare only implemented or instrumented mechanisms.

CITATION DISCIPLINE
- Public bibliography entries must resolve cleanly. No missing keys. No placeholder citations.
- Canonical secondary sources may be cited as normal public references when used for definition or method discipline.
- Local repo artifacts used as evidence (logs, transcripts, exports, manifests, internal briefs, memos) should normally be cited in footnotes or appendix-local evidence notes rather than laundered into the public bibliography.
- Every local evidence citation must include enough locator detail to be reproduced: file path, run/session identifier when available, and line range, turn range, event span, or short excerpt hash.
- If no stable locator can be produced, downgrade the claim rather than pretending the citation is reproducible.

WORD COUNT FLOOR
Target main-body length: 5,500–7,000 words
Absolute floor: 5,000 words

Hard rule:
- the floor applies to the main body, excluding bibliography and audit artifacts
- appendices may extend the work, but they may not substitute for missing main-body argument load
- a run under 5,000 main-body words cannot receive `PASS`

ELABORATION LAYER REQUIREMENT
For each canonical term that bears load in the paper, include:
1. one-sentence crisp definition
2. controlled elaboration
3. operational correspondence
4. positive example + near-miss
5. failure mode or adversarial boundary case

For major load-bearing concepts, controlled elaboration normally means 2 to 3 paragraphs rather than a drive-by mention.

Canonical terms for Adam v1 normally include:
- Adam
- operator identity, and Brian specifically only when materially relevant to current evidence or framing
- local-first graph-conditioned runtime
- persistent graph
- session / turn / document
- meme
- memode
- regard
- active set
- membrane
- feedback event
- trace event
- membrane event
- measurement event
- observatory
- semantic map / assemblies / runtime / active set planes
- inference profile
- budget mode
- local-first
- browser contract gap
- constitutional seed
- hum when it is materially discussed

Compression check:
- verify that condensation did not silently remove operational correspondence
- verify that concrete examples remain
- verify that failure modes remain explicit

LAYOUT REQUIREMENT
- Produce a two-column paper body.
- Keep top matter (title / author / date / abstract) in a one-column block.
- Verify the compiled PDF actually matches this layout.
- Do not assume the template worked because the source says `twocolumn`.
- Record the layout verification method and outcome in the audit artifact.
- If the PDF build is part of the run and layout cannot be verified, the run cannot receive `PASS`.

FIGURE BUNDLE CONTRACT
Produce a figure bundle under:
- `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/<THIS_RUN_VERSION>/figure_bundle/`

Required structure:
- `registry/FIGURE_REGISTRY.json`
- `data/`
- `static/`
- `interactive/`
- `latex/figures_generated.tex`

Minimums for this Adam v1 run:
- at least 6 OBSERVED figures or tables from real repo artifacts (logs, conversation transcripts, exports, tests, manifests)
- at least 6 SYNTHETIC figures or tables from deterministic generators
- at least 1 archaeology / drift figure when archaeology surfaces exist
- at least 1 memetic visualization when memetic evidence exists

Every figure included in the paper must have:
- provenance tag `[OBSERVED | SYNTHETIC | PROPOSED]`
- artifact pointer under `figure_bundle/`
- source hash / seed / locator details as appropriate
- reproduction notes
- explicit failure reason when a static or interactive export fails

If evidence is missing, classify the run as `PARTIAL` and emit labeled placeholders instead of pretending the figures exist.

FIGURE REGISTRY
`FIGURE_REGISTRY.json` must include, for each figure:
- `figure_id`
- `title`
- `provenance`
- `inputs`
- `outputs`
- `caption_tex`
- `latex`
- `build`
- `provenance_locator`
- `reproduction_notes`
- `export_status`
- `failure_reason`
- `paper.include`
- `paper.section`
- `paper.order`

LaTeX integration must happen through:
- `figure_bundle/latex/figures_generated.tex`

Do not hand-write ad hoc figure blocks if the figure is in the registry.

FIGURE REGISTRY SEMANTICS
The registry is allowed to contain more figures than the paper finally includes.

Hard rules:
- only figures with `paper.include=true` are emitted into `figures_generated.tex`
- included figures must have section placement and order fields
- missing static assets require explicit placeholder handling, never silent omission
- partial figure generation must be recorded as `PARTIAL` with failure reason and reproduction hint in the audit artifact
- if interactive or static exports fail, record the exact attempted artifact path, failure reason, and fallback behavior

FIGURE BUNDLE ACCEPTANCE TEST
A run is not fully successful unless:
- the figure bundle directory exists
- `FIGURE_REGISTRY.json` is valid and non-empty
- every in-paper figure has provenance and locator details
- observed and synthetic figures are visibly separated in captions and audit records
- archaeology/drift visualization appears when archaeology evidence exists
- at least one memetic visualization exists when memetic evidence is used in the paper
- the observed/synthetic target counts are met or the run is honestly marked `PARTIAL` with placeholder-backed justification

RUN OUTCOME STATES
Classify the run at the end as one of:
- `PASS` = all required outputs exist and hard evidence / build tests pass
- `PARTIAL` = the run is structurally complete but one or more evidence surfaces are missing, incomplete, or placeholder-backed
- `FAIL` = the run breaks core protocol (fabricated evidence, broken build without honest record, missing required output families, or silent omission of required audit artifacts)

Unresolved governance cannot receive `PASS` or `PARTIAL`; it is a fail-closed `FAIL` with degraded-mode limited audit outputs.

WHITEPAPER INPUT SURFACES TO READ
At minimum consider these:
- `./AGENTS.md`
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
- `./docs/PATCH_MANIFEST_V1_1.md`
- `./docs/PATCH_MANIFEST_V1_2.md`
- `./docs/MIGRATION_NOTES_V1_1.md`
- `./logs/runtime.jsonl`
- `./exports/conversations/**/*.md`
- selected `./exports/<experiment_id>/*.json`, manifests, and HTML artifacts
- current prompt / prompt-adjacent archaeology surfaces under `./scratch_space_writing_tasks/`
- resolved research-library path if present
- `./tmp/source_inventory/*.txt` when PDF text extraction fallbacks exist
- current runtime code that carries statement-form invariants, especially `./eden/runtime.py` or the current equivalent runtime entry module
- current runtime code under `./eden/` or the current equivalent runtime package/directory
- relevant tests under `./tests/`
- latest intelligence brief from `/Users/brianray/Adam/assets/white_paper_pipeline/intel_briefs/` if present
- latest Codex memo from `/Users/brianray/Adam/assets/white_paper_pipeline/writing_memos/` if present
- legacy fallback only:
  - latest intelligence brief under `./intelligence_briefs/` if present
  - latest Codex memo under `./whitepaper_prewriting_memo/` if present

PROBES AND EXECUTION PROOF
Prefer current repo-defined tests, scripts, Make targets, task runners, or documented entrypoints when they supersede historical candidates.

Treat commands such as `.venv/bin/python -m eden` and `.venv/bin/python app.py` as candidate historical entrypoints only if they are still present and current.

Record any supersession explicitly.

Prefer existing tests and scripts when generating probes:
- `.venv/bin/pytest -q tests/test_tui_smoke.py`
- `.venv/bin/pytest -q tests/test_runtime_e2e.py`
- `.venv/bin/pytest -q tests/test_regard.py`
- `.venv/bin/pytest -q tests/test_geometry.py`
- `.venv/bin/pytest -q tests/test_observatory_server.py`
- `.venv/bin/pytest -q tests/test_observatory_measurements.py`
- `.venv/bin/pytest -q tests/test_tanakh_tools.py`
- `.venv/bin/python scripts/check_observatory_build_meta.py`
- `.venv/bin/python scripts/run_tanakh_render_validation.py`
- `.venv/bin/python -m eden`
- `.venv/bin/python app.py`

Do not claim a mechanism is implemented merely because a doc names it. Use code + test/log/export proof.

PHASES
PHASE 0 — governance, run config, and mandatory run notes
- resolve governance
- resolve the canonical notes surface when governance is resolved
- write PRE note, or record `SKIPPED` / `WRITE_BLOCKED` as appropriate
- resolve `RUN_CONFIG`

Hard gate:
- If governance remains unresolved at the end of Phase 0, stop the run.
- Emit only the degraded-mode outputs allowed by the governance section.
- Do not proceed to Phases 1–8.

PHASE 1 — inventory, traversal, and baseline resolution
- resolve repo root, pipeline root, baseline draft, and current input surfaces
- execute the traversal protocol and write the traversal log
- record missingness honestly

PHASE 2 — archaeology, prompt archaeology, and claim map
- enumerate prior artifact lineage
- resolve prompt-archaeology surfaces or record `PROMPT_ARCH_MISSING`
- resolve public-discourse packet or record `PUBLIC_DISCOURSE_MISSING`
- build a claim map for the baseline
- identify vanished or drifted content

PHASE 3 — empirical program and evidence extraction
- mine runtime evidence
- extract observed episodes where justified
- separate observed from synthetic

PHASE 4 — figure / data generation
- generate figure bundle assets and registries
- produce placeholders honestly when evidence is insufficient

PHASE 5 — rewrite / refactor
- revise the whitepaper under register discipline
- preserve warranted continuity
- downgrade overclaims aggressively

PHASE 6 — citation + bibliography integrity
- verify every citation
- verify locator quality for local evidence
- remove or downgrade weakly anchored claims

PHASE 7 — LaTeX build and verification
- verify layout
- verify figure inclusion
- verify bibliography and cross-reference integrity

PHASE 8 — audit artifact and canonization copy
- write audit artifacts
- copy the canonical PDF and provenance manifest
- write POST note or `WRITE_BLOCKED`
- record write proof

AUDIT ARTIFACTS
Write under `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/<THIS_RUN_VERSION>/audit/`:
The standard audit list below applies only when governance is resolved and the run proceeds beyond degraded mode.
In governance-unresolved degraded mode, require only:
- governance resolution log
- short degraded-mode report
- execution/build status log

- governance resolution log
- run-config audit
- traversal log
- prompt-archaeology report or `PROMPT_ARCH_MISSING`
- public-discourse audit or `PUBLIC_DISCOURSE_MISSING`
- statement archive / appendix register
- claim map
- vanished claims + definitions ledger (or `NO_PRIOR_DRAFT_FAMILY` note)
- evidence registry for observed claims
- figure provenance registry
- experiment episode registry, including honest shortage notes when three observed `DONE` episodes are not supportable
- pdf build status report
- execution/build status log
- change log: what changed and why
- build log, layout verification, and write proof
- prompt-assumption self-check
- `WRITE_BLOCKED` report if any required write failed

REQUIRED OUTPUTS
The five-family output contract below applies only when governance is resolved and drafting proceeds.
In governance-unresolved degraded mode, only the allowed degraded-mode audit artifacts are required.

Under `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/<THIS_RUN_VERSION>/` write:
1. `latex/` updated LaTeX project
2. `pdf/` containing the compiled PDF when produced, or an explicit build-status note when PDF generation was skipped or blocked
3. `figure_bundle/` registry + assets
4. `audit/` internal audit artifacts
5. `data/` extracted datasets used for figures/tables

ACCEPTANCE TESTS
`PASS` requires every applicable test below to pass.
Any placeholder-backed or missing required surface forces `PARTIAL`.
Any fabrication, unresolved governance state, drafting attempted under unresolved governance, or silent omission forces `FAIL`.

A successful run must satisfy:
- main body word count `>= 5,000`
- complete claim map
- complete vanished-claims / definitions ledger, or honest `NO_PRIOR_DRAFT_FAMILY`
- evidence registry present
- experiment episode registry present
- observed vs synthetic separation preserved
- required in-paper observed and synthetic artifacts present, or honest `PARTIAL` placeholders with reasons
- runtime/log citation integrity
- figure registry integrity
- explicit handling of browser contract gaps where relevant
- statement archive / appendix integration present when source statements exist
- two-column body / one-column top matter verified in the PDF when PDF build is part of the run
- prompt assumptions that were superseded are explicitly reported rather than silently retained
- no missing citations or broken bibliography keys
- no public overclaims past current Adam v1 evidence
- no silent omissions
- if `PDF_BUILD_REQUIRED=true`, absence of a verified compiled PDF prevents `PASS`
- if PDF build is intentionally skipped by configuration, an explicit PDF build-status note is required and non-PDF parts of the run may still be evaluated normally

REPO-DRIFT SELF-CHECK (MANDATORY)
Before finalizing the run, explicitly report:
- assumptions in this prompt that were confirmed
- assumptions in this prompt that were superseded
- assumptions in this prompt that could not be evaluated
- any current repo surfaces that materially replace the prompt’s older expectations

If a prompt assumption is superseded by stronger current evidence, follow the repo evidence, not the prompt’s historical wording.

BEGIN NOW
- Do not ask permission.
- Do not assume old Eden beta directories exist.
- Do not let missing upstream artifacts override current repo truth.
- Do not treat historical wording as current proof.
- Produce an Adam v1 whitepaper that isomorphically reflects the repo that currently exists.
