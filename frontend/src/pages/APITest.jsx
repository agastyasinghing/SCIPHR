import React, { useState, useEffect } from 'react';
import api from '../api/api';
import Button from '../components/shared/Button';
import Card from '../components/shared/Card';
import '../styles/global.css';

/**
 * API Test Page
 * Tests connection to FastAPI backend
 */
const APITest = () => {
  const [status, setStatus] = useState('Not tested');
  const [fighters, setFighters] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fighter1, setFighter1] = useState('Merab Dvalishvili');
  const [fighter2, setFighter2] = useState('Petr Yan');
  
  // Test health check
  const testHealthCheck = async () => {
    setLoading(true);
    try {
      const result = await api.healthCheck();
      setStatus(`✅ Connected! ${result.message}`);
    } catch (error) {
      setStatus(`❌ Connection failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Test fighters endpoint
  const testGetFighters = async () => {
    setLoading(true);
    try {
      const result = await api.getFighters('', 20);
      setFighters(result.fighters);
      setStatus(`✅ Got ${result.count} fighters`);
    } catch (error) {
      setStatus(`❌ Failed to get fighters: ${error.message}`);
      setFighters([]);
    } finally {
      setLoading(false);
    }
  };
  
  // Test prediction endpoint
  const testPrediction = async () => {
    setLoading(true);
    setPrediction(null);
    try {
      const result = await api.predictFight(fighter1, fighter2);
      setPrediction(result);
      setStatus(`✅ Got prediction!`);
    } catch (error) {
      setStatus(`❌ Prediction failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Auto-test on mount
  useEffect(() => {
    testHealthCheck();
  }, []);
  
  return (
    <div className="container" style={{ padding: '2rem' }}>
      <h1>🧪 API Backend Test</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
        Testing connection to FastAPI backend at <code>localhost:8000</code>
      </p>
      
      {/* Status */}
      <Card variant="glass" style={{ marginBottom: '2rem' }}>
        <h3>Connection Status</h3>
        <p style={{ 
          fontSize: '1.125rem', 
          fontWeight: 600,
          color: status.includes('✅') ? 'var(--accent-lime)' : 'var(--accent-red)'
        }}>
          {status}
        </p>
      </Card>
      
      {/* Test Buttons */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '2rem' }}>
        <Button onClick={testHealthCheck} disabled={loading}>
          Test Health Check
        </Button>
        <Button onClick={testGetFighters} variant="secondary" disabled={loading}>
          Get Fighters List
        </Button>
      </div>
      
      {/* Fighters List */}
      {fighters.length > 0 && (
        <Card variant="glass" style={{ marginBottom: '2rem' }}>
          <h3>Available Fighters ({fighters.length})</h3>
          <div style={{ 
            maxHeight: '200px', 
            overflow: 'auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: '0.5rem',
            marginTop: '1rem'
          }}>
            {fighters.map((fighter, idx) => (
              <div key={idx} style={{ 
                padding: '0.5rem',
                background: 'rgba(255, 255, 255, 0.05)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem'
              }}>
                {fighter}
              </div>
            ))}
          </div>
        </Card>
      )}
      
      {/* Prediction Test */}
      <Card variant="glass" style={{ marginBottom: '2rem' }}>
        <h3>Test Prediction</h3>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          <input
            type="text"
            value={fighter1}
            onChange={(e) => setFighter1(e.target.value)}
            placeholder="Fighter 1"
            style={{
              flex: 1,
              minWidth: '200px',
              padding: '0.75rem',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-primary)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontSize: '1rem'
            }}
          />
          <span style={{ alignSelf: 'center', fontSize: '1.5rem' }}>VS</span>
          <input
            type="text"
            value={fighter2}
            onChange={(e) => setFighter2(e.target.value)}
            placeholder="Fighter 2"
            style={{
              flex: 1,
              minWidth: '200px',
              padding: '0.75rem',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-primary)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              fontSize: '1rem'
            }}
          />
        </div>
        <Button onClick={testPrediction} disabled={loading} variant="primary">
          Get Prediction
        </Button>
      </Card>
      
      {/* Prediction Result */}
      {prediction && (
        <Card variant="elevated" glow={true} glowColor="yellow">
          <h3>🎯 Prediction Result</h3>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem',
            marginTop: '1rem'
          }}>
            <div>
              <h4 style={{ color: 'var(--fighter-red)' }}>Fighter 1</h4>
              <p>{prediction.fighter1}</p>
              <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--accent-yellow)' }}>
                {(prediction.prob_fighter1 * 100).toFixed(1)}%
              </p>
            </div>
            
            <div>
              <h4 style={{ color: 'var(--fighter-blue)' }}>Fighter 2</h4>
              <p>{prediction.fighter2}</p>
              <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--accent-cyan)' }}>
                {(prediction.prob_fighter2 * 100).toFixed(1)}%
              </p>
            </div>
          </div>
          
          <div style={{ 
            marginTop: '2rem',
            padding: '1rem',
            background: 'rgba(132, 204, 22, 0.1)',
            borderRadius: 'var(--radius-md)'
          }}>
            <h4>🏆 Winner</h4>
            <p style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--accent-lime)' }}>
              {prediction.winner} ({(prediction.confidence * 100).toFixed(0)}% confidence)
            </p>
          </div>
          
          {prediction.ai_analysis && (
            <div style={{ marginTop: '2rem' }}>
              <h4>🤖 AI Analysis</h4>
              <div style={{ 
                marginTop: '1rem',
                padding: '1rem',
                background: 'rgba(255, 255, 255, 0.05)',
                borderRadius: 'var(--radius-md)',
                fontSize: '0.875rem',
                lineHeight: 1.6
              }}>
                <p><strong>Confidence Level:</strong> {prediction.ai_analysis.confidence_level}</p>
                <p><strong>Betting Advice:</strong> {prediction.ai_analysis.betting_advice}</p>
                {prediction.ai_analysis.key_factors && (
                  <>
                    <p><strong>Key Factors:</strong></p>
                    <ul>
                      {prediction.ai_analysis.key_factors.map((factor, idx) => (
                        <li key={idx}>{factor}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </div>
          )}
        </Card>
      )}
      
      {loading && (
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <div className="loading-spinner" style={{ margin: '0 auto' }}></div>
          <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Loading...</p>
        </div>
      )}
    </div>
  );
};

export default APITest;