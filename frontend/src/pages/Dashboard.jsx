import React, { useState, useEffect } from 'react';
import api from '../api/api';
import HeroFightCard from '../components/dashboard/HeroFightCard';
import QuickLinks from '../components/dashboard/QuickLinks';
import HotTakes from '../components/dashboard/HotTakes';
import UpcomingFights from '../components/dashboard/UpcomingFights';
import EventsTimeline from '../components/dashboard/EventsTimeline';
import ModelPerformance from '../components/dashboard/ModelPerformance';
import useScrollAnimation from '../hooks/useScrollAnimation';
import '../styles/global.css';
import './Dashboard.css';

/**
 * Main Dashboard Page
 * Fetches upcoming and past events once on mount and passes data as props.
 * Single fetch point — avoids duplicate API calls across child components.
 */
const Dashboard = () => {
  const [upcomingEvents, setUpcomingEvents] = useState([]);
  const [pastEvents, setPastEvents]         = useState([]);
  const [eventsLoading, setEventsLoading]   = useState(true);
  const [eventsError, setEventsError]       = useState(null);

  useEffect(() => {
    Promise.all([api.getUpcomingEvents(), api.getPastEvents()])
      .then(([upcomingRes, pastRes]) => {
        setUpcomingEvents(upcomingRes?.events ?? []);
        setPastEvents(pastRes?.events ?? []);
      })
      .catch((err) => setEventsError(err?.message ?? 'Failed to load events'))
      .finally(() => setEventsLoading(false));
  }, []);


  // Scroll animation refs
  const [heroRef, heroVisible] = useScrollAnimation();
  const [quickLinksRef, quickLinksVisible] = useScrollAnimation();
  const [hotTakesRef, hotTakesVisible] = useScrollAnimation();
  const [upcomingRef, upcomingVisible] = useScrollAnimation();
  const [timelineRef, timelineVisible] = useScrollAnimation();
  const [performanceRef, performanceVisible] = useScrollAnimation();
  const [updatesRef, updatesVisible] = useScrollAnimation();
  
  return (
    <div className="dashboard">
      <div className="container">
        {/* Events load error */}
        {eventsError && (
          <div className="dashboard-error" role="alert">
            Could not load events: {eventsError}
          </div>
        )}

        {/* News Ticker */}
        <div className="news-ticker">
          <span className="ticker-badge">🔴 LIVE</span>
          <div className="ticker-content">
            <span className="ticker-text">Latest: "Tom Aspinall confirms training camp has started for potential Jones bout" • Breaking: "UFC announces new event in Abu Dhabi" • Update: "Khamzat Chimaev cleared to fight"</span>
          </div>
        </div>
        
        {/* Hero Section - Next Main Event */}
        <section 
          ref={heroRef}
          className={`dashboard-section scroll-animate ${heroVisible ? 'visible' : ''}`}
        >
          {eventsLoading
            ? <div className="events-loading" aria-label="Loading events">Loading events…</div>
            : <HeroFightCard event={upcomingEvents[0] ?? null} />}

        </section>
        
        {/* Quick Links */}
        <section 
          ref={quickLinksRef}
          className={`dashboard-section scroll-animate ${quickLinksVisible ? 'visible' : ''}`}
        >
          <QuickLinks />
        </section>
        
        {/* Hot Takes Section */}
        <section 
          ref={hotTakesRef}
          className={`dashboard-section scroll-animate ${hotTakesVisible ? 'visible' : ''}`}
        >
          <div className="section-header">
            <h2 className="section-title">
              <span className="title-icon">🔥</span>
              Hot Takes - Controversial Predictions
            </h2>
            <p className="section-subtitle">Where SCIPHR disagrees with Vegas</p>
          </div>
          <HotTakes />
        </section>
        
        {/* Upcoming Fights Section */}
        <section 
          ref={upcomingRef}
          className={`dashboard-section scroll-animate ${upcomingVisible ? 'visible' : ''}`}
        >
          <div className="section-header">
            <h2 className="section-title">
              <span className="title-icon">🎯</span>
              Popular Upcoming Fights
            </h2>
          </div>
          <UpcomingFights events={upcomingEvents} />
        </section>
        
        {/* Events Timeline */}
        <section 
          ref={timelineRef}
          className={`dashboard-section scroll-animate ${timelineVisible ? 'visible' : ''}`}
        >
          <div className="section-header">
            <h2 className="section-title">
              <span className="title-icon">📅</span>
              Events Timeline
            </h2>
            <p className="section-subtitle">Past and upcoming UFC events</p>
          </div>
          <EventsTimeline upcoming={upcomingEvents} past={pastEvents} />
        </section>
        
        {/* Model Performance */}
        <section 
          ref={performanceRef}
          className={`dashboard-section scroll-animate ${performanceVisible ? 'visible' : ''}`}
        >
          <div className="section-header">
            <h2 className="section-title">
              <span className="title-icon">📈</span>
              Current Performance of SCIPHR Models
            </h2>
            <p className="section-subtitle">Based on 1,247 fight predictions with 12-month trailing average</p>
          </div>
          <ModelPerformance />
        </section>
        
        {/* Updates Section */}
        <section 
          ref={updatesRef}
          className={`dashboard-section scroll-animate ${updatesVisible ? 'visible' : ''}`}
        >
          <div className="section-header">
            <h2 className="section-title">
              <span className="title-icon">📰</span>
              SCIPHR Updates
            </h2>
          </div>
          <div className="updates-list">
            <div className="update-item">
              <span className="update-version">v2.0</span>
              <span className="update-text">Complete redesign with FightSignal-inspired UI</span>
            </div>
            <div className="update-item">
              <span className="update-version">v1.8</span>
              <span className="update-text">Backend integration with real-time predictions</span>
            </div>
            <div className="update-item">
              <span className="update-version">v1.7</span>
              <span className="update-text">Added value bet indicators for monetization</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Dashboard;