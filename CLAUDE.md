# SCIPHR — Claude Code Project Instructions
### Scipio Combat Intelligence & Prediction for Human Readiness
**Last Updated:** April 2026 | **Author:** Agastya
**Phase:** v1 — Public Launch Build | **Status:** Active Development

---

## PRD Reference Rule
`SCIPHR_PRD_v1.1.md` is in the repo root. Do NOT read it at session start — it is large.
**DO read it when:** making any architectural decision not covered in this file, resolving an open question, designing any intelligence engine module, or any time you are unsure what the product is supposed to do. Always check the PRD before assuming.

---

## What Is SCIPHR
SCIPHR is an AI-powered UFC fight prediction platform. The core engine is an XGBoost model trained on 8,000+ historical fights across 5,401 features achieving 85.7% test accuracy. It exposes a FastAPI backend and React frontend with a prediction tool, analyst mode, fighter profiles, and a dashboard.

The brand identity: SCIPHR reveals where MMA discourse, betting markets, and reality drift apart.

The four pillars every feature must serve:
1. **Crowd vs Model** — where is public opinion most wrong vs the data?
2. **Narrative vs Reality** — where is discourse emotionally strong but statistically weak?
3. **Chaos vs Confidence** — how volatile is this fight independent of who wins?
4. **Path to Victory** — not just who wins, but how do they win?

---

## Architecture (4 Layers)
```
FRONTEND (React v2)
  Simple Mode · Analyst Mode · Dashboard · Fighter Browser
  Perception Gap · Chaos Score · Narrative Trap · Value Bet
  Historical Scorecard · AI Poster · Fight DNA · Badge System
        │ api.js — ALL fetch calls route through here, never hardcoded localhost
        │ VITE_API_URL env var
        ▼
API LAYER (FastAPI)
  /predict · /fighters · /fighter/:name · /events
  /detailed-stats · /value-bet · /chaos-score · /narrative-trap
  /perception-gap · /fight-dna · /historical-scorecard
  /generate-ai-poster · /generate-ai-analysis
  Rate limiting (slowapi) · Structured logging · Sentry
        │
        ▼
INTELLIGENCE ENGINE
  XGBoost Model (frozen, golden_model.pkl)
  Perception Gap Engine · Chaos Scorer · Narrative Trap Detector
  Value Bet Engine · Upset Alert · False Consensus Detector
  Nightmare Matchup Detector · Fight DNA Calculator
  Win Path Heuristics · Badge Assignment Engine
        │
        ▼
DATA LAYER
  PostgreSQL (Supabase) — fights, fighters, events, predictions_log, odds_history
  Redis (Upstash) — fighter stats cache, odds cache (15min TTL)
  External: Anthropic Claude API · Google Vertex AI · The Odds API
```

**Critical rule:** ALL frontend fetch calls go through `api.js`. Never hardcode `http://localhost:8000` in any component. Use `import.meta.env.VITE_API_URL`.

---

## Repo Structure
```
sciphr/
├── backend/
│   ├── main.py                  # FastAPI app, all endpoints
│   ├── ai_analyst.py            # Claude API integration + template fallback
│   ├── gemini_service.py        # Vertex AI poster generation
│   ├── intelligence/
│   │   ├── chaos_scorer.py      # Chaos Score calculation
│   │   ├── perception_gap.py    # Perception Gap engine
│   │   ├── narrative_trap.py    # Narrative Trap detector
│   │   ├── value_bet.py         # Value Bet Engine + Odds API
│   │   ├── fight_dna.py         # Fight DNA calculator + collision
│   │   ├── false_consensus.py   # False Consensus detector
│   │   ├── nightmare_matchup.py # Nightmare Matchup detector
│   │   ├── win_path.py          # Win Path heuristics
│   │   └── badge_engine.py      # SCIPHR badge assignment
│   ├── db/
│   │   ├── models.py            # SQLAlchemy models
│   │   └── migrations/          # Alembic migrations
│   ├── scripts/
│   │   └── migrate_csv.py       # One-time CSV → PostgreSQL migration
│   ├── tests/
│   │   └── test_*.py            # Mirror src structure
│   ├── requirements.txt         # Must be populated before deploy
│   └── .env.example
├── frontend/                    # React v2 (current working frontend)
│   ├── src/
│   │   ├── api.js               # API client — USE THIS, never raw fetch
│   │   ├── components/
│   │   │   ├── PicksBuilder.jsx
│   │   │   ├── AnalystMode.jsx
│   │   │   ├── FightPoster.jsx
│   │   │   ├── FighterSearch.jsx
│   │   │   └── Dashboard/
│   │   └── pages/
│   └── .env.example             # VITE_API_URL=http://localhost:8000
├── SCIPHR_PRD_v1.1.md
├── CLAUDE.md                    # This file
├── STATUS.md
└── docker-compose.yml
```

