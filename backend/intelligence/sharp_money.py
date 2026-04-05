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

TODO(opus): Implement compute() using PRD §10.9 specification.
    Key formula decisions:
    - Opening line: is_opening_line=True row from odds_history
    - Current line: most recent row (already used by value_bet)
    - Movement direction: compare opening_implied vs current_implied per fighter
    - line_moved_toward_model: PRD §10.9 logic
    - movement_magnitude: abs(current_implied - opening_implied)
    - signal: MARKET_ALIGNMENT if aligned and magnitude > 0.03, else NEUTRAL
    - Return NEUTRAL (not None) when no fight_id or insufficient odds history
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
    # TODO(opus): Implement using PRD §10.9 logic.
    # See module docstring for full specification.
    # Query pattern mirrors value_bet.py — use is_opening_line=True for
    # opening snapshot and most-recent row for current line.
    raise NotImplementedError(
        "sharp_money.compute() — awaiting Opus implementation (PRD §10.9)"
    )
