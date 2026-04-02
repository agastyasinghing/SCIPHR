# Changelog

All notable changes to SCIPHR will be documented in this file.

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
