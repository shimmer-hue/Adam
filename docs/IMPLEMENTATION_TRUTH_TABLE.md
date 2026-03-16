# Implementation Truth Table

| Capability | Status | Notes / evidence |
| --- | --- | --- |
| Single persistent Adam graph | Implemented | runtime now reuses one primary graph across new and resumed sessions; validated in runtime/TUI tests |
| Operator-driven ingest instead of seeded startup | Implemented | startup no longer offers blank/seeded graph creation; documents enter the same graph through normal ingest flow |
| Fixed-pane operator looks | Implemented | amber-dark remains the default dialogue-first surface, and Deck now exposes a persisted `Typewriter Light` alternative proved by `tests/test_tui_smoke.py` |
| Live session dialogue boot | Implemented | app opens directly into a resumed-or-created session; wide terminals keep dialogue + telemetry visible, while compact terminals fall back to a dialogue-first composer/transcript view |
| `python -m eden` default entry path | Implemented | no subcommand required for the normal TUI path; flags remain optional overrides |
| Repo-root `python3 app.py` launcher | Implemented | root launcher re-execs the repo-local `.venv` interpreter and then dispatches into `eden.app:main` |
| Local repo-managed MLX model storage | Implemented | default MLX model target is `models/qwen3.5-35b-a3b-mlx-mxfp4` under repo root |
| Local MLX shard-readiness tracking | Implemented | the top action shelf status lines distinguish metadata-only, partial, and ready model states |
| Repo-local Qwen 3.5 MLX backend | Implemented | repo-local 4-shard model completed and real MLX generation succeeded |
| Multiline composer | Implemented | `TextArea`-based; covered by TUI smoke test |
| Composer focus recovery | Implemented | `Esc` returns focus to the composer, compact aperture view also collapses back to dialogue, and printable keys outside editable widgets are routed there automatically |
| Dialogue-first chat layout | Implemented | primary left dialogue deck now keeps transcript plus composer visible while the top row carries the action shelf, a live turn-status strip, and aperture; the right telemetry stack carries memgraph plus the reasoning/feed surface, and the bottom runtime chyron drawer remains hidden by default (`F11` to open) |
| Scrolling dialogue tape | Implemented | prime transcript now renders the persisted session inside a focusable scroll container instead of a bounded fixed pane |
| Static chiaroscuro transcript shading | Implemented | chat cards now use static shaded panel treatments instead of animated decorative glyph bands inside the message surface |
| Event-driven prime-screen refresh | Implemented | removed the 450ms whole-screen repaint loop; transcript and graph-health surfaces now cache and refresh on state changes |
| Operator-facing answer sanitization | Implemented | membrane now strips `Answer` / `Basis` / `Next Step` scaffolding and keeps model reasoning separate from Adam's visible reply |
| Aperture pull-down drawer | Implemented | `F8` opens a full-width readable active-set scan on wide terminals and a compact aperture-only swap view on small terminals |
| Latest-turn inline reply review | Implemented | `Review` / `F7` now focuses the in-chat explicit-feedback form for `accept` / `edit` / `reject` / `skip` while Adam's latest answer is pending review, then collapses back to a compact stored-feedback line after submission |
| Conversation log artifact | Implemented | active session transcript is written to markdown under `exports/conversations/` and surfaced via the action strip + merged runtime/event chyron |
| Conversation atlas archive surface | Implemented | modal archive browser exposes all saved sessions through sort/filter plus virtual folder/tag projections stored in session metadata; the `F10`/binding path now opens it through the same worker-safe flow as the action strip |
| Fixed local-MLX runtime contract | Implemented | the live TUI no longer exposes backend selection on the primary surface; local MLX is the normal runtime contract |
| Deck + Review secondary surfaces | Implemented | detailed budget / thinking / history remain in `Deck`; explicit feedback remains in `Review` |
| Dedicated runtime reasoning/feed surface | Implemented | MLX/Qwen reasoning is kept separate from the final answer, the prime TUI feed suppresses prompt-mirror scaffolding while surfacing response-first material, answer-beat reductions, useful hum continuity or first-turn seed details, runtime condition, membrane record, and consideration-trace telemetry in a focusable lower-right viewport, and the `Reasoning` lens now streams visible model reasoning live during generation when the backend emits it |
| Operator-label turn persistence | Implemented | saved turns and graph-ingested operator text are punctuated as `Brian the operator: ...` |
| Session-start inference profile flow | Implemented | new-session and resume flows use one shared session modal against the persistent graph, and the tuning apparatus now includes a bounded `history_turns` control (`1..256`) that persists per session; actual injected recent history is budget-bounded at prompt-assembly time |
| Manual inference mode | Implemented | persisted in session metadata and surfaced per turn |
| Runtime auto inference mode | Implemented | deterministic bounded heuristics; tested |
| Adam auto inference mode | Implemented with bounded fallback | mock path chooses bounded presets; MLX path falls back to `runtime_auto` and logs it |
| Live budget / allowance panel | Implemented | detailed budget surfaces remain in Deck, and the prime topbar now carries a compact used/remaining context-budget estimate sourced from the same preview/chat-state budget object and persisted per turn |
| Per-turn inference circumstance persistence | Implemented | stored in `turns.metadata_json` |
| Explicit feedback persistence | Implemented | accept/edit/reject/skip remain graph-backed and are now available inline in the chat deck |
| Edit stores rationale and corrected answer separately | Implemented | persisted in `feedback_events` |
| Persistent memes and memodes | Implemented | SQLite tables + edges + retrieval |
| Regard math in code | Implemented | `eden/regard.py` |
| Hum continuity artifact | Implemented as a bounded read-only runtime artifact | `eden/hum.py` derives `current_hum.md` plus `current_hum.json` from persisted `active_set_json`, `feedback_events`, and membrane events, refreshes after `chat()` and `apply_feedback()`, and now surfaces bounded hum entries, stats, metrics, and token-table counts through `session_state_snapshot()`, observatory overview/session turns, `observatory_index.json`, the prime-TUI `Hum Live` feed lens, the observatory continuity strip, and the conversation-log footer. Historical artifact lineage remains in `/Users/brianray/Desktop/adam_hum_ALL.md`. See `docs/HUM_SPEC.md`. |
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
| Tanach.us UXLC fetch / verify / index substrate | Implemented | `scripts/sync_tanakh_uxlc.py`; manifest/index sidecars and pytest fixture proof |
| Deterministic Tanakh analyzers and merkavah scene compiler | Implemented | `eden/tanakh/service.py`; analyzer hash determinism + scene replay determinism covered in `tests/test_tanakh_tools.py` |
| Tanakh observatory sidecar surface | Implemented | React observatory now exposes canonical reader, derived analyzer cards, provenance badges, JSON debug, and Three-derived scene panel via `tanakh_surface.json` |
| Tanakh render-validation harness | Instrumented | `tanakh_render_validation.json` + `.html` automate oracle capture and manual-review artifacts; glyph-placement comparison is not yet machine-scored |
| Layered observatory graph payload | Implemented | authoritative `semantic_*`, `runtime_*`, `assemblies`, `cluster_summaries`, and `active_set_slices` planes |
| Deterministic semantic clustering | Implemented | meme-only Louvain clustering with fixed seed, canonical node ordering, and versioned label/token inputs |
| Manual cluster annotation | Implemented | `motif_annotation` now supports `target.kind=\"cluster\"` with exact/transfer/detached cluster label semantics |
| Connected memode support validation | Implemented | memode assertion/update requires a connected qualifying meme support subgraph and rejects passenger memes |
| Live observatory read endpoints | Implemented | overview, graph, basin, sessions, transcript, active-set, runtime status/model |
| Observatory SSE invalidation stream | Implemented | compact invalidation events after turns, feedback, commits, and reverts |
| Browser-local view presets | Implemented | browser-proved via Playwright; `localStorage` only, keyed by the internal graph/export identity + surface + export manifest/source graph hash; hydration race fixed so reload restores saved view without entering the measurement ledger |
| Browser-local layout workbench | Implemented | worker-backed browser layouts now expose a family-organized 12-part terrain browser with operator-facing usage copy; the runnable subset includes `forceatlas2`, `fruchterman_reingold`, `kamada_kawai`, `linlog`, `sugiyama_layered`, `radial_tree`, `simple_circular`, `circular_degree`, `circular_community`, `radial`, `noverlap`, `fixed_coordinate`, and `community_clusters`, with pause/cancel/reset/compare controls and heavy-graph honesty proved in workbench Playwright journeys |
| Browser-local appearance, filters, and rankings | Implemented | React workbench exposes style mappings, search/filter rail, connected-component and ego controls, and worker-computed statistics/rankings; browser-local state remains outside the measurement ledger |
| Browser Data Lab and Gephi export interoperability | Implemented | node/edge tables, bulk selection handoff, CSV/JSON selection export, and Gephi-accepted graph downloads (`gexf`, `graphml`, `gdf`, `gml`, `graphviz dot`, `pajek net`, `netdraw vna`, `ucinet dl`, `tulip tlp`, `tgf`) are browser-visible and non-authoritative |
| Observatory browser E2E audit | Implemented | Playwright Chromium full battery plus Firefox/WebKit smoke proofs captured under `web/observatory/test-results/chromium-final` and `cross-browser-smoke`; every journey now fails if screenshot/DOM/JSON evidence artifacts are missing or empty |
| Frontend build freshness guard | Implemented | `build-meta.json` emitted at build time, runtime warning via `/api/status`, CI check script in `scripts/check_observatory_build_meta.py` |
| Robust observatory server lifecycle | Implemented | host/port args, reuse, free-port fallback, tests |
| Observatory open without forced synchronous export | Implemented | TUI observatory actions now start/open the server immediately and reuse existing artifacts when present |
| TUI observatory action progress surface | Implemented | the top action shelf separates selected action from active observatory work and shows phase-progress plus accurate elapsed time while the strip remains directly repeatable |
| Export location feedback | Implemented | TUI export action reports the artifact directory path in the session feedback surface after generation |
| Geometry diagnostics | Implemented | ringness, radiality, linearity, communities, triadic closure, spectral summaries, mirror/chirality/translation proxies |
| Large-graph geometry fallback | Implemented | large persistent graphs use sparse-safe approximations instead of SciPy / dense full-graph linear algebra |
| Large-graph local geometry cap | Implemented | geometry export now limits per-memode local reports to keep large persistent-graph exports tractable |
| Geometry ablation probes | Implemented | `CO_OCCURS_WITH` masking and dominant-cluster removal |
| Browser observatory view controls | Implemented | browser-proved source/build badges, graph modes, assembly render modes, basin lift modes, payload-status diagnostics, honest sparse/large-graph copy, and keyboard/text access |
| Browser compare / coordinate surface | Implemented | React workbench exposes coordinate-mode controls plus baseline/modified compare rendering backed by `preview_graph_patch`; browser-local compare state stays out of the measurement ledger |
| Browser observatory interaction modes | Implemented | explicit `INSPECT`, `MEASURE`, `EDIT`, `ABLATE`, and `COMPARE` controls are browser-visible and exercised in Vitest/Playwright |
| Preview before commit | Implemented | live API + server tests cover preview semantics, and the React observatory now exposes preview/commit controls plus compare patch rendering |
| Edge add/update/remove with provenance | Implemented | precision drawer exposes attributable edge mutation with preview/commit and ledger refresh; backend persistence/revert path remains covered in measurement/server tests |
| Known memode assertion | Implemented | browser flow exposes admissibility-bounded memode assertion with preview/commit; backend support validation remains covered in measurement tests |
| Memode membership refinement | Implemented | browser flow exposes memode membership refinement with preview/commit and persisted measurement events |
| Revert observatory-originated mutation | Implemented | React measurement ledger exposes explicit revert actions; backend/server tests prove `revert` event persistence and trace linkage |
| Local selection geometry | Implemented | browser workbench exposes local measurement preview and commit flows with selection-bounded geometry deltas |
| Browser-visible runtime trace of observatory edits | Implemented | `GET /api/sessions/<session_id>/trace` plus React runtime-trace panel make observatory causality visible in the browser and remain read-only evidence surfaces |
| Default Qwen 3.5 MLX local pathing | Implemented | runtime prepares repo-local model storage automatically when MLX is selected |
| Weight training / fine-tuning / LoRA | Deferred by design | explicitly out of scope |
| Governor / hidden planner | Deferred by design | explicitly absent |
| Embedding-based semantic retrieval | Deferred | lexical/graph retrieval only |

Validated in this patch:

- `./.venv/bin/pytest -q tests/test_observatory_measurements.py tests/test_observatory_server.py` -> `14 passed`
- `npm --prefix web/observatory run build`
- `npm --prefix web/observatory run test`
- `./.venv/bin/python scripts/check_observatory_build_meta.py`
