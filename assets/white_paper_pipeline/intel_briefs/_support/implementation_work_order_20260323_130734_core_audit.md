# Adam Implementation Work Order

Generated from `adam_intelligence_20260323_130734_core_audit.md`

## Priority 1 — Restore Green Python Proof

Task: resolve the failing ingest fixture dependency.

- Evidence: `./.venv/bin/pytest -q -x` fails at `tests/test_ingest.py::test_pages_pdf_fixture_extracts_readable_text`
- Cause: missing file `/Users/brianray/Adam/assets/cannonical_secondary_sources/bad_trip_with_jesus_theory_memoir.pdf`
- Shortest closure:
  - restore that file if it is still canonical, or
  - replace the hard dependency with an explicit optional-fixture guard and mark the test accordingly
- Proof command: `./.venv/bin/pytest -q`

## Priority 2 — Close Naming Drift

Task: decide whether Adam-first public naming should be completed in the browser shell.

- Evidence: `web/observatory/src/App.tsx` still renders `EDEN Observatory`
- Shortest closure:
  - rename visible browser title to `Adam Observatory`
  - preserve `eden/` package path and historical shell/runtime note in docs
- Proof commands:
  - `rg -n "EDEN Observatory" web/observatory/src/App.tsx`
  - `npm --prefix web/observatory test`

## Priority 3 — Clarify Measurement Scope

Task: make session-scoped versus experiment-scoped measurement counts explicit.

- Evidence:
  - `exports/bb298723-5fbf-4554-bf6b-ec5f4d336fbd/measurement_events.json` exports an empty `events` list
  - the matching `geometry_diagnostics.json` embeds two historical measurement events
- Shortest closure:
  - label every measurement export and browser badge with its scope
  - add an experiment-history count beside the current-session count
- Proof commands:
  - `./.venv/bin/pytest -q tests/test_observatory_measurements.py tests/test_observatory_server.py`
  - inspect both export files after a known commit/revert run

## Priority 4 — Preserve the Right Whitepaper Inputs

Task: advance the next numbered draft without importing baseline ontology drift.

- Preserve from support manuscript:
  - Adam-first framing
  - direct-loop empiricism
  - graph-legibility surfaces
- Restore from baseline where still admissible:
  - Foucault archive discipline
  - Austin felicity/governance discipline
- Do not re-import:
  - knowledge memodes
  - governor-object framing
  - memode-as-primary-persistence claims

## Priority 5 — Decide the Browser Causality Boundary

Task: either keep browser causality read-only and say so harder, or expose more server-side causal views intentionally.

- Evidence: browser preview/commit/revert is live, but trace copy still says causality is read-only
- Shortest closure:
  - if read-only is intentional, freeze that contract in docs and UI copy
  - if more causal drilldown is wanted, expose it as a distinct bounded read surface rather than as hidden mutability
- Proof commands:
  - `./.venv/bin/pytest -q tests/test_observatory_server.py`
  - `npm --prefix web/observatory test`
