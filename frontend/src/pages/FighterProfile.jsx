import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/api';
import Card from '../components/shared/Card';
import Button from '../components/shared/Button';
import './FighterProfile.css';
import { getFighterImage } from '../utils/imageUtils';

const WEIGHT_CLASS_COLORS = {
  'Strawweight':       { primary: '#EC4899', secondary: '#BE185D', bg: 'rgba(236,72,153,0.1)' },
  'Flyweight':         { primary: '#8B5CF6', secondary: '#6D28D9', bg: 'rgba(139,92,246,0.1)' },
  'Bantamweight':      { primary: '#3B82F6', secondary: '#1D4ED8', bg: 'rgba(59,130,246,0.1)' },
  'Featherweight':     { primary: '#06B6D4', secondary: '#0E7490', bg: 'rgba(6,182,212,0.1)' },
  'Lightweight':       { primary: '#10B981', secondary: '#047857', bg: 'rgba(16,185,129,0.1)' },
  'Welterweight':      { primary: '#FACC15', secondary: '#CA8A04', bg: 'rgba(250,204,21,0.1)' },
  'Middleweight':      { primary: '#F59E0B', secondary: '#D97706', bg: 'rgba(245,158,11,0.1)' },
  'Light Heavyweight': { primary: '#EF4444', secondary: '#B91C1C', bg: 'rgba(239,68,68,0.1)' },
  'Heavyweight':       { primary: '#7C3AED', secondary: '#5B21B6', bg: 'rgba(124,58,237,0.1)' },
};

const ScoreBar = ({ label, value, max = 100, color = '#10B981', note }) => {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="score-bar-row">
      <div className="score-bar-header">
        <span className="score-bar-label">{label}</span>
        <span className="score-bar-value" style={{ color }}>{value.toFixed(0)}/100</span>
      </div>
      {note && <span className="score-bar-note">{note}</span>}
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
};

/**
 * Fighter Profile Page
 */
