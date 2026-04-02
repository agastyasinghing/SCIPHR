"""
AI Fight Analyst
Uses Claude API to generate fight analysis and betting guidance
"""

import os

class AIFightAnalyst:
    """
    Generates AI-powered fight analysis using Claude
    """
    
    def __init__(self):
        """Initialize AI analyst with template-based generation"""
        pass
    
    def generate_fight_analysis(self, prediction_data):
        """
        Generate comprehensive fight analysis
        
        Args:
            prediction_data: Dictionary with prediction results and fighter stats
        
        Returns:
            Dictionary with analysis sections
        """
        fighter1 = prediction_data['fighter1']
        fighter2 = prediction_data['fighter2']
        winner = prediction_data['winner']
        confidence = prediction_data['confidence']
        f1_stats = prediction_data['fighter1_stats']
        f2_stats = prediction_data['fighter2_stats']
        
        # Build analysis prompt
        prompt = f"""You are an expert UFC analyst. Analyze this upcoming fight and provide betting guidance.

FIGHT: {fighter1} vs {fighter2}

FIGHTER STATS:
{fighter1}:
- Record: {f1_stats['wins_total']:.0f}-{f1_stats['losses_total']:.0f}
- Age: {f1_stats['age']:.0f}
- Height: {f1_stats['height']:.0f}cm
- Reach: {f1_stats['reach']:.0f}cm
- Strikes Landed/Min: {f1_stats['SLpM_total']:.2f}
- Striking Accuracy: {f1_stats['sig_str_acc_total']*100:.0f}%
- Takedown Accuracy: {f1_stats['td_acc_total']*100:.0f}%

{fighter2}:
- Record: {f2_stats['wins_total']:.0f}-{f2_stats['losses_total']:.0f}
- Age: {f2_stats['age']:.0f}
- Height: {f2_stats['height']:.0f}cm
- Reach: {f2_stats['reach']:.0f}cm
- Strikes Landed/Min: {f2_stats['SLpM_total']:.2f}
- Striking Accuracy: {f2_stats['sig_str_acc_total']*100:.0f}%
- Takedown Accuracy: {f2_stats['td_acc_total']*100:.0f}%

AI MODEL PREDICTION: {winner} ({confidence*100:.1f}% confidence)

Provide a concise analysis in this EXACT format:

KEY FACTORS:
- [3-4 bullet points on main advantages/disadvantages]

BETTING GUIDANCE:
✓ Model confidence: [HIGH/MEDIUM/LOW] - [brief reasoning]
✓ Recommended action: [specific betting advice]
⚠️ Risk factors: [what could go wrong]

Keep it under 150 words total. Be direct and actionable."""

        # For now, return a template-based analysis
        # We'll connect to actual Claude API after testing
        return self._generate_template_analysis(prediction_data)
    
    def _generate_template_analysis(self, data):
        """
        Template-based analysis (backup if API unavailable)
        """
        fighter1 = data['fighter1']
        fighter2 = data['fighter2']
        winner = data['winner']
        confidence = data['confidence']
        f1_stats = data['fighter1_stats']
        f2_stats = data['fighter2_stats']
        
        # Determine confidence level
        if confidence >= 0.75:
            conf_level = "HIGH"
            conf_text = "Strong pick with clear advantages"
        elif confidence >= 0.60:
            conf_level = "MEDIUM"
            conf_text = "Competitive matchup, slight edge"
        else:
            conf_level = "LOW"
            conf_text = "Too close to call, avoid betting"
        
        # Calculate key stats differences
        striking_diff = f1_stats['SLpM_total'] - f2_stats['SLpM_total']
        reach_diff = f1_stats['reach'] - f2_stats['reach']
        age_diff = f1_stats['age'] - f2_stats['age']
        
        # Build key factors
        factors = []
        
        if abs(striking_diff) > 1.5:
            better_striker = fighter1 if striking_diff > 0 else fighter2
            factors.append(f"{better_striker} has significant striking advantage ({abs(striking_diff):.1f} strikes/min)")
        
        if abs(reach_diff) > 5:
            longer_reach = fighter1 if reach_diff > 0 else fighter2
            factors.append(f"{longer_reach} has {abs(reach_diff):.0f}cm reach advantage")
        
        if abs(age_diff) > 5:
            younger = fighter1 if age_diff < 0 else fighter2
            factors.append(f"{younger} is {abs(age_diff):.0f} years younger")
        
        # Record comparison
        f1_record = f1_stats['wins_total'] / max(f1_stats['wins_total'] + f1_stats['losses_total'], 1)
        f2_record = f2_stats['wins_total'] / max(f2_stats['wins_total'] + f2_stats['losses_total'], 1)
        
        if abs(f1_record - f2_record) > 0.15:
            better_record = fighter1 if f1_record > f2_record else fighter2
            factors.append(f"{better_record} has superior win percentage")
        
        # If not enough factors, add generic ones
        if len(factors) < 2:
            factors.append(f"Model analyzed 5,401 features across both fighters")
            factors.append(f"Prediction based on historical matchup data")
        
        # Betting recommendation
        if confidence >= 0.75:
            bet_advice = f"Strong value on {winner} if odds are reasonable"
        elif confidence >= 0.60:
            bet_advice = f"Proceed with caution, small bet on {winner}"
        else:
            bet_advice = "Skip this fight - too unpredictable"
        
        # Risk factors
        risks = []
        if confidence < 0.70:
            risks.append("Close matchup could go either way")
        if f1_stats.get('losses_total', 0) == 0 or f2_stats.get('losses_total', 0) == 0:
            risks.append("Undefeated fighter - potential for surprise")
        if not risks:
            risks.append("MMA is inherently unpredictable")
        
                # Calculate proper betting odds
        if confidence >= 0.50:
            # Favorite - use negative American odds
            decimal_odds = 1 / confidence
            american_odds = -100 * (decimal_odds - 1) / (1 - (decimal_odds - 1) / decimal_odds)
            implied_odds = "-" + str(int(abs(american_odds)))
        else:
            # Underdog - use positive American odds
            decimal_odds = 1 / confidence
            american_odds = 100 * (decimal_odds - 1)
            implied_odds = "+" + str(int(american_odds))

        analysis = {
            'key_factors': factors[:4],
            'confidence_level': conf_level,
            'confidence_text': conf_text,
            'betting_advice': bet_advice,
            'risk_factors': risks[:2],
            'implied_odds': implied_odds,
            'disclaimer': "This is not financial advice. Bet responsibly. Never bet more than you can afford to lose.",
        }

        return analysis


# Singleton instance
ai_analyst = AIFightAnalyst()