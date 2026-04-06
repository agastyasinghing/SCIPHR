import React, { useState, useEffect } from 'react';
import Card from '../shared/Card';
import Button from '../shared/Button';
import './HeroFightCard.css';
import { getFighterImage } from '../../utils/imageUtils';

/**
 * Hero Fight Card Component
 * Displays the next main event. Accepts real event data from Dashboard.jsx.
 * Falls back to empty state when no event is provided.
 */
const HeroFightCard = ({ event }) => {
  const [timeUntil, setTimeUntil] = useState('');

  // Shape the event prop into the expected fight structure.
  // event comes from GET /events/upcoming → events_data[0]
  const mainCard = event?.fights?.[0] ?? null;
  const fight = mainCard
    ? {
        eventName: event.name ?? 'UFC Event',
        location: event.location ?? '',
        date: event.date ? new Date(event.date) : new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
        fighter1: { name: mainCard.r_fighter ?? mainCard.fighter1 ?? 'TBA', record: '' },
        fighter2: { name: mainCard.b_fighter ?? mainCard.fighter2 ?? 'TBA', record: '' },
        confidence: 'PENDING',
        dataPoints: null,
        valueBet: { hasValue: false },
        analysisUpdated: null,
      }
    : null;
  
  // Calculate countdown — must be called unconditionally (Rules of Hooks)
  useEffect(() => {
    if (!fight) return;

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
  }, [fight?.date]);

  // Early return after all hooks
  if (!fight) {
    return (
      <div className="hero-fight-card hero-fight-card--empty">
        <p>No upcoming events found. Check back soon.</p>
      </div>
    );
  }

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
                  src={getFighterImage(fight.fighter1.name, '')}
                  alt={fight.fighter1.name}
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
                  src={getFighterImage(fight.fighter2.name, '')}
                  alt={fight.fighter2.name}
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
        
        {/* Prediction Section — only shown when prediction data is available */}
        {fight.fighter1.prediction != null && (
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
            <span className={`confidence-badge confidence-${fight.confidence.toLowerCase().replace('-', '')}`}>
              🔥 Confidence: {fight.confidence}
            </span>
          </div>
        </div>
        )}
        
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
