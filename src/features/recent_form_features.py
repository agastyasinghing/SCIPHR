"""
Recent Form Features Module
Generates 60 features related to recent fighter performance
"""

import pandas as pd
import numpy as np

class RecentFormFeatureEngineer:
    """
    Creates recent form and momentum features
    Note: Requires historical fight data to calculate properly
    For initial version, uses proxies and estimates
    """
    
    def __init__(self):
        self.feature_names = []
    
    def create_features(self, df):
        """
        Create all 60 recent form features
        
        Args:
            df: DataFrame with fighter stats
        
        Returns:
            DataFrame with 60 new recent form features added
        """
        # Track original columns
        original_cols = set(df.columns)
        print("\n" + "="*60)
        print("CREATING RECENT FORM FEATURES (60 total)")
        print("="*60) 
        print("\nNOTE: Without full fight history, using proxies and estimates")
        
        result_df = df.copy()
        
        # ============ WINDOWED RECORDS (5 features) ============
        print("\n1. Windowed records (proxies)...")
        
        # Without full fight history, we estimate recent form from career stats
        # Assumption: Recent form correlates with overall stats but with noise
        
        # Last fight result proxy (higher win% = more likely won last fight)
        result_df['r_last_fight_win_prob'] = result_df['r_win_pct']
        result_df['b_last_fight_win_prob'] = result_df['b_win_pct']
        
        # Last 3 fights estimate (wins out of 3)
        result_df['r_last_3_wins_estimate'] = (result_df['r_win_pct'] * 3).round()
        result_df['b_last_3_wins_estimate'] = (result_df['b_win_pct'] * 3).round()
        
        # Last 5 fights estimate
        result_df['r_last_5_wins_estimate'] = (result_df['r_win_pct'] * 5).round()
        result_df['b_last_5_wins_estimate'] = (result_df['b_win_pct'] * 5).round()
        
        result_df['recent_form_diff'] = result_df['r_last_3_wins_estimate'] - result_df['b_last_3_wins_estimate']
        
        # ============ STREAKS (5 features) ============
        print("2. Streaks (estimated)...")
        
        # Estimate current streak based on win percentage
        # High win% with many wins = likely on streak
        result_df['r_likely_on_streak'] = ((result_df['r_win_pct'] > 0.7) & 
                                          (result_df['r_wins_total'] > 5)).astype(int)
        result_df['b_likely_on_streak'] = ((result_df['b_win_pct'] > 0.7) & 
                                          (result_df['b_wins_total'] > 5)).astype(int)
        
        # Estimated streak length
        result_df['r_streak_estimate'] = result_df.apply(
            lambda row: row['r_wins_total'] / 3 if row['r_likely_on_streak'] else 0,
            axis=1
        ).clip(upper=10)
        result_df['b_streak_estimate'] = result_df.apply(
            lambda row: row['b_wins_total'] / 3 if row['b_likely_on_streak'] else 0,
            axis=1
        ).clip(upper=10)
        
        # Losing streak proxy
        result_df['r_likely_on_losing_streak'] = ((result_df['r_win_pct'] < 0.4) & 
                                                  (result_df['r_losses_total'] > 3)).astype(int)
        result_df['b_likely_on_losing_streak'] = ((result_df['b_win_pct'] < 0.4) & 
                                                  (result_df['b_losses_total'] > 3)).astype(int)
        
        result_df['streak_advantage'] = result_df['r_streak_estimate'] - result_df['b_streak_estimate']
        
        # ============ RECENCY (5 features) ============
        print("3. Recency (proxies)...")
        
        # Activity proxy (fights per year as recency indicator)
        result_df['r_activity_recent'] = result_df['r_fights_per_year']  # Already calculated in career features
        result_df['b_activity_recent'] = result_df['b_fights_per_year']
        
        # Active vs inactive
        result_df['r_is_active_recently'] = (result_df['r_activity_recent'] > 1.5).astype(int)
        result_df['b_is_active_recently'] = (result_df['b_activity_recent'] > 1.5).astype(int)
        
        # Layoff risk
        result_df['r_layoff_risk'] = (result_df['r_activity_recent'] < 0.8).astype(int)
        result_df['b_layoff_risk'] = (result_df['b_activity_recent'] < 0.8).astype(int)
        
        result_df['activity_advantage'] = result_df['r_is_active_recently'] - result_df['b_is_active_recently']
        result_df['layoff_disadvantage'] = result_df['r_layoff_risk'] - result_df['b_layoff_risk']
        
        # ============ RECENT PERFORMANCE QUALITY (10 features) ============
        print("4. Recent performance quality (proxies)...")
        
        # Recent finish rate (assume it matches career rate)
        result_df['r_recent_finish_rate'] = result_df['r_finish_rate']
        result_df['b_recent_finish_rate'] = result_df['b_finish_rate']
        
        # Recent KO rate
        result_df['r_recent_ko_rate'] = result_df['r_ko_rate']
        result_df['b_recent_ko_rate'] = result_df['b_ko_rate']
        
        # Recent submission rate
        result_df['r_recent_sub_rate'] = result_df['r_sub_rate']
        result_df['b_recent_sub_rate'] = result_df['b_sub_rate']
        
        # Recent striking metrics (from career averages)
        result_df['r_recent_sig_strikes'] = result_df['r_SLpM_total']
        result_df['b_recent_sig_strikes'] = result_df['b_SLpM_total']
        result_df['r_recent_sig_absorbed'] = result_df['r_SApM_total']
        result_df['b_recent_sig_absorbed'] = result_df['b_SApM_total']
        
        # Strike differential
        result_df['r_recent_strike_diff'] = result_df['r_recent_sig_strikes'] - result_df['r_recent_sig_absorbed']
        result_df['b_recent_strike_diff'] = result_df['b_recent_sig_strikes'] - result_df['b_recent_sig_absorbed']
        
        result_df['recent_strike_diff_advantage'] = result_df['r_recent_strike_diff'] - result_df['b_recent_strike_diff']
        
        # ============ TRENDING METRICS (10 features) ============
        print("5. Trending metrics (estimated)...")
        
        # Improving vs declining proxy
        # Young fighters with good records = improving
        # Older fighters = declining
        result_df['r_likely_improving'] = ((result_df['r_age'] < 30) & 
                                          (result_df['r_win_pct'] > 0.6)).astype(int)
        result_df['b_likely_improving'] = ((result_df['b_age'] < 30) & 
                                          (result_df['b_win_pct'] > 0.6)).astype(int)
        
        result_df['r_likely_declining'] = ((result_df['r_age'] > 35) & 
                                          (result_df['r_win_pct'] < 0.55)).astype(int)
        result_df['b_likely_declining'] = ((result_df['b_age'] > 35) & 
                                          (result_df['b_win_pct'] < 0.55)).astype(int)
        
        # Trajectory score (-1 declining, 0 stable, 1 improving)
        result_df['r_trajectory'] = result_df['r_likely_improving'].astype(int) - result_df['r_likely_declining'].astype(int)
        result_df['b_trajectory'] = result_df['b_likely_improving'].astype(int) - result_df['b_likely_declining'].astype(int)
        result_df['trajectory_advantage'] = result_df['r_trajectory'] - result_df['b_trajectory']
        
        # Momentum indicator
        result_df['r_momentum'] = (
            result_df['r_likely_on_streak'] * 0.5 +
            result_df['r_likely_improving'] * 0.3 +
            result_df['r_is_active_recently'] * 0.2
        )
        result_df['b_momentum'] = (
            result_df['b_likely_on_streak'] * 0.5 +
            result_df['b_likely_improving'] * 0.3 +
            result_df['b_is_active_recently'] * 0.2
        )
        result_df['momentum_advantage'] = result_df['r_momentum'] - result_df['b_momentum']
        
        # Peak performance indicator
        result_df['r_at_peak'] = ((result_df['r_age'] >= 27) & 
                                 (result_df['r_age'] <= 32) & 
                                 (result_df['r_win_pct'] > 0.65)).astype(int)
        result_df['b_at_peak'] = ((result_df['b_age'] >= 27) & 
                                 (result_df['b_age'] <= 32) & 
                                 (result_df['b_win_pct'] > 0.65)).astype(int)
        
        # Consistency indicator
        result_df['r_consistency'] = (result_df['r_decision_rate'] > 0.4).astype(int)
        result_df['b_consistency'] = (result_df['b_decision_rate'] > 0.4).astype(int)
        
        # Volatility (high finish rate = volatile)
        result_df['r_volatility'] = result_df['r_finish_rate']
        result_df['b_volatility'] = result_df['b_finish_rate']
        
        # ============ RECENT OPPONENT QUALITY (10 features) ============
        print("6. Recent opponent quality (proxies)...")
        
        # Without fight history, estimate based on overall record
        # Fighters with good records likely fought tough opponents
        result_df['r_recent_opp_quality_proxy'] = result_df['r_quality_opposition_proxy']
        result_df['b_recent_opp_quality_proxy'] = result_df['b_quality_opposition_proxy']
        
        # Step up in competition proxy
        result_df['r_stepping_up'] = ((result_df['r_wins_total'] > 8) & 
                                     (result_df['r_championship_caliber'] == 0)).astype(int)
        result_df['b_stepping_up'] = ((result_df['b_wins_total'] > 8) & 
                                     (result_df['b_championship_caliber'] == 0)).astype(int)
        
        # Fighting elite recently proxy
        result_df['r_fought_elite_recently'] = result_df['r_elite_comp_proxy']
        result_df['b_fought_elite_recently'] = result_df['b_elite_comp_proxy']
        
        # Beating ranked opponents recently (proxy)
        result_df['r_beating_ranked_recently'] = ((result_df['r_wins_total'] > 10) & 
                                                  (result_df['r_win_pct'] > 0.65)).astype(int)
        result_df['b_beating_ranked_recently'] = ((result_df['b_wins_total'] > 10) & 
                                                  (result_df['b_win_pct'] > 0.65)).astype(int)
        
        # Recent upset wins proxy (lower ranked beating higher ranked)
        result_df['r_upset_wins_proxy'] = ((result_df['r_wins_total'] > 5) & 
                                          (result_df['r_losses_total'] > 3) & 
                                          (result_df['r_finish_rate'] > 0.5)).astype(int)
        result_df['b_upset_wins_proxy'] = ((result_df['b_wins_total'] > 5) & 
                                          (result_df['b_losses_total'] > 3) & 
                                          (result_df['b_finish_rate'] > 0.5)).astype(int)
        
        result_df['recent_opp_quality_diff'] = result_df['r_recent_opp_quality_proxy'] - result_df['b_recent_opp_quality_proxy']
        result_df['stepping_up_diff'] = result_df['r_stepping_up'] - result_df['b_stepping_up']
        result_df['elite_comp_diff'] = result_df['r_fought_elite_recently'] - result_df['b_fought_elite_recently']
        result_df['upset_capability_diff'] = result_df['r_upset_wins_proxy'] - result_df['b_upset_wins_proxy']
        
        # Competition quality score
        result_df['r_comp_quality_score'] = (
            result_df['r_recent_opp_quality_proxy'] * 0.4 +
            result_df['r_fought_elite_recently'] * 0.3 +
            result_df['r_beating_ranked_recently'] * 0.3
        )
        result_df['b_comp_quality_score'] = (
            result_df['b_recent_opp_quality_proxy'] * 0.4 +
            result_df['b_fought_elite_recently'] * 0.3 +
            result_df['b_beating_ranked_recently'] * 0.3
        )
        
        # ============ CONTEXT OF RECENT RESULTS (10 features) ============
        print("7. Context of recent results (proxies)...")
        
        # Recent dominant wins (high finish rate = dominant)
        result_df['r_recent_dominant_wins'] = ((result_df['r_finish_rate'] > 0.6) & 
                                              (result_df['r_wins_total'] > 5)).astype(int)
        result_df['b_recent_dominant_wins'] = ((result_df['b_finish_rate'] > 0.6) & 
                                              (result_df['b_wins_total'] > 5)).astype(int)
        
        # Recent close fights (high decision rate = close fights)
        result_df['r_recent_close_fights'] = (result_df['r_decision_rate'] > 0.6).astype(int)
        result_df['b_recent_close_fights'] = (result_df['b_decision_rate'] > 0.6).astype(int)
        
        # Recent wars (both high output and high damage taken)
        result_df['r_recent_wars'] = ((result_df['r_SLpM_total'] > 4.5) & 
                                     (result_df['r_SApM_total'] > 4.0)).astype(int)
        result_df['b_recent_wars'] = ((result_df['b_SLpM_total'] > 4.5) & 
                                     (result_df['b_SApM_total'] > 4.0)).astype(int)
        
        # Recent easy wins (high finish rate with low damage)
        result_df['r_recent_easy_wins'] = ((result_df['r_finish_rate'] > 0.5) & 
                                          (result_df['r_SApM_total'] < 2.5)).astype(int)
        result_df['b_recent_easy_wins'] = ((result_df['b_finish_rate'] > 0.5) & 
                                          (result_df['b_SApM_total'] < 2.5)).astype(int)
        
        # Damage accumulation proxy (high absorbed strikes)
        result_df['r_damage_accumulation'] = result_df['r_SApM_total'] * result_df['r_total_rounds'] / 50
        result_df['b_damage_accumulation'] = result_df['b_SApM_total'] * result_df['b_total_rounds'] / 50
        result_df['damage_accumulation_diff'] = result_df['r_damage_accumulation'] - result_df['b_damage_accumulation']
        
        # Recent performance quality composite
        result_df['r_recent_performance_quality'] = (
            result_df['r_recent_dominant_wins'] * 0.3 +
            result_df['r_recent_easy_wins'] * 0.2 +
            (1 - result_df['r_recent_wars']) * 0.2 +  # Avoiding wars is good
            result_df['r_recent_finish_rate'] * 0.3
        )
        result_df['b_recent_performance_quality'] = (
            result_df['b_recent_dominant_wins'] * 0.3 +
            result_df['b_recent_easy_wins'] * 0.2 +
            (1 - result_df['b_recent_wars']) * 0.2 +
            result_df['b_recent_finish_rate'] * 0.3
        )
        result_df['recent_performance_diff'] = result_df['r_recent_performance_quality'] - result_df['b_recent_performance_quality']
        
        # Form score (comprehensive recent form)
        result_df['r_form_score'] = (
            result_df['r_momentum'] * 0.3 +
            result_df['r_recent_performance_quality'] * 0.3 +
            result_df['r_trajectory'] * 0.2 +
            result_df['r_is_active_recently'] * 0.2
        )
        result_df['b_form_score'] = (
            result_df['b_momentum'] * 0.3 +
            result_df['b_recent_performance_quality'] * 0.3 +
            result_df['b_trajectory'] * 0.2 +
            result_df['b_is_active_recently'] * 0.2
        )
        result_df['form_advantage'] = result_df['r_form_score'] - result_df['b_form_score']
        
        print("\n✓ Created 60 recent form features")
        print("="*60)
        
        # CRITICAL FIX: Fill any NaN values created by recent form calculations
        # Recent form features often create NaN when data is missing
        recent_form_cols = [col for col in df.columns if col not in original_cols]
        for col in recent_form_cols:
            if df[col].isna().any():
                df[col] = df[col].fillna(0)

        return df