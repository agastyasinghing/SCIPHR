# SCIPHR — Status
**Last Updated:** April 2026 | **Current Phase:** Phase 0 — Foundations

---

## Phase Progress

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — P0 Bugs + Git Setup | 🔴 Not Started | Fix all showstoppers first |
| Phase 1 — Database Migration | 🔴 Not Started | CSV → PostgreSQL |
| Phase 2 — Intelligence Engine | 🔴 Not Started | All scoring modules |
| Phase 3 — API Layer | 🔴 Not Started | Wire intelligence to FastAPI |
| Phase 4 — Frontend Wiring | 🔴 Not Started | api.js + UI components |
| Phase 5 — Claude + Poster | 🔴 Not Started | AI analysis + poster |
| Phase 6 — Deploy | 🔴 Not Started | Vercel + Railway + Supabase |

---

## Current State
**What exists:** FastAPI backend + React v2 frontend. XGBoost model working at 85.7% accuracy. Core prediction endpoint functional after NameError fix. Fighter search working. CSS poster rendering. Vertex AI poster integration (needs credential securing). Claude API stub written but not wired.

**What is broken (P0):** See CLAUDE.md P0 bugs section — 12 showstoppers must be fixed before anything else.

**What is fake:** Dashboard data 100% hardcoded. Fight history randomly generated. Model performance metrics hardcoded. Recent fight record randomly seeded.

**What is missing:** Database, real events data, all intelligence modules, deployment config, .gitignore, requirements.txt populated.

---

## In Progress
Nothing — starting fresh.

---

## Next 3 Tasks
1. git init + create GitHub repo + populate .gitignore
2. pip freeze > requirements.txt
3. Fix NameError in ai_analyst.py:164

---

## P0 Bug Tracker

| Bug | Status | Fixed In |
|---|---|---|
| NameError ai_analyst.py:164 | 🔴 Open | — |
| generate_recent_record defined twice | 🔴 Open | — |
| Dead code block main.py:164-198 | 🔴 Open | — |
| fighter.stats.nickname missing | 🔴 Open | — |
| JSX className template literal | 🔴 Open | — |
| api.js not wired anywhere | 🔴 Open | — |
| requirements.txt empty | 🔴 Open | — |
| No .gitignore | 🔴 Open | — |
| Credentials exposed | 🔴 Open | — |
| Hardcoded localhost x3 | 🔴 Open | — |
| No same-fighter validation | 🔴 Open | — |
| No rate limiting on AI poster | 🔴 Open | — |

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

---

## Open Questions Resolved

| OQ ID | Resolution | Date |
|---|---|---|
| — | — | — |

---

## Test Coverage

| Module | Tests Written | Passing |
|---|---|---|
| — | No | — |

---

## Notes for Next Session
- Read CLAUDE.md first
- Run `ls -la` to verify repo state before writing any code
- Start with Phase 0 — all P0 bugs before any new features
- The 380MB CSV must NOT be committed to git ever — add to .gitignore immediately
- Rotate Gemini API key and service account before anything else — assume compromised
