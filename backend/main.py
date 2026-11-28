from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import json
import logging
import os
import sys
import numpy as np
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import create_engine, text
from gemini_service import generate_ai_poster
from ai_analyst import ai_analyst
from intelligence.orchestrator import IntelligenceOrchestrator
from intelligence.utils import classify_style
from sqlalchemy.exc import SQLAlchemyError
from fighter_profile import (  # FTR-01B1 read-model (read-only)
    build_profile_extension, build_history, guard_extension, sanitize_raw_stats, json_safe,
    inspect_legacy_raw_stats, assess_raw_inputs, assess_stored_scores, build_legacy_integrity,
    attribute_fights, resolve_fighter_identity, AmbiguousFighterIdentity,
)

# ── Structured logging (JSON, stdlib — no extra deps) ────────────────────────
# LOG_LEVEL env var controls verbosity (default: INFO).
# In production all output is JSON so Render/Sentry can parse structured fields.

class _JSONFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def _configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(_JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())


_configure_logging()
log = logging.getLogger(__name__)

# ── Sentry ────────────────────────────────────────────────────────────────────
# Initialised only when SENTRY_DSN env var is set — no-op otherwise.
# Never hardcode the DSN. Add SENTRY_DSN to backend/.env and deployment secrets.
_sentry_dsn = os.getenv("SENTRY_DSN")
if _sentry_dsn:
    import sentry_sdk
    sentry_sdk.init(
        dsn=_sentry_dsn,
        traces_sample_rate=0.1,
        send_default_pii=False,
    )

# ── Rate limiter ──────────────────────────────────────────────────────────────
# Uses Upstash Redis when UPSTASH_REDIS_URL is set — rate limits survive Render
# free-tier restarts.  Falls back to in-memory storage if Redis is unreachable
# so the server always starts even if Upstash is misconfigured.
_upstash_url = os.getenv("UPSTASH_REDIS_URL")
_REDIS_CONNECT_TIMEOUT_S = 2  # used at startup and in /health — single source of truth
_limiter_storage_uri = None
if _upstash_url:
    try:
        import redis as _redis_mod
        _test = _redis_mod.from_url(_upstash_url, socket_connect_timeout=_REDIS_CONNECT_TIMEOUT_S)
        _test.ping()
        _limiter_storage_uri = _upstash_url
        log.info("rate_limiter_storage_redis")
    except Exception as _redis_err:
        log.warning("redis_unavailable_using_memory", extra={"error": str(_redis_err)})

