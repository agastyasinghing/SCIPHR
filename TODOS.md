# SCIPHR — TODOS

Items considered and explicitly deferred. Each entry has enough context to
be actionable in 3 months without re-deriving the motivation.

---

## TODO-01 — Alembic migration versioning

**What:** Set up Alembic for schema version control in `backend/db/migrations/`.

**Why:** Phase 1 uses `Base.metadata.create_all(engine)` to create the schema,
which cannot be rolled back and can't be incrementally applied to an existing
database. Before the Phase 6 Supabase production deploy, any schema change
(adding a column, adding an index) requires manual SQL or wiping the DB.

**Pros:**
- Schema changes are versioned, reviewable, and reversible.
- `alembic upgrade head` is a single command for deploy pipelines.
- Supabase has Alembic integration guides that make Phase 6 deploy cleaner.

**Cons:**
- ~30 min of setup: `alembic init`, edit `env.py` to import `Base`, generate
  initial migration with `alembic revision --autogenerate -m "Phase 1 schema"`.
- Adds `alembic` to requirements.txt.

**Current state:** Schema defined in `backend/db/models.py`. Tables are
created by `backend/scripts/migrate_csv.py` via `create_all()`. Migration
files directory `backend/db/migrations/` doesn't exist yet.

**Where to start:**
```
cd backend
pip install alembic
alembic init db/migrations
# Edit db/migrations/env.py to import Base from db.models
alembic revision --autogenerate -m "Phase 1 initial schema"
alembic upgrade head
```

**Depends on / blocked by:** Nothing. Can be done any time after Phase 1.
Should be done before Phase 6 deploy.

---

## TODO-03 — scripts/fetch_odds.py (Odds API fetch script)

**What:** Script that calls The Odds API and writes snapshots to `odds_history`
for a given event's fights.

**Why:** `value_bet.py` reads from `odds_history` only — it never calls The Odds
API at predict time. Without this script, `value_bet` always returns `NO_ODDS`
for all predictions, making the Line Crack / Edge Detected signal permanently dark.

**Inputs (CLI args):**
  `--event-id INT`   fetch odds for all event_fights rows on this event
  `--fight-id INT`   fetch odds for one specific fight

**How:**
  GET `/v4/sports/mma_mixed_martial_arts/odds/` from The Odds API
  Map bookmaker lines to `odds_history` rows (one row per fighter per call)
  Mark first snapshot as `is_opening_line=True`
  Subsequent runs create new rows (intentional — line movement tracking)

**When to run:** Fight week (Mon–Fri before the event).
  Can be run multiple times to capture line movement.
  500 req/mo free tier budget is spent here, not at predict time.

**Depends on / blocked by:**
  Phase 2 `value_bet.py` formula complete (Opus)
  `ODDS_API_KEY` in `backend/.env`
  `event_fights` rows seeded for the event (Phase 3)

---

## TODO-04 — Resolve OQ-01: The Odds API free tier vs. paid

**What:** Decide whether to use The Odds API free tier (500 req/mo) or upgrade
to a paid plan before launch.

**Why:** 500 req/mo at 2 requests per event fight (opening + fight-week) supports
roughly 250 fights/month. UFC runs ~12 events/month × ~12 fights = ~144 fight
requests per month, leaving room. But if `scripts/fetch_odds.py` is run multiple
times per fight for line movement, the budget depletes quickly.

**Decision needed before:** Phase 3 `scripts/fetch_odds.py` is built.
See open question OQ-01 in CLAUDE.md.

---

## TODO-05 — Validate Chaos Score weights against historical upset rates (OQ-12)

**What:** Back-test `chaos_scorer` weights against historical upset rates in the
`fights` table after the formula is implemented.

**Why:** If chaos score weights are uncalibrated, `CHAOS_CERTIFIED` badge fires on
predictable fights and misses genuine coinflips — destroying SCIPHR's core
credibility. This is the validation gate before Phase 3 wiring.

