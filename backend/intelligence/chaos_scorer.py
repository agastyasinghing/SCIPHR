"""
Chaos Scorer — how unpredictable is this fight?

Output: ChaosResult with score 0-100, label, and driver list.

Display name: Chaos Score
Badge it powers: CHAOS_CERTIFIED (yellow)
Also contributes to: Card Temperature (Dashboard), false_consensus

Score composition (100 points max before weight-class multiplier):
    Finish rate      0-55   bilateral career finish involvement
    Style clash      0-15   striker vs grappler = max clash
    Offensive output 0-10   combined striking volume (slpm)
    Chin issues      0-10   opponent accuracy vs fighter defence gap
    Record volatility 0-10  alternating win/loss patterns
    Streak dynamics  0-5    loss streaks, opposing momentum

Label thresholds:
    0-30  LOW | 30-55  MODERATE | 55-75  HIGH | 75+  EXTREME
"""

from __future__ import annotations

from .models import ChaosResult, FighterContext
from . import utils


# Weight class finish rate multipliers (heavier = more finishes historically)
_WEIGHT_CLASS_MULTIPLIER: dict[str, float] = {
    "Heavyweight": 1.30,
    "Light Heavyweight": 1.20,
    "Middleweight": 1.10,
    "Welterweight": 1.00,
    "Lightweight": 1.00,
    "Featherweight": 0.95,
    "Bantamweight": 0.90,
    "Flyweight": 0.85,
    "Strawweight": 0.85,
    "Women's Featherweight": 0.90,
    "Women's Bantamweight": 0.90,
    "Women's Flyweight": 0.85,
    "Women's Strawweight": 0.85,
}

# Style clash matrix — frozenset for order-independent lookup.
_CLASH_MATRIX: dict[frozenset, float] = {
    frozenset({"STRIKER", "GRAPPLER"}): 1.0,
    frozenset({"BRAWLER", "GRAPPLER"}): 0.90,
    frozenset({"STRIKER", "WRESTLER"}): 0.85,
    frozenset({"BRAWLER", "WRESTLER"}): 0.75,
    frozenset({"BRAWLER", "COUNTER"}): 0.70,
    frozenset({"GRAPPLER", "COUNTER"}): 0.60,
    frozenset({"STRIKER", "COUNTER"}): 0.50,
    frozenset({"WRESTLER", "COUNTER"}): 0.45,
    frozenset({"STRIKER", "BRAWLER"}): 0.35,
    frozenset({"GRAPPLER", "WRESTLER"}): 0.30,
}


def _record_volatility(fights: list[dict], fighter_name: str) -> float:
    """Proportion of direction-changes in the win/loss sequence.  0.0-1.0."""
    if len(fights) < 3:
        return 0.0
    results: list[int] = []
    for f in fights:
        winner = (f.get("winner") or "").strip()
        if winner == fighter_name:
            results.append(1)
        elif winner:
            results.append(-1)
        # draws / NC ignored
    if len(results) < 3:
        return 0.0
    changes = sum(1 for i in range(1, len(results)) if results[i] != results[i - 1])
    return changes / (len(results) - 1)


