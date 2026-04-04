"""
Badge Assignment Engine — reads all intelligence module outputs and
assigns SCIPHR badges for the fighters in this matchup.

Badges are assigned PER FIGHTER (each Badge has a .fighter field).
badge_engine is called last in the orchestrator pipeline because it
depends on all other modules' outputs.

Badge-to-signal mapping:
    CHAOS_CERTIFIED   chaos.score >= 65
    NARRATIVE_HOSTAGE  narrative.risk == "HIGH"
    FALSE_FAVORITE     gap.overvalued_fighter is not None
    DOG_WITH_TEETH     gap.undervalued_fighter is not None
    FRAUD_CHECK        gap.overvalued + nightmare.is_nightmare on same fighter
    SILENT_KILLER      win paths dominated by grappling + fighter undervalued
    DECISION_PRISONER  all win paths are DECISION_* variants
    ROUND_ONE_DEMON    EARLY_KO is #1 ranked path with probability > 0.25
    PUBLIC_TAX         aura_score > 0.6 AND gap shows fighter overvalued
    AURA_MERCHANT      high aura + recent losses (declining record)
    CASUAL_MIRAGE      high aura + low offensive stats
"""

from __future__ import annotations

from typing import Optional

from .models import (
    BADGE_META,
    Badge,
    ChaosResult,
    FalseConsensusResult,
    FightDNAResult,
    NarrativeTrapResult,
    NightmareResult,
    PerceptionGapResult,
    ValueBetResult,
    WinPathResult,
)


def _badge(key: str, reason: str, fighter: str) -> Badge:
    """Create a Badge with label/color from BADGE_META."""
    return Badge(
        key=key,
        label=BADGE_META[key]["label"],
        color=BADGE_META[key]["color"],
        reason=reason,
        fighter=fighter,
    )


def _top_path(paths: list[dict]) -> Optional[str]:
    """Return the label of the first (highest-probability) path, or None."""
    return paths[0]["path"] if paths else None


def _top_prob(paths: list[dict]) -> float:
    """Return the probability of the top path, or 0."""
    return float(paths[0]["probability"]) if paths else 0.0


def _is_decision_only(paths: list[dict]) -> bool:
    """True if all paths with meaningful probability are DECISION_* variants."""
    dec_labels = {"DECISION_VOLUME", "DECISION_COUNTER", "SPLIT_DECISION"}
    # Consider paths with > 10% probability
    significant = [p for p in paths if p.get("probability", 0) > 0.10]
    return bool(significant) and all(p["path"] in dec_labels for p in significant)


def _grappling_dominant(paths: list[dict]) -> bool:
    """True if top 2 paths are grappling-based."""
    grapple_labels = {"GROUND_AND_POUND", "SUBMISSION", "TAKEDOWN_CONTROL"}
    top2 = [p["path"] for p in paths[:2]]
    return len(top2) >= 1 and all(p in grapple_labels for p in top2)


