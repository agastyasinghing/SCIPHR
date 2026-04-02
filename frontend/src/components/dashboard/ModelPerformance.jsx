import React from 'react';
import Card from '../shared/Card';
import './ModelPerformance.css';

/**
 * Model Performance Component
 * Shows accuracy metrics for different prediction models
 */
const ModelPerformance = () => {
  const models = [
    {
      id: 'quality',
      name: 'Quality-1',
      icon: '🏆',
      accuracy: 85.2,
      tier: 'ELITE ONLY',
      color: 'yellow',
      description: 'Premium accuracy model focusing on highest win rate',
      predictions: 247,
    },
    {
      id: 'balanced',
      name: 'Balanced-1',
      icon: '⭐',
      accuracy: 78.4,
      tier: 'ELITE ONLY',
      color: 'cyan',
      description: 'Balanced approach for consistent predictions',
      predictions: 523,
    },
    {
      id: 'volume',
      name: 'Volume-1',
      icon: '⚡',
      accuracy: 64.8,
      tier: 'ELITE & PRO',
      color: 'gray',
      description: 'Maximum coverage across all fights',
      predictions: 1247,
    },
  ];
  
  return (
    <div className="model-performance-section">
      {/* Performance Chart Placeholder */}
      <Card variant="glass" className="performance-chart-card">
        <div className="chart-header">
          <div className="chart-title">
            <h4>12-Month Performance Trend</h4>
            <p>Based on 1,247 fight predictions with trailing average</p>
          </div>
          <select className="time-range-select">
            <option value="12">12-month</option>
            <option value="6">6-month</option>
            <option value="3">3-month</option>
          </select>
        </div>
        
        {/* Simplified Chart Visualization */}
        <div className="chart-visualization">
          <div className="chart-legend">
            <div className="legend-item quality">
              <span className="legend-dot"></span>
              <span>Quality</span>
            </div>
            <div className="legend-item balanced">
              <span className="legend-dot"></span>
              <span>Balanced</span>
            </div>
            <div className="legend-item volume">
              <span className="legend-dot"></span>
              <span>Volume</span>
            </div>
          </div>
          
          {/* Mock Chart Lines */}
          <div className="chart-area">
            <div className="chart-line quality-line"></div>
            <div className="chart-line balanced-line"></div>
            <div className="chart-line volume-line"></div>
            <div className="chart-placeholder">
              <p>📊 Interactive chart coming soon</p>
              <p className="chart-note">Will show accuracy trends over time</p>
            </div>
          </div>
        </div>
      </Card>
      
      {/* Model Cards */}
      <div className="models-grid">
        {models.map((model) => (
          <Card 
            key={model.id}
            variant="glass"
            hover={true}
            className={`model-card model-${model.color}`}
          >
            <div className="model-header">
              <span className="model-icon">{model.icon}</span>
              <div className="model-info">
                <h4 className="model-name">{model.name}</h4>
                <span className="model-tier">{model.tier}</span>
              </div>
            </div>
            
            <div className="model-accuracy">
              <div className="accuracy-value">{model.accuracy}%</div>
              <div className="accuracy-label">AVERAGE ACCURACY</div>
            </div>
            
            <div className="model-description">
              {model.description}
            </div>
            
            <div className="model-stats">
              <div className="stat-item">
                <span className="stat-value">{model.predictions}</span>
                <span className="stat-label">Predictions</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">12mo</span>
                <span className="stat-label">Period</span>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default ModelPerformance;