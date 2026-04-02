"""
UFC Fight Predictor V2
Uses 256-feature model for predictions
"""

import pandas as pd
import numpy as np
import pickle
import sys
import io
from datetime import datetime
from features.feature_engine import UFCFeatureEngine

class UFCFightPredictorV2:
    """
    Predicts UFC fight outcomes using 256-feature model
    """
    
    def __init__(self, model_path='models/best_ufc_model_v2.pkl', data_path='data/large_dataset.csv'):
        """
        Initialize predictor
        
        Args:
            model_path: Path to saved V2 model
            data_path: Path to historical data
        """
        print("="*70)
        print("UFC FIGHT PREDICTOR V2")
        print("256-Feature Advanced Model")
        print("="*70)
        
        # Load the trained model
        print("\nLoading model...")
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.model_name = model_data['model_name']
        self.scaler = model_data.get('scaler', None)
        self.accuracy = model_data['accuracy']
        self.feature_count = model_data.get('feature_count', 256)
        self.feature_names = model_data.get('feature_names', [])
        
        print(f"✓ Loaded model: {self.model_name}")
        print(f"✓ Training accuracy: {self.accuracy:.2%}")
        print(f"✓ Features: {self.feature_count}")
        print(f"✓ Feature names loaded: {len(self.feature_names)}")
        
        # Load historical data
        print("\nLoading fighter database...")
        self.data = pd.read_csv(data_path)
        print(f"✓ Loaded {len(self.data)} historical fights")
        
        # Initialize feature engine
        self.feature_engine = UFCFeatureEngine()
        
        # Build fighter stats database
        self.fighter_stats = self._build_fighter_database()
        print(f"✓ Built database for {len(self.fighter_stats)} fighters")
        print("="*70)
        print("\n✓ Ready to predict!\n")
    
    def _build_fighter_database(self):
        """
        Build a database of each fighter's most recent stats
        """
        fighter_stats = {}
        df = self.data.copy()
        
        # Process each fight
        for _, fight in df.iterrows():
            red_fighter = fight['r_fighter']
            blue_fighter = fight['b_fighter']
            
            # Store Red fighter's stats
            fighter_stats[red_fighter] = self._extract_fighter_stats(fight, 'r')
            
            # Store Blue fighter's stats
            fighter_stats[blue_fighter] = self._extract_fighter_stats(fight, 'b')
        
        return fighter_stats
    
    def _extract_fighter_stats(self, fight, prefix):
        """Extract all stats for a fighter from a fight record"""
        stats = {}
        
        # Get all columns for this fighter
        for col in fight.index:
            if col.startswith(f'{prefix}_'):
                stat_name = col[2:]  # Remove prefix
                stats[stat_name] = fight[col]
        
        return stats
    
    def search_fighter(self, name):
        """Search for a fighter by name (fuzzy matching)"""
        name = name.lower().strip()
        
        # Exact match first
        for fighter in self.fighter_stats.keys():
            if fighter.lower() == name:
                return fighter
        
        # Partial match
        matches = []
        for fighter in self.fighter_stats.keys():
            if name in fighter.lower() or fighter.lower() in name:
                matches.append(fighter)
        
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            print(f"\nMultiple fighters found for '{name}':")
            for i, fighter in enumerate(matches, 1):
                print(f"  {i}. {fighter}")
            return None
        
        return None
    
    def get_fighter_stats(self, fighter_name):
        """Get stats for a specific fighter"""
        fighter = self.search_fighter(fighter_name)
        
        if fighter:
            return self.fighter_stats[fighter]
        else:
            print(f"Fighter '{fighter_name}' not found in database")
            return None
    
    def predict_fight(self, fighter1_name, fighter2_name, verbose=False):
        """
        Predict the outcome of a fight using 256-feature model
        
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
        
        # Get stats for both fighters
        f1_stats = self.fighter_stats[fighter1]
        f2_stats = self.fighter_stats[fighter2]
        
        if verbose:
            print(f"\n{fighter1} Stats:")
            print(f"  Record: {f1_stats.get('wins_total', 0):.0f}-{f1_stats.get('losses_total', 0):.0f}")
            print(f"  Age: {f1_stats.get('age', 0):.0f}, Weight: {f1_stats.get('weight', 0):.0f} lbs")
            
            print(f"\n{fighter2} Stats:")
            print(f"  Record: {f2_stats.get('wins_total', 0):.0f}-{f2_stats.get('losses_total', 0):.0f}")
            print(f"  Age: {f2_stats.get('age', 0):.0f}, Weight: {f2_stats.get('weight', 0):.0f} lbs")
        
        # Build feature vector
        features = self._build_feature_vector(f1_stats, f2_stats, verbose=verbose)
        
        if verbose:
            print(f"\n✓ Generated {len(features)} features for prediction")
        
        # Make prediction
        try:
            if self.scaler is not None:
                features_scaled = self.scaler.transform([features])
                prediction_proba = self.model.predict_proba(features_scaled)[0]
            else:
                prediction_proba = self.model.predict_proba([features])[0]
        except Exception as e:
            print(f"\n❌ ERROR during prediction: {e}")
            print(f"   Feature vector length: {len(features)}")
            print(f"   Expected features: {self.feature_count}")
            return None
        
        # Extract probabilities (prob_blue, prob_red)
        prob_blue = float(prediction_proba[0])
        prob_red = float(prediction_proba[1])
        
        # Determine winner
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
            print(f"\nModel: {self.model_name} (Accuracy: {self.accuracy:.1%})")
            print("="*70)
        
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
                'wins_total': float(f1_stats.get('wins_total', 0)),
                'losses_total': float(f1_stats.get('losses_total', 0)),
                'age': float(f1_stats.get('age', 0)),
                'height': float(f1_stats.get('height', 0)),
                'reach': float(f1_stats.get('reach', 0)),
                'SLpM_total': float(f1_stats.get('SLpM_total', 0)),
                'sig_str_acc_total': float(f1_stats.get('sig_str_acc_total', 0)),
                'td_acc_total': float(f1_stats.get('td_acc_total', 0))
            },
            'fighter2_stats': {
                'wins_total': float(f2_stats.get('wins_total', 0)),
                'losses_total': float(f2_stats.get('losses_total', 0)),
                'age': float(f2_stats.get('age', 0)),
                'height': float(f2_stats.get('height', 0)),
                'reach': float(f2_stats.get('reach', 0)),
                'SLpM_total': float(f2_stats.get('SLpM_total', 0)),
                'sig_str_acc_total': float(f2_stats.get('sig_str_acc_total', 0)),
                'td_acc_total': float(f2_stats.get('td_acc_total', 0))
            }
        }
    
    def _build_feature_vector(self, f1_stats, f2_stats, verbose=False):
        """
        Build 256-feature vector using saved feature names
        Ensures exact match with training features
        """
        # Create a temporary dataframe with both fighters
        temp_df = pd.DataFrame([{
            **{f'r_{k}': v for k, v in f1_stats.items()},
            **{f'b_{k}': v for k, v in f2_stats.items()}
        }])
        
        # CRITICAL FIX: Calculate derived columns that feature engineering expects
        # Total fights
        if 'r_total_fights' not in temp_df.columns:
            temp_df['r_total_fights'] = temp_df.get('r_wins_total', 0) + temp_df.get('r_losses_total', 0) + temp_df.get('r_draw', 0)
        if 'b_total_fights' not in temp_df.columns:
            temp_df['b_total_fights'] = temp_df.get('b_wins_total', 0) + temp_df.get('b_losses_total', 0) + temp_df.get('b_draw', 0)

        # Difference columns
        if 'weight_diff' not in temp_df.columns:
            temp_df['weight_diff'] = temp_df.get('r_weight', 0) - temp_df.get('b_weight', 0)
        if 'height_diff' not in temp_df.columns:
            temp_df['height_diff'] = temp_df.get('r_height', 0) - temp_df.get('b_height', 0)
        if 'reach_diff' not in temp_df.columns:
            temp_df['reach_diff'] = temp_df.get('r_reach', 0) - temp_df.get('b_reach', 0)
        if 'age_diff' not in temp_df.columns:
            temp_df['age_diff'] = temp_df.get('r_age', 0) - temp_df.get('b_age', 0)

        # Win percentage
        if 'r_win_pct' not in temp_df.columns:
            total = temp_df.get('r_total_fights', [1])[0]
            temp_df['r_win_pct'] = temp_df.get('r_wins_total', 0) / max(total, 1)
        if 'b_win_pct' not in temp_df.columns:
            total = temp_df.get('b_total_fights', [1])[0]
            temp_df['b_win_pct'] = temp_df.get('b_wins_total', 0) / max(total, 1)
        
        # Suppress feature engineering output
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            # Apply feature engineering
            temp_df_with_features = self.feature_engine.create_all_features(temp_df)
            
            # Fill NaN values
            temp_df_with_features = temp_df_with_features.fillna(0)
        finally:
            sys.stdout = old_stdout
        
        # Extract features in exact order
        feature_vector = []
        missing_features = []
        
        for feature_name in self.feature_names:
            if feature_name in temp_df_with_features.columns:
                val = temp_df_with_features[feature_name].iloc[0]
                if pd.notna(val) and np.isfinite(val):
                    feature_vector.append(val)
                else:
                    feature_vector.append(0)
            else:
                feature_vector.append(0)
                missing_features.append(feature_name)
        
        if missing_features and verbose:
            print(f"\nWarning: {len(missing_features)} features missing, using 0 as default")
        
        return feature_vector
    
    def list_available_fighters(self, search_term=None, limit=20):
        """List fighters in the database"""
        fighters = list(self.fighter_stats.keys())
        
        if search_term:
            search_term = search_term.lower()
            fighters = [f for f in fighters if search_term in f.lower()]
        
        fighters = sorted(fighters)[:limit]
        
        print(f"\nShowing {len(fighters)} fighters:")
        for i, fighter in enumerate(fighters, 1):
            stats = self.fighter_stats[fighter]
            print(f"{i:3d}. {fighter:30s} ({stats.get('wins_total', 0):.0f}-{stats.get('losses_total', 0):.0f})")


def main():
    """Test the predictor"""
    predictor = UFCFightPredictorV2()
    
    print("\n" + "="*70)
    print("TESTING PREDICTOR V2")
    print("="*70)
    
    # Test prediction
    predictor.predict_fight("Jon Jones", "Demetrious Johnson")


if __name__ == "__main__":
    main()