"""
Win Path Heuristics — how does each fighter win, and what does that
mean for this specific matchup?

Display name: Kill Chain
Used by: badge_engine (DECISION_PRISONER, ROUND_ONE_DEMON, SILENT_KILLER)

Win path labels:
    EARLY_KO           high KO rate + high slpm
    GROUND_AND_POUND   KO rate + takedown ability
    SUBMISSION         sub_avg + grappling style
    TAKEDOWN_CONTROL   high td_avg, low sub_avg
    DECISION_VOLUME    high slpm + decision career
    DECISION_COUNTER   counter style + decisions
    SPLIT_DECISION     base probability for close fights
"""

from __future__ import annotations

from .models import FighterContext, WinPathResult
from . import utils


_THREAT_MAP: dict[str, str] = {
    "EARLY_KO": "STRIKING",
    "GROUND_AND_POUND": "GRAPPLING",
    "SUBMISSION": "GRAPPLING",
    "TAKEDOWN_CONTROL": "WRESTLING",
    "DECISION_VOLUME": "STRIKING",
    "DECISION_COUNTER": "STRIKING",
    "SPLIT_DECISION": "STRIKING",
}

_METHOD_MAP: dict[str, str] = {
    "EARLY_KO": "KO",
    "GROUND_AND_POUND": "TKO",
    "SUBMISSION": "SUB",
    "TAKEDOWN_CONTROL": "DEC",
    "DECISION_VOLUME": "DEC",
    "DECISION_COUNTER": "DEC",
    "SPLIT_DECISION": "SPLIT_DEC",
}


def _method_counts(
    fights: list[dict], fighter_name: str,
) -> tuple[int, int, int, int]:
    """Count KO wins, Sub wins, Decision wins, and total wins."""
    ko = sub = dec = total = 0
    for f in fights:
        if (f.get("winner") or "").strip() != fighter_name:
            continue
        total += 1
        method = (f.get("method") or "").upper()
        if "KO" in method or "TKO" in method:
            ko += 1
        elif "SUB" in method:
            sub += 1
        else:
            dec += 1
    return ko, sub, dec, total


def _compute_paths(
    ctx: FighterContext,
) -> tuple[list[dict], str, str]:
    """
    Build ordered win-path list, most-likely method, and primary threat
    for one fighter.

    Returns:
        (paths, method, primary_threat)
        paths is [] and method is "UNKNOWN" when fighter has no data.
    """
    fights = ctx.fights
    stats = ctx.stats

    ko_wins, sub_wins, dec_wins, total_wins = _method_counts(fights, ctx.name)

    if total_wins == 0 and not fights:
        return [], "UNKNOWN", "STRIKING"

    # Career method rates
    if total_wins > 0:
        ko_rate = ko_wins / total_wins
        sub_rate = sub_wins / total_wins
        dec_rate = dec_wins / total_wins
    else:
        ko_rate = sub_rate = 0.33
        dec_rate = 0.34

    slpm = stats.get("slpm", 0) or 0
    td_avg = stats.get("td_avg", 0) or 0
    sub_avg = stats.get("sub_avg", 0) or 0
    str_def = stats.get("str_def", 0) or 0

    slpm_norm = min(slpm / 7.0, 1.0)
    td_norm = min(td_avg / 5.0, 1.0)
    sub_norm = min(sub_avg / 2.5, 1.0)

    style = utils.classify_style(stats)

    # ── Raw path weights ──────────────────────────────────────────────
    paths: dict[str, float] = {
        "EARLY_KO": ko_rate * 0.7 + slpm_norm * 0.3,
        "GROUND_AND_POUND": ko_rate * 0.4 + td_norm * 0.6,
        "SUBMISSION": sub_rate * 0.5 + sub_norm * 0.5,
        "TAKEDOWN_CONTROL": td_norm * 0.7 + (1.0 - sub_norm) * 0.3,
        "DECISION_VOLUME": dec_rate * 0.6 + slpm_norm * 0.4,
        "DECISION_COUNTER": dec_rate * 0.5 + str_def * 0.5,
        "SPLIT_DECISION": dec_rate * 0.3 + 0.1,
    }

    # Reduce TAKEDOWN_CONTROL for active submitters (they go for subs)
    if sub_avg > 1.0:
        paths["TAKEDOWN_CONTROL"] *= 0.5

    # Boost DECISION_COUNTER for COUNTER style
    if style == "COUNTER":
        paths["DECISION_COUNTER"] *= 1.3

    # Normalise to sum = 1.0
    total = sum(paths.values())
    if total > 0:
        paths = {k: v / total for k, v in paths.items()}

    sorted_paths = sorted(paths.items(), key=lambda x: -x[1])
    path_list = [{"path": k, "probability": round(v, 4)} for k, v in sorted_paths]

    top_path = sorted_paths[0][0]
    primary_threat = _THREAT_MAP.get(top_path, "STRIKING")
    method = _METHOD_MAP.get(top_path, "UNKNOWN")

    return path_list, method, primary_threat


def compute(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    model_probs: tuple[float, float],
) -> WinPathResult:
    """Compute the Kill Chain (win path heuristics) for both fighters."""
    f1_paths, f1_method, f1_threat = _compute_paths(f1_ctx)
    f2_paths, f2_method, f2_threat = _compute_paths(f2_ctx)

    # Overall most-likely method from the favoured fighter
    if not f1_paths or not f2_paths:
        method = "UNKNOWN"
    elif model_probs[0] >= model_probs[1]:
        method = f1_method
    else:
        method = f2_method

    return WinPathResult(
        available=True,
        f1_paths=f1_paths,
        f2_paths=f2_paths,
        most_likely_method=method,
        f1_primary_threat=f1_threat,
        f2_primary_threat=f2_threat,
    )
