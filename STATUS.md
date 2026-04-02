# SCIPHR — Status
**Last Updated:** April 2026 | **Current Phase:** Phase 1 — Database Migration

---

## Phase Progress

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — P0 Bugs + Git Setup | ✅ Complete | All 13 bugs fixed, 7/7 tests passing |
| Phase 1 — Database Migration | 🟡 In Progress | CSV → PostgreSQL |
| Phase 2 — Intelligence Engine | 🔴 Not Started | All scoring modules |
| Phase 3 — API Layer | 🔴 Not Started | Wire intelligence to FastAPI |
| Phase 4 — Frontend Wiring | 🔴 Not Started | api.js + UI components |
| Phase 5 — Claude + Poster | 🔴 Not Started | AI analysis + poster |
| Phase 6 — Deploy | 🔴 Not Started | Vercel + Railway + Supabase |

---

## Current State
**What exists:** FastAPI backend + React v2 frontend (moved to frontend/). XGBoost model working at 85.7% accuracy. Core prediction endpoint functional. Fighter search working. All P0 bugs fixed.

**What is broken:** Nothing critical. See user actions required below.

**What is fake:** Dashboard data 100% hardcoded. Fight history randomly generated. Model performance metrics hardcoded.

**What is missing:** Database, real events data, all intelligence modules, deployment config.

---

## User Actions Required (cannot be automated)
- **Rotate Google service account key** — `backend/service_account.json` was unprotected before .gitignore was added. Treat as compromised.
- **Create `backend/.env`** from `.env.example` with new credentials: `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT_ID`

---

## In Progress
Phase 1 — Database Migration (code complete, awaiting migration run against real Supabase DB).

---

## Next 3 Tasks
1. Create Supabase project + get DATABASE_URL → add to `backend/.env`
2. Run `cd backend && python scripts/migrate_csv.py --csv ../data/golden_full_converted.csv`
3. Smoke-test: start backend, hit /fighters and /predict, verify predictions_log row appears in Supabase

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

---

## Notes for Next Session
- Phase 1 code is complete. Next step is running the migration against a real Supabase DB.
- Create Supabase project → Settings → Database → Connection string → add to `backend/.env` as DATABASE_URL
- Run migration: `cd backend && python scripts/migrate_csv.py --csv ../data/golden_full_converted.csv`
- Run tests first to confirm no regressions: `cd backend && python -m pytest tests/ -v`
- The 380MB CSV (`data/golden_full_converted.csv`) is in .gitignore — never commit it
- After migration runs and smoke tests pass, mark Phase 1 ✅ in STATUS.md