**Acceptance criterion:**
  Fights scored HIGH/EXTREME chaos should show higher historical upset rates than
  LOW/MODERATE chaos fights. Target buckets (Opus to refine):
    LOW chaos    → model upset rate ~10–15%
    HIGH chaos   → model upset rate ~35–45%
    EXTREME chaos→ model upset rate ~45–50%

**How:** After `chaos_scorer.py` formula is implemented (Opus session):
  Run `compute()` on all historical fight pairs in the `fights` table.
  Bucket by label. Compare `actual_winner != predicted_winner` rate per bucket.

**Depends on / blocked by:**
  `chaos_scorer.py` formula complete (Opus)
  Phase 1 migration run (need fights in DB)

**Where to start:** `backend/scripts/validate_chaos_weights.py` (new file)

---

## TODO-02 — PRD text divergences (update PRD before v2 planning)

Two deliberate architectural decisions diverge from the PRD text. Both are
documented in STATUS.md Decisions Log but the PRD itself is not yet updated.
Flag these in the next PRD revision session to avoid confusing future contributors.

**Divergence A — fights table column count (PRD §11)**
PRD §11 says: "faithful migration of all 5,401 columns."
Actual design: `fights` table stores only 6 metadata columns (r_name, b_name,
date, winner, method, weight_class). Features live as JSONB on
`fighters.latest_features` instead.
Reason: per-fight JSONB would be ~912MB, exceeding Supabase free tier (500MB).
Per-fighter JSONB is ~85MB.

**Divergence B — ORM driver (PRD §15)**
PRD §15 says: "SQLAlchemy + asyncpg."
Actual implementation: sync SQLAlchemy + psycopg2.
Reason: the XGBoost prediction pipeline is synchronous Python; FastAPI
threadpools sync DB calls automatically. asyncpg would require rewriting the
entire predictor_golden.py call chain as async — not worth it for v1 throughput.

**Where to fix:** `SCIPHR_PRD_v1.1.md` §11 (Migration Strategy paragraph) and
§15 (Backend table, Database ORM row).

---

## TODO-06 — Fight DNA dimension names: behavioral vs statistical (v1.5)

**What:** PRD §10.13 specifies 7 behavioral/tactical dimensions for Fight DNA:
`patience_vs_chaos`, `pressure_vs_counter`, `finish_urgency`, `collapse_risk`,
`early_vs_late_danger`, `stylistic_rigidity`, `scramble_comfort`.

Built implementation uses 8 statistical output dimensions: `striking`, `grappling`,
`wrestling`, `submission`, `pressure`, `chin`, `cardio`, `speed`.

**Why this matters (brand/UX):**
PRD dimensions are meant to be instantly legible to a casual fan ("patience vs chaos"
is a fight concept; "striking" is just a stat). The visual DNA strand described in PRD
§10.13 depends on behavioral labels to be screenshot-worthy. "0.7 scramble_comfort"
conveys something; "0.7 grappling" does not.

**Why deferred:**
The 8 statistical dimensions are accurate and derivable today. The behavioral mapping
(e.g. deriving "stylistic_rigidity" from the dataset) requires either manual calibration
against historical fights or a short Opus session to define the heuristics.
v1 ships with statistical dims; frontend component can be designed around either.

**Where to start:** `backend/intelligence/fight_dna.py` — replace/rename the 8 dimensions
using behavioral heuristics derived from the same underlying stats (e.g.
`patience_vs_chaos = 1 - (slpm_norm * 0.6 + ko_rate * 0.4)` as a rough proxy).
Also update `FightDNAResult.f1_dna/f2_dna` dict keys and the frontend component.

**Depends on:** Phase 4 frontend Fight DNA component (design the visual first,
then calibrate dimension names to match what the component renders).

---

## TODO-07 — Narrative per-trap detail model (v1.5)

**What:** PRD §10.7 specifies a `NarrativeTrap` Pydantic model per detected narrative
with fields: `narrative`, `description`, `is_trap`, `base_rate`, `trap_message`.
Built `NarrativeTrapResult.active_traps` is just a `list[str]` of tag names —
no per-trap detail, no base rate, no is_trap flag per tag.

