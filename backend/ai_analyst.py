"""
AI Fight Analyst
Generates fight analysis using a structured template.
Claude API wiring deferred to post-launch (TODO-19).

Return contract:
    generate_fight_analysis() ALWAYS returns a dict with these keys:
        key_factors:      list[str]  — 2-4 bullet points
        confidence_level: str        — HIGH | MEDIUM | LOW
        confidence_text:  str        — one-line summary of confidence
        betting_advice:   str        — one-line action
        risk_factors:     list[str]  — 1-2 bullets
        implied_odds:     str        — American odds string (e.g. "-180", "+140")
        disclaimer:       str        — responsible gambling notice

    When Claude is wired (TODO-19), the Claude response MUST be parsed
    into this same dict shape — do NOT change the frontend to accept a raw string.
"""

import os
from intelligence.utils import classify_style


def _remap_for_style(stats: dict) -> dict:
    """
    Remap the fighter stats dict keys to the fighters-table column names
    expected by classify_style().

    Stats dict uses _total suffixes and percentage values for accuracy fields.
    classify_style() expects raw 0-1 fractions for str_acc / str_def.
    """
    return {
        "sub_avg": stats.get("sub_avg_total", 0) or 0,
        "td_avg":  stats.get("td_avg_total",  0) or 0,
        "slpm":    stats.get("SLpM_total",     0) or 0,
        # stats dict stores accuracy as 0–100; classify_style expects 0–1
        "str_acc": (stats.get("sig_str_acc_total", 0) or 0) / 100,
        "str_def": (stats.get("sig_str_def_total", 0) or 0) / 100,
    }


def _ko_rate(stats: dict) -> float:
    """
    Proxy KO rate: total knockdowns / total fights.
    Imprecise but the only KO-related metric in the fighter stats dict.
    """
    total_fights = (stats.get("wins_total", 0) or 0) + (stats.get("losses_total", 0) or 0)
    kds = stats.get("total_knockdowns", 0) or 0
    return kds / total_fights if total_fights > 0 else 0.0


