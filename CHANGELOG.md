# Changelog

All notable changes to SCIPHR will be documented in this file.

## [0.1.16.1] - 2026-04-11

### Fixed
- `frontend/src/components/picks/FighterSearchModal.jsx`: request limit corrected from 10000 → 5000 — the 10000 value exceeded the backend's `le=5000` Query constraint, causing the FighterSearchModal to receive a 422 and fail to load any fighters for selection

## [0.1.16.0] - 2026-04-11

### Fixed
- `backend/main.py`: `/fighters` endpoint limit cap raised from 500 → 5000 — requests for the full fighter database (2,615 fighters) returned a 422 validation error, causing `FighterSearch` to silently display 0 fighters
- `frontend/src/pages/FighterSearch.jsx`: request limit aligned to 5000 to match backend cap; API failures now surface a visible error card instead of an empty list

### Added
- `frontend/src/__tests__/FighterSearch.test.jsx`: 3 tests covering successful load, API failure → error card (regression for the silent-zero-fighters bug), and correct limit parameter

### Changed
- `.gitignore`: `.claude/settings.local.json` excluded from repo (local tool-permission state, not project code)

## [0.1.15.0] - 2026-04-11

### Added
- `backend/scripts/resolve_outcomes.py`: post-fight outcome resolution script; accepts `--event-id` and `--results` (JSON array); updates `actual_winner`, `was_correct`, `actual_method`, `actual_round`, `resolved_at` in `predictions_log`; idempotent; `--dry-run` supported
- `backend/tests/test_resolve_outcomes.py`: 9 tests covering correct/wrong prediction, order-insensitive matching, dry-run, no-match warning, winner-not-in-fight skip, idempotency, event_id filter, method/round persistence
- `backend/main.py`: `_sanitize_fighter_name()` helper — strips whitespace, enforces ≤100 chars, rejects non-printable chars; applied to `POST /predict`, `POST /predict/simple`, `POST /generate-ai-analysis`, `GET /fighter/{name}`, `GET /fighter/{name}/history`
- `backend/main.py`: `redis_connected` field in `GET /health` response (`"ok"` / `"error"` / `"not_configured"`); pings Upstash using `_REDIS_CONNECT_TIMEOUT_S`; does not affect degraded status (in-memory fallback covers Redis absence)
- `TODOS.md`: TODO-24 — Google service account key rotation (hard blocker before Render deploy)

### Changed
- `backend/main.py`: extracted `_REDIS_CONNECT_TIMEOUT_S = 2` constant; unified Redis timeout between startup check and `/health` check (was 3s vs 2s inconsistency)
- `TODOS.md`: TODO-22 — clarified custom domain purchase timing (buy before public announcement, not before paper launch)
- `STATUS.md`: Decisions Log — OQ-10 formally resolved: Render free tier chosen over Railway
- `SCIPHR_PRD_v1.1.md`: §17 paper launch graduation checklist — replaced "Claude analysis generating on 80%+ of predictions" with "Template analysis generating on 100% of predictions (Claude wiring deferred to post-launch — see TODOS.md TODO-19)"

### Fixed
- `backend/tests/test_api_phase3.py`: `test_health_ok` now asserts `redis_connected == "not_configured"` (correct for test env without `UPSTASH_REDIS_URL`)

## [0.1.14.0] - 2026-04-05

### Added
- `backend/Dockerfile`: production Docker image for Render deployment; `PYTHONPATH=/app/backend`, repo-root build context, layered pip install for cache efficiency
- `render.yaml`: Render blueprint with `dockerfilePath`, `dockerContext`, and all required env var stubs (`DATABASE_URL`, `SENTRY_DSN`, `ALLOWED_ORIGINS`, `UPSTASH_REDIS_URL`, `GEMINI_API_KEY`, etc.)
- `backend/requirements-prod.txt`: trimmed production dependency list (~250MB image vs ~600MB full); excludes matplotlib, seaborn, lightgbm, openpyxl, beautifulsoup4 and other dev-only packages
- `frontend/vercel.json`: SPA rewrite rule (`/* → /index.html`), Vite build config for Vercel deployment
- `backend/scripts/seed_scorecard.py`: seeds `predictions_log` with post-dataset-cutoff fights (≥`--after-date`); idempotent via date+fighter pair check; `--dry-run` flag; injects `_predictor` for testing
- `backend/tests/test_seed_scorecard.py`: 7 tests covering insert, idempotency, was_correct True/False, None predictor skip, date cutoff, and dry-run (263 Python + 34 Vitest all passing)
- `backend/main.py`: Upstash Redis rate-limiter storage with automatic in-memory fallback on connection failure; `UPSTASH_REDIS_URL` env var controls; ping tested at startup
- `TODOS.md`: TODO-22 (custom domain DNS wiring), TODO-23 (Render paid tier upgrade trigger)

