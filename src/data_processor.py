"""
Data Processor for UFC Fight Data
Cleans, transforms, and engineers features for ML models
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import re

class UFCDataProcessor:
    """
    Processes raw UFC fight data into ML-ready features
    """
    
    def __init__(self, data_path='data/ufc_fights.csv'):
        """
        Initialize processor and load data
        
        Args:
            data_path: Path to the scraped CSV file
        """
        print("Loading fight data...")
        self.raw_data = pd.read_csv(data_path)
        print(f"Loaded {len(self.raw_data)} fights")
        
        self.processed_data = None
        self.fighter_stats = None
        
    def clean_numeric_columns(self):
        """
        Clean and convert stat columns to proper numeric format
        
        Why: Scraped data comes as strings like "50 of 100" or "45%"
        We need to extract the actual numbers
        """
        print("\nCleaning numeric columns...")
        
        df = self.raw_data.copy()
        
        # Columns that need cleaning
        numeric_cols = [
            'fighter1_knockdowns', 'fighter2_knockdowns',
            'fighter1_sig_strikes', 'fighter2_sig_strikes',
            'fighter1_total_strikes', 'fighter2_total_strikes',
            'fighter1_takedowns', 'fighter2_takedowns',
            'fighter1_submissions', 'fighter2_submissions',
            'fighter1_reversals', 'fighter2_reversals'
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                # Extract first number from strings like "50 of 100"
                df[col] = df[col].astype(str).apply(lambda x: self._extract_number(x))
        
        # Clean percentage columns (like "45%") - MORE DEFENSIVE
        pct_cols = ['fighter1_sig_strike_pct', 'fighter2_sig_strike_pct',
                   'fighter1_takedown_pct', 'fighter2_takedown_pct']
        
        for col in pct_cols:
            if col in df.columns:
                df[col] = df[col].apply(self._extract_percentage)
        
        # Clean control time (format: "5:30" -> 5.5 minutes)
        if 'fighter1_ctrl_time' in df.columns:
            df['fighter1_ctrl_time'] = df['fighter1_ctrl_time'].apply(self._time_to_minutes)
            df['fighter2_ctrl_time'] = df['fighter2_ctrl_time'].apply(self._time_to_minutes)
        
        self.raw_data = df
        print("Cleaned numeric columns")
        
    def _extract_number(self, text):
        """
        Extract first number from a string
        Example: "50 of 100" -> 50
        """
        try:
            match = re.search(r'\d+', str(text))
            return int(match.group()) if match else 0
        except:
            return 0
    
    def _extract_percentage(self, text):
        """
        Extract percentage and convert to decimal
        Example: "45%" -> 0.45
        Handles garbage data gracefully
        """
        try:
            text = str(text)
            # Look for a number followed by %
            match = re.search(r'(\d+(?:\.\d+)?)%', text)
            if match:
                return float(match.group(1)) / 100
            # If no % sign, try to extract just a number
            match = re.search(r'\d+(?:\.\d+)?', text)
            if match:
                val = float(match.group())
                # If it's already a decimal (0-1), keep it
                if 0 <= val <= 1:
                    return val
                # If it's a percentage value (0-100), convert it
                elif val <= 100:
                    return val / 100
            return 0.0
        except:
            return 0.0
    
    def _time_to_minutes(self, time_str):
        """
        Convert time string to minutes
        Example: "5:30" -> 5.5 minutes
        """
        try:
            if ':' in str(time_str):
                parts = str(time_str).split(':')
                return int(parts[0]) + int(parts[1]) / 60
            return 0
        except:
            return 0
    
    def encode_categorical_features(self):
        """
        Convert text categories to numbers
        
        Why: ML models need numbers, not text
        Example: "KO/TKO" -> 1, "Submission" -> 2, "Decision" -> 3
        """
        print("\nEncoding categorical features...")
        
        df = self.raw_data.copy()
        
        # Encode finish method
        def map_method(method):
            method = str(method).upper()
            if 'KO' in method or 'TKO' in method:
                return 1
            elif 'SUB' in method:
                return 2
            elif 'DEC' in method or 'DECISION' in method:
                return 3
            else:
                return 4
        
        df['method_encoded'] = df['method'].apply(map_method)
        
        # Convert round to number
        df['round'] = pd.to_numeric(df['round'], errors='coerce').fillna(3)
        
        self.raw_data = df
        print("Encoded categorical features")
    
    def calculate_fighter_statistics(self):
        """
        Calculate cumulative statistics for each fighter
        
        Why: A fighter's history is crucial for prediction
        We calculate things like:
        - Win rate
        - Average strikes per fight
        - Finish rate
        - Recent form (last 3 fights)
        
        This is the MOST IMPORTANT part for ML performance
        """
        print("\nCalculating fighter statistics...")
        
        # Sort by date so we can calculate stats chronologically
        df = self.raw_data.copy()
        df['event_date'] = pd.to_datetime(df['event_date'], errors='coerce')
        df = df.sort_values('event_date')
        
        fighter_stats = {}
        
        # Process each fight chronologically
        for idx, fight in df.iterrows():
            f1 = fight['fighter1_name']
            f2 = fight['fighter2_name']
            
            # Initialize fighter if new
            if f1 not in fighter_stats:
                fighter_stats[f1] = self._init_fighter_stats()
            if f2 not in fighter_stats:
                fighter_stats[f2] = self._init_fighter_stats()
            
            # Store CURRENT stats before updating (for this fight's features)
            df.at[idx, 'f1_wins'] = fighter_stats[f1]['wins']
            df.at[idx, 'f1_losses'] = fighter_stats[f1]['losses']
            df.at[idx, 'f1_total_fights'] = fighter_stats[f1]['total_fights']
            df.at[idx, 'f1_finish_rate'] = fighter_stats[f1]['finish_rate']
            df.at[idx, 'f1_avg_strikes'] = fighter_stats[f1]['avg_strikes']
            df.at[idx, 'f1_avg_takedowns'] = fighter_stats[f1]['avg_takedowns']
            
            df.at[idx, 'f2_wins'] = fighter_stats[f2]['wins']
            df.at[idx, 'f2_losses'] = fighter_stats[f2]['losses']
            df.at[idx, 'f2_total_fights'] = fighter_stats[f2]['total_fights']
            df.at[idx, 'f2_finish_rate'] = fighter_stats[f2]['finish_rate']
            df.at[idx, 'f2_avg_strikes'] = fighter_stats[f2]['avg_strikes']
            df.at[idx, 'f2_avg_takedowns'] = fighter_stats[f2]['avg_takedowns']
            
            # UPDATE stats after this fight (for future fights)
            self._update_fighter_stats(fighter_stats[f1], fight, is_fighter1=True)
            self._update_fighter_stats(fighter_stats[f2], fight, is_fighter1=False)
        
        self.processed_data = df
        self.fighter_stats = fighter_stats
        print(f"Calculated stats for {len(fighter_stats)} fighters")
    
    def _init_fighter_stats(self):
        """Initialize empty stats for a new fighter"""
        return {
            'wins': 0,
            'losses': 0,
            'total_fights': 0,
            'finishes': 0,
            'finish_rate': 0.0,
            'avg_strikes': 0.0,
            'avg_takedowns': 0.0,
            'total_strikes': 0,
            'total_takedowns': 0
        }
    
    def _update_fighter_stats(self, stats, fight, is_fighter1):
        """
        Update a fighter's running statistics after a fight
        
        Args:
            stats: Fighter's stat dictionary
            fight: The fight row
            is_fighter1: True if this is fighter1, False if fighter2
        """
        # Determine if this fighter won
        fighter_won = (is_fighter1 and fight['winner'] == 1) or \
                      (not is_fighter1 and fight['winner'] == 0)
        
        # Update win/loss record
        if fighter_won:
            stats['wins'] += 1
        else:
            stats['losses'] += 1
        
        stats['total_fights'] += 1
        
        # Update finish rate (if fight ended early)
        if fight['method_encoded'] in [1, 2]:  # KO or Submission
            stats['finishes'] += 1
        
        if stats['total_fights'] > 0:
            stats['finish_rate'] = stats['finishes'] / stats['total_fights']
        
        # Update strike and takedown averages
        prefix = 'fighter1' if is_fighter1 else 'fighter2'
        
        strikes = fight.get(f'{prefix}_sig_strikes', 0)
        takedowns = fight.get(f'{prefix}_takedowns', 0)
        
        stats['total_strikes'] += strikes
        stats['total_takedowns'] += takedowns
        
        if stats['total_fights'] > 0:
            stats['avg_strikes'] = stats['total_strikes'] / stats['total_fights']
            stats['avg_takedowns'] = stats['total_takedowns'] / stats['total_fights']
    
    def create_fight_features(self):
        """
        Create differential features (comparing both fighters)
        
        Why: ML models learn better from comparisons than absolute values
        Example: Instead of "Fighter A has 10 wins, Fighter B has 5 wins"
               Better: "Fighter A has +5 win differential"
        """
        print("\nCreating fight features...")
        
        df = self.processed_data.copy()
        
        # Win rate differential
        df['f1_win_rate'] = df['f1_wins'] / (df['f1_total_fights'] + 1)  # +1 to avoid division by 0
        df['f2_win_rate'] = df['f2_wins'] / (df['f2_total_fights'] + 1)
        df['win_rate_diff'] = df['f1_win_rate'] - df['f2_win_rate']
        
        # Experience differential (total fights)
        df['experience_diff'] = df['f1_total_fights'] - df['f2_total_fights']
        
        # Finish rate differential
        df['finish_rate_diff'] = df['f1_finish_rate'] - df['f2_finish_rate']
        
        # Strike differential (average per fight)
        df['strike_diff'] = df['f1_avg_strikes'] - df['f2_avg_strikes']
        
        # Takedown differential
        df['takedown_diff'] = df['f1_avg_takedowns'] - df['f2_avg_takedowns']
        
        # In-fight stats (current fight)
        df['fight_strike_diff'] = df['fighter1_sig_strikes'] - df['fighter2_sig_strikes']
        df['fight_takedown_diff'] = df['fighter1_takedowns'] - df['fighter2_takedowns']
        df['fight_knockdown_diff'] = df['fighter1_knockdowns'] - df['fighter2_knockdowns']
        
        # Fill any NaN values with 0
        df = df.fillna(0)
        
        self.processed_data = df
        print("Created differential features")
    
    def prepare_ml_dataset(self, test_size=0.2):
        """
        Prepare final dataset for machine learning
        
        Args:
            test_size: Proportion of data to use for testing (0.2 = 20%)
        
        Returns:
            X_train, X_test, y_train, y_test
            
        Why split data:
        - Training set: Model learns from this (80%)
        - Test set: We evaluate performance on this (20%)
        - NEVER train on test data or we'll overfit!
        """
        print("\nPreparing ML dataset...")
        
        df = self.processed_data.copy()
        
        # Select features for the model
        feature_columns = [
            # Historical stats
            'f1_total_fights', 'f2_total_fights',
            'f1_wins', 'f2_wins',
            'f1_losses', 'f2_losses',
            'f1_finish_rate', 'f2_finish_rate',
            'f1_avg_strikes', 'f2_avg_strikes',
            'f1_avg_takedowns', 'f2_avg_takedowns',
            
            # Differential features
            'win_rate_diff',
            'experience_diff',
            'finish_rate_diff',
            'strike_diff',
            'takedown_diff',
            
            # In-fight stats
            'fighter1_sig_strikes', 'fighter2_sig_strikes',
            'fighter1_takedowns', 'fighter2_takedowns',
            'fighter1_knockdowns', 'fighter2_knockdowns',
            'fight_strike_diff',
            'fight_takedown_diff',
            'fight_knockdown_diff'
        ]
        
        # Remove rows where fighters have no history (can't predict those well)
        df = df[(df['f1_total_fights'] > 0) | (df['f2_total_fights'] > 0)]
        
        # Features (X) and target (y)
        X = df[feature_columns]
        y = df['winner']  # 1 = fighter1 wins, 0 = fighter2 wins
        
        # Split into train and test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        print(f"Training set: {len(X_train)} fights")
        print(f"Test set: {len(X_test)} fights")
        print(f"Features: {len(feature_columns)}")
        
        return X_train, X_test, y_train, y_test
    
    def process_all(self):
        """
        Run the complete processing pipeline
        
        This is the main function that runs everything in order
        """
        print("\n" + "="*50)
        print("Starting Data Processing Pipeline")
        print("="*50)
        
        self.clean_numeric_columns()
        self.encode_categorical_features()
        self.calculate_fighter_statistics()
        self.create_fight_features()
        
        # Save processed data
        output_path = 'data/processed_fights.csv'
        self.processed_data.to_csv(output_path, index=False)
        print(f"\nSaved processed data to: {output_path}")
        
        # Prepare ML datasets
        X_train, X_test, y_train, y_test = self.prepare_ml_dataset()
        
        print("\n" + "="*50)
        print("Processing Complete!")
        print("="*50)
        
        return X_train, X_test, y_train, y_test


if __name__ == "__main__":
    # Run the processor
    processor = UFCDataProcessor('data/ufc_fights.csv')
    X_train, X_test, y_train, y_test = processor.process_all()
    
    print("\nData Preview:")
    print(X_train.head())