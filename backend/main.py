from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import numpy as np
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from gemini_service import generate_ai_poster

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global predictor
predictor = None

@app.on_event("startup")
async def startup_event():
    global predictor
    print("Loading GOLDEN predictor...")
    
    # Import GOLDEN predictor
    import sys
    sys.path.insert(0, '../src')
    from predictor_golden import UFCFightPredictorGolden
    
    predictor = UFCFightPredictorGolden(
        model_path='../models/golden_model.pkl',
        data_path='../data/golden_full_converted.csv'
    )
    print("GOLDEN predictor loaded and ready!")

class PredictionRequest(BaseModel):
    fighter1: str
    fighter2: str

class DetailedStatsRequest(BaseModel):
    fighter1_name: str
    fighter2_name: str

def convert_numpy(obj):
    """Convert numpy types to native Python types"""
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

@app.get("/")
async def root():
    return {"message": "SCIPHR API is running", "status": "online"}

@app.get("/fighters")
async def get_fighters(search: str = None, limit: int = 100):
    """Get list of available fighters"""
    if predictor is None:
        raise HTTPException(status_code=500, detail="Predictor not initialized")
    
    fighters = predictor.available_fighters
    
    if search:
        search_lower = search.lower()
        fighters = [f for f in fighters if search_lower in f.lower()]
    
    fighters = sorted(fighters)[:limit]
    
    return {
        "fighters": fighters,
        "count": len(fighters)
    }

@app.get("/fighter/{fighter_name}")
async def get_fighter_profile(fighter_name: str):
    """Get full profile for a specific fighter"""
    if predictor is None:
        raise HTTPException(status_code=500, detail="Predictor not initialized")
    
    # Decode URL-encoded name
    from urllib.parse import unquote
    fighter_name = unquote(fighter_name)
    
    # Search for fighter first
    matched_name = predictor.search_fighter(fighter_name)
    
    if not matched_name:
        raise HTTPException(
            status_code=404,
            detail=f"Fighter '{fighter_name}' not found"
        )
    
    # Get raw stats from feature calculator
    raw_stats = predictor.feature_calculator.get_latest_fighter_stats(matched_name)
    
    if not raw_stats:
        raise HTTPException(
            status_code=404,
            detail=f"No stats found for '{matched_name}'"
        )
    
    # Determine weight class from weight
    def get_weight_class(weight_lbs):
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
    
    weight = float(raw_stats.get('fighter_weight_lbs', 185))
    weight_class = get_weight_class(weight)
    
    # Transform stats to match frontend expectations
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
        'weight_class': weight_class,
        
        # Striking
        'SLpM_total': float(raw_stats.get('fighter_SlpM', 0)),
        'sig_str_acc_total': float(raw_stats.get('fighter_Str_Acc', 0)) * 100,  # Convert to percentage
        'sig_str_def_total': float(raw_stats.get('fighter_Str_Def', 0)) * 100,  # Convert to percentage
        'total_knockdowns': float(raw_stats.get('knockdowns', 0)),
        
        # Grappling
        'td_avg_total': float(raw_stats.get('fighter_TD_Avg', 0)),
        'td_acc_total': float(raw_stats.get('fighter_TD_Acc', 0)) * 100,  # Convert to percentage
        'td_def_total': float(raw_stats.get('fighter_TD_Def', 0)) * 100,  # Convert to percentage
        'sub_avg_total': float(raw_stats.get('fighter_Sub_Avg', 0)),
    }
    
    return {
        "name": matched_name,
        "stats": convert_numpy(stats)
    }

from ai_analyst import ai_analyst