### Changed
- `backend/main.py`: `__file__`-anchored paths for model (`../models/golden_model.pkl`) and src (`../src`) — container-safe regardless of working directory
- `backend/main.py`: all `print()` statements replaced with stdlib `logging` + JSON formatter (`_JSONFormatter`); `LOG_LEVEL` env var controls verbosity; log field structure: `time`, `level`, `logger`, `msg`
- `backend/main.py`: `/health` response fields renamed per PRD §13: `db` → `db_connected`, `model` → `model_loaded`; `version` field added from `APP_VERSION` env var
- `backend/main.py`: rate limiter `Limiter(key_func=..., storage_uri=...)` — explicit `if/else` ternary replacing fragile `A and B or C` form
- `backend/gemini_service.py`: drops `GOOGLE_APPLICATION_CREDENTIALS` service-account-file dependency; uses `GEMINI_API_KEY` + Gemini Developer API REST endpoint exclusively; removes broken `_get_api_key_bearer()` stub and dead Vertex AI branch
- `backend/tests/test_api_phase3.py`: `/health` assertions updated to `db_connected`/`model_loaded`/`version`; 2 CORS tests added (`[23]` allowed origin, `[24]` blocked origin); total 25 passing
- `.gitignore`: `*.pkl` wildcard replaced with explicit exclusions (`best_ufc_model.pkl`, `best_ufc_model_v2.pkl`); `golden_model.pkl` (1.9MB) is now committed for Render deployment

## [0.1.13.0] - 2026-04-05

### Added
- `ai_analyst.py`: `intelligence_signals` parameter on `generate_fight_analysis()` and `_generate_template_analysis()` — chaos score, perception gap magnitude, narrative risk, and value signal now inform key factors, betting advice, and risk bullets
- `ai_analyst.py`: Fighter style (via `classify_style()`) and KO rate proxy (`total_knockdowns / total_fights`) computed and used in the Claude prompt (`_build_prompt`) ready for TODO-19 wiring
- `gemini_service.py`: `aspect_ratio` parameter on `generate_ai_poster()` — `"1:1"` (standard, default) or `"9:16"` (Instagram Story); was previously hardcoded to `"9:16"`
- `main.py`: `AIAnalysisRequest.intelligence_signals: Optional[dict]` — frontend passes full `IntelligenceResult.model_dump()` with each analysis request
- `main.py`: `AIPosterRequest.aspect_ratio: Optional[str]` — caller can select standard or Instagram Story poster format
- `frontend/src/api/api.js`: `generateAIAnalysis()` includes `intelligence_signals: predictionData.intelligence` in request body
- `AnalystMode.jsx` + `AnalystMode.css`: CSS spinner replaces plain "Analyzing..." text in AI Analysis loading state
- `TODOS.md`: TODO-21 — $10 Google Cloud cost alert for Imagen poster generation (manual deploy step, required before public launch)

### Fixed
- `backend/tests/test_p0.py`: `TestAnalystImpliedOdds` direct calls to `_generate_template_analysis()` updated to pass required `intelligence_signals` argument

## [0.1.12.0] - 2026-04-05

### Added
- `AnalystMode`: AI Analysis panel in Overview tab — fires `POST /generate-ai-analysis` async on mount when prediction is present; renders Key Factors, Betting Guidance, Risk Factors, and disclaimer; hidden until analysis is loading/loaded/errored (no empty-header flash)
- `AnalystMode`: Fight DNA upgraded from simple bars to `RadarChart` (Recharts) across all 8 dimensions (striking, grappling, wrestling, submission, pressure, chin, cardio, speed); null guard prevents crash when `fight_dna` module fails

### Changed
- `api.js`: `generateAIAnalysis()` request body fixed to match `AIAnalysisRequest` schema — was sending `{fighter1_name, fighter2_name, prediction}`, now sends `{fighter1, fighter2, winner, confidence, fighter1_stats, fighter2_stats}`
- `api.js`: `request()` now attaches `err.status = response.status` to thrown errors; consumers can check `err.status === 429` instead of parsing error message strings
- `AnalystMode`: 429 rate-limit errors show "Rate limit reached — try again in an hour." instead of generic error copy
- `backend/.env.example`: `ANTHROPIC_API_KEY` commented out as optional with note that template analysis is the v1 default; see TODO-19 for Claude SDK wiring

### Added (tests)
- `AnalystMode.test.jsx`: 9 new tests — AI analysis call on mount, null-prediction guard, successful render of key factors, 429 error copy, 500 error copy, Fight DNA RadarChart renders, null `fight_dna`, empty `f1_dna` null guard; mock updated to include `generateAIAnalysis`

### Added (docs)
- `TODOS.md` TODO-19: Claude API wiring in `ai_analyst.py` — prompt already built at line 35, needs `anthropic.Anthropic().messages.create()` call + template fallback
- `TODOS.md` TODO-20: Rate limit counter for `/generate-ai-analysis` — parity with `aiGenerationsLeft` pattern in `FightPoster.jsx`

## [0.1.11.0] - 2026-04-05

