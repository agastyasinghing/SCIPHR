import React from 'react';
import Card from '../shared/Card';
import './UpcomingFights.css';

/**
 * Upcoming Fights Component
 * Accepts events array from Dashboard.jsx (lifted state).
 * Falls back to empty state when no events are available.
 */
const UpcomingFights = ({ events = [] }) => {
  if (events.length === 0) {
    return (
      <div className="upcoming-fights-section upcoming-fights-section--empty">
        <p>No upcoming fights scheduled. Check back fight week.</p>
      </div>
    );
  }

  const upcomingFights = events.map((event) => {
    const main = event.fights?.[0];
    return {
      id: event.id,
      event: event.name,
      date: event.date ?? '',
      location: event.location ?? '',
      mainEvent: {
        fighter1: main?.r_fighter ?? main?.fighter1 ?? 'TBA',
        fighter2: main?.b_fighter ?? main?.fighter2 ?? 'TBA',
        prediction1: null,
        prediction2: null,
      },
      image: event.image ?? null,
      isTitle: event.is_title_fight ?? false,
    };
  });
  
  return (
    <div className="upcoming-fights-section">
      <div className="upcoming-fights-grid">
        {upcomingFights.map((fight) => (
          <Card 
            key={fight.id}
            variant="glass"
            hover={true}
            className="upcoming-fight-card"
          >
            {/* Event Image/Background */}
            <div className="fight-card-header">
              <div 
                className="fight-card-bg"
                style={{ 
                  backgroundImage: `url(${fight.image})`,
                  backgroundColor: '#1A1F2E' 
                }}
              ></div>
              {fight.isTitle && (
                <div className="title-badge">
                  <span className="title-icon">🏆</span>
                  <span>TITLE BOUT</span>
                </div>
              )}
            </div>
            
            {/* Event Info */}
            <div className="fight-card-content">
              <div className="event-info">
                <h4 className="event-name">{fight.event}</h4>
                <div className="event-details">
                  <span className="event-date">📅 {fight.date}</span>
                  <span className="event-location">📍 {fight.location}</span>
                </div>
              </div>
              
              {/* Main Event Fighters */}
              <div className="main-event">
                <div className="fighter-row">
                  <span className="fighter-name">{fight.mainEvent.fighter1}</span>
                  {fight.mainEvent.prediction1 != null && (
                    <span className="fighter-prediction">{fight.mainEvent.prediction1}%</span>
                  )}
                </div>
                <div className="vs-separator">VS</div>
                <div className="fighter-row">
                  <span className="fighter-name">{fight.mainEvent.fighter2}</span>
                  {fight.mainEvent.prediction2 != null && (
                    <span className="fighter-prediction">{fight.mainEvent.prediction2}%</span>
                  )}
                </div>
              </div>

              {fight.mainEvent.prediction1 != null && (
                <div className="mini-prediction-bar">
                  <div className="mini-bar fighter1-bar" style={{ width: `${fight.mainEvent.prediction1}%` }} />
                  <div className="mini-bar fighter2-bar" style={{ width: `${fight.mainEvent.prediction2}%` }} />
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default UpcomingFights;