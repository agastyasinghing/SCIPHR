import React, { useState, useEffect } from 'react';
import './AnalystMode.css';
import { 
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, 
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, 
  Tooltip, Legend, BarChart, Bar
} from 'recharts';

/**
 * Analyst Mode - Deep Statistical Breakdown
 * Shows all the features the ML model uses for predictions
 */
const AnalystMode = ({ fighter1, fighter2, prediction }) => {
  const [selectedSection, setSelectedSection] = useState('overview');
  const [detailedStats, setDetailedStats] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (fighter1 && fighter2) {
      fetchDetailedStats();
    }
  }, [fighter1, fighter2]);

  const fetchDetailedStats = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/detailed-stats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fighter1_name: fighter1.name,
          fighter2_name: fighter2.name
        })
      });
      const data = await response.json();
      setDetailedStats(data);
    } catch (error) {
      console.error('Error fetching detailed stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !detailedStats) {
    return (
      <div className="analyst-mode">
        <div className="analyst-loading">
          <div className="loading-spinner"></div>
          <p>Loading detailed analysis...</p>
        </div>
      </div>
    );
  }

  // Prepare data for visualizations
  const skillComparisonData = [
    { skill: 'Striking', [fighter1.name]: detailedStats.f1_str_acc || 0, [fighter2.name]: detailedStats.f2_str_acc || 0 },
    { skill: 'Grappling', [fighter1.name]: detailedStats.f1_td_acc || 0, [fighter2.name]: detailedStats.f2_td_acc || 0 },
    { skill: 'Strike Defense', [fighter1.name]: detailedStats.f1_str_def || 0, [fighter2.name]: detailedStats.f2_str_def || 0 },
    { skill: 'TD Defense', [fighter1.name]: detailedStats.f1_td_def || 0, [fighter2.name]: detailedStats.f2_td_def || 0 },
    { skill: 'Control', [fighter1.name]: detailedStats.f1_ctrl_ratio || 0, [fighter2.name]: detailedStats.f2_ctrl_ratio || 0 },
    { skill: 'Submissions', [fighter1.name]: detailedStats.f1_sub_avg || 0, [fighter2.name]: detailedStats.f2_sub_avg || 0 }
  ];

  const strikeLocationData = [
    { location: 'Head', [fighter1.name]: detailedStats.f1_head_acc || 0, [fighter2.name]: detailedStats.f2_head_acc || 0 },
    { location: 'Body', [fighter1.name]: detailedStats.f1_body_acc || 0, [fighter2.name]: detailedStats.f2_body_acc || 0 },
    { location: 'Legs', [fighter1.name]: detailedStats.f1_leg_acc || 0, [fighter2.name]: detailedStats.f2_leg_acc || 0 }
  ];

  const strikePositionData = [
    { position: 'Distance', [fighter1.name]: detailedStats.f1_distance_acc || 0, [fighter2.name]: detailedStats.f2_distance_acc || 0 },
    { position: 'Clinch', [fighter1.name]: detailedStats.f1_clinch_acc || 0, [fighter2.name]: detailedStats.f2_clinch_acc || 0 },
    { position: 'Ground', [fighter1.name]: detailedStats.f1_ground_acc || 0, [fighter2.name]: detailedStats.f2_ground_acc || 0 }
  ];

  const roundProgressionData = [
    { round: 'R1', [fighter1.name]: detailedStats.f1_r1_performance || 0, [fighter2.name]: detailedStats.f2_r1_performance || 0 },
    { round: 'R2', [fighter1.name]: detailedStats.f1_r2_performance || 0, [fighter2.name]: detailedStats.f2_r2_performance || 0 },
    { round: 'R3', [fighter1.name]: detailedStats.f1_r3_performance || 0, [fighter2.name]: detailedStats.f2_r3_performance || 0 },
    { round: 'R4', [fighter1.name]: detailedStats.f1_r4_performance || 0, [fighter2.name]: detailedStats.f2_r4_performance || 0 },
    { round: 'R5', [fighter1.name]: detailedStats.f1_r5_performance || 0, [fighter2.name]: detailedStats.f2_r5_performance || 0 }
  ];

  // Fighter momentum data
  const f1WinStreak = detailedStats.f1_win_streak || 0;
  const f2WinStreak = detailedStats.f2_win_streak || 0;
  const f1RecentRecord = detailedStats.f1_recent_fights || [];
  const f2RecentRecord = detailedStats.f2_recent_fights || [];

  return (
    <div className="analyst-mode">
      {/* Header */}
      <div className="analyst-header">
        <h2>🔬 Analyst Mode</h2>
        <p>Deep statistical breakdown using 5,426 features</p>
      </div>

      {/* Fighter Headers */}
      <div className="analyst-fighters">
        <div className="analyst-fighter left">
          <img src={`/fighters/${fighter1.name.replace(/ /g, '_')}.png`} alt={fighter1.name} />
          <div className="fighter-info">
            <h3>{fighter1.name}</h3>
            <p className="nickname">"{fighter1.stats.nickname}"</p>
            <p className="record">{Math.round(fighter1.stats.wins_total)}-{Math.round(fighter1.stats.losses_total)}-{Math.round(fighter1.stats.draw)}</p>
          </div>
        </div>
        <div className="analyst-vs">VS</div>
        <div className="analyst-fighter right">
          <div className="fighter-info">
            <h3>{fighter2.name}</h3>
            <p className="nickname">"{fighter2.stats.nickname}"</p>
            <p className="record">{Math.round(fighter2.stats.wins_total)}-{Math.round(fighter2.stats.losses_total)}-{Math.round(fighter2.stats.draw)}</p>
          </div>
          <img src={`/fighters/${fighter2.name.replace(/ /g, '_')}.png`} alt={fighter2.name} />
        </div>
      </div>

      {/* Navigation */}
      <div className="analyst-nav">
        <button 
          className={selectedSection === 'overview' ? 'active' : ''}
          onClick={() => setSelectedSection('overview')}
        >
          Overview
        </button>
        <button 
          className={selectedSection === 'striking' ? 'active' : ''}
          onClick={() => setSelectedSection('striking')}
        >
          Striking
        </button>
        <button 
          className={selectedSection === 'grappling' ? 'active' : ''}
          onClick={() => setSelectedSection('grappling')}
        >
          Grappling
        </button>
        <button 
          className={selectedSection === 'rounds' ? 'active' : ''}
          onClick={() => setSelectedSection('rounds')}
        >
          Round Analysis
        </button>
        <button 
          className={selectedSection === 'advanced' ? 'active' : ''}
          onClick={() => setSelectedSection('advanced')}
        >
          Advanced
        </button>
      </div>

      {/* Content Sections */}
      <div className="analyst-content">
        {selectedSection === 'overview' && (
          <OverviewSection 
            fighter1={fighter1}
            fighter2={fighter2}
            prediction={prediction}
            skillComparisonData={skillComparisonData}
            f1WinStreak={f1WinStreak}
            f2WinStreak={f2WinStreak}
            f1RecentRecord={f1RecentRecord}
            f2RecentRecord={f2RecentRecord}
          />
        )}

        {selectedSection === 'striking' && (
          <StrikingSection 
            fighter1={fighter1}
            fighter2={fighter2}
            strikeLocationData={strikeLocationData}
            strikePositionData={strikePositionData}
            detailedStats={detailedStats}
          />
        )}

        {selectedSection === 'grappling' && (
          <GrapplingSection 
            fighter1={fighter1}
            fighter2={fighter2}
            detailedStats={detailedStats}
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
            detailedStats={detailedStats}
          />
        )}
      </div>
    </div>
  );
};