### Added
- `api.js`: `predictSimple()` — calls `POST /predict/simple` without logging to `predictions_log`; for display previews only
- `api.js`: `getFighterHistory()`, `getCardPredictions()`, weight class / active-only filter params on `getFighters()`
- `GET /events/past` endpoint — returns past events sorted desc; was missing (pre-existing 404)
- `GET /events/{id}/card-predictions` — runs `predict/simple` for all fights on a card; used by Upset Watch feed
- `GET /fighters` now returns `[{name, weight_class, is_active}]` objects with optional `weight_class` and `active_only` query params
- `GET /fighter/{name}` now returns `intelligence` block with on-the-fly heuristic scores (`aura_score`, `composite_score`, `chaos_contribution`, `mirage_meter`, `style`, `scores_source`)
- `classify_style` import moved to module level in `main.py`
- `intelligence.scores_source` field — `"computed"` when DB has batch scores, `"heuristic"` otherwise
- TODOS 16–18: deferred gaps documented (endpoint shape standardisation, UpsetWatchFeed extraction, `card_temperature` field schema)
- FighterSearch: weight class filter and active/inactive status filter now functional; weight class tag badge on each card
- FighterProfile: intelligence scores panel, fight history table, style tag badge, "Predict a fight with" CTA
- HeroFightCard: live confidence bar from `predictSimple` (no-log); Card Temperature badge from `event.card_temperature`
- Dashboard: Upset Watch feed via `getCardPredictions`; "Editor's Picks" labeling with "not model output" subtitle; ModelPerformance subtitle links to /scorecard
- AnalystMode: dual probability bar, confidence tier badge (LEAN/MODERATE/STRONG/LOCK), Kelly fraction, fight history for both fighters
- FightPoster: compact intelligence signals below prediction stamp (Perception Gap, Chaos tier, Edge Detected)
- PicksBuilder: pre-loads fighters from `?fighter1=Name&fighter2=Name` URL params

### Fixed
- `HeroFightCard` used `api.predictFight()` (POST `/predict`) on every Dashboard load, polluting `predictions_log` with auto-generated preview entries — switched to `api.predictSimple()` (POST `/predict/simple`, no logging)
- Weight class filter was completely broken — `/fighters` previously returned strings, filter never applied; now returns objects and filter uses `weight_class` field correctly
- `test_fighters_endpoint_returns_db_names` — test expected string list; updated to extract names from object array
- `Dashboard.test.jsx` mock missing `predictSimple` and `getCardPredictions` — added both
- `AnalystMode.test.jsx` — `vi.mock` factory referenced `const mockRequest` before initialization (hoisting bug); replaced with inline `vi.fn()` and `import api` post-mock
- FighterSearchModal updated to use `fighter.name` since `/fighters` now returns objects

### Changed
- `GET /fighters` response shape changed from `string[]` to `{name, weight_class, is_active}[]`

## [0.1.10.0] - 2026-04-05

### Added
- **Phase 4: Frontend Wiring** — complete wiring of React frontend to real backend data
- `GET /historical-scorecard` endpoint — returns paginated prediction history from `predictions_log`, includes accuracy computation, `correct` flag per row, and pagination echo; max 200 rows per request
- `api.js`: `generateAIAnalysis()` and `getHistoricalScorecard()` methods; removed dead `getFighterStats()` and stub `getModelPerformance()`
- **Intelligence tab** in `AnalystMode` — all 11 SCIPHR signals rendered: Chaos Score, Perception Gap, Narrative Trap, False Consensus, Nightmare Matchup, Kill Chain (Win Path), Fight DNA (with per-dimension bars), Line Crack (Value Bet), Dog Teeth (Upset Alert), Sharp Echo, cinematic title
- **Badges** in `FightPoster` (Simple Mode) — all badge types with color tokens displayed after prediction stamp
- **Cinematic title** in `FightPoster` header — replaces hardcoded "FIGHT NIGHT"
- `HistoricalScorecard` page (`/scorecard` route) — empty state CTA when no predictions logged; stats row + table when data exists
- **vitest test scaffold** — 5 test files, 26 tests across Dashboard, PicksBuilder, FightPoster, AnalystMode, HistoricalScorecard; `@testing-library/react` + jsdom environment
- `frontend/src/data/hot-takes.json` — curated editorial JSON replaces inline mock array in `HotTakes.jsx`
- Backend tests for `/historical-scorecard` (6 tests covering empty state, row mapping, correct flag, accuracy, pagination)

### Changed
- `Dashboard.jsx` — fetches upcoming/past events on mount via `api.js`; passes data as props to `HeroFightCard`, `UpcomingFights`, `EventsTimeline`; shows loading state during fetch and error banner on failure
- `AnalystMode.jsx` — removed `/detailed-stats` secondary API call (was re-running XGBoost); now reads `fighter1_stats`, `fighter2_stats`, `intelligence` from prediction prop; tabs refactored from 5 repeated buttons to array-driven loop
- `HeroFightCard.jsx` — fixed Rules of Hooks violation (early return moved after all hooks); prediction bar null-guarded; accepts real event prop
- `ModelPerformance.jsx` — replaced fake multi-tier cards with real XGBoost model stats (85.7% accuracy, 8,231 fights, 5,401 features)
- `PicksBuilder.jsx` — prediction errors now shown inline via `role="alert"` div; same-fighter and connection errors have distinct messages
- Sharp Echo panel now shows all signals (not just `MARKET_ALIGNMENT`); `movement_magnitude` null-guarded
- `/historical-scorecard` `limit` parameter capped at 200 rows to prevent full-table pulls

