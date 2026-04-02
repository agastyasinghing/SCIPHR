import pandas as pd

df = pd.read_csv('data/golden_full_converted.csv')
print(f"Total columns: {len(df.columns)}")
print("\nAll columns:")
for i, col in enumerate(df.columns, 1):
    print(f"{i}. {col}")