"""
Kaggle UFC Data Processor V2
Uses advanced feature engineering with 190+ features
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from features.feature_engine import UFCFeatureEngine

class KaggleUFCProcessorV2:
    """
    Advanced processor with comprehensive feature engineering
    """
    
    def __init__(self, data_path='data/large_dataset.csv'):
        """
        Initialize processor and load data
        
        Args:
            data_path: Path to the Kaggle CSV file
        """
        print("="*70)
        print("KAGGLE UFC DATA PROCESSOR V2")
        print("Advanced Feature Engineering System")
        print("="*70)
        
        print("\nLoading data...")
        self.raw_data = pd.read_csv(data_path)
        print(f"✓ Loaded {len(self.raw_data)} fights")
        print(f"✓ Original columns: {len(self.raw_data.columns)}")
        
        self.processed_data = None
        self.feature_engine = UFCFeatureEngine()
        
    def clean_data(self):
        """
        Clean and prepare the data
        """
        print("\n" + "="*70)
        print("DATA CLEANING")
        print("="*70)
        
        df = self.raw_data.copy()
        
        # Convert winner to numeric
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
        initial_count = len(df)
        df = df.dropna(subset=['winner_encoded'])
        print(f"✓ Removed {initial_count - len(df)} fights with missing winner")
        
        # Fill missing numeric values with 0
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].fillna(0)
        
        # Remove any remaining rows with critical missing data
        critical_cols = ['r_fighter', 'b_fighter', 'winner_encoded', 
                        'r_weight', 'b_weight', 'r_height', 'b_height']
        available_critical = [col for col in critical_cols if col in df.columns]
        df = df.dropna(subset=available_critical)
        
        print(f"✓ Final dataset: {len(df)} fights")
        print("="*70)
        
        self.processed_data = df
        
    def create_features(self):
        """
    Create all advanced features using feature engine
    """
        if self.processed_data is None:
            raise ValueError("Must run clean_data() first")
    
        self.processed_data = self.feature_engine.create_all_features(self.processed_data)
    
        # NUCLEAR FIX: Fill ALL NaN values with 0
        print("\n🔧 Filling ALL NaN values...")
        self.processed_data = self.processed_data.fillna(0)
        print(f"✓ Filled all NaN values with 0")
        
    def add_synthetic_data(self):
        """
        Add synthetic impossible matchup data to teach weight dominance
        """
        print("\n" + "="*70)
        print("ADDING SYNTHETIC TRAINING DATA")
        print("="*70)
        
        from synthetic_data_generator import generate_impossible_matchups
        
        # Generate synthetic data
        synthetic_df = generate_impossible_matchups(n_samples=2000)
        
        # Combine with real data
        original_count = len(self.processed_data)
        self.processed_data = pd.concat([self.processed_data, synthetic_df], ignore_index=True)
        
        print(f"✓ Added {len(synthetic_df)} synthetic examples")
        print(f"✓ Total dataset: {len(self.processed_data)} fights")
        print(f"  Real: {original_count}")
        print(f"  Synthetic: {len(synthetic_df)}")
        print("="*70)
        
    def select_features_for_ml(self):
        """
        Select features for machine learning
        Returns list of feature column names
        """
        print("\n" + "="*70)
        print("SELECTING FEATURES FOR ML")
        print("="*70)
        
        # Get all numeric columns except identifiers and target
        exclude_cols = [
            'winner', 'winner_encoded', 'r_fighter', 'b_fighter',
            'date', 'location', 'event', 'fight_type',
            'r_career_stage', 'b_career_stage',
            # CRITICAL: Exclude all OUTCOME features (only known AFTER fight)
            'finish_round', 'finish', 'finish_details',
            'total_rounds', 'time_sec', 'time_format',
            'is_title_bout', 'win_by', 'last_round', 'format',
            # Exclude in-fight statistics (only known AFTER fight)
            'kd', 'kd_diff', 'r_kd', 'b_kd',
            'sig_str', 'sig_str_diff', 'r_sig_str', 'b_sig_str',
            'sig_str_att', 'sig_str_att_diff', 'r_sig_str_att', 'b_sig_str_att',
            'sig_str_acc', 'sig_str_acc_diff', 'r_sig_str_acc', 'b_sig_str_acc',
            'str', 'str_diff', 'r_str', 'b_str',
            'str_att', 'str_att_diff', 'r_str_att', 'b_str_att',
            'td', 'td_diff', 'r_td', 'b_td',
            'td_att', 'td_att_diff', 'r_td_att', 'b_td_att',
            'td_acc', 'td_acc_diff', 'r_td_acc', 'b_td_acc',
            'sub_att', 'sub_att_diff', 'r_sub_att', 'b_sub_att',
            'pass', 'pass_diff', 'r_pass', 'b_pass',
            'rev', 'rev_diff', 'r_rev', 'b_rev',
            'head', 'head_diff', 'r_head', 'b_head',
            'body', 'body_diff', 'r_body', 'b_body',
            'leg', 'leg_diff', 'r_leg', 'b_leg',
            'distance', 'distance_diff', 'r_distance', 'b_distance',
            'clinch', 'clinch_diff', 'r_clinch', 'b_clinch',
            'ground', 'ground_diff', 'r_ground', 'b_ground',
            'ctrl', 'ctrl_diff', 'r_ctrl', 'b_ctrl',
            'total_strikes', 'total_strikes_att'
        ]
        
        
        numeric_cols = self.processed_data.select_dtypes(include=[np.number]).columns
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]
        
        # Remove any columns with all NaN or all same value
        valid_features = []
        for col in feature_cols:
            if self.processed_data[col].nunique() > 1 and not self.processed_data[col].isna().all():
                valid_features.append(col)
        
        print(f"✓ Total numeric columns: {len(numeric_cols)}")
        print(f"✓ Valid features for ML: {len(valid_features)}")
        print(f"✓ Excluded columns: {len(feature_cols) - len(valid_features)}")
        print("="*70)
        
        return valid_features
    
    def prepare_ml_dataset(self, test_size=0.2, random_state=42):
        """
        Prepare final dataset for machine learning
        
        Args:
            test_size: Proportion of data for testing
            random_state: Random seed
            
        Returns:
            X_train, X_test, y_train, y_test, feature_names
        """
        print("\n" + "="*70)
        print("PREPARING ML DATASET")
        print("="*70)
        
        df = self.processed_data.copy()
        
        # Select features
        feature_columns = self.select_features_for_ml()
        
        # Create feature matrix (X) and target vector (y)
        X = df[feature_columns]
        y = df['winner_encoded']
        
        # DEBUG: Find which columns have NaN
        print(f"\n🔍 DEBUGGING NaN VALUES:")
        nan_cols = X.columns[X.isna().any()].tolist()
        print(f"Columns with NaN: {len(nan_cols)}")
        if nan_cols:
            print("First 10 columns with NaN:")
            for col in nan_cols[:10]:
                nan_count = X[col].isna().sum()
                print(f"  {col}: {nan_count} NaN values ({nan_count/len(X)*100:.1f}%)")
        
        # Remove any remaining NaN values
        print(f"\nBefore NaN removal: {len(X)} samples")
        print(f"Rows with NaN in X: {X.isna().any(axis=1).sum()}")
        print(f"Rows with NaN in y: {y.isna().sum()}")

        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]

        print(f"After NaN removal: {len(X)} samples")
        
        # Replace any inf values with large numbers
        X = X.replace([np.inf, -np.inf], [999999, -999999])
        
        print(f"✓ Feature matrix shape: {X.shape}")
        print(f"✓ Features: {len(feature_columns)}")
        print(f"✓ Samples: {len(X)}")
        
        # Split into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=test_size, 
            random_state=random_state,
            stratify=None
        )
        
        print(f"\n✓ Training set: {len(X_train)} fights")
        print(f"✓ Test set: {len(X_test)} fights")
        
        # Show class distribution
        print(f"\nTarget distribution:")
        print(f"  Red wins: {(y_train == 1).sum()} ({(y_train == 1).mean()*100:.1f}%)")
        print(f"  Blue wins: {(y_train == 0).sum()} ({(y_train == 0).mean()*100:.1f}%)")
        print(f"  Draws/NC: {((y_train != 0) & (y_train != 1)).sum()}")
        print("="*70)
        
        return X_train, X_test, y_train, y_test, feature_columns
    
    def process_all(self):
        
        print("\n" + "="*70)
        print("STARTING FULL PROCESSING PIPELINE")
        print("="*70)
        
        # Step 1: Clean data
        self.clean_data()
        
        # Step 1.5: ADD SYNTHETIC DATA (NEW!)
        self.add_synthetic_data()
        
        # Step 2: Create features
        self.create_features()
        
        # Step 3: Prepare ML dataset
        X_train, X_test, y_train, y_test, features = self.prepare_ml_dataset()
        
        # Save processed data
        output_path = 'data/kaggle_processed_v2.csv'
        self.processed_data.to_csv(output_path, index=False)
        print(f"\n✓ Saved processed data to: {output_path}")
        
        print("\n" + "="*70)
        print("PROCESSING COMPLETE!")
        print("="*70)
        print(f"✓ Total features created: {len(features)}")
        print(f"✓ Ready for model training")
        print("="*70)
        
        return X_train, X_test, y_train, y_test, features
    
    def get_feature_info(self):
        """
        Display information about features
        """
        summary = self.feature_engine.get_feature_summary()
        
        print("\n" + "="*70)
        print("FEATURE ENGINEERING SUMMARY")
        print("="*70)
        print(f"Total features created: {summary['total_features']}")
        print(f"\nBy module:")
        for module, count in summary['modules'].items():
            print(f"  {module}: {count} features")
        print("="*70)


if __name__ == "__main__":
    # Test the new processor
    print("\n" + "="*70)
    print("TESTING KAGGLE UFC PROCESSOR V2")
    print("="*70)
    
    processor = KaggleUFCProcessorV2('data/large_dataset.csv')
    X_train, X_test, y_train, y_test, features = processor.process_all()
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print(f"Training data shape: {X_train.shape}")
    print(f"Test data shape: {X_test.shape}")
    print(f"\nFirst 10 features:")
    for i, feat in enumerate(features[:10], 1):
        print(f"  {i}. {feat}")
    
    # Show feature info
    processor.get_feature_info()