### Fixed
- `HeroFightCard` Rules of Hooks violation — `useEffect` dependency on `fight?.date` used optional chaining; early return moved after all hooks
- `es-toolkit` upgraded to `^1.45.1` to resolve missing `compat/get.js` required by recharts
- `movement_magnitude` null guard in Sharp Echo panel (was `NaN` render when null)

## [0.1.9.1] - 2026-04-05

### Changed
- STATUS.md updated: Phase 2 Intelligence Engine marked complete (was "In Progress"); upset_alert, sharp_money, cinematic_title confirmed implemented with 44/44 tests passing
- Next 3 Tasks updated to reflect Phase 4 as next priority (intelligence stubs no longer blocking)

## [0.1.9.0] - 2026-04-05

### Added
- `GET /events/upcoming` — returns the next upcoming event by date; falls back to most recent past event when no future events are loaded
- `GET /events/{event_id}` — returns the full event card (all fights) by `event_id`; replaces the old `GET /events/{fight_id}` single-fight endpoint
- `GET /fighter/{name}/history` — last 20 fights in reverse chronological order from the `fights` table; applies fuzzy name match via `search_fighter` when predictor is loaded
- `POST /predict/simple` — fast prediction path skipping the intelligence orchestrator; returns `winner`, `confidence`, `prob_fighter1`, `prob_fighter2` only
- `POST /generate-ai-analysis` — standalone rate-limited (3/hr/IP) Claude analysis endpoint; uses `asyncio.to_thread` so the sync `generate_fight_analysis` never blocks the event loop
- `events_by_id` index built at startup alongside `events_index` for O(1) event card lookup
- `AIAnalysisRequest` and `SimplePredictionRequest` Pydantic request models
- TODOS 12–13: deferred `/health` field-name fix and parallel orchestrator (v2)

### Changed
- `POST /predict` no longer calls Claude inline; returns `ai_analysis: null` immediately — frontend calls `POST /generate-ai-analysis` asynchronously after prediction renders
- `predictions_log` INSERT now populates `odds_at_prediction` from `value_bet.implied_prob_f1/f2` when signal is not `NO_ODDS` and both implied probs are non-null
- Phase 3 API Layer test suite expanded from 12 to 23 tests covering all new endpoints, rate limit enforcement, blue-corner history path, and odds logging

### Fixed
- `odds_snapshot` construction now guards `implied_prob_f2 is not None` alongside `implied_prob_f1`, preventing a silent `float(None) TypeError` swallowed by the outer try/except
- `mock_predictor.search_fighter` returns `None` by default in tests, preventing MagicMock leaking into fighter name DB queries

## [0.1.8.0] - 2026-04-05

### Added
- Phase 3 API Layer: `IntelligenceOrchestrator` wired into `POST /predict` — every prediction response now includes a full `intelligence` bundle (all 11 modules; failed modules return `null` via `_safe_compute`)
- `fight_id: Optional[int]` on `PredictionRequest` — links ad-hoc predictions to curated event context for `narrative_trap` tags, `chaos_scorer` short_notice/weight_miss signals, and `cinematic_title` generation
- `GET /events` — returns all manually curated events from `backend/events/events.json` (loaded once at startup into memory)
- `GET /events/{fight_id}` — returns the event context dict for a specific fight by `fight_id`; 404 if not found
- `GET /health` — readiness check: `SELECT 1` DB ping + model loaded → 200 `{"status":"ok"}`, 503 `{"status":"degraded"}` if either fails
- Sentry SDK initialisation (opt-in via `SENTRY_DSN` env var; no-op if unset)
- `backend/events/events.json` — sample UFC 309 event with 4 fights and narrative tags
- `sentry-sdk==2.19.2` added to `requirements.txt`
- 12 new tests in `tests/test_api_phase3.py` covering all Phase 3 codepaths — 237/237 total passing

### Changed
- `POST /predict`: fighter stats now served from `predictor.predict_fight()` result directly, eliminating 2 redundant `get_latest_fighter_stats()` DB queries per request; warns if stats are absent
- `POST /predict`: same-fighter input validation moved before `predictor`/`orchestrator` None checks (pure input validation needs no initialized state)
- `POST /predict` and `POST /generate-ai-poster`: added `except HTTPException: raise` guard so HTTP exceptions are never swallowed by the outer `except Exception` handler
- `determine_weight_class()` consolidated — removed duplicate inline definition in `get_fighter_profile()`; single module-level function used everywhere

### Fixed
- `tests/test_predictions_log.py`: added `orchestrator` mock to `client_with_db` fixture — previously failed with 500 after orchestrator global was added to `/predict`

## [0.1.7.0] - 2026-04-05

