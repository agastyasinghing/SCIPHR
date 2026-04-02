import pickle
import numpy as np
from src.predictor_golden import UFCFightPredictorGolden

# Load model
with open('models/golden_model.pkl', 'rb') as f:
    model_data = pickle.load(f)

model = model_data['model']
feature_names = model_data['feature_names']
feature_importance = model.feature_importances_

predictor = UFCFightPredictorGolden()

def analyze_fight(fighter1, fighter2, fight_label):
    print('='*70)
    print(f'{fight_label}')
    print('='*70)
    
    result = predictor.predict_fight(fighter1, fighter2, verbose=False)
    
    if not result:
        print("Could not predict fight")
        return
    
    print(f'\nPREDICTION: {result["winner"]} wins ({result["confidence"]:.1%})')
    print(f'Breakdown: {fighter1} {result["prob_fighter1"]:.1%} | {fighter2} {result["prob_fighter2"]:.1%}')
    
    features = predictor.feature_calculator.build_full_feature_vector(
        fighter1, fighter2, feature_names
    )
    
    if not features:
        print("Could not build features")
        return
    
    print('\n📊 TOP 10 MOST INFLUENTIAL FEATURES:')
    print('-'*70)
    
    feature_contributions = []
    for name, val, imp in zip(feature_names, features, feature_importance):
        if val != 0:
            contribution = abs(val * imp)
            feature_contributions.append((name, val, imp, contribution))
    
    feature_contributions.sort(key=lambda x: x[3], reverse=True)
    
    for i, (name, value, importance, _) in enumerate(feature_contributions[:10], 1):
        direction = 'RED' if value > 0 else 'BLUE'
        print(f'{i:2d}. {name:40s}')
        print(f'    Value: {value:8.2f} | Importance: {importance:.4f} | -> {direction}')
    
    print('\n')

# Analyze fights
analyze_fight('Belal Muhammad', 'Ian Machado Garry', 'FIGHT 1: Belal Muhammad (RED) vs Ian Machado Garry (BLUE)')

analyze_fight('Arman Tsarukyan', 'Dan Hooker', 'FIGHT 2: Arman Tsarukyan (RED) vs Dan Hooker (BLUE)')
