import React from 'react';
import Card from '../shared/Card';
import './HotTakes.css';

/**
 * Hot Takes Component
 * Shows fights where SCIPHR disagrees significantly with Vegas odds
 */
const HotTakes = () => {
  // Mock data - we'll replace with real data later
  const hotTakes = [
    {
      id: 1,
      fighter1: 'Charles Oliveira',
      fighter2: 'Islam Makhachev',
      scipherPick: 'Charles Oliveira',
      scipherConfidence: 72,
      vegasOdds: 28,
      difference: 44,
      event: 'UFC 294',
      reasoning: 'Model sees massive value - Oliveira\'s submission game underrated',
    },
    {
      id: 2,
      fighter1: 'Sean O\'Malley',
      fighter2: 'Merab Dvalishvili',
      scipherPick: 'Merab Dvalishvili',
      scipherConfidence: 68,
      vegasOdds: 35,
      difference: 33,
      event: 'UFC 306',
      reasoning: 'Wrestling advantage heavily undervalued by bookmakers',
    },
    {
      id: 3,
      fighter1: 'Alexandre Pantoja',
      fighter2: 'Kai Kara-France',
      scipherPick: 'Kai Kara-France',
      scipherConfidence: 65,
      vegasOdds: 40,
      difference: 25,
      event: 'UFC Fight Night',
      reasoning: 'Striking differential and recent form trending upward',
    },
  ];
  
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