### Added
- `upset_alert.compute()` implemented (PRD §10.8): with-odds `UNDERDOG_EDGE` branch (dog model ≥ 0.45 AND reconstructed american ≥ +150 AND edge ≥ 0.08) + no-odds `MODEL_CONFIDENCE_NEAR_EVEN` fallback (0.45 ≤ dog_prob < 0.55)
- `sharp_money.compute()` implemented (PRD §10.9): queries `odds_history` for opening + latest snapshot, fires `MARKET_ALIGNMENT` when f1's implied line moves toward model with magnitude > 0.03, falls back to earliest row when `is_opening_line` flag is absent
- `cinematic_title.generate()` implemented (PRD §10.17): 18-template priority walk across chaos tier, DNA clash, nightmare, badges, false_consensus, upset edge, narratives, win paths, aura, veteran gap, and title-fight context; subtitle + weight-class color
- `_implied_to_american()` / `_payout_multiplier()` helpers in `upset_alert.py` (implied 0.40 → +150 exact)
- 44 new tests (12 `upset_alert`, 11 `sharp_money`, 21 `cinematic_title`) — 225/225 total passing

## [0.1.6.0] - 2026-04-04

### Added
- `upset_alert.py`: `UpsetResult` model + stubbed `compute()` wired into orchestrator and `IntelligenceResult` — awaiting Opus formula (PRD §10.8)
- `sharp_money.py`: `SharpMoneyResult` model + stubbed `compute()` wired into orchestrator and `IntelligenceResult` — awaiting Opus formula (PRD §10.9 line-movement detection)
- `cinematic_title.py`: `CinematicTitle` model + stubbed `generate()` wired into orchestrator — awaiting Opus formula (PRD §10.17 template system); includes `_WEIGHT_CLASS_COLORS` map
- `PerceptionGapResult`: `direction_f1`, `direction_f2` (OVERHYPED/ALIGNED/UNDERRATED), `magnitude` (LARGE/MODERATE/SMALL) fields for PRD §10.5 display spec
- `FalseConsensusResult`: `display_message` field + 4-label system (INVISIBLE_COINFLIP, FAKE_MISMATCH, PUBLIC_CERTAINTY_TRAP, MILD_OVERCONFIDENCE) replacing the previous 2-label set
- `ChaosResult`: `betting_implication` string field derived from tier
- `chaos_scorer.compute()`: `event_fight` optional parameter; `short_notice` (+8 pts) and `weight_miss` (+5 pts) flags now applied to score
- 7 new test cases: `weight_miss` chaos flag, `betting_implication` presence, `direction`/`magnitude` literals, `display_message` populated/empty, `direction_overhyped` end-to-end assertion
- TODOS 06–09: Fight DNA behavioral dimensions (v1.5), narrative per-trap model (v1.5), Card Temperature (Phase 3), CARD_BREAKER badge (v2 skip)

### Changed
- `ChaosResult.label` renamed to `ChaosResult.tier`; `MODERATE` tier renamed to `MIXED` to match PRD §10.6
- `IntelligenceResult` gains three new optional fields: `upset_alert`, `sharp_money`, `cinematic_title`
- `sharp_money` fallback: always returns `SharpMoneyResult(signal="NEUTRAL")` (never None) — mirrors `value_bet` sentinel pattern
- `_LARGE_THRESHOLD` local variable in `perception_gap.py` removed; reuses module-level `_STRONG_THRESHOLD`
- `false_consensus.py` comment updated: clarifies proxy threshold semantics vs PRD §10.14 market-gap thresholds
- All tests updated for `ChaosResult.tier` rename (test_chaos_scorer, test_models, test_badge_engine, test_false_consensus, test_orchestrator)

## [0.1.5.0] - 2026-04-04

### Added
- **Phase 2 Intelligence Engine — all 9 scoring formulas fully implemented** (174/174 tests passing)
- `chaos_scorer.py`: 6-signal weighted formula (finish rate 0-55, style clash 0-15, offensive output 0-10, chin issues 0-10, record volatility 0-10, streak dynamics 0-5) with weight-class multiplier (HW 1.30 → FLW 0.85) and symmetric style-clash matrix
- `perception_gap.py`: 5-component aura score heuristic (volume, finish rate, recency, win streak, win rate) driving perceived-vs-model probability delta; MODERATE (0.10) / STRONG (0.20) thresholds
- `narrative_trap.py`: tag-weighted risk scoring (HYPE_TRAIN, REVENGE_FIGHT, COMEBACK, SHORT_NOTICE, WEIGHT_MISS, TITLE_FIGHT) with trapped-fighter identification
- `value_bet.py`: half-Kelly criterion with FADE_OPPORTUNITY detection (market vs model direction disagreement) and STRONG_EDGE / EDGE_DETECTED / NO_EDGE signal classification
- `fight_dna.py`: 8-dimension fighter profiling (striking, grappling, wrestling, submission, pressure, chin, cardio, speed) with Euclidean clash intensity and collision-type labelling
- `false_consensus.py`: coinflip detection combining actual probability gap (<0.12) with chaos score (>=55) and model uncertainty
- `nightmare_matchup.py`: style-pattern matrix (STRIKER vs GRAPPLER → SEVERE, etc.) with data-volume guard downgrading severity when fight count < 3
- `win_path.py`: 7-path kill-chain labelling (EARLY_KO, GROUND_AND_POUND, SUBMISSION, TAKEDOWN_CONTROL, DECISION_VOLUME, DECISION_COUNTER, SPLIT_DECISION) with COUNTER-style boost and sub-threat modifier
- `badge_engine.py`: 11 SCIPHR badge rules wired to all module outputs (CHAOS_CERTIFIED, NARRATIVE_HOSTAGE, FALSE_FAVORITE, DOG_WITH_TEETH, FRAUD_CHECK, PUBLIC_TAX, ROUND_ONE_DEMON, DECISION_PRISONER, SILENT_KILLER, AURA_MERCHANT, CASUAL_MIRAGE) with fighter-name propagation from orchestrator

