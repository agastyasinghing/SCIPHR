import React, { useState, useEffect } from 'react';
import Card from '../shared/Card';
import Button from '../shared/Button';
import './HeroFightCard.css';
import { getFighterImage } from '../../utils/imageUtils';

/**
 * Hero Fight Card Component
 * Displays the next main event with fighter matchup, predictions, and value indicators
 */
const HeroFightCard = ({ fightData }) => {
  const [timeUntil, setTimeUntil] = useState('');
  
  // Mock data if none provided
  const defaultFight = {
    eventName: 'UFC 323',
    location: 'Las Vegas, USA',
    date: new Date(Date.now() + 12 * 24 * 60 * 60 * 1000), // 12 days from now
    fighter1: {
      name: 'Merab Dvalishvili',
      image: '/fighters/merab.jpg',
      record: '17-4-0',
      prediction: 68.3,
    },
    fighter2: {
      name: 'Petr Yan',
      image: '/fighters/yan.jpg',
      record: '16-5-0',
      prediction: 31.7,
    },
    confidence: 'MEDIUM-HIGH',
    dataPoints: 842,
    valueBet: {
      hasValue: true,
      percentage: 15,
      fighter: 'fighter1',
    },
    analysisUpdated: '21h ago',
  };
  
  const fight = fightData || defaultFight;
  
  // Calculate countdown
  useEffect(() => {
    const calculateTimeUntil = () => {
      const now = new Date();
      const diff = fight.date - now;
      
      if (diff <= 0) {
        setTimeUntil('LIVE NOW');
        return;
      }
      
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      
      setTimeUntil(`${days}d ${hours}h ${minutes}m`);
    };
    
    calculateTimeUntil();
    const interval = setInterval(calculateTimeUntil, 60000); // Update every minute
    
    return () => clearInterval(interval);
  }, [fight.date]);
  
  // Determine value bet text
  const getValueBetText = () => {
    if (!fight.valueBet.hasValue) return null;
    
    const fighter = fight.valueBet.fighter === 'fighter1' ? fight.fighter1.name : fight.fighter2.name;
    return `+${fight.valueBet.percentage}% vs Vegas odds - ${fighter} undervalued!`;
  };
  
  return (
    <div className="hero-fight-card">
      {/* Header with countdown and stats */}
      <div className="hero-header">
        <div className="hero-countdown">
          <span className="countdown-icon">⏰</span>
          <span className="countdown-text">Next main event in</span>
          <span className="countdown-time">{timeUntil}</span>
        </div>
        
        <div className="hero-stats">
          <div className="stat-badge stat-new">
            <span className="stat-icon">✅</span>
            <span>New analysis {fight.analysisUpdated}</span>
          </div>
          <div className="stat-badge stat-data">
            <span className="stat-icon">📊</span>
            <span>{fight.dataPoints} data points</span>
          </div>
        </div>
      </div>
      
      {/* Event title */}
      <div className="hero-event-title">
        <h2>{fight.eventName}</h2>
        <p className="event-location">
          <span className="location-icon">📍</span>
          {fight.location}
        </p>
      </div>
      
      {/* Main fight card */}
      <Card variant="elevated" className="hero-main-card">
        <div className="fighters-container">
          {/* Fighter 1 (Red Corner) */}
          <div className="fighter fighter-red">
            <div className="fighter-gradient gradient-fighter-red">
              <div className="fighter-image-container">
                <img 
                  src={getFighterImage('Merab Dvalishvili', 'Bantamweight')}
                  alt="Merab Dvalishvili"
                  className="fighter-image"
                />
                
              </div>
              <div className="fighter-info">
                <h3 className="fighter-name">{fight.fighter1.name}</h3>
                <p className="fighter-record">{fight.fighter1.record}</p>
              </div>
            </div>
          </div>
          
          {/* VS Divider */}
          <div className="vs-divider">
            <div className="vs-circle">
              <span className="vs-text">VS</span>
            </div>
          </div>
          
          {/* Fighter 2 (Blue Corner) */}
          <div className="fighter fighter-blue">
            <div className="fighter-gradient gradient-fighter-blue">
              <div className="fighter-image-container">
                <img 
                  src={getFighterImage('Petr Yan', 'Bantamweight')}
                  alt="Petr Yan"
                  className="fighter-image"
                />
              </div>
              <div className="fighter-info">
                <h3 className="fighter-name">{fight.fighter2.name}</h3>
                <p className="fighter-record">{fight.fighter2.record}</p>
              </div>
            </div>
          </div>
        </div>
        
        {/* Prediction Section */}
        <div className="prediction-section">
          <div className="prediction-bar">
            <div 
              className="prediction-fill prediction-fill-red"
              style={{ width: `${fight.fighter1.prediction}%` }}
            >
              <span className="prediction-percentage">{fight.fighter1.prediction.toFixed(1)}%</span>
            </div>
            <div 
              className="prediction-fill prediction-fill-blue"
              style={{ width: `${fight.fighter2.prediction}%` }}
            >
              <span className="prediction-percentage">{fight.fighter2.prediction.toFixed(1)}%</span>
            </div>
          </div>
          
          <div className="prediction-labels">
            <span className="prediction-label">📊 SCIPHR PREDICTION</span>
            <span className="confidence-badge confidence-{fight.confidence.toLowerCase().replace('-', '')}">
              🔥 Confidence: {fight.confidence}
            </span>
          </div>
        </div>
        
        {/* Value Bet Indicator (NEW - Our Edge!) */}
        {fight.valueBet.hasValue && (
          <div className="value-bet-indicator animate-pulse">
            <span className="value-icon">💰</span>
            <span className="value-text">VALUE BET:</span>
            <span className="value-detail">{getValueBetText()}</span>
          </div>
        )}
        
        {/* Action Buttons */}
        <div className="hero-actions">
          <Button 
            variant="ghost" 
            icon={<span>👁️</span>}
            onClick={() => console.log('View Event')}
          >
            View Event
          </Button>
          <Button 
            variant="ghost" 
            icon={<span>📡</span>}
            onClick={() => console.log('View Signals')}
          >
            View Signals
          </Button>
          <Button 
            variant="ghost" 
            icon={<span>⚖️</span>}
            onClick={() => console.log('Compare Fighters')}
          >
            Compare Fighters
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default HeroFightCard;
