"""
Value Bet Engine — where do the odds diverge from the model?

Output: ValueBetResult with signal, edge percentage, and Kelly fraction.

Display name: Line Crack / Edge Detected
Badge it powers: (LINE_CRACK / EDGE_DETECTED — green)

Data source: odds_history table (pre-populated by scripts/fetch_odds.py)
The Odds API is NEVER called at predict time — see TODO-03 in TODOS.md.

─────────────────────────────────────────────────────────────────────
TODO(opus): Implement the Kelly criterion edge calculation (odds-path only).

The NO_ODDS path (fight_id=None or no rows in odds_history) is already
fully implemented and does not need Opus.

Inputs available when odds exist:
    f1_ctx.name, f2_ctx.name  — for matching fighters to odds_history rows
    model_prob_f1/f2           — XGBoost model probabilities (0.0–1.0)
    odds rows                  — fighter_name, american_odds, implied_probability,
                                 is_opening_line, recorded_at

Utility functions (intelligence/utils.py):
    american_to_implied(odds_int)                     — odds → implied prob
    kelly_fraction(model_prob, implied_prob)          — half-Kelly fraction

Kelly formula (reference):
    edge_pct = model_prob - implied_prob
    kelly    = edge_pct / (1 - implied_prob)   [then clamped to half-Kelly]

Signal classification (Opus decides exact thresholds):
    kelly >= 0.10  → STRONG_EDGE
    kelly >= 0.04  → EDGE_DETECTED
    edge_pct < -0.05 → FADE_OPPORTUNITY  (model disagrees with favourite)
    else           → NO_EDGE

Line movement (if multiple odds_history rows exist):
    Detect if line has moved significantly from opening to current.
    Opening line: is_opening_line=True row.
    Movement direction can strengthen or weaken the signal.

Expected output when odds are present:
    ValueBetResult(
        signal="NO_EDGE" | "EDGE_DETECTED" | "STRONG_EDGE" | "FADE_OPPORTUNITY",
        active=True,
        edge_pct=float in [-1.0, 1.0],
        kelly_fraction=float in [0.0, 0.5],
        model_prob_f1=float in [0.0, 1.0],
        implied_prob_f1=float in [0.0, 1.0],
        model_prob_f2=float in [0.0, 1.0],
        implied_prob_f2=float in [0.0, 1.0],
    )
─────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import text

from .models import FighterContext, ValueBetResult


def compute(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    engine,
    fight_id: Optional[int] = None,
    model_prob_f1: Optional[float] = None,
    model_prob_f2: Optional[float] = None,
) -> ValueBetResult:
    """
    Compute the value bet signal for this fight.

    Args:
        f1_ctx:        Pre-loaded context for fighter 1.
        f2_ctx:        Pre-loaded context for fighter 2.
        engine:        SQLAlchemy Engine (for odds_history query).
        fight_id:      event_fights.id if this is a scheduled card fight;
                       None for ad-hoc predictions (→ NO_ODDS immediately).
        model_prob_f1: XGBoost probability for fighter 1 (0.0–1.0).
        model_prob_f2: XGBoost probability for fighter 2 (0.0–1.0).

    Returns:
        ValueBetResult.
        signal='NO_ODDS', active=False when fight_id is None or no odds found.
        Full Kelly result when odds are present (TODO: Opus).
    """
    # ── NO_ODDS fast path: ad-hoc prediction with no fight_id ────────────
    if fight_id is None:
        return ValueBetResult(signal="NO_ODDS", active=False)

    # ── Query odds_history for this fight ─────────────────────────────────
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT fighter_name, american_odds, implied_probability,
                       is_opening_line, recorded_at
                FROM odds_history
                WHERE fight_id = :fid
                ORDER BY recorded_at DESC
            """),
            {"fid": fight_id},
        ).fetchall()

    # ── NO_ODDS: fight_id provided but no odds recorded yet ───────────────
    if not rows:
        return ValueBetResult(signal="NO_ODDS", active=False)

    # ── Kelly calc: TODO(opus) ─────────────────────────────────────────────
    # Odds rows exist — run the Kelly criterion edge calculation.
    #
    # Available data:
    #   rows     — list of Row objects with (fighter_name, american_odds,
    #              implied_probability, is_opening_line, recorded_at)
    #   f1_ctx.name, f2_ctx.name — fighter names for row matching
    #   model_prob_f1, model_prob_f2 — XGBoost probabilities
    #
    # Steps (Opus):
    #   1. Find the most recent odds row for each fighter (latest recorded_at).
    #   2. Optionally find opening line (is_opening_line=True) for line movement.
    #   3. Compute edge_pct = model_prob - implied_prob for each fighter.
    #   4. Select the fighter with the larger positive edge as the bet target.
    #   5. Compute kelly = kelly_fraction(model_prob, implied_prob) from utils.
    #   6. Classify signal based on kelly threshold (see docstring).
    #   7. Return fully populated ValueBetResult.
    raise NotImplementedError(
        "value_bet Kelly calc: implement in Opus session. "
        "See module docstring for formula and signal classification guide."
    )