// Overview Section Component
const OverviewSection = ({ fighter1, fighter2, prediction, skillComparisonData, f1WinStreak, f2WinStreak, f1RecentRecord, f2RecentRecord }) => {
  return (
    <div className="overview-section">
      {/* Fighter Momentum */}
      <div className="momentum-section">
        <h3>🏆 Fighter Momentum</h3>
        <div className="momentum-grid">
          <div className="momentum-card left">
            <h4>{fighter1.name}</h4>
            <div className="win-streak">
              <span className="streak-number">{f1WinStreak}</span>
              <span className="streak-label">Win streak momentum</span>
            </div>
            <div className="recent-fights">
              {f1RecentRecord.map((result, i) => (
                <div key={i} className={`fight-result ${result.toLowerCase()}`}>
                  {result === 'W' ? '✓' : '✗'}
                </div>
              ))}
            </div>
          </div>
          <div className="momentum-card right">
            <h4>{fighter2.name}</h4>
            <div className="win-streak">
              <span className="streak-number">{f2WinStreak}</span>
              <span className="streak-label">Win streak momentum</span>
            </div>
            <div className="recent-fights">
              {f2RecentRecord.map((result, i) => (
                <div key={i} className={`fight-result ${result.toLowerCase()}`}>
                  {result === 'W' ? '✓' : '✗'}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Skill Comparison Radar */}
      <div className="chart-section">
        <h3>🥊 Skill Comparison</h3>
        <ResponsiveContainer width="100%" height={400}>
          <RadarChart data={skillComparisonData}>
            <PolarGrid stroke="#333" />
            <PolarAngleAxis dataKey="skill" stroke="#fff" />
            <PolarRadiusAxis stroke="#666" />
            <Radar name={fighter1.name} dataKey={fighter1.name} stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
            <Radar name={fighter2.name} dataKey={fighter2.name} stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
            <Legend />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Prediction Summary */}
      {prediction && (
        <div className="prediction-summary">
          <h3>🔮 SCIPHR Prediction</h3>
          <div className="prediction-card">
            <div className="winner-name">{prediction.winner}</div>
            <div className="confidence">{(prediction.confidence * 100).toFixed(1)}% Confidence</div>
            <div className="method">Predicted Method: {prediction.method || 'Decision'}</div>
          </div>
        </div>
      )}
    </div>
  );
};

// Striking Section Component
const StrikingSection = ({ fighter1, fighter2, strikeLocationData, strikePositionData, detailedStats }) => {
  return (
    <div className="striking-section">
      <h3>👊 Striking Analysis</h3>
      
      {/* Strike Accuracy by Target */}
      <div className="chart-section">
        <h4>Strikes by Target</h4>
        <ResponsiveContainer width="100%" height={350}>
          <RadarChart data={strikeLocationData}>
            <PolarGrid stroke="#333" />
            <PolarAngleAxis dataKey="location" stroke="#fff" />
            <PolarRadiusAxis stroke="#666" />
            <Radar name={fighter1.name} dataKey={fighter1.name} stroke="#ef4444" fill="#ef4444" fillOpacity={0.4} />
            <Radar name={fighter2.name} dataKey={fighter2.name} stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.4} />
            <Legend />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Strike Position Distribution */}
      <div className="chart-section">
        <h4>Strikes by Position</h4>
        <ResponsiveContainer width="100%" height={350}>
          <RadarChart data={strikePositionData}>
            <PolarGrid stroke="#333" />
            <PolarAngleAxis dataKey="position" stroke="#fff" />
            <PolarRadiusAxis stroke="#666" />
            <Radar name={fighter1.name} dataKey={fighter1.name} stroke="#ef4444" fill="#ef4444" fillOpacity={0.4} />
            <Radar name={fighter2.name} dataKey={fighter2.name} stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.4} />
            <Legend />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Detailed Striking Stats */}
      <div className="stats-bars">
        <StatBar 
          label="Striking Accuracy" 
          f1Value={detailedStats.f1_str_acc} 
          f2Value={detailedStats.f2_str_acc}
          f1Name={fighter1.name}
          f2Name={fighter2.name}
        />
        <StatBar 
          label="Strike Defense" 
          f1Value={detailedStats.f1_str_def} 
          f2Value={detailedStats.f2_str_def}
          f1Name={fighter1.name}
          f2Name={fighter2.name}
        />
        <StatBar 
          label="Head Strike Accuracy" 
          f1Value={detailedStats.f1_head_acc} 
          f2Value={detailedStats.f2_head_acc}
          f1Name={fighter1.name}
          f2Name={fighter2.name}
        />
        <StatBar 
          label="Body Strike Accuracy" 
          f1Value={detailedStats.f1_body_acc} 
          f2Value={detailedStats.f2_body_acc}
          f1Name={fighter1.name}
          f2Name={fighter2.name}
        />
      </div>
    </div>
  );
};