### Changed
- All 9 intelligence modules removed `raise NotImplementedError` stubs and their skip markers in tests
- `orchestrator.py`: passes `f1_name` / `f2_name` to `badge_engine.compute()` so per-fighter badges carry actual names rather than `"matchup"` placeholder
- `test_orchestrator.py`: renamed `test_all_stub_modules_return_none_in_result` → `test_all_modules_return_results` (formulas now return real results)

### Fixed
- `badge_engine.FALSE_FAVORITE`: reason string now picks `gap_f2` when F2 is the overvalued fighter (previously always formatted `gap_f1` regardless of direction)
- `badge_engine.ROUND_ONE_DEMON` / `DECISION_PRISONER` / `AURA_MERCHANT`: removed dead loop variables (`label_prefix`, `name`) and now assign the actual fighter name via the new `f1_name`/`f2_name` params

## [0.1.4.0] - 2026-04-03

### Added
- `backend/intelligence/` package: full Phase 2 Intelligence Engine scaffolding
  - `models.py`: Pydantic v2 models for all 9 module result types (`ChaosResult`, `PerceptionGapResult`, `NarrativeTrapResult`, `ValueBetResult`, `FightDNAResult`, `FalseConsensusResult`, `NightmareResult`, `WinPathResult`), `FighterContext` input model, `Badge`, `BADGE_META`, and `IntelligenceResult` bundle
  - `orchestrator.py`: `IntelligenceOrchestrator` — pre-loads fighter contexts (max 5 DB queries per `/predict`), runs all 9 modules via `_safe_compute` isolation, calls `badge_engine` via lambda in `_safe_compute` so a stub `NotImplementedError` never crashes the prediction response
  - `utils.py`: five pure utility functions shared across modules — `classify_style`, `finish_rate`, `win_streak`, `american_to_implied`, `kelly_fraction` (half-Kelly)
  - `narrative_trap.py`: `event_fight=None` and empty-narratives paths fully implemented (return `LOW` risk); tag scoring deferred to Opus
  - `value_bet.py`: `fight_id=None` and no-odds-rows paths fully implemented (return `NO_ODDS`); Kelly criterion calc deferred to Opus
  - `nightmare_matchup.py`: `classify_style()` call implemented; nightmare detection deferred to Opus
  - All remaining modules (`chaos_scorer`, `perception_gap`, `fight_dna`, `false_consensus`, `win_path`, `badge_engine`) scaffolded with detailed `TODO(opus)` formula briefs
- `backend/tests/`: full Phase 2 test suite (99 passing, 59 skipped Opus formula briefs)
  - `test_models.py` (30 tests): FighterContext validation, IntelligenceResult defaults, Badge Literal key enforcement, Field validator boundary checks
  - `test_utils.py` (34 tests): all 5 utility functions and all branches including critical edge cases
  - `test_orchestrator.py` (29 tests): `_safe_compute`, `_build_context` DB queries, `latest_features=NULL` warning, full orchestration with stubs
  - `test_narrative_trap.py`, `test_value_bet.py`, `test_badge_engine.py`: implemented-path tests + skipped formula briefs
  - `test_chaos_scorer.py`, `test_false_consensus.py`, `test_fight_dna.py`, `test_nightmare_matchup.py`, `test_perception_gap.py`, `test_win_path.py`: stub infrastructure test + skipped formula briefs
- `TODOS.md`: added TODO-03 (`scripts/fetch_odds.py`), TODO-04 (Odds API tier decision), TODO-05 (chaos weight back-test)

### Fixed
- `backend/intelligence/badge_engine.py`: replaced all-None short-circuit check with `_has_actionable_data()` gate that correctly treats `narrative.risk=="LOW"` and `value.active==False` as non-actionable, preventing `NotImplementedError` from propagating when narrative_trap returns a LOW-risk result for ad-hoc predictions
- `backend/intelligence/orchestrator.py`: removed unused `import json`; wrapped `badge_engine.compute()` in `_safe_compute` via lambda so any mid-build `NotImplementedError` (e.g. one module implemented before badge_engine) degrades to empty badges rather than crashing `/predict`

## [0.1.3.1] - 2026-04-02

### Fixed
- `main.py GET /fighters`: endpoint was reading from `predictor.available_fighters` (a list cached at server startup) — if the server started before the migration ran, the cache was empty and never refreshed; endpoint now queries the `fighters` table directly via `engine` on every request

### Changed
- `main.py GET /fighters`: added `Query(le=500)` ceiling on the `limit` parameter to prevent unbounded table scans from a single request
- `tests/test_fighters_endpoint.py`: updated module docstring to accurately describe the direct-DB-query behaviour (no longer references `predictor._build_fighter_list()`)

