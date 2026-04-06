import React from 'react';
import Card from '../shared/Card';
import './EventsTimeline.css';

/**
 * Events Timeline Component
 * Accepts upcoming and past event arrays from Dashboard.jsx (lifted state).
 * Falls back to empty state when both arrays are empty.
 */
const EventsTimeline = ({ upcoming = [], past = [] }) => {
  const now = new Date();

  const pastEvents = past.map((e) => ({
    id: `past-${e.id}`,
    name: e.name,
    date: e.date ? new Date(e.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '',
    status: 'past',
    fighters: (e.fights?.[0]
      ? [e.fights[0].r_fighter?.split(' ').pop(), e.fights[0].b_fighter?.split(' ').pop()]
      : []).filter(Boolean),
  }));

  const upcomingEvents = upcoming.map((e, idx) => ({
    id: `upcoming-${e.id}`,
    name: e.name,
    date: e.date ? new Date(e.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '',
    status: 'upcoming',
    isNext: idx === 0,
    fighters: (e.fights?.[0]
      ? [e.fights[0].r_fighter?.split(' ').pop(), e.fights[0].b_fighter?.split(' ').pop()]
      : []).filter(Boolean),
  }));

  const events = [...pastEvents.slice(-2), ...upcomingEvents.slice(0, 4)];
  
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