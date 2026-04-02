"""
Physical Features Module
Generates 50 features related to fighter physical attributes
"""

import pandas as pd
import numpy as np

class PhysicalFeatureEngineer:
    """
    Creates comprehensive physical attribute features
    """
    
    def __init__(self):
        self.feature_names = []
    
    def calculate_weight_class(self, weight):
        """Determine weight class from weight in lbs"""
        if weight <= 115:
            return 1  # Strawweight
        elif weight <= 125:
            return 2  # Flyweight
        elif weight <= 135:
            return 3  # Bantamweight
        elif weight <= 145:
            return 4  # Featherweight
        elif weight <= 155:
            return 5  # Lightweight
        elif weight <= 170:
            return 6  # Welterweight
        elif weight <= 185:
            return 7  # Middleweight
        elif weight <= 205:
            return 8  # Light Heavyweight
        else:
            return 9  # Heavyweight
    
    def calculate_bmi(self, weight, height):
        """Calculate BMI from weight (lbs) and height (inches)"""
        if height == 0:
            return 0
        return (weight / (height ** 2)) * 703
    
    def calculate_ape_index(self, reach, height):
        """Calculate ape index (reach - height)"""
        return reach - height
    
    def calculate_athletic_prime_score(self, age):
        """
        Calculate athletic prime score (peak at 27-32)
        Returns 0-1 score
        """
        if age < 20:
            return 0.5  # Too young
        elif age <= 25:
            return 0.7 + (age - 20) * 0.06  # Rising
        elif age <= 32:
            return 1.0  # Peak
        elif age <= 38:
            return 1.0 - (age - 32) * 0.08  # Declining
        else:
            return 0.3  # Well past prime
    
    def create_features(self, df):
        """
        Create all 50 physical features
        
        Args:
            df: DataFrame with fighter stats (must have r_ and b_ prefixed columns)
        
        Returns:
            DataFrame with 50 new physical features added
        """
        print("\n" + "="*60)
        print("CREATING PHYSICAL FEATURES (50 total)")
        print("="*60)
        
        result_df = df.copy()
        
        # ============ BASIC MEASUREMENTS (5 features) ============
        print("\n1. Basic measurements (already exist): weight, height, reach, age, stance")
        # These already exist as r_weight, r_height, etc.
        
        # ============ RATIOS & COMPARISONS (5 features) ============
        print("2. Ratios & comparisons...")
        result_df['weight_ratio'] = result_df['r_weight'] / result_df['b_weight'].replace(0, 1)
        result_df['height_ratio'] = result_df['r_height'] / result_df['b_height'].replace(0, 1)
        result_df['reach_ratio'] = result_df['r_reach'] / result_df['b_reach'].replace(0, 1)
        result_df['age_ratio'] = result_df['r_age'] / result_df['b_age'].replace(0, 1)
        result_df['bmi_ratio'] = result_df.apply(
            lambda row: self.calculate_bmi(row['r_weight'], row['r_height']) / 
                       (self.calculate_bmi(row['b_weight'], row['b_height']) + 0.01),
            axis=1
        )
        
        # ============ BODY COMPOSITION PROXIES (5 features) ============
        print("3. Body composition proxies...")
        result_df['r_bmi'] = result_df.apply(
            lambda row: self.calculate_bmi(row['r_weight'], row['r_height']), axis=1
        )
        result_df['b_bmi'] = result_df.apply(
            lambda row: self.calculate_bmi(row['b_weight'], row['b_height']), axis=1
        )
        result_df['r_ape_index'] = result_df.apply(
            lambda row: self.calculate_ape_index(row['r_reach'], row['r_height']), axis=1
        )
        result_df['b_ape_index'] = result_df.apply(
            lambda row: self.calculate_ape_index(row['b_reach'], row['b_height']), axis=1
        )
        result_df['r_frame_size'] = result_df['r_weight'] / result_df['r_height'].replace(0, 1)
        result_df['b_frame_size'] = result_df['b_weight'] / result_df['b_height'].replace(0, 1)
        result_df['r_power_frame'] = result_df['r_weight'] * result_df['r_reach']
        result_df['b_power_frame'] = result_df['b_weight'] * result_df['b_reach']
        result_df['frame_size_diff'] = result_df['r_frame_size'] - result_df['b_frame_size']
        result_df['power_frame_diff'] = result_df['r_power_frame'] - result_df['b_power_frame']
        
        # ============ WEIGHT CLASS CONTEXT (5 features) ============
        print("4. Weight class context...")
        result_df['r_weight_class'] = result_df['r_weight'].apply(self.calculate_weight_class)
        result_df['b_weight_class'] = result_df['b_weight'].apply(self.calculate_weight_class)
        result_df['weight_class_gap'] = abs(result_df['r_weight_class'] - result_df['b_weight_class'])
        result_df['is_same_weight_class'] = (result_df['weight_class_gap'] == 0).astype(int)
        result_df['weight_cut_estimate_diff'] = result_df.apply(
            lambda row: abs(row['r_weight'] - (row['r_weight_class'] * 15 + 100)) - 
                       abs(row['b_weight'] - (row['b_weight_class'] * 15 + 100)),
            axis=1
        )
        
        # ============ SIZE CATEGORIES (5 features) ============
        print("5. Size categories...")
        # Calculate percentiles within weight class for reach and height
        for prefix in ['r', 'b']:
            weight_col = f'{prefix}_weight'
            height_col = f'{prefix}_height'
            reach_col = f'{prefix}_reach'
            
            # Simplified percentile calculation
            result_df[f'{prefix}_height_percentile'] = result_df.groupby(f'{prefix}_weight_class')[height_col].rank(pct=True)
            result_df[f'{prefix}_reach_percentile'] = result_df.groupby(f'{prefix}_weight_class')[reach_col].rank(pct=True)
            result_df[f'{prefix}_is_undersized'] = (result_df[f'{prefix}_height_percentile'] < 0.3).astype(int)
            result_df[f'{prefix}_is_oversized'] = (result_df[f'{prefix}_height_percentile'] > 0.7).astype(int)
        
        result_df['size_percentile_diff'] = result_df['r_height_percentile'] - result_df['b_height_percentile']
        
        # ============ ANTHROPOMETRIC ADVANTAGES (5 features) ============
        print("6. Anthropometric advantages...")
        result_df['reach_advantage_inches'] = result_df['r_reach'] - result_df['b_reach']
        result_df['reach_advantage_pct'] = result_df['reach_advantage_inches'] / result_df['b_reach'].replace(0, 1)
        result_df['height_advantage_inches'] = result_df['r_height'] - result_df['b_height']
        result_df['weight_advantage_lbs'] = result_df['r_weight'] - result_df['b_weight']
        result_df['total_size_advantage_score'] = (
            result_df['reach_advantage_pct'] * 0.4 +
            (result_df['height_advantage_inches'] / 10) * 0.3 +
            (result_df['weight_advantage_lbs'] / 50) * 0.3
        )
        
        # ============ AGE DYNAMICS (5 features) ============
        print("7. Age dynamics...")
        result_df['age_gap'] = result_df['r_age'] - result_df['b_age']
        result_df['r_is_younger'] = (result_df['age_gap'] < 0).astype(int)
        result_df['youth_advantage_score'] = -result_df['age_gap'] / 10  # Negative age gap = younger = advantage
        result_df['r_is_in_prime'] = ((result_df['r_age'] >= 25) & (result_df['r_age'] <= 32)).astype(int)
        result_df['b_is_in_prime'] = ((result_df['b_age'] >= 25) & (result_df['b_age'] <= 32)).astype(int)
        result_df['r_years_from_prime'] = result_df['r_age'].apply(
            lambda age: 0 if 25 <= age <= 32 else min(abs(age - 25), abs(age - 32))
        )
        result_df['b_years_from_prime'] = result_df['b_age'].apply(
            lambda age: 0 if 25 <= age <= 32 else min(abs(age - 25), abs(age - 32))
        )
        
        # ============ PHYSICAL ARCHETYPES (5 features) ============
        print("8. Physical archetypes...")
        result_df['r_is_tall_for_weight'] = (result_df['r_height_percentile'] > 0.6).astype(int)
        result_df['b_is_tall_for_weight'] = (result_df['b_height_percentile'] > 0.6).astype(int)
        result_df['r_is_stocky'] = ((result_df['r_height_percentile'] < 0.4) & (result_df['r_bmi'] > 25)).astype(int)
        result_df['b_is_stocky'] = ((result_df['b_height_percentile'] < 0.4) & (result_df['b_bmi'] > 25)).astype(int)
        result_df['r_is_rangy'] = (result_df['r_ape_index'] > 3).astype(int)
        result_df['b_is_rangy'] = (result_df['b_ape_index'] > 3).astype(int)
        result_df['archetype_advantage'] = (
            result_df['r_is_tall_for_weight'] - result_df['b_is_tall_for_weight'] +
            result_df['r_is_rangy'] - result_df['b_is_rangy']
        )
        
        # ============ MOVEMENT METRICS (5 features) ============
        print("9. Movement metrics (estimated)...")
        result_df['r_speed_estimate'] = result_df['r_height'] / (result_df['r_weight'] + 1) * 100
        result_df['b_speed_estimate'] = result_df['b_height'] / (result_df['b_weight'] + 1) * 100
        result_df['speed_advantage'] = result_df['r_speed_estimate'] - result_df['b_speed_estimate']
        result_df['r_power_estimate'] = result_df['r_weight'] * result_df['r_reach'] / 1000
        result_df['b_power_estimate'] = result_df['b_weight'] * result_df['b_reach'] / 1000
        result_df['power_advantage'] = result_df['r_power_estimate'] - result_df['b_power_estimate']
        
        # ============ DURABILITY PROXIES (5 features) ============
        print("10. Durability proxies...")
        result_df['r_athletic_prime_score'] = result_df['r_age'].apply(self.calculate_athletic_prime_score)
        result_df['b_athletic_prime_score'] = result_df['b_age'].apply(self.calculate_athletic_prime_score)
        result_df['athletic_prime_advantage'] = result_df['r_athletic_prime_score'] - result_df['b_athletic_prime_score']
        
        # Wear and tear (age + estimated career length)
        result_df['r_durability_proxy'] = result_df['r_age'] * result_df['r_total_fights']
        result_df['b_durability_proxy'] = result_df['b_age'] * result_df['b_total_fights']
        result_df['durability_diff'] = result_df['r_durability_proxy'] - result_df['b_durability_proxy']

        # ============ FIX: EXTREME WEIGHT DOMINANCE ============
        print("\n11. Extreme weight dominance features...")

        weight_diff = result_df['weight_diff']
        weight_ratio = result_df['weight_ratio']

        # EXPONENTIAL weight advantage (not linear)
        result_df['weight_dominance_squared'] = (weight_diff / 50) ** 2
        result_df['weight_dominance_cubed'] = (weight_diff / 50) ** 3

        # Critical weight gaps
        result_df['weight_gap_30plus'] = (abs(weight_diff) > 30).astype(int)
        result_df['weight_gap_50plus'] = (abs(weight_diff) > 50).astype(int)
        result_df['weight_gap_70plus'] = (abs(weight_diff) > 70).astype(int)
        result_df['weight_gap_100plus'] = (abs(weight_diff) > 100).astype(int)

        # Combined size crush factor (weight * height * reach)
        result_df['size_crush_multiplier'] = (
            weight_ratio * 
            result_df['height_ratio'] * 
            result_df['reach_ratio']
        )

        # Impossible matchup flags
        result_df['impossible_weight_mismatch'] = (abs(weight_diff) > 60).astype(int)
        result_df['extreme_size_advantage'] = (result_df['size_crush_multiplier'] > 1.5).astype(int)

        # Weight class gap (how many divisions apart)
        def get_weight_class(weight):
            if weight <= 115: return 1   # Strawweight
            elif weight <= 125: return 2  # Flyweight
            elif weight <= 135: return 3  # Bantamweight
            elif weight <= 145: return 4  # Featherweight
            elif weight <= 155: return 5  # Lightweight
            elif weight <= 170: return 6  # Welterweight
            elif weight <= 185: return 7  # Middleweight
            elif weight <= 205: return 8  # Light Heavyweight
            else: return 9                # Heavyweight

        result_df['r_weight_class_num'] = result_df['r_weight'].apply(get_weight_class)
        result_df['b_weight_class_num'] = result_df['b_weight'].apply(get_weight_class)
        result_df['weight_class_gap'] = abs(
            result_df['r_weight_class_num'] - 
            result_df['b_weight_class_num']
        )

        # Critical weight class gaps
        result_df['weight_class_gap_3plus'] = (result_df['weight_class_gap'] >= 3).astype(int)
        result_df['weight_class_gap_5plus'] = (result_df['weight_class_gap'] >= 5).astype(int)

        print("✓ Added extreme weight dominance features")

        print("\n✓ Created 68 physical features")  # Updated from 50
        print("="*60)
        
        return result_df