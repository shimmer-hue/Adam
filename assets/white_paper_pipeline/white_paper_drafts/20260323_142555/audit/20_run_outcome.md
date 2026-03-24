
# Run Outcome

Classification: `PARTIAL`

Reason:
- structural run requirements were met: governance resolved, direct-source consultation recorded, figure bundle generated, audit family written, PDF built and layout-verified, next numbered draft canonized
- repo-wide proof is not fully green: `./.venv/bin/pytest -q` returned `1 failed, 118 passed, 1 warning`
- the hard failure remains `tests/test_ingest.py::test_pages_pdf_fixture_extracts_readable_text` because `/Users/brianray/Adam/assets/cannonical_secondary_sources/bad_trip_with_jesus_theory_memoir.pdf` is missing
- the soft warning remains the un-awaited `ConversationAtlasModal._load_preview_worker` coroutine in `tests/test_tui_smoke.py`

Acceptance-test summary:
- main-body word count >= 5000: PASS (`8337+61+894 (14/0/5/0) File: /Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/20260323_142555/latex/main.tex`)
- complete claim map: PASS
- complete theoretical restoration map: PASS
- direct-source consultation log present: PASS
- vanished-claims ledger present: PASS
- evidence registry present: PASS
- experiment episode registry present with three observed `DONE` episodes: PASS
- observed vs synthetic separation preserved: PASS
- required figure counts met: PASS (`8` observed / `7` synthetic)
- archaeology/drift figure present: PASS
- memetic visualization present: PASS
- runtime/log citation integrity present: PASS
- two-column body / one-column top matter verified in the PDF: PASS
- prompt-assumption drift explicitly reported: PASS
- repo-wide full proof green: FAIL

Theoretical-apparatus acceptance test:
- direct consultation of Foucault and Austin recorded: PASS
- main body contains substantive Foucault use: PASS
- main body contains substantive Austin use: PASS
- methodological constraint surface preserved as a main-body section: PASS
- every narrowing or removal logged in the restoration map / vanished ledger: PASS
