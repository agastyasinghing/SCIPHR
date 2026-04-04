"""
Narrative Trap Detector — where is discourse emotionally strong but
statistically weak?

Output: NarrativeTrapResult with risk level, active trap tags, and
the "trapped" fighter (the one the narrative is built around).

Display name: Narrative Trap
Badge it powers: NARRATIVE_HOSTAGE (purple)
Data source: event_fights.narratives (JSON list of tags, manually curated)

Risk calibration:
    risk_score 0          → LOW
    risk_score 1-3        → MODERATE
    risk_score 4+         → HIGH

    short_notice / weight_miss each add 2 / 1 points respectively.
    is_title_fight + any tag adds 1 bonus point.
"""

from __future__ import annotations

from typing import Optional

from .models import FighterContext, NarrativeTrapResult


# Tag risk weights
_TAG_WEIGHTS: dict[str, int] = {
    "HYPE_TRAIN": 2,
    "REVENGE_FIGHT": 2,
    "COMEBACK_STORY": 2,
    "LEGACY_FIGHT": 2,
    "RETIREMENT_FIGHT": 1,
    "HOME_FIGHTER": 1,
    "UPSET_ALERT": 1,
    "REDEMPTION_ARC": 1,
    "SHORT_NOTICE_CHAOS": 1,
}

# Tags that typically centre on fighter1 (the promoted / narrative-adjacent fighter)
_F1_NARRATIVE_TAGS = frozenset({
    "HYPE_TRAIN", "COMEBACK_STORY", "RETIREMENT_FIGHT",
    "REDEMPTION_ARC", "HOME_FIGHTER", "LEGACY_FIGHT",
})


def compute(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    event_fight: Optional[dict] = None,
) -> NarrativeTrapResult:
    """Detect narrative traps for this fight."""

    # No event fight data → no narrative context → always LOW risk.
    if event_fight is None:
        return NarrativeTrapResult(available=True, risk="LOW")

    narratives: list[str] = event_fight.get("narratives") or []
    is_title: bool = bool(event_fight.get("is_title_fight", False))
    short_notice: bool = bool(event_fight.get("short_notice", False))
    weight_miss: bool = bool(event_fight.get("weight_miss", False))

    # Nothing narrative-worthy at all → LOW
    if not narratives and not short_notice and not weight_miss:
        return NarrativeTrapResult(available=True, risk="LOW")

    # ── Score narrative risk ─────────────────────────────────────────
    risk_score = sum(_TAG_WEIGHTS.get(tag, 1) for tag in narratives)
    if short_notice:
        risk_score += 2
    if weight_miss:
        risk_score += 1
    if is_title and narratives:
        risk_score += 1

    if risk_score >= 4:
        risk = "HIGH"
    elif risk_score >= 1:
        risk = "MODERATE"
    else:
        risk = "LOW"

    # ── Identify trapped fighter ─────────────────────────────────────
    f1_name = event_fight.get("fighter1_name", f1_ctx.name)
    f2_name = event_fight.get("fighter2_name", f2_ctx.name)

    f1_tag_score = sum(1 for tag in narratives if tag in _F1_NARRATIVE_TAGS)
    f2_tag_score = len(narratives) - f1_tag_score  # remaining are neutral/f2

    trapped: Optional[str] = None
    if f1_tag_score > f2_tag_score:
        trapped = f1_name
    elif f2_tag_score > f1_tag_score:
        trapped = f2_name
    elif narratives:
        # Ambiguous — default to fighter1 (convention: promoted fighter)
        trapped = f1_name

    return NarrativeTrapResult(
        available=True,
        risk=risk,
        active_traps=list(narratives),
        trapped_fighter=trapped,
    )
