# Whitepaper Prompt Changelog

## Restored / strengthened
- Added fail-closed governance resolution with attempted-path logging, alias rejection rules, and a degraded-mode boundary that forbids drafting without established governance.
- Made PRE / POST run-note writing mandatory, with `WRITE_BLOCKED` fallback requirements instead of optional continuity notes.
- Added deterministic `RUN_CONFIG` auditing for `BASELINE_DRAFT_PATH`, `WHY_NOW`, `AUDIENCE`, `RED_LINES`, comparator state, PDF-build state, and safe continuation defaults.
- Added an explicit authority stack plus a traversal / context-crawl protocol with authority classes, version-family enumeration, and PDF-to-text fallback logging.
- Rebased research-library resolution onto the current Adam repo’s actual literature cache at `assets/cannonical_secondary_sources/`, while preserving bounded literature roles and the “literature is not implementation proof” rule.
- Added dedicated prompt-archaeology, public-discourse, statement-log, runtime-extraction, and experiment-episode protocols with explicit `PROMPT_ARCH_MISSING`, `PUBLIC_DISCOURSE_MISSING`, and `PARTIAL` behaviors.
- Hardened memetics and speech-act analysis with fidelity / fecundity / longevity proxies, felicity-condition requirements, and anti-gloss constraints.
- Raised the main-body floor back to 5,000 words, restored 2-3 paragraph elaboration expectations for load-bearing concepts, and added a compression-loss check.
- Raised figure expectations to 6 observed and 6 synthetic artifacts, strengthened registry fields, required failure reasons / reproduction notes, and tightened PASS / PARTIAL / FAIL acceptance tests.

## Preserved from current Adam version
- Kept Adam-centered naming discipline and the rule that legacy `EDEN` strings are historical anchors rather than default public naming.
- Kept repo-root resolution and the canonical white-paper pipeline root under `assets/white_paper_pipeline/`.
- Kept the current claim-register system: `IMPLEMENTED`, `INSTRUMENTED`, `CONCEPTUAL`, `UNKNOWN`, plus useful modifiers such as `EXPLICIT_BROWSER_CONTRACT_GAP`.
- Kept the public-claim rule, browser-contract-gap discipline, default-current-expectations-to-verify logic, and repo-drift self-check.
- Kept the non-negotiable Adam spine around local-first runtime, graph-conditioned persistence, memes/memodes, regard, active-set assembly, membrane, TUI primacy, and observatory secondary status.
- Kept the baseline-draft resolution strategy, canonization targets, and audit-oriented output structure rather than replacing them with older root-level draft assumptions.

## Intentionally not restored
- Did not restore `AGENTS_CODEX-WRITER.md` as a governing default because the current repo uses `/Users/brianray/Adam/AGENTS.md` as the live canonical governance surface.
- Did not restore `assets/seed_canon/...secondary_sources` as the primary literature-cache path because the current repo’s actual research library lives at `/Users/brianray/Adam/assets/cannonical_secondary_sources/`.
- Did not restore a single-log-file assumption because current runtime evidence is spread across `logs/runtime.jsonl`, `exports/conversations/`, and `exports/<experiment_id>/...` artifacts.
- Did not restore any Claude-specific memo step or memo machinery because the current prompt and repo workflow are explicitly Codex-centered.
- Did not restore Eden-only absolute-path loyalties or root-level whitepaper output directories because the Adam repo now uses the `assets/white_paper_pipeline/` structure as the canonical pipeline root.
