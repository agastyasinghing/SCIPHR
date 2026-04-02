"""
Feature Engine - Main Orchestrator
Combines all feature engineering modules
"""

import pandas as pd
import numpy as np
from .physical_features import PhysicalFeatureEngineer
from .career_features import CareerFeatureEngineer
from .recent_form_features import RecentFormFeatureEngineer

class UFCFeatureEngine:
    """
    Main feature engineering engine
    Orchestrates all feature creation modules
    """
    
    def __init__(self):
        self.physical_engineer = PhysicalFeatureEngineer()
        self.career_engineer = CareerFeatureEngineer()
        self.recent_form_engineer = RecentFormFeatureEngineer()
        
        self.feature_count = 0
        self.feature_names = []
    
    def create_all_features(self, df):
        """
        Create all features using all modules
        
        Args:
            df: Raw DataFrame with basic fighter stats
            
        Returns:
            DataFrame with all engineered features
        """
        print("\n" + "="*70)
        print("UFC FEATURE ENGINE - GENERATING ALL FEATURES")
        print("="*70)
        print(f"Input shape: {df.shape}")
        print(f"Input columns: {len(df.columns)}")
        
        result_df = df.copy()
        
        # Track original columns
        original_columns = set(df.columns)
        
        # ============ MODULE 1: PHYSICAL FEATURES ============
        print("\n" + "="*70)
        print("MODULE 1: PHYSICAL FEATURES")
        print("="*70)
        result_df = self.physical_engineer.create_features(result_df)
        physical_features = set(result_df.columns) - original_columns
        print(f"✓ Added {len(physical_features)} physical features")
        
        # ============ MODULE 2: CAREER FEATURES ============
        print("\n" + "="*70)
        print("MODULE 2: CAREER FEATURES")
        print("="*70)
        before_career = set(result_df.columns)
        result_df = self.career_engineer.create_features(result_df)
        career_features = set(result_df.columns) - before_career
        print(f"✓ Added {len(career_features)} career features")
        
        # ============ MODULE 3: RECENT FORM FEATURES ============
        print("\n" + "="*70)
        print("MODULE 3: RECENT FORM FEATURES")
        print("="*70)
        before_form = set(result_df.columns)
        result_df = self.recent_form_engineer.create_features(result_df)
        form_features = set(result_df.columns) - before_form
        print(f"✓ Added {len(form_features)} recent form features")
        
        # ============ SUMMARY ============
        total_new_features = len(set(result_df.columns) - original_columns)
        self.feature_count = total_new_features
        self.feature_names = list(set(result_df.columns) - original_columns)
        
        print("\n" + "="*70)
        print("FEATURE ENGINEERING COMPLETE")
        print("="*70)
        print(f"Original features: {len(original_columns)}")
        print(f"New features created: {total_new_features}")
        print(f"Total features: {len(result_df.columns)}")
        print(f"\nBreakdown:")
        print(f"  Physical features: {len(physical_features)}")
        print(f"  Career features: {len(career_features)}")
        print(f"  Recent form features: {len(form_features)}")
        print("="*70)
        
        return result_df
    
    def get_feature_names(self):
        """Return list of all created feature names"""
        return self.feature_names
    
    def get_feature_count(self):
        """Return total count of created features"""
        return self.feature_count
    
    def get_feature_summary(self):
        """Return summary of feature creation"""
        return {
            'total_features': self.feature_count,
            'feature_names': self.feature_names,
            'modules': {
                'physical': 50,
                'career': 80,
                'recent_form': 60
            }
        }