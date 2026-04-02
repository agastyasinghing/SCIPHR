"""
UFC Fight Predictor
Uses trained model to predict outcomes of upcoming fights
"""

import pandas as pd
import numpy as np
import pickle
from datetime import datetime

class UFCFightPredictor:
    """
    Predicts UFC fight outcomes using trained ML model
    """
    
    def __init__(self, model_path='models/best_ufc_model.pkl', data_path='data/large_dataset.csv'):
        """
        Initialize predictor
        
        Args:
            model_path: Path to saved model
            data_path: Path to historical data (for fighter stats lookup)
        """
        print("Loading prediction system...")
        
        # Load the trained model
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.model_name = model_data['model_name']
        self.scaler = model_data['scaler']
        self.accuracy = model_data['accuracy']
        
        print(f"Loaded model: {self.model_name}")
        print(f"Training accuracy: {self.accuracy:.2%}")
        
        # Load historical data to get fighter stats
        print("Loading fighter database...")
        self.data = pd.read_csv(data_path)
        print(f"Loaded {len(self.data)} historical fights")
        
        # Build fighter stats database
        self.fighter_stats = self._build_fighter_database()
        print(f"Built database for {len(self.fighter_stats)} fighters")
        print("Ready to predict!\n")
    
    def _build_fighter_database(self):
        """
        Build a database of each fighter's most recent stats
        
        Why: We need current stats for each fighter to make predictions
        
        How it works:
        - Go through all fights chronologically
        - For each fighter, keep updating their stats
        - End result: dictionary with each fighter's most recent stats
        """
        fighter_stats = {}
        
        # Sort by most recent fights first (assuming data is somewhat chronological)
        df = self.data.copy()
        
        # Process each fight
        for _, fight in df.iterrows():
            red_fighter = fight['r_fighter']
            blue_fighter = fight['b_fighter']
            
            # Store Red fighter's stats from this fight
            fighter_stats[red_fighter] = {
                'wins_total': fight.get('r_wins_total', 0),
                'losses_total': fight.get('r_losses_total', 0),
                'age': fight.get('r_age', 30),
                'height': fight.get('r_height', 70),
                'weight': fight.get('r_weight', 170),
                'reach': fight.get('r_reach', 70),
                'SLpM_total': fight.get('r_SLpM_total', 3),
                'SApM_total': fight.get('r_SApM_total', 3),
                'sig_str_acc_total': fight.get('r_sig_str_acc_total', 0.45),
                'td_acc_total': fight.get('r_td_acc_total', 0.40),
                'str_def_total': fight.get('r_str_def_total', 0.50),
                'td_def_total': fight.get('r_td_def_total', 0.60),
                'sub_avg': fight.get('r_sub_avg', 0.5),
                'td_avg': fight.get('r_td_avg', 1.0)
            }
            
            # Store Blue fighter's stats from this fight
            fighter_stats[blue_fighter] = {
                'wins_total': fight.get('b_wins_total', 0),
                'losses_total': fight.get('b_losses_total', 0),
                'age': fight.get('b_age', 30),
                'height': fight.get('b_height', 70),
                'weight': fight.get('b_weight', 170),
                'reach': fight.get('b_reach', 70),
                'SLpM_total': fight.get('b_SLpM_total', 3),
                'SApM_total': fight.get('b_SApM_total', 3),
                'sig_str_acc_total': fight.get('b_sig_str_acc_total', 0.45),
                'td_acc_total': fight.get('b_td_acc_total', 0.40),
                'str_def_total': fight.get('b_str_def_total', 0.50),
                'td_def_total': fight.get('b_td_def_total', 0.60),
                'sub_avg': fight.get('b_sub_avg', 0.5),
                'td_avg': fight.get('b_td_avg', 1.0)
            }
        
        return fighter_stats
    
    def search_fighter(self, name):
        """
        Search for a fighter by name (fuzzy matching)
        
        Why: Fighter names might be spelled differently
        Example: "Jon Jones" vs "Jonathan Jones"
        
        Args:
            name: Fighter name to search
            
        Returns:
            Best matching fighter name, or None
        """
        name = name.lower().strip()
        
        # Exact match first
        for fighter in self.fighter_stats.keys():
            if fighter.lower() == name:
                return fighter
        
        # Partial match (contains)
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
        """
        Get stats for a specific fighter
        
        Args:
            fighter_name: Name of the fighter
            
        Returns:
            Dictionary of fighter stats
        """
        fighter = self.search_fighter(fighter_name)
        
        if fighter:
            return self.fighter_stats[fighter]
        else:
            print(f"Fighter '{fighter_name}' not found in database")
            return None
    
    def predict_fight(self, fighter1_name, fighter2_name, verbose=True):
        """
        Predict the outcome of a fight
        
        This is the main function that does everything:
        1. Looks up both fighters
        2. Gets their stats
        3. Calculates differentials
        4. Feeds to model
        5. Returns prediction
        
        Args:
            fighter1_name: Name of first fighter (will be "Red" corner)
            fighter2_name: Name of second fighter (will be "Blue" corner)
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
            print("Try searching for similar names or check spelling")
            return None
        
        if not fighter2:
            print(f"\nError: Could not find '{fighter2_name}'")
            print("Try searching for similar names or check spelling")
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
            print(f"  Record: {f1_stats['wins_total']}-{f1_stats['losses_total']}")
            print(f"  Age: {f1_stats['age']}, Height: {f1_stats['height']:.1f}\", Reach: {f1_stats['reach']:.1f}\"")
            print(f"  Strikes/min: {f1_stats['SLpM_total']:.2f}, Accuracy: {f1_stats['sig_str_acc_total']:.1%}")
            
            print(f"\n{fighter2} Stats:")
            print(f"  Record: {f2_stats['wins_total']}-{f2_stats['losses_total']}")
            print(f"  Age: {f2_stats['age']}, Height: {f2_stats['height']:.1f}\", Reach: {f2_stats['reach']:.1f}\"")
            print(f"  Strikes/min: {f2_stats['SLpM_total']:.2f}, Accuracy: {f2_stats['sig_str_acc_total']:.1%}")
        
        # Build feature vector (52 features the model expects)
        features = self._build_feature_vector(f1_stats, f2_stats)
        
        # Make prediction
        # Neural Network needs scaled features
        if self.model_name == 'Neural Network' or self.model_name == 'Logistic Regression':
            features_scaled = self.scaler.transform([features])
            prediction_proba = self.model.predict_proba(features_scaled)[0]
        else:
            prediction_proba = self.model.predict_proba([features])[0]
        
        # prediction_proba = [prob_blue_wins, prob_red_wins]
        prob_blue = prediction_proba[0]
        prob_red = prediction_proba[1]
        
        # Determine winner
        if prob_red > prob_blue:
            winner = fighter1
            confidence = prob_red
            odds = self._probability_to_odds(prob_red)
        else:
            winner = fighter2
            confidence = prob_blue
            odds = self._probability_to_odds(prob_blue)
        
        if verbose:
            print("\n" + "="*70)
            print("PREDICTION RESULTS")
            print("="*70)
            print(f"\nPREDICTED WINNER: {winner}")
            print(f"   Confidence: {confidence:.1%}")
            print(f"   Implied Odds: {odds}")
            print(f"\nBreakdown:")
            print(f"  {fighter1} (Red): {prob_red:.1%} chance")
            print(f"  {fighter2} (Blue): {prob_blue:.1%} chance")
            print(f"\nModel: {self.model_name} (Training Accuracy: {self.accuracy:.1%})")
        
        return {
            'fighter1': fighter1,
            'fighter2': fighter2,
            'winner': winner,
            'confidence': confidence,
            'prob_fighter1': prob_red,
            'prob_fighter2': prob_blue,
            'implied_odds': odds,
            'model_name': self.model_name
        }
    
    def _build_feature_vector(self, f1_stats, f2_stats):
        """
        Build the feature vector the model expects
        NOW WITH: 10 new size/weight context features (52 total features)
        """
        # Helper function for weight class
        def get_weight_class(weight):
            if weight <= 125:
                return 1
            elif weight <= 135:
                return 2
            elif weight <= 145:
                return 3
            elif weight <= 155:
                return 4
            elif weight <= 170:
                return 5
            elif weight <= 185:
                return 6
            elif weight <= 205:
                return 7
            else:
                return 8
        
        # Red fighter features (14)
        red_features = [
            f1_stats['wins_total'],
            f1_stats['losses_total'],
            f1_stats['age'],
            f1_stats['height'],
            f1_stats['weight'],
            f1_stats['reach'],
            f1_stats['SLpM_total'],
            f1_stats['SApM_total'],
            f1_stats['sig_str_acc_total'],
            f1_stats['td_acc_total'],
            f1_stats['str_def_total'],
            f1_stats['td_def_total'],
            f1_stats['sub_avg'],
            f1_stats['td_avg']
        ]
        
        # Blue fighter features (14)
        blue_features = [
            f2_stats['wins_total'],
            f2_stats['losses_total'],
            f2_stats['age'],
            f2_stats['height'],
            f2_stats['weight'],
            f2_stats['reach'],
            f2_stats['SLpM_total'],
            f2_stats['SApM_total'],
            f2_stats['sig_str_acc_total'],
            f2_stats['td_acc_total'],
            f2_stats['str_def_total'],
            f2_stats['td_def_total'],
            f2_stats['sub_avg'],
            f2_stats['td_avg']
        ]
        
        # Original differential features (14)
        diff_features = [
            f1_stats['wins_total'] - f2_stats['wins_total'],
            f1_stats['losses_total'] - f2_stats['losses_total'],
            f1_stats['age'] - f2_stats['age'],
            f1_stats['height'] - f2_stats['height'],
            f1_stats['weight'] - f2_stats['weight'],
            f1_stats['reach'] - f2_stats['reach'],
            f1_stats['SLpM_total'] - f2_stats['SLpM_total'],
            f1_stats['SApM_total'] - f2_stats['SApM_total'],
            f1_stats['sig_str_acc_total'] - f2_stats['sig_str_acc_total'],
            f1_stats['td_acc_total'] - f2_stats['td_acc_total'],
            f1_stats['str_def_total'] - f2_stats['str_def_total'],
            f1_stats['td_def_total'] - f2_stats['td_def_total'],
            f1_stats['sub_avg'] - f2_stats['sub_avg'],
            f1_stats['td_avg'] - f2_stats['td_avg']
        ]
        
        # NEW: Size/weight context features (10)
        r_weight_class = get_weight_class(f1_stats['weight'])
        b_weight_class = get_weight_class(f2_stats['weight'])
        
        weight_class_diff = abs(r_weight_class - b_weight_class)
        is_same_weight_class = 1 if weight_class_diff == 0 else 0
        
        weight_diff_pct = abs(f1_stats['weight'] - f2_stats['weight']) / min(f1_stats['weight'], f2_stats['weight']) if min(f1_stats['weight'], f2_stats['weight']) > 0 else 0
        height_diff_pct = abs(f1_stats['height'] - f2_stats['height']) / min(f1_stats['height'], f2_stats['height']) if min(f1_stats['height'], f2_stats['height']) > 0 else 0
        reach_diff_pct = abs(f1_stats['reach'] - f2_stats['reach']) / min(f1_stats['reach'], f2_stats['reach']) if min(f1_stats['reach'], f2_stats['reach']) > 0 else 0
        
        is_cross_gender = 0  # Placeholder
        
        r_bmi = (f1_stats['weight'] / (f1_stats['height'] ** 2)) * 703
        b_bmi = (f2_stats['weight'] / (f2_stats['height'] ** 2)) * 703
        bmi_diff = abs(r_bmi - b_bmi)
        
        r_wh_ratio = f1_stats['weight'] / f1_stats['height']
        b_wh_ratio = f2_stats['weight'] / f2_stats['height']
        wh_ratio_diff = abs(r_wh_ratio - b_wh_ratio)
        
        realistic_matchup = 1 if weight_class_diff <= 2 else 0
        
        size_advantage_score = (
            (f1_stats['weight'] - f2_stats['weight']) / 100 +
            (f1_stats['height'] - f2_stats['height']) / 10 +
            (f1_stats['reach'] - f2_stats['reach']) / 10
        )
        
        size_features = [
            weight_class_diff,
            is_same_weight_class,
            weight_diff_pct,
            height_diff_pct,
            reach_diff_pct,
            is_cross_gender,
            bmi_diff,
            wh_ratio_diff,
            realistic_matchup,
            size_advantage_score
        ]
        
        # Combine all features (52 total: 14 + 14 + 14 + 10)
        return red_features + blue_features + diff_features + size_features
    
    def _probability_to_odds(self, probability):
        """
        Convert probability to American odds format
        
        Why: Betting sites show odds like -200 or +150
        
        How it works:
        - Probability > 50%: Negative odds (favorite)
        - Probability < 50%: Positive odds (underdog)
        
        Example:
        - 70% probability → -233 odds (bet $233 to win $100)
        - 30% probability → +233 odds (bet $100 to win $233)
        """
        if probability >= 0.5:
            # Favorite (negative odds)
            odds = -1 * (probability / (1 - probability)) * 100
            return f"{odds:.0f}"
        else:
            # Underdog (positive odds)
            odds = ((1 - probability) / probability) * 100
            return f"+{odds:.0f}"
    
    def predict_multiple_fights(self, fight_pairs):
        """
        Predict multiple fights at once
        
        Args:
            fight_pairs: List of tuples [(fighter1, fighter2), ...]
            
        Returns:
            List of prediction dictionaries
        """
        results = []
        
        for fighter1, fighter2 in fight_pairs:
            result = self.predict_fight(fighter1, fighter2, verbose=True)
            if result:
                results.append(result)
            print("\n")
        
        return results
    
    def list_available_fighters(self, search_term=None, limit=20):
        """
        List fighters in the database
        
        Args:
            search_term: Optional search term to filter
            limit: Maximum number to show
        """
        fighters = list(self.fighter_stats.keys())
        
        if search_term:
            search_term = search_term.lower()
            fighters = [f for f in fighters if search_term in f.lower()]
        
        fighters = sorted(fighters)[:limit]
        
        print(f"\nShowing {len(fighters)} fighters:")
        for i, fighter in enumerate(fighters, 1):
            stats = self.fighter_stats[fighter]
            print(f"{i:3d}. {fighter:30s} ({stats['wins_total']:.0f}-{stats['losses_total']:.0f})")


if __name__ == "__main__":
    # Initialize predictor
    predictor = UFCFightPredictor()
    
    # Example: Predict a fight
    print("\n" + "="*70)
    print("EXAMPLE PREDICTION")
    print("="*70)
    
    # You can change these to any fighters in the database
    predictor.predict_fight("Jon Jones", "Alexander Volkanovski")
    
    # Show some available fighters
    print("\n" + "="*70)
    print("SAMPLE FIGHTERS IN DATABASE")
    print("="*70)
    predictor.list_available_fighters(limit=30)