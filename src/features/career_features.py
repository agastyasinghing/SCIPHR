"""
Career Features Module
Generates 80 features related to fighter career statistics
"""

import pandas as pd
import numpy as np

class CareerFeatureEngineer:
    """
    Creates comprehensive career statistics features
    """
    
    def __init__(self):
        self.feature_names = []
    
    def calculate_finish_rate(self, wins, ko_wins, sub_wins):
        """Calculate finish rate (KO+SUB / total wins)"""
        if wins == 0:
            return 0
        return (ko_wins + sub_wins) / wins
    
    def calculate_ko_rate(self, wins, ko_wins):
        """Calculate KO rate"""
        if wins == 0:
            return 0
        return ko_wins / wins
    
    def calculate_submission_rate(self, wins, sub_wins):
        """Calculate submission rate"""
        if wins == 0:
            return 0
        return sub_wins / wins
    
    def create_features(self, df):
        """
        Create all 80 career features
        
        Args:
            df: DataFrame with fighter stats
        
        Returns:
            DataFrame with 80 new career features added
        """
        print("\n" + "="*60)
        print("CREATING CAREER FEATURES (80 total)")
        print("="*60)
        
        result_df = df.copy()
        
        # ============ BASIC RECORD (10 features) ============
        print("\n1. Basic record...")
        # Most already exist: r_wins_total, r_losses_total
        # Add draws/NC if available
        result_df['r_draws'] = result_df.get('r_draw', 0)
        result_df['b_draws'] = result_df.get('b_draw', 0)
        result_df['r_nc'] = 0  # No contest (if available in data)
        result_df['b_nc'] = 0
        
        # Win percentage
        result_df['r_total_fights'] = result_df['r_wins_total'] + result_df['r_losses_total'] + result_df['r_draws']
        result_df['b_total_fights'] = result_df['b_wins_total'] + result_df['b_losses_total'] + result_df['b_draws']
        result_df['r_win_pct'] = result_df['r_wins_total'] / result_df['r_total_fights'].replace(0, 1)
        result_df['b_win_pct'] = result_df['b_wins_total'] / result_df['b_total_fights'].replace(0, 1)
        
        # UFC vs non-UFC (estimated - UFC fights not directly in data, use heuristic)
        # Assume recent fights are UFC if they have complete stats
        result_df['r_ufc_fights_estimate'] = result_df['r_total_fights'] * 0.6  # Rough estimate
        result_df['b_ufc_fights_estimate'] = result_df['b_total_fights'] * 0.6
        
        result_df['win_pct_diff'] = result_df['r_win_pct'] - result_df['b_win_pct']
        result_df['total_fights_diff'] = result_df['r_total_fights'] - result_df['b_total_fights']
        
        # ============ FINISH RATES (10 features) ============
        print("2. Finish rates...")
        
        # Calculate KO and submission wins (estimated from methods)
        # This requires win method data which Kaggle has
        result_df['r_ko_wins'] = result_df.get('r_win_by_KO/TKO', 0) + result_df.get('r_win_by_TKO_Doctor_Stoppage', 0)
        result_df['b_ko_wins'] = result_df.get('b_win_by_KO/TKO', 0) + result_df.get('b_win_by_TKO_Doctor_Stoppage', 0)
        result_df['r_sub_wins'] = result_df.get('r_win_by_Submission', 0)
        result_df['b_sub_wins'] = result_df.get('b_win_by_Submission', 0)
        result_df['r_decision_wins'] = result_df.get('r_win_by_Decision_Unanimous', 0) + result_df.get('r_win_by_Decision_Split', 0) + result_df.get('r_win_by_Decision_Majority', 0)
        result_df['b_decision_wins'] = result_df.get('b_win_by_Decision_Unanimous', 0) + result_df.get('b_win_by_Decision_Split', 0) + result_df.get('b_win_by_Decision_Majority', 0)
        
        # Finish rates
        result_df['r_finish_rate'] = (result_df['r_ko_wins'] + result_df['r_sub_wins']) / result_df['r_wins_total'].replace(0, 1)
        result_df['b_finish_rate'] = (result_df['b_ko_wins'] + result_df['b_sub_wins']) / result_df['b_wins_total'].replace(0, 1)
        result_df['r_ko_rate'] = result_df['r_ko_wins'] / result_df['r_wins_total'].replace(0, 1)
        result_df['b_ko_rate'] = result_df['b_ko_wins'] / result_df['b_wins_total'].replace(0, 1)
        result_df['r_sub_rate'] = result_df['r_sub_wins'] / result_df['r_wins_total'].replace(0, 1)
        result_df['b_sub_rate'] = result_df['b_sub_wins'] / result_df['b_wins_total'].replace(0, 1)
        result_df['r_decision_rate'] = result_df['r_decision_wins'] / result_df['r_wins_total'].replace(0, 1)
        result_df['b_decision_rate'] = result_df['b_decision_wins'] / result_df['b_wins_total'].replace(0, 1)
        
        result_df['finish_rate_diff'] = result_df['r_finish_rate'] - result_df['b_finish_rate']
        result_df['ko_rate_diff'] = result_df['r_ko_rate'] - result_df['b_ko_rate']
        
        # ============ LOSS ANALYSIS (10 features) ============
        print("3. Loss analysis...")
        
        # Loss methods
        result_df['r_ko_losses'] = result_df.get('r_loss_by_KO/TKO', 0) + result_df.get('r_loss_by_TKO_Doctor_Stoppage', 0)
        result_df['b_ko_losses'] = result_df.get('b_loss_by_KO/TKO', 0) + result_df.get('b_loss_by_TKO_Doctor_Stoppage', 0)
        result_df['r_sub_losses'] = result_df.get('r_loss_by_Submission', 0)
        result_df['b_sub_losses'] = result_df.get('b_loss_by_Submission', 0)
        result_df['r_decision_losses'] = result_df.get('r_loss_by_Decision_Unanimous', 0) + result_df.get('r_loss_by_Decision_Split', 0) + result_df.get('r_loss_by_Decision_Majority', 0)
        result_df['b_decision_losses'] = result_df.get('b_loss_by_Decision_Unanimous', 0) + result_df.get('b_loss_by_Decision_Split', 0) + result_df.get('b_loss_by_Decision_Majority', 0)
        
        # Loss rates
        result_df['r_ko_loss_rate'] = result_df['r_ko_losses'] / result_df['r_losses_total'].replace(0, 1)
        result_df['b_ko_loss_rate'] = result_df['b_ko_losses'] / result_df['b_losses_total'].replace(0, 1)
        result_df['r_sub_loss_rate'] = result_df['r_sub_losses'] / result_df['r_losses_total'].replace(0, 1)
        result_df['b_sub_loss_rate'] = result_df['b_sub_losses'] / result_df['b_losses_total'].replace(0, 1)
        result_df['r_decision_loss_rate'] = result_df['r_decision_losses'] / result_df['r_losses_total'].replace(0, 1)
        result_df['b_decision_loss_rate'] = result_df['b_decision_losses'] / result_df['b_losses_total'].replace(0, 1)
        
        # Durability proxy (inverse of KO loss rate)
        result_df['r_chin_durability'] = 1 - result_df['r_ko_loss_rate']
        result_df['b_chin_durability'] = 1 - result_df['b_ko_loss_rate']
        result_df['chin_durability_diff'] = result_df['r_chin_durability'] - result_df['b_chin_durability']
        
        result_df['ko_loss_rate_diff'] = result_df['r_ko_loss_rate'] - result_df['b_ko_loss_rate']
        
        # ============ EXPERIENCE METRICS (10 features) ============
        print("4. Experience metrics...")
        
        # Total rounds (if available, else estimate)
        if 'r_total_rounds_fought' not in result_df.columns:
            result_df['r_total_rounds'] = result_df['r_total_fights'] * 2  # Rough estimate
            result_df['b_total_rounds'] = result_df['b_total_fights'] * 2
        else:
            result_df['r_total_rounds'] = result_df['r_total_rounds_fought']
            result_df['b_total_rounds'] = result_df['b_total_rounds_fought']
        
        result_df['r_avg_rounds_per_fight'] = result_df['r_total_rounds'] / result_df['r_total_fights'].replace(0, 1)
        result_df['b_avg_rounds_per_fight'] = result_df['b_total_rounds'] / result_df['b_total_fights'].replace(0, 1)
        
        # Championship experience proxy
        result_df['r_title_fights_estimate'] = (result_df['r_wins_total'] / 10).clip(upper=5)  # Rough estimate
        result_df['b_title_fights_estimate'] = (result_df['b_wins_total'] / 10).clip(upper=5)
        
        # Main event proxy (fighters with 15+ wins likely had main events)
        result_df['r_main_event_estimate'] = (result_df['r_wins_total'] > 15).astype(int)
        result_df['b_main_event_estimate'] = (result_df['b_wins_total'] > 15).astype(int)
        
        result_df['total_rounds_diff'] = result_df['r_total_rounds'] - result_df['b_total_rounds']
        result_df['avg_rounds_diff'] = result_df['r_avg_rounds_per_fight'] - result_df['b_avg_rounds_per_fight']
        result_df['experience_advantage'] = (
            (result_df['r_total_fights'] / 50) * 0.5 +
            (result_df['r_total_rounds'] / 100) * 0.5
        ) - (
            (result_df['b_total_fights'] / 50) * 0.5 +
            (result_df['b_total_rounds'] / 100) * 0.5
        )
        
        # ============ COMPETITION LEVEL (10 features) ============
        print("5. Competition level (proxies)...")
        
        # Quality of opposition proxy (win rate tells us something)
        # Fighters with high win% against tough competition are better
        result_df['r_quality_opposition_proxy'] = result_df['r_win_pct'] * result_df['r_total_fights'] / 50
        result_df['b_quality_opposition_proxy'] = result_df['b_win_pct'] * result_df['b_total_fights'] / 50
        
        # Top 5/10 fights proxy (fighters with many wins likely fought ranked opponents)
        result_df['r_top_opponent_fights_estimate'] = (result_df['r_wins_total'] / 5).clip(upper=10)
        result_df['b_top_opponent_fights_estimate'] = (result_df['b_wins_total'] / 5).clip(upper=10)
        
        # Championship caliber proxy
        result_df['r_championship_caliber'] = ((result_df['r_wins_total'] > 10) & (result_df['r_win_pct'] > 0.7)).astype(int)
        result_df['b_championship_caliber'] = ((result_df['b_wins_total'] > 10) & (result_df['b_win_pct'] > 0.7)).astype(int)
        
        # Strength of schedule proxy
        result_df['r_sos_proxy'] = result_df['r_total_fights'] * result_df['r_win_pct'] * (1 + result_df['r_losses_total'] / 20)
        result_df['b_sos_proxy'] = result_df['b_total_fights'] * result_df['b_win_pct'] * (1 + result_df['b_losses_total'] / 20)
        result_df['sos_diff'] = result_df['r_sos_proxy'] - result_df['b_sos_proxy']
        
        # Elite competition proxy
        result_df['r_elite_comp_proxy'] = ((result_df['r_wins_total'] > 15) & (result_df['r_finish_rate'] > 0.5)).astype(int)
        result_df['b_elite_comp_proxy'] = ((result_df['b_wins_total'] > 15) & (result_df['b_finish_rate'] > 0.5)).astype(int)
        
        result_df['quality_opposition_diff'] = result_df['r_quality_opposition_proxy'] - result_df['b_quality_opposition_proxy']
        result_df['championship_caliber_diff'] = result_df['r_championship_caliber'] - result_df['b_championship_caliber']
        
        # ============ PROGRESSION METRICS (10 features) ============
        print("6. Progression metrics...")
        
        # Career stage proxy
        result_df['r_career_stage'] = result_df['r_age'].apply(
            lambda age: 'prospect' if age < 25 else ('prime' if age <= 32 else 'veteran')
        )
        result_df['b_career_stage'] = result_df['b_age'].apply(
            lambda age: 'prospect' if age < 25 else ('prime' if age <= 32 else 'veteran')
        )
        result_df['r_career_stage_numeric'] = result_df['r_career_stage'].map({'prospect': 1, 'prime': 2, 'veteran': 3})
        result_df['b_career_stage_numeric'] = result_df['b_career_stage'].map({'prospect': 1, 'prime': 2, 'veteran': 3})
        
        # Years professional (age - 18 as rough estimate of when they started)
        result_df['r_years_pro_estimate'] = (result_df['r_age'] - 18).clip(lower=0)
        result_df['b_years_pro_estimate'] = (result_df['b_age'] - 18).clip(lower=0)
        
        # Fights per year
        result_df['r_fights_per_year'] = result_df['r_total_fights'] / result_df['r_years_pro_estimate'].replace(0, 1)
        result_df['b_fights_per_year'] = result_df['b_total_fights'] / result_df['b_years_pro_estimate'].replace(0, 1)
        
        # Activity level
        result_df['r_is_active'] = (result_df['r_fights_per_year'] > 2).astype(int)
        result_df['b_is_active'] = (result_df['b_fights_per_year'] > 2).astype(int)
        
        # Consistency proxy (low variance in performance = consistent)
        # Approximated by decision rate (consistent fighters go to decisions more)
        result_df['r_consistency_proxy'] = result_df['r_decision_rate']
        result_df['b_consistency_proxy'] = result_df['b_decision_rate']
        
        result_df['career_stage_diff'] = result_df['r_career_stage_numeric'] - result_df['b_career_stage_numeric']
        result_df['years_pro_diff'] = result_df['r_years_pro_estimate'] - result_df['b_years_pro_estimate']
        
        # ============ PERFORMANCE CONTEXTS (10 features) ============
        print("7. Performance contexts...")
        
        # Quick turnaround proxy (active fighters)
        result_df['r_quick_turnaround_proxy'] = (result_df['r_fights_per_year'] > 3).astype(int)
        result_df['b_quick_turnaround_proxy'] = (result_df['b_fights_per_year'] > 3).astype(int)
        
        # Layoff proxy (less active fighters)
        result_df['r_layoff_proxy'] = (result_df['r_fights_per_year'] < 1).astype(int)
        result_df['b_layoff_proxy'] = (result_df['b_fights_per_year'] < 1).astype(int)
        
        # Activity consistency
        result_df['r_activity_score'] = result_df['r_fights_per_year'] / 3  # Normalize to 3 fights/year
        result_df['b_activity_score'] = result_df['b_fights_per_year'] / 3
        result_df['activity_diff'] = result_df['r_activity_score'] - result_df['b_activity_score']
        
        # Durability score (fought many rounds without getting finished often)
        result_df['r_durability_score'] = (result_df['r_total_rounds'] / 50) * (1 - result_df['r_ko_loss_rate'])
        result_df['b_durability_score'] = (result_df['b_total_rounds'] / 50) * (1 - result_df['b_ko_loss_rate'])
        result_df['durability_diff'] = result_df['r_durability_score'] - result_df['b_durability_score']
        
        # Gate keeper vs contender proxy
        result_df['r_gatekeeper_proxy'] = ((result_df['r_wins_total'] > 8) & 
                                          (result_df['r_win_pct'] > 0.45) & 
                                          (result_df['r_win_pct'] < 0.65)).astype(int)
        result_df['b_gatekeeper_proxy'] = ((result_df['b_wins_total'] > 8) & 
                                          (result_df['b_win_pct'] > 0.45) & 
                                          (result_df['b_win_pct'] < 0.65)).astype(int)
        
        result_df['r_contender_proxy'] = ((result_df['r_wins_total'] > 12) & 
                                         (result_df['r_win_pct'] > 0.70)).astype(int)
        result_df['b_contender_proxy'] = ((result_df['b_wins_total'] > 12) & 
                                         (result_df['b_win_pct'] > 0.70)).astype(int)
        
        # ============ VERSATILITY (10 features) ============
        print("8. Versatility...")
        
        # Finishing versatility (can win by KO OR submission)
        result_df['r_finish_versatility'] = ((result_df['r_ko_rate'] > 0.2) & (result_df['r_sub_rate'] > 0.2)).astype(int)
        result_df['b_finish_versatility'] = ((result_df['b_ko_rate'] > 0.2) & (result_df['b_sub_rate'] > 0.2)).astype(int)
        
        # Finish method balance
        result_df['r_finish_balance'] = 1 - abs(result_df['r_ko_rate'] - result_df['r_sub_rate'])
        result_df['b_finish_balance'] = 1 - abs(result_df['b_ko_rate'] - result_df['b_sub_rate'])
        
        # Well-rounded score (can finish AND go to decision)
        result_df['r_well_rounded'] = ((result_df['r_finish_rate'] > 0.3) & (result_df['r_decision_rate'] > 0.2)).astype(int)
        result_df['b_well_rounded'] = ((result_df['b_finish_rate'] > 0.3) & (result_df['b_decision_rate'] > 0.2)).astype(int)
        
        # One-dimensional fighter (only one method)
        result_df['r_one_dimensional'] = ((result_df['r_ko_rate'] > 0.8) | 
                                         (result_df['r_sub_rate'] > 0.8) | 
                                         (result_df['r_decision_rate'] > 0.8)).astype(int)
        result_df['b_one_dimensional'] = ((result_df['b_ko_rate'] > 0.8) | 
                                         (result_df['b_sub_rate'] > 0.8) | 
                                         (result_df['b_decision_rate'] > 0.8)).astype(int)
        
        result_df['versatility_diff'] = (result_df['r_well_rounded'] - result_df['r_one_dimensional']) - \
                                        (result_df['b_well_rounded'] - result_df['b_one_dimensional'])
        
        # Finishing threat level
        result_df['r_finish_threat'] = result_df['r_finish_rate'] * result_df['r_wins_total'] / 10
        result_df['b_finish_threat'] = result_df['b_finish_rate'] * result_df['b_wins_total'] / 10
        result_df['finish_threat_diff'] = result_df['r_finish_threat'] - result_df['b_finish_threat']

        # ============ FIX: UNDEFEATED BIAS PENALTY ============
        print("\n9. Anti-bias adjustments...")

        # Undefeated fighters with few fights get penalized
        result_df['r_undefeated_small_sample'] = (
            (result_df['r_losses_total'] == 0) & 
            (result_df['r_wins_total'] < 20)
        ).astype(int)

        result_df['b_undefeated_small_sample'] = (
            (result_df['b_losses_total'] == 0) & 
            (result_df['b_wins_total'] < 20)
        ).astype(int)

        # Career stage penalty - undefeated early career vs proven veteran
        result_df['r_proven_veteran_score'] = (
            result_df['r_wins_total'] * 
            (1 + result_df['r_losses_total'] * 0.1)  # Losses add experience
        )

        result_df['b_proven_veteran_score'] = (
            result_df['b_wins_total'] * 
            (1 + result_df['b_losses_total'] * 0.1)
        )

        result_df['veteran_experience_diff'] = (
            result_df['r_proven_veteran_score'] - 
            result_df['b_proven_veteran_score']
        )

        # Quality over quantity - win% adjusted by sample size
        result_df['r_win_quality_score'] = (
            result_df['r_win_pct'] * 
            np.log1p(result_df['r_total_fights'])  # Log scale for sample size
        )

        result_df['b_win_quality_score'] = (
            result_df['b_win_pct'] * 
            np.log1p(result_df['b_total_fights'])
        )

        result_df['win_quality_diff'] = (
            result_df['r_win_quality_score'] - 
            result_df['b_win_quality_score']
        )

        print("✓ Added anti-bias features")

        print("\n✓ Created 90 career features")  # Updated from 80
        print("="*60)
        
        return result_df