import React from 'react';
import Card from '../shared/Card';
import './UpcomingFights.css';

/**
 * Upcoming Fights Component
 * Grid of popular upcoming fight cards
 */
const UpcomingFights = () => {
  // Mock data
  const upcomingFights = [
    {
      id: 1,
      event: 'UFC 323',
      date: 'Dec 6, 2025',
      location: 'Las Vegas',
      mainEvent: {
        fighter1: 'Merab Dvalishvili',
        fighter2: 'Petr Yan',
        prediction1: 68,
        prediction2: 32,
      },
      image: '/events/ufc323.jpg',
      isTitle: true,
    },
    {
      id: 2,
      event: 'UFC Fight Night',
      date: 'Nov 29, 2025',
      location: 'Abu Dhabi',
      mainEvent: {
        fighter1: 'Robert Whittaker',
        fighter2: 'Khamzat Chimaev',
        prediction1: 45,
        prediction2: 55,
      },
      image: '/events/fightnight.jpg',
      isTitle: false,
    },
    {
      id: 3,
      event: 'UFC 324',
      date: 'Dec 13, 2025',
      location: 'New York',
      mainEvent: {
        fighter1: 'Jon Jones',
        fighter2: 'Tom Aspinall',
        prediction1: 52,
        prediction2: 48,
      },
      image: '/events/ufc324.jpg',
      isTitle: true,
    },
    {
      id: 4,
      event: 'UFC Fight Night',
      date: 'Dec 20, 2025',
      location: 'London',
      mainEvent: {
        fighter1: 'Leon Edwards',
        fighter2: 'Shavkat Rakhmonov',
        prediction1: 58,
        prediction2: 42,
      },
      image: '/events/london.jpg',
      isTitle: false,
    },
  ];
  
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
                  <span className="fighter-prediction">{fight.mainEvent.prediction1}%</span>
                </div>
                <div className="vs-separator">VS</div>
                <div className="fighter-row">
                  <span className="fighter-name">{fight.mainEvent.fighter2}</span>
                  <span className="fighter-prediction">{fight.mainEvent.prediction2}%</span>
                </div>
              </div>
              
              {/* Mini Prediction Bar */}
              <div className="mini-prediction-bar">
                <div 
                  className="mini-bar fighter1-bar"
                  style={{ width: `${fight.mainEvent.prediction1}%` }}
                ></div>
                <div 
                  className="mini-bar fighter2-bar"
                  style={{ width: `${fight.mainEvent.prediction2}%` }}
                ></div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default UpcomingFights;