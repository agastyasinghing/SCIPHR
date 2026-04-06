import React, { useState, useEffect } from 'react';
import api from '../../api/api';
import './AnalystMode.css';
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend,
} from 'recharts';

// ---------------------------------------------------------------------------
// Confidence tier helper
// ---------------------------------------------------------------------------
const getConfidenceTier = (confidence) => {
  if (!confidence) return { tier: '—', color: '#6B7280' };
  if (confidence >= 0.75) return { tier: 'LOCK',     color: '#10B981' };
  if (confidence >= 0.65) return { tier: 'STRONG',   color: '#3B82F6' };
  if (confidence >= 0.55) return { tier: 'MODERATE', color: '#F59E0B' };
  return                         { tier: 'LEAN',     color: '#9CA3AF' };
};

/*
 * Data flow:
 *   PicksBuilder calls POST /predict → prediction prop
 *   prediction.fighter1_stats / fighter2_stats → stat tabs
 *   prediction.intelligence (all 11 modules)  → Intelligence tab
 *   Fight history fetched separately for each fighter via GET /fighter/:name/history
 */
const AnalystMode = ({ fighter1, fighter2, prediction }) => {
  const [selectedSection, setSelectedSection] = useState('overview');
  const [f1History, setF1History] = useState([]);
  const [f2History, setF2History] = useState([]);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiAnalysisLoading, setAiAnalysisLoading] = useState(false);
  const [aiAnalysisError, setAiAnalysisError] = useState(null);

  // Fetch fight history for both fighters when names are known
  useEffect(() => {
    if (fighter1?.name) {
      api.getFighterHistory(fighter1.name)
        .then(r => setF1History(r?.fights?.slice(0, 5) ?? []))
        .catch(() => setF1History([]));
    }
    if (fighter2?.name) {
      api.getFighterHistory(fighter2.name)
        .then(r => setF2History(r?.fights?.slice(0, 5) ?? []))
        .catch(() => setF2History([]));
    }
  }, [fighter1?.name, fighter2?.name]);

  // Fetch AI analysis when prediction is available (fires once per unique prediction)
  useEffect(() => {
    if (!prediction || !fighter1?.name || !fighter2?.name) return;
    setAiAnalysisLoading(true);
    setAiAnalysisError(null);
    setAiAnalysis(null);
    api.generateAIAnalysis(fighter1.name, fighter2.name, prediction)
      .then(r => setAiAnalysis(r?.analysis ?? null))
      .catch(err => {
        if (err.status === 429) {
          setAiAnalysisError('Rate limit reached — try again in an hour.');
        } else {
          setAiAnalysisError('AI analysis unavailable.');
        }
      })
      .finally(() => setAiAnalysisLoading(false));
  // Depend on winner+confidence so it refires on a new prediction, not on object identity
  }, [prediction?.winner, prediction?.confidence]); // eslint-disable-line react-hooks/exhaustive-deps

  const f1Stats = prediction?.fighter1_stats ?? {};
  const f2Stats = prediction?.fighter2_stats ?? {};
  const intel   = prediction?.intelligence   ?? {};

  const skillComparisonData = [
    { skill: 'Striking',       [fighter1?.name]: f1Stats.str_acc    ?? 0, [fighter2?.name]: f2Stats.str_acc    ?? 0 },
    { skill: 'Grappling',      [fighter1?.name]: f1Stats.td_acc     ?? 0, [fighter2?.name]: f2Stats.td_acc     ?? 0 },
    { skill: 'Strike Defense', [fighter1?.name]: f1Stats.str_def    ?? 0, [fighter2?.name]: f2Stats.str_def    ?? 0 },
    { skill: 'TD Defense',     [fighter1?.name]: f1Stats.td_def     ?? 0, [fighter2?.name]: f2Stats.td_def     ?? 0 },
    { skill: 'Control',        [fighter1?.name]: f1Stats.ctrl_ratio ?? 0, [fighter2?.name]: f2Stats.ctrl_ratio ?? 0 },
    { skill: 'Submissions',    [fighter1?.name]: f1Stats.sub_avg    ?? 0, [fighter2?.name]: f2Stats.sub_avg    ?? 0 },
  ];

  const strikeLocationData = [
    { location: 'Head', [fighter1?.name]: f1Stats.head_acc ?? 0, [fighter2?.name]: f2Stats.head_acc ?? 0 },
    { location: 'Body', [fighter1?.name]: f1Stats.body_acc ?? 0, [fighter2?.name]: f2Stats.body_acc ?? 0 },
    { location: 'Legs', [fighter1?.name]: f1Stats.leg_acc  ?? 0, [fighter2?.name]: f2Stats.leg_acc  ?? 0 },
  ];

  const strikePositionData = [
    { position: 'Distance', [fighter1?.name]: f1Stats.distance_acc ?? 0, [fighter2?.name]: f2Stats.distance_acc ?? 0 },
    { position: 'Clinch',   [fighter1?.name]: f1Stats.clinch_acc   ?? 0, [fighter2?.name]: f2Stats.clinch_acc   ?? 0 },
    { position: 'Ground',   [fighter1?.name]: f1Stats.ground_acc   ?? 0, [fighter2?.name]: f2Stats.ground_acc   ?? 0 },
  ];

  const roundProgressionData = [
    { round: 'R1', [fighter1?.name]: f1Stats.r_r1_sig_pct ?? 0, [fighter2?.name]: f2Stats.r_r1_sig_pct ?? 0 },
    { round: 'R2', [fighter1?.name]: f1Stats.r_r2_sig_pct ?? 0, [fighter2?.name]: f2Stats.r_r2_sig_pct ?? 0 },
    { round: 'R3', [fighter1?.name]: f1Stats.r_r3_sig_pct ?? 0, [fighter2?.name]: f2Stats.r_r3_sig_pct ?? 0 },
    { round: 'R4', [fighter1?.name]: f1Stats.r_r4_sig_pct ?? 0, [fighter2?.name]: f2Stats.r_r4_sig_pct ?? 0 },
    { round: 'R5', [fighter1?.name]: f1Stats.r_r5_sig_pct ?? 0, [fighter2?.name]: f2Stats.r_r5_sig_pct ?? 0 },
  ];

  const tabs = ['overview', 'striking', 'grappling', 'rounds', 'advanced', 'intelligence'];
  const confTier = getConfidenceTier(prediction?.confidence);

  return (
    <div className="analyst-mode">
      <div className="analyst-header">
        <h2>Analyst Mode</h2>
        {intel.cinematic_title?.title && (
          <p className="analyst-cinematic-title">{intel.cinematic_title.title}</p>
        )}
        <p>Deep statistical breakdown using 5,401 features</p>
      </div>

      <div className="analyst-fighters">
        <div className="analyst-fighter left">
          <img src={`/fighters/${fighter1?.name?.replace(/ /g, '_')}.png`} alt={fighter1?.name} />
          <div className="fighter-info">
            <h3>{fighter1?.name}</h3>
            <p className="record">
              {Math.round(f1Stats.wins_total ?? 0)}-{Math.round(f1Stats.losses_total ?? 0)}-{Math.round(f1Stats.draw ?? 0)}
            </p>
          </div>
        </div>
        <div className="analyst-vs">VS</div>
        <div className="analyst-fighter right">
          <div className="fighter-info">
            <h3>{fighter2?.name}</h3>
            <p className="record">
              {Math.round(f2Stats.wins_total ?? 0)}-{Math.round(f2Stats.losses_total ?? 0)}-{Math.round(f2Stats.draw ?? 0)}
            </p>
          </div>
          <img src={`/fighters/${fighter2?.name?.replace(/ /g, '_')}.png`} alt={fighter2?.name} />
        </div>
      </div>

      <div className="analyst-nav">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={selectedSection === tab ? 'active' : ''}
            onClick={() => setSelectedSection(tab)}
          >
            {tab === 'intelligence' ? 'Intelligence' :
             tab === 'rounds'       ? 'Round Analysis' :
             tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <div className="analyst-content">
        {selectedSection === 'overview' && (
          <OverviewSection
            fighter1={fighter1}
            fighter2={fighter2}
            prediction={prediction}
            skillComparisonData={skillComparisonData}
            f1Stats={f1Stats}
            f2Stats={f2Stats}
            confTier={confTier}
            f1History={f1History}
            f2History={f2History}
            aiAnalysis={aiAnalysis}
            aiAnalysisLoading={aiAnalysisLoading}
            aiAnalysisError={aiAnalysisError}
          />
        )}
        {selectedSection === 'striking' && (
          <StrikingSection
            fighter1={fighter1}
            fighter2={fighter2}
            strikeLocationData={strikeLocationData}
            strikePositionData={strikePositionData}
            f1Stats={f1Stats}
            f2Stats={f2Stats}
          />
        )}
        {selectedSection === 'grappling' && (
          <GrapplingSection
            fighter1={fighter1}
            fighter2={fighter2}
            f1Stats={f1Stats}
            f2Stats={f2Stats}
          />
        )}
        {selectedSection === 'rounds' && (
          <RoundAnalysisSection
            fighter1={fighter1}
            fighter2={fighter2}
            roundProgressionData={roundProgressionData}
          />
        )}
        {selectedSection === 'advanced' && (
          <AdvancedSection
            fighter1={fighter1}
            fighter2={fighter2}
            f1Stats={f1Stats}
            f2Stats={f2Stats}
          />
        )}
        {selectedSection === 'intelligence' && (
          <IntelligenceSection
            fighter1={fighter1}
            fighter2={fighter2}
            intel={intel}
          />
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Overview Section
// ---------------------------------------------------------------------------
const OverviewSection = ({
  fighter1, fighter2, prediction, skillComparisonData,
  f1Stats, f2Stats, confTier, f1History, f2History,
  aiAnalysis, aiAnalysisLoading, aiAnalysisError,
}) => {
  const probF1  = prediction ? (prediction.prob_fighter1 ?? 0) : null;
  const probF2  = prediction ? (prediction.prob_fighter2 ?? 0) : null;
  const vb      = prediction?.intelligence?.value_bet;
  const kelly   = vb && vb.signal !== 'NO_ODDS' && vb.kelly_fraction != null
    ? `${(vb.kelly_fraction * 100).toFixed(1)}% bankroll (half-Kelly)`
    : null;

  return (
    <div className="overview-section">
      {/* Prediction Confidence Panel */}
      {prediction && (
        <div className="prediction-summary">
          <h3>SCIPHR Prediction</h3>
          <div className="prediction-card">
            {/* Dual probability bar */}
            {probF1 !== null && (
              <div className="prob-bar-wrapper">
                <div className="prob-bar">
                  <div
                    className="prob-bar-fill prob-bar-f1"
                    style={{ width: `${(probF1 * 100).toFixed(1)}%` }}
                  >
                    <span className="prob-bar-label">{(probF1 * 100).toFixed(1)}%</span>
                  </div>
                  <div
                    className="prob-bar-fill prob-bar-f2"
                    style={{ width: `${(probF2 * 100).toFixed(1)}%` }}
                  >
                    <span className="prob-bar-label">{(probF2 * 100).toFixed(1)}%</span>
                  </div>
                </div>
                <div className="prob-bar-names">
                  <span>{fighter1?.name}</span>
                  <span>{fighter2?.name}</span>
                </div>
              </div>
            )}

            <div className="prediction-meta-row">
              <div className="winner-name">{prediction.winner}</div>
              <span
                className="confidence-tier-badge"
                style={{ color: confTier.color, borderColor: `${confTier.color}55` }}
              >
                {confTier.tier}
              </span>
            </div>
            <div className="confidence">{((prediction.confidence ?? 0) * 100).toFixed(1)}% Confidence</div>
            <div className="method">
              Most likely method: {prediction.intelligence?.win_path?.most_likely_method ?? 'Unknown'}
            </div>
            {kelly && (
              <div className="kelly-hint">
                <span className="kelly-icon">💰</span>
                <span>Suggested Kelly: {kelly}</span>
              </div>
            )}
          </div>

          {/* AI Analysis — fires async after prediction renders; hidden until there's content */}
          {(aiAnalysisLoading || aiAnalysisError || aiAnalysis) && (
          <div className="ai-analysis-panel">
            <h4 className="ai-analysis-header">AI Analysis</h4>
            {aiAnalysisLoading && (
              <div className="ai-analysis-loading">
                <div className="ai-spinner" aria-label="Analyzing" />
                <span>Analyzing...</span>
              </div>
            )}
            {aiAnalysisError && (
              <p className="ai-analysis-error">{aiAnalysisError}</p>
            )}
            {aiAnalysis && (
              <>
                {aiAnalysis.key_factors?.length > 0 && (
                  <div className="ai-subsection">
                    <h5>Key Factors</h5>
                    <ul className="ai-factors-list">
                      {aiAnalysis.key_factors.map((f, i) => <li key={i}>{f}</li>)}
                    </ul>
                  </div>
                )}
                <div className="ai-subsection">
                  <h5>Betting Guidance</h5>
                  <p className="ai-confidence-text">{aiAnalysis.confidence_text}</p>
                  <p>{aiAnalysis.betting_advice}</p>
                  {aiAnalysis.implied_odds && (
                    <p className="ai-implied-odds">Implied odds: {aiAnalysis.implied_odds}</p>
                  )}
                </div>
                {aiAnalysis.risk_factors?.length > 0 && (
                  <div className="ai-subsection">
                    <h5>Risk Factors</h5>
                    <ul className="ai-factors-list">
                      {aiAnalysis.risk_factors.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                )}
                <p className="ai-disclaimer">{aiAnalysis.disclaimer}</p>
              </>
            )}
          </div>
          )}
        </div>
      )}

      {/* Momentum */}
      <div className="momentum-section">
        <h3>Fighter Momentum</h3>
        <div className="momentum-grid">
          <div className="momentum-card left">
            <h4>{fighter1?.name}</h4>
            <div className="win-streak">
              <span className="streak-number">{f1Stats.current_win_streak ?? 0}</span>
              <span className="streak-label">Win streak</span>
            </div>
          </div>
          <div className="momentum-card right">
            <h4>{fighter2?.name}</h4>
            <div className="win-streak">
              <span className="streak-number">{f2Stats.current_win_streak ?? 0}</span>
              <span className="streak-label">Win streak</span>
            </div>
          </div>
        </div>
      </div>

      {/* Skill Comparison */}
      <div className="chart-section">
        <h3>Skill Comparison</h3>
        <ResponsiveContainer width="100%" height={400}>
          <RadarChart data={skillComparisonData}>
            <PolarGrid stroke="#333" />
            <PolarAngleAxis dataKey="skill" stroke="#fff" />
            <PolarRadiusAxis stroke="#666" />
            <Radar name={fighter1?.name} dataKey={fighter1?.name} stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
            <Radar name={fighter2?.name} dataKey={fighter2?.name} stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
            <Legend />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Recent Form */}
      {(f1History.length > 0 || f2History.length > 0) && (
        <div className="recent-form-section">
          <h3>Recent Form (Last 5 Fights)</h3>
          <div className="recent-form-grid">
            {[
              { name: fighter1?.name, history: f1History },
              { name: fighter2?.name, history: f2History },
            ].map(({ name, history }) => (
              <div key={name} className="recent-form-col">
                <h4>{name}</h4>
                {history.length === 0 ? (
                  <p className="form-empty">No history available</p>
                ) : (
                  <div className="form-list">
                    {history.map((fight, i) => (
                      <div key={i} className={`form-row form-row--${fight.result?.toLowerCase()}`}>
                        <span className={`form-result form-result--${fight.result?.toLowerCase()}`}>
                          {fight.result === 'W' ? 'W' : 'L'}
                        </span>
                        <div className="form-detail">
                          <span className="form-opponent">{fight.opponent}</span>
                          <span className="form-method">{fight.method || 'DEC'} · {fight.date}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Striking Section
// ---------------------------------------------------------------------------
const StrikingSection = ({ fighter1, fighter2, strikeLocationData, strikePositionData, f1Stats, f2Stats }) => (
  <div className="striking-section">
    <h3>Striking Analysis</h3>
    <div className="chart-section">
      <h4>Strikes by Target</h4>
      <ResponsiveContainer width="100%" height={350}>
        <RadarChart data={strikeLocationData}>
          <PolarGrid stroke="#333" />
          <PolarAngleAxis dataKey="location" stroke="#fff" />
          <PolarRadiusAxis stroke="#666" />
          <Radar name={fighter1?.name} dataKey={fighter1?.name} stroke="#ef4444" fill="#ef4444" fillOpacity={0.4} />
          <Radar name={fighter2?.name} dataKey={fighter2?.name} stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.4} />
          <Legend />
        </RadarChart>
      </ResponsiveContainer>
    </div>
    <div className="chart-section">
      <h4>Strikes by Position</h4>
      <ResponsiveContainer width="100%" height={350}>
        <RadarChart data={strikePositionData}>
          <PolarGrid stroke="#333" />
          <PolarAngleAxis dataKey="position" stroke="#fff" />
          <PolarRadiusAxis stroke="#666" />
          <Radar name={fighter1?.name} dataKey={fighter1?.name} stroke="#ef4444" fill="#ef4444" fillOpacity={0.4} />
          <Radar name={fighter2?.name} dataKey={fighter2?.name} stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.4} />
          <Legend />
        </RadarChart>
      </ResponsiveContainer>
    </div>
    <div className="stats-bars">
      <StatBar label="Striking Accuracy"     f1Value={f1Stats.str_acc}  f2Value={f2Stats.str_acc}  f1Name={fighter1?.name} f2Name={fighter2?.name} />
      <StatBar label="Strike Defense"        f1Value={f1Stats.str_def}  f2Value={f2Stats.str_def}  f1Name={fighter1?.name} f2Name={fighter2?.name} />
      <StatBar label="Head Strike Accuracy"  f1Value={f1Stats.head_acc} f2Value={f2Stats.head_acc} f1Name={fighter1?.name} f2Name={fighter2?.name} />
      <StatBar label="Body Strike Accuracy"  f1Value={f1Stats.body_acc} f2Value={f2Stats.body_acc} f1Name={fighter1?.name} f2Name={fighter2?.name} />
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Grappling Section
// ---------------------------------------------------------------------------
const GrapplingSection = ({ fighter1, fighter2, f1Stats, f2Stats }) => (
  <div className="grappling-section">
    <h3>Grappling Analysis</h3>
    <div className="stats-bars">
      <StatBar label="Takedown Accuracy"    f1Value={f1Stats.td_acc}     f2Value={f2Stats.td_acc}     f1Name={fighter1?.name} f2Name={fighter2?.name} />
      <StatBar label="Takedown Defense"     f1Value={f1Stats.td_def}     f2Value={f2Stats.td_def}     f1Name={fighter1?.name} f2Name={fighter2?.name} />
      <StatBar label="Takedowns Per Fight"  f1Value={f1Stats.td_avg}     f2Value={f2Stats.td_avg}     f1Name={fighter1?.name} f2Name={fighter2?.name} />
      <StatBar label="Submission Attempts"  f1Value={f1Stats.sub_avg}    f2Value={f2Stats.sub_avg}    f1Name={fighter1?.name} f2Name={fighter2?.name} />
      <StatBar label="Control Time Ratio"   f1Value={f1Stats.ctrl_ratio} f2Value={f2Stats.ctrl_ratio} f1Name={fighter1?.name} f2Name={fighter2?.name} />
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Round Analysis Section
// ---------------------------------------------------------------------------
const RoundAnalysisSection = ({ fighter1, fighter2, roundProgressionData }) => (
  <div className="round-analysis-section">
    <h3>Round Progression</h3>
    <p className="section-description">
      Shows if fighters get stronger (line goes up) or weaker (line goes down) as the fight continues.
    </p>
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={roundProgressionData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="round" stroke="#fff" />
        <YAxis stroke="#fff" />
        <Tooltip contentStyle={{ backgroundColor: '#1a1f2e', border: '1px solid #333' }} labelStyle={{ color: '#fff' }} />
        <Legend />
        <Line type="monotone" dataKey={fighter1?.name} stroke="#ef4444" strokeWidth={3} />
        <Line type="monotone" dataKey={fighter2?.name} stroke="#3b82f6" strokeWidth={3} />
      </LineChart>
    </ResponsiveContainer>
  </div>
);

// ---------------------------------------------------------------------------
// Advanced Section
// ---------------------------------------------------------------------------
const AdvancedSection = ({ fighter1, fighter2, f1Stats, f2Stats }) => (
  <div className="advanced-section">
    <h3>Advanced Metrics</h3>
    <div className="advanced-grid">
      <div className="metric-card">
        <h4>Clinch Efficiency</h4>
        <StatBar label="Clinch Strike Accuracy"   f1Value={f1Stats.clinch_acc}   f2Value={f2Stats.clinch_acc}   f1Name={fighter1?.name} f2Name={fighter2?.name} />
      </div>
      <div className="metric-card">
        <h4>Ground Game</h4>
        <StatBar label="Ground Strike Accuracy"   f1Value={f1Stats.ground_acc}   f2Value={f2Stats.ground_acc}   f1Name={fighter1?.name} f2Name={fighter2?.name} />
      </div>
      <div className="metric-card">
        <h4>Distance Fighting</h4>
        <StatBar label="Distance Strike Accuracy" f1Value={f1Stats.distance_acc} f2Value={f2Stats.distance_acc} f1Name={fighter1?.name} f2Name={fighter2?.name} />
      </div>
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Intelligence Section — all 11 SCIPHR signals + badges
// ---------------------------------------------------------------------------
const IntelligenceSection = ({ fighter1, fighter2, intel }) => {
  const badges   = intel.badges         ?? [];
  const chaos    = intel.chaos          ?? null;
  const pg       = intel.perception_gap ?? null;
  const nt       = intel.narrative_trap ?? null;
  const fc       = intel.false_consensus ?? null;
  const nm       = intel.nightmare      ?? null;
  const wp       = intel.win_path       ?? null;
  const dna      = intel.fight_dna      ?? null;
  const vb       = intel.value_bet      ?? null;
  const ua       = intel.upset_alert    ?? null;
  const sm       = intel.sharp_money    ?? null;
  const ct       = intel.cinematic_title ?? null;

  return (
    <div className="intelligence-section">
      {/* Cinematic Title */}
      {ct?.title && (
        <div className="intel-panel intel-panel--title">
          <div className="intel-panel-header">Fight Title</div>
          <div className="intel-cinematic-title">{ct.title}</div>
          {ct.subtitle && <div className="intel-cinematic-subtitle">{ct.subtitle}</div>}
        </div>
      )}

      {/* Badges */}
      {badges.length > 0 && (
        <div className="intel-panel">
          <div className="intel-panel-header">SCIPHR Badges</div>
          <div className="intel-badges-grid">
            {badges.map((badge) => (
              <div key={`${badge.key}-${badge.fighter}`} className={`intel-badge intel-badge--${badge.color}`}>
                <span className="intel-badge-label">{badge.label}</span>
                <span className="intel-badge-fighter">{badge.fighter}</span>
                <span className="intel-badge-reason">{badge.reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Chaos Score */}
      {chaos?.available && (
        <div className="intel-panel">
          <div className="intel-panel-header">Chaos Score</div>
          <div className="intel-row">
            <span className="intel-score">{chaos.score?.toFixed(0) ?? '—'}/100</span>
            <span className={`intel-tier intel-tier--${chaos.tier?.toLowerCase()}`}>{chaos.tier}</span>
          </div>
          {chaos.drivers?.length > 0 && (
            <div className="intel-drivers">
              {chaos.drivers.map((d) => <span key={d} className="intel-driver-tag">{d}</span>)}
            </div>
          )}
          {chaos.betting_implication && (
            <p className="intel-note">{chaos.betting_implication}</p>
          )}
        </div>
      )}

      {/* Perception Gap */}
      {pg?.available && (
        <div className="intel-panel">
          <div className="intel-panel-header">Perception Gap</div>
          <div className="intel-two-col">
            <div>
              <span className="intel-label">{fighter1?.name}</span>
              <span className={`intel-direction intel-direction--${pg.direction_f1?.toLowerCase()}`}>
                {pg.direction_f1} ({pg.gap_f1 >= 0 ? '+' : ''}{(pg.gap_f1 * 100).toFixed(0)}pts)
              </span>
            </div>
            <div>
              <span className="intel-label">{fighter2?.name}</span>
              <span className={`intel-direction intel-direction--${pg.direction_f2?.toLowerCase()}`}>
                {pg.direction_f2} ({pg.gap_f2 >= 0 ? '+' : ''}{(pg.gap_f2 * 100).toFixed(0)}pts)
              </span>
            </div>
          </div>
          <p className="intel-note">Gap magnitude: {pg.magnitude}</p>
        </div>
      )}

      {/* Narrative Trap */}
      {nt?.available && (
        <div className="intel-panel">
          <div className="intel-panel-header">Narrative Trap</div>
          <div className="intel-row">
            <span className={`intel-tier intel-tier--${nt.risk?.toLowerCase()}`}>Risk: {nt.risk}</span>
            {nt.trapped_fighter && <span className="intel-label">Trapped: {nt.trapped_fighter}</span>}
          </div>
          {nt.active_traps?.length > 0 && (
            <div className="intel-drivers">
              {nt.active_traps.map((trap) => <span key={trap} className="intel-driver-tag">{trap}</span>)}
            </div>
          )}
        </div>
      )}

      {/* False Consensus */}
      {fc?.available && fc.label !== 'NONE' && (
        <div className="intel-panel">
          <div className="intel-panel-header">False Consensus</div>
          <div className="intel-row">
            <span className="intel-score">{fc.label?.replace(/_/g, ' ')}</span>
          </div>
          {fc.display_message && <p className="intel-note">{fc.display_message}</p>}
        </div>
      )}

      {/* Nightmare Matchup */}
      {nm?.available && nm.is_nightmare && (
        <div className="intel-panel">
          <div className="intel-panel-header">Nightmare Matchup</div>
          <div className="intel-row">
            <span className={`intel-tier intel-tier--${nm.severity?.toLowerCase()}`}>{nm.severity}</span>
            {nm.nightmare_fighter && <span className="intel-label">{nm.nightmare_fighter} faces stylistic nightmare</span>}
          </div>
          {nm.matchup_label && <p className="intel-note">{nm.matchup_label?.replace(/_/g, ' ')}</p>}
        </div>
      )}

      {/* Kill Chain (Win Path) */}
      {wp?.available && (
        <div className="intel-panel">
          <div className="intel-panel-header">Kill Chain</div>
          <p className="intel-note">Most likely method: {wp.most_likely_method}</p>
          <div className="intel-two-col">
            <div>
              <div className="intel-label">{fighter1?.name}</div>
              {(wp.f1_paths ?? []).slice(0, 3).map((p) => (
                <div key={p.path} className="intel-path-row">
                  <span className="intel-path-label">{p.path?.replace(/_/g, ' ')}</span>
                  <span className="intel-path-pct">{((p.probability ?? 0) * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
            <div>
              <div className="intel-label">{fighter2?.name}</div>
              {(wp.f2_paths ?? []).slice(0, 3).map((p) => (
                <div key={p.path} className="intel-path-row">
                  <span className="intel-path-label">{p.path?.replace(/_/g, ' ')}</span>
                  <span className="intel-path-pct">{((p.probability ?? 0) * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Fight DNA — RadarChart across 8 dimensions */}
      {dna?.available && Object.keys(dna.f1_dna ?? {}).length > 0 && (() => {
        const dnaData = Object.keys(dna.f1_dna).map(dim => ({
          dim: dim.charAt(0).toUpperCase() + dim.slice(1),
          [fighter1?.name]: dna.f1_dna[dim],
          [fighter2?.name]: dna.f2_dna?.[dim] ?? 0,
        }));
        return (
          <div className="intel-panel">
            <div className="intel-panel-header">Fight DNA</div>
            <div className="intel-row">
              <span className="intel-score">{dna.collision_type?.replace(/_/g, ' ')}</span>
              <span className="intel-note">
                Clash intensity: {((dna.style_clash_intensity ?? 0) * 100).toFixed(0)}%
              </span>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={dnaData}>
                <PolarGrid stroke="#333" />
                <PolarAngleAxis dataKey="dim" stroke="#fff" tick={{ fontSize: 11 }} />
                <PolarRadiusAxis domain={[0, 1]} stroke="#666" tick={false} />
                <Radar name={fighter1?.name} dataKey={fighter1?.name} stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
                <Radar name={fighter2?.name} dataKey={fighter2?.name} stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
                <Legend />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        );
      })()}

      {/* Value Bet */}
      {vb && vb.signal !== 'NO_ODDS' && (
        <div className="intel-panel">
          <div className="intel-panel-header">Line Crack</div>
          <div className="intel-row">
            <span className={`intel-tier ${vb.signal === 'STRONG_EDGE' || vb.signal === 'EDGE_DETECTED' ? 'intel-tier--high' : ''}`}>
              {vb.signal?.replace(/_/g, ' ')}
            </span>
            {vb.edge_pct != null && (
              <span className="intel-score">
                Edge: {vb.edge_pct >= 0 ? '+' : ''}{(vb.edge_pct * 100).toFixed(1)}%
              </span>
            )}
          </div>
          {vb.kelly_fraction != null && (
            <p className="intel-note">Kelly fraction: {(vb.kelly_fraction * 100).toFixed(1)}%</p>
          )}
        </div>
      )}

      {/* Dog Teeth (Upset Alert) */}
      {ua?.is_alert && (
        <div className="intel-panel">
          <div className="intel-panel-header">Dog Teeth</div>
          <div className="intel-row">
            {ua.underdog_name && <span className="intel-label">{ua.underdog_name}</span>}
            {ua.american_odds != null && <span className="intel-score">+{ua.american_odds}</span>}
          </div>
          {ua.edge != null && (
            <p className="intel-note">
              Model edge: {ua.edge >= 0 ? '+' : ''}{(ua.edge * 100).toFixed(1)}%
              {ua.model_probability != null && ` (model: ${(ua.model_probability * 100).toFixed(0)}%)`}
            </p>
          )}
        </div>
      )}

      {/* Sharp Echo */}
      {sm && sm.signal !== undefined && (
        <div className="intel-panel">
          <div className="intel-panel-header">Sharp Echo</div>
          <div className="intel-row">
            <span className={`intel-tier ${sm.signal === 'MARKET_ALIGNMENT' ? 'intel-tier--high' : ''}`}>
              {sm.signal?.replace(/_/g, ' ')}
            </span>
            {sm.signal === 'MARKET_ALIGNMENT' && sm.movement_magnitude != null && (
              <span className="intel-note">
                Line moved {((sm.movement_magnitude ?? 0) * 100).toFixed(1)}pts toward model
              </span>
            )}
          </div>
        </div>
      )}

      {/* Fallback when no intel available */}
      {!chaos && !pg && !nt && !fc && !nm && !wp && !dna && badges.length === 0 && (
        <div className="intel-empty">
          <p>Run a prediction to see SCIPHR intelligence signals.</p>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// StatBar — shared comparison bar
// ---------------------------------------------------------------------------
const StatBar = ({ label, f1Value, f2Value, f1Name, f2Name }) => {
  const v1 = f1Value ?? 0;
  const v2 = f2Value ?? 0;
  const total = v1 + v2 || 1;
  const f1Pct = (v1 / total) * 100;
  const advantage = Math.abs(v1 - v2);
  const advantageFighter = v1 > v2 ? f1Name : f2Name;

  return (
    <div className="stat-bar-container">
      <div className="stat-bar-header">
        <span className="stat-label">{label}</span>
        {advantage > 5 && (
          <span className="advantage-label">{advantageFighter} +{advantage.toFixed(1)}%</span>
        )}
      </div>
      <div className="stat-bar-values">
        <span className="f1-value">{v1.toFixed(1)}%</span>
        <span className="f2-value">{v2.toFixed(1)}%</span>
      </div>
      <div className="stat-bar">
        <div className="f1-bar" style={{ width: `${f1Pct}%` }} />
        <div className="f2-bar" style={{ width: `${100 - f1Pct}%` }} />
      </div>
    </div>
  );
};

export default AnalystMode;
