"""
Fight DNA Calculator — what kind of fight will this be, dimensionally?

Output: FightDNAResult with 8-dimension profiles for each fighter,
a collision type, and style clash intensity.

Display name: Fight DNA
Used by: badge_engine (DECISION_PRISONER, ROUND_ONE_DEMON logic)
Frontend: Fight DNA visual component (Phase 4)

Eight dimensions (normalised 0.0-1.0):
    STRIKING      slpm + str_acc
    GRAPPLING     td_avg + td_acc + sub_avg
    WRESTLING     td_avg + td_acc
    SUBMISSION    sub_avg + td_acc
    PRESSURE      slpm + td_avg (combined pace)
    CHIN          str_def + inverse KO-loss rate
    CARDIO        decision rate from career history
    SPEED         slpm + str_acc (output + precision = speed)

Collision type:  "{f1_style}_VS_{f2_style}" from classify_style()
Clash intensity: Euclidean distance between offensive DNA dimensions, 0-1.
"""

from __future__ import annotations

import math

from .models import FighterContext, FightDNAResult
from . import utils


# Offensive dimensions used for clash intensity calculation
_OFFENSIVE_DIMS = ("striking", "grappling", "wrestling", "submission", "pressure")


def _compute_dna(ctx: FighterContext) -> dict[str, float]:
    """Build 8-dimension DNA profile for one fighter."""
    stats = ctx.stats
    fights = ctx.fights

    slpm = stats.get("slpm", 0) or 0
    str_acc = stats.get("str_acc", 0) or 0
    str_def = stats.get("str_def", 0) or 0
    td_avg = stats.get("td_avg", 0) or 0
    td_acc = stats.get("td_acc", 0) or 0
    sub_avg = stats.get("sub_avg", 0) or 0

    # Normalisation reference points (approximate UFC elite ceilings)
    slpm_norm = min(slpm / 7.0, 1.0)
    td_norm = min(td_avg / 5.0, 1.0)
    sub_norm = min(sub_avg / 2.5, 1.0)

    striking = 0.6 * slpm_norm + 0.4 * str_acc
    grappling = 0.4 * td_norm + 0.3 * td_acc + 0.3 * sub_norm
    wrestling = 0.6 * td_norm + 0.4 * td_acc
    submission = 0.7 * sub_norm + 0.3 * td_acc
    pressure = 0.6 * slpm_norm + 0.4 * td_norm

    # Chin: striking defence + inverse of KO-loss rate
    ko_losses = 0
    total_losses = 0
    for f in fights:
        winner = (f.get("winner") or "").strip()
        if winner and winner != ctx.name:
            total_losses += 1
            method = (f.get("method") or "").upper()
            if "KO" in method or "TKO" in method:
                ko_losses += 1
    ko_loss_rate = ko_losses / max(total_losses, 1)
    chin = 0.5 * str_def + 0.5 * (1.0 - ko_loss_rate)

    # Cardio: decision rate (fighters who go deep have endurance)
    if fights:
        dec_count = sum(
            1 for f in fights if "DECISION" in (f.get("method") or "").upper()
        )
        dec_rate = dec_count / len(fights)
    else:
        dec_rate = 0.5  # neutral default

    cardio = dec_rate

    # Speed: output + accuracy proxy
    speed = 0.5 * slpm_norm + 0.5 * str_acc

    def _clamp(v: float) -> float:
        return round(min(1.0, max(0.0, v)), 4)

    return {
        "striking": _clamp(striking),
        "grappling": _clamp(grappling),
        "wrestling": _clamp(wrestling),
        "submission": _clamp(submission),
        "pressure": _clamp(pressure),
        "chin": _clamp(chin),
        "cardio": _clamp(cardio),
        "speed": _clamp(speed),
    }


def compute(f1_ctx: FighterContext, f2_ctx: FighterContext) -> FightDNAResult:
    """Compute the Fight DNA profile for both fighters and their collision."""
    f1_dna = _compute_dna(f1_ctx)
    f2_dna = _compute_dna(f2_ctx)

    # ── Collision type (from classify_style, not DNA dims) ────────────
    style1 = utils.classify_style(f1_ctx.stats)
    style2 = utils.classify_style(f2_ctx.stats)
    collision_type = f"{style1}_VS_{style2}"

    # ── Style clash intensity — Euclidean distance on offensive dims ──
    diff_sq = sum(
        (f1_dna.get(d, 0) - f2_dna.get(d, 0)) ** 2 for d in _OFFENSIVE_DIMS
    )
    clash_intensity = min(1.0, math.sqrt(diff_sq) / math.sqrt(len(_OFFENSIVE_DIMS)))

    # ── Primary dimension — largest absolute gap between fighters ─────
    max_diff = 0.0
    primary = "STRIKING"
    for dim in f1_dna:
        diff = abs(f1_dna[dim] - f2_dna[dim])
        if diff > max_diff:
            max_diff = diff
            primary = dim.upper()

    return FightDNAResult(
        available=True,
        f1_dna=f1_dna,
        f2_dna=f2_dna,
        collision_type=collision_type,
        style_clash_intensity=round(clash_intensity, 4),
        primary_dimension=primary,
    )
