# Implementation Truth Table

| Capability | Status | Notes / evidence |
| --- | --- | --- |
| Blank Eden bootstrap | Implemented | runtime + TUI path; validated in tests and demo |
| Seeded Eden bootstrap code path | Implemented | ingests `assets/seed_canon/`; heavy-path validation started on real canon files |
| Fixed-pane amber TUI | Implemented | preserved and refocused around a dialogue-first primary chat surface |
| Live session dialogue boot | Implemented | app opens directly into a resumed-or-created session; wide terminals keep dialogue + telemetry visible, while compact terminals fall back to a dialogue-first composer/transcript view |
| `python -m eden` default entry path | Implemented | no subcommand required for the normal TUI path; flags remain optional overrides |
| Repo-root `python3 app.py` launcher | Implemented | root launcher re-execs the repo-local `.venv` interpreter and then dispatches into `eden.app:main` |
| Local repo-managed MLX model storage | Implemented | default MLX model target is `models/qwen3.5-35b-a3b-mlx-mxfp4` under repo root |
| Local MLX shard-readiness tracking | Implemented | live contract surfaces distinguish metadata-only, partial, and ready model states |
| Repo-local Qwen 3.5 MLX backend | Implemented | repo-local 4-shard model completed and real MLX generation succeeded |
| Multiline composer | Implemented | `TextArea`-based; covered by TUI smoke test |
| Composer focus recovery | Implemented | `Esc` returns focus to the composer, compact aperture view also collapses back to dialogue, and printable keys outside editable widgets are routed there automatically |
| Dialogue-first chat layout | Implemented | primary left dialogue deck keeps transcript + inline review + composer visible; right telemetry stack now uses full-width memgraph/aperture/thinking/event slices plus a thin runtime chyron |
| Scrolling dialogue tape | Implemented | prime transcript now renders the persisted session inside a focusable scroll container instead of a bounded fixed pane |
| Static chiaroscuro transcript shading | Implemented | chat cards now use static shaded panel treatments instead of animated decorative glyph bands inside the message surface |
| Event-driven prime-screen refresh | Implemented | removed the 450ms whole-screen repaint loop; transcript and graph-health surfaces now cache and refresh on state changes |
| Operator-facing answer sanitization | Implemented | membrane now strips `Answer` / `Basis` / `Next Step` scaffolding and keeps model reasoning separate from Adam's visible reply |
| Aperture pull-down drawer | Implemented | `F8` opens a full-width readable active-set scan on wide terminals and a compact aperture-only swap view on small terminals |
| Inline reply review | Implemented | typed `A` / `E` / `R` / `S` plus `Y` confirmation now live directly under Adam's latest answer; `Review` keeps focus in the composer and explains the missing prerequisite if no Adam reply exists yet |
| Conversation log artifact | Implemented | active session transcript is written to markdown under `exports/conversations/` and surfaced via the action bus + merged runtime/event chyron |
| Conversation atlas archive surface | Implemented | modal archive browser exposes all saved sessions through sort/filter plus virtual folder/tag projections stored in session metadata; the `F10`/binding path now opens it through the same worker-safe flow as the action bus |
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
| React observatory shell | Implemented | checked-in Vite bundle served by Python shells and copied into static exports |
| Layered observatory graph payload | Implemented | authoritative `semantic_*`, `runtime_*`, `assemblies`, `cluster_summaries`, and `active_set_slices` planes |
| Deterministic semantic clustering | Implemented | meme-only Louvain clustering with fixed seed, canonical node ordering, and versioned label/token inputs |
| Manual cluster annotation | Implemented | `motif_annotation` now supports `target.kind=\"cluster\"` with exact/transfer/detached cluster label semantics |
| Connected memode support validation | Implemented | memode assertion/update requires a connected qualifying meme support subgraph and rejects passenger memes |
| Live observatory read endpoints | Implemented | overview, graph, basin, sessions, transcript, active-set, runtime status/model |
| Observatory SSE invalidation stream | Implemented | compact invalidation events after turns, feedback, commits, and reverts |
| Browser-local view presets | Implemented | `localStorage` only, keyed by experiment + surface + export manifest/source graph hash |
| Frontend build freshness guard | Implemented | `build-meta.json` emitted at build time, runtime warning via `/api/status`, CI check script in `scripts/check_observatory_build_meta.py` |
| Robust observatory server lifecycle | Implemented | host/port args, reuse, free-port fallback, tests |
| Observatory open without forced synchronous export | Implemented | TUI observatory actions now start/open the server immediately and reuse existing artifacts when present |
| TUI observatory action progress surface | Implemented | Action Bus now separates menu focus from active observatory work, shows phase-progress plus accurate elapsed time, and resets the menu after dispatch so repeat observatory launches remain selectable |
| Export location feedback | Implemented | TUI export action reports the artifact directory path in the session feedback surface after generation |
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

- `./.venv/bin/pytest -q tests/test_observatory_measurements.py tests/test_observatory_server.py` -> `14 passed`
- `npm --prefix web/observatory run build`
- `npm --prefix web/observatory run test`
- `./.venv/bin/python scripts/check_observatory_build_meta.py`
