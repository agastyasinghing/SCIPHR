import React from 'react';
import Card from '../shared/Card';
import hotTakesData from '../../data/hot-takes.json';
import './HotTakes.css';

/**
 * Hot Takes Component
 * Shows fights where SCIPHR disagrees significantly with Vegas odds.
 * Data is curated editorially each fight week in src/data/hot-takes.json.
 */
const HotTakes = () => {
  const hotTakes = hotTakesData;
  
  return (
    <div className="hot-takes-section">
      <div className="hot-takes-grid">
        {hotTakes.map((take) => (
          <Card 
            key={take.id} 
            variant="glass" 
            hover={true}
            className="hot-take-card"
          >
            {/* Difference Badge */}
            <div className="difference-badge">
              <span className="difference-icon">⚡</span>
              <span className="difference-value">+{take.difference}%</span>
              <span className="difference-label">VALUE</span>
            </div>
            
            {/* Fight Matchup */}
            <div className="hot-take-matchup">
              <div className="matchup-fighters">
                <span className="fighter-name">{take.fighter1}</span>
                <span className="vs-text">VS</span>
                <span className="fighter-name">{take.fighter2}</span>
              </div>
              <div className="matchup-event">{take.event}</div>
            </div>
            
            {/* Predictions Comparison */}
            <div className="predictions-comparison">
              <div className="prediction-row sciphr-prediction">
                <div className="prediction-label">
                  <span className="label-icon">🤖</span>
                  <span>SCIPHR</span>
                </div>
                <div className="prediction-bar-container">
                  <div 
                    className="prediction-bar sciphr-bar"
                    style={{ width: `${take.scipherConfidence}%` }}
                  ></div>
                  <span className="prediction-value">{take.scipherConfidence}%</span>
                </div>
              </div>
              
              <div className="prediction-row vegas-prediction">
                <div className="prediction-label">
                  <span className="label-icon">🎰</span>
                  <span>Vegas</span>
                </div>
                <div className="prediction-bar-container">
                  <div 
                    className="prediction-bar vegas-bar"
                    style={{ width: `${take.vegasOdds}%` }}
                  ></div>
                  <span className="prediction-value">{take.vegasOdds}%</span>
                </div>
              </div>
            </div>
            
            {/* Pick */}
            <div className="hot-take-pick">
              <span className="pick-label">OUR PICK:</span>
              <span className="pick-fighter">{take.scipherPick}</span>
            </div>
            
            {/* Reasoning */}
            <div className="hot-take-reasoning">
              <p>{take.reasoning}</p>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default HotTakes;