**Why this matters:**
The Historical Scorecard (§10.10) is supposed to show "Flagged narratives: Hyped fighter
won 44% — below base rate ✓" and "Narrative Trap calls accurate: 61% of the time."
This requires per-trap `base_rate` to compute. Without it, narrative performance
tracking on the scorecard is impossible.

**Why deferred:**
v1 narrative tags are manually curated (no NLP). Per-trap base rates require
historical validation against the fights dataset (an Opus session to derive).

**Where to start:** Add `NarrativeTrap` Pydantic model to `intelligence/models.py`,
update `NarrativeTrapResult.active_traps: list[str]` → `traps: list[NarrativeTrap]`,
populate `base_rate` from a lookup table calibrated against the fights table.
Also update `narrative_outcomes` table inserts to store per-trap data.

**Depends on:** Phase 1 migration (need fights in DB to compute base rates),
Opus session for historical base rate calibration.

---

## TODO-08 — Card Temperature calculation (Phase 3 dashboard)

**What:** PRD §10.6 specifies a `card_temperature()` function that derives
`CardTemperature` (CHALK/MIXED/CHAOS/DOG) from per-fight chaos scores across
a full event card. The `events.card_temperature` column exists in the DB schema
but nothing populates it.

**Why this matters:** The Dashboard (§10.3) displays Card Temperature as the event's
headline signal. It's also used to drive the Card Temperature badge and fight week
content framing.

**Where to build:** Add `card_temperature()` to `intelligence/chaos_scorer.py`
(it directly consumes chaos scores) and call it from a Phase 3 endpoint or a
fight-week admin script that populates `events.card_temperature` after all fights
are scored.

**Implementation note:** PRD §10.6 derivation:
```python
avg_chaos = mean(chaos_score for each fight on card)
high_chaos_count = count(fights with chaos_score >= 55)  # HIGH tier (0-100 scale)
if avg_chaos >= 70: label = "CHAOS CARD"
elif avg_chaos >= 50: label = "MIXED CARD"
elif high_chaos_count >= 3: label = "DOG CARD"
else: label = "CHALK CARD"
```

**Depends on:** Phase 3 API Layer (events endpoints), all fight chaos scores computed.

---

## TODO-09 — CARD_BREAKER badge (v2 skip)

