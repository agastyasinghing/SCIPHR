"""
Convert UFC Golden Dataset to SCIPHR format
Maps f_1_/f_2_ columns to r_/b_ (red/blue corner)
"""

import pandas as pd
import numpy as np
from datetime import datetime

def convert_golden_to_sciphr_format(input_path='data/UFC_full_data_golden.csv', 
                                     output_path='data/golden_converted.csv'):
    """
    Convert golden dataset to match SCIPHR's expected format
    """
    print("="*70)
    print("CONVERTING GOLDEN DATASET TO SCIPHR FORMAT")
    print("="*70)
    
    # Load golden dataset
    print("\n📂 Loading golden dataset...")
    df = pd.read_csv(input_path)
    print(f"   Loaded {len(df):,} fights")
    
    # Create new dataframe with mapped columns
    print("\n🔄 Mapping columns...")
    
    converted = pd.DataFrame()
    
    # Basic fight info
    converted['date'] = pd.to_datetime(df['event_date'])
    converted['event'] = df['event_name']
    converted['r_fighter'] = df['f_1_name']
    converted['b_fighter'] = df['f_2_name']
    
    # Winner (convert to red/blue format)
    converted['winner'] = df['winner']
    
    # Red corner (f_1) stats
    converted['r_height'] = df['f_1_fighter_height_cm']
    converted['r_weight'] = df['f_1_fighter_weight_lbs']
    converted['r_reach'] = df['f_1_fighter_reach_cm']
    converted['r_stance'] = df['f_1_fighter_stance']
    converted['r_dob'] = df['f_1_fighter_dob']
    
    # Calculate age at fight time
    r_dob = pd.to_datetime(df['f_1_fighter_dob'], errors='coerce')
    converted['r_age'] = (converted['date'] - r_dob).dt.days / 365.25
    
    # Record
    converted['r_wins_total'] = df['f_1_fighter_w']
    converted['r_losses_total'] = df['f_1_fighter_l']
    converted['r_draw'] = df['f_1_fighter_d']
    
    # Striking stats
    converted['r_SLpM_total'] = df['f_1_fighter_SlpM']
    converted['r_sig_str_acc_total'] = df['f_1_fighter_Str_Acc']
    converted['r_SApM_total'] = df['f_1_fighter_SApM']
    converted['r_sig_str_def_total'] = df['f_1_fighter_Str_Def']
    
    # Takedown stats
    converted['r_td_avg_total'] = df['f_1_fighter_TD_Avg']
    converted['r_td_acc_total'] = df['f_1_fighter_TD_Acc']
    converted['r_td_def_total'] = df['f_1_fighter_TD_Def']
    converted['r_sub_avg_total'] = df['f_1_fighter_Sub_Avg']
    
    # Blue corner (f_2) stats - same mappings
    converted['b_height'] = df['f_2_fighter_height_cm']
    converted['b_weight'] = df['f_2_fighter_weight_lbs']
    converted['b_reach'] = df['f_2_fighter_reach_cm']
    converted['b_stance'] = df['f_2_fighter_stance']
    converted['b_dob'] = df['f_2_fighter_dob']
    
    b_dob = pd.to_datetime(df['f_2_fighter_dob'], errors='coerce')
    converted['b_age'] = (converted['date'] - b_dob).dt.days / 365.25
    
    converted['b_wins_total'] = df['f_2_fighter_w']
    converted['b_losses_total'] = df['f_2_fighter_l']
    converted['b_draw'] = df['f_2_fighter_d']
    
    converted['b_SLpM_total'] = df['f_2_fighter_SlpM']
    converted['b_sig_str_acc_total'] = df['f_2_fighter_Str_Acc']
    converted['b_SApM_total'] = df['f_2_fighter_SApM']
    converted['b_sig_str_def_total'] = df['f_2_fighter_Str_Def']
    
    converted['b_td_avg_total'] = df['f_2_fighter_TD_Avg']
    converted['b_td_acc_total'] = df['f_2_fighter_TD_Acc']
    converted['b_td_def_total'] = df['f_2_fighter_TD_Def']
    converted['b_sub_avg_total'] = df['f_2_fighter_Sub_Avg']
    
    # BONUS: Add betting odds (for monetization later!)
    if 'f_1_odds' in df.columns:
        converted['r_odds'] = df['f_1_odds']
        converted['b_odds'] = df['f_2_odds']
    
    # Add more detailed stats if available
    if 'f_1_knockdowns' in df.columns:
        converted['r_total_knockdowns'] = df['f_1_knockdowns']
        converted['b_total_knockdowns'] = df['f_2_knockdowns']
    
    if 'f_1_total_strikes_succ' in df.columns:
        converted['r_total_strikes_landed'] = df['f_1_total_strikes_succ']
        converted['b_total_strikes_landed'] = df['f_2_total_strikes_succ']
        converted['r_total_strikes_att'] = df['f_1_total_strikes_att']
        converted['b_total_strikes_att'] = df['f_2_total_strikes_att']
    
    if 'f_1_sig_strikes_succ' in df.columns:
        converted['r_sig_strikes_landed'] = df['f_1_sig_strikes_succ']
        converted['b_sig_strikes_landed'] = df['f_2_sig_strikes_succ']
        converted['r_sig_strikes_att'] = df['f_1_sig_strikes_att']
        converted['b_sig_strikes_att'] = df['f_2_sig_strikes_att']
    
    if 'f_1_takedown_succ' in df.columns:
        converted['r_takedowns_landed'] = df['f_1_takedown_succ']
        converted['b_takedowns_landed'] = df['f_2_takedown_succ']
        converted['r_takedowns_att'] = df['f_1_takedown_att']
        converted['b_takedowns_att'] = df['f_2_takedown_att']
    
    # Fill NaN values
    converted = converted.fillna(0)
    
    # Sort by date
    converted = converted.sort_values('date')
    
    print(f"\n✅ Conversion complete!")
    print(f"   Rows: {len(converted):,}")
    print(f"   Columns: {len(converted.columns)}")
    print(f"   Date range: {converted['date'].min()} to {converted['date'].max()}")
    
    # Save
    print(f"\n💾 Saving to {output_path}...")
    converted.to_csv(output_path, index=False)
    print("   ✓ Saved!")
    
    # Show sample
    print(f"\n🔍 Sample fighters:")
    sample_fighters = converted['r_fighter'].value_counts().head(5)
    for fighter, count in sample_fighters.items():
        print(f"   {fighter}: {count} fights")
    
    print("\n" + "="*70)
    return converted


if __name__ == "__main__":
    convert_golden_to_sciphr_format()