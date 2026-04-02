"""
Train UFC prediction model using FULL golden dataset
All 5,000+ features including rolling averages, streaks, and differences
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import xgboost as xgb
import pickle
from datetime import datetime

def train_golden_model():
    print("="*70)
    print("TRAINING MODEL ON GOLDEN DATASET")
    print("="*70)
    
    # Load converted golden dataset
    print("\n📂 Loading golden dataset...")
    df = pd.read_csv('data/golden_full_converted.csv')
    print(f"   Loaded {len(df):,} fights")
    print(f"   Features: {len(df.columns):,} columns")
    
    # Check date range
    df['date'] = pd.to_datetime(df['date'])
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    
    # SPLIT: Train on everything BEFORE Oct 2025, test on UFC 320+
    test_cutoff = '2025-10-01'
    train_df = df[df['date'] < test_cutoff].copy()
    test_df = df[df['date'] >= test_cutoff].copy()
    
    print(f"\n📊 TRAIN/TEST SPLIT:")
    print(f"   Training fights: {len(train_df):,} (before {test_cutoff})")
    print(f"   Test fights: {len(test_df):,} (UFC 320+)")
    
    # Prepare features
    print("\n🔧 Preparing features...")
    
    # Remove non-feature columns
    exclude_cols = ['date', 'event', 'winner', 'event_date', 'event_city', 
                   'event_state', 'event_country', 'referee', 'result', 
                   'result_details', 'finish_round', 'finish_time',
                   'r_name', 'b_name', 'r_fighter_f_name', 'b_fighter_f_name',
                   'r_fighter_l_name', 'b_fighter_l_name', 'r_url', 'b_url',
                   'r_fighter_url', 'b_fighter_url', 'r_fighter_dob', 'b_fighter_dob']
    
    feature_cols = [col for col in train_df.columns 
                   if col not in exclude_cols 
                   and col != 'winner_encoded']
    
    print(f"   Using {len(feature_cols):,} features")
    
    # Prepare X and y
    X_train = train_df[feature_cols].fillna(0)

    # FIX: Convert object (string) columns to numeric
    print(f"\n🔧 Converting string columns to numeric...")
    object_cols = X_train.select_dtypes(include=['object']).columns
    print(f"   Found {len(object_cols)} string columns: {list(object_cols)}")

    for col in object_cols:
        # Convert categorical strings to numeric codes
        X_train[col] = pd.Categorical(X_train[col]).codes
    
    print(f"   ✓ Converted to numeric codes")
    y_train_raw = train_df['winner_encoded'].fillna(0).astype(int)
    
    # FIX: Remap winner encoding from [-1, 0, 1] to [0, 1, 2]
    # -1 = draw/no contest → 0
    # 0 = fighter 2 wins → 1  
    # 1 = fighter 1 wins → 2
    print(f"\n🔧 Fixing winner encoding...")
    print(f"   Original values: {sorted(y_train_raw.unique())}")
    y_train = y_train_raw + 1  # Shift everything up by 1
    print(f"   Remapped values: {sorted(y_train.unique())}")
    
    X_test = test_df[feature_cols].fillna(0)
    # Convert same columns in test set
    for col in object_cols:
        X_test[col] = pd.Categorical(X_test[col]).codes
    y_test_raw = test_df['winner_encoded'].fillna(0).astype(int)
    y_test = y_test_raw + 1  # Same shift for test data
    
    print(f"   Training samples: {len(X_train):,}")
    print(f"   Test samples: {len(X_test):,}")
    
    # Handle infinite values
    X_train = X_train.replace([np.inf, -np.inf], 0)
    X_test = X_test.replace([np.inf, -np.inf], 0)
    
    # Train XGBoost model
    print("\n🤖 Training XGBoost model...")
    print("   This may take a few minutes with 5,000+ features...")
    
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    print("   ✓ Training complete!")
    
    # Evaluate
    print("\n📈 EVALUATION:")
    
    # Training accuracy
    train_pred = model.predict(X_train)
    train_acc = accuracy_score(y_train, train_pred)
    print(f"   Training accuracy: {train_acc:.2%}")
    
    # Test accuracy (UFC 320+)
    if len(X_test) > 0:
        test_pred = model.predict(X_test)
        test_acc = accuracy_score(y_test, test_pred)
        print(f"   Test accuracy (UFC 320+): {test_acc:.2%}")
        
        # Show predictions on UFC 320
        print(f"\n🥊 UFC 320+ PREDICTIONS:")
        test_df_copy = test_df.copy()
        test_df_copy['predicted_winner'] = test_pred
        
        for idx, fight in test_df_copy.iterrows():
            actual = fight['winner']
            
            # predicted is now: 0=draw, 1=fighter2, 2=fighter1
            if fight['predicted_winner'] == 2:
                predicted = "Fighter 1"
            elif fight['predicted_winner'] == 1:
                predicted = "Fighter 2"
            else:
                predicted = "Draw/NC"
            
            # Also need to remap the actual winner encoding for comparison
            actual_encoded = fight['winner_encoded'] + 1
            correct = "✓" if fight['predicted_winner'] == actual_encoded else "✗"
            
            fighter1 = fight.get('r_name', 'Fighter 1')
            fighter2 = fight.get('b_name', 'Fighter 2')
            
            print(f"   {correct} {fighter1} vs {fighter2}")
            print(f"      Predicted: {predicted}, Actual: {actual}")
    
    # Feature importance
    print("\n🔝 TOP 20 MOST IMPORTANT FEATURES:")
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for idx, row in feature_importance.head(20).iterrows():
        print(f"   {row['feature']}: {row['importance']:.4f}")
    
    # Save model
    print("\n💾 Saving model...")
    model_data = {
        'model': model,
        'model_name': 'xgboost_golden',
        'accuracy': train_acc,
        'test_accuracy': test_acc if len(X_test) > 0 else None,
        'feature_count': len(feature_cols),
        'feature_names': feature_cols,
        'trained_date': datetime.now().strftime('%Y-%m-%d'),
        'training_fights': len(train_df),
        'scaler': None
    }
    
    with open('models/golden_model.pkl', 'wb') as f:
        pickle.dump(model_data, f)
    
    print("   ✓ Saved to models/golden_model.pkl")
    
    print("\n" + "="*70)
    print("✅ TRAINING COMPLETE!")
    print("="*70)
    
    return model, feature_cols


if __name__ == "__main__":
    train_golden_model()