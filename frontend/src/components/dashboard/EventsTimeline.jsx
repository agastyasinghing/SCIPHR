import React from 'react';
import Card from '../shared/Card';
import './EventsTimeline.css';

/**
 * Events Timeline Component
 * Visual timeline of past and upcoming UFC events
 */
const EventsTimeline = () => {
  // Mock data
  const events = [
    {
      id: 1,
      name: 'UFC 320',
      date: 'Nov 8',
      status: 'past',
      fighters: ['Jones', 'Miocic'],
    },
    {
      id: 2,
      name: 'UFC Fight Night',
      date: 'Nov 15',
      status: 'past',
      fighters: ['Aspinall', 'Blaydes'],
    },
    {
      id: 3,
      name: 'UFC Qatar',
      date: 'Nov 22',
      status: 'recent',
      fighters: ['Tsarukyan', 'Hooker'],
    },
    {
      id: 4,
      name: 'UFC 323',
      date: 'Dec 6',
      status: 'upcoming',
      fighters: ['Dvalishvili', 'Yan'],
      isNext: true,
    },
    {
      id: 5,
      name: 'UFC 324',
      date: 'Dec 13',
      status: 'upcoming',
      fighters: ['Jones', 'Aspinall'],
    },
    {
      id: 6,
      name: 'UFC Fight Night',
      date: 'Dec 20',
      status: 'upcoming',
      fighters: ['Edwards', 'Rakhmonov'],
    },
  ];
  
  return (
    <div className="events-timeline-section">
      <Card variant="glass" className="timeline-card">
        {/* Timeline Container */}
        <div className="timeline-container">
          <div className="timeline-line"></div>
          
          <div className="timeline-events">
            {events.map((event, index) => (
              <div 
                key={event.id}
                className={`timeline-event ${event.status} ${event.isNext ? 'next-event' : ''}`}
              >
                {/* Event Node */}
                <div className="event-node">
                  {event.isNext && (
                    <div className="next-indicator">
                      <span>NEXT</span>
                    </div>
                  )}
                  <div className="node-circle">
                    {event.status === 'past' && <span>✓</span>}
                    {event.status === 'recent' && <span>🔴</span>}
                    {event.status === 'upcoming' && <span>◯</span>}
                  </div>
                </div>
                
                {/* Event Info */}
                <div className="event-info-card">
                  <div className="event-date">{event.date}</div>
                  <div className="event-name">{event.name}</div>
                  <div className="event-fighters">
                    {event.fighters.map((fighter, idx) => (
                      <span key={idx} className="fighter-avatar" title={fighter}>
                        {fighter.charAt(0)}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
        
        {/* Quick Actions */}
        <div className="timeline-actions">
          <button className="timeline-action-btn upcoming-btn">
            <span className="action-icon">📅</span>
            <span>Upcoming Events</span>
          </button>
          <button className="timeline-action-btn past-btn">
            <span className="action-icon">⏰</span>
            <span>Past Events</span>
          </button>
          <button className="timeline-action-btn all-btn">
            <span className="action-icon">📚</span>
            <span>All Events</span>
          </button>
        </div>
      </Card>
    </div>
  );
};

export default EventsTimeline;