// Grappling Section Component
const GrapplingSection = ({ fighter1, fighter2, detailedStats }) => {
  return (
    <div className="grappling-section">
      <h3>🤼 Grappling Analysis</h3>
      
      <div className="stats-bars">
        <StatBar 
          label="Takedown Accuracy" 
          f1Value={detailedStats.f1_td_acc} 
          f2Value={detailedStats.f2_td_acc}
          f1Name={fighter1.name}
          f2Name={fighter2.name}
        />
        <StatBar 
          label="Takedown Defense" 
          f1Value={detailedStats.f1_td_def} 
          f2Value={detailedStats.f2_td_def}
          f1Name={fighter1.name}
          f2Name={fighter2.name}
        />
        <StatBar 
          label="Takedowns Per Fight" 
          f1Value={detailedStats.f1_td_avg} 
          f2Value={detailedStats.f2_td_avg}
          f1Name={fighter1.name}
          f2Name={fighter2.name}
        />
        <StatBar 
          label="Submission Attempts" 
          f1Value={detailedStats.f1_sub_avg} 
          f2Value={detailedStats.f2_sub_avg}
          f1Name={fighter1.name}
          f2Name={fighter2.name}
        />
        <StatBar 
          label="Control Time Ratio" 
          f1Value={detailedStats.f1_ctrl_ratio} 
          f2Value={detailedStats.f2_ctrl_ratio}
          f1Name={fighter1.name}
          f2Name={fighter2.name}
        />
      </div>
    </div>
  );
};

