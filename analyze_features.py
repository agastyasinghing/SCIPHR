import pandas as pd

df = pd.read_csv('data/golden_full_converted.csv')

# Group features by category
categories = {}
for col in df.columns:
    # Extract category from column name
    if '_' in col:
        category = col.split('_')[0] + '_' + col.split('_')[1] if len(col.split('_')) > 1 else col.split('_')[0]
    else:
        category = 'other'
    
    if category not in categories:
        categories[category] = []
    categories[category].append(col)

# Print summary
print(f"Total Features: {len(df.columns)}\n")
print("Feature Categories:\n")
for cat, cols in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)[:30]:
    print(f"{cat}: {len(cols)} features")
    print(f"  Examples: {', '.join(cols[:3])}")
    print()