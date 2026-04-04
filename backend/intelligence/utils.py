"""
Shared utility functions for the SCIPHR intelligence layer.

All functions are pure (no DB access, no side effects).
Used by multiple intelligence modules — keep this file free of
module-specific logic.

Functions:
    classify_style  — derive fighting style from profile stats
    finish_rate     — proportion of a fighter's fights ending in a finish
    win_streak      — current win (+) or loss (-) streak
    american_to_implied — American odds → implied probability
    kelly_fraction  — half-Kelly bet size given model vs implied probability
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Style classification
# ---------------------------------------------------------------------------

# Threshold table (all values from fighters table column names):
#   sub_avg   — avg submission attempts per 15 min
#   td_avg    — avg takedowns landed per 15 min
#   slpm      — significant strikes landed per minute
#   str_acc   — striking accuracy (0.0–1.0 in DB)
#   str_def   — striking defence (0.0–1.0 in DB)
#
# Ordering matters: GRAPPLER/WRESTLER checked before STRIKER/BRAWLER/COUNTER.
_STYLE_THRESHOLDS = {
    "GRAPPLER":  lambda s: (s.get("sub_avg", 0) or 0) > 1.5,
    "WRESTLER":  lambda s: (s.get("td_avg", 0) or 0) > 3.0,
    "STRIKER":   lambda s: (
        (s.get("slpm", 0) or 0) > 5.0 and (s.get("td_avg", 0) or 0) < 1.5
    ),
    "BRAWLER":   lambda s: (
        (s.get("slpm", 0) or 0) > 4.0 and (s.get("str_acc", 0) or 0) > 0.50
    ),
    "COUNTER":   lambda s: (
        (s.get("str_def", 0) or 0) > 0.65 and (s.get("slpm", 0) or 0) < 3.0
    ),
}


def classify_style(stats: dict) -> str:
    """
    Derive a fighter's primary style from their profile stats dict.

    Uses the fighters table column keys (sub_avg, td_avg, slpm, str_acc,
    str_def) — NOT the r_* XGBoost feature keys.

    Called on-the-fly at predict time; result is NOT persisted to
    fighters.style (which remains NULL in v1).

    Returns one of: GRAPPLER | WRESTLER | STRIKER | BRAWLER | COUNTER.
    Defaults to 'STRIKER' when stats are all zero or no threshold fires.
    """
    for style, test in _STYLE_THRESHOLDS.items():
        try:
            if test(stats):
                return style
        except (TypeError, KeyError):
            continue
    return "STRIKER"


# ---------------------------------------------------------------------------
# Fight history helpers
# ---------------------------------------------------------------------------

def _is_finish(method: str) -> bool:
    """Return True if the fight method is a finish (KO/TKO/Submission)."""
    m = (method or "").upper()
    return "KO" in m or "TKO" in m or "SUB" in m or "COULD NOT CONTINUE" in m


def finish_rate(fights: list[dict], fighter_name: str) -> float:
    """
    Proportion of this fighter's fights that ended in a finish
    (KO, TKO, Submission, or TKO - Doctor's Stoppage), regardless of winner.

    A high finish_rate means the fighter is *involved in* exciting finishes —
    both as aggressor and recipient.  Used by chaos_scorer to detect
    fighters who consistently raise fight volatility.

    Args:
        fights:       List of fight dicts with at least a 'method' key.
                      From FighterContext.fights (date DESC order).
        fighter_name: Name for context (unused in calculation; kept for
                      symmetry with win_streak signature).

    Returns:
        0.0 if fights is empty; float in [0.0, 1.0] otherwise.
    """
    if not fights:
        return 0.0
    finishes = sum(1 for f in fights if _is_finish(f.get("method", "")))
    return finishes / len(fights)


def win_streak(fights: list[dict], fighter_name: str) -> int:
    """
    Current consecutive win streak (positive) or loss streak (negative).

    fights must be ordered date DESC (most recent first) — as returned by
    IntelligenceOrchestrator._build_context().

    Returns:
        Positive int: number of consecutive wins heading into this fight.
        Negative int: number of consecutive losses.
        0:            no fights, or most recent result was a draw/NC.

    Streak counting stops at the first result that breaks the direction
    (e.g. a loss ends a win streak even if wins resume after it).
    """
    if not fights:
        return 0

    streak = 0
    for fight in fights:
        winner = (fight.get("winner") or "").strip()
        if winner == fighter_name:
            if streak < 0:
                break   # on a loss streak — first win ends it
            streak += 1
        elif winner and winner.upper() not in ("DRAW", "NC", "NO CONTEST", ""):
            # another named fighter won
            if streak > 0:
                break   # on a win streak — first loss ends it
            streak -= 1
        else:
            # draw, NC, or unknown result — stop streak counting
            break

    return streak


# ---------------------------------------------------------------------------
# Odds / Kelly utilities
# ---------------------------------------------------------------------------

def american_to_implied(odds: int) -> float:
    """
    Convert American moneyline odds to implied probability.

    Examples:
        american_to_implied(-185) → 0.6491  (heavy favourite)
        american_to_implied(+150) → 0.4000  (underdog)
        american_to_implied(0)    → 0.5000  (even money)

    Returns: float in [0.0, 1.0].
    Raises:  ValueError if odds is not int-like.
    """
    odds = int(odds)
    if odds > 0:
        return 100.0 / (odds + 100.0)
    elif odds < 0:
        return abs(odds) / (abs(odds) + 100.0)
    else:
        return 0.5


def kelly_fraction(model_prob: float, implied_prob: float) -> float:
    """
    Half-Kelly fraction: recommended bet size as a fraction of bankroll.

    Formula: f = (model_prob - implied_prob) / (1 - implied_prob)
    Then capped at half-Kelly (max 0.5) — full Kelly is too aggressive
    for sports betting with imperfect model probabilities.

    Args:
        model_prob:   XGBoost model probability for this fighter (0.0–1.0).
        implied_prob: Market implied probability from American odds (0.0–1.0).

    Returns:
        float in [0.0, 0.5].
        Returns 0.0 for negative or zero edge, or invalid inputs.
        A separate check for FADE signals lives in value_bet.compute().

    Edge cases:
        - implied_prob <= 0 or >= 1 → 0.0 (avoids division by zero)
        - model_prob <= 0 or model_prob >= 1 → 0.0 (model extremes not trusted)
    """
    if implied_prob <= 0.0 or implied_prob >= 1.0:
        return 0.0
    if model_prob <= 0.0 or model_prob >= 1.0:
        return 0.0

    edge = (model_prob - implied_prob) / (1.0 - implied_prob)
    # Clamp: no negative Kelly (handled by FADE signal in value_bet),
    # cap at 0.5 (half-Kelly ceiling).
    return max(0.0, min(0.5, edge))