class AIFightAnalyst:
    """
    Generates AI-powered fight analysis using a template.
    Claude SDK wiring deferred to post-launch (TODO-19).
    """

    def __init__(self):
        pass

    def generate_fight_analysis(
        self,
        prediction_data: dict,
        intelligence_signals: dict | None = None,
    ) -> dict:
        """
        Generate structured fight analysis.

        Args:
            prediction_data: Dict with fighter1, fighter2, winner, confidence,
                             fighter1_stats, fighter2_stats.
            intelligence_signals: Optional dict mirroring the IntelligenceResult
                             model_dump(). Keys: chaos, perception_gap,
                             narrative_trap, value_bet. None for ad-hoc predictions.

        Returns:
            dict with keys: key_factors, confidence_level, confidence_text,
            betting_advice, risk_factors, implied_odds, disclaimer.
            (See module docstring for full contract.)
        """
        return self._generate_template_analysis(prediction_data, intelligence_signals or {})

    def _build_prompt(
        self,
        prediction_data: dict,
        intelligence_signals: dict,
    ) -> str:
        """
        Build the Claude prompt. Kept in sync with the PRD §10.11 spec.
        Used when Claude SDK is wired (TODO-19).
        """
        f1 = prediction_data["fighter1"]
        f2 = prediction_data["fighter2"]
        winner = prediction_data["winner"]
        confidence = prediction_data["confidence"]
        f1s = prediction_data.get("fighter1_stats", {})
        f2s = prediction_data.get("fighter2_stats", {})

        chaos    = intelligence_signals.get("chaos") or {}
        pg       = intelligence_signals.get("perception_gap") or {}
        nt       = intelligence_signals.get("narrative_trap") or {}
        vb       = intelligence_signals.get("value_bet") or {}

        f1_style = classify_style(_remap_for_style(f1s))
        f2_style = classify_style(_remap_for_style(f2s))
        f1_ko    = _ko_rate(f1s)
        f2_ko    = _ko_rate(f2s)

        return f"""You are SCIPHR, an AI-powered UFC fight prediction system.
Analyze this matchup and provide a sharp, data-driven fight breakdown.

Fight: {f1} vs {f2}
Weight Class: {prediction_data.get('weight_class', 'Unknown')}

Model Prediction: {winner} wins with {confidence:.1%} confidence

Intelligence Signals:
- Chaos Score: {chaos.get('score', 'N/A')}/100 ({chaos.get('tier', 'N/A')})
- Perception Gap: {pg.get('magnitude', 'N/A')} ({pg.get('direction_f1', 'N/A')} / {pg.get('direction_f2', 'N/A')})
- Narrative Risk: {nt.get('risk', 'LOW')}
- Value Signal: {vb.get('signal', 'NO_ODDS')}

Fighter Stats:
{f1}: {int(f1s.get('wins_total', 0))}-{int(f1s.get('losses_total', 0))}, {f1_style}, KO rate: {f1_ko:.0%}
{f2}: {int(f2s.get('wins_total', 0))}-{int(f2s.get('losses_total', 0))}, {f2_style}, KO rate: {f2_ko:.0%}

Write a 3-paragraph analysis covering:
1. Why the model favors {winner} — key statistical advantages
2. The biggest threat to this prediction — what could go wrong
3. Betting angle — where the edge is (or isn't) given current lines

Be direct, data-first, and slightly adversarial toward weak narratives.
Avoid: clichés, "it depends," excessive hedging. Channel Scipio: precise intelligence."""

    def _generate_template_analysis(
        self,
        data: dict,
        intelligence_signals: dict,
    ) -> dict:
        """
        Template-based analysis. Returns the canonical dict shape.
        """
        fighter1   = data["fighter1"]
        fighter2   = data["fighter2"]
        winner     = data["winner"]
        confidence = data["confidence"]
        f1s        = data.get("fighter1_stats", {})
        f2s        = data.get("fighter2_stats", {})

        chaos = intelligence_signals.get("chaos") or {}
        pg    = intelligence_signals.get("perception_gap") or {}
        nt    = intelligence_signals.get("narrative_trap") or {}
        vb    = intelligence_signals.get("value_bet") or {}

        # Style and KO rate
        f1_style = classify_style(_remap_for_style(f1s))
        f2_style = classify_style(_remap_for_style(f2s))
        f1_ko    = _ko_rate(f1s)
        f2_ko    = _ko_rate(f2s)

        # Confidence tier
        if confidence >= 0.75:
            conf_level = "HIGH"
            conf_text  = "Strong pick with clear statistical advantages"
        elif confidence >= 0.60:
            conf_level = "MEDIUM"
            conf_text  = "Competitive matchup, slight edge to the model pick"
        else:
            conf_level = "LOW"
            conf_text  = "Too close to call — avoid betting"

        # Key factors
        factors = []

        striking_diff = f1s.get("SLpM_total", 0) - f2s.get("SLpM_total", 0)
        if abs(striking_diff) > 1.5:
            better = fighter1 if striking_diff > 0 else fighter2
            factors.append(f"{better} has significant striking advantage ({abs(striking_diff):.1f} strikes/min)")

        reach_diff = f1s.get("reach", 0) - f2s.get("reach", 0)
        if abs(reach_diff) > 5:
            longer = fighter1 if reach_diff > 0 else fighter2
            factors.append(f"{longer} has {abs(reach_diff):.0f}cm reach advantage")

        age_diff = f1s.get("age", 0) - f2s.get("age", 0)
        if abs(age_diff) > 5:
            younger = fighter1 if age_diff < 0 else fighter2
            factors.append(f"{younger} is {abs(age_diff):.0f} years younger")

        f1_win_pct = f1s.get("wins_total", 0) / max(f1s.get("wins_total", 0) + f1s.get("losses_total", 0), 1)
        f2_win_pct = f2s.get("wins_total", 0) / max(f2s.get("wins_total", 0) + f2s.get("losses_total", 0), 1)
        if abs(f1_win_pct - f2_win_pct) > 0.15:
            better = fighter1 if f1_win_pct > f2_win_pct else fighter2
            factors.append(f"{better} has superior win percentage")

        # Style-based factor
        winner_style = f1_style if winner == fighter1 else f2_style
        if winner_style in ("GRAPPLER", "WRESTLER"):
            factors.append(f"{winner}'s grappling style ({winner_style}) aligns with model edge")
        elif winner_style == "COUNTER":
            factors.append(f"{winner} is a counter-fighter — rewards patience over aggression")

        # Intelligence signal factors
        if chaos.get("tier") in ("HIGH", "EXTREME"):
            factors.append(f"High chaos fight ({chaos.get('tier')}) — model confidence discounted accordingly")
        if pg.get("magnitude") in ("MODERATE", "LARGE") and pg.get("undervalued_fighter"):
            factors.append(f"Perception Gap: {pg['undervalued_fighter']} undervalued by public")
        if nt.get("risk") == "HIGH" and nt.get("trapped_fighter"):
            factors.append(f"Narrative Trap flagged on {nt['trapped_fighter']} — discount hype")

        if len(factors) < 2:
            factors.append("Model analyzed 5,401 features across both fighters")
            factors.append("Prediction based on 8,000+ historical fight outcomes")

        # Betting advice
        if confidence >= 0.75:
            bet_advice = f"Strong value on {winner} if odds are reasonable"
        elif confidence >= 0.60:
            bet_advice = f"Small bet on {winner} warranted — proceed with caution"
        else:
            bet_advice = "Skip this fight — too unpredictable for confident betting"

        # Value signal overlay
        if vb.get("signal") in ("EDGE_DETECTED", "STRONG_EDGE"):
            bet_advice += f" | Line Crack detected ({vb['signal']})"
        elif vb.get("signal") == "FADE_OPPORTUNITY":
            bet_advice += " | Fade Opportunity — model strongly disagrees with the market"

        # Risk factors
        risks = []
        if confidence < 0.70:
            risks.append("Close matchup — either fighter can win")
        if chaos.get("tier") in ("HIGH", "EXTREME"):
            risks.append(f"Chaos Score {chaos.get('score', 0):.0f}/100 — high finish volatility")
        if nt.get("risk") == "HIGH":
            risks.append("Narrative Trap active — emotionally charged fight context")
        winner_ko = f1_ko if winner == fighter1 else f2_ko
        if winner_ko < 0.05:
            risks.append(f"{winner} low KO rate ({winner_ko:.0%}) — stoppage finish unlikely")
        if not risks:
            risks.append("MMA is inherently unpredictable — even strong model picks can lose")

        # Implied odds from confidence
        if confidence >= 0.50:
            decimal_odds = 1 / confidence
            american_odds = -100 * (decimal_odds - 1) / (1 - (decimal_odds - 1) / decimal_odds)
            implied_odds = "-" + str(int(abs(american_odds)))
        else:
            decimal_odds = 1 / confidence
            american_odds = 100 * (decimal_odds - 1)
            implied_odds = "+" + str(int(american_odds))

        return {
            "key_factors":      factors[:4],
            "confidence_level": conf_level,
            "confidence_text":  conf_text,
            "betting_advice":   bet_advice,
            "risk_factors":     risks[:2],
            "implied_odds":     implied_odds,
            "disclaimer":       "This is not financial advice. Bet responsibly. Never bet more than you can afford to lose.",
        }


# Singleton instance
ai_analyst = AIFightAnalyst()
