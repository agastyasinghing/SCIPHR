import React from 'react';
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
 * Landing page showing next event, quick links, and key features
 */
const Dashboard = () => {
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
          <HeroFightCard />
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
          <UpcomingFights />
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
          <EventsTimeline />
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