**What:** PRD §10.16 defines the `CARD_BREAKER` badge: "Fighter's presence reliably
shifts the entire card's dynamics." Trigger: `name_recognition_tier == ELITE and
fan_base_size == LARGE`.

**Why skipped:** Both `name_recognition_tier` and `fan_base_size` are fields that
require external data (social following, pay-per-view numbers, media coverage) not
present in the dataset. No proxy derivable from existing stats is reliable enough
to be on-brand.

**v2 path:** Wire to a manually curated `elite_fighters` lookup table or add a
`is_elite` boolean to the `fighters` table that the operator maintains. Could also
be derived from betting line history (fighters who consistently command -200 or
better lines across 10+ fights).

**Status:** Badge key not registered in `models.py` BadgeKey Literal (intentional —
prevents accidental assignment). Add it back when data source is available.

---

## TODO-10 — /historical-scorecard endpoint + data seeding

**What:** Design and build the `/historical-scorecard` API endpoint and the
script that seeds `predictions_log` with retroactive model predictions against
historical fight outcomes.

**Why:** The scorecard page requires data — without seeding, it launches empty.
OQ-11 is unresolved: do we run the model retrospectively against the dataset?
If yes, each seeded row needs a `winner_actual` field to score accuracy.
`predictions_log` currently only stores predictions, not actuals.

**Pros:**
- Enables the Historical Scorecard page to display model accuracy at launch.
- Provides social proof ("the model called 72% of fights correctly").
- Drives the `narrative_outcomes` and `badge_outcomes` tracking from PRD §10.10.

**Cons:**
- Requires schema change: add `winner_actual` and `fight_date` to `predictions_log`.
- Retroactive seeding script must run the predictor against 8,000+ historical fights —
  slow and may surface edge cases in the feature pipeline.
- Accuracy metric needs careful definition (model prediction == actual winner, or
  probability calibration?).

**Current state:** `predictions_log` table exists (`backend/db/models.py`). Phase 3
wires `/predict` to insert live predictions. No historical rows. No seeding script.
`predictions_log` schema has no `winner_actual` column.

**Where to start:**
1. Add `winner_actual` and `fight_date` columns to `predictions_log` in `db/models.py`.
2. Write `backend/scripts/seed_scorecard.py` — iterate `fights` table, call
   `predictor.predict_fight(r_name, b_name)`, insert row with `winner_actual=winner`.
3. Build `GET /historical-scorecard` endpoint that reads from `predictions_log`
   grouped by month with accuracy metrics.
4. Design the frontend scorecard page in Phase 4 around this schema.

**Depends on / blocked by:** Phase 1 migration run (need fights in DB), Phase 4
frontend page design, Alembic setup (TODO-01) for the schema migration.

---

## TODO-11 — Structured logging in main.py

**What:** Replace ~15 `print()` debug statements in `main.py` with
`logging.getLogger(__name__)` calls at appropriate levels.

**Why:** In production (Railway), structured logs are filterable by level.
`print()` always emits to stdout regardless of log level. Setting
`LOG_LEVEL=WARNING` in prod is currently meaningless — all print statements fire.

**Pros:**
- `LOG_LEVEL=WARNING` silences debug noise in production.
- Consistent with `intelligence/` modules which already use `logging`.
- Structured log lines are easier to parse in Railway's log viewer.

**Cons:**
- Low-urgency cosmetic cleanup. No functional change.
- ~30 min of mechanical work across `/predict`, `/generate-ai-poster`,
  `/detailed-stats` handlers.

**Current state:** All debug output in `main.py` uses `print()`. The
`intelligence/orchestrator.py` and all intelligence modules already use
`logging.getLogger(__name__)` correctly. `main.py` is the outlier.

**Where to start:**
Add `log = logging.getLogger(__name__)` at the top of `main.py`.
Replace `print(f"PREDICTION REQUEST: ...")` with `log.info(...)`,
verbose traces with `log.debug(...)`, and error blocks with `log.error(...)`.

**Depends on:** Nothing. Standalone cleanup pass.

---

## TODO-12 — /health response field names (fix before deploy)

**What:** `/health` currently returns `{status, db, model}`.
PRD §13 specifies `{status, model_loaded, db_connected, version}`.

**Why deferred:** Field names are cosmetic and no frontend code depends on them yet.
Renaming before frontend is wired avoids breaking the health check once it's used.

**Where to fix:** `main.py` `health_check()` function.
Rename: `db` → `db_connected`, `model` → `model_loaded`.
Add: `version` field populated from `os.getenv("APP_VERSION", "unknown")`.

**Depends on:** Nothing. Fix before Phase 6 deploy.

---

## TODO-13 — Parallel intelligence orchestrator (v2)

**What:** `IntelligenceOrchestrator.compute()` runs all 11 modules sequentially.
PRD §9 event flow step 6 specifies "Intelligence Engine runs in parallel."

**Why deferred:** Sequential execution is well within the <600ms latency budget
for v1 traffic volumes. Parallelism adds complexity (ThreadPoolExecutor or
asyncio.gather with sync-to-async wrapping) for minimal gain at v1 scale.

**Where to start:** In `intelligence/orchestrator.py`, replace the sequential
`_safe_compute()` calls with `concurrent.futures.ThreadPoolExecutor` or convert
orchestrator to async and use `asyncio.gather(*[asyncio.to_thread(_safe_compute, m) for m in modules])`.
Run the 5 DB queries first (they must precede module calls), then fan out.

**Depends on:** Phase 6 load testing to confirm whether latency budget is actually
exceeded at realistic concurrency. Don't do this speculatively.

---

## TODO-14 — Frontend test coverage expansion (Phase 5+)

**What:** Extend the vitest + @testing-library/react test scaffold (built in Phase 4)
to cover Phase 5 components: AI poster error states, `generate-ai-analysis` loading
and polling behavior, and the Claude analysis render panel.

**Why:** Phase 4 established the test pattern (vitest + jsdom + @testing-library).
Phase 5 adds async Claude analysis state (loading → rendered) and the AI poster
generation flow — both have non-obvious failure modes (rate-limit 429, timeout,
template fallback). Without tests, these are first discovered in production.

**Pros:**
- Catches null-safety bugs in Claude analysis render (`ai_analysis` is null by default,
  populated async via a second API call — easy to forget the null guard).
- Rate-limit 429 on `/generate-ai-poster` needs a test: currently shows `aiPosterError`
  inline state but the specific 429 message should differ from a generic 500.

**Cons:**
- Phase 5 async polling tests require `vi.useFakeTimers()` — slightly more setup.

**Current state:** Phase 4 test scaffold in `frontend/src/__tests__/`.
Setup in `frontend/vite.config.js` (vitest + jsdom).
Test script: `npm run test` in `frontend/`.

**Where to start:**
```
frontend/src/__tests__/FightPoster.test.jsx   — add 429 rate-limit error test
frontend/src/__tests__/AnalystMode.test.jsx   — add Claude analysis render test
frontend/src/__tests__/AIAnalysis.test.jsx    — new: polling + timeout + fallback
```

**Depends on / blocked by:** Phase 5 build (need the components to exist first).

---

## TODO-15 — Phase 4 PRD Audit: Deferred v2 gaps

These gaps were identified in the Phase 4 PRD audit and explicitly deferred.
Fixed gaps (P1/P2/P3) are tracked in git history.

### v2 (post-auth, post-launch)

**Gap 7 — Analyst Mode: historical perception gap profiles**
PRD §10.2 asks for "Historical performance of fighters with similar perception gap profiles."
Requires: aggregate `predictions_log` after it has been seeded with 100+ entries.
`predictions_log.perception_gap` column exists — query is straightforward once data exists.
Where: new `/fighter/{name}/similar-gap-history` endpoint + AnalystMode panel.

**Gap 8 — Analyst Mode: Narrative Trap per-trap base rates**
PRD §10.2 asks for "Statistical backing score for each narrative (strong/weak/trap)" and
"Historical base rate for this narrative type." Blocked by TODO-07 (NarrativeTrapResult
still uses `active_traps: list[str]`, not `list[NarrativeTrap]` with base_rate).
Fix TODO-07 first, then update AnalystMode IntelligenceSection to show per-trap detail.

**Gap 9 — Analyst Mode: Win Path round-range breakdown**
PRD §10.2 asks for "Which round range the fight is most likely to end in."
`WinPathResult` has no round distribution field. Requires extending the win_path module
with round probability buckets (R1, R1-2, R2-3, R3+) — Opus session needed.
Where: `backend/intelligence/win_path.py` + `WinPathResult.round_distribution: dict`.

**Gap 10 — Analyst Mode: Style collision advantage display**
PRD §10.2 asks for "Style collision: where each fighter has advantage (striking range,
clinch, takedown, top control, cardio)." Fight DNA shows dimensions but not the per-zone
advantage format. Implement after TODO-06 (behavioral DNA dimensions) is resolved.

**Gap 11 — Analyst Mode: Sportsbook odds in Value Bet panel**
PRD §10.2 asks for "Current sportsbook odds (The Odds API)" and "Implied probability vs
model probability" in the Value Bet panel. Currently blocked by TODO-03 (fetch_odds.py
not built). Once odds pipeline is live, `ValueBetResult.implied_prob_f1/f2` have the data.
Just display them in the Line Crack panel alongside signal + edge_pct.

**Gap 12 — Value Bet panel: Kelly only shows when odds present**
PRD §10.2 puts Kelly-equivalent bet sizing in the Prediction confidence panel for all
fights. Currently only shown when `vb.signal !== 'NO_ODDS'`. Post-odds-pipeline, remove
the conditional and always show Kelly when confidence is meaningful.

**Gap 15 — Fighter browser: Aura score, Composite score on cards**
PRD §10.4 lists SCIPHR composite score and aura score on fighter profiles. Intelligence
scores are now computed on-the-fly at profile load. For the fighter browser cards, add
these scores once the batch scoring job (nightly refresh) populates `fighters.composite_score`
and `fighters.aura_score` in the DB — avoids N profile fetches on the list page.

**Gap 19 — News ticker: real fight-week content from events.json**
PRD §10.3 asks for manually curated fight-week updates tagged INJURY / WEIGHT MISS /
LATE REPLACEMENT / CAMP NEWS. Currently hardcoded placeholder text.
Schema: add a `news_items: [{text, tag, date}]` array to events.json.
Frontend: parse and render with per-tag color coding in the ticker.

---

### Post-launch (after predictions_log is seeded via TODO-10)

**Gaps 28-31 — Historical Scorecard full breakdown**

All four scorecard depth gaps are blocked by `predictions_log` being empty at launch.

**Gap 28 — Breakdown stats (main card, favorites, underdogs, edge-detected)**
PRD shows overall/main-card/favorites/underdogs/edge-detected accuracy tiers.
Backend: extend `/historical-scorecard` to GROUP BY `is_main_card`, `confidence >= 0.65`,
`value_signal`. Frontend: add breakdown stat cards above the predictions table.

**Gap 29 — Value Bet ROI tracking**
PRD shows ROI per signal tier (Edge Detected +12.4%, Strong Edge +18.7%).
Requires: `odds_at_prediction` populated (currently only when odds pipeline is live) +
`actual_winner` resolved post-fight. Backend: add ROI computation to scorecard endpoint.

**Gap 30 — Narrative Trap performance section**
PRD shows "Flagged narratives: Hyped fighter won 44% — below base rate ✓".
Requires: `narrative_outcomes` table populated post-fight (via admin tool).
Also blocked by TODO-07 (per-trap NarrativeTrap model with base_rate).

**Gap 31 — Event grouping in predictions table**
PRD mockup groups predictions under event headers (e.g., "UFC 317 · April 12 2026").
Requires: `event_id` FK on `predictions_log` populated at predict time (currently NULL
for ad-hoc predictions). Backend: JOIN predictions_log → events to group by event.
Frontend: render collapsible event sections in the table.

---

## TODO-16 — Standardise `/events/upcoming` and `/events/past` response shapes

**What:** `/events/upcoming` returns a single event object `{}`. `/events/past` returns
`{events: [...]}`. Dashboard normalises with `upcomingRes?.events ?? (upcomingRes ? [upcomingRes] : [])`.

**Why:** If `/events/upcoming` is ever refactored to return multiple upcoming events
(e.g., next two cards), the shape mismatch will silently break the normalisation.

**Fix:** Change `/events/upcoming` to return `{events: [event]}` — single-element array —
matching the `/events/past` shape. Update Dashboard.jsx to remove the normalisation shim
and always use `res.events`.

**Where:** `backend/main.py` `/events/upcoming` handler + `frontend/src/pages/Dashboard.jsx`.
**When:** Before Phase 6 deploy or when the upcoming-events query changes.

---

## TODO-17 — Extract UpsetWatchFeed to its own component file

**What:** `UpsetWatchFeed` is defined inline inside `Dashboard.jsx`.

**Why:** Inline component definitions prevent independent unit testing and reuse
(e.g., embedding on the HeroFightCard or a standalone page).

**Fix:** Move to `frontend/src/components/dashboard/UpsetWatchFeed.jsx` + matching
`UpsetWatchFeed.css` (extract relevant `.upset-watch-*` rules from `Dashboard.css`).
Import it back into Dashboard.jsx. No functional change.

**When:** Before writing Phase 5/6 tests for the dashboard components (see TODO-14).

---

## TODO-18 — Document `card_temperature` field schema in events.json

**What:** `HeroFightCard` reads `event.card_temperature` to render the Card Temperature badge.
The field is absent from most events — the badge silently hides. No in-repo documentation
tells the operator which values are valid.

**Why:** Without documentation, the operator populating events.json each fight week has
no way to know the accepted values or their display meaning.

**Fix:** Add a `_schema` comment block at the top of `backend/events/events.json` (or a
companion `backend/events/events.schema.json`) documenting:
```
card_temperature: "CHALK CARD" | "MIXED CARD" | "CHAOS CARD" | "DOG CARD"
  CHALK CARD  — heavy-favourite-dominated card (green badge)
  MIXED CARD  — balanced chalk/dog card (amber badge)
  CHAOS CARD  — multiple live dogs, volatile card (red badge)
  DOG CARD    — underdog-heavy card, upset potential (orange badge)
