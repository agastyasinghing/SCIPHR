import React, { useState, useEffect } from 'react';
import api from '../api/api';
import './HistoricalScorecard.css';

/**
 * Historical Scorecard Page
 * Reads from predictions_log via GET /historical-scorecard.
 * Shows empty state at launch (predictions_log starts empty).
 * actual_winner populated post-fight by admin tool (TODO-10).
 */
const HistoricalScorecard = () => {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    api.getHistoricalScorecard()
      .then(setData)
      .catch((err) => setError(err?.message ?? 'Failed to load scorecard'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="scorecard-page">
        <div className="scorecard-loading">
          <div className="loading-spinner" />
          <p>Loading prediction history...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="scorecard-page">
        <div className="scorecard-error" role="alert">
          {error}
        </div>
      </div>
    );
  }

  const predictions = data?.predictions ?? [];

  return (
    <div className="scorecard-page">
      <div className="container">
        <div className="scorecard-header">
          <h1 className="scorecard-title">Historical Scorecard</h1>
          <p className="scorecard-subtitle">
            Every SCIPHR prediction, tracked against reality.
          </p>
        </div>

        {/* Summary Stats */}
        {predictions.length > 0 && (
          <div className="scorecard-stats">
            <div className="scorecard-stat">
              <span className="scorecard-stat-value">{data.total ?? predictions.length}</span>
              <span className="scorecard-stat-label">Total Picks</span>
            </div>
            {data.accuracy != null && (
              <div className="scorecard-stat">
                <span className="scorecard-stat-value">{data.accuracy}%</span>
                <span className="scorecard-stat-label">Accuracy</span>
              </div>
            )}
            {data.resolved_count > 0 && (
              <div className="scorecard-stat">
                <span className="scorecard-stat-value">{data.resolved_count}</span>
                <span className="scorecard-stat-label">Resolved</span>
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {predictions.length === 0 && (
          <div className="scorecard-empty">
            <div className="scorecard-empty-icon">📋</div>
            <h2>No prediction history yet</h2>
            <p>SCIPHR tracks every pick. Check back after fight night.</p>
            <a href="/picks" className="scorecard-cta">Make your first prediction</a>
          </div>
        )}

        {/* Predictions Table */}
        {predictions.length > 0 && (
          <div className="scorecard-table-wrapper">
            <table className="scorecard-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Matchup</th>
                  <th>SCIPHR Pick</th>
                  <th>Confidence</th>
                  <th>Edge Signal</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {predictions.map((p) => (
                  <tr key={p.id} className={p.correct === true ? 'row-correct' : p.correct === false ? 'row-wrong' : ''}>
                    <td className="scorecard-date">
                      {p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="scorecard-matchup">
                      {p.fighter1} vs {p.fighter2}
                    </td>
                    <td className="scorecard-pick">{p.predicted_winner ?? '—'}</td>
                    <td className="scorecard-confidence">
                      {p.confidence != null ? `${(p.confidence * 100).toFixed(1)}%` : '—'}
                    </td>
                    <td className="scorecard-signal">
                      {p.value_signal && p.value_signal !== 'NO_ODDS' && p.value_signal !== 'NO_EDGE'
                        ? <span className="signal-badge">{p.value_signal.replace(/_/g, ' ')}</span>
                        : '—'}
                    </td>
                    <td className="scorecard-result">
                      {p.correct === true  && <span className="result-correct">Correct</span>}
                      {p.correct === false && <span className="result-wrong">Wrong</span>}
                      {p.correct === null  && <span className="result-pending">Pending</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default HistoricalScorecard;
