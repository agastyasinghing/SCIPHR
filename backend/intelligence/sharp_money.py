"""
Sharp Money Indicator — detect when line movement aligns with the model.

Output: SharpMoneyResult with aligned flag and MARKET_ALIGNMENT signal.
Display name: Sharp Echo.

PRD §10.9 specification:
    Sharp Money fires when the line moves TOWARD the model's prediction
    from opening, suggesting sophisticated bettors agree with the model.

    Example:
        Model says Fighter A at 60%.
        Opening line implies 52%. Current line implies 58%.
        Line moved toward model → MARKET_ALIGNMENT.

    Conditions for MARKET_ALIGNMENT:
        (current_implied > opening_implied AND model_prob > 0.55) OR
        (current_implied < opening_implied AND model_prob < 0.45)
        AND movement_magnitude > 0.03

Badge powered: SHARP_ECHO fight-level badge (teal)

Data source:
    Reads opening_line and latest odds from odds_history table.
    Requires fight_id — returns NEUTRAL when no fight_id provided.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import text

from .models import FighterContext, SharpMoneyResult


def compute(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    engine,
    fight_id: Optional[int] = None,
    model_prob_f1: Optional[float] = None,
    model_prob_f2: Optional[float] = None,
) -> SharpMoneyResult:
    """
    Compute the Sharp Money signal for this fight.

    Args:
        f1_ctx:       FighterContext for fighter 1.
        f2_ctx:       FighterContext for fighter 2.
        engine:       SQLAlchemy Engine (shared, no new connections).
        fight_id:     event_fights.id — None returns NEUTRAL immediately.
        model_prob_f1: XGBoost model probability for fighter 1.
        model_prob_f2: XGBoost model probability for fighter 2.

    Returns:
        SharpMoneyResult — always returned, never raises.
        Returns SharpMoneyResult(signal="NEUTRAL") when fight_id is None
        or when odds_history has insufficient data (< 2 snapshots).
    """
    if fight_id is None or model_prob_f1 is None or model_prob_f2 is None:
        return SharpMoneyResult(signal="NEUTRAL")

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT fighter_name, implied_probability,
                       is_opening_line, recorded_at
                FROM odds_history
                WHERE fight_id = :fid
                ORDER BY recorded_at ASC
            """),
            {"fid": fight_id},
        ).fetchall()

    # Need at least an opening + a current snapshot
    if not rows or len(rows) < 2:
        return SharpMoneyResult(signal="NEUTRAL")

    # ── Find opening + current implied for f1 (f2 is the symmetric complement) ──
    opening_f1: Optional[float] = None
    current_f1: Optional[float] = None

    for row in rows:
        m = dict(row._mapping)
        if m["fighter_name"] != f1_ctx.name:
            continue
        implied = float(m["implied_probability"])
        if bool(m.get("is_opening_line")) and opening_f1 is None:
            opening_f1 = implied
        current_f1 = implied  # rows ASC → last write wins = latest

    # Fallback: if no explicit is_opening_line row, use earliest snapshot
    if opening_f1 is None:
        for row in rows:
            m = dict(row._mapping)
            if m["fighter_name"] == f1_ctx.name:
                opening_f1 = float(m["implied_probability"])
                break

    if opening_f1 is None or current_f1 is None:
        return SharpMoneyResult(signal="NEUTRAL")

    # Opening == current means no movement at all
    if opening_f1 == current_f1:
        return SharpMoneyResult(
            aligned=False,
            movement_magnitude=0.0,
            signal="NEUTRAL",
        )

    # Check alignment from f1's perspective (f2 is the symmetric complement)
    movement_magnitude = abs(current_f1 - opening_f1)
    line_moved_toward_model = (
        (current_f1 > opening_f1 and model_prob_f1 > 0.55)
        or (current_f1 < opening_f1 and model_prob_f1 < 0.45)
    )
    aligned_signal = line_moved_toward_model and movement_magnitude > 0.03

    return SharpMoneyResult(
        aligned=bool(line_moved_toward_model),
        movement_magnitude=round(float(movement_magnitude), 4),
        signal="MARKET_ALIGNMENT" if aligned_signal else "NEUTRAL",
    )
