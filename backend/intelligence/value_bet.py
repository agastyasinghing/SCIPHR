"""
Value Bet Engine — where do the odds diverge from the model?

Output: ValueBetResult with signal, edge percentage, and Kelly fraction.

Display name: Line Crack / Edge Detected
Badge it powers: (LINE_CRACK / EDGE_DETECTED — green)

Data source: odds_history table (pre-populated by scripts/fetch_odds.py)
The Odds API is NEVER called at predict time — see TODO-03 in TODOS.md.

Signal classification:
    FADE_OPPORTUNITY  model and market disagree on favourite direction
    STRONG_EDGE       kelly >= 0.10
    EDGE_DETECTED     kelly >= 0.04
    NO_EDGE           model agrees with market (small or no edge)
    NO_ODDS           no odds data available
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import text

from .models import FighterContext, ValueBetResult
from . import utils


def compute(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    engine,
    fight_id: Optional[int] = None,
    model_prob_f1: Optional[float] = None,
    model_prob_f2: Optional[float] = None,
) -> ValueBetResult:
    """Compute the value bet signal for this fight."""

    # ── NO_ODDS fast path: ad-hoc prediction with no fight_id ────────
    if fight_id is None:
        return ValueBetResult(signal="NO_ODDS", active=False)

    # ── Query odds_history for this fight ─────────────────────────────
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

    # ── NO_ODDS: fight_id provided but no odds recorded yet ──────────
    if not rows:
        return ValueBetResult(signal="NO_ODDS", active=False)

    # ── Find latest odds for each fighter ─────────────────────────────
    f1_odds: Optional[dict] = None
    f2_odds: Optional[dict] = None
    for row in rows:
        m = dict(row._mapping)
        name = m["fighter_name"]
        if name == f1_ctx.name and f1_odds is None:
            f1_odds = m
        elif name == f2_ctx.name and f2_odds is None:
            f2_odds = m
        if f1_odds and f2_odds:
            break

    if not f1_odds or not f2_odds:
        return ValueBetResult(signal="NO_ODDS", active=False)

    # ── Implied probabilities ─────────────────────────────────────────
    implied_f1 = float(
        f1_odds.get("implied_probability")
        or utils.american_to_implied(int(f1_odds["american_odds"]))
    )
    implied_f2 = float(
        f2_odds.get("implied_probability")
        or utils.american_to_implied(int(f2_odds["american_odds"]))
    )

    # ── Edge calculation ──────────────────────────────────────────────
    edge_f1 = model_prob_f1 - implied_f1
    edge_f2 = model_prob_f2 - implied_f2

    # Kelly for the fighter with the positive edge
    if edge_f1 >= edge_f2:
        kelly = utils.kelly_fraction(model_prob_f1, implied_f1)
    else:
        kelly = utils.kelly_fraction(model_prob_f2, implied_f2)

    # ── Signal classification ─────────────────────────────────────────
    # FADE: model and market disagree on who the favourite is
    market_fav_f1 = implied_f1 >= implied_f2
    model_fav_f1 = model_prob_f1 >= model_prob_f2
    fav_agrees = market_fav_f1 == model_fav_f1

    if not fav_agrees and max(abs(edge_f1), abs(edge_f2)) > 0.05:
        signal = "FADE_OPPORTUNITY"
    elif kelly >= 0.10:
        signal = "STRONG_EDGE"
    elif kelly >= 0.04:
        signal = "EDGE_DETECTED"
    else:
        signal = "NO_EDGE"

    # Kelly output only for actionable signals
    if signal in ("EDGE_DETECTED", "STRONG_EDGE", "FADE_OPPORTUNITY"):
        kelly_out = round(kelly, 4)
    else:
        kelly_out = None

    return ValueBetResult(
        signal=signal,
        active=True,
        edge_pct=round(edge_f1, 4),        # always from f1's perspective
        kelly_fraction=kelly_out,
        model_prob_f1=model_prob_f1,
        implied_prob_f1=round(implied_f1, 4),
        model_prob_f2=model_prob_f2,
        implied_prob_f2=round(implied_f2, 4),
    )
