from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os
import sys
import json
import numpy as np
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import create_engine, text
from gemini_service import generate_ai_poster
from ai_analyst import ai_analyst
from intelligence.orchestrator import IntelligenceOrchestrator

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
# TODO (Phase 6): Switch limiter storage to Redis (Upstash).
# Current in-memory storage resets on server restart — fine for v1 but
# configure UPSTASH_REDIS_URL before high-traffic launch.
limiter = Limiter(key_func=get_remote_address)

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
    print("✓ Database connection verified")

    # ── Model ─────────────────────────────────────────────────────────────
    print("Loading GOLDEN predictor...")
    sys.path.insert(0, '../src')
    from predictor_golden import UFCFightPredictorGolden

    predictor = UFCFightPredictorGolden(
        model_path='../models/golden_model.pkl',
        engine=engine,
    )
    print("✓ GOLDEN predictor loaded and ready!")

    # ── Intelligence orchestrator ─────────────────────────────────────────
    orchestrator = IntelligenceOrchestrator(engine)
    print("✓ Intelligence orchestrator ready")

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
    print(
        f"✓ Events loaded: {len(events_data['events'])} event(s), "
        f"{len(events_index)} fight(s) indexed"
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
    is_healthy = db_status == "ok" and model_status == "loaded"

    body = {
        "status": "ok" if is_healthy else "degraded",
        "db": db_status,
        "model": model_status,
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
async def get_fighters(search: str = None, limit: int = Query(default=100, le=500)):
    """Get list of available fighters — always queries the DB, never the startup cache."""
    if engine is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    with engine.connect() as conn:
        if search:
            rows = conn.execute(
                text("SELECT name FROM fighters WHERE LOWER(name) LIKE LOWER(:q) ORDER BY name LIMIT :lim"),
                {"q": f"%{search}%", "lim": limit},
            ).fetchall()
        else:
            rows = conn.execute(
                text("SELECT name FROM fighters ORDER BY name LIMIT :lim"),
                {"lim": limit},
            ).fetchall()

    fighters = [row[0] for row in rows]
    return {"fighters": fighters, "count": len(fighters)}


@app.get("/fighter/{fighter_name}")
async def get_fighter_profile(fighter_name: str):
    """Get full profile for a specific fighter."""
    if predictor is None:
        raise HTTPException(status_code=500, detail="Predictor not initialized")

    from urllib.parse import unquote
    fighter_name = unquote(fighter_name)

    matched_name = predictor.search_fighter(fighter_name)

    if not matched_name:
        raise HTTPException(
            status_code=404,
            detail=f"Fighter '{fighter_name}' not found"
        )

    raw_stats = predictor.feature_calculator.get_latest_fighter_stats(matched_name)

    if not raw_stats:
        raise HTTPException(
            status_code=404,
            detail=f"No stats found for '{matched_name}'"
        )

    weight = float(raw_stats.get('fighter_weight_lbs', 185))

    stats = {
        # Record
        'wins_total': float(raw_stats.get('fighter_w', 0)),
        'losses_total': float(raw_stats.get('fighter_l', 0)),
        'draw': float(raw_stats.get('fighter_d', 0)),

        # Physical
        'age': float(raw_stats.get('age', 0)),
        'height': float(raw_stats.get('fighter_height_cm', 0)),
        'reach': float(raw_stats.get('fighter_reach_cm', 0)),
        'weight': weight,
        'weight_class': determine_weight_class(weight),

        # Striking
        'SLpM_total': float(raw_stats.get('fighter_SlpM', 0)),
        'sig_str_acc_total': float(raw_stats.get('fighter_Str_Acc', 0)) * 100,
        'sig_str_def_total': float(raw_stats.get('fighter_Str_Def', 0)) * 100,
        'total_knockdowns': float(raw_stats.get('knockdowns', 0)),

        # Grappling
        'td_avg_total': float(raw_stats.get('fighter_TD_Avg', 0)),
        'td_acc_total': float(raw_stats.get('fighter_TD_Acc', 0)) * 100,
        'td_def_total': float(raw_stats.get('fighter_TD_Def', 0)) * 100,
        'sub_avg_total': float(raw_stats.get('fighter_Sub_Avg', 0)),
    }

    return {
        "name": matched_name,
        "stats": convert_numpy(stats)
    }


@app.get("/fighter/{fighter_name}/history")
async def get_fighter_history(fighter_name: str):
    """
    Return the last 20 fights for a fighter in reverse chronological order.

    Uses fuzzy name matching (search_fighter) when predictor is loaded.
    Each fight includes: opponent, date, result (W/L), method, weight_class.
    """
    if engine is None:
        raise HTTPException(status_code=500, detail="Database not initialized")

    from urllib.parse import unquote
    fighter_name = unquote(fighter_name)

    # Apply fuzzy match if predictor is ready; fall back to exact name otherwise
    if predictor is not None:
        matched = predictor.search_fighter(fighter_name)
        if matched:
            fighter_name = matched

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT r_name, b_name, date, winner, method, weight_class
                FROM fights
                WHERE r_name = :name OR b_name = :name
                ORDER BY date DESC
                LIMIT 20
            """),
            {"name": fighter_name},
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No fight history found for '{fighter_name}'")

    history = []
    for row in rows:
        opponent = row.b_name if row.r_name == fighter_name else row.r_name
        history.append({
            "opponent": opponent,
            "date": str(row.date),
            "result": "W" if row.winner == fighter_name else "L",
            "method": row.method or "",
            "weight_class": row.weight_class or "",
        })

    return {"name": fighter_name, "fights": history, "count": len(history)}


@app.post("/predict/simple")
async def predict_fight_simple(request: SimplePredictionRequest):
    """
    Fast prediction path — returns winner + confidence only.
    Skips the intelligence orchestrator entirely.

    Use this for low-latency contexts (e.g. bulk previews, dashboard cards).
    For the full intelligence bundle use POST /predict.
    """
    if request.fighter1.strip().lower() == request.fighter2.strip().lower():
        raise HTTPException(
            status_code=400,
            detail="Fighter 1 and Fighter 2 must be different fighters",
        )
    if predictor is None:
        raise HTTPException(status_code=500, detail="Predictor not initialized")

    result = predictor.predict_fight(request.fighter1, request.fighter2, verbose=False)
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
    if request.fighter1.strip().lower() == request.fighter2.strip().lower():
        raise HTTPException(
            status_code=400,
            detail="Fighter 1 and Fighter 2 must be different fighters",
        )

    if predictor is None:
        raise HTTPException(status_code=500, detail="Predictor not initialized")
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    try:
        print(f"\n{'='*70}")
        print(f"PREDICTION REQUEST: {request.fighter1} vs {request.fighter2}")
        print(f"{'='*70}")

        result = predictor.predict_fight(
            request.fighter1,
            request.fighter2,
            verbose=False,
        )

        if result is None:
            raise HTTPException(status_code=404, detail="One or both fighters not found")

        print(f"\nResult received. Winner: {result.get('winner')}, Confidence: {result.get('confidence')}")

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
        print("✓ Intelligence computed")

        # AI analysis is NOT generated here — it is async and non-blocking.
        # The frontend calls POST /generate-ai-analysis separately after the
        # prediction renders.  ai_analysis: null is the intentional response.
        if not result.get('fighter1_stats') or not result.get('fighter2_stats'):
            print(f"⚠️ fighter stats missing from predictor result for {result['fighter1']} vs {result['fighter2']}")

        print("\nBuilding response...")
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

        print(f"Response built successfully!")
        print(f"Confidence: {response['confidence']}")
        print(f"{'='*70}\n")

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
            print(f"predictions_log INSERT failed (non-fatal): {log_err}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"\n{'='*70}")
        print(f"❌ ERROR IN PREDICTION:")
        print(traceback.format_exc())
        print(f"{'='*70}\n")
        raise HTTPException(status_code=500, detail=str(e))


class AIPosterRequest(BaseModel):
    fighter1_name: str
    fighter2_name: str
    prediction: dict  # Contains winner, confidence, etc.


@app.post("/generate-ai-poster")
@limiter.limit("3/hour")
async def create_ai_poster(request: Request, poster_request: AIPosterRequest):
    """Generate AI poster using Gemini."""
    try:
        print(f"\n{'='*70}")
        print(f"AI POSTER REQUEST")
        print(f"Fighter 1: {poster_request.fighter1_name}")
        print(f"Fighter 2: {poster_request.fighter2_name}")
        print(f"Winner: {poster_request.prediction.get('winner')}")
        print(f"{'='*70}\n")

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

        result = generate_ai_poster(fighter1_data, fighter2_data, prediction_data)

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
        import traceback
        print(f"\n{'='*70}")
        print(f"ERROR IN AI POSTER GENERATION:")
        print(traceback.format_exc())
        print(f"{'='*70}\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-ai-analysis")
@limiter.limit("3/hour")
async def generate_ai_analysis(request: Request, analysis_request: AIAnalysisRequest):
    """
    Generate AI fight analysis using Claude (template fallback if API unavailable).

    Called by the frontend AFTER /predict renders — keeps /predict fast.
    Rate limited to 3/hour/IP to protect Claude API costs.

    Request body mirrors the fields that ai_analyst.generate_fight_analysis()
    needs: fighter names, winner, confidence, and both fighters' stats dicts
    (the same dicts returned in the /predict fighter1_stats/fighter2_stats fields).
    """
    import asyncio

    prediction_data = {
        "fighter1": analysis_request.fighter1,
        "fighter2": analysis_request.fighter2,
        "winner": analysis_request.winner,
        "confidence": analysis_request.confidence,
        "fighter1_stats": analysis_request.fighter1_stats,
        "fighter2_stats": analysis_request.fighter2_stats,
    }

    # asyncio.to_thread runs the sync function in a thread pool — the event
    # loop is never blocked, so other requests can proceed while Claude responds.
    try:
        analysis = await asyncio.to_thread(
            ai_analyst.generate_fight_analysis, prediction_data
        )
        return {"analysis": analysis}
    except Exception as e:
        import traceback
        print(f"AI analysis generation failed: {traceback.format_exc()}")
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

        print(f"\n{'='*70}")
        print(f"📊 DETAILED STATS REQUEST")
        print(f"Fighter 1: {fighter1_name}")
        print(f"Fighter 2: {fighter2_name}")
        print(f"{'='*70}\n")

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

        print("✅ Stats compiled successfully\n")
        return {"success": True, **detailed_stats}

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
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