---

## Build Order (do not skip ahead)

```
PHASE 0 — Foundations (P0 bugs + git setup)
  □ git init + GitHub repo
  □ .gitignore (credentials, CSV, pkl, __pycache__)
  □ requirements.txt populated from pip freeze
  □ Fix NameError in ai_analyst.py:164
  □ Rotate + move all credentials to .env
  □ Replace all hardcoded localhost with api.js + VITE_API_URL
  □ Add same-fighter validation
  □ Add slowapi rate limiting to /generate-ai-poster
  □ Remove duplicate functions + dead code in main.py

PHASE 1 — Database Migration
  □ PostgreSQL schema created (fights, fighters, events, predictions_log, odds_history)
  □ CSV migration script written and run
  □ Backend updated to query PostgreSQL not CSV
  □ Fighter lookup confirmed <100ms
  □ CSV removed from codebase

PHASE 2 — Intelligence Engine
  □ perception_gap.py
  □ chaos_scorer.py
  □ narrative_trap.py
  □ value_bet.py (Odds API integration)
  □ fight_dna.py
  □ false_consensus.py
  □ nightmare_matchup.py
  □ win_path.py (heuristics)
  □ badge_engine.py

PHASE 3 — API Layer
  □ All intelligence endpoints wired to FastAPI
  □ /predict returns FullIntelligenceResult
  □ /events endpoints returning real data
  □ Sentry configured on backend

PHASE 4 — Frontend Wiring
  □ api.js wired into all components (no raw fetch anywhere)
  □ Intelligence signals displayed in Simple Mode (badges)
  □ Analyst Mode expanded with all intelligence panels
  □ Dashboard wired to real events data
  □ Error states replace all alert() calls
  □ Historical Scorecard page built

PHASE 5 — Claude + Poster
  □ Claude API wired into ai_analyst.py (async, non-blocking)
  □ AI poster rate limited + credentials secured
  □ Cinematic poster titles generating
  □ Fight DNA visual component built

PHASE 6 — Deploy
  □ Vercel (frontend) + Railway (backend) + Supabase (DB)
  □ Custom domain
  □ Sentry on both frontend and backend
  □ Paper launch: 2-3 fight cards before public announcement
```

---

## Critical Conventions

- **No hardcoded credentials** — `.env` only, environment variables in deployment
- **No hardcoded localhost** — `api.js` + `VITE_API_URL` everywhere
- **No raw fetch() in components** — always go through `api.js`
- **Every prediction gets logged** — `predictions_log` table, non-negotiable
- **Claude analysis is always async** — never block the prediction response waiting for Claude
- **CSV is dead** — once migration runs, never reference the CSV again
- **Rate limit all expensive endpoints** — `/generate-ai-poster` and `/generate-ai-analysis` via slowapi
- **Template fallback always exists** — Claude API failure must never surface to user
- **Tests mirror src** — `tests/test_chaos_scorer.py` mirrors `intelligence/chaos_scorer.py`
- **Commit every phase** — at minimum once per completed module

