"""
Tests for intelligence/value_bet.py

NO_ODDS paths + Kelly calc path — all active.
"""

import pytest

from intelligence.value_bet import compute
from intelligence.models import ValueBetResult


# ---------------------------------------------------------------------------
# NO_ODDS paths
# ---------------------------------------------------------------------------

def test_no_fight_id_returns_no_odds(engine, f1_ctx, f2_ctx):
    result = compute(f1_ctx, f2_ctx, engine=engine, fight_id=None)
    assert isinstance(result, ValueBetResult)
    assert result.signal == "NO_ODDS"
    assert result.active is False
    assert result.edge_pct is None
    assert result.kelly_fraction is None


def test_fight_id_with_no_odds_rows_returns_no_odds(engine, f1_ctx, f2_ctx):
    result = compute(
        f1_ctx, f2_ctx, engine=engine,
        fight_id=9999,
        model_prob_f1=0.60,
        model_prob_f2=0.40,
    )
    assert result.signal == "NO_ODDS"
    assert result.active is False


def test_no_odds_result_is_valid_pydantic_model(engine, f1_ctx, f2_ctx):
    result = compute(f1_ctx, f2_ctx, engine=engine, fight_id=None)
    rehydrated = ValueBetResult(**result.model_dump())
    assert rehydrated.signal == "NO_ODDS"


# ---------------------------------------------------------------------------
# Kelly calc path
# ---------------------------------------------------------------------------

def test_strong_edge_when_model_strongly_disagrees(engine, f1_ctx, f2_ctx):
    """
    model_prob_f1=0.70 but market implies 0.5595 for f1.
    edge = 0.70 - 0.5595 = 0.14 -> kelly ~0.32 -> STRONG_EDGE.
    """
    from sqlalchemy import text

    fight_id = 1
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO events (event_name, event_date, is_published)
            VALUES ('Test Event', '2024-06-01', 0)
        """))
        conn.execute(text("""
            INSERT INTO event_fights (event_id, fighter1_name, fighter2_name)
            VALUES (1, :f1, :f2)
        """), {"f1": f1_ctx.name, "f2": f2_ctx.name})
        conn.execute(text("""
            INSERT INTO odds_history
              (fight_id, fighter_name, american_odds, implied_probability, is_opening_line)
            VALUES
              (:fid, :f1, -127, 0.5595, 1),
              (:fid, :f2, 107, 0.4831, 1)
        """), {"fid": fight_id, "f1": f1_ctx.name, "f2": f2_ctx.name})

    result = compute(
        f1_ctx, f2_ctx, engine=engine,
        fight_id=fight_id,
        model_prob_f1=0.70,
        model_prob_f2=0.30,
    )

    assert result.signal in ("EDGE_DETECTED", "STRONG_EDGE")
    assert result.active is True
    assert result.edge_pct is not None
    assert result.edge_pct > 0.10
    assert result.kelly_fraction is not None
    assert 0.0 < result.kelly_fraction <= 0.5


def test_no_edge_when_model_agrees_with_market(engine, f1_ctx, f2_ctx):
    """When model_prob matches implied_prob closely -> NO_EDGE."""
    from sqlalchemy import text

    fight_id = 2
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO events (event_name, event_date, is_published)
            VALUES ('Test Event 2', '2024-07-01', 0)
        """))
        conn.execute(text("""
            INSERT INTO event_fights (event_id, fighter1_name, fighter2_name)
            VALUES (1, :f1, :f2)
        """), {"f1": f1_ctx.name, "f2": f2_ctx.name})
        conn.execute(text("""
            INSERT INTO odds_history
              (fight_id, fighter_name, american_odds, implied_probability, is_opening_line)
            VALUES
              (:fid, :f1, -165, 0.6226, 1),
              (:fid, :f2, 140, 0.4167, 1)
        """), {"fid": fight_id, "f1": f1_ctx.name, "f2": f2_ctx.name})

    result = compute(
        f1_ctx, f2_ctx, engine=engine,
        fight_id=fight_id,
        model_prob_f1=0.62,
        model_prob_f2=0.38,
    )
    assert result.signal == "NO_EDGE"
    assert result.active is True


def test_fade_opportunity_when_model_disagrees_with_favourite(engine, f1_ctx, f2_ctx):
    """
    model_prob_f1=0.35 but market has f1 as -200 favourite (implied=0.67).
    Model strongly disagrees with the favourite -> FADE_OPPORTUNITY.
    """
    from sqlalchemy import text

    fight_id = 3
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO events (event_name, event_date, is_published)
            VALUES ('Test Event 3', '2024-08-01', 0)
        """))
        conn.execute(text("""
            INSERT INTO event_fights (event_id, fighter1_name, fighter2_name)
            VALUES (1, :f1, :f2)
        """), {"f1": f1_ctx.name, "f2": f2_ctx.name})
        conn.execute(text("""
            INSERT INTO odds_history
              (fight_id, fighter_name, american_odds, implied_probability, is_opening_line)
            VALUES
              (:fid, :f1, -200, 0.6667, 1),
              (:fid, :f2, 170, 0.3704, 1)
        """), {"fid": fight_id, "f1": f1_ctx.name, "f2": f2_ctx.name})

    result = compute(
        f1_ctx, f2_ctx, engine=engine,
        fight_id=fight_id,
        model_prob_f1=0.35,
        model_prob_f2=0.65,
    )
    assert result.signal == "FADE_OPPORTUNITY"
    assert result.active is True
    assert result.edge_pct is not None
    assert result.edge_pct < -0.10


def test_result_fields_all_populated_when_edge_found(engine, f1_ctx, f2_ctx):
    """When EDGE_DETECTED or STRONG_EDGE, all result fields should be non-None."""
    from sqlalchemy import text

    fight_id = 4
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO events (event_name, event_date, is_published)
            VALUES ('Test Event 4', '2024-09-01', 0)
        """))
        conn.execute(text("""
            INSERT INTO event_fights (event_id, fighter1_name, fighter2_name)
            VALUES (1, :f1, :f2)
        """), {"f1": f1_ctx.name, "f2": f2_ctx.name})
        conn.execute(text("""
            INSERT INTO odds_history
              (fight_id, fighter_name, american_odds, implied_probability, is_opening_line)
            VALUES
              (:fid, :f1, -150, 0.6000, 1),
              (:fid, :f2, 130, 0.4348, 1)
        """), {"fid": fight_id, "f1": f1_ctx.name, "f2": f2_ctx.name})

    result = compute(
        f1_ctx, f2_ctx, engine=engine,
        fight_id=fight_id,
        model_prob_f1=0.75,
        model_prob_f2=0.25,
    )
    assert result.signal in ("EDGE_DETECTED", "STRONG_EDGE")
    assert result.model_prob_f1 is not None
    assert result.implied_prob_f1 is not None
    assert result.model_prob_f2 is not None
    assert result.implied_prob_f2 is not None
    assert result.edge_pct is not None
    assert result.kelly_fraction is not None
