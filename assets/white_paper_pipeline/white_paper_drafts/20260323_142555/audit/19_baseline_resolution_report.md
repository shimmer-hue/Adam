
# Baseline Resolution Report

Candidate scan root: `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts`

Candidate list:
- `eden_whitepaper_v14.pdf` -> parsed version `14` -> `sha256:0ac4ed914143db71d9035d92f9091327800e8380988fd9bc0fc3b445d1129107`

Selected numbered baseline:
- path: `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/eden_whitepaper_v14.pdf`
- parsed version: `14`
- status: `BASELINE_EXPECTATION_MATCHED`
- override status: `false`
- `CURRENT_BASELINE_VERSION = 14`
- `NEXT_DRAFT_NUMBER = 15`
- `NEXT_DRAFT_BASENAME = eden_whitepaper_v15.pdf`

Support-manuscript resolution:
- path: `/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/20260320_111343/pdf/adam_whitepaper_20260320_111343.pdf`
- hash: `sha256:0c5659e33917a8526f96591cb8cde105efde09f10219dd383fbd5e857dcd2e54`
- role: preservation-target input only

Correction override status:
- root-level `eden_whitepaper_v15.pdf` was not present before this run
- `FAILED_NUMBERED_DRAFT_DEMOTED` not triggered because no higher-numbered root-level candidate existed to demote
- notes-only claims of prior `v15` canonization were treated as archaeology drift, not as canonical baseline supersession
