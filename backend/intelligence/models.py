"""
Pydantic models for the SCIPHR intelligence layer.

All 9 module result types, FighterContext (input), Badge, and
IntelligenceResult (bundle) live here.  badge_engine and orchestrator
import from this file only — no cross-module result imports needed.

Design notes:
  - available=False is the sentinel for a module that failed in _safe_compute.
    badge_engine and callers must check available before using result fields.
  - Field(ge=..., le=...) validators on numeric outputs catch Opus formula bugs
    (e.g. chaos score returning 150 instead of 75) at model instantiation time.
  - All numeric scores use consistent scale documented per field.
  - value_bet is never None in IntelligenceResult — it always returns at minimum
    signal='NO_ODDS' (when no odds are available for this fight).
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------

class FighterContext(BaseModel):
    """
    Pre-loaded data for one fighter, assembled by IntelligenceOrchestrator
    before any module runs.  Pure data container — no DB access here.

    stats keys (from fighters table columns, consistent naming):
      wins, losses, draws, age, weight_lbs, height_cm, reach_cm
      slpm, str_acc, str_def, td_avg, td_acc, td_def, sub_avg, weight_class

    fights rows (from fights table, ordered date DESC):
      r_name, b_name, date, winner, method, weight_class
    """

    name: str
    stats: dict                # fighters table profile columns (see docstring)
    fights: list[dict]         # historical fights, most recent first
    wins: int = 0
    losses: int = 0
    draws: int = 0

    model_config = ConfigDict(frozen=True)


# ---------------------------------------------------------------------------
# Module result models
# ---------------------------------------------------------------------------

class ChaosResult(BaseModel):
    """
    Output of chaos_scorer.compute().

    score:              0 (perfectly predictable) → 100 (coin flip with explosions)
    tier:               bucketed score label (LOW/MIXED/HIGH/EXTREME — PRD §10.6)
    drivers:            human-readable list of signals that raised the score
                        (e.g. "high_finish_rate", "style_clash", "chin_issues")
    confidence:         0–1, how reliable the chaos estimate is given data volume
    betting_implication: one-sentence betting guidance derived from tier (PRD §10.6)
    """

    available: bool = True
    score: float = Field(0.0, ge=0.0, le=100.0)
    tier: Literal["LOW", "MIXED", "HIGH", "EXTREME"] = "LOW"
    drivers: list[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    betting_implication: str = ""


class PerceptionGapResult(BaseModel):
    """
    Output of perception_gap.compute().

    gap_f1 / gap_f2:
        model_prob - perceived_public_prob for each fighter.
        Positive = model rates this fighter HIGHER than public heuristic implies.
        Negative = model rates this fighter LOWER (public overvalues them).
        Range: [-1.0, 1.0]

    overvalued_fighter / undervalued_fighter:
        Fighter name, or None if gap is within noise threshold.

    aura_score_f1 / aura_score_f2:
        Heuristic "public perceived strength" score (0–1).
        Derived from: career volume, finish rate, recency, weight class.

    direction_f1 / direction_f2:
        OVERHYPED  — public rates this fighter higher than the model does
        UNDERRATED — model rates this fighter higher than public does
        ALIGNED    — gap within noise threshold

    magnitude:
        Overall gap size label based on the largest abs gap of the two fighters.
        LARGE (> 0.20), MODERATE (> 0.10), SMALL (≤ 0.10)
    """

    available: bool = True
    gap_f1: float = Field(0.0, ge=-1.0, le=1.0)
    gap_f2: float = Field(0.0, ge=-1.0, le=1.0)
    label: Literal["NONE", "MODERATE", "STRONG"] = "NONE"
    overvalued_fighter: Optional[str] = None
    undervalued_fighter: Optional[str] = None
    aura_score_f1: float = Field(0.0, ge=0.0, le=1.0)
    aura_score_f2: float = Field(0.0, ge=0.0, le=1.0)
    direction_f1: Literal["OVERHYPED", "ALIGNED", "UNDERRATED"] = "ALIGNED"
    direction_f2: Literal["OVERHYPED", "ALIGNED", "UNDERRATED"] = "ALIGNED"
    magnitude: Literal["LARGE", "MODERATE", "SMALL"] = "SMALL"


class NarrativeTrapResult(BaseModel):
    """
    Output of narrative_trap.compute().

    risk:         LOW | MODERATE | HIGH — how much narrative context distorts
                  this prediction.
    active_traps: tags from event_fights.narratives that fired for this fight
                  (e.g. ["HYPE_TRAIN", "REVENGE_FIGHT", "COMEBACK_STORY"]).
    trapped_fighter:
                  the fighter the narrative centers on (the "trap" fighter),
                  or None if no narrative signals present.
    """

    available: bool = True
    risk: Literal["LOW", "MODERATE", "HIGH"] = "LOW"
    active_traps: list[str] = Field(default_factory=list)
    trapped_fighter: Optional[str] = None


class ValueBetResult(BaseModel):
    """
    Output of value_bet.compute().

    signal:
        NO_ODDS         — no odds available (most ad-hoc predictions)
        NO_EDGE         — odds available but model agrees with the market
        EDGE_DETECTED   — mild Kelly edge (0.04 < kelly < 0.10)
        STRONG_EDGE     — strong Kelly edge (kelly >= 0.10)
        FADE_OPPORTUNITY— model strongly disagrees with a favored fighter

    edge_pct:
        Signed edge: model_prob_f1 - implied_prob_f1.
        Positive = model likes f1 more than market does.
        None when signal is NO_ODDS.

    kelly_fraction:
        Recommended fraction of bankroll to bet (half-Kelly).
        0.0–0.5 range. None when signal is NO_ODDS or NO_EDGE.
    """

    signal: Literal[
        "NO_ODDS", "NO_EDGE", "EDGE_DETECTED", "STRONG_EDGE", "FADE_OPPORTUNITY"
    ] = "NO_ODDS"
    active: bool = False
    edge_pct: Optional[float] = Field(None, ge=-1.0, le=1.0)
    kelly_fraction: Optional[float] = Field(None, ge=0.0, le=0.5)
    model_prob_f1: Optional[float] = Field(None, ge=0.0, le=1.0)
    implied_prob_f1: Optional[float] = Field(None, ge=0.0, le=1.0)
    model_prob_f2: Optional[float] = Field(None, ge=0.0, le=1.0)
    implied_prob_f2: Optional[float] = Field(None, ge=0.0, le=1.0)


class FightDNAResult(BaseModel):
    """
    Output of fight_dna.compute().

    f1_dna / f2_dna:
        Dict of dimension name → score (0.0–1.0).
        Dimensions (Opus to calibrate weights):
          striking, grappling, wrestling, submission, pressure,
          chin, cardio, speed

    collision_type:
        Stylistic matchup label derived from each fighter's dominant dimension.
        e.g. "STRIKER_VS_WRESTLER", "GRAPPLER_VS_GRAPPLER"

    style_clash_intensity:
        0.0 (mirror match) → 1.0 (maximum stylistic opposition).
        Drives the "collision" visual in the frontend Fight DNA component.

    primary_dimension:
        The single most decisive dimension for this matchup.
        Used by badge_engine for DECISION_PRISONER / ROUND_ONE_DEMON logic.
    """

    available: bool = True
    f1_dna: dict = Field(default_factory=dict)
    f2_dna: dict = Field(default_factory=dict)
    collision_type: str = "UNKNOWN"
    style_clash_intensity: float = Field(0.0, ge=0.0, le=1.0)
    primary_dimension: str = "STRIKING"


class FalseConsensusResult(BaseModel):
    """
    Output of false_consensus.compute().

    is_coinflip:
        True when model probability is within the "invisible coinflip" zone
        (abs(prob_f1 - prob_f2) < threshold) despite one fighter appearing
        to be a clear favourite in perception_gap aura scores.

    consensus_fighter:
        The fighter the public perceives as the clear favourite.
        None if public consensus is split or no perception data available.

    actual_gap:
        abs(prob_f1 - prob_f2) from the model.  Low value + high aura
        disparity = INVISIBLE_COINFLIP.

    label:
        NONE                — fight is not a disguised coinflip
        INVISIBLE_COINFLIP  — market says obvious, model says coinflip (≥ 0.25 gap)
        FAKE_MISMATCH       — labelled a blowout, model disagrees significantly (≥ 0.15)
        PUBLIC_CERTAINTY_TRAP — crowd more sure than data warrants (≥ 0.08)
        MILD_OVERCONFIDENCE — mild market overconfidence (< 0.08)

    display_message:
        One-sentence brand-voice message for the "FALSE CONSENSUS" banner.
        Empty string when label is NONE.
    """

    available: bool = True
    is_coinflip: bool = False
    consensus_fighter: Optional[str] = None
    actual_gap: float = Field(0.0, ge=0.0, le=1.0)
    label: Literal[
        "NONE",
        "INVISIBLE_COINFLIP",
        "FAKE_MISMATCH",
        "PUBLIC_CERTAINTY_TRAP",
        "MILD_OVERCONFIDENCE",
    ] = "NONE"
    display_message: str = ""


class NightmareResult(BaseModel):
    """
    Output of nightmare_matchup.compute().

    is_nightmare:
        True when fighter styles create a known lopsided matchup pattern
        (e.g. a pure wrestler vs. a wrestler-killer striker).

    nightmare_fighter:
        The fighter facing their stylistic nightmare.
        None if no nightmare detected.

    style_f1 / style_f2:
        Derived via utils.classify_style() at predict time (on-the-fly,
        not persisted — fighters.style column stays NULL in v1).

    matchup_label:
        Canonical matchup description, e.g. "WRESTLER_VS_STRIKER".
        None when severity is NONE.

    severity:
        NONE | MILD | SEVERE — how pronounced the stylistic nightmare is.
    """

    available: bool = True
    is_nightmare: bool = False
    nightmare_fighter: Optional[str] = None
    style_f1: str = "STRIKER"
    style_f2: str = "STRIKER"
    matchup_label: Optional[str] = None
    severity: Literal["NONE", "MILD", "SEVERE"] = "NONE"


class WinPathResult(BaseModel):
    """
    Output of win_path.compute().  Display name: Kill Chain.

    f1_paths / f2_paths:
        Ordered list of likely win paths for each fighter.
        Each path: {"path": str, "probability": float}
        Path labels (Opus to decide weights):
          EARLY_KO, GROUND_AND_POUND, SUBMISSION, TAKEDOWN_CONTROL,
          DECISION_VOLUME, DECISION_COUNTER, SPLIT_DECISION

    most_likely_method:
        Single overall method prediction for this fight.

    f1_primary_threat / f2_primary_threat:
        The primary danger zone for each fighter heading into this fight.
        e.g. "GRAPPLING", "STRIKING", "CLINCH"
    """

    available: bool = True
    f1_paths: list[dict] = Field(default_factory=list)
    f2_paths: list[dict] = Field(default_factory=list)
    most_likely_method: Literal["KO", "TKO", "SUB", "DEC", "SPLIT_DEC", "UNKNOWN"] = "UNKNOWN"
    f1_primary_threat: str = "STRIKING"
    f2_primary_threat: str = "STRIKING"


# ---------------------------------------------------------------------------
# New P1 result models
# ---------------------------------------------------------------------------

class UpsetResult(BaseModel):
    """
    Output of upset_alert.compute().  Display name: Dog Teeth.

    is_alert:
        True when the model gives the betting underdog a meaningful probability
        of winning — enough to warrant flagging.

    underdog_name:
        The fighter the model believes is undervalued by the market.
        None when no odds are available and alert is model-confidence-only.

    model_probability:
        Model's win probability for the underdog fighter.

    implied_probability:
        Market's implied probability for the underdog (from odds_history).
        None when odds are unavailable.

    edge:
        model_probability - implied_probability.
        None when odds are unavailable.

    american_odds:
        Underdog's current moneyline (positive = underdog).
        None when odds are unavailable.

    payout_multiplier:
        Return per $1 bet if underdog wins (american_odds / 100 + 1).

    reason:
        Short classification of why the alert fired.
        e.g. "MODEL_CONFIDENCE_NEAR_EVEN" | "UNDERDOG_EDGE"
    """

    is_alert: bool = False
    underdog_name: Optional[str] = None
    model_probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    implied_probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    edge: Optional[float] = Field(None, ge=-1.0, le=1.0)
    american_odds: Optional[int] = None
    payout_multiplier: Optional[float] = None
    reason: Optional[str] = None


class SharpMoneyResult(BaseModel):
    """
    Output of sharp_money.compute().  Display name: Sharp Echo.

    aligned:
        True when line has moved TOWARD the model's prediction from opening.
        Suggests sophisticated bettors agree with the model.

    movement_magnitude:
        Absolute implied probability shift from opening to current line.
        0.0 when no movement or no opening line available.

    signal:
        MARKET_ALIGNMENT — line moved toward model with meaningful magnitude
        NEUTRAL          — no meaningful movement or insufficient data
    """

    aligned: bool = False
    movement_magnitude: float = Field(0.0, ge=0.0, le=1.0)
    signal: Literal["MARKET_ALIGNMENT", "NEUTRAL"] = "NEUTRAL"


class CinematicTitle(BaseModel):
    """
    Output of cinematic_title.generate().

    title:
        The fight's cinematic title card (e.g. "Crown or Collapse").

    subtitle:
        One-line context subtitle (weight class, key signals).

    weight_class_color:
        CSS color token for the title display — matches weight class convention.
    """

    title: str = "The Matchup"
    subtitle: str = ""
    weight_class_color: str = "default"


# ---------------------------------------------------------------------------
# Badge model
# ---------------------------------------------------------------------------

# All valid badge keys.  Must match CLAUDE.md vocabulary exactly.
BadgeKey = Literal[
    "FRAUD_CHECK",
    "DOG_WITH_TEETH",
    "FALSE_FAVORITE",
    "DECISION_PRISONER",
    "ROUND_ONE_DEMON",
    "NARRATIVE_HOSTAGE",
    "CHAOS_CERTIFIED",
    "SILENT_KILLER",
    "PUBLIC_TAX",
    "AURA_MERCHANT",
    "CASUAL_MIRAGE",
]

# Canonical display metadata for each badge key.
# badge_engine uses this to populate label/color without hardcoding them.
BADGE_META: dict[str, dict] = {
    "FRAUD_CHECK":       {"label": "Fraud Check",        "color": "amber"},
    "DOG_WITH_TEETH":    {"label": "Dog With Teeth",      "color": "orange"},
    "FALSE_FAVORITE":    {"label": "False Favorite",      "color": "red"},
    "DECISION_PRISONER": {"label": "Decision Prisoner",   "color": "gray"},
    "ROUND_ONE_DEMON":   {"label": "Round One Demon",     "color": "red"},
    "NARRATIVE_HOSTAGE": {"label": "Narrative Hostage",   "color": "purple"},
    "CHAOS_CERTIFIED":   {"label": "Chaos Certified",     "color": "yellow"},
    "SILENT_KILLER":     {"label": "Silent Killer",       "color": "teal"},
    "PUBLIC_TAX":        {"label": "Public Tax",          "color": "gold"},
    "AURA_MERCHANT":     {"label": "Aura Merchant",       "color": "violet"},
    "CASUAL_MIRAGE":     {"label": "Casual Mirage",       "color": "pink"},
}


class Badge(BaseModel):
    """
    A single SCIPHR intelligence badge assigned to a fighter in this matchup.

    key:    must be one of the 11 defined BadgeKey values (Literal-validated).
    label:  human-readable display name (from BADGE_META).
    color:  CSS/Tailwind color token (from BADGE_META).
    reason: 1-sentence explanation of why this badge fired for this fight.
    fighter: which fighter this badge is assigned to (f1 or f2 name).
    """

    key: BadgeKey
    label: str
    color: str
    reason: str
    fighter: str


# ---------------------------------------------------------------------------
# Bundle result
# ---------------------------------------------------------------------------

class IntelligenceResult(BaseModel):
    """
    Full intelligence bundle returned by IntelligenceOrchestrator.compute().

    value_bet is never None — it always returns at minimum
    ValueBetResult(signal='NO_ODDS') when no odds are available.

    All other modules may be None if _safe_compute caught an exception.
    Callers and badge_engine must handle None for any optional module.
    """

    chaos: Optional[ChaosResult] = None
    perception_gap: Optional[PerceptionGapResult] = None
    narrative_trap: Optional[NarrativeTrapResult] = None
    value_bet: ValueBetResult = Field(default_factory=ValueBetResult)
    fight_dna: Optional[FightDNAResult] = None
    false_consensus: Optional[FalseConsensusResult] = None
    nightmare: Optional[NightmareResult] = None
    win_path: Optional[WinPathResult] = None
    upset_alert: Optional[UpsetResult] = None
    sharp_money: Optional[SharpMoneyResult] = None
    cinematic_title: Optional[CinematicTitle] = None
    badges: list[Badge] = Field(default_factory=list)