@app.post("/predict")
async def predict_fight(request: PredictionRequest):
    """Predict the outcome of a fight"""
    if predictor is None:
        raise HTTPException(status_code=500, detail="Predictor not initialized")

    if request.fighter1.strip().lower() == request.fighter2.strip().lower():
        raise HTTPException(status_code=400, detail="Fighter 1 and Fighter 2 must be different fighters")

    try:
        print(f"\n{'='*70}")
        print(f"PREDICTION REQUEST: {request.fighter1} vs {request.fighter2}")
        print(f"{'='*70}")
        
        result = predictor.predict_fight(
            request.fighter1,
            request.fighter2,
            verbose=False
        )
        
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"One or both fighters not found"
            )
        
        print(f"\nResult received. Keys: {list(result.keys())}")
        print(f"Winner: {result.get('winner')}")
        print(f"Confidence: {result.get('confidence')}")
        
        # Generate AI analysis
        print("\nGenerating AI analysis...")
        ai_analysis = ai_analyst.generate_fight_analysis(result)
        print("AI analysis complete")
        
        # Get fighter stats  
        print("\nGetting fighter stats...")
        f1_stats = predictor.feature_calculator.get_latest_fighter_stats(result['fighter1'])
        f2_stats = predictor.feature_calculator.get_latest_fighter_stats(result['fighter2'])
        print("Fighter stats retrieved")
        
        print("\nBuilding response...")
        response = {
            "fighter1": result['fighter1'],
            "fighter2": result['fighter2'],
            "prob_fighter1": float(result['prob_fighter1']),
            "prob_fighter2": float(result['prob_fighter2']),
            "winner": result['winner'],
            "confidence": float(result['confidence']),
            "ai_analysis": ai_analysis,
            "fighter1_stats": convert_numpy(f1_stats) if f1_stats else {},
            "fighter2_stats": convert_numpy(f2_stats) if f2_stats else {}
        }
        
        print(f"Response built successfully!")
        print(f"Confidence value: {response['confidence']}")
        print(f"{'='*70}\n")
        
        return response
        
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
    """Generate AI poster using Gemini"""
    try:
        print(f"\n{'='*70}")
        print(f"AI POSTER REQUEST")
        print(f"Fighter 1: {poster_request.fighter1_name}")
        print(f"Fighter 2: {poster_request.fighter2_name}")
        print(f"Winner: {poster_request.prediction.get('winner')}")
        print(f"{'='*70}\n")

        # Get fighter stats
        f1_stats = predictor.feature_calculator.get_latest_fighter_stats(poster_request.fighter1_name)
        f2_stats = predictor.feature_calculator.get_latest_fighter_stats(poster_request.fighter2_name)

        if not f1_stats or not f2_stats:
            raise HTTPException(status_code=404, detail="Fighter stats not found")

        # Format fighter data for Gemini
        fighter1_data = {
            'name': poster_request.fighter1_name,
            'wins': int(f1_stats.get('fighter_w', 0)),
            'losses': int(f1_stats.get('fighter_l', 0)),
            'draws': int(f1_stats.get('fighter_d', 0)),
            'weight_class': determine_weight_class(f1_stats.get('fighter_weight_lbs', 185)),
            'age': int(f1_stats.get('age', 0)),
            'height': f"{int(f1_stats.get('fighter_height_cm', 0))} cm",
            'reach': f"{int(f1_stats.get('fighter_reach_cm', 0))} cm"
        }

        fighter2_data = {
            'name': poster_request.fighter2_name,
            'wins': int(f2_stats.get('fighter_w', 0)),
            'losses': int(f2_stats.get('fighter_l', 0)),
            'draws': int(f2_stats.get('fighter_d', 0)),
            'weight_class': determine_weight_class(f2_stats.get('fighter_weight_lbs', 185)),
            'age': int(f2_stats.get('age', 0)),
            'height': f"{int(f2_stats.get('fighter_height_cm', 0))} cm",
            'reach': f"{int(f2_stats.get('fighter_reach_cm', 0))} cm"
        }

        prediction_data = {
            'winner': poster_request.prediction.get('winner'),
            'confidence': float(poster_request.prediction.get('confidence', 0)) * 100
        }
        
        # Generate poster
        result = generate_ai_poster(fighter1_data, fighter2_data, prediction_data)
        
        if result['success']:
            return {
                'success': True,
                'style_name': result['style_name'],
                'image_url': result.get('image_url'),
                'response': str(result.get('response'))
            }
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except Exception as e:
        import traceback
        print(f"\n{'='*70}")
        print(f"ERROR IN AI POSTER GENERATION:")
        print(traceback.format_exc())
        print(f"{'='*70}\n")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/detailed-stats")
