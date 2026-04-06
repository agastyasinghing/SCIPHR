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
 * Fetches upcoming and past events once on mount.
 * Also fetches card predictions for the Upset Watch feed once the upcoming
 * event is resolved.
 */
const Dashboard = () => {
  const [upcomingEvents, setUpcomingEvents]     = useState([]);
  const [pastEvents, setPastEvents]             = useState([]);
  const [eventsLoading, setEventsLoading]       = useState(true);
  const [eventsError, setEventsError]           = useState(null);
  const [cardPredictions, setCardPredictions]   = useState([]);

  useEffect(() => {
    Promise.all([api.getUpcomingEvents(), api.getPastEvents()])
      .then(([upcomingRes, pastRes]) => {
        const upcoming = upcomingRes?.events ?? (upcomingRes ? [upcomingRes] : []);
        const past     = pastRes?.events     ?? (pastRes     ? [pastRes]     : []);
        setUpcomingEvents(upcoming);
        setPastEvents(past);

        // Load card predictions for Upset Watch once we have the event id
        const eventId = upcomingRes?.event_id ?? upcoming[0]?.event_id;
        if (eventId) {
          api.getCardPredictions(eventId)
            .then(res => setCardPredictions(res?.predictions ?? []))
            .catch(() => setCardPredictions([]));
        }
      })
      .catch((err) => setEventsError(err?.message ?? 'Failed to load events'))
      .finally(() => setEventsLoading(false));
  }, []);

  // Upset Watch: fights where model gives 45–55% to either fighter (near coinflip)
  const upsetWatchFights = cardPredictions.filter(p => p.is_close);

  const [heroRef,        heroVisible]        = useScrollAnimation();
  const [quickLinksRef,  quickLinksVisible]  = useScrollAnimation();
  const [hotTakesRef,    hotTakesVisible]    = useScrollAnimation();
  const [upcomingRef,    upcomingVisible]    = useScrollAnimation();
  const [upsetRef,       upsetVisible]       = useScrollAnimation();
  const [timelineRef,    timelineVisible]    = useScrollAnimation();
  const [performanceRef, performanceVisible] = useScrollAnimation();
  const [updatesRef,     updatesVisible]     = useScrollAnimation();

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
            <span className="ticker-text">
              Latest: "Tom Aspinall confirms training camp has started for potential Jones bout" •
              Breaking: "UFC announces new event in Abu Dhabi" •
              Update: "Khamzat Chimaev cleared to fight"
            </span>
          </div>
        </div>

        {/* Hero Section */}
        <section ref={heroRef} className={`dashboard-section scroll-animate ${heroVisible ? 'visible' : ''}`}>
          {eventsLoading
            ? <div className="events-loading" aria-label="Loading events">Loading events…</div>
            : <HeroFightCard event={upcomingEvents[0] ?? null} />}
        </section>

        {/* Quick Links */}
        <section ref={quickLinksRef} className={`dashboard-section scroll-animate ${quickLinksVisible ? 'visible' : ''}`}>
          <QuickLinks />
        </section>

        {/* Editor's Picks (formerly "Hot Takes") */}
        <section ref={hotTakesRef} className={`dashboard-section scroll-animate ${hotTakesVisible ? 'visible' : ''}`}>
          <div className="section-header">
            <h2 className="section-title">
              <span className="title-icon">🔥</span>
              Editor's Picks
            </h2>
            <p className="section-subtitle">Manually curated fight angles — not model output</p>
          </div>
          <HotTakes />
        </section>

        {/* Upcoming Fights */}
        <section ref={upcomingRef} className={`dashboard-section scroll-animate ${upcomingVisible ? 'visible' : ''}`}>
          <div className="section-header">
            <h2 className="section-title">
              <span className="title-icon">🎯</span>
              Popular Upcoming Fights
            </h2>
          </div>
          <UpcomingFights events={upcomingEvents} />
        </section>

        {/* Upset Watch */}
        <section ref={upsetRef} className={`dashboard-section scroll-animate ${upsetVisible ? 'visible' : ''}`}>
          <div className="section-header">
            <h2 className="section-title">
              <span className="title-icon">🦷</span>
              Upset Watch
            </h2>
            <p className="section-subtitle">Fights where the model sees a near-coinflip — any result would surprise the room</p>
          </div>
          <UpsetWatchFeed fights={upsetWatchFights} loading={eventsLoading} />
        </section>

        {/* Events Timeline */}
        <section ref={timelineRef} className={`dashboard-section scroll-animate ${timelineVisible ? 'visible' : ''}`}>
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
        <section ref={performanceRef} className={`dashboard-section scroll-animate ${performanceVisible ? 'visible' : ''}`}>
          <div className="section-header">
            <h2 className="section-title">
              <span className="title-icon">📈</span>
              Current Performance of SCIPHR Models
            </h2>
            <p className="section-subtitle">
              Model accuracy is tracked on the{' '}
              <a href="/scorecard" className="scorecard-link">Historical Scorecard</a>{' '}
              — updated after every event.
            </p>
          </div>
          <ModelPerformance />
        </section>

        {/* Updates */}
        <section ref={updatesRef} className={`dashboard-section scroll-animate ${updatesVisible ? 'visible' : ''}`}>
          <div className="section-header">
            <h2 className="section-title">
              <span className="title-icon">📰</span>
              SCIPHR Updates
            </h2>
          </div>
          <div className="updates-list">
            <div className="update-item">
              <span className="update-version">v1.0</span>
              <span className="update-text">Phase 4 complete — intelligence signals, dashboard, fighter browser, scorecard</span>
            </div>
            <div className="update-item">
              <span className="update-version">v0.9</span>
              <span className="update-text">Phase 3 complete — all 11 intelligence modules wired, full API layer</span>
            </div>
            <div className="update-item">
              <span className="update-version">v0.8</span>
              <span className="update-text">Phase 1/2 complete — 8,231 fights in Supabase, XGBoost 85.7% accuracy</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

// ── Upset Watch Feed ──────────────────────────────────────────────────────────

const UpsetWatchFeed = ({ fights, loading }) => {
  if (loading) {
    return <p className="upset-watch-empty">Loading fight card...</p>;
  }
  if (!fights || fights.length === 0) {
    return (
      <div className="upset-watch-empty">
        <p>No Upset Watch fights on this card — model has high confidence across the board.</p>
      </div>
    );
  }

  return (
    <div className="upset-watch-grid">
      {fights.map((fight, i) => {
        const f1Pct = (fight.prob_fighter1 * 100).toFixed(1);
        const f2Pct = (fight.prob_fighter2 * 100).toFixed(1);
        return (
          <div key={fight.fight_id ?? i} className="upset-watch-card">
            <div className="upset-watch-header">
              <span className="upset-watch-badge">🦷 Upset Watch</span>
            </div>
            <div className="upset-watch-fighters">
              <div className="uw-fighter">
                <span className="uw-name">{fight.fighter1}</span>
                <span className="uw-pct">{f1Pct}%</span>
              </div>
              <span className="uw-vs">VS</span>
              <div className="uw-fighter uw-fighter--right">
                <span className="uw-name">{fight.fighter2}</span>
                <span className="uw-pct">{f2Pct}%</span>
              </div>
            </div>
            <div className="uw-bar">
              <div className="uw-bar-fill uw-bar-f1" style={{ width: `${f1Pct}%` }} />
              <div className="uw-bar-fill uw-bar-f2" style={{ width: `${f2Pct}%` }} />
            </div>
            <p className="uw-note">
              Model edge: {Math.abs(fight.prob_fighter1 - fight.prob_fighter2) < 0.05
                ? 'Near-perfect coinflip'
                : `${fight.winner} by ${((fight.confidence) * 100).toFixed(0)}%`}
            </p>
          </div>
        );
      })}
    </div>
  );
};

export default Dashboard;
