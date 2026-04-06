# SCIPHR — Status
**Last Updated:** April 2026 | **Current Phase:** Phase 4 — Frontend Wiring

---

## Phase Progress

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — P0 Bugs + Git Setup | ✅ Complete | All 13 bugs fixed, 7/7 tests passing |
| Phase 1 — Database Migration | ✅ Complete | 8,231 fights + 2,615 fighters migrated to Supabase |
| Phase 2 — Intelligence Engine | ✅ Complete | All 9 modules implemented; upset_alert, sharp_money, cinematic_title done (44/44 tests) |
| Phase 3 — API Layer | ✅ Complete | Intelligence wired, /health, /events, Sentry |
| Phase 4 — Frontend Wiring | ✅ Complete | api.js wired, badges, intel tab, dashboard events, scorecard shell |
| Phase 5 — Claude + Poster | 🔴 Not Started | AI analysis + poster |
| Phase 6 — Deploy | 🔴 Not Started | Vercel + Railway + Supabase |

---

## Current State
**What exists:** FastAPI backend + React v2 frontend. XGBoost model at 85.7% accuracy. All P0 bugs fixed. Supabase live (8,231 fights, 2,615 fighters). All 9 intelligence modules implemented (44/44 tests). Phase 4 complete + PRD audit P1/P2/P3 gaps resolved: HeroFightCard fetches live prediction, Upset Watch feed, Editor's Picks relabeled, ModelPerformance subtitle honest, compact intelligence signals in FightPoster, Analyst Mode probability bar + confidence tier + fight history, /fighters returns objects with weight_class/is_active, weight class + active/inactive filter fixed, FighterProfile intelligence scores + fight history + style tag + predict CTA.

**What is broken:** Nothing critical.

**What is fake:** HistoricalScorecard shows empty state (predictions_log empty at launch, no seeding yet — TODO-10). News ticker is hardcoded placeholder text (TODO-15 documents the schema).

**What is missing:** Claude analysis wiring (Phase 5). AI poster Phase 5. Scorecard seeding (TODO-10). Card Temperature requires `card_temperature` field in events.json (operator must populate manually — see TODO-15). Scorecard breakdown stats (Gaps 28-31, deferred to post-launch in TODO-15).

---

## User Actions Required (cannot be automated)
- **Rotate Google service account key** — `backend/service_account.json` was unprotected before .gitignore was added. Treat as compromised.
- **Create `backend/.env`** from `.env.example` with new credentials: `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT_ID`

---

## In Progress
Phase 5 — Claude + Poster (next up).

---

## Next 3 Tasks
1. Start Phase 5: wire Claude analysis async call in AnalystMode (POST /generate-ai-analysis after prediction renders)
2. Wire AI poster generation flow (already built in FightPoster — verify rate-limit error handling is correct)
3. Run TODO-10 seeding session: add winner_actual population tool, seed predictions_log with historical fights

## Phase 4 PRD Audit — Gaps Fixed (April 2026)

| Gap | Fix | Files |
|---|---|---|
| Gap 1-3: FightPoster compact signals | Added Perception Gap, Chaos tier, Edge Detected below prediction stamp | FightPoster.jsx |
| Gap 4-6: Analyst Overview panel | Dual probability bar, confidence tier (LEAN/MODERATE/STRONG/LOCK), Kelly sizing | AnalystMode.jsx |
| Gap 13: Analyst fight history | useEffect fetches GET /fighter/:name/history for both fighters | AnalystMode.jsx, api.js |
| Gap 14: HeroFightCard prediction | Calls api.predictFight() on mount, renders confidence bar + Perception Gap badges | HeroFightCard.jsx |
| Gap 16: Card Temperature | Reads event.card_temperature from events.json, displays in HeroFightCard | HeroFightCard.jsx |
| Gap 17: HotTakes labeling | Relabeled "Editor's Picks" with "not model output" subtitle | Dashboard.jsx, HotTakes.jsx |
| Gap 18: Upset Watch feed | GET /events/{id}/card-predictions endpoint + UpsetWatchFeed section | main.py, Dashboard.jsx, api.js |
| Gap 20: Fake ModelPerformance subtitle | Replaced with honest "tracked on Historical Scorecard" link | Dashboard.jsx |
| Gap 21: Weight class filter broken | /fighters returns objects; filter uses weight_class field correctly | main.py, FighterSearch.jsx |
| Gap 22: Active/inactive filter | Added status filter dropdown (All/Active/Inactive) | FighterSearch.jsx |
| Gap 23: Fighter intelligence scores | Computed on-the-fly: composite, aura, chaos contribution, mirage meter | main.py, FighterProfile.jsx |
| Gap 24: Fighter fight history | Calls GET /fighter/:name/history, renders table | FighterProfile.jsx, api.js |
| Gap 25: Style tag on profile | classify_style() result added to /fighter/:name response and profile card | main.py, FighterProfile.jsx |
| Gap 26: Predict CTA on profile | "Predict a fight with {name}" button → /picks?fighter1=Name | FighterProfile.jsx, PicksBuilder.jsx |
| Gap 27: Weight class on fighter cards | Colored weight class badge on each card in FighterSearch grid | FighterSearch.jsx |

