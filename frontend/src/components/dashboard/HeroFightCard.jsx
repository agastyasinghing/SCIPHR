import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api/api';
import Card from '../shared/Card';
import Button from '../shared/Button';
import './HeroFightCard.css';
import { getFighterImage } from '../../utils/imageUtils';

/**
 * Hero Fight Card Component
 * Displays the next main event.  Fetches a simple (non-logging) model prediction
 * on mount so the confidence bar renders live without polluting predictions_log.
 */
const HeroFightCard = ({ event }) => {
  const navigate = useNavigate();
  const [timeUntil, setTimeUntil]           = useState('');
  const [prediction, setPrediction]         = useState(null);
  const [predLoading, setPredLoading]       = useState(false);

  const mainCard = event?.fights?.[0] ?? null;
  const fight = mainCard
    ? {
        eventName: event.name ?? 'UFC Event',
        eventId:   event.event_id ?? null,
        location:  event.location ?? '',
        date:      event.date ? new Date(event.date) : new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
        fighter1:  { name: mainCard.r_fighter ?? mainCard.fighter1 ?? 'TBA' },
        fighter2:  { name: mainCard.b_fighter ?? mainCard.fighter2 ?? 'TBA' },
        cardTemperature: event.card_temperature ?? null,
      }
    : null;

  // Countdown timer
  useEffect(() => {
    if (!fight) return;
    const calc = () => {
      const diff = fight.date - new Date();
      if (diff <= 0) { setTimeUntil('LIVE NOW'); return; }
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      setTimeUntil(`${d}d ${h}h ${m}m`);
    };
    calc();
    const id = setInterval(calc, 60000);
    return () => clearInterval(id);
  }, [fight?.date]);

  // Fetch prediction for main event fight
  useEffect(() => {
    if (!fight) return;
    const f1 = fight.fighter1.name;
    const f2 = fight.fighter2.name;
    if (f1 === 'TBA' || f2 === 'TBA' || !f1 || !f2) return;

    setPredLoading(true);
    api.predictSimple(f1, f2)
      .then(res => setPrediction(res))
      .catch(() => setPrediction(null))
      .finally(() => setPredLoading(false));
  }, [fight?.fighter1?.name, fight?.fighter2?.name]);

  if (!fight) {
    return (
      <div className="hero-fight-card hero-fight-card--empty">
        <p>No upcoming events found. Check back soon.</p>
      </div>
    );
  }

  const probF1 = prediction ? (prediction.prob_fighter1 * 100).toFixed(1) : null;
  const probF2 = prediction ? (prediction.prob_fighter2 * 100).toFixed(1) : null;

  const cardTempLabel = fight.cardTemperature;
  const cardTempColor = {
    'CHALK CARD': '#10B981',
    'MIXED CARD': '#F59E0B',
    'CHAOS CARD': '#EF4444',
    'DOG CARD':   '#F97316',
  }[cardTempLabel] || '#6B7280';

  return (
    <div className="hero-fight-card">
      {/* Header */}
      <div className="hero-header">
        <div className="hero-countdown">
          <span className="countdown-icon">⏰</span>
          <span className="countdown-text">Next main event in</span>
          <span className="countdown-time">{timeUntil}</span>
        </div>

        <div className="hero-stats">
          {cardTempLabel && (
            <div className="stat-badge" style={{ borderColor: cardTempColor, color: cardTempColor }}>
              <span className="stat-icon">🌡️</span>
              <span>{cardTempLabel}</span>
            </div>
          )}
        </div>
      </div>

      {/* Event title */}
      <div className="hero-event-title">
        <h2>{fight.eventName}</h2>
        {fight.location && (
          <p className="event-location">
            <span className="location-icon">📍</span>
            {fight.location}
          </p>
        )}
      </div>

      {/* Main fight card */}
      <Card variant="elevated" className="hero-main-card">
        <div className="fighters-container">
          {/* Fighter 1 */}
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
              </div>
            </div>
          </div>

          {/* VS */}
          <div className="vs-divider">
            <div className="vs-circle"><span className="vs-text">VS</span></div>
          </div>

          {/* Fighter 2 */}
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
              </div>
            </div>
          </div>
        </div>

        {/* Prediction bar */}
        {predLoading && (
          <div className="prediction-loading">
            <span>Loading SCIPHR prediction...</span>
          </div>
        )}

        {prediction && probF1 !== null && (
          <div className="prediction-section">
            <div className="prediction-bar">
              <div className="prediction-fill prediction-fill-red" style={{ width: `${probF1}%` }}>
                <span className="prediction-percentage">{probF1}%</span>
              </div>
              <div className="prediction-fill prediction-fill-blue" style={{ width: `${probF2}%` }}>
                <span className="prediction-percentage">{probF2}%</span>
              </div>
            </div>
            <div className="prediction-labels">
              <span className="prediction-label">📊 SCIPHR PREDICTION</span>
              <span className="prediction-winner">
                {prediction.winner} · {(prediction.confidence * 100).toFixed(1)}% confidence
              </span>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="hero-actions">
          <Button
            variant="primary"
            icon={<span>🔮</span>}
            onClick={() =>
              navigate(`/picks?fighter1=${encodeURIComponent(fight.fighter1.name)}&fighter2=${encodeURIComponent(fight.fighter2.name)}`)
            }
          >
            Analyze this fight
          </Button>
          <Button
            variant="ghost"
            icon={<span>👁️</span>}
            onClick={() => navigate(`/fighter/${encodeURIComponent(fight.fighter1.name)}`)}
          >
            {fight.fighter1.name.split(' ').pop()}
          </Button>
          <Button
            variant="ghost"
            icon={<span>👁️</span>}
            onClick={() => navigate(`/fighter/${encodeURIComponent(fight.fighter2.name)}`)}
          >
            {fight.fighter2.name.split(' ').pop()}
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default HeroFightCard;
