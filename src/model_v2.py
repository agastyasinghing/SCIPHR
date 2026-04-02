"""
UFC Model Training V2
Trains ensemble models on 256 advanced features
"""

import pandas as pd
import numpy as np
import pickle
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import xgboost as xgb
import lightgbm as lgb
from datetime import datetime

class UFCModelV2:
    """
    Advanced model training with ensemble approach
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.results = {}
        
    def train_all_models(self, X_train, X_test, y_train, y_test, feature_names):  # CHANGED: Added feature_names parameter
        """
        Train all models and compare performance
        """
        print("\n" + "="*70)
        print("TRAINING MODELS ON 256 FEATURES")
        print("="*70)
        print(f"Training samples: {len(X_train)}")
        print(f"Test samples: {len(X_test)}")
        print(f"Features: {X_train.shape[1]}")
        
        # ============ MODEL 1: XGBOOST ============
        print("\n" + "-"*70)
        print("MODEL 1: XGBoost")
        print("-"*70)
        
        xgb_model = xgb.XGBClassifier(
            n_estimators=500,
            max_depth=8,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='binary:logistic',
            random_state=42,
            eval_metric='logloss'
        )
        
        print("Training XGBoost...")
        xgb_model.fit(X_train, y_train)
        xgb_pred = xgb_model.predict(X_test)
        xgb_acc = accuracy_score(y_test, xgb_pred)
        
        self.models['xgboost'] = xgb_model
        self.results['xgboost'] = xgb_acc
        
        print(f"✓ XGBoost Accuracy: {xgb_acc:.4f} ({xgb_acc*100:.2f}%)")
        
        # ============ MODEL 2: LIGHTGBM ============
        print("\n" + "-"*70)
        print("MODEL 2: LightGBM")
        print("-"*70)
        
        lgb_model = lgb.LGBMClassifier(
            n_estimators=500,
            max_depth=8,
            learning_rate=0.03,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbose=-1
        )
        
        print("Training LightGBM...")
        lgb_model.fit(X_train, y_train)
        lgb_pred = lgb_model.predict(X_test)
        lgb_acc = accuracy_score(y_test, lgb_pred)
        
        self.models['lightgbm'] = lgb_model
        self.results['lightgbm'] = lgb_acc
        
        print(f"✓ LightGBM Accuracy: {lgb_acc:.4f} ({lgb_acc*100:.2f}%)")
        
        # ============ MODEL 3: RANDOM FOREST ============
        print("\n" + "-"*70)
        print("MODEL 3: Random Forest")
        print("-"*70)
        
        rf_model = RandomForestClassifier(
            n_estimators=300,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=4,
            random_state=42,
            n_jobs=-1
        )
        
        print("Training Random Forest...")
        rf_model.fit(X_train, y_train)
        rf_pred = rf_model.predict(X_test)
        rf_acc = accuracy_score(y_test, rf_pred)
        
        self.models['random_forest'] = rf_model
        self.results['random_forest'] = rf_acc
        
        print(f"✓ Random Forest Accuracy: {rf_acc:.4f} ({rf_acc*100:.2f}%)")
        
        # ============ MODEL 4: NEURAL NETWORK ============
        print("\n" + "-"*70)
        print("MODEL 4: Neural Network")
        print("-"*70)
        
        # Scale features for neural network
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        nn_model = MLPClassifier(
            hidden_layer_sizes=(256, 128, 64, 32),
            activation='relu',
            solver='adam',
            alpha=0.001,
            batch_size=32,
            learning_rate='adaptive',
            learning_rate_init=0.001,
            max_iter=200,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1
        )
        
        print("Training Neural Network...")
        nn_model.fit(X_train_scaled, y_train)
        nn_pred = nn_model.predict(X_test_scaled)
        nn_acc = accuracy_score(y_test, nn_pred)
        
        self.models['neural_network'] = nn_model
        self.scalers['neural_network'] = scaler
        self.results['neural_network'] = nn_acc
        
        print(f"✓ Neural Network Accuracy: {nn_acc:.4f} ({nn_acc*100:.2f}%)")
        
        # ============ MODEL 5: LOGISTIC REGRESSION ============
        print("\n" + "-"*70)
        print("MODEL 5: Logistic Regression")
        print("-"*70)
        
        # Scale for logistic regression
        lr_scaler = StandardScaler()
        X_train_scaled_lr = lr_scaler.fit_transform(X_train)
        X_test_scaled_lr = lr_scaler.transform(X_test)
        
        lr_model = LogisticRegression(
            C=0.1,
            max_iter=1000,
            random_state=42,
            n_jobs=-1
        )
        
        print("Training Logistic Regression...")
        lr_model.fit(X_train_scaled_lr, y_train)
        lr_pred = lr_model.predict(X_test_scaled_lr)
        lr_acc = accuracy_score(y_test, lr_pred)
        
        self.models['logistic_regression'] = lr_model
        self.scalers['logistic_regression'] = lr_scaler
        self.results['logistic_regression'] = lr_acc
        
        print(f"✓ Logistic Regression Accuracy: {lr_acc:.4f} ({lr_acc*100:.2f}%)")
        
        # ============ FINAL RESULTS ============
        self.print_final_results()
        
        # Save best model WITH FEATURE NAMES
        self.save_best_model(feature_names)  # CHANGED: Pass feature_names
        
    def print_final_results(self):
        """Print final comparison of all models"""
        print("\n" + "="*70)
        print("FINAL RESULTS SUMMARY")
        print("="*70)
        
        # Sort by accuracy
        sorted_results = sorted(self.results.items(), key=lambda x: x[1], reverse=True)
        
        for i, (model_name, accuracy) in enumerate(sorted_results, 1):
            best_marker = " *** BEST ***" if i == 1 else ""
            print(f"{model_name:25s}: {accuracy:.4f} ({accuracy*100:.2f}%){best_marker}")
        
        best_model = sorted_results[0][0]
        best_acc = sorted_results[0][1]
        
        print(f"\nBest Model: {best_model}")
        print(f"Best Accuracy: {best_acc:.4f} ({best_acc*100:.2f}%)")
        print("="*70)
        
    def save_best_model(self, feature_names):  # CHANGED: Added feature_names parameter
        """Save the best performing model"""
        # Find best model
        best_model_name = max(self.results.items(), key=lambda x: x[1])[0]
        best_model = self.models[best_model_name]
        best_accuracy = self.results[best_model_name]
        
        # Package model data - NOW INCLUDES FEATURE NAMES
        model_data = {
            'model': best_model,
            'model_name': best_model_name,
            'scaler': self.scalers.get(best_model_name, None),
            'accuracy': best_accuracy,
            'feature_count': len(feature_names),  # CHANGED: Use actual count
            'feature_names': feature_names,  # NEW: Save feature names
            'trained_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'version': 'v2'
        }
        
        # Save to file
        output_path = 'models/best_ufc_model_v2.pkl'
        with open(output_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"\nSaving best model ({best_model_name}) to {output_path}...")
        print("✓ Model saved successfully")
        print(f"✓ Saved {len(feature_names)} feature names")  # NEW: Confirm saved
        
        # Print feature importance for tree-based models
        if best_model_name in ['xgboost', 'lightgbm', 'random_forest']:
            self.print_feature_importance(best_model, best_model_name)
    
    def print_feature_importance(self, model, model_name, top_n=15):
        """Print top N most important features"""
        print(f"\nFeature Importance ({model_name}):")
        print("-"*50)
        
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            indices = np.argsort(importances)[::-1][:top_n]
            
            for i, idx in enumerate(indices, 1):
                print(f"{i:2d}. Feature {idx:3d}: {importances[idx]:.4f}")
        
        print("="*70)


def main():
    """Main training pipeline"""
    print("\n" + "="*70)
    print("UFC MODEL TRAINING V2")
    print("Advanced Feature Set (256 features)")
    print("="*70)
    
    # Load processed data
    print("\nLoading processed data...")
    from kaggle_processor_v2 import KaggleUFCProcessorV2
    
    processor = KaggleUFCProcessorV2('data/large_dataset.csv')
    X_train, X_test, y_train, y_test, features = processor.process_all()
    
    print(f"\n✓ Data loaded")
    print(f"✓ Training samples: {len(X_train)}")
    print(f"✓ Features: {len(features)}")
    
    # Train models - NOW PASSING FEATURE NAMES
    trainer = UFCModelV2()
    trainer.train_all_models(X_train, X_test, y_train, y_test, features)  # CHANGED: Pass features
    
    print("\n" + "="*70)
    print("MODEL TRAINING COMPLETE!")
    print("="*70)


if __name__ == "__main__":
    main()