# Implementation Truth Table

| Capability | Status | Notes / evidence |
| --- | --- | --- |
| Blank Eden bootstrap | Implemented | runtime + TUI path; validated in tests and demo |
| Seeded Eden bootstrap code path | Implemented | ingests `assets/seed_canon/`; heavy-path validation started on real canon files |
| Fixed-pane amber TUI | Implemented | preserved and refocused around a dialogue-first primary chat surface |
| Live session dialogue boot | Implemented | app opens directly into a resumed-or-created session with the top action bus, visible transcript/composer, and secondary telemetry panels |
| `python -m eden` default entry path | Implemented | no subcommand required for the normal TUI path; flags remain optional overrides |
| Repo-root `python3 app.py` launcher | Implemented | root launcher re-execs the repo-local `.venv` interpreter and then dispatches into `eden.app:main` |
| Local repo-managed MLX model storage | Implemented | default MLX model target is `models/qwen3.5-35b-a3b-mlx-mxfp4` under repo root |
| Local MLX shard-readiness tracking | Implemented | live contract surfaces distinguish metadata-only, partial, and ready model states |
| Repo-local Qwen 3.5 MLX backend | Implemented | repo-local 4-shard model completed and real MLX generation succeeded |
| Multiline composer | Implemented | `TextArea`-based; covered by TUI smoke test |
| Composer focus recovery | Implemented | `Esc` returns focus to the composer and printable keys outside editable widgets are routed there automatically |
| Dialogue-first chat layout | Implemented | primary left dialogue deck keeps transcript + inline review + composer visible; right telemetry stack now uses full-width memgraph/aperture/thinking/event slices plus a thin runtime chyron |
| Scrolling dialogue tape | Implemented | prime transcript now renders the persisted session inside a focusable scroll container instead of a bounded fixed pane |
| Static chiaroscuro transcript shading | Implemented | chat cards now use static shaded panel treatments instead of animated decorative glyph bands inside the message surface |
| Event-driven prime-screen refresh | Implemented | removed the 450ms whole-screen repaint loop; transcript and graph-health surfaces now cache and refresh on state changes |
| Operator-facing answer sanitization | Implemented | membrane now strips `Answer` / `Basis` / `Next Step` scaffolding and keeps model reasoning separate from Adam's visible reply |
| Aperture pull-down drawer | Implemented | `F8` opens a full-width readable active-set scan above the dialogue/telemetry split |
| Inline reply review | Implemented | typed `A` / `E` / `R` / `S` plus `Y` confirmation now live directly under Adam's latest answer and write through the graph-backed feedback path |
| Conversation log artifact | Implemented | active session transcript is written to markdown under `exports/conversations/` and surfaced via the action bus + merged runtime/event chyron |
| Conversation atlas archive surface | Implemented | modal archive browser exposes all saved sessions through sort/filter plus virtual folder/tag projections stored in session metadata |
| Fixed local-MLX runtime contract | Implemented | the live TUI no longer exposes backend selection on the primary surface; local MLX is the normal runtime contract |
| Deck + Review secondary surfaces | Implemented | detailed budget / thinking / history remain in `Deck`; explicit feedback remains in `Review` |
| Dedicated model thinking panel | Implemented | MLX/Qwen reasoning is kept on and surfaced separately from the final answer via Deck |
| Operator-label turn persistence | Implemented | saved turns and graph-ingested operator text are punctuated as `Brian the operator: ...` |
| Session-start inference profile flow | Implemented | new-session and blank/seeded session modal |
| Manual inference mode | Implemented | persisted in session metadata and surfaced per turn |
| Runtime auto inference mode | Implemented | deterministic bounded heuristics; tested |
| Adam auto inference mode | Implemented with bounded fallback | mock path chooses bounded presets; MLX path falls back to `runtime_auto` and logs it |
| Live budget / allowance panel | Implemented | updates from preview/chat state and persists per turn |
| Per-turn inference circumstance persistence | Implemented | stored in `turns.metadata_json` |
| Explicit feedback persistence | Implemented | accept/edit/reject/skip remain graph-backed and are now available inline in the chat deck |
| Edit stores rationale and corrected answer separately | Implemented | persisted in `feedback_events` |
| Persistent memes and memodes | Implemented | SQLite tables + edges + retrieval |
| Regard math in code | Implemented | `eden/regard.py` |
| PDF ingest | Implemented | validated on `eden_whitepaper_v14.pdf` |
| CSV/TXT/Markdown ingest | Implemented | validated in tests |
| Ingest framing prompt | Implemented | document ingest modal indexes operator framing text into the memgraph as persistent document-conditioning material |
| Live memgraph bus visualization | Implemented | signal field now renders a brighter orthographic glyph slice using active nodes, recall anchors, recent trace events, ingest roots, and a bus-to-aperture read with an always-visible legend |
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

- `.venv/bin/pytest -q` -> `34 passed`
- CLI observatory fallback from occupied requested port to actual port `8877`
- live observatory preview / commit / revert succeeded against a real experiment
- mock demo export wrote graph, basin, geometry, measurement, and index artifacts
- observatory graph instrument and geometry lab opened in a real browser session
- repo-local Qwen MLX model completed under `models/qwen3.5-35b-a3b-mlx-mxfp4`
- direct MLX generation succeeded against the repo-local Qwen model
- EDEN runtime chat completed against the repo-local MLX backend with separate reasoning and answer surfaces
