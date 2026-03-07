# Implementation Truth Table

| Capability | Status | Notes / evidence |
| --- | --- | --- |
| Blank Eden bootstrap | Implemented | runtime + TUI path; validated in tests and demo |
| Seeded Eden bootstrap code path | Implemented | ingests `assets/seed_canon/`; heavy-path validation started on real canon files |
| Fixed-pane amber TUI | Implemented | preserved and refocused around a cockpit-style primary chat surface |
| Panel-based launcher for startup and runtime surfaces | Implemented | startup cockpit keeps the top action menu, Qwen thinking preview, runtime trace, and preview chat on one screen |
| `python -m eden` default entry path | Implemented | no subcommand required for the normal TUI path; flags remain optional overrides |
| Repo-root `python3 app.py` launcher | Implemented | root launcher re-execs the repo-local `.venv` interpreter and then dispatches into `eden.app:main` |
| Local repo-managed MLX model storage | Implemented | default MLX model target is `models/qwen3.5-35b-a3b-mlx-mxfp4` under repo root |
| Local MLX shard-readiness tracking | Implemented | startup/runtime distinguish metadata-only, partial, and ready model states |
| Repo-local Qwen 3.5 MLX backend | Implemented | repo-local 4-shard model completed and real MLX generation succeeded |
| Multiline composer | Implemented | `TextArea`-based; covered by TUI smoke test |
| Cockpit chat layout | Implemented | aperture / controls on the left, animated cockpit + trace upper-right, chat deck lower-right |
| Fixed local-MLX launcher | Implemented | startup TUI no longer exposes backend selection; local MLX is the launcher contract |
| Deck + Review secondary surfaces | Implemented | detailed budget / thinking / history remain in `Deck`; explicit feedback remains in `Review` |
| Dedicated model thinking panel | Implemented | MLX/Qwen reasoning is kept on and surfaced separately from the final answer via Deck |
| Operator-label turn persistence | Implemented | saved turns and graph-ingested operator text are punctuated as `Brian the operator: ...` |
| Session-start inference profile flow | Implemented | startup/new-session modal |
| Manual inference mode | Implemented | persisted in session metadata and surfaced per turn |
| Runtime auto inference mode | Implemented | deterministic bounded heuristics; tested |
| Adam auto inference mode | Implemented with bounded fallback | mock path chooses bounded presets; MLX path falls back to `runtime_auto` and logs it |
| Live budget / allowance panel | Implemented | updates from preview/chat state and persists per turn |
| Per-turn inference circumstance persistence | Implemented | stored in `turns.metadata_json` |
| Explicit feedback persistence | Implemented | accept/edit/reject/skip remain graph-backed |
| Edit stores rationale and corrected answer separately | Implemented | persisted in `feedback_events` |
| Persistent memes and memodes | Implemented | SQLite tables + edges + retrieval |
| Regard math in code | Implemented | `eden/regard.py` |
| PDF ingest | Implemented | validated on `eden_whitepaper_v14.pdf` |
| CSV/TXT/Markdown ingest | Implemented | validated in tests |
| Graph knowledge-base export | Implemented | generated and browser-opened |
| Behavioral attractor basin export | Implemented | upgraded with inference-circumstance overlays |
| Geometry lab export | Implemented | `geometry_lab.html` + `geometry_diagnostics.json` |
| Measurement ledger export | Implemented | `measurement_ledger.html` + `measurement_events.json` |
| Observatory index page | Implemented | `observatory_index.html` |
| Robust observatory server lifecycle | Implemented | host/port args, reuse, free-port fallback, tests |
| Observatory open without forced synchronous export | Implemented | TUI observatory actions now start/open the server immediately and reuse existing artifacts when present |
| Geometry diagnostics | Implemented | ringness, radiality, linearity, communities, triadic closure, spectral summaries, mirror/chirality/translation proxies |
| Large-graph geometry fallback | Implemented | seeded-scale graphs use sparse-safe approximations instead of SciPy / dense full-graph linear algebra |
| Large-graph local geometry cap | Implemented | geometry export now limits per-memode local reports to keep seeded exports tractable |
| Geometry ablation probes | Implemented | `CO_OCCURS_WITH` masking and dominant-cluster removal |
| Browser observatory filtering | Implemented | graph and basin filters / geometry slice selection |
| Browser observatory interaction modes | Implemented | `INSPECT`, `MEASURE`, `EDIT`, `ABLATE`, `COMPARE` |
| Preview before commit | Implemented | local geometry + global delta preview via live API |
| Edge add/update/remove with provenance | Implemented | observatory precision drawer + measurement events |
| Known memode assertion | Implemented | operator can materialize a memode from a node selection |
| Memode membership refinement | Implemented | persisted and revertible via measurement ledger |
| Revert observatory-originated mutation | Implemented | explicit `revert` action stored as its own event |
| Local selection geometry | Implemented | geometry lab + graph preview support selection-local metrics |
| TUI trace of observatory edits | Implemented | runtime log and trace events emitted on commit / revert |
| Default Qwen 3.5 MLX local pathing | Implemented | runtime prepares repo-local model storage automatically when MLX is selected |
| Weight training / fine-tuning / LoRA | Deferred by design | explicitly out of scope |
| Governor / hidden planner | Deferred by design | explicitly absent |
| Embedding-based semantic retrieval | Deferred | lexical/graph retrieval only |

Validated in this patch:

- `.venv/bin/pytest -q` -> `31 passed`
- CLI observatory fallback from occupied requested port to actual port `8877`
- live observatory preview / commit / revert succeeded against a real experiment
- mock demo export wrote graph, basin, geometry, measurement, and index artifacts
- observatory graph instrument and geometry lab opened in a real browser session
- repo-local Qwen MLX model completed under `models/qwen3.5-35b-a3b-mlx-mxfp4`
- direct MLX generation succeeded against the repo-local Qwen model
- EDEN runtime chat completed against the repo-local MLX backend with separate reasoning and answer surfaces