limiter = Limiter(
    key_func=get_remote_address,
    **({"storage_uri": _limiter_storage_uri} if _limiter_storage_uri else {}),
)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — env var driven for deploy; localhost fallback for dev
_cors_origins_env = os.getenv("ALLOWED_ORIGINS", "")
_cors_origins = (
    [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    if _cors_origins_env
    else ["http://localhost:5173", "http://127.0.0.1:5173"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# ── Application globals ───────────────────────────────────────────────────────
predictor = None
engine = None
orchestrator = None
events_data: dict = {"events": []}
events_index: dict = {}   # fight_id (int) → fight dict, built at startup
events_by_id: dict = {}   # event_id (int) → full event dict, built at startup


def _load_events() -> dict:
    """
    Load events/events.json from the backend directory.

    Fails fast at startup if the file is missing — prevents the server
    from running without event data that intelligence modules depend on.
    narrative_trap tags, chaos short_notice/weight_miss, and cinematic_title
    are all driven by event_fight dicts from this file.

    Returns:
        Parsed events dict with structure {"events": [...]}

    Raises:
        RuntimeError: if events/events.json does not exist.
    """
    events_path = Path(__file__).parent / "events" / "events.json"
    if not events_path.exists():
        raise RuntimeError(
            f"events/events.json not found at {events_path}. "
            "Create this file before starting the server. "
            "See backend/events/events.json for the required schema."
        )
    with events_path.open(encoding="utf-8") as f:
        return json.load(f)


@app.on_event("startup")
async def startup_event():
    global predictor, engine, orchestrator, events_data, events_index, events_by_id

    # ── Database ──────────────────────────────────────────────────────────
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable not set")

    engine = create_engine(database_url, pool_pre_ping=True)

    # Fail fast on misconfigured DATABASE_URL (SELECT 1 health check)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    log.info("db_connected")

    # ── Model ─────────────────────────────────────────────────────────────
    # __file__-anchored paths are container-safe regardless of working directory.
    # Locally: backend/../src and backend/../models work identically.
    _repo_root = Path(__file__).parent.parent
    _src_path = str(_repo_root / "src")
    _model_path = str(_repo_root / "models" / "golden_model.pkl")

    log.info("model_loading", extra={"path": _model_path})
    sys.path.insert(0, _src_path)
    from predictor_golden import UFCFightPredictorGolden

    predictor = UFCFightPredictorGolden(
        model_path=_model_path,
        engine=engine,
    )
    log.info("model_loaded")

    # ── Intelligence orchestrator ─────────────────────────────────────────
    orchestrator = IntelligenceOrchestrator(engine)
    log.info("orchestrator_ready")

    # ── Events data ───────────────────────────────────────────────────────
    # Load events.json once at startup into memory (zero disk I/O per request).
    # Build fight_id index for O(1) lookup from /predict.
    # To pick up new events, restart the server.
    events_data = _load_events()
    for event in events_data.get("events", []):
        eid = event.get("event_id")
        if eid is not None:
            events_by_id[int(eid)] = event
        for fight in event.get("fights", []):
            fid = fight.get("fight_id")
            if fid is not None:
                events_index[int(fid)] = fight
    log.info(
        "events_loaded",
        extra={
            "events": len(events_data["events"]),
            "fights_indexed": len(events_index),
        },
    )


# ── Request models ────────────────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    fighter1: str
    fighter2: str
    fight_id: Optional[int] = None  # links prediction to events_index for event context


class SimplePredictionRequest(BaseModel):
    fighter1: str
    fighter2: str


class DetailedStatsRequest(BaseModel):
    fighter1_name: str
    fighter2_name: str


class AIAnalysisRequest(BaseModel):
    fighter1: str
    fighter2: str
    winner: str
    confidence: float
    fighter1_stats: dict
    fighter2_stats: dict
    # IntelligenceResult.model_dump() from the /predict response.
    # Keys used: chaos, perception_gap, narrative_trap, value_bet.
    # Optional — None for ad-hoc predictions without an orchestrator result.
    intelligence_signals: Optional[dict] = None


# ── Utilities ─────────────────────────────────────────────────────────────────

def convert_numpy(obj):
    """Convert numpy types to native Python types for JSON serialisation."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(item) for item in obj]
    else:
        return obj


def determine_weight_class(weight_lbs):
    """Derive UFC weight class label from weight in lbs."""
    if weight_lbs <= 115:
        return 'Strawweight'
    elif weight_lbs <= 125:
        return 'Flyweight'
    elif weight_lbs <= 135:
        return 'Bantamweight'
    elif weight_lbs <= 145:
        return 'Featherweight'
    elif weight_lbs <= 155:
        return 'Lightweight'
    elif weight_lbs <= 170:
        return 'Welterweight'
    elif weight_lbs <= 185:
        return 'Middleweight'
    elif weight_lbs <= 205:
        return 'Light Heavyweight'
    else:
        return 'Heavyweight'


# ── Input sanitization ────────────────────────────────────────────────────────

_FIGHTER_NAME_MAX_LEN = 100


def _sanitize_fighter_name(name: str, field: str = "Fighter name") -> str:
    """
    Validate and normalise a fighter name from user input (PRD §18 Security).

    Rules:
      - Strip leading/trailing whitespace.
      - Max 100 characters after stripping.
      - Must be fully printable (rejects NUL bytes, control chars, etc.).

    Raises HTTPException 422 on any violation so FastAPI surfaces a clear
    error to the caller rather than passing garbage into the predictor.
    """
    name = name.strip()
    if len(name) > _FIGHTER_NAME_MAX_LEN:
        raise HTTPException(
            status_code=422,
            detail=f"{field} must be {_FIGHTER_NAME_MAX_LEN} characters or fewer",
        )
    if not name.isprintable():
        raise HTTPException(
            status_code=422,
            detail=f"{field} contains invalid characters",
        )
    return name


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "SCIPHR API is running", "status": "online"}


@app.get("/health")
async def health_check():
    """
    Readiness check: DB ping + model loaded.

    Returns 200 {"status": "ok"} when both are healthy.
    Returns 503 {"status": "degraded"} when either is unavailable.

    Used by Railway/Vercel health gates and on-call alerting.
    The DB ping runs a SELECT 1 — trivial cost, catches pool exhaustion
    and misconfigured DATABASE_URL.
    """
    db_status = "ok"
    try:
        if engine is None:
            db_status = "error"
        else:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    model_status = "loaded" if predictor is not None else "not_loaded"

    # Redis check — optional; in-memory fallback is used if Redis is unreachable.
    # "not_configured" when UPSTASH_REDIS_URL is absent (acceptable for dev).
    # "error" when configured but unreachable (rate limits fall back to in-memory).
    # Neither state marks the service degraded — only DB/model failures do.
    redis_status = "not_configured"
    if _upstash_url:
        try:
            import redis as _redis_chk
            _r = _redis_chk.from_url(_upstash_url, socket_connect_timeout=_REDIS_CONNECT_TIMEOUT_S)
            _r.ping()
            redis_status = "ok"
        except Exception:
            redis_status = "error"

    is_healthy = db_status == "ok" and model_status == "loaded"

    body = {
        "status": "ok" if is_healthy else "degraded",
        "db_connected": db_status,
        "model_loaded": model_status,
        "redis_connected": redis_status,
        "version": os.getenv("APP_VERSION", "unknown"),
    }
    return JSONResponse(status_code=200 if is_healthy else 503, content=body)


@app.get("/events")
async def get_events():
    """Return all manually curated events with fight metadata."""
    return {"events": events_data.get("events", [])}


@app.get("/events/upcoming")
async def get_upcoming_event():
    """
    Return the next upcoming event (closest future date).
    Falls back to the most recent past event when no future events are loaded.

    Used by the Dashboard to display the current/next fight card.
    events.json must be updated each fight week — see CLAUDE.md §Build Order.
    """
    from datetime import date as _date
    today = str(_date.today())
    all_events = events_data.get("events", [])

    upcoming = sorted(
        [e for e in all_events if e.get("date", "") >= today],
        key=lambda e: e.get("date", ""),
    )
    if upcoming:
        return upcoming[0]

    past = sorted(
        [e for e in all_events if e.get("date", "") < today],
        key=lambda e: e.get("date", ""),
        reverse=True,
    )
    if past:
        return past[0]

    raise HTTPException(status_code=404, detail="No events found")


@app.get("/events/past")
async def get_past_events():
    """
    Return all past events sorted most-recent first.

    Used by the Dashboard EventsTimeline.
    """
    from datetime import date as _date
    today = str(_date.today())
    all_events = events_data.get("events", [])
    past = sorted(
        [e for e in all_events if e.get("date", "") < today],
        key=lambda e: e.get("date", ""),
        reverse=True,
    )
    return {"events": past}


@app.get("/events/{event_id}")
async def get_event(event_id: int):
    """
    Return the full event card (all fights) for the given event_id.

    event_id corresponds to the top-level 'event_id' field in events.json,
    not to individual fight_ids.  Use fight_id in POST /predict to link
    a prediction to event context.
    """
    event = events_by_id.get(event_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail=f"Event ID {event_id} not found",
        )
    return event


@app.get("/fighters")
async def get_fighters(
    search: str = None,
    limit: int = Query(default=100, le=5000),  # covers full DB (2,615 fighters); raise if dataset grows
    weight_class: str = None,
    active_only: bool = False,
):
    """
    Get list of available fighters as objects with name, weight_class, is_active.

    Supports optional filters:
      weight_class — case-sensitive weight class string (e.g. "Lightweight")
      active_only  — when True, omit fighters where is_active = false
    """
    if engine is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    clauses = []
    params: dict = {"lim": limit}

    if search:
        clauses.append("LOWER(name) LIKE LOWER(:q)")
        params["q"] = f"%{search}%"
    if weight_class:
        clauses.append("weight_class = :wc")
        params["wc"] = weight_class
    if active_only:
        clauses.append("(is_active IS NULL OR is_active = true)")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = text(
        f"SELECT name, weight_class, COALESCE(is_active, true) AS is_active "
        f"FROM fighters {where} ORDER BY name LIMIT :lim"
    )

    with engine.connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    fighters = [
        {
            "name": row[0],
            "weight_class": row[1] or "",
            "is_active": bool(row[2]),
        }
        for row in rows
    ]
    return {"fighters": fighters, "count": len(fighters)}


def _resolve_profile_identity(name: str):
    """Shared profile/history identity resolution -> exact stored name | None | HTTP 409."""
    fuzzy = predictor.search_fighter if predictor is not None else None
    if engine is None:                                 # no DB identity available (legacy path)
        return fuzzy(name) if fuzzy else None
    try:
        with engine.connect() as conn:
            return resolve_fighter_identity(conn, name, fuzzy)
    except AmbiguousFighterIdentity as exc:
        raise HTTPException(status_code=409, detail=exc.detail())


@app.get("/fighter/{fighter_name}")
async def get_fighter_profile(fighter_name: str):
    """Get full profile for a specific fighter, including computed intelligence scores."""
    if predictor is None:
        raise HTTPException(status_code=500, detail="Predictor not initialized")

    from urllib.parse import unquote
    fighter_name = _sanitize_fighter_name(unquote(fighter_name))

    # FTR-01B1-R4: resolve the stored identity BEFORE the case-insensitive first-match
    # predictor.search_fighter (exact > unique normalised > 409 on collision > checked fuzzy).
    # The one resolved name is used for every lookup below.  DB errors propagate.
    matched_name = _resolve_profile_identity(fighter_name)

    if not matched_name:
        raise HTTPException(
            status_code=404,
            detail=f"Fighter '{fighter_name}' not found"
        )

    # FTR-01B1-R2/R3: the shared calculator coerces with float() and raises on a
    # malformed stored number.  On ValueError/TypeError the profile-only reader
    # inspects the stored row (SELECT only) and we recover ONLY if it finds a stored
    # value that float() cannot convert - evidence that explains the failure.  Without
    # that evidence the original exception is re-raised (it is a real bug, not data).
    # Database/connection errors are never caught and still surface as failures.
    malformed_keys: list = []
    try:
        raw_stats = predictor.feature_calculator.get_latest_fighter_stats(matched_name)
    except (ValueError, TypeError):
        if engine is None:
            raise
        inspection = inspect_legacy_raw_stats(engine, matched_name)
        if not inspection["coercion_failures"]:
            raise
        log.warning("profile_raw_stats_fallback fighter=%r fields=%s",
                    matched_name, inspection["coercion_failures"])
        raw_stats, malformed_keys = inspection["raw"], inspection["malformed"]

    if not raw_stats:
        raise HTTPException(
            status_code=404,
            detail=f"No stats found for '{matched_name}'"
        )

    # FTR-01B1-R1/R2: neutralise non-finite, malformed and impossible legacy inputs at
    # the boundary.  Each is replaced by the legacy placeholder (None -> 0) and reported
    # in `legacy_integrity`; valid values pass through untouched.
    raw_stats, nonfinite_keys = sanitize_raw_stats(raw_stats)
    malformed_keys = sorted(set(malformed_keys) | set(nonfinite_keys))
    raw_stats, range_corruption = assess_raw_inputs(raw_stats)

    weight = float(raw_stats.get('fighter_weight_lbs', 185) or 185)

    stats = {
        # Record
        'wins_total': float(raw_stats.get('fighter_w', 0) or 0),
        'losses_total': float(raw_stats.get('fighter_l', 0) or 0),
        'draw': float(raw_stats.get('fighter_d', 0) or 0),

        # Physical
        'age': float(raw_stats.get('age', 0) or 0),
        'height': float(raw_stats.get('fighter_height_cm', 0) or 0),
        'reach': float(raw_stats.get('fighter_reach_cm', 0) or 0),
        'weight': weight,
        'weight_class': determine_weight_class(weight),

        # Striking
        'SLpM_total': float(raw_stats.get('fighter_SlpM', 0) or 0),
        'sig_str_acc_total': float(raw_stats.get('fighter_Str_Acc', 0) or 0) * 100,
        'sig_str_def_total': float(raw_stats.get('fighter_Str_Def', 0) or 0) * 100,
        'total_knockdowns': float(raw_stats.get('knockdowns', 0) or 0),

        # Grappling
        'td_avg_total': float(raw_stats.get('fighter_TD_Avg', 0) or 0),
        'td_acc_total': float(raw_stats.get('fighter_TD_Acc', 0) or 0) * 100,
        'td_def_total': float(raw_stats.get('fighter_TD_Def', 0) or 0) * 100,
        'sub_avg_total': float(raw_stats.get('fighter_Sub_Avg', 0) or 0),
    }

    # ── Intelligence scores ────────────────────────────────────────────────────
    # Read stored values from fighters table; fall back to on-the-fly computation
    # when columns are NULL (expected in v1 before batch scoring runs).

    stored = None
    try:
        if engine is not None:
            with engine.connect() as conn:
                # FTR-01B1-R4: exact resolved identity; the row's name is re-checked in
                # Python so no collation can mix another fighter's stored values in.
                stored = next((r for r in conn.execute(
                    text(
                        "SELECT name, style, is_active, aura_score, chaos_contribution, "
                        "mirage_meter, composite_score "
                        "FROM fighters WHERE name = :name"
                    ),
                    {"name": matched_name},
                ).fetchall() if r.name == matched_name), None)
    except SQLAlchemyError:
        pass  # never block profile on a DB hiccup (legacy behaviour; programming errors still surface)

    # FTR-01B1-R2: validate stored scores (None / valid numbers pass; corrupted => ignore all stored)
    stored_scores, stored_corruption = assess_stored_scores(stored)

    # Numeric building blocks for on-the-fly computation
    wins = float(raw_stats.get('fighter_w', 0) or 0)
    losses = float(raw_stats.get('fighter_l', 0) or 0)
    total_fights = wins + losses or 1
    win_rate = wins / total_fights
    slpm = float(raw_stats.get('fighter_SlpM', 0) or 0)
    str_acc = float(raw_stats.get('fighter_Str_Acc', 0) or 0)   # 0–1
    str_def = float(raw_stats.get('fighter_Str_Def', 0) or 0)   # 0–1
    td_avg = float(raw_stats.get('fighter_TD_Avg', 0) or 0)
    sub_avg = float(raw_stats.get('fighter_Sub_Avg', 0) or 0)

    # Style
    style_val = (stored.style if stored and stored.style else None)
    if not style_val:
        style_val = classify_style({
            'slpm': slpm, 'str_acc': str_acc, 'str_def': str_def,
            'td_avg': td_avg, 'sub_avg': sub_avg,
        })

    # is_active
    is_active = bool(stored.is_active) if stored and stored.is_active is not None else True

    # Aura score (0–100): proxy for public hype level
    finish_proxy = min(1.0, (slpm / 6.0) * 0.5 + (td_avg / 5.0) * 0.5)
    aura_score = stored_scores["aura_score"] if stored_scores["aura_score"] is not None else round(
        min(100.0, win_rate * 40.0 + finish_proxy * 35.0 + min(total_fights, 20) / 20.0 * 25.0), 1
    )

    # Composite score (0–100): overall model-quality rating
    composite_score = stored_scores["composite_score"] if stored_scores["composite_score"] is not None else round(
        min(100.0, max(0.0, (win_rate * 40.0 + str_acc * 30.0 + str_def * 30.0) * 100.0)), 1
    )

    # Chaos contribution (0–100): how much this fighter raises fight volatility
    slpm_norm = min(1.0, slpm / 7.0)
    chin_risk = max(0.0, 1.0 - str_def)  # low defense = high chin risk
    chaos_contribution = stored_scores["chaos_contribution"] if stored_scores["chaos_contribution"] is not None else round(
        min(100.0, (slpm_norm * 0.5 + chin_risk * 0.5) * 100.0), 1
    )

    # Mirage Meter (0–100): resume inflation proxy
    # High win rate + low defensive stats → potential mirage
    mirage_meter = stored_scores["mirage_meter"] if stored_scores["mirage_meter"] is not None else round(
        min(100.0, max(0.0, (win_rate - 0.65) * 200.0)) if win_rate > 0.65 and str_def < 0.55 else 0.0, 1
    )

    scores_are_stored = stored_scores["aura_score"] is not None

    # FTR-01B1-R2: legacy scores computed from corrupted inputs are withheld (null),
    # never presented as trustworthy; the corruption is described in `legacy_integrity`,
    # which is built independently of the data_quality extension.
    legacy_scores = {
        "aura_score": aura_score, "composite_score": composite_score,
        "chaos_contribution": chaos_contribution, "mirage_meter": mirage_meter,
    }
    heuristic_scores = {n for n, v in stored_scores.items() if v is None}
    legacy_integrity, withheld = build_legacy_integrity(
        malformed_keys, range_corruption, stored_corruption, heuristic_scores)
    for n in withheld:
        legacy_scores[n] = None
    if legacy_integrity["corrupted"]:
        log.warning(
            "profile_legacy_corruption fighter=%r raw=%s stored=%s withheld=%s", matched_name,
            [e["field"] for e in legacy_integrity["raw_input_corruption"]],
            [e["field"] for e in stored_corruption], sorted(withheld))

    # FTR-01B1: additive availability-aware objects.  Legacy `stats` and
    # `intelligence` above are intentionally unchanged for valid data (see data_quality.legacy_compat).
    extension = guard_extension(build_profile_extension, engine, matched_name, log)
    if isinstance(extension["data_quality"], dict):
        extension["data_quality"]["legacy_corrupted_fields"] = [
            e["field"] for e in legacy_integrity["raw_input_corruption"]]

    return json_safe({
        "name": matched_name,
        "data_quality": extension["data_quality"],
        "scores": extension["scores"],
        "extension_status": extension["extension_status"],
        "legacy_integrity": legacy_integrity,
        "stats": convert_numpy(stats),
        "intelligence": {
            "style": style_val,
            "is_active": is_active,
            "aura_score": legacy_scores["aura_score"],
            "composite_score": legacy_scores["composite_score"],
            "chaos_contribution": legacy_scores["chaos_contribution"],
            "mirage_meter": legacy_scores["mirage_meter"],
            "scores_source": "computed" if scores_are_stored else "heuristic",
        },
    })


@app.get("/fighter/{fighter_name}/history")
async def get_fighter_history(fighter_name: str):
    """
    Return the last 20 fights for a fighter in reverse chronological order.

    Uses fuzzy name matching (search_fighter) when predictor is loaded.
    Each fight includes: opponent, date, result (W/L/D/NC/UNKNOWN), method, weight_class.
    result_counts / methods_available_fraction describe these (latest 20) rows only.
    """
    if engine is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    from urllib.parse import unquote
    fighter_name = _sanitize_fighter_name(unquote(fighter_name))

    # FTR-01B1-R4: same shared resolver as the profile route.  Unresolvable names keep the
    # requested spelling (no fighter row -> attribution finds no/unique bouts -> 404 as before).
    resolved = _resolve_profile_identity(fighter_name)
    if resolved:
        fighter_name = resolved

    # FTR-01B1-R2/R3: participant matching is whitespace/case-normalised, with ONE shared
    # attribution policy (also used by profile coverage): when two fighter records share a
    # normalised name only exactly-named bouts are attributed and the rest are withheld.
    with engine.connect() as conn:
        attribution = attribute_fights(conn, fighter_name)
    rows = attribution.rows[:20]

    if not rows and not attribution.withheld_ambiguous:
        raise HTTPException(status_code=404, detail=f"No fight history found for '{fighter_name}'")

    # FTR-01B1: result is W/L/D/NC/UNKNOWN (never "not a win" == loss); additive metadata.
    payload = build_history(fighter_name, rows, attribution)
    return {"name": fighter_name, "count": len(payload["fights"]), **payload}


@app.get("/events/{event_id}/card-predictions")
async def get_card_predictions(event_id: int):
    """
    Run POST /predict/simple for every fight on an event card.

    Used by the Dashboard for the Upset Watch feed and card-level previews.
    Fighter name mismatches (events.json name != DB name) are skipped
    gracefully — only fights where both names resolve are included.

    Returns:
        {event_id, predictions: [{fighter1, fighter2, winner, confidence,
                                   prob_fighter1, prob_fighter2, is_close}]}
    where is_close = abs(prob_f1 - prob_f2) < 0.15  (model near-coinflip).
    """
    if predictor is None:
        raise HTTPException(status_code=500, detail="Predictor not initialized")

    event = events_by_id.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail=f"Event ID {event_id} not found")

    predictions = []
    for fight in event.get("fights", []):
        f1 = fight.get("r_fighter") or fight.get("fighter1", "")
        f2 = fight.get("b_fighter") or fight.get("fighter2", "")
        if not f1 or not f2 or f1 == "TBA" or f2 == "TBA":
            continue
        try:
            result = predictor.predict_fight(f1, f2, verbose=False)
            if result is None:
                continue
            prob_f1 = float(result["prob_fighter1"])
            prob_f2 = float(result["prob_fighter2"])
            predictions.append({
                "fight_id": fight.get("fight_id"),
                "fighter1": result["fighter1"],
                "fighter2": result["fighter2"],
                "winner": result["winner"],
                "confidence": float(result["confidence"]),
                "prob_fighter1": prob_f1,
                "prob_fighter2": prob_f2,
                # is_close: model within 15% either way → Upset Watch candidate
                "is_close": abs(prob_f1 - prob_f2) < 0.15,
            })
        except Exception:
            continue  # skip unresolvable fighter names silently

    return {"event_id": event_id, "predictions": predictions}


@app.post("/predict/simple")
async def predict_fight_simple(request: SimplePredictionRequest):
    """
    Fast prediction path — returns winner + confidence only.
    Skips the intelligence orchestrator entirely.

    Use this for low-latency contexts (e.g. bulk previews, dashboard cards).
    For the full intelligence bundle use POST /predict.
    """
    f1 = _sanitize_fighter_name(request.fighter1, "fighter1")
    f2 = _sanitize_fighter_name(request.fighter2, "fighter2")
    if f1.lower() == f2.lower():
        raise HTTPException(
            status_code=400,
            detail="Fighter 1 and Fighter 2 must be different fighters",
        )
    if predictor is None:
        raise HTTPException(status_code=500, detail="Predictor not initialized")

    result = predictor.predict_fight(f1, f2, verbose=False)
    if result is None:
        raise HTTPException(status_code=404, detail="One or both fighters not found")

    return {
        "fighter1": result["fighter1"],
        "fighter2": result["fighter2"],
        "winner": result["winner"],
        "confidence": float(result["confidence"]),
        "prob_fighter1": float(result["prob_fighter1"]),
        "prob_fighter2": float(result["prob_fighter2"]),
    }


@app.post("/predict")
async def predict_fight(request: PredictionRequest):
    """
    Predict the outcome of a fight and return the full intelligence bundle.

    Data flow:
      1. XGBoost prediction → prob_f1, prob_f2, winner
      2. events_index lookup (if fight_id provided) → event_fight context
      3. IntelligenceOrchestrator.compute() → IntelligenceResult (all 11 modules)
      4. AI analysis generation (template fallback if Claude unavailable)
      5. predictions_log INSERT (non-fatal on failure)

    The intelligence field is always present in the response.
    Individual modules that fail return None within IntelligenceResult
    (see _safe_compute in orchestrator.py — no module failure can fail /predict).
    """
    # Input validation runs before globals check — no initialized state needed.
    f1 = _sanitize_fighter_name(request.fighter1, "fighter1")
    f2 = _sanitize_fighter_name(request.fighter2, "fighter2")
    if f1.lower() == f2.lower():
        raise HTTPException(
            status_code=400,
            detail="Fighter 1 and Fighter 2 must be different fighters",
        )

    if predictor is None:
        raise HTTPException(status_code=500, detail="Predictor not initialized")
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    try:
        log.info("predict_request", extra={"fighter1": f1, "fighter2": f2})

        result = predictor.predict_fight(
            f1,
            f2,
            verbose=False,
        )

        if result is None:
            raise HTTPException(status_code=404, detail="One or both fighters not found")

        log.debug("predict_result", extra={"winner": result.get("winner"), "confidence": result.get("confidence")})

        # Resolve event context from fight_id (None for ad-hoc predictions).
        # Modules degrade gracefully when event_fight is None.
        event_fight = events_index.get(request.fight_id) if request.fight_id is not None else None

        # Run intelligence engine.
        # orchestrator.compute() always returns IntelligenceResult — never raises.
        # Modules that fail return None inside IntelligenceResult (_safe_compute).
        model_probs = (float(result['prob_fighter1']), float(result['prob_fighter2']))
        intel_result = orchestrator.compute(
            f1_name=result['fighter1'],
            f2_name=result['fighter2'],
            model_probs=model_probs,
            fight_id=request.fight_id,
            event_fight=event_fight,
        )
        log.debug("intelligence_computed")

        # AI analysis is NOT generated here — it is async and non-blocking.
        # The frontend calls POST /generate-ai-analysis separately after the
        # prediction renders.  ai_analysis: null is the intentional response.
        if not result.get('fighter1_stats') or not result.get('fighter2_stats'):
            log.warning("fighter_stats_missing", extra={"fighter1": result["fighter1"], "fighter2": result["fighter2"]})

        log.debug("building_response")
        response = {
            "fighter1": result['fighter1'],
            "fighter2": result['fighter2'],
            "prob_fighter1": float(result['prob_fighter1']),
            "prob_fighter2": float(result['prob_fighter2']),
            "winner": result['winner'],
            "confidence": float(result['confidence']),
            "ai_analysis": None,  # populated async via POST /generate-ai-analysis
            # predictor.predict_fight() fetches fighter stats internally —
            # use those directly to avoid redundant DB queries.
            "fighter1_stats": convert_numpy(result.get('fighter1_stats') or {}),
            "fighter2_stats": convert_numpy(result.get('fighter2_stats') or {}),
            # Intelligence bundle: all 11 modules. Failed modules are None.
            "intelligence": intel_result.model_dump(),
        }

        log.info("predict_success", extra={"winner": response["winner"], "confidence": response["confidence"]})

        # Log every prediction — non-negotiable per CLAUDE.md.
        # try/except ensures a DB failure here never fails the response.
        try:
            from db.models import PredictionLog
            from sqlalchemy import insert

            # Build odds snapshot from value_bet result if odds are available.
            # value_bet.signal == NO_ODDS when no odds_history rows exist for this fight.
            vb = intel_result.value_bet
            odds_snapshot = None
            if vb.signal != "NO_ODDS" and vb.implied_prob_f1 is not None and vb.implied_prob_f2 is not None:
                odds_snapshot = {
                    response["fighter1"]: {"implied": float(vb.implied_prob_f1)},
                    response["fighter2"]: {"implied": float(vb.implied_prob_f2)},
                }

            with engine.begin() as conn:
                conn.execute(
                    insert(PredictionLog).values(
                        fighter1=response["fighter1"],
                        fighter2=response["fighter2"],
                        winner=response["winner"],
                        confidence=response["confidence"],
                        prob_f1=response["prob_fighter1"],
                        prob_f2=response["prob_fighter2"],
                        odds_at_prediction=odds_snapshot,
                    )
                )
        except Exception as log_err:
            log.warning("predictions_log_insert_failed", extra={"error": str(log_err)})

        return response

    except HTTPException:
        raise
    except Exception as e:
        log.error("predict_error", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/historical-scorecard")
async def get_historical_scorecard(limit: int = 50, offset: int = 0):
    """
    Return paginated prediction history from predictions_log.
    actual_winner is NULL until an admin resolves the fight post-event.
    Returns rows ordered newest-first. Max 200 rows per request.
    """
    limit = min(limit, 200)  # cap to prevent full-table pulls
    try:
        from db.models import PredictionLog
        from sqlalchemy import select, func as sqlfunc

        with engine.connect() as conn:
            total_row = conn.execute(
                select(sqlfunc.count()).select_from(PredictionLog)
            ).scalar()

            rows = conn.execute(
                select(
                    PredictionLog.id,
                    PredictionLog.fighter1,
                    PredictionLog.fighter2,
                    PredictionLog.winner,
                    PredictionLog.confidence,
                    PredictionLog.prob_f1,
                    PredictionLog.prob_f2,
                    PredictionLog.actual_winner,
                    PredictionLog.value_signal,
                    PredictionLog.edge_pct,
                    PredictionLog.created_at,
                )
                .order_by(PredictionLog.created_at.desc())
                .limit(limit)
                .offset(offset)
            ).fetchall()

        predictions = []
        for row in rows:
            correct = (
                row.actual_winner == row.winner
                if row.actual_winner and row.winner
                else None  # unresolved
            )
            predictions.append({
                "id": row.id,
                "fighter1": row.fighter1,
                "fighter2": row.fighter2,
                "predicted_winner": row.winner,
                "confidence": float(row.confidence) if row.confidence else None,
                "prob_f1": float(row.prob_f1) if row.prob_f1 else None,
                "prob_f2": float(row.prob_f2) if row.prob_f2 else None,
                "actual_winner": row.actual_winner,
                "correct": correct,
                "value_signal": row.value_signal,
                "edge_pct": float(row.edge_pct) if row.edge_pct else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })

        resolved = [p for p in predictions if p["correct"] is not None]
        accuracy = (
            sum(1 for p in resolved if p["correct"]) / len(resolved)
            if resolved else None
        )

        return {
            "predictions": predictions,
            "total": total_row,
            "limit": limit,
            "offset": offset,
            "accuracy": round(accuracy * 100, 1) if accuracy is not None else None,
            "resolved_count": len(resolved),
        }

    except Exception as e:
        log.error("historical_scorecard_error", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class AIPosterRequest(BaseModel):
    fighter1_name: str
    fighter2_name: str
    prediction: dict  # Contains winner, confidence, etc.
    # "1:1" = standard (default), "9:16" = Instagram Story format
    aspect_ratio: Optional[str] = "1:1"


@app.post("/generate-ai-poster")
@limiter.limit("3/hour")
async def create_ai_poster(request: Request, poster_request: AIPosterRequest):
    """Generate AI poster using Gemini."""
    try:
        log.info(
            "poster_request",
            extra={
                "fighter1": poster_request.fighter1_name,
                "fighter2": poster_request.fighter2_name,
                "winner": poster_request.prediction.get("winner"),
            },
        )

        f1_stats = predictor.feature_calculator.get_latest_fighter_stats(poster_request.fighter1_name)
        f2_stats = predictor.feature_calculator.get_latest_fighter_stats(poster_request.fighter2_name)

        if not f1_stats or not f2_stats:
            raise HTTPException(status_code=404, detail="Fighter stats not found")

        fighter1_data = {
            'name': poster_request.fighter1_name,
            'wins': int(f1_stats.get('fighter_w', 0)),
            'losses': int(f1_stats.get('fighter_l', 0)),
            'draws': int(f1_stats.get('fighter_d', 0)),
            'weight_class': determine_weight_class(f1_stats.get('fighter_weight_lbs', 185)),
            'age': int(f1_stats.get('age', 0)),
            'height': f"{int(f1_stats.get('fighter_height_cm', 0))} cm",
            'reach': f"{int(f1_stats.get('fighter_reach_cm', 0))} cm",
        }

        fighter2_data = {
            'name': poster_request.fighter2_name,
            'wins': int(f2_stats.get('fighter_w', 0)),
            'losses': int(f2_stats.get('fighter_l', 0)),
            'draws': int(f2_stats.get('fighter_d', 0)),
            'weight_class': determine_weight_class(f2_stats.get('fighter_weight_lbs', 185)),
            'age': int(f2_stats.get('age', 0)),
            'height': f"{int(f2_stats.get('fighter_height_cm', 0))} cm",
            'reach': f"{int(f2_stats.get('fighter_reach_cm', 0))} cm",
        }

        prediction_data = {
            'winner': poster_request.prediction.get('winner'),
            'confidence': float(poster_request.prediction.get('confidence', 0)) * 100,
        }

        result = generate_ai_poster(
            fighter1_data,
            fighter2_data,
            prediction_data,
            aspect_ratio=poster_request.aspect_ratio or "1:1",
        )

        if result['success']:
            return {
                'success': True,
                'style_name': result['style_name'],
                'image_url': result.get('image_url'),
                'response': str(result.get('response')),
            }
        else:
            raise HTTPException(status_code=500, detail=result['error'])

    except HTTPException:
        raise
    except Exception as e:
        log.error("poster_error", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-ai-analysis")
@limiter.limit("3/hour")
async def generate_ai_analysis(request: Request, analysis_request: AIAnalysisRequest):
    """
    Generate AI fight analysis using Claude (template fallback if API unavailable).

    Called by the frontend AFTER /predict renders — keeps /predict fast.
    Rate limited to 3/hour/IP to protect Claude API costs.

    Request body: fighter names, winner, confidence, fighter stats dicts
    (from /predict fighter1_stats/fighter2_stats), and intelligence_signals
    (from /predict intelligence — the IntelligenceResult model_dump()).
    """
    import asyncio

    f1 = _sanitize_fighter_name(analysis_request.fighter1, "fighter1")
    f2 = _sanitize_fighter_name(analysis_request.fighter2, "fighter2")
    winner = _sanitize_fighter_name(analysis_request.winner, "winner")

    prediction_data = {
        "fighter1": f1,
        "fighter2": f2,
        "winner": winner,
        "confidence": analysis_request.confidence,
        "fighter1_stats": analysis_request.fighter1_stats,
        "fighter2_stats": analysis_request.fighter2_stats,
    }

    # asyncio.to_thread runs the sync function in a thread pool — the event
    # loop is never blocked, so other requests can proceed while Claude responds.
    try:
        analysis = await asyncio.to_thread(
            ai_analyst.generate_fight_analysis,
            prediction_data,
            analysis_request.intelligence_signals,
        )
        return {"analysis": analysis}
    except Exception as e:
        log.error("ai_analysis_error", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detailed-stats")
async def get_detailed_stats(request: DetailedStatsRequest):
    """
    Get detailed statistics for Analyst Mode.
    Uses the same data extraction as the prediction endpoint.
    """
    try:
        fighter1_name = request.fighter1_name
        fighter2_name = request.fighter2_name

        log.info("detailed_stats_request", extra={"fighter1": fighter1_name, "fighter2": fighter2_name})

        result = predictor.predict_fight(fighter1_name, fighter2_name, verbose=False)

        if not result or 'fighter1_stats' not in result or 'fighter2_stats' not in result:
            return {"success": False, "error": "Could not get fighter stats"}

        f1_stats = result['fighter1_stats']
        f2_stats = result['fighter2_stats']

        def safe_float(val, default=0):
            try:
                return float(val) if val is not None and str(val) != 'nan' else default
            except:
                return default

        detailed_stats = {
            "f1_str_acc": safe_float(f1_stats.get('str_acc', 50), 50),
            "f1_str_def": safe_float(f1_stats.get('str_def', 50), 50),
            "f1_td_acc": safe_float(f1_stats.get('td_acc', 40), 40),
            "f1_td_def": safe_float(f1_stats.get('td_def', 60), 60),
            "f1_td_avg": safe_float(f1_stats.get('td_avg', 2), 2),
            "f1_sub_avg": safe_float(f1_stats.get('sub_avg', 1), 1),
            "f1_ctrl_ratio": safe_float(f1_stats.get('ctrl_ratio', 50), 50),
            "f1_head_acc": safe_float(f1_stats.get('head_acc', 45), 45),
            "f1_body_acc": safe_float(f1_stats.get('body_acc', 40), 40),
            "f1_leg_acc": safe_float(f1_stats.get('leg_acc', 35), 35),
            "f1_distance_acc": safe_float(f1_stats.get('distance_acc', 50), 50),
            "f1_clinch_acc": safe_float(f1_stats.get('clinch_acc', 45), 45),
            "f1_ground_acc": safe_float(f1_stats.get('ground_acc', 40), 40),
            "f1_r1_performance": safe_float(f1_stats.get('r_r1_sig_pct', 50), 50),
            "f1_r2_performance": safe_float(f1_stats.get('r_r2_sig_pct', 48), 48),
            "f1_r3_performance": safe_float(f1_stats.get('r_r3_sig_pct', 45), 45),
            "f1_r4_performance": safe_float(f1_stats.get('r_r4_sig_pct', 42), 42),
            "f1_r5_performance": safe_float(f1_stats.get('r_r5_sig_pct', 40), 40),
            "f2_str_acc": safe_float(f2_stats.get('str_acc', 48), 48),
            "f2_str_def": safe_float(f2_stats.get('str_def', 52), 52),
            "f2_td_acc": safe_float(f2_stats.get('td_acc', 38), 38),
            "f2_td_def": safe_float(f2_stats.get('td_def', 62), 62),
            "f2_td_avg": safe_float(f2_stats.get('td_avg', 1.5), 1.5),
            "f2_sub_avg": safe_float(f2_stats.get('sub_avg', 0.8), 0.8),
            "f2_ctrl_ratio": safe_float(f2_stats.get('ctrl_ratio', 48), 48),
            "f2_head_acc": safe_float(f2_stats.get('head_acc', 48), 48),
            "f2_body_acc": safe_float(f2_stats.get('body_acc', 38), 38),
            "f2_leg_acc": safe_float(f2_stats.get('leg_acc', 32), 32),
            "f2_distance_acc": safe_float(f2_stats.get('distance_acc', 52), 52),
            "f2_clinch_acc": safe_float(f2_stats.get('clinch_acc', 42), 42),
            "f2_ground_acc": safe_float(f2_stats.get('ground_acc', 38), 38),
            "f2_r1_performance": safe_float(f2_stats.get('r_r1_sig_pct', 52), 52),
            "f2_r2_performance": safe_float(f2_stats.get('r_r2_sig_pct', 50), 50),
            "f2_r3_performance": safe_float(f2_stats.get('r_r3_sig_pct', 48), 48),
            "f2_r4_performance": safe_float(f2_stats.get('r_r4_sig_pct', 45), 45),
            "f2_r5_performance": safe_float(f2_stats.get('r_r5_sig_pct', 42), 42),
            "f1_win_streak": calculate_win_streak(f1_stats),
            "f2_win_streak": calculate_win_streak(f2_stats),
            "f1_recent_fights": generate_recent_record(f1_stats),
            "f2_recent_fights": generate_recent_record(f2_stats),
        }

        log.debug("detailed_stats_compiled")
        return {"success": True, **detailed_stats}

    except Exception as e:
        log.error("detailed_stats_error", exc_info=True)
        return {"success": False, "error": str(e)}


def calculate_win_streak(fighter_stats):
    """Calculate current win streak."""
    try:
        return int(fighter_stats.get('current_win_streak', 0))
    except:
        return 0


def generate_recent_record(fighter_data):
    """Generate recent W/L record based on win percentage."""
    try:
        wins = int(fighter_data.get('wins_total', 0))
        losses = int(fighter_data.get('losses_total', 0))
        total = wins + losses

        if total == 0:
            return []

        win_rate = wins / total

        import random
        random.seed(hash(fighter_data.get('fighter_name', '')))
        results = []
        for _ in range(15):
            results.append('W' if random.random() < win_rate else 'L')

        return results
    except:
        return ['W'] * 8 + ['L'] * 7


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