```
**When:** Before Phase 6 / operator handoff documentation pass.

---

## TODO-19 — Wire actual Claude API in ai_analyst.py (post-launch)

**What:** Replace the always-template path in `generate_fight_analysis()` with a real
`anthropic.Anthropic().messages.create()` call when `ANTHROPIC_API_KEY` is set,
falling back to `_generate_template_analysis()` on any exception.

**Why:** The full prompt is already built (`ai_analyst.py:35–70`) — it feeds fighter stats,
records, and the XGBoost prediction into a structured analyst prompt. The only thing
missing is the actual API call. Template output is solid for v1 launch; Claude analysis
would add narrative depth and more contextual betting guidance.

**Pros:**
- Prompt is already written and tested against template output — minimal new work.
- Template fallback means Claude failure is invisible to users.
- Differentiates SCIPHR's "AI analyst" framing from a pure stats tool.

**Cons:**
- API cost per analysis call (~$0.005–0.02 depending on model).
- Adds ~1–3s latency to `/generate-ai-analysis` (already async via `asyncio.to_thread`).
- Requires `ANTHROPIC_API_KEY` in production environment.

**Implementation (ai_analyst.py):**
```python
import anthropic

def generate_fight_analysis(self, prediction_data):
    prompt = self._build_prompt(prediction_data)  # extract existing prompt build
    try:
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",  # fast + cheap for structured output
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        return self._parse_claude_response(message.content[0].text, prediction_data)
    except Exception:
        return self._generate_template_analysis(prediction_data)