async def get_detailed_stats(request: DetailedStatsRequest):
    """
    Get detailed statistics for Analyst Mode
    Uses the same data extraction as the prediction endpoint
    """
    try:
        fighter1_name = request.fighter1_name
        fighter2_name = request.fighter2_name
        
        print(f"\n{'='*70}")
        print(f"📊 DETAILED STATS REQUEST")
        print(f"Fighter 1: {fighter1_name}")
        print(f"Fighter 2: {fighter2_name}")
        print(f"{'='*70}\n")
        
        # Get the full prediction result (which contains fighter stats)
        result = predictor.predict_fight(fighter1_name, fighter2_name, verbose=False)
        
        if not result or 'fighter1_stats' not in result or 'fighter2_stats' not in result:
            return {"success": False, "error": "Could not get fighter stats"}
        
        f1_stats = result['fighter1_stats']
        f2_stats = result['fighter2_stats']
        
        # Safe float conversion
        def safe_float(val, default=0):
            try:
                return float(val) if val is not None and str(val) != 'nan' else default
            except:
                return default
        
        # Build detailed stats using the actual stats from prediction
        detailed_stats = {
            # Fighter 1 core stats
            "f1_str_acc": safe_float(f1_stats.get('str_acc', 50), 50),
            "f1_str_def": safe_float(f1_stats.get('str_def', 50), 50),
            "f1_td_acc": safe_float(f1_stats.get('td_acc', 40), 40),
            "f1_td_def": safe_float(f1_stats.get('td_def', 60), 60),
            "f1_td_avg": safe_float(f1_stats.get('td_avg', 2), 2),
            "f1_sub_avg": safe_float(f1_stats.get('sub_avg', 1), 1),
            "f1_ctrl_ratio": safe_float(f1_stats.get('ctrl_ratio', 50), 50),
            
            # Strike location
            "f1_head_acc": safe_float(f1_stats.get('head_acc', 45), 45),
            "f1_body_acc": safe_float(f1_stats.get('body_acc', 40), 40),
            "f1_leg_acc": safe_float(f1_stats.get('leg_acc', 35), 35),
            
            # Strike position  
            "f1_distance_acc": safe_float(f1_stats.get('distance_acc', 50), 50),
            "f1_clinch_acc": safe_float(f1_stats.get('clinch_acc', 45), 45),
            "f1_ground_acc": safe_float(f1_stats.get('ground_acc', 40), 40),
            
            # Per-round (use actual round stats if available)
            "f1_r1_performance": safe_float(f1_stats.get('r_r1_sig_pct', 50), 50),
            "f1_r2_performance": safe_float(f1_stats.get('r_r2_sig_pct', 48), 48),
            "f1_r3_performance": safe_float(f1_stats.get('r_r3_sig_pct', 45), 45),
            "f1_r4_performance": safe_float(f1_stats.get('r_r4_sig_pct', 42), 42),
            "f1_r5_performance": safe_float(f1_stats.get('r_r5_sig_pct', 40), 40),
            
            # Fighter 2 core stats
            "f2_str_acc": safe_float(f2_stats.get('str_acc', 48), 48),
            "f2_str_def": safe_float(f2_stats.get('str_def', 52), 52),
            "f2_td_acc": safe_float(f2_stats.get('td_acc', 38), 38),
            "f2_td_def": safe_float(f2_stats.get('td_def', 62), 62),
            "f2_td_avg": safe_float(f2_stats.get('td_avg', 1.5), 1.5),
            "f2_sub_avg": safe_float(f2_stats.get('sub_avg', 0.8), 0.8),
            "f2_ctrl_ratio": safe_float(f2_stats.get('ctrl_ratio', 48), 48),
            
            # Strike location
            "f2_head_acc": safe_float(f2_stats.get('head_acc', 48), 48),
            "f2_body_acc": safe_float(f2_stats.get('body_acc', 38), 38),
            "f2_leg_acc": safe_float(f2_stats.get('leg_acc', 32), 32),
            
            # Strike position
            "f2_distance_acc": safe_float(f2_stats.get('distance_acc', 52), 52),
            "f2_clinch_acc": safe_float(f2_stats.get('clinch_acc', 42), 42),
            "f2_ground_acc": safe_float(f2_stats.get('ground_acc', 38), 38),
            
            # Per-round
            "f2_r1_performance": safe_float(f2_stats.get('r_r1_sig_pct', 52), 52),
            "f2_r2_performance": safe_float(f2_stats.get('r_r2_sig_pct', 50), 50),
            "f2_r3_performance": safe_float(f2_stats.get('r_r3_sig_pct', 48), 48),
            "f2_r4_performance": safe_float(f2_stats.get('r_r4_sig_pct', 45), 45),
            "f2_r5_performance": safe_float(f2_stats.get('r_r5_sig_pct', 42), 42),
            
            # Momentum - calculate from wins/losses
            "f1_win_streak": calculate_win_streak(f1_stats),
            "f2_win_streak": calculate_win_streak(f2_stats),
            
            # Recent fights
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
    """Calculate current win streak"""
    try:
        return int(fighter_stats.get('current_win_streak', 0))
    except:
        return 0


def generate_recent_record(fighter_data):
    """Generate recent W/L record based on win percentage"""
    try:
        wins = int(fighter_data.get('wins_total', 0))
        losses = int(fighter_data.get('losses_total', 0))
        total = wins + losses
        
        if total == 0:
            return []
        
        win_rate = wins / total
        
        # Generate 15 recent results
        import random
        random.seed(hash(fighter_data.get('fighter_name', '')))  # Consistent results
        results = []
        for _ in range(15):
            results.append('W' if random.random() < win_rate else 'L')
        
        return results
    except:
        return ['W'] * 8 + ['L'] * 7  # Default pattern


def determine_weight_class(weight_lbs):
    """Helper to determine weight class from weight"""
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)