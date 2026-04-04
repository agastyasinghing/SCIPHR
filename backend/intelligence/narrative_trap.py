"""
Narrative Trap Detector — where is discourse emotionally strong but
statistically weak?

Output: NarrativeTrapResult with risk level, active trap tags, and
the "trapped" fighter (the one the narrative is built around).

Display name: Narrative Trap
Badge it powers: NARRATIVE_HOSTAGE (purple)
Data source: event_fights.narratives (JSON list of tags, manually curated)

─────────────────────────────────────────────────────────────────────
TODO(opus): Implement the narrative trap scoring formula.

Context (from STATUS.md Decisions Log):
    "Narrative traps v1: manually tagged in events JSON"
    Automated NLP deferred to v2. The event_fights.narratives field
    is a JSON list of strings, e.g. ["HYPE_TRAIN", "REVENGE_FIGHT"].

Inputs available:
    f1_ctx, f2_ctx     — fighter contexts (stats, fights)
    event_fight        — dict from event_fights table row (may be None for
                         ad-hoc /predict calls without an associated event)

event_fight dict keys (from EventFight model):
    narratives         — list[str] of trap tags (may be None/empty)
    fighter1_name      — name of fighter in corner 1
    fighter2_name      — name of fighter in corner 2
    is_title_fight     — bool (title fights attract more narrative pressure)
    short_notice       — bool (short-notice fights are high narrative risk)
    weight_miss        — bool (weight miss signals chaos + narrative)
    notes              — free text fight-week intel

Known narrative trap tags (Opus to assign risk weights):
    HYPE_TRAIN         — one fighter is heavily promoted going into this
    REVENGE_FIGHT      — rematch with an emotional revenge narrative
    COMEBACK_STORY     — fighter returning from loss/injury/hiatus
    RETIREMENT_FIGHT   — "going out on their shield" narrative
    HOME_FIGHTER       — massive crowd support for local fighter
    UPSET_ALERT        — underdog getting extra media coverage
    LEGACY_FIGHT       — title defence framed as legacy-defining
    REDEMPTION_ARC     — fighter recovering public narrative after scandal
    SHORT_NOTICE_CHAOS — late replacement, minimal camp

Risk calibration (Opus decides final thresholds):
    0 tags + no short_notice/weight_miss → LOW
    1 tag OR (short_notice OR weight_miss) → MODERATE
    2+ tags OR (title_fight + 1+ tag) → HIGH

trapped_fighter logic:
    The fighter the narrative is BUILT AROUND.  Usually the more hype-adjacent
    fighter (HYPE_TRAIN, COMEBACK_STORY, RETIREMENT_FIGHT tags point to them).
    If no clear narrative subject, return None.

When event_fight is None (ad-hoc prediction):
    Return NarrativeTrapResult(available=True, risk="LOW") immediately —
    no narrative data available for non-event predictions.
─────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Optional

from .models import FighterContext, NarrativeTrapResult


def compute(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    event_fight: Optional[dict] = None,
) -> NarrativeTrapResult:
    """
    Detect narrative traps for this fight.

    Args:
        f1_ctx:      Pre-loaded context for fighter 1.
        f2_ctx:      Pre-loaded context for fighter 2.
        event_fight: Dict from event_fights table row, or None for ad-hoc
                     /predict calls with no associated scheduled fight.

    Returns:
        NarrativeTrapResult.
        If event_fight is None → risk='LOW', no active traps.
        If event_fight has narratives → risk derived from tag count + weights.

    TODO(opus): Implement the risk scoring and trapped_fighter logic.
    """
    # No event fight data → no narrative context → always LOW risk.
    # This path is fully implemented and does not need Opus.
    if event_fight is None:
        return NarrativeTrapResult(available=True, risk="LOW")

    # Event fight present but may have no narratives tagged yet.
    narratives = event_fight.get("narratives") or []
    if not narratives:
        return NarrativeTrapResult(available=True, risk="LOW")

    # TODO(opus): Implement narrative risk scoring from tag list.
    # Inputs: narratives (list[str]), event_fight["is_title_fight"],
    #         event_fight["short_notice"], event_fight["weight_miss"],
    #         f1_ctx.name, f2_ctx.name (to identify trapped_fighter)
    # See module docstring for tag vocabulary and risk calibration guide.
    raise NotImplementedError(
        "narrative_trap formula: implement in Opus session. "
        "See module docstring for tag vocabulary and risk calibration."
    )