## [0.1.3.0] - 2026-04-02

### Fixed
- `migrate_csv.py`: silent migration failure caused by Supabase session pooler rolling back the entire insert as a single transaction — replaced with chunked inserts (100 rows/transaction) with explicit commit after each chunk

### Added
- `migrate_csv.py`: `--fighters-only` flag to upsert only the fighters table (reads CSV for feature data, skips fight inserts); useful for backfilling fighters when fights are already present
- `migrate_csv.py`: connection timeout retry logic — each chunk retried up to 3 times with exponential backoff (2s → 4s → 8s) on `OperationalError` / `DatabaseError`
- `migrate_csv.py`: progress logging every 500 rows (`fights ... 500 / 8231 rows submitted`)
- `tests/test_migrate_csv.py`: `test_fighters_only_skips_fights` — asserts fights table stays empty and fighters table is populated when `fighters_only=True`

## [0.1.2.0] - 2026-04-02

### Added
- `backend/db/models.py`: `EventFight` table — event_id FK, fighter1_name, fighter2_name, card_position, weight_class, is_title_fight, narratives (JSON list of narrative signal tags), short_notice, weight_miss, notes; used by Phase 2 Narrative Trap detector and Phase 3 events API
- `backend/db/models.py`: `NarrativeOutcome` table — tracks Narrative Trap prediction outcomes over time; feeds `/scorecard/narrative-traps` (Phase 4)
- `backend/db/models.py`: `predictions_log` intelligence signal columns — chaos_score, perception_gap, narrative_risk, value_signal, edge_pct, odds_at_prediction (JSON); all NULL until Phase 2 wires intelligence modules into /predict
- `backend/db/models.py`: `predictions_log` FK linkage — event_id → events, fight_id → event_fights; NULL until Phase 3 event data is populated
- `backend/db/models.py`: `predictions_log` post-fight resolution columns — actual_winner, was_correct, actual_method, actual_round, resolved_at; NULL until fight resolves; feeds Historical Scorecard (Phase 4)
- `backend/db/models.py`: `fighters` structural columns — nickname, style (STRIKER|WRESTLER|GRAPPLER|BRAWLER|COUNTER), is_active, photo_path; needed by Fighter Browser (Phase 4) and nightmare_matchup.py / win_path.py (Phase 2)
- `backend/db/models.py`: `fighters` Phase 2 computed score columns — aura_score, chaos_contribution, mirage_meter, composite_score, last_computed_at; NULL until intelligence modules run; defined now to avoid a migration mid-Phase 2
- `backend/db/models.py`: `fighters` audit columns — created_at, updated_at (server-side defaults)
- `backend/db/models.py`: `events` renamed columns (name→event_name, date→event_date) and added card_temperature, avg_chaos_score, is_published, created_at, updated_at
- `TODOS.md`: TODO-02 — two PRD text divergences flagged for next PRD revision (fights table column count §11, asyncpg→psycopg2 §15)

### Changed
- `backend/db/models.py`: `OddsHistory` restructured from per-event-pair to per-fighter-per-recording schema; added fighter_name, american_odds, implied_probability, is_opening_line; fight_id FK now points to event_fights (not events) for fight-level granularity required by Sharp Money Indicator
- `backend/scripts/migrate_csv.py`: Fighter upsert now explicitly sets updated_at=func.now() in on_conflict_do_update set_ dict — SQLAlchemy's onupdate= event does not fire for Core SQL upserts

## [0.1.1.0] - 2026-04-02

### Added
- `backend/db/models.py`: SQLAlchemy models for all 5 tables — `fighters`, `fights`, `predictions_log`, `events`, `odds_history`; uses `BigInteger().with_variant(Integer, "sqlite")` for cross-DB PK compatibility; JSON type (not dialect JSONB) for SQLite test compatibility
- `backend/scripts/migrate_csv.py`: One-time CSV → PostgreSQL migration script; loads 380MB golden CSV, sorts by date ascending so latest fight overwrites earlier, pre-normalizes all features to canonical `r_*` form regardless of corner assignment, dialect-aware ON CONFLICT (SQLite/PostgreSQL), idempotent re-runs
- `backend/db/__init__.py`, `backend/scripts/__init__.py`: Package init files
- `src/golden_feature_calculator.py`: Fully rewritten — CSV/pandas loading replaced with two indexed DB queries per prediction; `get_latest_fighter_stats()` maps DB columns to original CSV key names; `build_full_feature_vector()` fetches fighter1 directly (canonical `r_*`), remaps fighter2 (`r_*→b_*`), computes `diff_*` features, assembles 5,401-element vector; `_parse_json()` helper handles SQLite string vs PostgreSQL dict return
- `src/predictor_golden.py`: `__init__` accepts `engine` parameter instead of `data_path`; `_build_fighter_list()` queries `SELECT name FROM fighters` instead of reading CSV
- `backend/main.py`: Startup event connects to PostgreSQL via `DATABASE_URL` env var with `SELECT 1` health check; predictor initialized with DB engine; every `/predict` success inserts a row into `predictions_log` (try/except — non-fatal)
- `backend/requirements.txt`: Added `psycopg2-binary==2.9.10` and `SQLAlchemy==2.0.41`
- `backend/tests/conftest.py`: Shared SQLite in-memory fixture with `StaticPool` + `check_same_thread=False` for FastAPI threadpool compatibility
- `backend/tests/test_feature_calculator.py`: 7 integration tests for `GoldenFeatureCalculator` — stats mapping, missing fighter, `r_*` direct / `b_*` remap, suffix remap, mutual-exclusion warning, `diff_*` computation
- `backend/tests/test_migrate_csv.py`: 4 integration tests — NaN→0.0, latest-fight-wins, idempotency, `was_red=False` canonical remapping
- `backend/tests/test_fighters_endpoint.py`: 2 tests — `/fighters` returns DB-sourced names, empty DB returns `[]` without crash
- `backend/tests/test_predictions_log.py`: 1 test — successful `/predict` inserts exactly one `predictions_log` row
- `TODOS.md`: TODO-01 — Alembic setup before Phase 6 deploy

