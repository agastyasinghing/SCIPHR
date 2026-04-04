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
