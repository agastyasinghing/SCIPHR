"""
Generate synthetic training data for impossible matchups
Teaches model that extreme size differences = certain outcomes
"""

import pandas as pd
import numpy as np

def generate_impossible_matchups(n_samples=2000):
    """
    Generate synthetic fights where extreme weight mismatches exist
    These teach the model: size ALWAYS wins in absurd scenarios
    """
    
    synthetic_fights = []
    
    # Scenario 1: Heavyweight vs Flyweight (500 examples)
    for i in range(500):
        # Even if flyweight is undefeated, heavyweight wins
        synthetic_fights.append({
            'r_weight': np.random.uniform(240, 265),
            'b_weight': np.random.uniform(115, 135),
            'r_height': np.random.uniform(74, 78),
            'b_height': np.random.uniform(62, 66),
            'r_reach': np.random.uniform(78, 84),
            'b_reach': np.random.uniform(64, 68),
            'r_age': np.random.uniform(25, 35),
            'b_age': np.random.uniform(25, 35),
            'r_wins_total': np.random.randint(10, 25),
            'b_wins_total': np.random.randint(15, 30),  # Flyweight can be better record
            'r_losses_total': np.random.randint(2, 8),
            'b_losses_total': np.random.randint(0, 3),  # Flyweight can be undefeated
            'winner_encoded': 1  # Red (heavy) ALWAYS wins
        })
    
    # Scenario 2: Light Heavyweight vs Bantamweight (500 examples)
    for i in range(500):
        synthetic_fights.append({
            'r_weight': np.random.uniform(195, 205),
            'b_weight': np.random.uniform(130, 140),
            'r_height': np.random.uniform(72, 76),
            'b_height': np.random.uniform(65, 68),
            'r_reach': np.random.uniform(76, 80),
            'b_reach': np.random.uniform(67, 71),
            'r_age': np.random.uniform(25, 35),
            'b_age': np.random.uniform(25, 35),
            'r_wins_total': np.random.randint(8, 20),
            'b_wins_total': np.random.randint(12, 25),
            'r_losses_total': np.random.randint(1, 6),
            'b_losses_total': np.random.randint(0, 2),
            'winner_encoded': 1
        })
    
    # Scenario 3: Middleweight vs Flyweight (500 examples)
    for i in range(500):
        synthetic_fights.append({
            'r_weight': np.random.uniform(175, 190),
            'b_weight': np.random.uniform(115, 130),
            'r_height': np.random.uniform(71, 75),
            'b_height': np.random.uniform(62, 66),
            'r_reach': np.random.uniform(74, 78),
            'b_reach': np.random.uniform(64, 68),
            'r_age': np.random.uniform(25, 35),
            'b_age': np.random.uniform(25, 35),
            'r_wins_total': np.random.randint(10, 20),
            'b_wins_total': np.random.randint(15, 28),
            'r_losses_total': np.random.randint(2, 7),
            'b_losses_total': np.random.randint(0, 3),
            'winner_encoded': 1
        })
    
    # Scenario 4: Reverse scenarios - small fighter in red corner still loses
    for i in range(500):
        # Flyweight vs Heavyweight (reversed)
        synthetic_fights.append({
            'r_weight': np.random.uniform(115, 135),
            'b_weight': np.random.uniform(240, 265),
            'r_height': np.random.uniform(62, 66),
            'b_height': np.random.uniform(74, 78),
            'r_reach': np.random.uniform(64, 68),
            'b_reach': np.random.uniform(78, 84),
            'r_age': np.random.uniform(25, 35),
            'b_age': np.random.uniform(25, 35),
            'r_wins_total': np.random.randint(15, 30),
            'b_wins_total': np.random.randint(10, 25),
            'r_losses_total': np.random.randint(0, 3),
            'b_losses_total': np.random.randint(2, 8),
            'winner_encoded': 0  # Blue (heavy) wins
        })
    
    df = pd.DataFrame(synthetic_fights)

    # Add winner column (required by clean_data method)
    df['winner'] = df['winner_encoded'].apply(lambda x: 'Red' if x == 1 else 'Blue')
    
    # Add basic features needed for feature engineering
    df['r_fighter'] = 'SYNTHETIC_RED'
    df['b_fighter'] = 'SYNTHETIC_BLUE'
    
    # Calculate total fights from wins + losses
    df['r_total_fights'] = df['r_wins_total'] + df['r_losses_total']
    df['b_total_fights'] = df['b_wins_total'] + df['b_losses_total']
    
    # Add finish rates (random but reasonable)
    df['r_ko_wins'] = (df['r_wins_total'] * np.random.uniform(0.3, 0.5, len(df))).astype(int)
    df['r_sub_wins'] = (df['r_wins_total'] * np.random.uniform(0.2, 0.4, len(df))).astype(int)
    df['b_ko_wins'] = (df['b_wins_total'] * np.random.uniform(0.3, 0.5, len(df))).astype(int)
    df['b_sub_wins'] = (df['b_wins_total'] * np.random.uniform(0.2, 0.4, len(df))).astype(int)
    
    # Calculate decision wins (remaining wins)
    df['r_dec_wins'] = df['r_wins_total'] - df['r_ko_wins'] - df['r_sub_wins']
    df['b_dec_wins'] = df['b_wins_total'] - df['b_ko_wins'] - df['b_sub_wins']
    
    # Make sure decision wins aren't negative
    df['r_dec_wins'] = df['r_dec_wins'].clip(lower=0)
    df['b_dec_wins'] = df['b_dec_wins'].clip(lower=0)
    
    # Add loss types (distribute losses randomly)
    df['r_ko_losses'] = (df['r_losses_total'] * np.random.uniform(0.3, 0.5, len(df))).astype(int)
    df['r_sub_losses'] = (df['r_losses_total'] * np.random.uniform(0.2, 0.4, len(df))).astype(int)
    df['r_dec_losses'] = df['r_losses_total'] - df['r_ko_losses'] - df['r_sub_losses']
    df['r_dec_losses'] = df['r_dec_losses'].clip(lower=0)
    
    df['b_ko_losses'] = (df['b_losses_total'] * np.random.uniform(0.3, 0.5, len(df))).astype(int)
    df['b_sub_losses'] = (df['b_losses_total'] * np.random.uniform(0.2, 0.4, len(df))).astype(int)
    df['b_dec_losses'] = df['b_losses_total'] - df['b_ko_losses'] - df['b_sub_losses']
    df['b_dec_losses'] = df['b_dec_losses'].clip(lower=0)
    
    # Add draws (set to 0 for synthetic data)
    df['r_draw'] = 0
    df['b_draw'] = 0
    
    # Add stance
    df['r_stance'] = 'Orthodox'
    df['b_stance'] = 'Orthodox'
    
    # Add any other columns that might be needed (set to 0 or reasonable defaults)
    # These are columns that might exist in real data but not critical for our features
    for col in ['r_sig_str_pct', 'b_sig_str_pct', 'r_td_pct', 'b_td_pct', 
                'r_sub_att_pct', 'b_sub_att_pct']:
        if col not in df.columns:
            df[col] = 0.5  # Reasonable default percentage
    
    print(f"✓ Generated {len(df)} synthetic impossible matchup examples")
    return df


if __name__ == "__main__":
    # Test the generator
    df = generate_impossible_matchups()
    print("\n" + "="*70)
    print("SYNTHETIC DATA TEST")
    print("="*70)
    print(f"\nGenerated {len(df)} fights")
    print(f"\nFirst few examples:")
    print(df.head())
    print(f"\nWeight ranges:")
    print(f"  Red: {df['r_weight'].min():.0f} - {df['r_weight'].max():.0f} lbs")
    print(f"  Blue: {df['b_weight'].min():.0f} - {df['b_weight'].max():.0f} lbs")
    print(f"\nWin distribution:")
    print(f"  Red wins: {(df['winner_encoded'] == 1).sum()}")
    print(f"  Blue wins: {(df['winner_encoded'] == 0).sum()}")