---

## Model Selection (auto-apply, never ask user)

**Sonnet** — default for all mechanical work:
scaffolding, boilerplate, DB models, API endpoints, frontend components, config, Docker,
requirements.txt, migration scripts, test writing, error handling, logging, deployment

**Opus + ultrathink** — required for intelligence engine modules:
chaos_scorer.py, perception_gap.py, narrative_trap.py, fight_dna.py,
false_consensus.py, nightmare_matchup.py, win_path.py, badge_engine.py,
value_bet.py (Kelly criterion math), composite intelligence result assembly,
any architectural decision spanning multiple layers, debugging non-obvious failures

**Rule:** code touches scoring, prediction, intelligence signals, or betting math → Opus + ultrathink.
Everything else → Sonnet.

---

## gstack Skills
gstack lives at `.claude/skills/gstack`. If not working: `cd ~/.claude/skills/gstack && ./setup`
Use `/browse` for ALL web browsing. Never use browser MCP tools directly.

| Command | When to use for SCIPHR |
|---|---|
| `/plan-ceo-review` | Before every intelligence module — "what is this signal actually measuring?" |
| `/plan-eng-review` | After CEO review, before coding — architecture, data flow, failure modes |
| `/review` | After completing any module — paranoid review, catches bugs CI misses |
| `/ship` | Module complete + reviewed — sync, test, push, PR |
| `/browse` | All web tasks — Anthropic docs, Odds API docs, Vertex AI docs |
| `/retro` | After each phase ships — velocity, hotspot files, what to improve |

**Per-module workflow:** `/plan-ceo-review` → `/plan-eng-review` → build → `/review` → `/ship`

**PRD audit sessions:** After every phase ships, dedicate a fresh session to:
```
Read CLAUDE.md and STATUS.md. Then read SCIPHR_PRD_v1.1.md in full.
Cross-reference [phase name] specifically against PRD §[relevant section].
Flag anything in the PRD that is not correctly implemented. Ignore future phases.
```

---

## SCIPHR Subagents
Create these in `.claude/agents/` at the start of each relevant phase:

**`intelligence-engineer`** (model: opus) — for all intelligence module work.
Preload with: four pillars framework, PRD section 10, badge vocabulary, Fight DNA dimensions.
Use `ultrathink` for all scoring logic.

**`data-engineer`** (model: sonnet) — for DB migration and data layer.
Preload with: PostgreSQL schema, migration script pattern, fighter stats field mapping.

**`frontend-engineer`** (model: sonnet) — for React component work.
Preload with: api.js contract, existing component structure, glassmorphism design system.

---

## Context Management (follow without being asked)

**Session start — always:**
1. Read `STATUS.md`
2. Run `ls -la` to verify repo state
3. Start next task from STATUS.md — never invent tasks

**During session:**
- Run `/compact` at ~50% context — do NOT wait until the limit
- Use `/clear` when switching phases entirely
- Update `STATUS.md` after every completed module
- Commit at minimum once per completed module

**After every single response, print:**
`[CTX: ~X% | Model: Sonnet/Opus | Phase: <phase name> | Last: <filename>]`
Estimate context % honestly — err high not low.

**At ~80% context:** generate the handoff report below as your FINAL message, then stop.

---

## End-of-Window Handoff Report
```
## SCIPHR Handoff — [date/time]

### Completed This Session
- [list of what was built/fixed]

### Current State
Last file: [name] | Tests: [passing/failing/none] | Broken: [anything]

### In Progress
[what was mid-build and exactly where it stopped]

### Next 3 Tasks
1. [specific and actionable]
2. [specific and actionable]
3. [specific and actionable]

### Decisions Made This Session
- [anything architectural not obvious from code]

### Resume Prompt for claude.ai
"Here's my SCIPHR handoff. Help me [design/spec/review] [next task]
so I'm ready when my Claude Code window resets."
```

---