---

## P0 Bug Tracker

| Bug | Status | Fixed In |
|---|---|---|
| NameError ai_analyst.py:164 | ✅ Fixed | ai_analyst.py |
| generate_recent_record defined twice | ✅ Fixed | main.py |
| Dead code block main.py:164-198 | ✅ Fixed | main.py |
| fighter.stats.nickname missing | ✅ Fixed | AnalystMode.jsx (removed) |
| JSX className template literal | ✅ Fixed | HeroFightCard.jsx |
| api.js not wired anywhere | ✅ Fixed | AnalystMode, FightPoster, PicksBuilder |
| requirements.txt incomplete | ✅ Fixed | backend/requirements.txt |
| No .gitignore | ✅ Fixed | .gitignore |
| Credentials exposed | ✅ Fixed | .gitignore (user must rotate key) |
| Hardcoded localhost x3 | ✅ Fixed | All 3 components wired through api.js |
| No same-fighter validation | ✅ Fixed | main.py /predict (HTTP 400) |
| No rate limiting on AI poster | ✅ Fixed | main.py slowapi 3/hr/IP |
| gemini_service.py startup crash | ✅ Fixed | gemini_service.py (Bug 13, unlisted) |
| CORS wildcards (audit gap) | ✅ Fixed | main.py — allow_methods/headers/credentials locked down per PRD §14 |
| alert() in FightPoster.jsx (audit gap) | ✅ Fixed | FightPoster.jsx — replaced with aiPosterError inline state |
| .env.example missing (audit gap) | ✅ Fixed | backend/.env.example created with rotation checklist |

---

## Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| Apr 2026 | Intelligence module interface: Pydantic BaseModel | Already in use in main.py; validates outputs, serializes to JSON cleanly |
| Apr 2026 | Intelligence orchestration: IntelligenceOrchestrator class | Keeps main.py clean; badge_engine needs all outputs; easy to test |
| Apr 2026 | fighters.style: on-the-fly via classify_style(), not persisted | Modules stay pure (no DB writes); fighters.style remains NULL in v1 |
| Apr 2026 | value_bet: reads odds_history only; no live Odds API at predict time | Protects 500 req/mo free tier; deterministic /predict latency |
| Apr 2026 | Intelligence data loading: orchestrator pre-loads fight history | Max 5 DB queries per /predict regardless of module count |
| Apr 2026 | Intelligence failure isolation: per-module _safe_compute() | Any module exception returns None; prediction always succeeds |
| Apr 2026 | Intelligence models: single models.py file | badge_engine needs all 9 result types; central file avoids circular imports |
| Apr 2026 | Phase 2 build split: Sonnet scaffolding + stubs; Opus scoring formulas | CLAUDE.md model selection rule; stubs have detailed TODO(opus) briefs |
| Apr 2026 | Fight history query: no LIMIT (full career) | Max ~35 rows per fighter; finish_rate accuracy over full career |
| Apr 2026 | Database: PostgreSQL Option A — direct CSV migration, all columns | Simplest path, eliminates hosting blockers, no join complexity |
| Apr 2026 | Events data: manual JSON curation for v1 | Zero cost, zero tech risk |
| Apr 2026 | Odds data: The Odds API free tier | 500 req/mo sufficient for fight week cadence |
| Apr 2026 | Win Path: heuristic only (renamed Kill Chain) | Model retrain deferred to v3 |
| Apr 2026 | Auth: not in v1 | Public launch first |
| Apr 2026 | Perception Gap v1: heuristic from dataset proxies | Live sentiment deferred to v2 |
| Apr 2026 | Narrative traps v1: manually tagged in events JSON | Automated NLP deferred to v2 |
| Apr 2026 | Model: frozen, no retraining | 85.7% strong enough for launch |
| Apr 2026 | Canonical frontend: frontend-redesign/ → frontend/ | v2 components only live there; old frontend/ deleted |
| Apr 2026 | Nickname fix: remove from JSX | No nickname field in backend; Phase 2 adds it properly |
| Apr 2026 | Rate limiter storage: in-memory for v1 | Redis (Upstash) deferred to Phase 6 |
| Apr 2026 | fastapi upgraded 0.104.1 → 0.135.3 | starlette 0.27 incompatible with httpx 0.28 in venv |
| Apr 2026 | Feature storage: JSONB per fighter (not per fight) | Per-fight JSONB ~912MB exceeds Supabase free tier; per-fighter ~85MB |
| Apr 2026 | Features stored in canonical r_* form | Eliminates was_red branch at prediction time; simplifies build_full_feature_vector |
| Apr 2026 | Sync SQLAlchemy + psycopg2 (not asyncpg) | Prediction pipeline is sync Python; FastAPI threadpools sync calls automatically |
| Apr 2026 | Schema via create_all(), Alembic deferred to Phase 6 | Schema stable after Phase 1; see TODOS.md TODO-01 |
| Apr 2026 | ChaosResult.label renamed to .tier, MODERATE→MIXED | PRD §10.6 uses 'tier' and 'MIXED'; 'label' was a naming deviation. All tests updated. |
| Apr 2026 | upset_alert, sharp_money, cinematic_title: implemented per PRD §10.8/§10.9/§10.17 | 44/44 tests pass. upset_alert: NO_ODDS fallback + UNDERDOG_EDGE (model≥0.45, american≥+150, edge≥0.08). sharp_money: opening vs current implied, 0.03 movement threshold. cinematic_title: 18-template priority ladder, weight-class color map. |
| Apr 2026 | FalseConsensusResult expanded to 4 labels (not 2); added display_message | PRD §10.14 requires INVISIBLE_COINFLIP/FAKE_MISMATCH/PUBLIC_CERTAINTY_TRAP/MILD_OVERCONFIDENCE |
| Apr 2026 | PerceptionGapResult: added direction_f1/f2 (OVERHYPED/UNDERRATED/ALIGNED) and magnitude | PRD §10.5 display spec requires "Perception Gap: +23pts (Overhyped)" — direction fields enable this |
| Apr 2026 | chaos_scorer accepts event_fight dict; short_notice (+8pts) weight_miss (+5pts) applied | PRD §10.6 lists both as explicit chaos factors; orchestrator now passes event_fight through |
| Apr 2026 | Phase 3: intelligence endpoints bundle-only (no standalone /chaos-score etc.) | All signals returned from /predict; standalone endpoints duplicate DB context-building for zero frontend benefit |
| Apr 2026 | Phase 3: /historical-scorecard deferred to Phase 4 | OQ-11 unresolved; predictions_log empty at launch; scorecard + seeding script designed together with frontend page |
| Apr 2026 | Phase 3: fight_id optional on PredictionRequest | Links /predict to events context (narrative_trap, chaos short_notice/weight_miss); None for ad-hoc predictions |
| Apr 2026 | Phase 3: events.json loaded once at startup into memory | Fail-fast on missing file; zero disk I/O per request; server restart needed to pick up new events (acceptable for manual fight-week curation) |
| Apr 2026 | Phase 3: same-fighter validation moved before predictor/orchestrator None checks | Input validation needs no initialized state; existing tests relied on this ordering |
| Apr 2026 | /predict returns ai_analysis: null; Claude called async via POST /generate-ai-analysis | Eliminates ~3s blocking from /predict; frontend calls /generate-ai-analysis after prediction renders |
| Apr 2026 | POST /predict/simple added (no orchestrator) | Fast path for casual users and dashboard previews; returns winner + confidence only |
| Apr 2026 | GET /fighter/{name}/history added | Last 20 fights from fights table, fuzzy name match applied |
| Apr 2026 | GET /events/{id} now returns full event card; GET /events/upcoming added | PRD §13 routing alignment; events_by_id index built at startup alongside events_index |
| Apr 2026 | POST /generate-ai-analysis added (rate limited 3/hr/IP, asyncio.to_thread) | Standalone Claude endpoint; async wrapper makes sync generate_fight_analysis non-blocking |
| Apr 2026 | predictions_log INSERT now includes odds_at_prediction from value_bet result | Populated when value_bet signal != NO_ODDS and implied probs are available |

