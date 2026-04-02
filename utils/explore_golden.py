import pandas as pd

df = pd.read_csv('data/UFC_full_data_golden.csv')

print("\n🔍 COLUMN MAPPING ANALYSIS:")
print("="*70)

# Show all fighter 1 columns
f1_cols = [col for col in df.columns if col.startswith('f_1_')]
print(f"\nFIGHTER 1 COLUMNS ({len(f1_cols)}):")
for col in f1_cols[:30]:
    print(f"   {col}")

# Show fighter 2 columns  
f2_cols = [col for col in df.columns if col.startswith('f_2_')]
print(f"\nFIGHTER 2 COLUMNS ({len(f2_cols)}):")
for col in f2_cols[:30]:
    print(f"   {col}")

# Check a specific fighter
print("\n🔍 SAMPLE FIGHTER DATA:")
sample = df[df['f_1_name'] == 'Alex Pereira'].iloc[0] if len(df[df['f_1_name'] == 'Alex Pereira']) > 0 else df.iloc[0]

print(f"\nFighter: {sample['f_1_name']}")
print(f"Record: {sample['f_1_fighter_w']}-{sample['f_1_fighter_l']}-{sample['f_1_fighter_d']}")
print(f"Height: {sample['f_1_fighter_height_cm']}cm")
print(f"Weight: {sample['f_1_fighter_weight_lbs']}lbs")
print(f"Reach: {sample['f_1_fighter_reach_cm']}cm")
print(f"Odds: {sample['f_1_odds']}")

# Check if Pereira vs Ankalaev exists
pereira_fights = df[(df['f_1_name'] == 'Alex Pereira') | (df['f_2_name'] == 'Alex Pereira')]
print(f"\n🔥 ALEX PEREIRA FIGHTS IN DATASET: {len(pereira_fights)}")
if len(pereira_fights) > 0:
    print("\nMost recent:")
    recent = pereira_fights.sort_values('event_date', ascending=False).iloc[0]
    print(f"   {recent['f_1_name']} vs {recent['f_2_name']}")
    print(f"   Date: {recent['event_date']}")
    print(f"   Winner: {recent['winner']}")