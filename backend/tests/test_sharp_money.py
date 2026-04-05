"""
Tests for intelligence/sharp_money.py (PRD §10.9).

MARKET_ALIGNMENT fires when:
    (current_implied > opening_implied AND model_prob > 0.55) OR
    (current_implied < opening_implied AND model_prob < 0.45)
    AND movement_magnitude > 0.03
Otherwise NEUTRAL.
"""

import pytest
from sqlalchemy import text

from intelligence.sharp_money import compute
from intelligence.models import SharpMoneyResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_event_and_fight(conn, fight_id, f1_name, f2_name):
    conn.execute(text("""
        INSERT INTO events (event_name, event_date, is_published)
        VALUES ('Test Event', '2024-06-01', 0)
    """))
    conn.execute(text("""
        INSERT INTO event_fights (event_id, fighter1_name, fighter2_name)
        VALUES (1, :f1, :f2)
    """), {"f1": f1_name, "f2": f2_name})


def _seed_odds(conn, fight_id, fighter_name, implied, is_opener, recorded_at):
    conn.execute(text("""
        INSERT INTO odds_history
          (fight_id, fighter_name, american_odds, implied_probability,
           is_opening_line, recorded_at)
        VALUES (:fid, :name, 0, :imp, :open, :ts)
    """), {
        "fid": fight_id, "name": fighter_name, "imp": implied,
        "open": 1 if is_opener else 0, "ts": recorded_at,
    })


# ---------------------------------------------------------------------------
# Neutral / no-data paths
# ---------------------------------------------------------------------------

def test_no_fight_id_returns_neutral(engine, f1_ctx, f2_ctx):
    result = compute(
        f1_ctx, f2_ctx, engine=engine, fight_id=None,
        model_prob_f1=0.60, model_prob_f2=0.40,
    )
    assert isinstance(result, SharpMoneyResult)
    assert result.signal == "NEUTRAL"
    assert result.aligned is False
    assert result.movement_magnitude == 0.0


def test_missing_model_probs_returns_neutral(engine, f1_ctx, f2_ctx):
    result = compute(
        f1_ctx, f2_ctx, engine=engine, fight_id=1,
        model_prob_f1=None, model_prob_f2=None,
    )
    assert result.signal == "NEUTRAL"


def test_no_odds_rows_returns_neutral(engine, f1_ctx, f2_ctx):
    result = compute(
        f1_ctx, f2_ctx, engine=engine, fight_id=9999,
        model_prob_f1=0.60, model_prob_f2=0.40,
    )
    assert result.signal == "NEUTRAL"


def test_single_snapshot_returns_neutral(engine, f1_ctx, f2_ctx):
    """One snapshot per fighter is insufficient to measure movement."""
    with engine.begin() as conn:
        _seed_event_and_fight(conn, 1, f1_ctx.name, f2_ctx.name)
        _seed_odds(conn, 1, f1_ctx.name, 0.55, True, "2024-06-01 09:00:00")

    result = compute(
        f1_ctx, f2_ctx, engine=engine, fight_id=1,
        model_prob_f1=0.60, model_prob_f2=0.40,
    )
    assert result.signal == "NEUTRAL"


# ---------------------------------------------------------------------------
# MARKET_ALIGNMENT: line moves toward model
# ---------------------------------------------------------------------------

def test_line_moves_toward_model_favorite_fires(engine, f1_ctx, f2_ctx):
    """
    Model says f1 at 60%. Opening 0.52, current 0.58 → moved toward model.
    Movement magnitude 0.06 > 0.03 → MARKET_ALIGNMENT.
    """
    with engine.begin() as conn:
        _seed_event_and_fight(conn, 1, f1_ctx.name, f2_ctx.name)
        _seed_odds(conn, 1, f1_ctx.name, 0.52, True,  "2024-06-01 09:00:00")
        _seed_odds(conn, 1, f2_ctx.name, 0.48, True,  "2024-06-01 09:00:00")
        _seed_odds(conn, 1, f1_ctx.name, 0.58, False, "2024-06-01 15:00:00")
        _seed_odds(conn, 1, f2_ctx.name, 0.42, False, "2024-06-01 15:00:00")

    result = compute(
        f1_ctx, f2_ctx, engine=engine, fight_id=1,
        model_prob_f1=0.60, model_prob_f2=0.40,
    )
    assert result.signal == "MARKET_ALIGNMENT"
    assert result.aligned is True
    assert result.movement_magnitude == pytest.approx(0.06)