const FighterProfile = () => {
  const { name } = useParams();
  const navigate = useNavigate();
  const [fighter, setFighter]     = useState(null);
  const [history, setHistory]     = useState([]);
  const [loading, setLoading]     = useState(true);
  const [histLoading, setHistLoading] = useState(false);
  const [error, setError]         = useState(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getFighterProfile(name);
        setFighter(result);
        // Fetch fight history in parallel
        setHistLoading(true);
        api.getFighterHistory(result.name)
          .then(h => setHistory(h?.fights ?? []))
          .catch(() => setHistory([]))
          .finally(() => setHistLoading(false));
      } catch {
        setError('Fighter not found');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [name]);

  if (loading) {
    return (
      <div className="fighter-profile-page">
        <div className="container">
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Loading fighter profile...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !fighter) {
    return (
      <div className="fighter-profile-page">
        <div className="container">
          <div className="error-state">
            <span className="error-icon">❌</span>
            <h2>Fighter Not Found</h2>
            <p>We couldn't find a fighter with that name.</p>
            <Button onClick={() => navigate('/fighters')}>Back to Fighters</Button>
          </div>
        </div>
      </div>
    );
  }

  const stats    = fighter.stats;
  const intel    = fighter.intelligence ?? {};
  const wc       = stats.weight_class || 'Welterweight';
  const colors   = WEIGHT_CLASS_COLORS[wc] || WEIGHT_CLASS_COLORS['Welterweight'];

  const wins   = Math.round(stats.wins_total   || 0);
  const losses = Math.round(stats.losses_total || 0);
  const draws  = Math.round(stats.draw         || 0);
  const age    = Math.round(stats.age          || 0);
  const height = stats.height ? `${Math.round(stats.height)} cm` : 'N/A';
  const reach  = stats.reach  ? `${Math.round(stats.reach)} cm`  : 'N/A';

  const slpm    = (stats.SLpM_total         || 0).toFixed(2);
  const strAcc  = (stats.sig_str_acc_total  || 0).toFixed(1);
  const strDef  = (stats.sig_str_def_total  || 0).toFixed(1);
  const tdAvg   = (stats.td_avg_total       || 0).toFixed(2);
  const tdAcc   = (stats.td_acc_total       || 0).toFixed(1);
  const tdDef   = (stats.td_def_total       || 0).toFixed(1);
  const subAvg  = (stats.sub_avg_total      || 0).toFixed(2);

  const style           = intel.style             || 'STRIKER';
  const auraScore       = intel.aura_score        ?? 0;
  const compositeScore  = intel.composite_score   ?? 0;
  const chaosContrib    = intel.chaos_contribution ?? 0;
  const mirageMeter     = intel.mirage_meter      ?? 0;

  const handlePredict = () => {
    navigate(`/picks?fighter1=${encodeURIComponent(fighter.name)}`);
  };

  return (
    <div className="fighter-profile-page">
      <div className="container">
        {/* Back */}
        <Button variant="ghost" icon={<span>←</span>} onClick={() => navigate('/fighters')} className="back-button">
          Back to Fighters
        </Button>

        {/* Header */}
        <Card variant="elevated" className="fighter-header">
          <div className="header-content">
            <div className="fighter-avatar-large">
              <img src={getFighterImage(fighter.name, stats.weight_class)} alt={fighter.name} />
            </div>

            <div className="fighter-header-info">
              <div className="fighter-name-row">
                <h1 className="fighter-name-large">{fighter.name}</h1>
                {intel.is_active === false && <span className="inactive-badge">Inactive</span>}
              </div>

              <div className="fighter-badges">
                <span
                  className="weight-class-badge"
                  style={{ background: colors.bg, borderColor: colors.primary, color: colors.primary }}
                >
                  {wc}
                </span>
                <span
                  className="style-badge"
                  style={{ background: 'rgba(107,114,128,0.2)', borderColor: '#6B7280', color: '#9CA3AF' }}
                >
                  {style}
                </span>
              </div>

              <div className="fighter-vitals">
                {[
                  ['Record', `${wins}-${losses}-${draws}`],
                  ['Age', age || 'N/A'],
                  ['Height', height],
                  ['Reach', reach],
                ].map(([label, val]) => (
                  <React.Fragment key={label}>
                    <div className="vital-item">
                      <span className="vital-label">{label}</span>
                      <span className="vital-value">{val}</span>
                    </div>
                    <div className="vital-divider" />
                  </React.Fragment>
                ))}
              </div>

              <Button variant="primary" size="medium" onClick={handlePredict} style={{ marginTop: '1rem' }}>
                🥊 Predict a fight with {fighter.name.split(' ')[0]}
              </Button>
            </div>
          </div>
        </Card>

        {/* Intelligence Scores */}
        <Card variant="glass" className="stat-card intelligence-card">
          <div className="stat-card-header">
            <span className="stat-icon">🧠</span>
            <h3>SCIPHR Intelligence</h3>
          </div>
          <div className="intelligence-scores">
            <ScoreBar
              label="Composite Score"
              value={compositeScore}
              color={colors.primary}
              note="Overall SCIPHR quality rating"
            />
            <ScoreBar
              label="Aura Score"
              value={auraScore}
              color="#8B5CF6"
              note="Public hype proxy — higher = more hyped"
            />
            <ScoreBar
              label="Chaos Contribution"
              value={chaosContrib}
              color="#F59E0B"
              note="How much this fighter raises fight volatility"
            />
            <ScoreBar
              label="Mirage Meter"
              value={mirageMeter}
              color="#EF4444"
              note="Resume inflation — higher = potentially inflated record"
            />
          </div>
        </Card>

        {/* Stats Grid */}
        <div className="stats-grid">
          {/* Striking */}
          <Card variant="glass" className="stat-card striking-card">
            <div className="stat-card-header"><span className="stat-icon">👊</span><h3>Striking</h3></div>
            <div className="stat-rows">
              <div className="stat-row"><span className="stat-label">Sig. Strikes Landed/Min</span><span className="stat-value">{slpm}</span></div>
              <div className="stat-row"><span className="stat-label">Striking Accuracy</span><span className="stat-value">{strAcc}%</span></div>
              <div className="stat-row"><span className="stat-label">Strike Defense</span><span className="stat-value">{strDef}%</span></div>
              <div className="stat-row"><span className="stat-label">Total Knockdowns</span><span className="stat-value">{Math.round(stats.total_knockdowns || 0)}</span></div>
            </div>
          </Card>

          {/* Grappling */}
          <Card variant="glass" className="stat-card grappling-card">
            <div className="stat-card-header"><span className="stat-icon">🤼</span><h3>Grappling</h3></div>
            <div className="stat-rows">
              <div className="stat-row"><span className="stat-label">Takedowns/15min</span><span className="stat-value">{tdAvg}</span></div>
              <div className="stat-row"><span className="stat-label">Takedown Accuracy</span><span className="stat-value">{tdAcc}%</span></div>
              <div className="stat-row"><span className="stat-label">Takedown Defense</span><span className="stat-value">{tdDef}%</span></div>
              <div className="stat-row"><span className="stat-label">Submissions/15min</span><span className="stat-value">{subAvg}</span></div>
            </div>
          </Card>

          {/* Career */}
          <Card variant="glass" className="stat-card career-card">
            <div className="stat-card-header"><span className="stat-icon">🏆</span><h3>Career</h3></div>
            <div className="stat-rows">
              <div className="stat-row"><span className="stat-label">Total Fights</span><span className="stat-value">{wins + losses + draws}</span></div>
              <div className="stat-row"><span className="stat-label">Win Rate</span><span className="stat-value">{wins > 0 ? ((wins / (wins + losses)) * 100).toFixed(1) : 0}%</span></div>
              <div className="stat-row"><span className="stat-label">Wins</span><span className="stat-value">{wins}</span></div>
              <div className="stat-row"><span className="stat-label">Losses</span><span className="stat-value">{losses}</span></div>
            </div>
          </Card>

          {/* Physical */}
          <Card variant="glass" className="stat-card physical-card">
            <div className="stat-card-header"><span className="stat-icon">📏</span><h3>Physical</h3></div>
            <div className="stat-rows">
              <div className="stat-row"><span className="stat-label">Age</span><span className="stat-value">{age} years</span></div>
              <div className="stat-row"><span className="stat-label">Height</span><span className="stat-value">{height}</span></div>
              <div className="stat-row"><span className="stat-label">Reach</span><span className="stat-value">{reach}</span></div>
              <div className="stat-row"><span className="stat-label">Weight Class</span><span className="stat-value">{wc}</span></div>
            </div>
          </Card>
        </div>

        {/* Fight History */}
        <Card variant="glass" className="stat-card history-card">
          <div className="stat-card-header"><span className="stat-icon">📋</span><h3>Fight History</h3></div>
          {histLoading ? (
            <p className="history-loading">Loading fight history...</p>
          ) : history.length === 0 ? (
            <p className="history-empty">No fight history available.</p>
          ) : (
            <div className="history-table-wrapper">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Opponent</th>
                    <th>Result</th>
                    <th>Method</th>
                    <th>Weight Class</th>
                  </tr>
                </thead>
                <tbody>
                  {history.slice(0, 10).map((fight, i) => (
                    <tr key={i}>
                      <td>{fight.date || '—'}</td>
                      <td
                        className="history-opponent"
                        onClick={() => navigate(`/fighter/${encodeURIComponent(fight.opponent)}`)}
                      >
                        {fight.opponent}
                      </td>
                      <td>
                        <span className={`result-badge result-${fight.result?.toLowerCase()}`}>
                          {fight.result === 'W' ? 'Win' : fight.result === 'L' ? 'Loss' : fight.result}
                        </span>
                      </td>
                      <td>{fight.method || '—'}</td>
                      <td>{fight.weight_class || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default FighterProfile;