// Round Analysis Section Component
const RoundAnalysisSection = ({ fighter1, fighter2, roundProgressionData }) => {
  return (
    <div className="round-analysis-section">
      <h3>📊 Round Progression</h3>
      <p className="section-description">
        Shows if fighters get stronger (line goes up) or weaker (line goes down) as the fight continues.
      </p>
      
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={roundProgressionData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis dataKey="round" stroke="#fff" />
          <YAxis stroke="#fff" />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1a1f2e', border: '1px solid #333' }}
            labelStyle={{ color: '#fff' }}
          />
          <Legend />
          <Line type="monotone" dataKey={fighter1.name} stroke="#ef4444" strokeWidth={3} />
          <Line type="monotone" dataKey={fighter2.name} stroke="#3b82f6" strokeWidth={3} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

// Advanced Section Component
const AdvancedSection = ({ fighter1, fighter2, detailedStats }) => {
  return (
    <div className="advanced-section">
      <h3>⚡ Advanced Metrics</h3>
      
      <div className="advanced-grid">
        <div className="metric-card">
          <h4>Clinch Efficiency</h4>
          <StatBar 
            label="Clinch Strike Accuracy" 
            f1Value={detailedStats.f1_clinch_acc} 
            f2Value={detailedStats.f2_clinch_acc}
            f1Name={fighter1.name}
            f2Name={fighter2.name}
          />
        </div>

        <div className="metric-card">
          <h4>Ground Game</h4>
          <StatBar 
            label="Ground Strike Accuracy" 
            f1Value={detailedStats.f1_ground_acc} 
            f2Value={detailedStats.f2_ground_acc}
            f1Name={fighter1.name}
            f2Name={fighter2.name}
          />
        </div>

        <div className="metric-card">
          <h4>Distance Fighting</h4>
          <StatBar 
            label="Distance Strike Accuracy" 
            f1Value={detailedStats.f1_distance_acc} 
            f2Value={detailedStats.f2_distance_acc}
            f1Name={fighter1.name}
            f2Name={fighter2.name}
          />
        </div>
      </div>
    </div>
  );
};

// StatBar Component
const StatBar = ({ label, f1Value, f2Value, f1Name, f2Name }) => {
  const f1Percentage = (f1Value / (f1Value + f2Value)) * 100 || 50;
  const f2Percentage = 100 - f1Percentage;
  const advantage = Math.abs(f1Value - f2Value);
  const advantageFighter = f1Value > f2Value ? f1Name : f2Name;

  return (
    <div className="stat-bar-container">
      <div className="stat-bar-header">
        <span className="stat-label">{label}</span>
        {advantage > 5 && (
          <span className="advantage-label">
            {advantageFighter} +{advantage.toFixed(1)}%
          </span>
        )}
      </div>
      <div className="stat-bar-values">
        <span className="f1-value">{f1Value?.toFixed(1)}%</span>
        <span className="f2-value">{f2Value?.toFixed(1)}%</span>
      </div>
      <div className="stat-bar">
        <div className="f1-bar" style={{ width: `${f1Percentage}%` }}></div>
        <div className="f2-bar" style={{ width: `${f2Percentage}%` }}></div>
      </div>
    </div>
  );
};

export default AnalystMode;