```

**Current state:** `ai_analyst.py` builds the prompt at line 35 then immediately calls
`_generate_template_analysis()` at line 74. Template fallback exists and is well-tested.
`ANTHROPIC_API_KEY` is in `.env.example` as a commented-out optional field.

**Where to start:** `backend/ai_analyst.py` — extract prompt build to `_build_prompt()`,
add `anthropic` import, wrap API call in try/except → template fallback.

**Depends on / blocked by:** Nothing. Standalone. Do after v1 paper launch confirms
template output quality is insufficient for users.

---

## TODO-20 — Rate limit visibility for /generate-ai-analysis

**What:** Show the user how many AI analysis calls remain before hitting the 3/hr rate
limit, matching the `aiGenerationsLeft` counter already on the AI poster in `FightPoster.jsx`.

**Why:** Users hit 429 with no warning — the error message appears only after the limit is
reached. The poster already sets user expectations ("1 left") before they run out.

**Pros:**
- UX parity with the AI poster flow.
- Reduces surprise 429 errors.

**Cons:**
- The rate limit is IP-based on the backend (slowapi). There is no API endpoint to query
  remaining quota — we'd have to track client-side in state (optimistic counter), which
  can drift if the user has multiple tabs open or reloads.
- 3/hr is generous enough that most users won't hit it.

**Implementation:** Add `aiAnalysisLeft` state (init: 1) to `AnalystMode.jsx`.
Decrement on successful `generateAIAnalysis()` call. Show "X remaining" copy near the
AI Analysis panel. Pattern: `FightPoster.jsx` lines 28, 91 (aiGenerationsLeft).

**Depends on / blocked by:** Phase 5 AI analysis wiring (TODO-20 builds on top of it).
Consider doing this at the same time as TODO-19 (Claude wiring) since that's when
per-call cost makes quota visibility matter most.
