"""
Kaggle UFC Data Processor
Processes the pre-cleaned Kaggle UFC dataset for ML
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

class KaggleUFCProcessor:
    """
    Processes Kaggle UFC dataset for machine learning
    """
    
    def __init__(self, data_path='data/large_dataset.csv'):
        """
        Initialize processor and load data
        
        Args:
            data_path: Path to the Kaggle CSV file
        """
        print("Loading Kaggle UFC data...")
        self.raw_data = pd.read_csv(data_path)
        print(f"Loaded {len(self.raw_data)} fights")
        print(f"Columns: {len(self.raw_data.columns)}")
        
        self.processed_data = None
        
    def clean_data(self):
        """
        Clean and prepare the data
        
        Why: Even though Kaggle data is clean, we need to:
        - Handle missing values
        - Convert winner column to numeric
        - Remove fights with incomplete data
        """
        print("\nCleaning data...")
        
        df = self.raw_data.copy()
        
        # Convert winner to numeric
        # Red = 1, Blue = 0, Draw/NC = 0.5
        def encode_winner(winner):
            if pd.isna(winner):
                return np.nan
            winner = str(winner).lower()
            if 'red' in winner:
                return 1
            elif 'blue' in winner:
                return 0
            else:
                return 0.5  # Draw or No Contest
        
        df['winner_encoded'] = df['winner'].apply(encode_winner)
        
        # Remove fights with missing winner
        df = df.dropna(subset=['winner_encoded'])
        
        # Fill missing numeric values with 0
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].fillna(0)
        
        # Remove any remaining rows with critical missing data
        critical_cols = ['r_fighter', 'b_fighter', 'winner_encoded']
        df = df.dropna(subset=critical_cols)
        
        print(f"Cleaned data: {len(df)} fights remain")
        
        self.processed_data = df
    
    def _get_weight_class(self, weight, gender='Male'):
        """
        Determine weight class from weight
        
        Args:
            weight: Fighter weight in lbs
            gender: 'Male' or 'Female'
            
        Returns:
            Weight class number (1-8 for men, 1-4 for women)
        """
        if gender == 'Female' or weight < 130:
            # Women's divisions
            if weight <= 115:
                return 1  # Strawweight
            elif weight <= 125:
                return 2  # Flyweight
            elif weight <= 135:
                return 3  # Bantamweight
            else:
                return 4  # Featherweight
        else:
            # Men's divisions
            if weight <= 125:
                return 1  # Flyweight
            elif weight <= 135:
                return 2  # Bantamweight
            elif weight <= 145:
                return 3  # Featherweight
            elif weight <= 155:
                return 4  # Lightweight
            elif weight <= 170:
                return 5  # Welterweight
            elif weight <= 185:
                return 6  # Middleweight
            elif weight <= 205:
                return 7  # Light Heavyweight
            else:
                return 8  # Heavyweight
    
    def create_size_features(self):
        """
        Create 10 new features related to size and weight class context
        
        These features help the model understand:
        - Weight class differences (heavyweight vs flyweight)
        - Relative size advantages
        - Realistic matchup detection
        """
        print("\nCreating size/weight context features...")
        
        df = self.processed_data.copy()
        
        # Get weight classes for both fighters
        df['r_weight_class'] = df.apply(
            lambda row: self._get_weight_class(row.get('r_weight', 170)), 
            axis=1
        )
        df['b_weight_class'] = df.apply(
            lambda row: self._get_weight_class(row.get('b_weight', 170)), 
            axis=1
        )
        
        # Feature 1: Weight class difference (how many classes apart)
        df['weight_class_diff'] = abs(df['r_weight_class'] - df['b_weight_class'])
        
        # Feature 2: Is same weight class (binary)
        df['is_same_weight_class'] = (df['weight_class_diff'] == 0).astype(int)
        
        # Feature 3: Weight difference as percentage of lighter fighter
        df['weight_diff_percentage'] = df.apply(
            lambda row: abs(row['r_weight'] - row['b_weight']) / min(row['r_weight'], row['b_weight']) 
            if min(row['r_weight'], row['b_weight']) > 0 else 0,
            axis=1
        )
        
        # Feature 4: Height difference as percentage
        df['height_diff_percentage'] = df.apply(
            lambda row: abs(row['r_height'] - row['b_height']) / min(row['r_height'], row['b_height']) 
            if min(row['r_height'], row['b_height']) > 0 else 0,
            axis=1
        )
        
        # Feature 5: Reach difference as percentage
        df['reach_diff_percentage'] = df.apply(
            lambda row: abs(row['r_reach'] - row['b_reach']) / min(row['r_reach'], row['b_reach']) 
            if min(row['r_reach'], row['b_reach']) > 0 else 0,
            axis=1
        )
        
        # Feature 6: Is cross-gender (would need gender data - assume no for now)
        df['is_cross_gender'] = 0  # Placeholder - Kaggle data doesn't have gender easily
        
        # Feature 7: BMI difference
        # BMI = weight(lbs) / height(inches)^2 * 703
        df['r_bmi'] = (df['r_weight'] / (df['r_height'] ** 2)) * 703
        df['b_bmi'] = (df['b_weight'] / (df['b_height'] ** 2)) * 703
        df['bmi_diff'] = abs(df['r_bmi'] - df['b_bmi'])
        
        # Feature 8: Weight to height ratio difference (how "thick" the fighter is)
        df['r_weight_height_ratio'] = df['r_weight'] / df['r_height']
        df['b_weight_height_ratio'] = df['b_weight'] / df['b_height']
        df['weight_height_ratio_diff'] = abs(df['r_weight_height_ratio'] - df['b_weight_height_ratio'])
        
        # Feature 9: Realistic matchup flag (0 if >2 weight classes apart)
        df['realistic_matchup'] = (df['weight_class_diff'] <= 2).astype(int)
        
        # Feature 10: Size advantage score (composite)
        # Higher score = bigger size advantage for red fighter
        df['size_advantage_score'] = (
            (df['r_weight'] - df['b_weight']) / 100 +  # Weight advantage
            (df['r_height'] - df['b_height']) / 10 +   # Height advantage
            (df['r_reach'] - df['b_reach']) / 10       # Reach advantage
        )
        
        self.processed_data = df
        print(f"Created 10 new size/weight features")
        print(f"Sample weight classes - Red: {df['r_weight_class'].mean():.1f}, Blue: {df['b_weight_class'].mean():.1f}")
        
    def select_features(self):
        """
        Select the most important features for prediction
        NOW INCLUDING: 10 new size/weight context features
        """
        print("\nSelecting features...")
        
        # Original features + NEW size features
        feature_columns = [
            # Red fighter career stats
            'r_wins_total',
            'r_losses_total', 
            'r_age',
            'r_height',
            'r_weight',
            'r_reach',
            'r_SLpM_total',
            'r_SApM_total',
            'r_sig_str_acc_total',
            'r_td_acc_total',
            'r_str_def_total',
            'r_td_def_total',
            'r_sub_avg',
            'r_td_avg',
            
            # Blue fighter career stats
            'b_wins_total',
            'b_losses_total',
            'b_age',
            'b_height',
            'b_weight',
            'b_reach',
            'b_SLpM_total',
            'b_SApM_total',
            'b_sig_str_acc_total',
            'b_td_acc_total',
            'b_str_def_total',
            'b_td_def_total',
            'b_sub_avg',
            'b_td_avg',
            
            # Original differential features
            'wins_total_diff',
            'losses_total_diff',
            'age_diff',
            'height_diff',
            'weight_diff',
            'reach_diff',
            'SLpM_total_diff',
            'SApM_total_diff',
            'sig_str_acc_total_diff',
            'td_acc_total_diff',
            'str_def_total_diff',
            'td_def_total_diff',
            'sub_avg_diff',
            'td_avg_diff',
            
            # NEW: 10 size/weight context features
            'weight_class_diff',
            'is_same_weight_class',
            'weight_diff_percentage',
            'height_diff_percentage',
            'reach_diff_percentage',
            'is_cross_gender',
            'bmi_diff',
            'weight_height_ratio_diff',
            'realistic_matchup',
            'size_advantage_score'
        ]
        
        # Check which features are available
        available_features = [col for col in feature_columns if col in self.processed_data.columns]
        missing_features = [col for col in feature_columns if col not in self.processed_data.columns]
        
        if missing_features:
            print(f"Warning: Missing features: {missing_features}")
        
        print(f"Using {len(available_features)} features for prediction")
        
        return available_features
    
    def prepare_ml_dataset(self, test_size=0.2, random_state=42):
        """
        Prepare final dataset for machine learning
        
        Args:
            test_size: Proportion of data for testing (0.2 = 20%)
            random_state: Random seed for reproducibility
            
        Returns:
            X_train, X_test, y_train, y_test
        """
        print("\nPreparing ML dataset...")
        
        df = self.processed_data.copy()
        
        # Select features
        feature_columns = self.select_features()
        
        # Create feature matrix (X) and target vector (y)
        X = df[feature_columns]
        y = df['winner_encoded']
        
        # Remove any remaining NaN values
        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        
        # Split into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=test_size, 
            random_state=random_state,
            stratify=None  # Can't stratify with continuous values (draws)
        )
        
        print(f"Training set: {len(X_train)} fights")
        print(f"Test set: {len(X_test)} fights")
        print(f"Features: {len(feature_columns)}")
        
        # Show class distribution
        print(f"\nTarget distribution:")
        print(f"  Red wins: {(y_train == 1).sum()} ({(y_train == 1).mean()*100:.1f}%)")
        print(f"  Blue wins: {(y_train == 0).sum()} ({(y_train == 0).mean()*100:.1f}%)")
        print(f"  Draws/NC: {((y_train != 0) & (y_train != 1)).sum()}")
        
        return X_train, X_test, y_train, y_test, feature_columns
    
    def process_all(self):
        """
        Run the complete processing pipeline
        NOW WITH: Size/weight context features
        """
        print("\n" + "="*50)
        print("Starting Kaggle Data Processing")
        print("="*50)
        
        self.clean_data()
        self.create_size_features()  # NEW - Add size features
        X_train, X_test, y_train, y_test, features = self.prepare_ml_dataset()
        
        # Save processed data
        output_path = 'data/kaggle_processed.csv'
        self.processed_data.to_csv(output_path, index=False)
        print(f"\nSaved processed data to: {output_path}")
        
        print("\n" + "="*50)
        print("Processing Complete!")
        print("="*50)
        
        return X_train, X_test, y_train, y_test, features
    
    def get_feature_info(self):
        """
        Display information about the features we're using
        """
        feature_columns = self.select_features()
        
        print("\nFeature Descriptions:")
        print("-" * 50)
        
        descriptions = {
            'wins_total': 'Career wins before this fight',
            'losses_total': 'Career losses before this fight',
            'age': 'Fighter age at time of fight',
            'height': 'Fighter height in inches',
            'weight': 'Fighter weight in lbs',
            'reach': 'Fighter reach in inches',
            'SLpM_total': 'Significant strikes landed per minute',
            'SApM_total': 'Significant strikes absorbed per minute',
            'sig_str_acc_total': 'Striking accuracy percentage',
            'td_acc_total': 'Takedown accuracy percentage',
            'str_def_total': 'Striking defense percentage',
            'td_def_total': 'Takedown defense percentage',
            'sub_avg': 'Submission attempts per fight',
            'td_avg': 'Takedowns per fight'
        }
        
        for feat in feature_columns:
            # Get base feature name (remove r_, b_, or _diff)
            base = feat.replace('r_', '').replace('b_', '').replace('_diff', '')
            desc = descriptions.get(base, 'Statistical comparison')
            
            if feat.startswith('r_'):
                print(f"  {feat}: Red fighter - {desc}")
            elif feat.startswith('b_'):
                print(f"  {feat}: Blue fighter - {desc}")
            elif feat.endswith('_diff'):
                print(f"  {feat}: Differential - {desc}")


if __name__ == "__main__":
    # Run the processor
    processor = KaggleUFCProcessor('data/large_dataset.csv')
    X_train, X_test, y_train, y_test, features = processor.process_all()
    
    print("\nData Preview:")
    print(X_train.head())
    
    # Show feature info
    processor.get_feature_info()