def compute(f1_ctx: FighterContext, f2_ctx: FighterContext) -> ChaosResult:
    """Compute the Chaos Score for a matchup."""
    drivers: list[str] = []

    # ── Signal 1: bilateral finish rate (0-55) ───────────────────────
    fr1 = utils.finish_rate(f1_ctx.fights, f1_ctx.name)
    fr2 = utils.finish_rate(f2_ctx.fights, f2_ctx.name)
    avg_finish = (fr1 + fr2) / 2.0
    finish_score = avg_finish * 55.0
    if avg_finish > 0.55:
        drivers.append("high_finish_rate")

    # ── Signal 2: style clash (0-15) ─────────────────────────────────
    style1 = utils.classify_style(f1_ctx.stats)
    style2 = utils.classify_style(f2_ctx.stats)
    if style1 == style2:
        clash = 0.0
    else:
        clash = _CLASH_MATRIX.get(frozenset({style1, style2}), 0.40)
    clash_score = clash * 15.0
    if clash > 0.5:
        drivers.append("style_clash")

    # ── Signal 3: offensive output (0-10) ────────────────────────────
    slpm1 = f1_ctx.stats.get("slpm", 0) or 0
    slpm2 = f2_ctx.stats.get("slpm", 0) or 0
    avg_slpm_norm = (min(slpm1 / 7.0, 1.0) + min(slpm2 / 7.0, 1.0)) / 2.0
    offense_score = avg_slpm_norm * 10.0

    # ── Signal 4: chin issues (0-10) ─────────────────────────────────
    str_acc1 = f1_ctx.stats.get("str_acc", 0) or 0
    str_acc2 = f2_ctx.stats.get("str_acc", 0) or 0
    str_def1 = f1_ctx.stats.get("str_def", 0) or 0
    str_def2 = f2_ctx.stats.get("str_def", 0) or 0
    vuln1 = max(0.0, str_acc2 - str_def1)
    vuln2 = max(0.0, str_acc1 - str_def2)
    chin_factor = (vuln1 + vuln2) / 2.0
    chin_score = min(10.0, chin_factor * 35.0)
    if chin_factor > 0.05:
        drivers.append("chin_issues")

    # ── Signal 5: record volatility (0-10) ───────────────────────────
    vol1 = _record_volatility(f1_ctx.fights, f1_ctx.name)
    vol2 = _record_volatility(f2_ctx.fights, f2_ctx.name)
    avg_vol = (vol1 + vol2) / 2.0
    vol_score = avg_vol * 10.0
    if avg_vol > 0.4:
        drivers.append("record_volatility")

    # ── Signal 6: streak dynamics (0-5) ──────────────────────────────
    streak1 = utils.win_streak(f1_ctx.fights, f1_ctx.name)
    streak2 = utils.win_streak(f2_ctx.fights, f2_ctx.name)
    streak_chaos = 0.0
    if streak1 < 0 or streak2 < 0:
        streak_chaos += min(abs(min(streak1, streak2)) * 1.5, 4.0)
        drivers.append("loss_streak")
    if (streak1 > 0) != (streak2 > 0) and streak1 != 0 and streak2 != 0:
        streak_chaos += 1.0
    streak_score = min(5.0, streak_chaos)

    # ── Combine ──────────────────────────────────────────────────────
    raw = finish_score + clash_score + offense_score + chin_score + vol_score + streak_score

    # Weight-class multiplier (symmetric — average both fighters)
    wc1 = f1_ctx.stats.get("weight_class", "Unknown")
    wc2 = f2_ctx.stats.get("weight_class", "Unknown")
    wc_mult = (
        _WEIGHT_CLASS_MULTIPLIER.get(wc1, 1.0)
        + _WEIGHT_CLASS_MULTIPLIER.get(wc2, 1.0)
    ) / 2.0

    score = max(0.0, min(100.0, raw * wc_mult))

    # ── Label ────────────────────────────────────────────────────────
    if score < 30:
        label = "LOW"
    elif score < 55:
        label = "MODERATE"
    elif score < 75:
        label = "HIGH"
    else:
        label = "EXTREME"

    # ── Confidence (based on minimum data availability) ──────────────
    min_fights = min(len(f1_ctx.fights), len(f2_ctx.fights))
    confidence = min(1.0, min_fights / 10.0)
    # Floor: if we have *some* data for the other fighter, give 0.1
    if confidence == 0.0 and max(len(f1_ctx.fights), len(f2_ctx.fights)) > 0:
        confidence = 0.1

    return ChaosResult(
        available=True,
        score=round(score, 2),
        label=label,
        drivers=drivers,
        confidence=round(confidence, 2),
    )