---

## Phase 3 PRD Audit — Gaps vs §9 & §13 (April 2026)

PRD §13 lists endpoints not implemented (and not yet covered by a logged decision):

| Gap | PRD Spec | Current State | Priority |
|---|---|---|---|
| `POST /predict/simple` | Fast predict, no intelligence layer | Not built | P2 — useful for latency; defer to Phase 4 or skip for v1 |
| `GET /fighter/{name}/history` | Chronological fight record | Not built | P2 — needed by Fighter Browser page in Phase 4 |
| Events routing mismatch | `/events/upcoming` + `/events/{id}` (Event) | `/events` (all) + `/events/{fight_id}` (single fight) | P2 — routing diverges from PRD; /events/{id} should return the full event card, not one fight |
| `GET /events/{id}/temperature` | CardTemperature | Not built | P3 — deferred until card temperature module exists |
| `POST /generate-ai-analysis` | Standalone AI analysis endpoint | Embedded inside /predict only | P2 — needed so frontend can trigger re-analysis without re-predicting |
| `/health` response shape | `{status, model_loaded, db_connected, version}` | `{status, db, model}` — field names differ, missing `version` | P3 — cosmetic; fix before deploy |
| `predictions_log` missing odds | Log odds at time of pick | INSERT does not include odds | P2 — fix when odds pipeline is live |

PRD §9 architecture gaps:

| Gap | PRD Spec | Current State | Priority |
|---|---|---|---|
| Claude async | Non-blocking; renders when ready | `generate_fight_analysis()` is sync — blocks /predict response up to ~3s | **P1 — fix before Phase 5** |
| Structured logging | structlog JSON logs on every request | print() everywhere in main.py | P3 — fix before deploy |
| Orchestrator parallelism | Intelligence modules run in parallel | Modules run sequentially in orchestrator | P3 — acceptable for v1 latency |

---

## Open Questions Resolved

| OQ ID | Resolution | Date |
|---|---|---|
| — | — | — |

---

## Test Coverage

| Module | Tests Written | Passing |
|---|---|---|
| P0 bugs (same-fighter, rate limit, NameError) | Yes | 7/7 ✅ |
| GoldenFeatureCalculator (DB-backed) | Yes | 7/7 ✅ |
| migrate_csv.py | Yes | 4/4 ✅ |
| predictions_log insert | Yes | 1/1 ✅ |
| Phase 3 API Layer (endpoints + intelligence wiring) | Yes | 23/23 ✅ |
| **Total** | | **248/248 ✅** |

---

## Notes for Next Session
- **Phase 1 is complete.** Supabase live: 8,231 fights, 2,615 fighters. DATABASE_URL in backend/.env.
- **Phase 3 audit complete** — 7 PRD §13 endpoint gaps and 3 §9 architecture gaps logged in table above.
- Most urgent carry-forward: Claude analysis is blocking (P1 fix). See audit table above.
- Phase 4 start: wire api.js into all components, display intelligence badges in Simple Mode.
- Before Phase 5: fix Claude async gap (asyncio.to_thread or background task in /predict).
- 3 intelligence stubs still need Opus: upset_alert, sharp_money, cinematic_title (NotImplementedError).