### Changed
- `backend/.env.example`: `DATABASE_URL` corrected from `asyncpg` to `psycopg2` driver scheme
- `backend/main.py`: Removed unused `from sqlalchemy.orm import Session` import
- `backend/scripts/migrate_csv.py`: Added `# mirrors main.py determine_weight_class` comment on `_weight_class()` threshold duplication
- `STATUS.md`: Phase 1 marked 🟡 In Progress; decisions log updated with 4 new entries; test coverage updated (21/21); next 3 tasks updated to Supabase migration steps

## [0.1.0.2] - 2026-04-02

### Fixed
- `main.py`: Lock down CORS — `allow_methods` → `["GET", "POST"]`, `allow_headers` → `["Content-Type"]`, `allow_credentials` → `False` per PRD §14 security requirements
- `FightPoster.jsx`: Replace two `alert()` calls with inline `aiPosterError` state — error clears on retry, renders in-component instead of browser dialog
- `backend/.env.example`: Created — documents all required env vars and explicitly calls out both credentials that must be rotated (Gemini API key + Google service account are separate)

### Changed
- `STATUS.md`: Next 3 Tasks updated to Phase 1 items (schema, migration script, backend wiring); stale `git init` task removed; 3 audit gaps added to P0 bug tracker

## [0.1.0.1] - 2026-04-01

### Fixed
- `main.py`: Replace `request: dict` on `/detailed-stats` with `DetailedStatsRequest` Pydantic model — missing fields now return 422 instead of silently passing `None` to the predictor
- `main.py`: CORS `allow_origins` now read from `ALLOWED_ORIGINS` env var (comma-separated); falls back to localhost for dev — fixes prod deploy blocker
- `gemini_service.py`: Remove unused `import base64`
- `ai_analyst.py`: Remove dead `prob_f1`/`prob_f2` variables from `generate_fight_analysis` (prompt using them is never sent until Phase 5)

## [0.1.0.0] - 2026-04-01

### Added
- `.gitignore` excluding credentials, CSVs, model pkl, venv, pycache
- `backend/requirements.txt` fully populated from pip freeze (80 packages incl. slowapi, anthropic)
- `backend/tests/test_p0.py` — 7 regression tests: same-fighter guard (4 cases), rate limit 429, ai_analyst NameError fix (favorite + underdog paths)
- `backend/tests/__init__.py`
- `VERSION` and `CHANGELOG.md`

### Fixed
- `ai_analyst.py`: NameError — `analysis['implied_odds']` assigned before `analysis` dict was defined; moved into dict literal
- `main.py`: Duplicate `generate_recent_record` definition removed (first shadowed by second)
- `main.py`: Dead code block after `return` in `get_fighter_profile` deleted (~36 lines)
- `main.py`: Dead `get_recent_results()` function removed (called non-existent `predictor.get_fighter_data()`)
- `main.py /predict`: Same-fighter validation added (HTTP 400, case+whitespace insensitive)
- `main.py /generate-ai-poster`: slowapi rate limiter added (3/hr/IP, in-memory; Redis deferred to Phase 6)
- `gemini_service.py`: Credential check moved from module level to inside `generate_ai_poster()` — server no longer crashes on startup without `.env`
- `frontend/src/api/api.js`: `VITE_API_URL` guard — throws in production if unset, warns + falls back in dev
- `frontend/.../AnalystMode.jsx`: Wired through `api.js`; removed `fighter.stats.nickname` references (field absent from backend)
- `frontend/.../FightPoster.jsx`: Wired through `api.js`
- `frontend/.../PicksBuilder.jsx`: Wired through `api.js`
- `frontend/.../HeroFightCard.jsx`: Fixed JSX className template literal (double-quote → backtick)

### Changed
- Frontend restructured: `frontend-redesign/sciphr-redesign/frontend-redesign/` moved to `frontend/`; old v1 frontend deleted
- `fastapi` upgraded `0.104.1` → `0.135.3` (starlette 0.27 incompatible with httpx 0.28 in venv)