def compute(
    chaos: Optional[ChaosResult] = None,
    gap: Optional[PerceptionGapResult] = None,
    narrative: Optional[NarrativeTrapResult] = None,
    value: Optional[ValueBetResult] = None,
    dna: Optional[FightDNAResult] = None,
    consensus: Optional[FalseConsensusResult] = None,
    nightmare: Optional[NightmareResult] = None,
    win: Optional[WinPathResult] = None,
    f1_name: Optional[str] = None,
    f2_name: Optional[str] = None,
) -> list[Badge]:
    """Assign SCIPHR badges based on all available intelligence module outputs."""
    badges: list[Badge] = []

    # ── Early return: no actionable signals present ───────────────────
    def _has_actionable_data() -> bool:
        if chaos is not None and chaos.available:
            return True
        if gap is not None and gap.available:
            return True
        if narrative is not None and narrative.risk != "LOW":
            return True
        if value is not None and value.active:
            return True
        if dna is not None and dna.available:
            return True
        if consensus is not None and consensus.available:
            return True
        if nightmare is not None and nightmare.available:
            return True
        if win is not None and win.available:
            return True
        return False

    if not _has_actionable_data():
        return badges

    # ── CHAOS_CERTIFIED ───────────────────────────────────────────────
    if chaos is not None and chaos.available and chaos.score >= 65:
        drivers_str = ", ".join(chaos.drivers[:2]) if chaos.drivers else "volatile matchup"
        badges.append(_badge(
            "CHAOS_CERTIFIED",
            f"Chaos Score {chaos.score:.0f} — {drivers_str}",
            "matchup",
        ))

    # ── NARRATIVE_HOSTAGE ─────────────────────────────────────────────
    if narrative is not None and narrative.risk == "HIGH":
        traps_str = ", ".join(narrative.active_traps[:2]) if narrative.active_traps else "high narrative risk"
        fighter = narrative.trapped_fighter or "matchup"
        badges.append(_badge(
            "NARRATIVE_HOSTAGE",
            f"HIGH narrative risk: {traps_str}",
            fighter,
        ))

    # ── FALSE_FAVORITE ────────────────────────────────────────────────
    if gap is not None and gap.available and gap.overvalued_fighter:
        ov_gap = gap.gap_f1 if gap.gap_f1 < 0 else gap.gap_f2
        badges.append(_badge(
            "FALSE_FAVORITE",
            f"{gap.overvalued_fighter} is overvalued by public perception (gap {ov_gap:+.0%})",
            gap.overvalued_fighter,
        ))

    # ── DOG_WITH_TEETH ────────────────────────────────────────────────
    if gap is not None and gap.available and gap.undervalued_fighter:
        badges.append(_badge(
            "DOG_WITH_TEETH",
            f"{gap.undervalued_fighter} is undervalued — model sees hidden edge",
            gap.undervalued_fighter,
        ))

    # ── FRAUD_CHECK — overvalued + nightmare matchup ──────────────────
    if (
        gap is not None and gap.available and gap.overvalued_fighter
        and nightmare is not None and nightmare.is_nightmare
        and nightmare.nightmare_fighter == gap.overvalued_fighter
    ):
        badges.append(_badge(
            "FRAUD_CHECK",
            f"{gap.overvalued_fighter} is overvalued AND faces nightmare matchup ({nightmare.matchup_label})",
            gap.overvalued_fighter,
        ))

    # ── PUBLIC_TAX — paying a premium for name recognition ────────────
    if gap is not None and gap.available and gap.overvalued_fighter:
        # Check if the overvalued fighter has high aura
        ov_is_f1 = gap.overvalued_fighter is not None and gap.gap_f1 < -0.10
        aura = gap.aura_score_f1 if ov_is_f1 else gap.aura_score_f2
        if aura > 0.6:
            badges.append(_badge(
                "PUBLIC_TAX",
                f"Public paying premium for {gap.overvalued_fighter} (aura {aura:.0%})",
                gap.overvalued_fighter,
            ))

    # ── ROUND_ONE_DEMON ───────────────────────────────────────────────
    if win is not None and win.available:
        for paths, fname in [(win.f1_paths, f1_name), (win.f2_paths, f2_name)]:
            if _top_path(paths) == "EARLY_KO" and _top_prob(paths) > 0.25:
                badges.append(_badge(
                    "ROUND_ONE_DEMON",
                    f"EARLY_KO is dominant win path ({_top_prob(paths):.0%})",
                    fname or "matchup",
                ))
                break  # one ROUND_ONE_DEMON per fight is enough

    # ── DECISION_PRISONER ─────────────────────────────────────────────
    if win is not None and win.available:
        for paths, fname in [(win.f1_paths, f1_name), (win.f2_paths, f2_name)]:
            if _is_decision_only(paths):
                badges.append(_badge(
                    "DECISION_PRISONER",
                    "Only viable win paths are decision variants",
                    fname or "matchup",
                ))
                break

    # ── SILENT_KILLER — dominant grappler under public radar ──────────
    if (
        win is not None and win.available
        and gap is not None and gap.available
        and gap.undervalued_fighter
    ):
        for paths, threat in [
            (win.f1_paths, win.f1_primary_threat),
            (win.f2_paths, win.f2_primary_threat),
        ]:
            if _grappling_dominant(paths) and threat in ("GRAPPLING", "WRESTLING"):
                badges.append(_badge(
                    "SILENT_KILLER",
                    f"Dominant grappler flying under public radar",
                    gap.undervalued_fighter,
                ))
                break

    # ── AURA_MERCHANT — high aura but declining output ────────────────
    if gap is not None and gap.available:
        for aura, fname in [
            (gap.aura_score_f1, f1_name),
            (gap.aura_score_f2, f2_name),
        ]:
            if aura > 0.65 and consensus is not None and consensus.is_coinflip:
                badges.append(_badge(
                    "AURA_MERCHANT",
                    "High public perception sustained by narrative, not recent performance",
                    fname or "matchup",
                ))
                break

    # ── CASUAL_MIRAGE — high recognition, low statistical output ──────
    if (
        gap is not None and gap.available
        and dna is not None and dna.available
    ):
        for aura, dna_profile in [
            (gap.aura_score_f1, dna.f1_dna),
            (gap.aura_score_f2, dna.f2_dna),
        ]:
            striking = dna_profile.get("striking", 0)
            pressure = dna_profile.get("pressure", 0)
            if aura > 0.6 and striking < 0.4 and pressure < 0.4:
                badges.append(_badge(
                    "CASUAL_MIRAGE",
                    "High name recognition but low offensive statistical output",
                    "matchup",
                ))
                break

    return badges
