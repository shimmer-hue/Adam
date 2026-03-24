
# Execution and Build Status Log

| Status | Action | Command / method | Result | Affected output family | Downstream consequence |
| --- | --- | --- | --- | --- | --- |
| `EXECUTED` | governance resolution | repo-root AGENTS scan | governance resolved from `/Users/brianray/Adam/AGENTS.md` | gating | drafting allowed |
| `EXECUTED` | PRE note append | notes write before drafting | appended PRE-FLIGHT entry to `/Users/brianray/Adam/codex_notes_garden.md` | notes surface | run compliant with note discipline |
| `EXECUTED` | baseline/support resolution | numbered scan + support-manuscript scan | baseline `v14`, support March 20 Adam-first PDF | lineage control | numbered baseline preserved |
| `EXECUTED` | direct-source consultation | `pdfinfo`, `pdftotext`, `.venv` `pypdf` per-page extracts | Foucault/Austin/Butler/Barad/Blackmore/Dennett/Zhang opened and range-extracted | theoretical apparatus | restoration map grounded in direct consultation |
| `EXECUTED` | targeted runtime proof | `./.venv/bin/pytest -q tests/test_runtime_e2e.py` | `14 passed` | empirical evidence | DONE episode E1 refreshed |
| `EXECUTED` | targeted observatory proof | `./.venv/bin/pytest -q tests/test_observatory_measurements.py` | `12 passed` | empirical evidence | DONE episode E2 refreshed |
| `EXECUTED` | targeted hum proof | `./.venv/bin/pytest -q tests/test_hum_runtime.py` | `4 passed` | empirical evidence | DONE episode E3 refreshed |
| `EXECUTED` | targeted geometry proof | `./.venv/bin/pytest -q tests/test_geometry.py` | `6 passed` | geometry evidence | geometry claims refreshed |
| `EXECUTED` | targeted observatory server proof | `./.venv/bin/pytest -q tests/test_observatory_server.py` | `7 passed` | browser/server evidence | live API still tested |
| `EXECUTED` | regard proof | `./.venv/bin/pytest -q tests/test_regard.py` | `2 passed` | selection evidence | regard claims refreshed |
| `EXECUTED` | TUI smoke proof | `./.venv/bin/pytest -q tests/test_tui_smoke.py` | `25 passed, 1 warning` | TUI evidence | runtime warning captured for closure |
| `EXECUTED` | observatory build freshness check | `./.venv/bin/python scripts/check_observatory_build_meta.py` | `ok: true` | frontend freshness evidence | checked-in bundle matches source hash |
| `SKIPPED` | fresh Playwright browser rerun | none | relied on checked-in `OBSERVATORY_E2E_AUDIT.md` plus refreshed server-side tests | browser E2E proof | browser evidence remains bounded to checked-in audit + current server tests |
| `EXECUTED` | repo-wide regression capture | `./.venv/bin/pytest -q` | `1 failed, 118 passed, 1 warning` | global proof boundary | run classified `PARTIAL` rather than `PASS` |
| `EXECUTED` | figure/data generation | `./.venv/bin/python /Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/20260323_142555/data/generate_figure_bundle.py` | figure bundle and registry written | figure bundle / data | observed and synthetic targets met |
| `EXECUTED` | LaTeX build | `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex` | `main.pdf` built successfully | PDF / latex | build family complete |
| `EXECUTED` | layout verification renders | `pdftoppm -png -f 1,2,13 -singlefile ...` | `page-01.png`, `page-02.png`, `page-13.png` generated | PDF verification | one-column top matter, two-column body, and figure inclusion visually checked |
| `EXECUTED` | audit artifact write | generated markdown/json audit family | all required non-degraded audit files written | audit | audit family complete |
| `EXECUTED` | canonization copy | filesystem copy + provenance manifest | wrote `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/eden_whitepaper_v15.pdf` and `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/eden_whitepaper_v15.json` | canonical numbered draft | next numbered draft canonized despite overall `PARTIAL` run outcome |
