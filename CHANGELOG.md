# Changelog

All notable changes to SCIPHR will be documented in this file.

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
