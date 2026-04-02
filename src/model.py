"""
UFC Fight Outcome Prediction Model
Trains and evaluates multiple ML algorithms
"""

import pandas as pd
import numpy as np
import pickle
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns

class UFCPredictionModel:
    """
    Trains and evaluates UFC fight prediction models
    """
    
    def __init__(self):
        """
        Initialize the model trainer
        """
        self.models = {}
        self.scaler = StandardScaler()
        self.best_model = None
        self.best_model_name = None
        self.best_accuracy = 0
        
    def scale_features(self, X_train, X_test):
        """
        Scale features to similar ranges
        
        Why: Some features are 0-1 (percentages), others are 0-100 (age, weight)
        Scaling puts everything on the same scale so no feature dominates
        
        Example:
        - Before: height=180, accuracy=0.45
        - After: height=0.8, accuracy=0.6 (both scaled to similar range)
        """
        print("\nScaling features...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return X_train_scaled, X_test_scaled
    
    def train_logistic_regression(self, X_train, y_train):
        """
        Train Logistic Regression model
        
        What it is: Draws a line (or hyperplane) to separate winners from losers
        
        Pros: Fast, simple, interpretable
        Cons: Can't capture complex patterns
        
        Best for: Quick baseline to beat
        """
        print("\n" + "="*50)
        print("Training Logistic Regression...")
        print("="*50)
        
        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(X_train, y_train)
        
        self.models['Logistic Regression'] = model
        print("Training complete")
        
        return model
    
    def train_random_forest(self, X_train, y_train):
        """
        Train Random Forest model
        
        What it is: Creates 100 decision trees, each votes on the outcome
        
        How it works:
        - Tree 1: "If wins_diff > 5 and height_diff > 3, predict Red"
        - Tree 2: "If strike_diff > 2 and age_diff < 5, predict Red"
        - ... (98 more trees)
        - Final prediction: Majority vote
        
        Pros: Handles complex patterns, resistant to overfitting
        Cons: Slower than logistic regression
        
        Best for: Good all-around performer
        """
        print("\n" + "="*50)
        print("Training Random Forest...")
        print("="*50)
        
        model = RandomForestClassifier(
            n_estimators=100,  # Number of trees
            max_depth=20,  # How deep each tree can go
            min_samples_split=10,  # Minimum samples to split a node
            random_state=42
        )
        model.fit(X_train, y_train)
        
        self.models['Random Forest'] = model
        print("Training complete")
        
        return model
    
    def train_xgboost(self, X_train, y_train):
        """
        Train XGBoost model
        
        What it is: Gradient boosting - builds trees sequentially, each fixing
        the mistakes of the previous one
        
        How it works:
        - Tree 1: Makes predictions, some are wrong
        - Tree 2: Focuses on fixing Tree 1's mistakes
        - Tree 3: Fixes remaining mistakes from Tree 1 & 2
        - ... keeps improving
        
        Pros: Usually the most accurate for structured data
        Cons: Can overfit if not tuned properly
        
        Best for: Competitions and production systems (Kaggle winners use this)
        """
        print("\n" + "="*50)
        print("Training XGBoost...")
        print("="*50)
        
        model = xgb.XGBClassifier(
            n_estimators=100,  # Number of boosting rounds
            max_depth=6,  # Tree depth
            learning_rate=0.1,  # How much each tree contributes
            random_state=42,
            eval_metric='logloss'
        )
        model.fit(X_train, y_train)
        
        self.models['XGBoost'] = model
        print("Training complete")
        
        return model
    
    def train_neural_network(self, X_train, y_train):
        """
        Train Neural Network model
        
        What it is: Mimics how brain neurons work - layers of interconnected nodes
        
        Architecture:
        - Input layer: 42 features
        - Hidden layer 1: 64 neurons (learns basic patterns)
        - Hidden layer 2: 32 neurons (learns complex combinations)
        - Output layer: 1 neuron (probability of Red winning)
        
        Pros: Can learn very complex patterns
        Cons: Needs more data, slower, less interpretable
        
        Best for: When you have tons of data and complex patterns
        """
        print("\n" + "="*50)
        print("Training Neural Network...")
        print("="*50)
        
        model = MLPClassifier(
            hidden_layer_sizes=(64, 32),  # Two hidden layers
            activation='relu',  # Activation function
            max_iter=500,  # Training iterations
            random_state=42,
            early_stopping=True,  # Stop if not improving
            validation_fraction=0.1
        )
        model.fit(X_train, y_train)
        
        self.models['Neural Network'] = model
        print("Training complete")
        
        return model
    
    def evaluate_model(self, model, model_name, X_test, y_test):
        """
        Evaluate a model's performance
        
        Metrics:
        - Accuracy: % of correct predictions
        - Precision: Of predicted Red wins, how many were actually Red wins?
        - Recall: Of actual Red wins, how many did we predict?
        - F1-Score: Balance between precision and recall
        """
        print(f"\nEvaluating {model_name}...")
        
        # Make predictions
        y_pred = model.predict(X_test)
        
        # Calculate accuracy
        accuracy = accuracy_score(y_test, y_pred)
        print(f"Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
        
        # Detailed classification report
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, 
                                   target_names=['Blue Wins', 'Red Wins']))
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        print("\nConfusion Matrix:")
        print(cm)
        print(f"  True Blue Wins: {cm[0][0]}")
        print(f"  False Red Wins: {cm[0][1]} (predicted Red, was Blue)")
        print(f"  False Blue Wins: {cm[1][0]} (predicted Blue, was Red)")
        print(f"  True Red Wins: {cm[1][1]}")
        
        # Track best model
        if accuracy > self.best_accuracy:
            self.best_accuracy = accuracy
            self.best_model = model
            self.best_model_name = model_name
            print(f"\n*** NEW BEST MODEL: {model_name} ***")
        
        return accuracy, y_pred
    
    def train_all_models(self, X_train, X_test, y_train, y_test):
        """
        Train and evaluate all models
        """
        print("\n" + "="*70)
        print("TRAINING ALL MODELS")
        print("="*70)
        
        # Scale features (required for Logistic Regression and Neural Network)
        X_train_scaled, X_test_scaled = self.scale_features(X_train, X_test)
        
        results = {}
        
        # Train Logistic Regression (uses scaled data)
        lr_model = self.train_logistic_regression(X_train_scaled, y_train)
        lr_acc, _ = self.evaluate_model(lr_model, 'Logistic Regression', 
                                        X_test_scaled, y_test)
        results['Logistic Regression'] = lr_acc
        
        # Train Random Forest (uses original data)
        rf_model = self.train_random_forest(X_train, y_train)
        rf_acc, _ = self.evaluate_model(rf_model, 'Random Forest', 
                                        X_test, y_test)
        results['Random Forest'] = rf_acc
        
        # Train XGBoost (uses original data)
        xgb_model = self.train_xgboost(X_train, y_train)
        xgb_acc, _ = self.evaluate_model(xgb_model, 'XGBoost', 
                                         X_test, y_test)
        results['XGBoost'] = xgb_acc
        
        # Train Neural Network (uses scaled data)
        nn_model = self.train_neural_network(X_train_scaled, y_train)
        nn_acc, _ = self.evaluate_model(nn_model, 'Neural Network', 
                                        X_test_scaled, y_test)
        results['Neural Network'] = nn_acc
        
        # Print summary
        print("\n" + "="*70)
        print("FINAL RESULTS SUMMARY")
        print("="*70)
        for model_name, acc in sorted(results.items(), key=lambda x: x[1], reverse=True):
            star = " *** BEST ***" if model_name == self.best_model_name else ""
            print(f"{model_name:25s}: {acc:.4f} ({acc*100:.2f}%){star}")
        
        print(f"\nBest Model: {self.best_model_name}")
        print(f"Best Accuracy: {self.best_accuracy:.4f} ({self.best_accuracy*100:.2f}%)")
        
        return results
    
    def save_best_model(self, filepath='models/best_ufc_model.pkl'):
        """
        Save the best model to disk
        
        Why: So we can load it later for predictions without retraining
        """
        print(f"\nSaving best model ({self.best_model_name}) to {filepath}...")
        
        model_data = {
            'model': self.best_model,
            'model_name': self.best_model_name,
            'scaler': self.scaler,
            'accuracy': self.best_accuracy
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print("Model saved successfully")
    
    def get_feature_importance(self, feature_names):
        """
        Show which features are most important for predictions
        
        Only works for tree-based models (Random Forest, XGBoost)
        """
        if self.best_model_name in ['Random Forest', 'XGBoost']:
            print(f"\nFeature Importance ({self.best_model_name}):")
            print("-" * 50)
            
            importances = self.best_model.feature_importances_
            indices = np.argsort(importances)[::-1]
            
            print("\nTop 15 Most Important Features:")
            for i in range(min(15, len(feature_names))):
                idx = indices[i]
                print(f"{i+1:2d}. {feature_names[idx]:30s}: {importances[idx]:.4f}")
        else:
            print(f"\nFeature importance not available for {self.best_model_name}")


if __name__ == "__main__":
    # Import the data processor
    from kaggle_processor import KaggleUFCProcessor
    
    # Process data
    print("Processing data...")
    processor = KaggleUFCProcessor('data/large_dataset.csv')
    X_train, X_test, y_train, y_test, feature_names = processor.process_all()
    
    # Train models
    trainer = UFCPredictionModel()
    results = trainer.train_all_models(X_train, X_test, y_train, y_test)
    
    # Save best model
    trainer.save_best_model()
    
    # Show feature importance
    trainer.get_feature_importance(feature_names)
    
    print("\n" + "="*70)
    print("MODEL TRAINING COMPLETE!")
    print("="*70)