def test_line_moves_toward_model_underdog_fires(engine, f1_ctx, f2_ctx):
    """
    Model says f1 at 30%. f1's implied drops 0.50 → 0.42 (moved away from f1).
    model_prob_f1 < 0.45 AND current < opening → MARKET_ALIGNMENT.
    """
    with engine.begin() as conn:
        _seed_event_and_fight(conn, 1, f1_ctx.name, f2_ctx.name)
        _seed_odds(conn, 1, f1_ctx.name, 0.50, True,  "2024-06-01 09:00:00")
        _seed_odds(conn, 1, f2_ctx.name, 0.50, True,  "2024-06-01 09:00:00")
        _seed_odds(conn, 1, f1_ctx.name, 0.42, False, "2024-06-01 15:00:00")
        _seed_odds(conn, 1, f2_ctx.name, 0.58, False, "2024-06-01 15:00:00")

    result = compute(
        f1_ctx, f2_ctx, engine=engine, fight_id=1,
        model_prob_f1=0.30, model_prob_f2=0.70,
    )
    assert result.signal == "MARKET_ALIGNMENT"
    assert result.movement_magnitude == pytest.approx(0.08)


# ---------------------------------------------------------------------------
# NEUTRAL: conditions not met
# ---------------------------------------------------------------------------

def test_line_moves_away_from_model_returns_neutral(engine, f1_ctx, f2_ctx):
    """Model says f1 favorite but line moves against f1 → NEUTRAL."""
    with engine.begin() as conn:
        _seed_event_and_fight(conn, 1, f1_ctx.name, f2_ctx.name)
        _seed_odds(conn, 1, f1_ctx.name, 0.55, True,  "2024-06-01 09:00:00")
        _seed_odds(conn, 1, f1_ctx.name, 0.48, False, "2024-06-01 15:00:00")

    result = compute(
        f1_ctx, f2_ctx, engine=engine, fight_id=1,
        model_prob_f1=0.70, model_prob_f2=0.30,
    )
    assert result.signal == "NEUTRAL"
    # Line still "moved" by 0.07 but NOT toward model
    assert result.aligned is False


def test_movement_below_threshold_returns_neutral(engine, f1_ctx, f2_ctx):
    """
    Line moves toward model but magnitude <= 0.03 → NEUTRAL (aligned=True still).
    """
    with engine.begin() as conn:
        _seed_event_and_fight(conn, 1, f1_ctx.name, f2_ctx.name)
        _seed_odds(conn, 1, f1_ctx.name, 0.55, True,  "2024-06-01 09:00:00")
        _seed_odds(conn, 1, f1_ctx.name, 0.57, False, "2024-06-01 15:00:00")

    result = compute(
        f1_ctx, f2_ctx, engine=engine, fight_id=1,
        model_prob_f1=0.62, model_prob_f2=0.38,
    )
    assert result.signal == "NEUTRAL"
    assert result.movement_magnitude == pytest.approx(0.02)
    # Direction agrees (aligned=True), but magnitude fails threshold
    assert result.aligned is True


def test_moderate_model_with_line_movement_returns_neutral(engine, f1_ctx, f2_ctx):
    """
    Model says 0.50/0.50 (not > 0.55 or < 0.45). Line moves but model
    has no strong opinion → NEUTRAL.
    """
    with engine.begin() as conn:
        _seed_event_and_fight(conn, 1, f1_ctx.name, f2_ctx.name)
        _seed_odds(conn, 1, f1_ctx.name, 0.45, True,  "2024-06-01 09:00:00")
        _seed_odds(conn, 1, f1_ctx.name, 0.55, False, "2024-06-01 15:00:00")

    result = compute(
        f1_ctx, f2_ctx, engine=engine, fight_id=1,
        model_prob_f1=0.50, model_prob_f2=0.50,
    )
    assert result.signal == "NEUTRAL"


# ---------------------------------------------------------------------------
# Fallback: no explicit opening_line flag
# ---------------------------------------------------------------------------

def test_uses_earliest_row_as_opening_when_flag_missing(engine, f1_ctx, f2_ctx):
    """With no is_opening_line=True row, earliest ASC row is the opener."""
    with engine.begin() as conn:
        _seed_event_and_fight(conn, 1, f1_ctx.name, f2_ctx.name)
        _seed_odds(conn, 1, f1_ctx.name, 0.50, False, "2024-06-01 09:00:00")
        _seed_odds(conn, 1, f1_ctx.name, 0.60, False, "2024-06-01 15:00:00")

    result = compute(
        f1_ctx, f2_ctx, engine=engine, fight_id=1,
        model_prob_f1=0.70, model_prob_f2=0.30,
    )
    assert result.signal == "MARKET_ALIGNMENT"
    assert result.movement_magnitude == pytest.approx(0.10)


def test_result_is_valid_pydantic_model(engine, f1_ctx, f2_ctx):
    result = compute(
        f1_ctx, f2_ctx, engine=engine, fight_id=None,
        model_prob_f1=0.60, model_prob_f2=0.40,
    )
    rehydrated = SharpMoneyResult(**result.model_dump())
    assert rehydrated.signal == "NEUTRAL"
