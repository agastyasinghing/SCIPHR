"""
Golden Feature Calculator - SIMPLIFIED
Just extracts pre-calculated features from the dataset
"""

import pandas as pd
import numpy as np

class GoldenFeatureCalculator:
    """
    Extracts features from golden dataset (features already calculated)
    """
    
    def __init__(self, data_path='data/golden_full_converted.csv'):
        """Load the full golden dataset"""
        print("Loading golden dataset for feature calculation...")
        self.data = pd.read_csv(data_path)
        self.data['date'] = pd.to_datetime(self.data['date'])
        print(f"✓ Loaded {len(self.data)} fights with {len(self.data.columns)} columns")
    
    def get_latest_fighter_stats(self, fighter_name):
        """
        Get fighter's most recent base stats (from their last fight)
        """
        # Find most recent fight
        recent = self.data[
            (self.data['r_name'] == fighter_name) | 
            (self.data['b_name'] == fighter_name)
        ].sort_values('date', ascending=False)
        
        if len(recent) == 0:
            return {}
        
        fight = recent.iloc[0]
        
        # Determine which corner
        if fight['r_name'] == fighter_name:
            prefix = 'r_'
        else:
            prefix = 'b_'
        
        # Extract all stats
        stats = {}
        for col in fight.index:
            if col.startswith(prefix):
                stat_name = col[2:]  # Remove r_ or b_ prefix
                stats[stat_name] = fight[col]
        
        return stats
    
    def build_full_feature_vector(self, fighter1_name, fighter2_name, feature_names):
        """
        Build complete 5,401 feature vector for a matchup
        CRITICAL: Must exclude fights where both fighters appear together!
        """
        print(f"\n🔧 Building full feature vector for {fighter1_name} vs {fighter2_name}...")
        
        # Find most recent fights for each fighter
        # EXCLUDING any fight where they faced each other
        f1_fights = self.data[
            ((self.data['r_name'] == fighter1_name) | (self.data['b_name'] == fighter1_name))
        ].sort_values('date', ascending=False)
        
        f2_fights = self.data[
            ((self.data['r_name'] == fighter2_name) | (self.data['b_name'] == fighter2_name))
        ].sort_values('date', ascending=False)
        
        # Exclude fights where BOTH fighters appear
        f1_fights = f1_fights[
            ~((f1_fights['r_name'] == fighter2_name) | (f1_fights['b_name'] == fighter2_name))
        ]
        
        f2_fights = f2_fights[
            ~((f2_fights['r_name'] == fighter1_name) | (f2_fights['b_name'] == fighter1_name))
        ]
        
        if len(f1_fights) == 0:
            print(f"   ✗ No fights found for {fighter1_name}")
            return None
        
        if len(f2_fights) == 0:
            print(f"   ✗ No fights found for {fighter2_name}")
            return None
        
        # Get most recent fight for each
        f1_fight = f1_fights.iloc[0]
        f2_fight = f2_fights.iloc[0]
        
        # Determine which corner each fighter was in their last fight
        f1_was_red = (f1_fight['r_name'] == fighter1_name)
        f2_was_red = (f2_fight['r_name'] == fighter2_name)
        
        print(f"   Fighter 1 most recent: {f1_fight['r_name']} vs {f1_fight['b_name']} ({f1_fight['date'].strftime('%Y-%m-%d')})")
        print(f"   Fighter 1 was in: {'RED' if f1_was_red else 'BLUE'} corner in that fight")
        
        print(f"   Fighter 2 most recent: {f2_fight['r_name']} vs {f2_fight['b_name']} ({f2_fight['date'].strftime('%Y-%m-%d')})")
        print(f"   Fighter 2 was in: {'RED' if f2_was_red else 'BLUE'} corner in that fight")
        
        # Build feature dictionary
        all_stats = {}
        
        # Extract fighter1's stats and map to RED corner
        f1_prefix = 'r_' if f1_was_red else 'b_'
        f1_suffix = '_r' if f1_was_red else '_b'
        
        print(f"\n   DEBUG - Fighter 1 extraction:")
        print(f"   f1_prefix: {f1_prefix}, f1_suffix: {f1_suffix}")
        f1_extracted = 0
        
        for col in f1_fight.index:
            # Get all stats for fighter1 (whether they were red or blue)
            if col.startswith(f1_prefix):
                # Prefix-based column (r_fighter_w, b_fighter_w, etc)
                new_col = 'r_' + col[len(f1_prefix):]
                all_stats[new_col] = f1_fight[col]
                f1_extracted += 1
                if f1_extracted <= 3:
                    print(f"   {col} -> {new_col} = {f1_fight[col]}")
            elif col.endswith(f1_suffix):
                # Suffix-based column (wins_3_r, wins_3_b, etc)
                base_name = col[:-len(f1_suffix)]
                new_col = base_name + '_r'
                all_stats[new_col] = f1_fight[col]
                f1_extracted += 1
        
        print(f"   Extracted {f1_extracted} columns for fighter 1")
        
        # Extract fighter2's stats and map to BLUE corner
        f2_prefix = 'r_' if f2_was_red else 'b_'
        f2_suffix = '_r' if f2_was_red else '_b'
        
        print(f"\n   DEBUG - Fighter 2 extraction:")
        print(f"   f2_prefix: {f2_prefix}, f2_suffix: {f2_suffix}")
        f2_extracted = 0
        
        for col in f2_fight.index:
            # Get all stats for fighter2 (whether they were red or blue)
            if col.startswith(f2_prefix):
                # Prefix-based column
                new_col = 'b_' + col[len(f2_prefix):]
                all_stats[new_col] = f2_fight[col]
                f2_extracted += 1
                if f2_extracted <= 3:
                    print(f"   {col} -> {new_col} = {f2_fight[col]}")
            elif col.endswith(f2_suffix):
                # Suffix-based column
                base_name = col[:-len(f2_suffix)]
                new_col = base_name + '_b'
                all_stats[new_col] = f2_fight[col]
                f2_extracted += 1
        
        print(f"   Extracted {f2_extracted} columns for fighter 2")
        
        # FINAL CHECK
        print(f"\n   FINAL STATS CHECK:")
        print(f"   r_fighter_w (should be {fighter1_name}): {all_stats.get('r_fighter_w', 'MISSING')}")
        print(f"   b_fighter_w (should be {fighter2_name}): {all_stats.get('b_fighter_w', 'MISSING')}")
        
        # Calculate matchup-specific difference features
        print("\n   Calculating matchup-specific difference features...")
        self._calculate_differences(all_stats)
        
        # Convert to DataFrame
        temp_df = pd.DataFrame([all_stats])
        
        # Convert string columns to numeric
        object_cols = temp_df.select_dtypes(include=['object']).columns
        for col in object_cols:
            temp_df[col] = pd.Categorical(temp_df[col]).codes
        
        # Extract features in correct order
        feature_vector = []
        missing_count = 0
        
        for feature_name in feature_names:
            if feature_name in temp_df.columns:
                val = temp_df[feature_name].iloc[0]
                if pd.notna(val) and np.isfinite(val):
                    feature_vector.append(float(val))
                else:
                    feature_vector.append(0.0)
            else:
                feature_vector.append(0.0)
                missing_count += 1
        
        non_zero = sum(1 for f in feature_vector if f != 0)
        print(f"   ✓ Built {len(feature_vector)} features ({non_zero} non-zero, {missing_count} missing)")
        
        return feature_vector
    
    def _calculate_differences(self, all_stats):
        """
        Calculate difference features between red and blue fighters
        Format: diff_STAT = r_STAT - b_STAT
        """
        # Find all r_ stats
        r_stats = {k: v for k, v in all_stats.items() if k.startswith('r_')}
        
        for r_key, r_val in r_stats.items():
            # Get corresponding blue stat
            b_key = r_key.replace('r_', 'b_', 1)
            
            if b_key in all_stats:
                b_val = all_stats[b_key]
                
                # Calculate difference if both are numeric
                if pd.api.types.is_numeric_dtype(type(r_val)) and pd.api.types.is_numeric_dtype(type(b_val)):
                    if pd.notna(r_val) and pd.notna(b_val):
                        # Create diff column name
                        stat_name = r_key[2:]  # Remove 'r_' prefix
                        diff_key = f'diff_{stat_name}'
                        all_stats[diff_key] = r_val - b_val
        
        # Also handle _r and _b suffixes
        r_suffix_stats = {k: v for k, v in all_stats.items() if k.endswith('_r')}
        
        for r_key, r_val in r_suffix_stats.items():
            b_key = r_key[:-2] + '_b'  # Replace _r with _b
            
            if b_key in all_stats:
                b_val = all_stats[b_key]
                
                if pd.api.types.is_numeric_dtype(type(r_val)) and pd.api.types.is_numeric_dtype(type(b_val)):
                    if pd.notna(r_val) and pd.notna(b_val):
                        stat_name = r_key[:-2]  # Remove '_r' suffix
                        diff_key = f'diff_{stat_name}'
                        all_stats[diff_key] = r_val - b_val