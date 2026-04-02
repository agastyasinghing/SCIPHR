"""
Convert FULL UFC Golden Dataset - ALL 5,437 columns
"""

import pandas as pd
import numpy as np

def convert_full_golden_dataset(input_path='data/UFC_full_data_golden.csv',
                                output_path='data/golden_full_converted.csv'):
    """
    Map ALL columns from golden dataset to SCIPHR format
    """
    print("="*70)
    print("CONVERTING FULL GOLDEN DATASET (ALL COLUMNS)")
    print("="*70)
    
    # Load dataset
    print("\n📂 Loading golden dataset...")
    df = pd.read_csv(input_path)
    print(f"   Loaded {len(df):,} fights with {len(df.columns):,} columns")
    
    # Create converted dataframe
    converted = pd.DataFrame()
    
    # BASIC FIGHT INFO (keep as-is)
    converted['date'] = pd.to_datetime(df['event_date'])
    converted['event'] = df['event_name']
    converted['winner'] = df['winner']
    converted['winner_encoded'] = df['winner_encoded'] if 'winner_encoded' in df.columns else 0
    
    # Map ALL f_1_* columns to r_* (red corner)
    print("\n🔴 Mapping Fighter 1 (Red Corner) columns...")
    f1_cols = [col for col in df.columns if col.startswith('f_1_')]
    for col in f1_cols:
        new_name = col.replace('f_1_', 'r_')
        converted[new_name] = df[col]
    print(f"   Mapped {len(f1_cols)} columns")
    
    # Map ALL f_2_* columns to b_* (blue corner)
    print("🔵 Mapping Fighter 2 (Blue Corner) columns...")
    f2_cols = [col for col in df.columns if col.startswith('f_2_')]
    for col in f2_cols:
        new_name = col.replace('f_2_', 'b_')
        converted[new_name] = df[col]
    print(f"   Mapped {len(f2_cols)} columns")
    
    # Map rolling average columns
    print("📊 Mapping rolling average columns...")
    rolling_patterns = ['_3_f_1', '_4_f_1', '_5_f_1', '_6_f_1', '_7_f_1', '_8_f_1',
                       '_9_f_1', '_10_f_1', '_11_f_1', '_12_f_1', '_13_f_1', '_14_f_1', '_15_f_1']
    for pattern in rolling_patterns:
        cols = [c for c in df.columns if pattern in c]
        for col in cols:
            new_name = col.replace('_f_1', '_r').replace('_f_2', '_b')
            if col not in converted.columns:
                converted[new_name] = df[col]
    
    # Map f_2 rolling averages
    rolling_patterns_f2 = ['_3_f_2', '_4_f_2', '_5_f_2', '_6_f_2', '_7_f_2', '_8_f_2',
                          '_9_f_2', '_10_f_2', '_11_f_2', '_12_f_2', '_13_f_2', '_14_f_2', '_15_f_2']
    for pattern in rolling_patterns_f2:
        cols = [c for c in df.columns if pattern in c]
        for col in cols:
            new_name = col.replace('_f_2', '_b')
            if col not in converted.columns:
                converted[new_name] = df[col]
    
    # Map ALL difference columns (keep as-is, they're fighter-agnostic)
    print("⚖️  Mapping difference columns...")
    diff_cols = [col for col in df.columns if col.startswith('diff_')]
    for col in diff_cols:
        converted[col] = df[col]
    print(f"   Mapped {len(diff_cols)} difference columns")
    
    # Map other important columns
    other_important = ['event_date', 'event_city', 'event_state', 'event_country',
                      'referee', 'num_rounds', 'title_fight', 'weight_class', 'gender',
                      'result', 'result_details', 'finish_round', 'finish_time']
    
    for col in other_important:
        if col in df.columns and col not in converted.columns:
            converted[col] = df[col]
    
    # Fill NaN
    print("\n🔧 Filling NaN values...")
    converted = converted.fillna(0)
    
    # Sort by date
    converted = converted.sort_values('date')
    
    print(f"\n✅ CONVERSION COMPLETE!")
    print(f"   Output rows: {len(converted):,}")
    print(f"   Output columns: {len(converted.columns):,}")
    print(f"   Date range: {converted['date'].min()} to {converted['date'].max()}")
    
    # Save
    print(f"\n💾 Saving to {output_path}...")
    converted.to_csv(output_path, index=False)
    print("   ✓ Saved!")
    
    # Show column breakdown
    print(f"\n📊 COLUMN BREAKDOWN:")
    r_cols = len([c for c in converted.columns if c.startswith('r_')])
    b_cols = len([c for c in converted.columns if c.startswith('b_')])
    diff_cols_count = len([c for c in converted.columns if c.startswith('diff_')])
    other = len(converted.columns) - r_cols - b_cols - diff_cols_count
    
    print(f"   Red corner (r_*): {r_cols}")
    print(f"   Blue corner (b_*): {b_cols}")
    print(f"   Differences (diff_*): {diff_cols_count}")
    print(f"   Other: {other}")
    
    print("\n" + "="*70)
    return converted


if __name__ == "__main__":
    convert_full_golden_dataset()