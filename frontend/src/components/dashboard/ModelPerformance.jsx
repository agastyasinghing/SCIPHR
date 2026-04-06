import React from 'react';
import Card from '../shared/Card';
import './ModelPerformance.css';

/**
 * Model Performance Component
 * Shows accuracy metrics for the SCIPHR XGBoost model.
 * Static values until /historical-scorecard is seeded (TODO-10).
 */
const ModelPerformance = () => {
  const stats = [
    { label: 'Test Accuracy', value: '85.7%', note: 'held-out test set' },
    { label: 'Training Fights', value: '8,231', note: 'historical UFC bouts' },
    { label: 'Features', value: '5,401', note: 'per-fight feature vector' },
    { label: 'Algorithm', value: 'XGBoost', note: 'gradient boosted trees' },
  ];

  return (
    <div className="model-performance-section">
      <Card variant="glass" className="performance-chart-card">
        <div className="chart-header">
          <div className="chart-title">
            <h4>SCIPHR Model v1</h4>
            <p>XGBoost classifier trained on 8,231 UFC fights</p>
          </div>
        </div>

        <div className="model-stats-grid">
          {stats.map((s) => (
            <div key={s.label} className="model-stat-card">
              <div className="model-stat-value">{s.value}</div>
              <div className="model-stat-label">{s.label}</div>
              <div className="model-stat-note">{s.note}</div>
            </div>
          ))}
        </div>

        <div className="chart-placeholder">
          <p>Live accuracy tracking enabled after fight week</p>
          <p className="chart-note">Historical scorecard records every pick</p>
        </div>
      </Card>
    </div>
  );
};

export default ModelPerformance;