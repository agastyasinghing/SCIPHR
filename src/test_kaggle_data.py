import pandas as pd
df = pd.read_csv('data/large_dataset.csv')
print(f"Total fights: {len(df)}")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nFirst few rows:")
print(df.head())