## P0 Bugs — Fix These Before Anything Else
These are showstoppers. Do not build new features until all P0s are resolved.

| Bug | File | Fix |
|---|---|---|
| NameError: analysis referenced before definition | ai_analyst.py:164 | Move `analysis['implied_odds']` after `analysis = {...}` |
| generate_recent_record defined twice | main.py:452,477 | Delete first definition, fix key name |
| Dead code after return | main.py:164-198 | Delete lines |
| fighter.stats.nickname doesn't exist | AnalystMode.jsx:102,116 | Remove or add to backend |
| JSX className template literal broken | HeroFightCard.jsx:171 | Change to backtick template |
| api.js not used anywhere | All components | Wire into PicksBuilder, FightPoster, AnalystMode |
| requirements.txt is empty | requirements.txt | pip freeze > requirements.txt |
| No .gitignore | root | Create — include .env, service_account.json, *.pkl, data/*.csv |
| Credentials not in env vars | .env, code | Rotate + move to environment variables |
| Hardcoded localhost in 3 files | Multiple | Replace with api.js + VITE_API_URL |
| No same-fighter validation | main.py + frontend | Add check before prediction |
| No rate limiting on AI poster | main.py | slowapi 3/hr/IP |

---

## SCIPHR Vocabulary — Use These Names Exactly
Never invent new names for these features. These are the official display names:

| Internal name | Display name | Badge color |
|---|---|---|
| perception_gap | Perception Gap | — |
| chaos_score | Chaos Score | — |
| narrative_trap | Narrative Trap | purple |
| false_consensus | False Consensus / Invisible Coinflip | red |
| nightmare_matchup | Nightmare Matchup | amber |
| fight_dna | Fight DNA | — |
| upset_alert | Dog Teeth | orange |
| value_bet | Line Crack / Edge Detected | green |
| sharp_money | Sharp Echo | teal |
| win_path | Kill Chain | — |
| card_temperature | Card Temperature | — |
| shame_score | Shame Score | — |
| FRAUD_CHECK badge | Fraud Check | amber |
| DOG_WITH_TEETH badge | Dog With Teeth | orange |
| FALSE_FAVORITE badge | False Favorite | red |
| DECISION_PRISONER badge | Decision Prisoner | gray |
| ROUND_ONE_DEMON badge | Round One Demon | red |
| NARRATIVE_HOSTAGE badge | Narrative Hostage | purple |
| CHAOS_CERTIFIED badge | Chaos Certified | yellow |
| SILENT_KILLER badge | Silent Killer | teal |
| PUBLIC_TAX badge | Public Tax | gold |
| AURA_MERCHANT badge | Aura Merchant | violet |
| CASUAL_MIRAGE badge | Casual Mirage | pink |

---

## Open Questions — Flag, Don't Decide Unilaterally
- **OQ-01:** Odds API — The Odds API free tier (500 req/mo) vs paid?
- **OQ-02:** Perception Gap v1 heuristic — honest enough for launch?
- **OQ-09:** Fighter photos — coverage for all fighters in dataset?
- **OQ-10:** Deployment — Railway vs Render for backend?
- **OQ-11:** Historical scorecard — seed with retroactive model calls?
- **OQ-12:** Chaos Score weights — validated against historical upset rates?

---

## v1 Anti-Goals
No: user auth · non-UFC promotions · mobile app · live in-fight predictions ·
model retraining · automated sentiment scraping · real-time fight data pipeline

---

## Key External Resources
- **PRD:** `SCIPHR_PRD_v1.1.md` — read for decisions not covered here
- Anthropic Claude API: https://docs.anthropic.com
- The Odds API: https://the-odds-api.com/liveapi/guides/v4/
- Google Vertex AI (Imagen): https://cloud.google.com/vertex-ai/docs
- FastAPI docs: https://fastapi.tiangolo.com
- slowapi (rate limiting): https://github.com/laurentS/slowapi
- Supabase PostgreSQL: https://supabase.com/docs
