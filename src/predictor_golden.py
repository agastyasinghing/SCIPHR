"""
UFC Fight Predictor using Golden Dataset Model
With FULL feature calculation (5,401 features)
"""

import pandas as pd
import numpy as np
import pickle
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from golden_feature_calculator import GoldenFeatureCalculator

class UFCFightPredictorGolden:
    """
    Predicts UFC fight outcomes using golden dataset model (5,401 features)
    """
    
    def __init__(self, model_path='models/golden_model.pkl', data_path='data/golden_full_converted.csv'):
        """
        Initialize predictor with golden model
        """
        print("="*70)
        print("UFC FIGHT PREDICTOR - GOLDEN MODEL")
        print("5,401 Features | 85.7% Test Accuracy on UFC 320")
        print("="*70)
        
        # Load the trained model
        print("\nLoading model...")
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.model_name = model_data['model_name']
        self.accuracy = model_data['accuracy']
        self.test_accuracy = model_data.get('test_accuracy', None)
        self.feature_count = model_data['feature_count']
        self.feature_names = model_data['feature_names']
        
        print(f"✓ Loaded model: {self.model_name}")
        print(f"✓ Training accuracy: {self.accuracy:.2%}")
        if self.test_accuracy:
            print(f"✓ Test accuracy (UFC 320): {self.test_accuracy:.2%}")
        print(f"✓ Features: {self.feature_count}")
        
        # Initialize feature calculator
        print("\nInitializing feature calculator...")
        self.feature_calculator = GoldenFeatureCalculator(data_path)
        
        # Build list of available fighters
        print("\nBuilding fighter list...")
        self.available_fighters = self._build_fighter_list()
        print(f"✓ {len(self.available_fighters)} fighters available")
        
        print("="*70)
        print("\n✓ Ready to predict!\n")
    
    def _build_fighter_list(self):
        """Get list of all fighters in dataset"""
        fighters = set()
        
        r_fighters = self.feature_calculator.data['r_name'].dropna().unique()
        b_fighters = self.feature_calculator.data['b_name'].dropna().unique()
        
        fighters.update(r_fighters)
        fighters.update(b_fighters)
        
        return sorted(list(fighters))
    
    def search_fighter(self, name):
        """Search for a fighter by name (fuzzy matching)"""
        name = name.lower().strip()
        
        # Exact match first
        for fighter in self.available_fighters:
            if str(fighter).lower() == name:
                return fighter
        
        # Partial match
        matches = []
        for fighter in self.available_fighters:
            if name in str(fighter).lower() or str(fighter).lower() in name:
                matches.append(fighter)
        
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            print(f"\nMultiple fighters found for '{name}':")
            for i, fighter in enumerate(matches[:10], 1):
                print(f"  {i}. {fighter}")
            return None
        
        return None
    
    def predict_fight(self, fighter1_name, fighter2_name, verbose=False):
        """
        Predict fight outcome between two fighters
        
        Args:
            fighter1_name: Name of first fighter (Red corner)
            fighter2_name: Name of second fighter (Blue corner)
            verbose: If True, print detailed info
        
        Returns:
            Dictionary with prediction results
        """
        if verbose:
            print("="*70)
            print(f"PREDICTING: {fighter1_name} vs {fighter2_name}")
            print("="*70)
        
        # Look up both fighters
        fighter1 = self.search_fighter(fighter1_name)
        fighter2 = self.search_fighter(fighter2_name)
        
        if not fighter1:
            print(f"\nError: Could not find '{fighter1_name}'")
            return None
        
        if not fighter2:
            print(f"\nError: Could not find '{fighter2_name}'")
            return None
        
        if verbose:
            print(f"\nMatched fighters:")
            print(f"  Red Corner: {fighter1}")
            print(f"  Blue Corner: {fighter2}")
        
        # Build FULL feature vector with rolling stats and differences
        features = self.feature_calculator.build_full_feature_vector(
            fighter1, fighter2, self.feature_names
        )
        
        if features is None or len(features) != self.feature_count:
            print(f"\nError: Feature vector has {len(features)} features, expected {self.feature_count}")
            return None
        
        # Make prediction
        try:
            prediction_proba = self.model.predict_proba([features])[0]
            prediction = self.model.predict([features])[0]
        except Exception as e:
            print(f"\n❌ ERROR during prediction: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        # Extract probabilities
        # Model outputs: [prob_draw, prob_fighter2, prob_fighter1]
        prob_draw = float(prediction_proba[0])
        prob_blue = float(prediction_proba[1])
        prob_red = float(prediction_proba[2])
        
        # Determine winner (ignoring draws)
        if prob_red > prob_blue:
            winner = fighter1
            confidence = prob_red
        else:
            winner = fighter2
            confidence = prob_blue
        
        if verbose:
            print("\n" + "="*70)
            print("PREDICTION RESULTS")
            print("="*70)
            print(f"\n🥊 PREDICTED WINNER: {winner}")
            print(f"   Confidence: {confidence:.1%}")
            print(f"\nBreakdown:")
            print(f"  {fighter1} (Red): {prob_red:.1%} chance")
            print(f"  {fighter2} (Blue): {prob_blue:.1%} chance")
            print(f"  Draw/NC: {prob_draw:.1%} chance")
            print("="*70)
        
        # Get basic stats for display
        f1_stats = self.feature_calculator.get_latest_fighter_stats(fighter1)
        f2_stats = self.feature_calculator.get_latest_fighter_stats(fighter2)
        
        return {
            'fighter1': fighter1,
            'fighter2': fighter2,
            'winner': winner,
            'confidence': float(confidence),
            'prob_fighter1': float(prob_red),
            'prob_fighter2': float(prob_blue),
            'model_name': str(self.model_name),
            'implied_odds': f"-{int(confidence * 100)}" if confidence > 0.5 else f"+{int((1-confidence) * 100)}",
            'fighter1_stats': {
                'wins_total': float(f1_stats.get('fighter_w', 0)),
                'losses_total': float(f1_stats.get('fighter_l', 0)),
                'age': float(f1_stats.get('age', 0)),
                'height': float(f1_stats.get('fighter_height_cm', 0)),
                'reach': float(f1_stats.get('fighter_reach_cm', 0)),
                'SLpM_total': float(f1_stats.get('fighter_SlpM', 0)),
                'sig_str_acc_total': float(f1_stats.get('fighter_Str_Acc', 0)),
                'td_acc_total': float(f1_stats.get('fighter_TD_Acc', 0))
            },
            'fighter2_stats': {
                'wins_total': float(f2_stats.get('fighter_w', 0)),
                'losses_total': float(f2_stats.get('fighter_l', 0)),
                'age': float(f2_stats.get('age', 0)),
                'height': float(f2_stats.get('fighter_height_cm', 0)),
                'reach': float(f2_stats.get('fighter_reach_cm', 0)),
                'SLpM_total': float(f2_stats.get('fighter_SlpM', 0)),
                'sig_str_acc_total': float(f2_stats.get('fighter_Str_Acc', 0)),
                'td_acc_total': float(f2_stats.get('fighter_TD_Acc', 0))
            }
        }


def main():
    """Test the predictor"""
    predictor = UFCFightPredictorGolden()
    
    # Test predictions
    print("\n" + "="*70)
    print("TESTING PREDICTIONS")
    print("="*70)
    
    # Test 1: Pereira vs Ankalaev (we know result: Pereira won)
    predictor.predict_fight("Alex Pereira", "Magomed Ankalaev", verbose=True)
    
    # Test 2: Aspinall vs Topuria (should heavily favor Aspinall)
    predictor.predict_fight("Tom Aspinall", "Ilia Topuria", verbose=True)


if __name__ == "__main__":
    main()